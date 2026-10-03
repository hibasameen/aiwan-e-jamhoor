#!/usr/bin/env python3
"""
Per-inset transforms for the labelled Commons election maps (1990, 1993, 1997).

Each city box on these maps is a zoomed copy of a patch that the main map
draws as a flat light-grey placeholder (#c3c3c3) — Peshawar, Rawalpindi,
Faisalabad, Lahore and Karachi. So a box need not be fitted against modern
district outlines: it is fitted, in pixel space, against its own placeholder
on the main map, and then carried to lon/lat with the main map.

    box px --(scale + shift, fit_inset)--> main-map px --(main-map transform)--> lon/lat

Placeholder mask. Comparison is made only inside the box's own rectangle, so a
box whose frame clips a seat (Karachi's NA-196) costs nothing.

Model. Scale + shift (3 parameters) by default: the boxes look like straight
enlargements, north up. 'sim' adds rotation, 'affine' the full six.

Pairing. Every box is tried against every placeholder and the best-scoring
one-to-one pairing is kept, so no labels are needed to place a box. The labels
then serve as an independent check.

fit_inset_geo fits pixels straight to a true outline (a city's seats, or a
district), starting from a linearised transform; audit_207_identity.py uses it
to register the map's drawing of a district to that district.
"""
import itertools
import numpy as np
from scipy import ndimage, optimize

GREY = np.array([195, 195, 195])


def land_components(a):
    """Connected drawn areas: the main map, the city boxes, legend swatches."""
    lum = a.sum(2)
    m = ndimage.binary_fill_holes(ndimage.binary_closing(lum >= 200, np.ones((9, 9))))
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    comps = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sizes[i - 1] < 3000:
            continue
        comps.append({'cid': i, 'px': int(sizes[i - 1]), 'slice': sl,
                      'bbox': (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)})
    comps.sort(key=lambda c: -c['px'])
    return lab, comps


def placeholders(a, lab, main_cid, min_px=100):
    """Flat light-grey patches on the main map: one per city box."""
    m = (np.abs(a - GREY).sum(2) <= 6) & (lab == main_cid)
    pl, n = ndimage.label(m)
    out = []
    for i, sl in enumerate(ndimage.find_objects(pl), start=1):
        px = int((pl[sl] == i).sum())
        if px < min_px:
            continue
        out.append({'pid': i, 'px': px, 'mask': pl == i,
                    'bbox': (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)})
    return out


# ---- transform models: inset px -> main px ---------------------------------
def unpack(p, model, c):
    """Return 2x3 matrix M with main = M @ [x - cx, y - cy, 1]."""
    if model == 'st':                      # log-scale, tx, ty
        s = np.exp(p[0])
        return np.array([[s, 0, p[1]], [0, s, p[2]]])
    if model == 'sim':                     # + rotation
        s, th = np.exp(p[0]), p[3]
        return np.array([[s * np.cos(th), -s * np.sin(th), p[1]],
                         [s * np.sin(th), s * np.cos(th), p[2]]])
    if model == 'affine':                  # log sx, tx, ty, rot, log aspect, shear
        s, th, asp, sh = np.exp(p[0]), p[3], np.exp(p[4]), p[5]
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        A = R @ np.array([[s * asp, sh * s], [0, s / asp]])
        return np.array([[A[0, 0], A[0, 1], p[1]], [A[1, 0], A[1, 1], p[2]]])
    raise ValueError(model)


def apply(M, c, pts):
    pts = np.asarray(pts, float)
    d = pts - c
    return np.column_stack([M[0, 0] * d[:, 0] + M[0, 1] * d[:, 1] + M[0, 2],
                            M[1, 0] * d[:, 0] + M[1, 1] * d[:, 1] + M[1, 2]])


NPAR = {'st': 3, 'sim': 4, 'affine': 6}


def soft_iou(src, pts, M, c, target):
    """src: inset land (0/1) at sample points `pts` (inset px). target is
    sampled bilinearly at the forward-mapped points."""
    q = apply(M, c, pts)
    t = ndimage.map_coordinates(target, [q[:, 1], q[:, 0]], order=1, mode='constant')
    inter = np.minimum(src, t).sum()
    union = np.maximum(src, t).sum()
    return inter / union if union else 0.0


