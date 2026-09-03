#!/usr/bin/env python3
"""
Assemble all resolved 2023-delimitation seats into na_2023delim_true_partial.geojson:
- 38 single-seat canvases from out/seats_2023_scaffold.geojson
- all out/sindh/C*.geojson canvas splits (54 seats)
Then physical-sliver cleanup at seat level: any detached seat part < MINKM2 whose
seat has a bigger main body is reassigned to the neighbouring seat with the longest
shared boundary (iterated). Preserves the exact national-partial partition.
"""
import json, glob, collections
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import make_valid

MINKM2 = 1.0
feats = {}
sc = json.load(open('out/seats_2023_scaffold.geojson'))
for f in sc['features']:
    feats[f['properties']['na']] = f
for fn in sorted(glob.glob('out/sindh/C*.geojson')):
    for f in json.load(open(fn))['features']:
        feats[f['properties']['na']] = f
print(len(feats), 'seats resolved')

geo = {na: make_valid(shape(f['geometry'])) for na, f in feats.items()}
KM2 = 111*104

def parts(g):
    return list(g.geoms) if g.geom_type == 'MultiPolygon' else [g]

changed, rounds = 1, 0
while changed and rounds < 6:
    changed = 0; rounds += 1
    for na in list(geo):
        ps = sorted(parts(geo[na]), key=lambda p: -p.area)
        if len(ps) < 2: continue
        keep = [ps[0]]
        for p in ps[1:]:
            if p.area*KM2 >= MINKM2:
                keep.append(p); continue
            # reassign to neighbour with longest shared boundary
            best, bl = None, 0.0
            pb = p.buffer(0.001)
            for nb in geo:
                if nb == na: continue
                if geo[nb].distance(p) > 0.01: continue
                l = pb.intersection(geo[nb]).area
                if l > bl: bl, best = l, nb
            if best is None:
                keep.append(p); continue
            geo[best] = make_valid(geo[best].union(p)); changed += 1
        geo[na] = make_valid(unary_union(keep))
    print(f'round {rounds}: {changed} slivers reassigned')

out = {'type':'FeatureCollection','features':[]}
for na in sorted(geo, key=lambda x:int(x.split('-')[1])):
    f = feats[na]
    f['geometry'] = mapping(geo[na])
    out['features'].append(f)
json.dump(out, open('out/na_2023delim_true_partial.geojson','w'))

# integrity: pairwise overlap + union check within Sindh block
sindh = {na:g for na,g in geo.items() if 190 <= int(na.split('-')[1]) <= 250}
u = make_valid(unary_union(list(sindh.values())))
tot = sum(g.area for g in sindh.values())
print(f'partial file: {len(out["features"])} seats; sindh {len(sindh)} seats, sum/union={tot/u.area:.6f}')
multi = {na: len(parts(g)) for na,g in geo.items() if len(parts(g))>3}
print('seats with >3 parts:', multi)
