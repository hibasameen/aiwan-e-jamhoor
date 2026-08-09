#!/usr/bin/env python3
"""
Audit our 2024 constituency partition against the PBS/ECP "Preliminary
Delimitation 2023" district maps Hib saved in "2023 Delimitation/NA/".

Per district: colour-cluster the seat fills, clean line-work (opening), fit the
map's district area to OUR district outline (affine -> quadratic), match colour
classes to our seats by IoU, and report. Low IoU = candidate for rebuild.

    python3 scripts/audit_city_districts.py "Malir" "Karachi East" ...
"""
import json, sys, os
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union
sys.path.insert(0, 'scripts')
import georef_map as G
import georef_refine as GR

Image.MAX_IMAGE_PIXELS = None
NA_DIR = '2023 Delimitation/NA'
# map file stem -> prefix of RESULTS['2024'] seat names
PREFIX = {'Malir': 'Malir-', 'Karachi Korangi': 'Korangi Karachi-',
          'Karachi Keemari': 'Keamari-', 'Karachi Central': 'Karachi Central-',
          'Karachi West': 'Karachi West-', 'Karachi South': 'Karachi South-',
          'Karachi East': 'Karachi East-', 'Hyderabad': 'Hyderabad'}

def load_ours():
    t = open('map.html', encoding='utf-8').read()
    def blob(p):
        i = t.index(p); j = t.index('\n', i); s = t[i+len(p):j]
        return json.loads(s[:-1] if s.endswith(';') else s)
    R = blob('window.RESULTS='); GEO = blob('window.GEOS=')
    return R['2024'], {f['properties']['na']: f for f in GEO['2024']['features']}

def seat_masks(img_path, nseats):
    im = Image.open(img_path).convert('RGB')
    im = im.resize((im.size[0]//3, im.size[1]//3))
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[:,:,0], a[:,:,1], a[:,:,2]
    mx, mn = a.max(2), a.min(2)
    white = mn > 228
    black = mx < 95
    blue  = (b > r + 50) & (b > 120)
    pink  = (r > 195) & (b > 140) & (g < r - 45)
    grey  = (mx - mn < 10) & (mn > 95) & (mn < 235)
    cand = ~(white|black|blue|pink|grey)
    # land = fill of candidate colours
    land = ndimage.binary_closing(cand, np.ones((7,7)))
    filled = ndimage.binary_fill_holes(land | blue)
    lab, n = ndimage.label(filled)
    if n == 0: return None, None, None
    sizes = ndimage.sum(filled, lab, range(1, n+1))
    district = ndimage.binary_fill_holes(lab == (int(np.argmax(sizes))+1))
    sel = cand & district
    pix = a[sel]
    if len(pix) < 1000: return None, None, None
    samp = pix[np.random.default_rng(0).choice(len(pix), min(200000, len(pix)), replace=False)].astype(np.float32)
    K = nseats + 3                       # headroom so tiny seats keep a cluster
    crit = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 50, 0.4)
    _, _, centers = cv2.kmeans(samp, K, None, crit, 6, cv2.KMEANS_PP_CENTERS)
    merged = []
    for c in centers:
        for m in merged:
            if np.linalg.norm(c-m) < 20: break
        else: merged.append(c)
    centers = np.array(merged)
    best = np.full(a.shape[:2], 1e9, np.float32)
    cls = np.zeros(a.shape[:2], np.int16)
    af = a.astype(np.float32)
    for i, c in enumerate(centers, 1):
        d = ((af[:,:,0]-c[0])**2 + (af[:,:,1]-c[1])**2 + (af[:,:,2]-c[2])**2)
        upd = d < best
        best[upd] = d[upd]; cls[upd] = i
    cls[~sel] = 0
    masks = []
    for i in range(1, len(centers)+1):
        m = cls == i
        m = ndimage.binary_opening(m, np.ones((5,5)))   # kill line-work
        if m.sum() > 0.0015 * district.sum():
            masks.append((m, tuple(int(v) for v in centers[i-1])))
    return district, masks, a.shape

def audit(stem, R24, F24, do_plot=True):
    path = f'{NA_DIR}/{stem} NA.JPG'
    if not os.path.exists(path):
        print(f'{stem}: file missing'); return None
    pref = PREFIX[stem]
    seats = sorted([na for na, r in R24.items() if (r.get('name') or '').startswith(pref)],
                   key=lambda k: int(k.split('-')[1]))
    ours = {na: shape(F24[na]['geometry']).buffer(0) for na in seats}
    outline = unary_union(list(ours.values())).buffer(0)
    district, masks, shp = seat_masks(path, max(2, len(seats)))
    if district is None:
        print(f'{stem}: segmentation failed'); return None
    aff, iou = G.fit(district, outline, verbose=False)
    try:
        coef, iou2, _ = GR.refine(district, outline, aff, deg=2, step=4)
    except Exception:
        coef, iou2 = None, iou
    print(f'== {stem}: {len(seats)} seats, {len(masks)} colour classes, georef IoU {iou:.2f}->{iou2:.2f}')
    def warp_mask(m):
        cs2, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        ps = []
        for c in cs2:
            if cv2.contourArea(c) < 40: continue
            e = c.reshape(-1,2).astype(float)
            ll = GR.forward(e, coef, 2) if coef is not None else \
                 np.column_stack([aff[0]*e[:,0]+aff[1]*e[:,1]+aff[2], aff[3]*e[:,0]+aff[4]*e[:,1]+aff[5]])
            try:
                q = Polygon(ll).buffer(0)
                if q.area > 0: ps.append(q)
            except Exception: pass
        return unary_union(ps) if ps else None
    rows = []
    for m, col in masks:
        w = warp_mask(m)
        if w is None: continue
        best = max(((w.intersection(g).area / w.union(g).area, na) for na, g in ours.items()))
        rows.append((best[1], best[0], w.area, col, w))
    rows.sort(key=lambda r: int(r[0].split('-')[1]))
    for na, i, ar, col, _ in rows:
        mark = ' <-- LOW' if i < 0.55 else ''
        print(f'   class{col} -> {na} ({R24[na]["name"]}): IoU {i:.2f}{mark}')
    claimed = {r[0] for r in rows}
    for na in seats:
        if na not in claimed: print(f'   {na} ({R24[na]["name"]}): NO matching colour class')
    return rows

if __name__ == '__main__':
    R24, F24 = load_ours()
    for stem in (sys.argv[1:] or list(PREFIX)):
        audit(stem, R24, F24)
