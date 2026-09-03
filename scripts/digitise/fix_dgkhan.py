#!/usr/bin/env python3
"""DG Khan (NA-189..192) re-split. The dis2.jpg sheet is drawn ~45deg off
north and the district is elongated and near-symmetric about its long axis, so
boundary-only ICP multi-start converges to displaced/flipped fits regardless of
start rotation. Fix: the four region masks' identities are known from the
sheet's NA labels (verified visually: NE=189, centre=190, west=191, south=192),
so an affine is solved directly from the 4 mask-centroid <-> plotree-centroid
pairs, then refined by boundary ICP (similarity update, initialised from the
affine) + TPS, then the usual label transfer over gb 'Dera Ghazi Khan'."""
import json, csv, sys
BASE = '/root/aiwan'
sys.path.insert(0, f'{BASE}/scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union
from shapely import make_valid
from scipy.spatial import cKDTree
from scipy.interpolate import RBFInterpolator
import run_punjab_fix as R

SEATS = ['NA-189', 'NA-190', 'NA-191', 'NA-192']


def main():
    gb, cents = R.load_geo()
    gbd = gb['Dera Ghazi Khan']
    img = cv2.imread(f'{BASE}/psheets/dis2.jpg')
    opts = {'strict_red': True, 'min_ratio': 0.03}
    masks, _, dil = R.region_masks(img, 4, opts)
    masks = masks[:4]
    # identify masks by which red NA-label text they contain is already known
    # (visual verification): order masks by px position NE->centre->west->south
    mc_px = np.array([[np.nonzero(m)[1].mean(), np.nonzero(m)[0].mean()] for m in masks])
    order = [int(np.argmax(mc_px[:, 0] - mc_px[:, 1])),   # NE: max(x - y) -> 189
             None, None,
             int(np.argmax(mc_px[:, 1] - 0.3 * mc_px[:, 0]))]  # S: max y -> 192
    rest = [i for i in range(4) if i not in (order[0], order[3])]
    # of the remaining two, 190 is the more central/east one (larger x)
    order[1], order[2] = (rest[0], rest[1]) if mc_px[rest[0], 0] > mc_px[rest[1], 0] else (rest[1], rest[0])
    assert len(set(order)) == 4
    lat0 = gbd.centroid.y
    KX, KY = 111.32 * np.cos(np.radians(lat0)), 110.57
    src = mc_px[order].astype(float).copy()
    src[:, 1] = -src[:, 1]
    dst = np.array([[cents[s][0] * KX, cents[s][1] * KY] for s in SEATS])
    # similarity Procrustes on the 4 anchor pairs ONLY (boundary ICP drifts:
    # the drawn shape is schematic and near-symmetric about its long axis)
    ms, md = src.mean(0), dst.mean(0)
    Sc, Dc = src - ms, dst - md
    C = Dc.T @ Sc / len(src)
    U, sv, Vt = np.linalg.svd(C)
    Ssg = np.eye(2)
    if np.linalg.det(U @ Vt) < 0:
        Ssg[1, 1] = -1
    Rm = U @ Ssg @ Vt
    sc = np.trace(np.diag(sv) @ Ssg) / (Sc ** 2).sum() * len(src)
    A = sc * Rm
    bvec = md - A @ ms
    # single trimmed boundary correspondence pass + gentle TPS so the outline
    # lands on the gb district without unpinning the anchors
    b = gbd.boundary
    segs = [b] if b.geom_type == 'LineString' else list(b.geoms)
    D = np.array([(x * KX, y * KY) for g in segs for x, y in zip(*g.xy)])
    tree = cKDTree(D)
    union = R.content_body(img)
    cnts, _ = cv2.findContours((union * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    P0 = sorted(cnts, key=cv2.contourArea, reverse=True)[0].reshape(-1, 2).astype(float)
    P0 = P0[::max(1, len(P0) // 2500)].copy(); P0[:, 1] = -P0[:, 1]
    X2 = P0 @ A.T + bvec
    d, idx = tree.query(X2)
    rms = float(np.sqrt((d ** 2).mean()))
    keep = d < np.percentile(d, 80)
    src_tps = np.vstack([X2[keep][::6], dst])
    dst_tps = np.vstack([D[idx][keep][::6], dst])  # anchors pinned (zero shift)
    tps = RBFInterpolator(src_tps, dst_tps - src_tps, kernel='thin_plate_spline', smoothing=2.0)

    def p2m(P):
        Q = P.astype(float).copy(); Q[:, 1] = -Q[:, 1]
        Xq = Q @ A.T + bvec
        return Xq + tps(Xq)
    # anchor sanity: mean distance of mask centroids to their plotree targets
    anchor_err = float(np.mean(np.linalg.norm(p2m(mc_px[order]) - dst, axis=1)))
    print(f'ICP rms {rms:.1f} km; anchor mean err {anchor_err:.1f} km')
    # label transfer
    pts, labs = [], []
    for k, mi in enumerate(order):
        ys, xs = np.nonzero(masks[mi])
        step = max(1, len(xs) // 15000)
        pts.append(np.stack([xs[::step], ys[::step]], 1)); labs.append(np.full(len(xs[::step]), k))
    P = np.concatenate(pts); L = np.concatenate(labs)
    M = p2m(P)
    from shapely import contains_xy
    inside = contains_xy(gbd.buffer(0.02), M[:, 0] / KX, M[:, 1] / KY)
    M, L = M[inside], L[inside]
    tree2 = cKDTree(M)
    minx, miny, maxx, maxy = gbd.bounds
    gn = 520
    gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
    XX, YY = np.meshgrid(gx, gy)
    _, gi = tree2.query(np.stack([XX.ravel() * KX, YY.ravel() * KY], 1))
    classes = L[gi].reshape(gn, gn)
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    feats = {}
    for k, name in enumerate(SEATS):
        cm = (classes == k).astype(np.uint8)
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = []
        for c in cs:
            if len(c) < 4 or cv2.contourArea(c) < 9:
                continue
            q = c.reshape(-1, 2).astype(float)
            polys.append(make_valid(Polygon(zip(minx + q[:, 0] * dx, miny + q[:, 1] * dy)).buffer(max(dx, dy) * 0.6)))
        if polys:
            feats[name] = make_valid(unary_union(polys).intersection(gbd))
    missing = [s for s in SEATS if s not in feats or feats[s].is_empty]
    if missing:
        raise RuntimeError(f'missing {missing}')
    tot = sum(g.area for g in feats.values())
    print({k: round(g.area / tot, 2) for k, g in sorted(feats.items())})
    src_tag = (f'sheet-split (red-line trace, anchor-affine+ICP fit): Punjab/dis2.jpg, '
               f'rms {rms:.1f}km, anchors {anchor_err:.1f}km')
    v2 = json.load(open(f'{BASE}/data/na_2018delim_v2.geojson'))
    for f in v2['features']:
        na = f['properties']['na']
        if na in feats:
            f['properties'] = {'na': na, 'dist': f['properties'].get('dist', ''),
                               'approx': False, 'src': src_tag}
            f['geometry'] = mapping(make_valid(feats[na]).simplify(0.0015))
    json.dump(v2, open(f'{BASE}/data/na_2018delim_v2.geojson', 'w'))
    R.debug_png('Dera Ghazi Khan', img, feats, gbd, f'{BASE}/debug/punjab_DGKhan.png')
    print('merged')


if __name__ == '__main__':
    main()
