#!/usr/bin/env python3
"""
Cross-check our results against the labelled Commons maps.

The maps state each seat's NA number, so the join needs no georeferencing.
Colour-to-party is not given by a legend we can read, so we infer it: for each
fill colour, the party our data most often records as winner among seats shown
in that colour. Every seat that then disagrees with that mapping is a genuine
discrepancy between the two sources, and is reported.
"""
import json, io, collections, sys

MAPS = {'1993': 'Pakistan_General_election_1993_read.json',
        '1997': 'Pakistan_General_election_1997_read.json',
        '2002': 'Pakistan_General_election_2002_read.json',
        '2008': 'Pakistan_General_election_2008_read.json',
        '2013': 'Pakistan_General_election_2013_read.json'}

s = io.open('/mnt/user-data/uploads/Aiwan-e-Jamhoor/map.html', encoding='utf-8').read()
i = s.find('window.RESULTS='); j = s.index('{', i)
R, _ = json.JSONDecoder().raw_decode(s, j)
i2 = s.find('const PARTY_CAT=')
CAT = eval(s[i2 + len('const PARTY_CAT='):s.index('};', i2) + 1])
cat = lambda p: CAT.get(p, 'Other')

report = {}
for year, f in MAPS.items():
    try: m = json.load(open('/home/claude/' + f))
    except FileNotFoundError: continue
    ours = R.get(year, {})
    pairs = [(na, v['hex']) for na, v in m.items() if na in ours]
    # infer colour -> party category from the modal winner per colour
    byc = collections.defaultdict(collections.Counter)
    for na, hx in pairs: byc[hx][cat(ours[na]['wp'])] += 1
    key = {hx: c.most_common(1)[0][0] for hx, c in byc.items()}
    agree, dis = 0, []
    for na, hx in pairs:
        mine = cat(ours[na]['wp'])
        theirs = key[hx]
        if mine == theirs: agree += 1
        else: dis.append((na, ours[na]['name'], mine, theirs, hx))
    n = len(pairs)
    report[year] = {'checked': n, 'agree': agree,
                    'pct': round(100 * agree / n, 1) if n else 0,
                    'colours': {hx: (p, sum(byc[hx].values())) for hx, p in key.items()},
                    'dis': dis}

for y, r in report.items():
    print(f"\n===== {y} =====")
    print(f"  seats cross-checked : {r['checked']}  (of {len(R.get(y,{}))} in our data)")
    print(f"  agreement           : {r['agree']}/{r['checked']}  = {r['pct']}%")
    print(f"  colour key inferred : " + ', '.join(
        f"{hx}->{p} ({n})" for hx, (p, n) in sorted(r['colours'].items(), key=lambda x: -x[1][1])[:8]))
    if r['dis']:
        print(f"  disagreements ({len(r['dis'])}):")
        for na, nm, mine, theirs, hx in r['dis'][:14]:
            print(f"     {na:<8} {nm[:26]:<26} ours={mine:<16} map={theirs:<16} {hx}")
        if len(r['dis']) > 14: print(f"     ... and {len(r['dis'])-14} more")
json.dump({y: {k: v for k, v in r.items() if k != 'colours'} for y, r in report.items()},
          open('/home/claude/crosscheck.json', 'w'), indent=1)
