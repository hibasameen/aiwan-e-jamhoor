#!/usr/bin/env python3
"""
Restore digitised detail to the 2024 city constituencies in map.html.

GEOS['2024'] was embedded from the app-ready simplification (11-25 vertices for
some Karachi/Lahore seats), which looks blocky at the new 55x city zoom. The
full digitised partition (data/na_2023delim_true_full.geojson, sheet-digitised,
rms ~1-1.5 km) is on disk, so seats that are small OR inside a major-city box
get their geometry re-embedded from it at a gentle 0.0005-deg simplification.
Large rural seats keep the existing light geometry. Asserts + backup.
"""
import json, time
from shapely.geometry import shape, mapping, box, MultiPolygon
from shapely.geometry.polygon import orient

CITY = [box(66.55,24.70,67.67,25.74), box(73.92,31.17,74.74,31.82),
        box(72.54,32.97,73.73,34.12), box(72.60,30.57,73.78,31.89),
        box(71.17,33.53,71.95,34.42), box(66.14,29.71,67.53,30.57)]
SMALL = 0.06          # deg^2
TOL = 0.0005          # ~55 m

def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o

def wind(g):
    if g.geom_type == 'Polygon': return orient(g, -1.0)
    if g.geom_type == 'MultiPolygon': return MultiPolygon([orient(p, -1.0) for p in g.geoms])
    return g

TRUE = {f['properties']['na']: shape(f['geometry']).buffer(0)
        for f in json.load(open('data/na_2023delim_true_full.geojson'))['features']}

txt = open('map.html', encoding='utf-8').read()
open(f'map.html.bak_{int(time.time())}', 'w', encoding='utf-8').write(txt)
lines = txt.split('\n')
gi = next(i for i, l in enumerate(lines) if l.startswith('window.GEOS='))
G = json.loads(lines[gi][len('window.GEOS='):-1])

up, kept = 0, 0
for f in G['2024']['features']:
    na = f['properties']['na']
    g = shape(f['geometry']).buffer(0)
    urban = any(g.intersects(cb) for cb in CITY)
    if (g.area < SMALL or urban) and na in TRUE:
        det = wind(TRUE[na].simplify(TOL).buffer(0))
        f['geometry'] = rnd(mapping(det))
        up += 1
    else:
        kept += 1

lines[gi] = 'window.GEOS=' + json.dumps(G, separators=(',', ':'), ensure_ascii=False) + ';'
out = '\n'.join(lines)
open('map.html', 'w', encoding='utf-8').write(out)
print(f'upgraded {up} seats to full detail, kept {kept}; map.html {len(out)//1024} KB')
