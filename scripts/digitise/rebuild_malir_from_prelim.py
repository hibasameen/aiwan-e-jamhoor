#!/usr/bin/env python3
"""
Rebuild NA-229/230/231 (District Malir, 2023 delimitation) from the PBS/ECP
"District Malir — Preliminary Delimitation 2023" map supplied by Hib.

Why: our sheet digitisation segmented NA-231 from a faint yellow wash on the
marked final sheet (medium confidence, rms 2.18 km) and placed the wedge too far
north-east. The PBS/ECP map has crisp colour fills (yellow=231, lavender=230,
khaki=229) matching the final Form-7 composition (Airport, Malir Cantt, Murad
Memon part, Kathor arm) and the Wikipedia locator. This script:

 1. colour-segments the three seats
 2. georeferences the map's district area to OUR Malir district outline
    (union of current NA-229/230/231 — that outline was exact all along)
 3. rebuilds the three seats as an exact partition of that outline
 4. swaps them into map.html GEOS['2024'] and na_2023delim_true_full.geojson

Caveat recorded in props: source map is the PRELIMINARY 2023 delimitation; the
final Form-7 kept the same seat structure for Malir (composition text matches).
"""
import json, time
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import sys; sys.path.insert(0, 'scripts')
import georef_map as G

Image.MAX_IMAGE_PIXELS = None
IMG = '/sessions/relaxed-clever-cannon/mnt/uploads/Malir NA.JPG'

