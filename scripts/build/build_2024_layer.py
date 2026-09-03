#!/usr/bin/env python3
"""Prepare the app's 2024 layer from the true 2023-delimitation boundaries.

Replaces the old district-Voronoi na_2024delim_simplified.geojson. Carries the
district label across from that file (the panel uses properties.dist) and gives
every seat a normalised `confidence` so the map can mark provisional lines.
"""
import json

NEW = 'out/kpbal/na_2023delim_simplified.geojson'
OLD = 'data/na_2024delim_simplified.geojson'
OUT = 'data/na_2023delim_app.geojson'

# documented low-confidence seats from the earlier Sindh/Punjab legs (METHODOLOGY §7)
LOW = {'NA-78', 'NA-80',                                  # Gujranwala city split undrawn
       'NA-101', 'NA-102', 'NA-103', 'NA-104',            # Faisalabad city voronoi
       'NA-115', 'NA-116',                                # Sheikhupura invented city disc
       'NA-232', 'NA-233', 'NA-234'}                      # Korangi taluka-composition

HIGH_SRC = ('sheet-split', 'hybrid: sheet-split', 'district-composition')


def confidence(p):
    if p.get('confidence'):
        return p['confidence']                            # the 36 new seats set their own
    src = str(p.get('src', ''))
    if src.startswith(HIGH_SRC):
        return 'high'
    return 'medium'


dist = {f['properties']['na']: f['properties'].get('dist')
        for f in json.load(open(OLD))['features']}
gj = json.load(open(NEW))
counts = {}
for f in gj['features']:
    p = f['properties']
    na = p['na']
    c = 'low' if na in LOW else confidence(p)
    src = str(p.get('src', ''))
    f['properties'] = {
        'na': na,
        'dist': dist.get(na),
        'approx': bool(p.get('approx')),
        'confidence': c,
        'src': src[:150],
        'rms_km': p.get('rms_km'),
    }
    counts[c] = counts.get(c, 0) + 1
json.dump(gj, open(OUT, 'w'), separators=(',', ':'))
missing_dist = [f['properties']['na'] for f in gj['features'] if not f['properties']['dist']]
print(f'{OUT}: {len(gj["features"])} seats  confidence={counts}')
print(f'  seats with no district label: {len(missing_dist)} {missing_dist[:10]}')
