#!/usr/bin/env python3
"""
Rebuild the 1977 (200-seat) and 1985 (own-numbering 207-seat) Voronoi layers with
full era coverage, then swap them into map.html.

Why: the original 1977 build expanded only Punjab/Sindh districts, leaving ~47% of
the country uncovered (nearly all of Balochistan, the KP carve-outs, the Tando
districts...). The 1985 layer still missed Chakwal / Khanewal / Swabi / Charsadda —
districts created around 1985 that its (source-numbered) names never mention.

Era logic added here:
 * EXTRA common to both eras: Peshawar+=Charsadda (carved 1988), Mardan+=Swabi
   (1988), Jhelum+=Chakwal (1985; Chakwal came mainly from Jhelum, partly Attock —
   assigned to Jhelum, documented approximation), Multan+=Khanewal (1985).
 * 1977 only: Kohat+=Karak (1982), Sargodha+=Khushab (1982), Sukkur+=Shikarpur
   (1977), Muzaffargarh includes Layyah (1982) via the old crosswalk already.
 * 1977 Balochistan had just 7 seats labelled Quetta/Sibi/Kalat — they covered the
   whole DIVISIONS. Overridden by seat number to the divisions' modern districts.
 * Tribal seats get the FR regions alongside the 7 agencies.
"""
import json, csv, time
import sys; sys.path.insert(0, 'scripts')
import build_reconstructed_geometry as brg
from build_map_numbering import EXPAND88, expand, TN

DIST = brg.load_districts()
FRS = ['FR Peshawar', 'FR Kohat', 'FR Bannu', 'FR Lakki Marwat', 'FR DI Khan', 'FR Tank']
Q_DIV = ['Quetta', 'Pishin', 'Killa Abdullah', 'Chaghi', 'Nushki', 'Loralai',
         'Barkhan', 'Musakhail', 'Zhob', 'Killa Saifullah', 'Sherani']
S_DIV = ['Sibi', 'Ziarat', 'Harnai', 'Lehri', 'Kohlu', 'Dera Bugti', 'Kachhi',
         'Jhal Magsi', 'Nasirabad', 'Jaffarabad', 'Sohbatpur']
K_DIV = ['Kalat', 'Mastung', 'Khuzdar', 'Awaran', 'Kharan', 'Washuk', 'Lasbela',
         'Kech', 'Panjgur', 'Gwadar']
EXTRA_BOTH = {'Peshawar': ['Charsadda'], 'Mardan': ['Swabi'],
              'Jhelum': ['Chakwal'], 'Multan': ['Khanewal']}
EXTRA_77 = {'Kohat': ['Karak'], 'Sargodha': ['Khushab'], 'Sukkur': ['Shikarpur']}

def apply_extra(ds, extra):
    out = list(ds)
    for d in ds:
        for e in extra.get(d, []):
            if e in TN and e not in out: out.append(e)
    return out

def load_xw(path):
    return {r['na']: r['districts'].split(';') for r in csv.DictReader(open(path))}

def coverage_check(xw, label):
    covered = {d for ds in xw.values() for d in ds}
    AJK_GB = {'Astor','Bagh','Bhimber','Diamir','Ghanchi','Ghizer','Gilgit','Hattian','Haveli',
              'Hunza Nagar','Kotli','Mirpur','Muzaffarabad','Neelum','Poonch','Skardu','Sudhnutti'}
    missing = [d for d in DIST if d not in covered and d not in AJK_GB]
    print(f'{label}: unclaimed districts -> {missing or "NONE"}')
    return missing

# ---------- 1977 ----------
x77 = load_xw('data/results_1977/na_1977_seat_districts.csv')
for na, ds in x77.items():
    n = int(na.split('-')[1])
    if 194 <= n <= 196: x77[na] = list(Q_DIV); continue
    if 197 <= n <= 198: x77[na] = list(S_DIV); continue
    if 199 <= n <= 200: x77[na] = list(K_DIV); continue
    ds = expand(ds)                       # EXPAND88 era carve-outs
    ds = apply_extra(ds, EXTRA_BOTH)
    ds = apply_extra(ds, EXTRA_77)
    if 27 <= n <= 34:                     # tribal seats: agencies + FRs
        ds = ds + [f for f in FRS if f not in ds]
    x77[na] = ds
assert not coverage_check(x77, '1977'), '1977 still has unclaimed districts'
feats77 = brg.build(x77, DIST)
brg.write([{**f, 'approx': True} for f in feats77], x77,
          'data/boundaries/na_200seat_1977_reconstructed.geojson')

# ---------- 1985 ----------
x85 = load_xw('data/results_1985/na_1985_seat_districts.csv')
for na, ds in x85.items():
    n = int(na.split('-')[1])
    ds = expand(ds)
    ds = apply_extra(ds, EXTRA_BOTH)
    if 27 <= n <= 34:
        ds = ds + [f for f in FRS if f not in ds]
    x85[na] = ds
for na, extra in (('NA-197', ['Chaghi', 'Nushki']), ('NA-206', ['Gwadar']),
                  ('NA-203', ['Nasirabad', 'Jaffarabad', 'Sohbatpur'])):
    for d in extra:
        if d in TN and d not in x85[na]: x85[na].append(d)
assert not coverage_check(x85, '1985'), '1985 still has unclaimed districts'
feats85 = brg.build(x85, DIST)
brg.write([{**f, 'approx': True} for f in feats85], x85,
          'data/boundaries/na_207seat_1985numbering_reconstructed.geojson')

# ---------- swap into map.html ----------
def load_geo(path, seats200):
    gj = json.load(open(path))
    for f in gj['features']:
        n = int(f['properties']['na'].split('-')[1])
        f['properties']['prov'] = ('Khyber Pakhtunkhwa' if n <= 26 else 'FATA' if n <= 34 else
            'Islamabad Capital Territory' if n == 35 else 'Punjab' if n <= 150 else
            'Sindh' if n <= (193 if seats200 else 196) else 'Balochistan')
    return gj

def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o

G77 = load_geo('data/boundaries/na_200seat_1977_reconstructed.geojson', True)
G85 = load_geo('data/boundaries/na_207seat_1985numbering_reconstructed.geojson', False)
for gj in (G77, G85):
    for f in gj['features']: f['geometry'] = rnd(f['geometry'])

lines = open('map.html', encoding='utf-8').read().split('\n')
open(f'map.html.bak_{int(time.time())}', 'w', encoding='utf-8').write('\n'.join(lines))
pfx = 'window.GEOS='
assert lines[206].startswith(pfx) and lines[206].endswith(';')
G = json.loads(lines[206][len(pfx):-1])
G['200seat'] = G77
G['207seat85'] = G85
lines[206] = pfx + json.dumps(G, separators=(',', ':'), ensure_ascii=False) + ';'
open('map.html', 'w', encoding='utf-8').write('\n'.join(lines))
print('swapped 200seat + 207seat85 into map.html;', len('\n'.join(lines)) // 1024, 'KB')
