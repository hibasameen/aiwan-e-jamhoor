#!/usr/bin/env python3
"""Leg 2 driver: upgrade all KP + FATA + ICT 2018 seats in na_2018delim_v2.geojson.

Single-seat groups -> harmonized geoBoundaries unions (FR strips carved from the
gb districts that contain them, along 2015 FR lines; NA-51 = union of the six FRs).
Multi-seat groups -> sheet-split via scripts/split_district_by_sheet.py, with
fallback to the existing (Voronoi) feature on failure.
"""
import json, sys
sys.path.insert(0, 'scripts')
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import make_valid
from split_district_by_sheet import split_district

SHEET_DIR = '/mnt/user-data/uploads/Aiwan-e-Jamhoor/2018 Delimitation'

gb = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
      for f in json.load(open('data/gb_PAK_ADM2.geojson'))['features']}
old = json.load(open('data/districts_2015.geojson'))
d15 = {}
for f in old['features']:
    g = make_valid(shape(f['geometry']))
    n = f['properties']['districts']
    d15[n] = unary_union([d15[n], g]) if n in d15 else g

# ---- carve FR strips out of gb districts ----
FRS = ['FR Peshawar', 'FR Kohat', 'FR Bannu', 'FR Lakki Marwat', 'FR Tank', 'FR DI Khan']
FR_2015 = {}
for fr in FRS:
    cands = [k for k in d15 if k.replace('.', '').replace(' ', '').lower() == fr.replace('.', '').replace(' ', '').lower()]
    if not cands:
        cands = [k for k in d15 if k.lower().startswith('fr') and fr.split()[-1].lower() in k.lower()]
    if not cands:
        print('WARN no 2015 polygon for', fr); continue
    FR_2015[fr] = d15[cands[0]]
harm = dict(gb)
for fr, g in FR_2015.items():
    for name in list(harm):
        if harm[name].intersects(g):
            ov = harm[name].intersection(g)
            if ov.area > 0.2 * g.area or ov.area > 0.001:
                harm[name] = make_valid(harm[name].difference(g.buffer(0.005)))

GBN = {'Batagram': 'Battagram', 'Bajaur Agency': 'Bajaur', 'Khyber Agency': 'Khyber',
       'Kurram Agency': 'Kurram', 'Mohmand Agency': 'Mohmand', 'Orakzai Agency': 'Orakzai',
       'North Waziristan Agency': 'North Waziristan', 'South Waziristan Agency': 'South Waziristan',
       'Islamabad': 'Islamabad Capital Territory', 'Lower Dir': 'Lower Dir', 'Upper Dir': 'Upper Dir'}
def H(name):
    return harm[GBN.get(name, name)]

SINGLES = {  # na -> district
 'NA-1': 'Chitral', 'NA-5': 'Upper Dir', 'NA-8': 'Malakand', 'NA-9': 'Buner', 'NA-10': 'Shangla',
 'NA-11': 'Kohistan', 'NA-12': 'Batagram', 'NA-17': 'Haripur', 'NA-32': 'Kohat', 'NA-33': 'Hangu',
 'NA-34': 'Karak', 'NA-35': 'Bannu', 'NA-36': 'Lakki Marwat', 'NA-37': 'Tank',
 'NA-42': 'Mohmand Agency', 'NA-47': 'Orakzai Agency', 'NA-48': 'North Waziristan Agency'}

MULTIS = [  # (district-for-gb, sheet path, seats)  legend hue words supplied inline
 ('Swat', 'KPK/pa24.jpg', {'NA-2': 'green', 'NA-3': 'salmon-pink', 'NA-4': 'pale yellow'}),
 ('Lower Dir', 'KPK/pa8.jpg', {'NA-6': 'pale green', 'NA-7': 'pink'}),
 ('Mansehra', 'KPK/pa17.jpg', {'NA-13': 'green', 'NA-14': 'cream'}),
 ('Abbottabad', 'KPK/pa1.jpg', {'NA-15': 'chartreuse', 'NA-16': 'teal'}),
 ('Swabi', 'KPK/pa23.jpg', {'NA-18': 'pale green', 'NA-19': 'pink'}),
 ('Mardan', 'KPK/pa18.jpg', {'NA-20': 'pale green', 'NA-21': 'light blue', 'NA-22': 'pink'}),
 ('Charsadda', 'KPK/pa5.jpg', {'NA-23': 'pale green', 'NA-24': 'orange'}),
 ('Nowshera', 'KPK/pa19.jpg', {'NA-25': 'light blue', 'NA-26': 'pale green'}),
 ('Peshawar', 'KPK/pa20.jpg', {'NA-27': 'tan', 'NA-28': 'pale green', 'NA-29': 'pink', 'NA-30': 'light blue', 'NA-31': 'salmon'}),
 ('Dera Ismail Khan', 'KPK/pa7.jpg', {'NA-38': 'pale green', 'NA-39': 'salmon-pink'}),
 ('Bajaur Agency', 'FATA/Bajaur Agency.jpg', {'NA-40': 'pale green', 'NA-41': 'crimson'}),
 ('Khyber Agency', 'FATA/Khyber Agency.jpg', {'NA-43': 'light green', 'NA-44': 'orange'}),
 ('Kuram Agency', 'FATA/Kuram Agency.jpg', {'NA-45': 'blue', 'NA-46': 'pink'}),
 ('South Waziristan Agency', 'FATA/South Waziristan Agency.jpg', {'NA-49': 'orange-tan', 'NA-50': 'yellow'}),
 ('Islamabad', 'Federal Capital Territory/Islamabad.jpg', {'NA-52': 'pink', 'NA-53': 'orange', 'NA-54': 'purple'}),
]
KURAM_GB = {'Kuram Agency': 'Kurram Agency'}  # sheet-name vs gb-name quirk

results = {}
report = []
for na, dname in SINGLES.items():
    if na == 'NA-51':
        continue
    g = H(dname)
    results[na] = (g, f'district-exact union (geoBoundaries ADM2, FR-carved)')
results['NA-51'] = (make_valid(unary_union(list(FR_2015.values()))),
                    'district-exact union (six FR strips, 2015 layer)')

for dname, sheetrel, seats in MULTIS:
    gbd = H(KURAM_GB.get(dname, dname))
    legend = [{'na': k, 'colour': v} for k, v in seats.items()]
    try:
        feats, rms = split_district(f'{SHEET_DIR}/{sheetrel}', legend, gbd)
        got = set(feats)
        if got != set(seats):
            raise RuntimeError(f'seat mismatch {got ^ set(seats)}')
        for na, g in feats.items():
            if g.is_empty:
                raise RuntimeError(f'{na} empty')
        for na, g in feats.items():
            results[na] = (g, f'sheet-split: {sheetrel}, outline-fit rms {rms:.1f}km')
        report.append((dname, 'OK', f'rms {rms:.1f}km'))
    except Exception as e:
        report.append((dname, 'FALLBACK-voronoi', str(e)[:80]))

v2 = json.load(open('data/na_2018delim_v2.geojson'))
for f in v2['features']:
    na = f['properties']['na']
    if na in results:
        g, src = results[na]
        f['properties'] = {'na': na, 'dist': f['properties'].get('dist', ''), 'approx': 'sheet-split' not in src and na not in SINGLES and na != 'NA-51',
                           'src': src}
        f['properties']['approx'] = False if ('sheet-split' in src or 'district-exact' in src) else True
        f['geometry'] = mapping(make_valid(g).simplify(0.0015))
json.dump(v2, open('data/na_2018delim_v2.geojson', 'w'))
print('=== report ===')
for r in report:
    print(*r)
print('updated seats:', len(results))
