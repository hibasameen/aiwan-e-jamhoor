#!/usr/bin/env python3
"""
Final boundary fix in map.html:
  * GEOS['207seat']   <- merged v2 traced set (162 main + 21 inset + 16 low-conf
                         + 8 Voronoi), correct inset placement, validated
  * GEOS['207seat85'] <- NEW: Voronoi set in ElectionPakistani-1985 numbering
  * YEARS['1985']     -> geo '207seat85' (its results use the 1985 numbering,
                         which differs from the 1988-97 map numbering)
  * YEARS['1988'].prev -> null (cross-year compare vs 1985 would join wrong
                         seats across numbering schemes)
Asserts + backup, as always.
"""
import json, time

def load(path, seats200=False):
    gj = json.load(open(path))
    for f in gj['features']:
        n = int(f['properties']['na'].split('-')[1])
        f['properties']['prov'] = ('Khyber Pakhtunkhwa' if n <= 26 else 'FATA' if n <= 34 else
            'Islamabad Capital Territory' if n == 35 else 'Punjab' if n <= 150 else
            'Sindh' if n <= 196 else 'Balochistan')
    return gj

def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o

TRACED = load('data/boundaries/na_207seat_1985-1997_traced.geojson')
V85 = load('data/boundaries/na_207seat_1985numbering_reconstructed.geojson')
for f in V85['features']:
    f['geometry'] = rnd(f['geometry'])

MAP = 'map.html'
lines = open(MAP, encoding='utf-8').read().split('\n')
open(f'{MAP}.bak_{int(time.time())}', 'w', encoding='utf-8').write('\n'.join(lines))

idx, pfx = 206, 'window.GEOS='
assert lines[idx].startswith(pfx) and lines[idx].endswith(';')
G = json.loads(lines[idx][len(pfx):-1])
G['207seat'] = TRACED
G['207seat85'] = V85
lines[idx] = pfx + json.dumps(G, separators=(',', ':'), ensure_ascii=False) + ';'
txt = '\n'.join(lines)

def sub1(old, new):
    assert txt.count(old) == 1, f'want 1, got {txt.count(old)}: {old[:80]}'
    return txt.replace(old, new)

txt = sub1("'1985':{geo:'207seat',delim:'1985 non-party · 207-seat delim · map-traced',seats:207,postponed:[],prev:null}",
           "'1985':{geo:'207seat85',delim:'1985 non-party · 207-seat delim · reconstructed (approx, source numbering)',seats:207,postponed:[],prev:null}")
txt = sub1("'1988':{geo:'207seat',delim:'1985–1997 delimitation · map-traced',seats:207,postponed:[],prev:'1985'}",
           "'1988':{geo:'207seat',delim:'1985–1997 delimitation · map-traced',seats:207,postponed:[],prev:null}")

open(MAP, 'w', encoding='utf-8').write(txt)
print('finalized: GEOS 207seat swapped, 207seat85 added, 1985 repointed, 1988.prev cut')
print('map.html size:', len(txt) // 1024, 'KB')