# ---------- 1. segmentation (half resolution is plenty) ----------
im = Image.open(IMG).convert('RGB')
im = im.resize((im.size[0] // 2, im.size[1] // 2))
a = np.asarray(im).astype(int)
r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
yellow  = (r > 200) & (abs(r - g) < 45) & ((r - b) >= 70)
lav     = (r > 150) & (b - (r + g) / 2 > 22) & (b > 190)
khaki   = (r > 150) & (abs(r - g) < 32) & ((r - b) >= 10) & ((r - b) < 70) & ~yellow
water   = (b > r + 60) & (r < 140)
land = yellow | lav | khaki
land = ndimage.binary_closing(land, np.ones((7, 7)))
filled = ndimage.binary_fill_holes(land | water)
lab, n = ndimage.label(filled)
sizes = ndimage.sum(filled, lab, range(1, n + 1))
district = lab == (int(np.argmax(sizes)) + 1)
district = ndimage.binary_fill_holes(district)
print(f'district px {district.sum():,} | yellow {yellow.sum():,} lav {lav.sum():,} khaki {khaki.sum():,}')

# class raster: 1=229 khaki, 2=230 lavender, 3=231 yellow (inside district only)
cls = np.zeros(district.shape, np.uint8)
cls[khaki & district] = 1
cls[lav & district] = 2
cls[yellow & district] = 3
# mode smooth to kill text/lines
k = np.ones((5, 5))
for _ in range(2):
    counts = [ndimage.uniform_filter((cls == i).astype(float), 5) for i in (1, 2, 3)]
    m = np.argmax(np.stack(counts), 0) + 1
    conf = np.max(np.stack(counts), 0)
    cls = np.where(district & (conf > 0.15), m, cls).astype(np.uint8)
# fill unlabelled district px (river/text) by nearest class
un = district & (cls == 0)
_, (iy, ix) = ndimage.distance_transform_edt(cls == 0, return_indices=True)
cls[un] = cls[iy[un], ix[un]]

# ---------- 2. georeference to our Malir outline ----------
txt = open('map.html', encoding='utf-8').read()
lines = txt.split('\n')
gi = next(i for i, l in enumerate(lines) if l.startswith('window.GEOS='))
GEO = json.loads(lines[gi][len('window.GEOS='):-1])
cur = {f['properties']['na']: shape(f['geometry']).buffer(0)
       for f in GEO['2024']['features'] if f['properties']['na'] in ('NA-229', 'NA-230', 'NA-231')}
malir = unary_union(list(cur.values())).buffer(0)
aff, iou = G.fit(district, malir, verbose=True)
print(f'georef IoU {iou:.3f}')
A, B, C, D, E, F = aff
det = A * E - B * D
inv = np.array([[E / det, -B / det], [-D / det, A / det]])

# ---------- 3. exact partition on a lon/lat grid ----------
x0, y0, x1, y1 = malir.bounds
CELL = 0.002
W = int((x1 - x0) / CELL) + 2; H = int((y1 - y0) / CELL) + 2
from PIL import ImageDraw
mimg = Image.new('L', (W, H), 0)
dr = ImageDraw.Draw(mimg)
polys = malir.geoms if malir.geom_type == 'MultiPolygon' else [malir]
for p in polys:
    for ring, v in [(p.exterior, 255)] + [(rr, 0) for rr in p.interiors]:
        xy = np.asarray(ring.coords)
        dr.polygon(list(zip((xy[:, 0] - x0) / CELL, (y1 - xy[:, 1]) / CELL)), fill=v)
mmask = np.asarray(mimg) > 127
gy, gx = np.where(mmask)
lon = x0 + gx * CELL; lat = y1 - gy * CELL
px = inv[0, 0] * (lon - C) + inv[0, 1] * (lat - F)
py = inv[1, 0] * (lon - C) + inv[1, 1] * (lat - F)
pxi = np.clip(px.astype(int), 0, cls.shape[1] - 1)
pyi = np.clip(py.astype(int), 0, cls.shape[0] - 1)
lab2 = cls[pyi, pxi]
out = np.zeros((H, W), np.uint8)
out[gy, gx] = lab2
# any zero cells inside mask -> nearest labelled
un = mmask & (out == 0)
if un.any():
    _, (iy, ix) = ndimage.distance_transform_edt(out == 0, return_indices=True)
    out[un] = out[iy[un], ix[un]]
shares = {i: (out == i).sum() / mmask.sum() for i in (1, 2, 3)}
print('area shares NA-229/230/231:', {f'NA-{228+i}': round(s, 3) for i, s in shares.items()})

# ---------- 4. vectorise + clip to exact outline ----------
def vec(mask):
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    outp = []
    for i, c in enumerate(cs):
        if hier[0][i][3] != -1 or cv2.contourArea(c) < 3: continue
        e = c.reshape(-1, 2).astype(float)
        ring = np.column_stack([x0 + e[:, 0] * CELL, y1 - e[:, 1] * CELL])
        holes = []
        j = hier[0][i][2]
        while j != -1:
            hc = cs[j].reshape(-1, 2).astype(float)
            if cv2.contourArea(cs[j]) >= 3:
                holes.append(np.column_stack([x0 + hc[:, 0] * CELL, y1 - hc[:, 1] * CELL]))
            j = hier[0][j][0]
        try:
            p = Polygon(ring, holes).buffer(0)
            if not p.is_empty: outp.append(p)
        except Exception: pass
    return unary_union(outp) if outp else None

geoms = {}
for i, na in ((1, 'NA-229'), (2, 'NA-230'), (3, 'NA-231')):
    g = vec(out == i)
    g = g.simplify(0.001).buffer(0).intersection(malir)
    geoms[na] = g
# distribute residue of the exact outline
resid = malir.difference(unary_union(list(geoms.values())).buffer(0))
if not resid.is_empty:
    pieces = resid.geoms if resid.geom_type in ('MultiPolygon', 'GeometryCollection') else [resid]
    for p in pieces:
        if p.geom_type != 'Polygon' or p.area == 0: continue
        best = min(geoms, key=lambda na: geoms[na].distance(p))
        geoms[best] = unary_union([geoms[best], p])
tot = sum(g.area for g in geoms.values())
print('final shares:', {na: round(g.area / tot, 3) for na, g in geoms.items()},
      '| sym-diff vs outline %.2e' % unary_union(list(geoms.values())).symmetric_difference(malir).area)

# ---------- 5. swap into map.html + true_full ----------
def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o
def wind(g):
    if g.geom_type == 'Polygon': return orient(g, -1.0)
    if g.geom_type == 'MultiPolygon': return MultiPolygon([orient(p, -1.0) for p in g.geoms])
    return g
SRC = ('PBS/ECP District Malir Preliminary-Delimitation-2023 map (colour fills), '
       'georeferenced to the digitised Malir outline; final Form-7 composition concurs')
open(f'map.html.bak_{int(time.time())}', 'w', encoding='utf-8').write(txt)
for f in GEO['2024']['features']:
    na = f['properties']['na']
    if na in geoms:
        f['geometry'] = rnd(mapping(wind(geoms[na].buffer(0))))
        f['properties']['src'] = SRC
        f['properties']['confidence'] = 'medium'
lines[gi] = 'window.GEOS=' + json.dumps(GEO, separators=(',', ':'), ensure_ascii=False) + ';'
open('map.html', 'w', encoding='utf-8').write('\n'.join(lines))
TF = json.load(open('data/na_2023delim_true_full.geojson'))
for f in TF['features']:
    na = f['properties']['na']
    if na in geoms:
        f['geometry'] = mapping(wind(geoms[na].buffer(0)))
        f['properties']['src'] = SRC
json.dump(TF, open('data/na_2023delim_true_full.geojson', 'w'))
print('swapped into map.html + na_2023delim_true_full.geojson')
