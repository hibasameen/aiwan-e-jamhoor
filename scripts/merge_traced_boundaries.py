#!/usr/bin/env python3
"""
Merge the three traced Commons maps (1990/1993/1997 — same 207-seat delimitation)
into one boundary set, best geometry per seat, and fall back to the Voronoi
reconstruction for the seats no map's OCR could label.

Preference per NA:
  1. a properly-placed MAIN-map trace (years ordered 1993, 1997, 1990)
  2. an inset (Karachi) trace, same year order
  3. the reconstructed (Voronoi) polygon  -> properties.approx = true

Output: data/boundaries/na_207seat_1985-1997_traced.geojson
"""
import json
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.geometry.polygon import orient

YEARS = ['1993', '1997', '1990']
traced = {y: {f['properties']['na']: f for f in
              json.load(open(f'data/wip/trace/na_traced_{y}.geojson'))['features']}
          for y in YEARS}
recon = {f['properties']['na']: f for f in
         json.load(open('data/boundaries/na_207seat_1985-1997_reconstructed.geojson'))['features']}

def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o

def clean(geom):
    g = shape(geom).buffer(0)
    if g.is_empty: return None
    if g.geom_type == 'Polygon': g = orient(g, -1.0)
    elif g.geom_type == 'MultiPolygon': g = MultiPolygon([orient(p, -1.0) for p in g.geoms])
    return g

def pick(na):
    for y in YEARS:                       # main-map trace first
        f = traced[y].get(na)
        if f and not f['properties']['inset']:
            return f['geometry'], f'commons-{y}', False
    for y in YEARS:                       # then inset trace (Karachi)
        f = traced[y].get(na)
        if f and f['properties']['inset']:
            return f['geometry'], f'commons-{y}-inset', False
    if na in recon:                       # then reconstruction
        return recon[na]['geometry'], 'reconstructed', True
    return None, None, None

feats, src_tally = [], {}
for n in range(1, 208):
    na = f'NA-{n}'
    geom, src, approx = pick(na)
    if geom is None: continue
    g = clean(geom)
    if g is None: continue
    src_tally[src.split('-inset')[0]] = src_tally.get(src.split('-inset')[0], 0) + 1
    feats.append({'type': 'Feature',
                  'properties': {'na': na, 'src': src, 'approx': approx},
                  'geometry': rnd(mapping(g))})

out = 'data/boundaries/na_207seat_1985-1997_traced.geojson'
json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w'))
print(f'wrote {out}: {len(feats)} seats')
print('provenance:', src_tally)
print('reconstructed fallbacks:', sorted(int(f['properties']['na'].split('-')[1])
      for f in feats if f['properties']['approx']))