def fit_inset(inset_mask, bbox, target, model='st', step=2, p0=None):
    """Fit inset -> main px. inset_mask: full-image bool of the inset's land.
    bbox: inset rectangle (x0,y0,x1,y1); only pixels inside it are compared,
    which is what makes a frame-clipped inset fit correctly. target: float
    main-map mask (1 = placeholder area)."""
    x0, y0, x1, y1 = bbox
    xs, ys = np.meshgrid(np.arange(x0, x1, step) + 0.5 * step,
                         np.arange(y0, y1, step) + 0.5 * step)
    pts = np.column_stack([xs.ravel(), ys.ravel()])
    src = inset_mask[pts[:, 1].astype(int), pts[:, 0].astype(int)].astype(float)
    c = np.array([(x0 + x1) / 2.0, (y0 + y1) / 2.0])
    if p0 is None:
        # moment start: match areas and centroids
        ty, tx = ndimage.center_of_mass(target)
        yy, xx = np.nonzero(inset_mask[y0:y1, x0:x1])
        s = np.sqrt(target.sum() / max(1, len(xx)))
        mc = np.array([xx.mean() + x0, yy.mean() + y0]) - c
        p0 = np.array([np.log(s), tx - s * mc[0], ty - s * mc[1]])
    p0 = np.concatenate([p0, np.zeros(NPAR[model] - len(p0))])[:NPAR[model]]
    loss = lambda p: 1 - soft_iou(src, pts, unpack(p, model, c), c, target)
    best, bl = p0, loss(p0)
    # coarse grid over scale and shift first (the loss is flat far from home)
    if model == 'st':
        s0 = np.exp(p0[0])
        for ds in np.linspace(-0.5, 0.5, 21):
            for dx in np.linspace(-1, 1, 9) * s0 * (x1 - x0) * 0.15:
                for dy in np.linspace(-1, 1, 9) * s0 * (y1 - y0) * 0.15:
                    p = p0 + np.array([ds, dx, dy])
                    l = loss(p)
                    if l < bl:
                        best, bl = p, l
    steps = np.array([0.05, 1.0, 1.0, 0.02, 0.02, 0.02])[:NPAR[model]]
    for mult in (1.0, 0.3, 0.1):
        simplex = np.vstack([best] + [best + np.eye(len(best))[i] * steps[i] * mult
                                      for i in range(len(best))])
        r = optimize.minimize(loss, best, method='Nelder-Mead',
                              options={'maxiter': 3000, 'xatol': 1e-6, 'fatol': 1e-7,
                                       'initial_simplex': simplex})
        if r.fun < bl:
            best, bl = r.x, r.fun
    return {'model': model, 'p': best, 'M': unpack(best, model, c), 'c': c,
            'iou': 1 - bl, 'scale': float(np.exp(best[0]))}


def pair_insets(insets, phs, target_of):
    """Fit every inset against every placeholder (scale+shift, coarse), then
    choose the one-to-one pairing with the highest total IoU."""
    score = np.zeros((len(insets), len(phs)))
    fits = {}
    for i, ins in enumerate(insets):
        for j, ph in enumerate(phs):
            f = fit_inset(ins['mask'], ins['bbox'], target_of(ins, ph), 'st', step=4)
            if f['scale'] > 0.7:           # a box is always an enlargement, so
                f['iou'] = 0.0             # inset -> main must shrink
            score[i, j] = f['iou']
            fits[i, j] = f
    best, bs = None, -1
    k = min(len(insets), len(phs))
    for perm in itertools.permutations(range(len(phs)), k):
        s = sum(score[i, perm[i]] for i in range(k))
        if s > bs:
            best, bs = perm, s
    return {i: best[i] for i in range(k)}, score, fits


