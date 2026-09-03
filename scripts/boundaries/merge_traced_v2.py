#!/usr/bin/env python3
"""
Merge the v2 traces (na_traced2_{1990,1993,1997}.geojson) into the final
207-seat boundary set, with placement validation.

Tiering per seat (year priority 1993 > 1997 > 1990 inside each tier):
  0  main-map trace, label read or unique-elimination
  1  inset trace (city boxes, affine-fitted), label read or unique-elimination
  2  low-confidence pairing (region real, NA assignment by ordering)
  3  Voronoi reconstruction in map numbering (approx)

Validation: a candidate is rejected if its polygon sits >40 km from the union
of its crosswalk districts — this is the guard against misplaced insets.

Output: data/boundaries/na_207seat_1985-1997_traced.geojson (overwrites)
"""
import json
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import sys; sys.path.insert(0, 'scripts')
import build_reconstructed_geometry as brg

KM = 105.0
YEARS = ['1993', '1997', '1990']
XW = json.load(open('data/wip/trace/xwalk_207map.json'))['base']
DIST = brg.load_districts()
DUNION = {na: unary_union([DIST[d] for d in ds if d in DIST]) for na, ds in XW.items()}

traced = {y: {f['properties']['na']: f for f in
              json.load(open(f'data/wip/trace/na_traced2_{y}.geojson'))['features']}
          for y in YEARS}
recon = {f['properties']['na']: f for f in
         json.load(open('data/boundaries/na_207seat_map_reconstructed.geojson'))['features']}

def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o

def clean(geom):
    g = shape(geom).buffer(0)
    if g.is_empty: return None
    if g.geom_type == 'Polygon': return orient(g, -1.0)
    if g.geom_type == 'MultiPolygon':
        return MultiPolygon([orient(p, -1.0) for p in g.geoms])
    return None

def tier(f):
    p = f['properties']
    if p.get('confidence') == 'low': return 2
    return 1 if p.get('inset') else 0

feats, tally, demoted = [], {}, []
for n in range(1, 208):
    na = f'NA-{n}'
    cands = []
    for y in YEARS:
        f = traced[y].get(na)
        if f: cands.append((tier(f), YEARS.index(y), f))
    cands.sort(key=lambda t: (t[0], t[1]))
    chosen = None
    for _, _, f in cands:
        g = clean(f['geometry'])
        if g is None: continue
        d = DUNION[na].distance(g) * KM if na in DUNION else 999
        if d > 40:
            demoted.append((na, f['properties']['src'], round(d)))
            continue
        chosen = (f, g); break
    if chosen:
        f, g = chosen
        pr = {'na': na, 'src': f['properties']['src'], 'approx': False}
        if f['properties'].get('inset'): pr['src'] += '-inset'
        if f['properties'].get('confidence') == 'low': pr['confidence'] = 'low'
        feats.append({'type': 'Feature', 'properties': pr, 'geometry': rnd(mapping(g))})
        key = 'traced-low' if 'confidence' in pr else ('traced-inset' if '-inset' in pr['src'] else 'traced')
        tally[key] = tally.get(key, 0) + 1
    elif na in recon:
        g = clean(recon[na]['geometry'])
        feats.append({'type': 'Feature',
                      'properties': {'na': na, 'src': 'reconstructed', 'approx': True},
                      'geometry': rnd(mapping(g))})
        tally['voronoi'] = tally.get('voronoi', 0) + 1

out = 'data/boundaries/na_207seat_1985-1997_traced.geojson'
json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w'))
print(f'wrote {out}: {len(feats)} seats | {tally}')
print('validation demotions:', demoted if demoted else 'none')
lows = sorted(int(f['properties']['na'].split('-')[1]) for f in feats if f['properties'].get('confidence'))
vor = sorted(int(f['properties']['na'].split('-')[1]) for f in feats if f['properties']['approx'])
print('low-confidence seats:', lows)
print('voronoi fallbacks:', vor)
