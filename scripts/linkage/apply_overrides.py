#!/usr/bin/env python3
"""Apply agent-verified splits and merges to the spine; rebuild persons; emit dynasties.json."""
import csv, json
from collections import defaultdict, Counter

OUT = '/home/claude/aej/out'
SL = '/home/claude/aej/scripts_link'
ov = json.load(open(f'{SL}/overrides.json'))
cands = list(csv.DictReader(open(f'{OUT}/candidacies.csv')))

# ---- splits first ----
new_pid_counter = [0]
def fresh_pid():
    new_pid_counter[0] += 1
    return f'PX{new_pid_counter[0]:03d}'

split_map = {}  # (old_pid, split_index) handled per rule
for rule in ov['splits']:
    pid = rule['person_id']; m = rule['match']
    tgt = rule.get('merge_into')
    npid = tgt if tgt else fresh_pid()
    n = 0
    for c in cands:
        if c['person_id'] != pid: continue
        okm = True
        if 'year' in m and c['year'] != m['year']: okm = False
        if 'district' in m and c['district'] != m['district']: okm = False
        if 'district_contains' in m and m['district_contains'] not in c['district']: okm = False
        if 'name_contains' in m and m['name_contains'] not in c['name_core']: okm = False
        if okm:
            c['person_id'] = npid; n += 1
    print(f"split {pid} -> {npid}: {n} rows ({rule['why'][:50]})")

# ---- merges (union-find over pids) ----
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for mr in ov['merges']:
    ids = mr['ids']
    for b in ids[1:]:
        ra, rb = find(ids[0]), find(b)
        if ra != rb: parent[rb] = ra
pid_map = {}
for c in cands:
    p = c['person_id']
    c['person_id'] = find(p)
    pid_map[p] = c['person_id']

# ---- rebuild persons ----
groups = defaultdict(list)
for c in cands: groups[c['person_id']].append(c)
persons = []
for pid, members in groups.items():
    wins = [m for m in members if m['outcome']=='Win']
    pool = wins if wins else members
    canon = Counter(m['name_raw'] for m in pool).most_common(1)[0][0]
    years = sorted(set(int(m['year']) for m in members))
    win_years = sorted(set(int(m['year']) for m in wins))
    persons.append(dict(person_id=pid, canonical_name=canon, n_candidacies=len(members),
        n_wins=len(wins), n_win_years=len(win_years), win_years='|'.join(map(str,win_years)),
        years='|'.join(map(str,years)),
        parties='|'.join(sorted(set(m['party'] for m in members))),
        districts='|'.join(sorted(set(m['district'] for m in members if m['district']))),
        provinces='|'.join(sorted(set(m['province'] for m in members if m['province']))) ))
print(f'persons after overrides: {len(persons)}')

with open(f'{OUT}/candidacies_final.csv','w',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(cands[0].keys())); w.writeheader(); w.writerows(cands)
with open(f'{OUT}/persons_final.csv','w',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(persons[0].keys())); w.writeheader(); w.writerows(persons)

# ---- dynasties.json ----
dyn = json.load(open(f'{SL}/dynasties_verified.json'))
pinfo = {p['person_id']: p for p in persons}
out_fams = []
for fam in dyn:
    nodes = {}
    edges = []
    for seed in fam.get('seeds', []):
        sp = find(pid_map.get(seed, seed))
        pi = pinfo.get(sp)
        if pi:
            nodes[sp] = dict(id=sp, name=pi['canonical_name'], wins=int(pi['n_wins']),
                win_years=pi['win_years'], years=pi['years'], parties=pi['parties'], districts=pi['districts'][:60])
    for e in fam['edges']:
        a, b = pid_map.get(e['a'], e['a']), pid_map.get(e['b'], e['b'])
        a, b = find(a), find(b)
        for pid in (a, b):
            if pid not in nodes:
                pi = pinfo.get(pid)
                if pi:
                    nodes[pid] = dict(id=pid, name=pi['canonical_name'], wins=int(pi['n_wins']),
                        win_years=pi['win_years'], years=pi['years'], parties=pi['parties'],
                        districts=pi['districts'][:60])
                else:
                    nodes[pid] = dict(id=pid, name=f'({pid} not found)', wins=0, win_years='', years='', parties='', districts='')
        if a != b:
            edges.append(dict(a=a, b=b, rel=e['rel'], note=e['note'], src=e['src']))
    out_fams.append(dict(family=fam['family'], base=fam['base'], notes=fam['notes'],
                         nodes=list(nodes.values()), edges=edges,
                         total_wins=sum(n['wins'] for n in nodes.values())))
json.dump(out_fams, open(f'{OUT}/dynasties.json','w'), indent=1)
missing = [n['name'] for f in out_fams for n in f['nodes'] if 'not found' in n['name']]
print('families:', len(out_fams), 'edges:', sum(len(f['edges']) for f in out_fams),
      'nodes:', sum(len(f['nodes']) for f in out_fams))
print('missing pids:', missing)
