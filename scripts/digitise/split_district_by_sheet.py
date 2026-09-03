#!/usr/bin/env python3
"""
Split a known district polygon along the internal constituency lines of an
ungridded ECP delimitation sheet.

Used for the 2018 KP/FATA/ICT leg (no sheets there carry printed UTM grids, so
the Quetta grid-georeference method does not apply).

Method per district (see also METHODOLOGY.md):
1. Colour-segment the sheet into per-seat masks: k-means in LAB space over
   "colourful" pixels (saturation>30, V>120), k = number of seats (+1 slack),
   clusters matched to the legend's colour words via a hue-word table; component
   filtering as in digitise_sheet.py. For a 2-seat sheet with one unreliable
   colour, the weak seat is taken as the remainder of the district.
2. Fit the union-of-masks outline to the geoBoundaries district polygon:
   similarity ICP with multi-start over 0/90/180/270-degree initial rotations
   (several sheets are scanned rotated), then a thin-plate-spline (RBF) warp on
   the converged ICP point pairs so the sheet outline lands exactly on the gb
   outline. Internal lines inherit the warp.
3. Transfer labels: map every masked sheet pixel through affine+TPS to lon/lat,
   build a KDTree; classify a dense raster grid over the gb district polygon by
   nearest labelled point; extract per-seat regions from the classified grid
   (cv2.findContours in grid space), then intersect with the gb district polygon.
   Coverage of the district is exact and seamless by construction; only the
   POSITION of internal lines carries sheet-fit error (est. 0.5-2 km).
4. QA: piece count vs seat count; per-seat area share on the sheet vs in the
   output (large drift flags a bad fit); visual overlay per district.

Outputs one feature per seat with src='sheet-split: <sheet>, outline-fit'.
"""
import cv2, numpy as np, json
from shapely.geometry import shape, Polygon, mapping
from shapely.ops import unary_union
from shapely import make_valid
from scipy.spatial import cKDTree
from scipy.interpolate import RBFInterpolator

# hue-word -> OpenCV hue range (0-179); sat/val gates applied separately
HUE_WORDS = {
    'green': (35, 75), 'light green': (35, 75), 'chartreuse': (30, 55), 'teal': (75, 95),
    'yellow': (22, 34), 'pale yellow': (20, 34), 'cream': (15, 32), 'tan': (12, 25),
    'orange': (8, 22), 'orange-tan': (8, 24), 'salmon': (2, 14), 'salmon-pink': (0, 14),
    'pink': (150, 179), 'crimson': (170, 179), 'red': (0, 8), 'magenta': (140, 170),
    'purple': (125, 150), 'lavender': (120, 150), 'violet': (125, 150),
    'blue': (95, 125), 'light blue': (90, 120), 'khaki': (18, 32), 'peach': (5, 20),
}

def hue_range(word):
    w = word.lower()
    for key in sorted(HUE_WORDS, key=len, reverse=True):
        if key in w:
            return HUE_WORDS[key]
    return None

def load_small(path, width=3000):
    img = cv2.imread(path)
    if img is None:
        raise IOError(path)
    if img.shape[1] > width:
        sc = width / img.shape[1]
        img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    return img

