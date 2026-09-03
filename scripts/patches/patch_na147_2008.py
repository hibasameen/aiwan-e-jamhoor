#!/usr/bin/env python3
"""
Correction: GE-2008 NA-147 Okara-V winner.

Cookman's 2008 file (and therefore results_all.json, map.html, candidates.html and
the spine) names the winner "Muhammad Zafar Yasin Wattoo" with 84,778 votes. The
votes are right; the name is not. Mian Manzoor Ahmad Khan Wattoo won BOTH NA-146
(46,941) and NA-147 (84,778) on 18 Feb 2008 as an independent, kept NA-146 and
vacated NA-147; in the by-election that followed his son Khurram Jahangir Wattoo
(PPP, 79,195) beat Zafar Yasin Wattoo (IND, 15,965) — the contest that
ElectionPakistani shows in place of the general-election result, which is how
the reader's correction (@megadelusion, 14 Aug 2026) arose.

Evidence: Geo TV 2008 result page for NA-147 (winner "Mian Manzoor Ahmed Wattoo",
Independent, 83,412 provisional; same candidate list as Cookman); NA 13th-Assembly
roll (NA-146 Manzoor Wattoo, NA-147 Khuram Jehangir Wattoo, PPPP); Wikipedia
"Khurram Jahangir Wattoo" citing ECP GE-2008 report Vol. II for the by-election
figures; ElectionPakistani ge2008/NA-147.htm.

Applied in place (idempotent, asserts on every anchor):
  data/linked/candidacies_final.csv  name fields + person_id -> P01417 (Manzoor Wattoo)
  data/linked/persons_final.csv      drop P04634; P01417 n_candidacies 9, n_wins 2
  data/linked/family_clusters.csv    drop P04634 from cluster F0018
  data/results_all.json, data/results_2008_2013.json, map.html, candidates.html
  then: python3 scripts/house/build_house.py && python3 scripts/house/build_house_page.py
"""
import csv, json, os, re
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
os.chdir(ROOT)
OLD, NEW = 'Muhammad Zafar Yasin Wattoo', 'Mian Manzoor Ahmad Khan Wattoo'

# 1. spine
rows = list(csv.DictReader(open('data/linked/candidacies_final.csv', encoding='utf-8')))
fields = rows[0].keys()
tgt = [r for r in rows if r['year'] == '2008' and r['na'] == 'NA-147' and r['rank'] == '1']
ref = [r for r in rows if r['year'] == '2008' and r['na'] == 'NA-146' and r['rank'] == '1']
assert len(tgt) == 1 and len(ref) == 1
t, m = tgt[0], ref[0]
if t['name_raw'] == OLD:
    for k in ('name_raw', 'name_full', 'name_core', 'name_squash', 'name_distinct'): t[k] = m[k]
    t['person_id'] = 'P01417'; t['src'] = t['src'] + '+corr2026-09'
    with open('data/linked/candidacies_final.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print('candidacies_final: corrected')
else:
    print('candidacies_final: already corrected')

prs = list(csv.DictReader(open('data/linked/persons_final.csv', encoding='utf-8')))
pf = prs[0].keys()
if any(p['person_id'] == 'P04634' for p in prs):
    prs = [p for p in prs if p['person_id'] != 'P04634']
    p = next(p for p in prs if p['person_id'] == 'P01417')
    p['n_candidacies'] = str(int(p['n_candidacies']) + 1); p['n_wins'] = str(int(p['n_wins']) + 1)
    with open('data/linked/persons_final.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=pf); w.writeheader(); w.writerows(prs)
    print('persons_final: P04634 removed, P01417 updated')

fc = open('data/linked/family_clusters.csv', encoding='utf-8').read()
if 'P04634' in fc:
    fc = fc.replace('Muhammad Zafar Yasin Wattoo (1W/1C, IND); ', '').replace('|P04634', '').replace('P04634|', '')
    # F0018 counts: members 6->5, wins 1->0, winners 1->0
    fc = re.sub(r'(F0018,yasin,[^,]+,)6,1,1,', r'\g<1>5,0,0,', fc)
    open('data/linked/family_clusters.csv', 'w', encoding='utf-8').write(fc); print('family_clusters: updated')

# 2. results + pages (the name occurs only in this seat's record)
for f in ['data/results_all.json', 'data/results_2008_2013.json', 'map.html']:
    s = open(f, encoding='utf-8').read()
    n = s.count(OLD)
    if n:
        assert n == 2, (f, n)
        open(f, 'w', encoding='utf-8').write(s.replace(OLD, NEW)); print(f, 'corrected')

f = 'candidates.html'; s = open(f, encoding='utf-8').read()
a = '"P04634":{"n":"Muhammad Zafar Yasin Wattoo","w":1,"c":[[2008,"NA-147","okara","IND","84778","1",1]]},'
if a in s:
    s = s.replace(a, '')
    b = '"P01417":{"n":"Mian Manzoor Ahmad Khan Wattoo","w":1,"c":[[1997,"NA-112","okara","PML-H","26449","2",0],[1997,"NA-113","okara","PML-H","46403","2",0],[2008,"NA-146","okara","IND","46941","1",1],'
    assert s.count(b) == 1
    s = s.replace(b, '"P01417":{"n":"Mian Manzoor Ahmad Khan Wattoo","w":2,"c":[[1997,"NA-112","okara","PML-H","26449","2",0],[1997,"NA-113","okara","PML-H","46403","2",0],[2008,"NA-146","okara","IND","46941","1",1],[2008,"NA-147","okara","IND","84778","1",1],')
    open(f, 'w', encoding='utf-8').write(s); print('candidates.html corrected')
print('done — now rebuild house: scripts/house/build_house.py && build_house_page.py')
