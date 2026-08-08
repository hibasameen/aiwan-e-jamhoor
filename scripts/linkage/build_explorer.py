#!/usr/bin/env python3
"""Assemble the self-contained careers & dynasties explorer HTML."""
import csv, json

OUT = '/home/claude/aej/out'
SL = '/home/claude/aej/scripts_link'

career = json.load(open(f'{OUT}/career.json'))
dyn = json.load(open(f'{OUT}/dynasties.json'))

# compact per-person careers for search
persons = list(csv.DictReader(open(f'{OUT}/persons_final.csv')))
cands = list(csv.DictReader(open(f'{OUT}/candidacies_final.csv')))
car = {}
for c in cands:
    pid = c['person_id']
    car.setdefault(pid, []).append([int(c['year']), c['na'], c['district'], c['party'],
        c['votes'] or '', c['rank'] or '', 1 if c['outcome']=='Win' else 0])
people = {}
for p in persons:
    pid = p['person_id']
    rows = sorted(car.get(pid, []))
    people[pid] = {'n': p['canonical_name'], 'w': int(p['n_wins']), 'c': rows}

# trim career.json parts we embed
embed_career = dict(
    longest=career['longest'][:60],
    serial=career['serial'][:25],
    loyalty=career['loyalty'],
    seat_moves=sorted(career['seat_moves'], key=lambda s: -len(s['moves']))[:40],
    turnover=career['turnover'],
    top_win_switches=None,
)
from collections import Counter
sw = career['switches']
winsw = Counter((s['from_party'], s['to_party']) for s in sw if s['won_after'])
embed_career['top_win_switches'] = [[a, b, n] for (a, b), n in winsw.most_common(18)]
allsw = Counter((s['from_party'], s['to_party']) for s in sw)
embed_career['top_all_switches'] = [[a, b, n] for (a, b), n in allsw.most_common(18)]
# per-pair switch counts summary
pair_tot = Counter()
for s in sw:
    pair_tot[f"{s['y1']}-{s['y2']}"] += 1
embed_career['switch_pairs'] = dict(pair_tot)

stats = dict(
    candidacies=len(cands), persons=len(people),
    multi=sum(1 for p in persons if '|' in p['years']),
    multiwin=sum(1 for p in persons if int(p['n_win_years'])>1),
    families=len(dyn), edges=sum(len(f['edges']) for f in dyn),
    dyn_wins=sum(f['total_wins'] for f in dyn),
    switch_events=len(sw),
)

tpl = open(f'{SL}/explorer_template.html').read()
html = (tpl.replace('/*__CAREER__*/null', json.dumps(embed_career))
           .replace('/*__DYN__*/null', json.dumps(dyn))
           .replace('/*__PEOPLE__*/null', json.dumps(people, separators=(',',':')))
           .replace('/*__STATS__*/null', json.dumps(stats)))
open(f'{OUT}/aiwan_careers_dynasties.html','w').write(html)
print('wrote explorer,', len(html)/1e6, 'MB; stats:', stats)
