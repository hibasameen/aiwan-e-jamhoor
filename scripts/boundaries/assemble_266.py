#!/usr/bin/env python3
"""Merge the 36 new KP/Balochistan/ICT seats into the 230-seat partial layer,
clean slivers/overlaps, and verify a 266-seat exact national partition."""
import json, os, sys
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import make_valid
BASE = '/root/aiwan'

old = json.load(open(f'{BASE}/data/na_2023delim_true_partial.geojson'))
new = json.load(open(f'{BASE}/out/kpbal/kp_bal_ict_2023.geojson'))

seats = {}
props = {}
for f in old['features']:
    na = f['properties']['na']
    seats[na] = make_valid(shape(f['geometry']).buffer(0))
    props[na] = dict(f['properties'])
sheetgeo = {}
sp = f'{BASE}/out/kpbal/quetta_sheet.geojson'
if os.path.exists(sp):
    for f in json.load(open(sp))['features']:
        sheetgeo[f['properties']['na']] = f
newly = set()
for f in new['features']:
    na = f['properties']['na']
    f = sheetgeo.get(na, f)          # sheet-digitised output wins over composition
    if na in seats:
        print('!! duplicate seat from new build:', na); continue
    seats[na] = make_valid(shape(f['geometry']).buffer(0))
    props[na] = dict(f['properties'])
    newly.add(na)
print(f'sheet-digitised overrides applied: {sorted(sheetgeo)}')
print(f'total seats: {len(seats)} (was {len(old["features"])}, added {len(newly)})')

# --- apply canvas-level transfers (detached lobes wrongly held by a canvas)
tpath = f'{BASE}/out/kpbal/transfers.json'
if os.path.exists(tpath):
    for t in json.load(open(tpath)):
        lobe = make_valid(shape(t['geometry']).buffer(0))
        tgt = t['to']
        seats[tgt] = make_valid(unary_union([seats[tgt], lobe]))
        print(f"transferred {t['area_km2']:,} km2 from {t['from_canvas']} -> {tgt}")

# --- inter-seat overlap pass (only touches the new seats + their neighbours)
keys = sorted(seats, key=lambda s: int(s.split('-')[1]))
import itertools
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection

def polyonly(g):
    g = make_valid(g)
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    if hasattr(g, 'geoms'):
        ps = [x for x in g.geoms if isinstance(x, (Polygon, MultiPolygon)) and not x.is_empty]
        return unary_union(ps) if ps else Polygon()
    return Polygon()

def perim(g):
    g = polyonly(g)
    if g.is_empty: return 0.0
    if g.geom_type == 'Polygon': return g.exterior.length
    return sum(x.exterior.length for x in g.geoms)

for na in list(seats): seats[na] = polyonly(seats[na])

fixed = 0
for a, b in itertools.combinations(keys, 2):
    ga, gb = seats[a], seats[b]
    if not ga.intersects(gb):
        continue
    inter = ga.intersection(gb)
    if inter.is_empty or inter.area <= 0:
        continue
    if inter.geom_type in ('LineString', 'MultiLineString', 'Point', 'MultiPoint'):
        continue
    # give the overlap to whichever seat shares more boundary with it
    loser = b if perim(ga) >= perim(gb) else a
    seats[loser] = polyonly(seats[loser].difference(inter))
    fixed += 1
print(f'overlaps resolved: {fixed}')

# --- sliver pass: parts under 1 km2 that are detached go to the longest-shared neighbour
KM2 = 1.0/12100.0
moved = 0
for na in keys:
    g = seats[na]
    if g.geom_type != 'MultiPolygon':
        continue
    parts = sorted(g.geoms, key=lambda p: -p.area)
    keep = [parts[0]]
    for p in parts[1:]:
        if p.area >= KM2:
            keep.append(p); continue
        best, bl = None, 0.0
        for other in keys:
            if other == na:
                continue
            if not seats[other].intersects(p.buffer(1e-6)):
                continue
            l = seats[other].intersection(p.buffer(1e-6)).length
            if l > bl:
                bl, best = l, other
        if best:
            seats[best] = polyonly(unary_union([seats[best], p])); moved += 1
        else:
            keep.append(p)
    seats[na] = polyonly(unary_union(keep))
print(f'slivers reassigned: {moved}')

feats = []
for na in keys:
    p = props[na]; p['na'] = na
    feats.append(dict(type='Feature', properties=p, geometry=mapping(seats[na])))
out = dict(type='FeatureCollection', features=feats)
json.dump(out, open(f'{BASE}/out/kpbal/na_2023delim_true_full.geojson', 'w'))

# --- verification
uni = unary_union(list(seats.values()))
ref = unary_union([make_valid(shape(f['geometry']).buffer(0))
                   for f in json.load(open(f'{BASE}/data/na_2018delim_v2.geojson'))['features']])
print(f'\nseats           : {len(feats)}')
print(f'missing numbers : {[i for i in range(1,267) if f"NA-{i}" not in seats]}')
tot = sum(g.area for g in seats.values())
print(f'sum of parts     : {tot*12100:,.0f} km2')
print(f'union            : {uni.area*12100:,.0f} km2  (overlap residue {(tot-uni.area)*12100:,.2f} km2)')
print(f'2018 layer union : {ref.area*12100:,.0f} km2')
print(f'sym-diff vs 2018 : {uni.symmetric_difference(ref).area/ref.area:.4%}')
