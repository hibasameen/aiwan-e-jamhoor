#!/usr/bin/env python3
"""
Project the 1993 and 1997 district-level results onto the 2002-delimitation
constituencies by areal apportionment.

For each 2002 seat X and each 1993/97 district unit U that it overlaps, the
share of U assumed to fall inside X is area(X n U) / area(U). That share of U's
registered electorate is attributed to the parties in proportion to the seats
they won in U. Summing over all overlapping units gives a party weighting for
X; the largest wins the fill.

The assumption is uniform electorate density within each source district. It is
exact where a 2002 seat sits inside one district (most of Punjab and Sindh) and
weakest in Balochistan, where 2002 seats span several sparsely populated ones.
"""
import json, io, collections
from shapely.geometry import shape
from shapely import make_valid

C2002 = 'data/na_constituencies_2002delim.geojson'
UNITS = 'data/districts_1990s.geojson'
RES   = 'data/districts_1990s_results.json'

seats = {f['properties']['na']: make_valid(shape(f['geometry']))
         for f in json.load(io.open(C2002, encoding='utf-8'))['features']}
uf  = json.load(io.open(UNITS, encoding='utf-8'))['features']
res = json.load(open(RES))

xw, report = {}, {}
for y in ('1993', '1997'):
    units = {}
    for f in uf:
        p = f['properties']
        if p['y'] in ('*', y):
            g = make_valid(shape(f['geometry']))
            units[p['u']] = units[p['u']].union(g) if p['u'] in units else g
    ub = {u: g.bounds for u, g in units.items()}

    out, exact, blended, touched = {}, 0, 0, set()
    for na, sg in seats.items():
        sb, w = sg.bounds, collections.Counter()
        parts = []
        for u, g in units.items():
            r = res[y].get(u)
            if not r or r.get('noPoll'): continue
            b = ub[u]
            if b[0] > sb[2] or b[2] < sb[0] or b[1] > sb[3] or b[3] < sb[1]: continue
            try: a = sg.intersection(g).area
            except Exception: continue
            if a <= 0: continue
            frac = a / g.area                      # share of the district inside this seat
            elect = (r['reg'] or 0) * frac         # its electorate, apportioned
            if elect <= 0: continue
            touched.add(u)
            for party, n in r['tally']:
                w[party] += elect * (n / r['seats'])
            parts.append((u, elect))
        if not w:
            out[na] = None; continue
        tot = sum(w.values())
        top, tw = w.most_common(1)[0]
        parts.sort(key=lambda x: -x[1])
        src = [p[0] for p in parts[:3]]
        purity = round(100 * tw / tot, 1)
        single = len(parts) == 1 or (parts[0][1] / sum(p[1] for p in parts) > 0.97)
        exact += single; blended += (not single)
        out[na] = {'wp': top, 'pur': purity, 'src': src, 'n': len(parts), 'one': single}
    xw[y] = out
    withres = {u for u in res[y] if not res[y][u].get('noPoll')}
    report[y] = {'seatsFilled': sum(1 for v in out.values() if v),
                 'noData': [k for k, v in out.items() if not v],
                 'singleDistrict': exact, 'blended': blended,
                 'districtsUnused': sorted(withres - touched),
                 'lowPurity': sorted([(k, v['pur'], v['src'][:2]) for k, v in out.items()
                                      if v and v['pur'] < 40], key=lambda x: x[1])[:8]}

for y in ('1993', '1997'):
    r = report[y]
    print(f"\n{y}: filled {r['seatsFilled']}/{len(seats)} 2002 seats"
          f" | wholly inside one district {r['singleDistrict']}"
          f" | spanning several {r['blended']}")
    print(f"   districts whose result is used nowhere: {r['districtsUnused']}")
    print(f"   seats with no data: {r['noData']}")
    print(f"   least decisive fills (winning weight <40%): {r['lowPurity']}")

json.dump(xw, open('data/na2002_from_1990s.json', 'w'), separators=(',', ':'))
print(f"\nwrote xwalk.json ({round(len(json.dumps(xw))/1e6,3)} MB)")