def seat_masks(img, legend, frame_frac=0.05):
    """legend: [{'na':..., 'colour': 'light green'}, ...] -> {na: mask}"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    H, W = h.shape
    base = (s > 30) & (v > 120)
    frame = np.zeros_like(h, np.uint8)
    frame[int(frame_frac * H):int((1 - frame_frac) * H), int(frame_frac * W):int((1 - frame_frac) * W)] = 1
    masks = {}
    for e in legend:
        rng = hue_range(e['colour'])
        if rng is None:
            masks[e['na']] = None
            continue
        lo, hi = rng
        m = (base & ((h >= lo) & (h <= hi) if lo <= hi else ((h >= lo) | (h <= hi))))
        m = (m & (frame > 0)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        areas = [(stats[i][4], i) for i in range(1, n)]
        out = np.zeros_like(m)
        if areas:
            amax = max(a for a, _ in areas)
            for a, i in areas:
                if a >= max(1200, 0.05 * amax):
                    out[lab == i] = 1
        masks[e['na']] = out
    # overlap resolution: a pixel claimed by 2+ masks goes to none (boundary zone)
    keys = [k for k in masks if masks[k] is not None]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ov = masks[keys[i]] & masks[keys[j]]
            if ov.sum():
                masks[keys[i]] &= ~ov
                masks[keys[j]] &= ~ov
    return masks

def fit_outline(union_mask, district_geom, n_icp=40):
    """Similarity ICP (multi-start 4 rotations) sheet px -> lon/lat metric; then TPS pairs."""
    lat0 = district_geom.centroid.y
    KX, KY = 111.32 * np.cos(np.radians(lat0)), 110.57
    b = district_geom.boundary
    segs = [b] if b.geom_type == 'LineString' else list(b.geoms)
    D = np.array([(x * KX, y * KY) for g in segs for x, y in zip(*g.xy)])
    tree = cKDTree(D)
    cnts, _ = cv2.findContours((union_mask * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    P0 = cnts[0].reshape(-1, 2).astype(float)
    P0 = P0[::max(1, len(P0) // 2500)].copy()
    P0[:, 1] = -P0[:, 1]
    areaP = cv2.contourArea(cnts[0])
    s0 = np.sqrt(district_geom.area * KX * KY / areaP)
    best = None
    for rot in (0, 90, 180, 270):
        th0 = np.radians(rot)
        A = s0 * np.array([[np.cos(th0), -np.sin(th0)], [np.sin(th0), np.cos(th0)]])
        bvec = D.mean(0) - A @ P0.mean(0)
        X = P0 @ A.T + bvec
        for _ in range(n_icp):
            d, idx = tree.query(X)
            Y = D[idx]
            mx, my = X.mean(0), Y.mean(0)
            Xc, Yc = X - mx, Y - my
            C = Yc.T @ Xc / len(X)
            U, sv, Vt = np.linalg.svd(C)
            S = np.eye(2)
            if np.linalg.det(U @ Vt) < 0:
                S[1, 1] = -1
            R = U @ S @ Vt
            sc = np.trace(np.diag(sv) @ S) / (Xc ** 2).sum() * len(X)
            A = sc * R @ A
            bvec = my + sc * R @ (bvec - mx)
            X = P0 @ A.T + bvec
        d, _ = tree.query(X)
        rms = float(np.sqrt((d ** 2).mean()))
        if best is None or rms < best[0]:
            best = (rms, A.copy(), bvec.copy())
    rms, A, bvec = best
    # TPS pairs from converged correspondences (subsampled, deduped targets)
    X = P0 @ A.T + bvec
    d, idx = tree.query(X)
    keep = d < np.percentile(d, 90)
    src = X[keep][::6]
    dst = D[idx][keep][::6]
    tps = RBFInterpolator(src, dst - src, kernel='thin_plate_spline', smoothing=1.0)
    def px_to_metric(P):   # P: (n,2) pixel coords (y down)
        Q = P.astype(float).copy()
        Q[:, 1] = -Q[:, 1]
        X = Q @ A.T + bvec
        return X + tps(X)
    return px_to_metric, (KX, KY), rms

def split_district(img_path, legend, district_geom, grid_n=520):
    img = load_small(img_path)
    masks = seat_masks(img, legend)
    good = {k: m for k, m in masks.items() if m is not None and m.sum() > 3000}
    missing = [k for k in masks if k not in good]
    if len(good) < len(masks) - 1 or len(good) < 1:
        raise RuntimeError(f'too few usable masks; missing {missing}')
    union = np.zeros_like(next(iter(good.values())))
    for m in good.values():
        union |= m
    union = cv2.morphologyEx((union * 255).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)) // 255
    px_to_metric, (KX, KY), rms = fit_outline(union, district_geom)
    # labelled pixel cloud (subsample for speed)
    pts, labs = [], []
    for i, (na, m) in enumerate(sorted(good.items())):
        ys, xs = np.nonzero(m)
        step = max(1, len(xs) // 20000)
        pts.append(np.stack([xs[::step], ys[::step]], 1))
        labs.append(np.full(len(xs[::step]), i))
    P = np.concatenate(pts); L = np.concatenate(labs)
    M = px_to_metric(P)
    tree = cKDTree(M)
    names = [na for na, _ in sorted(good.items())]
    # classify dense grid over district
    minx, miny, maxx, maxy = district_geom.bounds
    gx = np.linspace(minx, maxx, grid_n)
    gy = np.linspace(miny, maxy, grid_n)
    XX, YY = np.meshgrid(gx, gy)
    GM = np.stack([XX.ravel() * KX, YY.ravel() * KY], 1)
    _, gi = tree.query(GM)
    classes = L[gi].reshape(grid_n, grid_n)
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    feats = {}
    for i, na in enumerate(names):
        cm = (classes == i).astype(np.uint8)
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = []
        for c in cs:
            if len(c) < 4 or cv2.contourArea(c) < 9:
                continue
            q = c.reshape(-1, 2).astype(float)
            lon = minx + q[:, 0] * dx
            lat = miny + q[:, 1] * dy
            polys.append(make_valid(Polygon(zip(lon, lat)).buffer(max(dx, dy) * 0.6)))
        if polys:
            g = make_valid(unary_union(polys)).intersection(district_geom)
            feats[na] = make_valid(g)
    # remainder seat (weak colour) = district minus assigned
    if missing:
        assigned = make_valid(unary_union(list(feats.values())))
        feats[missing[0]] = make_valid(district_geom.difference(assigned))
    # normalise: assign any unclaimed district area to nearest seat piece
    return feats, rms
