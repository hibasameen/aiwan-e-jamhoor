#!/usr/bin/env python3
"""
Rebuild the six Karachi 2023 canvases from the 2018 layer's district footprints.

COD ADM2's Karachi polygons misplace the West/South line (real Keamari/Mauripur
peninsula sits in COD 'South Karachi'), so canvases C090-C095 built from COD are
wrong at district scale. The 2018 layer was sheet-fitted per district (dis8-dis15)
and its Karachi district unions are the best available footprints; 2023 kept the
same district lines (Keamari was carved from West, but our canvas merges the two).

Method: freeze the current Karachi block footprint B (union of the six current
canvases — it partitions exactly against neighbouring districts). Classify a dense
grid over B by nearest 2018-district union; extract per-district polygons from the
grid; exact-partition normalisation (sequential difference, slivers to the district
with longest shared boundary). Overwrite the six features in out/canvases_2023.geojson
(and district features in out/districts_2023.geojson: Malir, Korangi, Karachi East,
Karachi South, Karachi West, Karachi Central).
"""
import json, numpy as np, cv2
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union
from shapely import make_valid
from scipy.spatial import cKDTree

D18 = {  # 2023 district -> 2018 seat numbers whose union is its footprint
 'Malir': [236, 237, 238], 'Korangi': [239, 240, 241],
 'Karachi East': [242, 243, 244, 245], 'Karachi South': [246, 247],
 'Karachi West': [248, 249, 250, 251, 252],  # = West + Keamari (2023)
 'Karachi Central': [253, 254, 255, 256]}
CANV = {  # canvas_id -> district(s)
 'C090_Malir': 'Malir', 'C091_Korangi': 'Korangi', 'C092_KarachiEast': 'Karachi East',
 'C093_KarachiSouth': 'Karachi South', 'C094_KarachiWest': 'Karachi West',
 'C095_KarachiCentral': 'Karachi Central'}

na18 = json.load(open('data/na_2018delim_v2.geojson'))
g18 = {}
for dist, nums in D18.items():
    gs = [make_valid(shape(f['geometry'])) for f in na18['features']
          if int(f['properties']['na'].split('-')[1]) in nums]
    assert len(gs) == len(nums), (dist, len(gs))
    g18[dist] = make_valid(unary_union(gs)).buffer(0)

cj = json.load(open('out/canvases_2023.geojson'))
cur = {f['properties']['canvas_id']: make_valid(shape(f['geometry']))
       for f in cj['features'] if f['properties']['canvas_id'] in CANV}
B = make_valid(unary_union(list(cur.values()))).buffer(0)

# report displacement
for cid, dist in CANV.items():
    a, b = cur[cid], g18[dist]
    print(f'{cid:22s} COD-area {a.area*111*104:8.0f}km2  2018-area {b.area*111*104:8.0f}km2 '
          f'IoU {a.intersection(b).area/a.union(b).area:.2f}')

# dense grid classification over B
minx, miny, maxx, maxy = B.bounds
N = 900
gx = np.linspace(minx, maxx, N); gy = np.linspace(miny, maxy, N)
XX, YY = np.meshgrid(gx, gy)
pts = np.stack([XX.ravel(), YY.ravel()], 1)
from shapely import STRtree, points as shp_points
P = shp_points(pts[:, 0], pts[:, 1])
inside = np.array([B.covers(p) for p in P])
names = list(g18)
# containment first
lab = np.full(len(pts), -1)
for i, n in enumerate(names):
    g = g18[n]
    m = np.array([inside[j] and lab[j] < 0 and g.covers(P[j]) for j in range(len(pts))])
    lab[m] = i
# nearest for the rest (boundary-sample KD-trees)
trees = []
for n in names:
    bnd = g18[n].boundary
    segs = [bnd] if bnd.geom_type == 'LineString' else list(bnd.geoms)
    C = np.concatenate([np.stack(s.xy, 1) for s in segs])
    trees.append(cKDTree(C))
un = np.where(inside & (lab < 0))[0]
if len(un):
    dmat = np.stack([t.query(pts[un])[0] for t in trees], 1)
    lab[un] = dmat.argmin(1)
classes = lab.reshape(N, N)
dx, dy = gx[1]-gx[0], gy[1]-gy[0]
new = {}
for i, n in enumerate(names):
    cm = (classes == i).astype(np.uint8)
    cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
    polys = []
    for c in cs:
        if len(c) < 4 or cv2.contourArea(c) < 4: continue
        q = c.reshape(-1, 2).astype(float)
        polys.append(make_valid(Polygon(zip(minx+q[:,0]*dx, miny+q[:,1]*dy)).buffer(max(dx,dy)*0.7)))
    new[n] = make_valid(unary_union(polys)).intersection(B) if polys else None
# exact partition: sequential difference in fixed order, remainder to last
acc = None
order = sorted(names, key=lambda n: -new[n].area)
for k, n in enumerate(order):
    g = new[n] if acc is None else make_valid(new[n].difference(acc))
    if k == len(order)-1:
        g = make_valid(B.difference(acc))
    new[n] = g
    acc = g if acc is None else make_valid(acc.union(g))
res = make_valid(B.difference(unary_union(list(new.values()))))
print('residual after partition:', res.area)

# write back
for f in cj['features']:
    cid = f['properties']['canvas_id']
    if cid in CANV:
        f['geometry'] = mapping(new[CANV[cid]])
json.dump(cj, open('out/canvases_2023.geojson', 'w'))
dj = json.load(open('out/districts_2023.geojson'))
for f in dj['features']:
    n = f['properties']['district']
    if n in new:
        f['geometry'] = mapping(new[n])
        f['properties']['flags'] = (f['properties'].get('flags','') +
                                    ';footprint-from-2018-seat-unions').strip(';')
json.dump(dj, open('out/districts_2023.geojson', 'w'))
print('updated canvases + districts. New areas (km2):')
for n in names: print(f'  {n:16s} {new[n].area*111*104:8.0f}')
