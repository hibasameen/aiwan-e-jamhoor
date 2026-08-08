#!/usr/bin/env python3
"""Career analysis from the linked spine: party switching, longest-serving, seat moves."""
import csv, json
from collections import defaultdict, Counter

OUT = '/home/claude/aej/out'
cands = list(csv.DictReader(open(f'{OUT}/candidacies_final.csv')))
persons = {p['person_id']: p for p in csv.DictReader(open(f'{OUT}/persons_final.csv'))}
YEARS = [1993, 1997, 2002, 2008, 2013, 2018, 2024]

# person -> year -> best candidacy (win preferred, else best rank)
py = defaultdict(dict)
for c in cands:
    c['year'] = int(c['year'])
    pid, y = c['person_id'], c['year']
    cur = py[pid].get(y)
    def score(r):
        try: rank = int(r['rank'])
        except: rank = 99
        return (0 if r['outcome']=='Win' else 1, rank)
    if cur is None or score(c) < score(cur):
        py[pid][y] = c

# all candidacies per person-year (for multi-seat)
py_all = defaultdict(lambda: defaultdict(list))
for c in cands:
    py_all[c['person_id']][c['year']].append(c)

# ---------------- longest serving (most GE wins) ----------------
longest = []
for pid, p in persons.items():
    wy = [y for y in py[pid] if py[pid][y]['outcome']=='Win']
    if len(wy) >= 3:
        seq = []
        for y in sorted(py[pid]):
            r = py[pid][y]
            seq.append(dict(year=y, na=r['na'], constituency=r['constituency'] or r['district'],
                            party=r['party'], outcome=r['outcome'],
                            multi=len([x for x in py_all[pid][y]])))
        longest.append(dict(person_id=pid, name=p['canonical_name'], ge_wins=len(wy),
                            win_years=sorted(wy), contested=sorted(py[pid]), seq=seq,
                            parties=sorted(set(s['party'] for s in seq))))
longest.sort(key=lambda d: (-d['ge_wins'], -len(d['contested'])))
print(f'persons with >=3 GE wins: {len(longest)}')
for d in longest[:15]:
    print(d['ge_wins'], d['name'], d['win_years'], d['parties'])

# ---------------- party switching ----------------
# person-level party sequence over contested GEs (party of best candidacy each year)
switches = []       # individual switch events between consecutive contested GEs
flow_pairs = defaultdict(Counter)   # (y1,y2) -> (party1->party2) counts, all candidates
flow_pairs_win = defaultdict(Counter)  # winners in y2
for pid in py:
    ys = sorted(py[pid])
    if len(ys) < 2: continue
    for a, b in zip(ys, ys[1:]):
        p1, p2 = py[pid][a]['party'], py[pid][b]['party']
        flow_pairs[(a,b)][(p1,p2)] += 1
        if py[pid][b]['outcome']=='Win': flow_pairs_win[(a,b)][(p1,p2)] += 1
        if p1 != p2:
            switches.append(dict(person_id=pid, name=persons[pid]['canonical_name'],
                y1=a, y2=b, from_party=p1, to_party=p2,
                won_before=py[pid][a]['outcome']=='Win', won_after=py[pid][b]['outcome']=='Win'))
print(f'switch events: {len(switches)}')
sw_win = [s for s in switches if s['won_after']]
print(f'switches that won after: {len(sw_win)}')
c = Counter((s['from_party'], s['to_party']) for s in sw_win)
print('top winning-switch flows:', c.most_common(15))

# consecutive-GE flows for adjacent pairs only (1993-97, 97-02, ...)
adj = {}
for (a,b), cnt in flow_pairs.items():
    if YEARS.index(b) - YEARS.index(a) == 1:
        adj[f'{a}-{b}'] = {f'{p1}>{p2}': n for (p1,p2), n in cnt.items()}

# serial switchers
per_person_switches = Counter(s['person_id'] for s in switches)
serial = []
for pid, n in per_person_switches.most_common(40):
    seq = [(y, py[pid][y]['party'], py[pid][y]['outcome']) for y in sorted(py[pid])]
    wins = sum(1 for _,_,o in seq if o=='Win')
    serial.append(dict(person_id=pid, name=persons[pid]['canonical_name'], n_switches=n,
                       wins=wins, seq=seq))
print('\nserial switchers (top 10):')
for s in serial[:10]:
    print(s['n_switches'], s['name'], s['seq'])

# loyalty rates by party: among candidates who contested consecutive GEs under party X, share who stayed
loyalty = {}
for (a,b), cnt in flow_pairs.items():
    if YEARS.index(b) - YEARS.index(a) != 1: continue
    for (p1,p2), n in cnt.items():
        if p1 in ('IND',): continue
        loyalty.setdefault(p1, Counter())
        loyalty[p1]['total'] += n
        if p1==p2: loyalty[p1]['stay'] += n
loy = {p: dict(stay=v['stay'], total=v['total'], rate=round(v['stay']/v['total'],3))
       for p,v in loyalty.items() if v['total']>=30}
print('\nparty retention (consecutive GEs, n>=30):')
for p,v in sorted(loy.items(), key=lambda kv:-kv[1]['rate']): print(' ',p,v)

# ---------------- seat switching (winners) ----------------
seat_moves = []
for pid in py:
    wins = [(y, py[pid][y]) for y in sorted(py[pid]) if py[pid][y]['outcome']=='Win']
    dists = set(r['district'] for _, r in wins if r['district'])
    if len(wins) >= 2 and len(dists) >= 2:
        seat_moves.append(dict(person_id=pid, name=persons[pid]['canonical_name'],
            moves=[(y, r['na'], r['district'], r['party']) for y, r in wins]))
print(f'\nwinners who won from >1 district: {len(seat_moves)}')
for s in seat_moves[:8]: print(' ', s['name'], s['moves'])

# ---------------- turnover / incumbency ----------------
turnover = {}
for a, b in zip(YEARS, YEARS[1:]):
    winners_a = set(pid for pid in py if a in py[pid] and py[pid][a]['outcome']=='Win')
    winners_b = set(pid for pid in py if b in py[pid] and py[pid][b]['outcome']=='Win')
    recon = [pid for pid in winners_a if b in py[pid]]           # incumbents who ran again
    rewon = [pid for pid in recon if py[pid][b]['outcome']=='Win']
    turnover[f'{a}-{b}'] = dict(winners=len(winners_a), ran_again=len(recon),
        rewon=len(rewon), reelection_rate=round(len(rewon)/max(1,len(recon)),3),
        newcomers=len([pid for pid in winners_b if all(y >= b for y in py[pid])]))
print('\nincumbency:', json.dumps(turnover, indent=1))

json.dump(dict(longest=longest, switches=switches, serial=serial[:40], adjacent_flows=adj,
               loyalty=loy, seat_moves=seat_moves, turnover=turnover),
          open(f'{OUT}/career.json','w'), indent=1)
print('\nwrote career.json')
