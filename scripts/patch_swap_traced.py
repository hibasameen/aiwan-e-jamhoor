#!/usr/bin/env python3
"""
Swap the all-Voronoi GEOS['207seat'] in map.html for the map-traced boundary set
(176 traced from the 1990/93/97 Commons maps + 31 reconstructed fallbacks), and
update the 1985-1997 delimitation captions. Asserts + backup.
"""
import json, re, time

TR = json.load(open('data/boundaries/na_207seat_1985-1997_traced.geojson'))
for f in TR['features']:                       # add prov (range-based, 207-seat)
    n = int(f['properties']['na'].split('-')[1])
    f['properties']['prov'] = ('Khyber Pakhtunkhwa' if n <= 26 else 'FATA' if n <= 34 else
        'Islamabad Capital Territory' if n == 35 else 'Punjab' if n <= 150 else
        'Sindh' if n <= 196 else 'Balochistan')

MAP = 'map.html'
lines = open(MAP, encoding='utf-8').read().split('\n')
open(f'{MAP}.bak_{int(time.time())}', 'w', encoding='utf-8').write('\n'.join(lines))

idx, pfx = 206, 'window.GEOS='
assert lines[idx].startswith(pfx) and lines[idx].endswith(';')
G = json.loads(lines[idx][len(pfx):-1])
G['207seat'] = TR
lines[idx] = pfx + json.dumps(G, separators=(',', ':'), ensure_ascii=False) + ';'
txt = '\n'.join(lines)

def sub1(old, new):
    assert txt.count(old) == 1, f'want 1, got {txt.count(old)}: {old[:70]}'
    return txt.replace(old, new)

TR_CAP = '1985–1997 delimitation · map-traced'
txt = sub1("delim:'1985–1997 delimitation · reconstructed (approx)',seats:207,postponed:[],prev:'1985'}",
           f"delim:'{TR_CAP}',seats:207,postponed:[],prev:'1985'}}")       # 1988
for yr, prev in (('1990', '1988'), ('1993', '1990'), ('1997', '1993')):
    txt = sub1(f"'{yr}':{{geo:'207seat',delim:'1985–1997 delimitation · reconstructed (approx)',seats:207,postponed:[],prev:'{prev}'}}",
               f"'{yr}':{{geo:'207seat',delim:'{TR_CAP}',seats:207,postponed:[],prev:'{prev}'}}")
txt = sub1("delim:'1985 non-party · 207-seat delim · reconstructed (approx)'",
           "delim:'1985 non-party · 207-seat delim · map-traced'")

open(MAP, 'w', encoding='utf-8').write(txt)
appx = sorted(int(f['properties']['na'].split('-')[1]) for f in TR['features'] if f['properties']['approx'])
print(f"swapped GEOS['207seat'] -> {len(TR['features'])} traced seats ({len(appx)} reconstructed fallbacks)")
print("map.html size now:", len(txt)//1024, "KB")
