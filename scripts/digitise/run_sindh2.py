#!/usr/bin/env python3
"""Sindh v2: fixes over run_sindh.py:
- content-blob union for outline fit on sheets with weak/absent fills (use_blob)
- relaxed saturation gates for pale fills
- distance-cutoff NN label transfer so a 'white' remainder seat gets the
  unclaimed area instead of slivers (root cause of the silent East Karachi bug)
- colour labels are authoritative; plotree-centroid Hungarian is QA-only
- per-district debug PNGs in debug/
"""
import json, csv, sys, os
BASE = '/root/aiwan'
sys.path.insert(0, f'{BASE}/scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping, Point, GeometryCollection, Polygon
from shapely.ops import unary_union, voronoi_diagram
from shapely import make_valid
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from split_district_by_sheet import hue_range, load_small, fit_outline
from run_sindh import build_districts, SINGLE

SD = f'{BASE}/sheets'
os.makedirs(f'{BASE}/debug', exist_ok=True)

# sheet, key, [(na, colour)], use_blob
JOBS = [
 ('dis22.jpg', 'Shikarpur',           [('NA-198','light blue'), ('NA-199','cream')], True),
 ('dis7.jpg',  'Kamber Shahdadkot',   [('NA-202','pale yellow'), ('NA-203','light blue')], False),
 ('dis3.jpg',  'Ghotki',              [('NA-204','pale yellow'), ('NA-205','lavender')], True),
 ('dis24.jpg', 'Sukkur',              [('NA-206','cream'), ('NA-207','pale blue')], True),
 ('dis14.jpg', 'Khairpur',            [('NA-208','blue'), ('NA-209','tan'), ('NA-210','green')], False),
 ('dis19.jpg', 'Naushahro Feroze',    [('NA-211','yellow'), ('NA-212','pale blue')], True),
 ('dis21.jpg', 'Shaheed Benazirabad', [('NA-213','yellow'), ('NA-214','pink')], False),
 ('dis20.jpg', 'Sanghar',             [('NA-215','yellow'), ('NA-216','light green'), ('NA-217','royal blue')], True),
 ('dis18.jpg', 'Mirpurkhas',          [('NA-218','green'), ('NA-219','cream')], True),
 ('dis27.jpg', 'Tharparkar',          [('NA-221','light blue'), ('NA-222','cream')], True),
 ('dis4.jpg',  'Hyderabad',           [('NA-225','light blue'), ('NA-226','green'), ('NA-227','pale yellow')], False),
 ('dis1.jpg',  'Badin',               [('NA-229','salmon-pink'), ('NA-230','green')], False),
 ('dis2.jpg',  'Dadu',                [('NA-234','yellow'), ('NA-235','white')], True),
 ('dis10.jpg', 'Malir Karachi',       [('NA-236','light blue'), ('NA-237','light green'), ('NA-238','pink')], False),
 ('dis15.jpg', 'Korangi Karachi',     [('NA-239','yellow'), ('NA-240','light green'), ('NA-241','light blue')], False),
 ('dis9.jpg',  'East Karachi',        [('NA-242','white'), ('NA-243','green'), ('NA-244','magenta'), ('NA-245','yellow')], True),
 ('dis11.jpg', 'South Karachi',       [('NA-246','pink'), ('NA-247','light blue')], False),
 ('dis12.jpg', 'West Karachi',        [('NA-248','pink'), ('NA-249','teal'), ('NA-250','brown'), ('NA-251','chartreuse'), ('NA-252','tan')], True),
 ('dis8.jpg',  'Central Karachi',     [('NA-253','light blue'), ('NA-254','salmon-pink'), ('NA-255','green'), ('NA-256','yellow')], False),
]


def seat_masks2(img, legend, frame_frac=0.03):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    H, W = h.shape
    base = (s > 18) & (v > 110)
    frame = np.zeros_like(h, np.uint8)
    frame[int(frame_frac * H):int((1 - frame_frac) * H), int(frame_frac * W):int((1 - frame_frac) * W)] = 1
    SPECIAL = {'royal blue': lambda: ((h >= 100) & (h <= 130) & (s > 45) & (v > 90)),
               'pale blue': lambda: ((h >= 85) & (h <= 125) & (s > 10) & (v > 140))}
    masks = {}
    for e in legend:
        if e['colour'].lower() in SPECIAL:
            m = SPECIAL[e['colour'].lower()]()
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
            continue
        if 'brown' in e['colour'].lower():
            # dark red/brown fills fail the generic value gate
            m = (((h <= 12) | (h >= 175)) & (s > 55) & (v > 55) & (v < 165))
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
            continue
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
    keys = [k for k in masks if masks[k] is not None]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ov = masks[keys[i]] & masks[keys[j]]
            if ov.sum():
                masks[keys[i]] &= ~ov
                masks[keys[j]] &= ~ov
    # drop callout chips: small solid rectangles sitting in whitespace (real
    # fills, however small, are surrounded by dense map linework)
    nonwhite = (((s > 28) | (v < 150)) & (frame > 0)).astype(np.uint8)
    chips = np.zeros((H, W), np.uint8)
    for k in keys:
        n, lab, stats, cent = cv2.connectedComponentsWithStats(masks[k], 8)
        for i in range(1, n):
            x, y, w2, h2, a = stats[i]
            if w2 > 0.22 * W or h2 > 0.12 * H:
                continue
            extent = a / max(w2 * h2, 1)
            if extent < 0.45:
                continue
            comp = (lab == i).astype(np.uint8)
            cs2, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            filled = np.zeros_like(comp)
            cv2.drawContours(filled, cs2, -1, 1, -1)   # text holes inside the
            ring = cv2.dilate(filled, np.ones((25, 25), np.uint8)) & ~filled  # chip must not count
            dens = nonwhite[ring > 0].mean() if ring.sum() else 1.0
            fext = filled[y:y + h2, x:x + w2].sum() / max(w2 * h2, 1)  # rectangularity
            cx, cy = cent[i]
            near_margin = (cx < 0.20 * W or cx > 0.80 * W or cy < 0.12 * H or cy > 0.90 * H)
            if dens < 0.18 or fext > 0.85 or (fext > 0.55 and near_margin):
                masks[k][lab == i] = 0
                chips[lab == i] = 1
    return masks, chips


def content_blob(img, colour_union, chips=None, frame_frac=0.04):
    """Solid district blob from all non-white content (lines, text, fills).
    Component chosen = the one overlapping the colour-mask union most (the
    district linework often touches the frame via roads, so frame-touching
    cannot be the drop criterion)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    H, W = s.shape
    nonwhite = ((s > 28) | (v < 150)).astype(np.uint8)
    if chips is not None:
        nonwhite &= ~cv2.dilate(chips, np.ones((13, 13), np.uint8))
    ff = max(3, int(frame_frac * min(H, W)))
    nonwhite[:ff, :] = 0; nonwhite[-ff:, :] = 0; nonwhite[:, :ff] = 0; nonwhite[:, -ff:] = 0
    m = cv2.morphologyEx(nonwhite, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    best, bscore = None, -1
    for i in range(1, n):
        if stats[i][4] < 0.01 * H * W:
            continue
        score = int(((lab == i) & (colour_union > 0)).sum())
        if score > bscore:
            best, bscore = i, score
    if best is None or bscore <= 0:
        return None
    blob = (lab == best).astype(np.uint8)
    blob = cv2.morphologyEx(blob, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    cs, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(blob)
    cv2.drawContours(filled, cs, -1, 1, -1)
    return filled


def fit_outline_all(union_mask, district_geom, n_icp=40):
    """Like split_district_by_sheet.fit_outline but returns ALL four rotation
    candidates [(rms, px_to_metric)] sorted by rms. Boundary rms alone cannot
    distinguish a 180-degree flip of an elongated district from the correct
    orientation, so the caller disambiguates with seat centroids."""
    from scipy.interpolate import RBFInterpolator
    lat0 = district_geom.centroid.y
    KX, KY = 111.32 * np.cos(np.radians(lat0)), 110.57
    b = district_geom.boundary
    segs = [b] if b.geom_type == 'LineString' else list(b.geoms)
    Dpts = np.array([(x * KX, y * KY) for g in segs for x, y in zip(*g.xy)])
    tree = cKDTree(Dpts)
    cnts, _ = cv2.findContours((union_mask * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    P0 = cnts[0].reshape(-1, 2).astype(float)
    P0 = P0[::max(1, len(P0) // 2500)].copy()
    P0[:, 1] = -P0[:, 1]
    areaP = cv2.contourArea(cnts[0])
    s0 = np.sqrt(district_geom.area * KX * KY / areaP)
    out = []
    for rotd in (0, 90, 180, 270):
        th0 = np.radians(rotd)
        A = s0 * np.array([[np.cos(th0), -np.sin(th0)], [np.sin(th0), np.cos(th0)]])
        bvec = Dpts.mean(0) - A @ P0.mean(0)
        X = P0 @ A.T + bvec
        for _ in range(n_icp):
            d, idx = tree.query(X)
            Y = Dpts[idx]
            mx, my = X.mean(0), Y.mean(0)
            Xc, Yc = X - mx, Y - my
            C = Yc.T @ Xc / len(X)
            U, sv, Vt = np.linalg.svd(C)
            S = np.eye(2)
            if np.linalg.det(U @ Vt) < 0:
                S[1, 1] = -1
            Rm = U @ S @ Vt
            sc = np.trace(np.diag(sv) @ S) / (Xc ** 2).sum() * len(X)
            A = sc * Rm @ A
            bvec = my + sc * Rm @ (bvec - mx)
            X = P0 @ A.T + bvec
        d, _ = tree.query(X)
        rms = float(np.sqrt((d ** 2).mean()))
        X = P0 @ A.T + bvec
        d, idx = tree.query(X)
        keep = d < np.percentile(d, 90)
        src = X[keep][::6]
        dst = Dpts[idx][keep][::6]
        tps = RBFInterpolator(src, dst - src, kernel='thin_plate_spline', smoothing=1.0)

        def make_p2m(A=A, bvec=bvec, tps=tps):
            def p2m(P):
                Q = P.astype(float).copy()
                Q[:, 1] = -Q[:, 1]
                X2 = Q @ A.T + bvec
                return X2 + tps(X2)
            return p2m
        out.append((rms, make_p2m()))
    out.sort(key=lambda t: t[0])
    return out, (KX, KY)


def split2(img_path, legend, geom, use_blob, clip_geom=None, cents=None):
    """geom: the polygon the SHEET depicts (fit + label-transfer domain).
    clip_geom: optional final output domain (e.g. the gbOpen-blob carve of a
    Karachi district when the COD polygon extends beyond the blob).
    cents: plotree seat centroids {na: (lon, lat)} for rotation disambiguation."""
    img = load_small(img_path)
    masks, chips = seat_masks2(img, legend)
    good = {k: m for k, m in masks.items() if m is not None and m.sum() > 1200}
    weak = [k for k in masks if k not in good]
    if len(weak) > 1:
        raise RuntimeError(f'>1 weak seat: {weak}')
    cunion = np.zeros_like(next(iter(good.values())))
    for m in good.values():
        cunion |= m
    cunion = cv2.morphologyEx((cunion * 255).astype(np.uint8), cv2.MORPH_CLOSE,
                              np.ones((25, 25), np.uint8)) // 255
    # When a weak seat exists the colour union is incomplete, so the outline fit
    # MUST come from the content blob (a low colour-union rms is meaningless:
    # ICP+TPS will happily squeeze a partial union onto the full district).
    blob = content_blob(img, cunion, chips)
    if blob is not None:
        # clip fills (and the fit union) to the map body: kills stray swatches,
        # table patches and legend fragments outside the district drawing
        bl = cv2.dilate(blob, np.ones((9, 9), np.uint8))
        for k in list(good):
            good[k] = good[k] & bl
            if good[k].sum() <= 1200:
                del good[k]
        weak = [k for k in masks if k not in good]
        if len(weak) > 1:
            raise RuntimeError(f'>1 weak seat after blob clip: {weak}')
        cunion = np.zeros_like(next(iter(good.values())))
        for m in good.values():
            cunion |= m
        cunion = cv2.morphologyEx((cunion * 255).astype(np.uint8), cv2.MORPH_CLOSE,
                                  np.ones((25, 25), np.uint8)) // 255
        cunion &= bl
    if weak:
        if blob is None:
            raise RuntimeError('weak seat but content blob failed')
        cands = [('content-blob', blob)]
    elif use_blob and blob is not None:
        # a colour union covering well under the full drawing is not a valid
        # fit shape (rms comparison is meaningless for partial unions)
        if cunion.sum() < 0.65 * blob.sum():
            cands = [('content-blob', blob)]
        else:
            cands = [('colour-union', cunion), ('content-blob', blob)]
    else:
        cands = [('colour-union', cunion)]
    # centroid cost of a candidate transform: mean distance between mapped
    # good-mask centroids and their plotree seat centroids (sheet labels)
    def cent_cost(p2m, KX, KY):
        if not cents:
            return 0.0
        ds = []
        for na, m in good.items():
            if na not in cents:
                continue
            ys, xs = np.nonzero(m)
            c = p2m(np.array([[xs.mean(), ys.mean()]]))[0]
            t = np.array([cents[na][0] * KX, cents[na][1] * KY])
            ds.append(np.linalg.norm(c - t))
        return float(np.mean(ds)) if ds else 0.0

    # Boundary rms picks the fit; centroid cost ONLY breaks true rotation
    # ambiguity (near-identical rms, e.g. 180-flip of an elongated district).
    # A generous window here lets noisy plotree centroids override orientations
    # already verified against the sheets — keep it tight.
    best = None
    for tagf, u in cands:
        try:
            rots, (KX, KY) = fit_outline_all(u, geom)
        except Exception:
            continue
        best_rms = rots[0][0]
        viable = [r for r in rots if r[0] <= best_rms * 1.25 + 0.5]
        if len(viable) > 1:
            chosen = min(viable, key=lambda r: cent_cost(r[1], KX, KY))
        else:
            chosen = viable[0]
        rms_c, p2m = chosen
        if best is None or rms_c < best[2][2]:
            best = (None, (tagf, u), (p2m, (KX, KY), rms_c))
    if best is None:
        raise RuntimeError('no usable fit')
    _, (fit_tag, union), (px_to_metric, (KX, KY), rms) = best
    pts, labs = [], []
    names = sorted(good)
    for i, na in enumerate(names):
        ys, xs = np.nonzero(good[na])
        step = max(1, len(xs) // 20000)
        pts.append(np.stack([xs[::step], ys[::step]], 1))
        labs.append(np.full(len(xs[::step]), i))
    P = np.concatenate(pts); L = np.concatenate(labs)
    M = px_to_metric(P)
    # drop labelled pixels that land outside the district (callout chips,
    # legend swatches, key-map insets all map outside the fitted outline)
    from shapely import contains_xy
    inside = contains_xy(geom.buffer(0.02), M[:, 0] / KX, M[:, 1] / KY)
    if inside.sum() < 500:
        raise RuntimeError('fit maps almost all labelled pixels outside district')
    M, L = M[inside], L[inside]
    # a seat whose labels all fell outside is effectively weak/absent: demote
    for i, na in enumerate(list(names)):
        if (L == i).sum() == 0 and na not in weak:
            if weak:
                raise RuntimeError(f'{na}: all labels outside and weak slot taken by {weak[0]}')
            weak = [na]
            keep = L != i
            M, L = M[keep], L[keep]
            L = np.where(L > i, L - 1, L)
            names = [n2 for n2 in names if n2 != na]
            del good[na]
    tree = cKDTree(M)
    out_geom = clip_geom if clip_geom is not None else geom
    dom = make_valid(unary_union([geom, out_geom]))
    minx, miny, maxx, maxy = dom.bounds
    gn = 520
    gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
    XX, YY = np.meshgrid(gx, gy)
    d, gi = tree.query(np.stack([XX.ravel() * KX, YY.ravel() * KY], 1))
    classes = L[gi].reshape(gn, gn)
    if weak:
        # sampling spacing estimate: labelled points per km2
        area_km2 = abs(geom.area) * KX * KY
        spacing = np.sqrt(max(area_km2, 1.0) / max(len(M), 1))
        cutoff = max(2.0, 3.0 * spacing)
        # the weak seat only absorbs unclaimed cells INSIDE the sheet's own
        # polygon; outside it (carve extension) plain NN extension applies
        in_geom = contains_xy(geom.buffer(0.01), XX.ravel(), YY.ravel()).reshape(gn, gn)
        unclaimed = (d.reshape(gn, gn) > cutoff) & in_geom
        classes = classes.copy()
        classes[unclaimed] = len(names)  # weak class id
        names = names + [weak[0]]
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    feats = {}
    for k, na in enumerate(names):
        cm = (classes == k).astype(np.uint8)
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = []
        for c in cs:
            if len(c) < 4 or cv2.contourArea(c) < 9:
                continue
            q = c.reshape(-1, 2).astype(float)
            polys.append(make_valid(Polygon(zip(minx + q[:, 0] * dx, miny + q[:, 1] * dy)).buffer(max(dx, dy) * 0.6)))
        if polys:
            g = make_valid(unary_union(polys).intersection(out_geom))
            if not g.is_empty:
                feats[na] = g
    if weak:
        # the weak seat may only absorb unclaimed area INSIDE the sheet's own
        # domain; carve area beyond the COD polygon goes to nearest-seat top-up
        wdom = make_valid(out_geom.intersection(geom)) if clip_geom is not None else geom
        strong = make_valid(unary_union([g for n2, g in feats.items() if n2 != weak[0]]))
        w = feats.get(weak[0])
        w = unary_union([w, wdom.difference(strong)]) if w is not None else wdom.difference(strong)
        feats[weak[0]] = make_valid(make_valid(w).difference(strong))
    # coverage top-up: any part of the output domain not claimed goes to the
    # nearest seat (needed when clip_geom extends past the label-transfer grid)
    rem = make_valid(out_geom.difference(unary_union(list(feats.values()))))
    if not rem.is_empty and rem.area > 1e-6:
        geoms = list(rem.geoms) if rem.geom_type in ('MultiPolygon', 'GeometryCollection') else [rem]
        for gpart in geoms:
            if gpart.geom_type != 'Polygon' or gpart.area == 0:
                continue
            near = min(feats, key=lambda n2: feats[n2].distance(gpart))
            feats[near] = make_valid(unary_union([feats[near], gpart]))
    return feats, rms, img, masks, union, (KX, KY), fit_tag


def debug_png(key, img, masks, union, feats, geom, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 6))
    ax[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); ax[0].set_title(key); ax[0].axis('off')
    over = np.zeros(img.shape[:2] + (3,), np.uint8)
    cols = [(255, 60, 60), (60, 200, 60), (80, 80, 255), (230, 200, 40), (200, 60, 200), (40, 200, 200)]
    for i, (na, m) in enumerate(sorted((k, v) for k, v in masks.items() if v is not None)):
        over[m > 0] = cols[i % 6]
    cs, _ = cv2.findContours((union * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(over, cs, -1, (255, 255, 255), 3)
    ax[1].imshow(over); ax[1].set_title('masks + fit union'); ax[1].axis('off')
    for i, (na, g) in enumerate(sorted(feats.items())):
        gs = [g] if g.geom_type == 'Polygon' else list(g.geoms)
        for p in gs:
            if p.geom_type != 'Polygon' or p.is_empty:
                continue
            x, y = p.exterior.xy
            ax[2].fill(x, y, alpha=0.55, color=np.array(cols[i % 6]) / 255)
        c = g.centroid
        ax[2].annotate(na.replace('NA-', ''), (c.x, c.y), fontsize=8, ha='center')
    bx = geom.boundary
    for seg in ([bx] if bx.geom_type == 'LineString' else list(bx.geoms)):
        x, y = seg.xy
        ax[2].plot(x, y, 'k-', lw=0.8)
    ax[2].set_aspect(1 / np.cos(np.radians(geom.centroid.y)) if False else 'equal')
    ax[2].set_title('output vs district'); ax[2].axis('off')
    plt.tight_layout(); plt.savefig(path, dpi=90); plt.close()


def main():
    D = build_districts()
    cod = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
           for f in json.load(open(f'{BASE}/data/cod_PAK_ADM2.geojson'))['features']}
    cents = {r['seat']: (float(r['X']), float(r['Y']))
             for r in csv.DictReader(open(f'{BASE}/plotree_elections/essentials/NA_2018_centroids.csv'))}
    results, report = {}, []

    for na, key in SINGLE:
        tag = 'district-exact union (geoBoundaries ADM2)'
        if key == 'Sujawal':
            tag = 'district-exact (geoBoundaries ADM2; Sujawal carved via COD 2022)'
        if key == 'Thatta':
            tag = 'district-exact (geoBoundaries ADM2 minus COD-carved Sujawal)'
        results[na] = (D[key], tag, False)

    for sheet, key, legend, use_blob in JOBS:
        seats = [na for na, _ in legend]
        try:
            leg = [{'na': na, 'colour': col} for na, col in legend]
            if key.endswith('Karachi'):
                # sheet depicts the full 2018-era district (COD, or GADM36 for
                # West/South where COD-2022 moved Keamari); output clipped to
                # the gbOpen-blob carve so provincial edges stay gbOpen-consistent
                fitg = D['_karachi_fit_targets'][key]
                feats, rms, img, masks, union, _, fit_tag = split2(
                    f'{SD}/{sheet}', leg, fitg, use_blob, clip_geom=D[key], cents=cents)
            else:
                feats, rms, img, masks, union, _, fit_tag = split2(f'{SD}/{sheet}', leg, D[key], use_blob, cents=cents)
            missing = [s for s in seats if s not in feats or feats[s].is_empty]
            if missing:
                raise RuntimeError(f'missing {missing}')
            areas = {s: feats[s].area / D[key].area for s in seats}
            lat0 = D[key].centroid.y
            KX, KY = 111.32 * np.cos(np.radians(lat0)), 110.57
            P = np.array([[feats[s].centroid.x * KX, feats[s].centroid.y * KY] for s in seats])
            T = np.array([[cents[s][0] * KX, cents[s][1] * KY] for s in seats])
            ri, ti = linear_sum_assignment(((P[:, None, :] - T[None, :, :]) ** 2).sum(-1))
            qa = 'plotree-QA ok' if all(seats[r] == seats[t] for r, t in zip(ri, ti)) else 'plotree-QA differs (sheet labels kept)'
            tag = f'sheet-split (colour-fill): Sindh/{sheet}, outline-fit rms {rms:.1f}km'
            if key.endswith('Karachi'):
                tag += '; district COD-carved from gbOpen Karachi'
            for s in seats:
                results[s] = (feats[s], tag, False)
            report.append((key, 'OK', f'rms {rms:.1f} ({fit_tag}) | {qa} | shares ' +
                           ' '.join(f'{s[-3:]}:{areas[s]:.2f}' for s in seats)))
            debug_png(key, img, masks, union, feats, D[key], f'{BASE}/debug/{key.replace(" ","_")}.png')
        except Exception as e:
            report.append((key, 'FAIL', str(e)[:90]))

    lark = D['Larkana']
    pts = [Point(*cents[s]) for s in ('NA-200', 'NA-201')]
    vor = voronoi_diagram(GeometryCollection(pts), envelope=lark.buffer(1.0))
    cells = list(vor.geoms)
    for s, pt in zip(('NA-200', 'NA-201'), pts):
        cell = next((c for c in cells if c.contains(pt)), None) or min(cells, key=lambda c: c.distance(pt))
        results[s] = (make_valid(cell.intersection(lark)),
                      'district-Voronoi (no ECP sheet for Larkana; plotree centroids) [approx]', True)

    n_fail = sum(1 for r in report if r[1] == 'FAIL')
    v2 = json.load(open(f'{BASE}/data/na_2018delim_v2.backup.geojson'))
    updated = 0
    for f in v2['features']:
        na = f['properties']['na']
        if na in results:
            g, src, approx = results[na]
            f['properties'] = {'na': na, 'dist': f['properties'].get('dist', ''),
                               'approx': bool(approx), 'src': src}
            f['geometry'] = mapping(make_valid(g).simplify(0.0015))
            updated += 1
    json.dump(v2, open(f'{BASE}/data/na_2018delim_v2.geojson', 'w'))

    print('=== report ===')
    for r in report:
        print(*r)
    print(f'updated {updated}/{len(results)} seats; {n_fail} district FAILs')


if __name__ == '__main__':
    main()