# ---- optional: fit an inset straight to a true outline -------------------------
def fit_inset_geo(inset_mask, bbox, geom, lin0, model='sim', ds=2):
    """Fit inset px -> lon/lat directly against a true outline `geom` (e.g. the
    2002-delimitation seats of that city), comparing only inside the inset's
    rectangle so frame clipping is ignored. `lin0` is a 2x3 start matrix
    (lon/lat = lin0 @ [x, y, 1]), normally the placeholder solution linearised
    at the box centre. Returns the 2x3 matrix and the IoU.

    Not independent of any check made against the same outline."""
    import georef_map as G
    x0, y0, x1, y1 = bbox
    m = inset_mask[y0:y1, x0:x1][::ds, ::ds]
    H, W = m.shape
    # parameterise about the box centre: lon/lat = c0 + R S (px - centre)
    cx, cy = (x1 - x0) / 2.0, (y1 - y0) / 2.0
    A0 = lin0[:, :2]
    c0 = lin0 @ np.array([x0 + cx, y0 + cy, 1.0])
    sx = np.hypot(*A0[:, 0])
    th0 = np.arctan2(A0[1, 0], A0[0, 0])
    flip = np.sign(np.linalg.det(A0))            # image y runs down
    sx0, sy0 = np.hypot(*A0[:, 0]), np.hypot(*A0[:, 1])

    def mat(p):
        if model == 'nup':
            # north up: lon and lat scales only, no rotation or shear
            A = np.array([[sx0 * np.exp(p[0]), 0], [0, -sy0 * np.exp(p[1])]])
            lon, lat = c0[0] + p[2], c0[1] + p[3]
            t_full = np.array([lon, lat]) - A @ np.array([x0 + cx, y0 + cy])
            return A, A * ds, t_full + A @ np.array([x0, y0]), t_full
        s, th, lon, lat = np.exp(p[0]) * sx, th0 + p[1], c0[0] + p[2], c0[1] + p[3]
        asp = np.exp(p[4]) if len(p) > 4 else 1.0
        sh = p[5] if len(p) > 5 else 0.0
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        A = R @ np.array([[s * asp, s * sh], [0, flip * s / asp]])
        # to the downsampled crop grid: px = x0 + ds*u
        Ad = A * ds
        t_full = np.array([lon, lat]) - A @ np.array([x0 + cx, y0 + cy])
        return A, Ad, t_full + A @ np.array([x0, y0]), t_full

    def loss(p):
        _, Ad, t, _ = mat(p)
        params = (Ad[0, 0], Ad[0, 1], t[0], Ad[1, 0], Ad[1, 1], t[1])
        r = G.rasterise(geom, params, (H, W))
        if r is None:
            return 1.0
        u = np.logical_or(r, m).sum()
        return 1 - np.logical_and(r, m).sum() / u if u else 1.0

    n = {'nup': 4, 'sim': 4, 'affine': 6}[model]
    best = np.zeros(n)
    bl = start_iou = loss(best)
    # multi-start: the loss has false minima when the start is 20 km out
    for ls in (0.0, 0.15, 0.3):
        for dx in (-0.2, -0.1, 0.0, 0.1, 0.2):
            for dy in (-0.2, -0.1, 0.0, 0.1, 0.2):
                p = np.zeros(n)
                p[0] = ls
                if model == 'nup':
                    p[1] = ls
                p[2], p[3] = dx, dy
                l = loss(p)
                if l < bl:
                    best, bl = p, l
    steps = np.array([0.05, 0.03, 0.02, 0.02, 0.03, 0.03])[:n]
    for mult in (1.0, 0.3, 0.1):
        simplex = np.vstack([best] + [best + np.eye(n)[i] * steps[i] * mult for i in range(n)])
        r = optimize.minimize(loss, best, method='Nelder-Mead',
                              options={'maxiter': 2000, 'xatol': 1e-6, 'fatol': 1e-6,
                                       'initial_simplex': simplex})
        if r.fun < bl:
            best, bl = r.x, r.fun
    A, _, _, t = mat(best)
    return np.column_stack([A, t]), 1 - bl, best, 1 - start_iou


def linearise(warp, bbox):
    """2x3 lon/lat = L @ [x, y, 1] matching `warp` at the box centre."""
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h = 10.0
    P = np.array([[cx, cy], [cx + h, cy], [cx, cy + h]])
    q = warp(P)
    A = np.column_stack([(q[1] - q[0]) / h, (q[2] - q[0]) / h])
    return np.column_stack([A, q[0] - A @ np.array([cx, cy])])
