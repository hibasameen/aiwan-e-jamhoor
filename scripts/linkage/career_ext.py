#!/usr/bin/env python3
"""Career analysis over the 1977-2024 extended spine. 1985 (non-party) is excluded
from party-based analytics (retention, switch flows) but kept in careers/turnover."""
import csv, json
from collections import defaultdict, Counter

BASE='/sessions/eloquent-zen-cori/mnt/outputs/aej'
cands=list(csv.DictReader(open(f'{BASE}/out/candidacies_ext.csv')))
persons={p['person_id']:p for p in csv.DictReader(open(f'{BASE}/out/persons_ext.csv'))}
YEARS=[1977,1985,1988,1990,1993,1997,2002,2008,2013,2018,2024]
PARTYLESS={1985}

py=defaultdict(dict)
for c in cands:
    c['year']=int(c['year']); pid,y=c['person_id'],c['year']
    cur=py[pid].get(y)
    def score(r):
        try: rank=int(r['rank'])
        except: rank=99
        return (0 if r['outcome']=='Win' else 1, rank)
    if cur is None or score(c)<score(cur): py[pid][y]=c
py_all=defaultdict(lambda: defaultdict(list))
for c in cands: py_all[c['person_id']][c['year']].append(c)

# longest careers
longest=[]
for pid,p in persons.items():
    wy=[y for y in py[pid] if py[pid][y]['outcome']=='Win']
    if len(wy)>=3:
        seq=[dict(year=y,na=py[pid][y]['na'],constituency=py[pid][y]['constituency'] or py[pid][y]['district'],
                  party=py[pid][y]['party'],outcome=py[pid][y]['outcome'],multi=len(py_all[pid][y]))
             for y in sorted(py[pid])]
        longest.append(dict(person_id=pid,name=p['canonical_name'],ge_wins=len(wy),
            win_years=sorted(wy),contested=sorted(py[pid]),seq=seq,
            parties=sorted(set(s['party'] for s in seq))))
longest.sort(key=lambda d:(-d['ge_wins'],-len(d['contested'])))
print('persons with >=3 GE wins:',len(longest))
for d in longest[:12]: print(d['ge_wins'],d['name'],d['win_years'],d['parties'])

# party switching (skip pairs touching 1985)
switches=[]; flow_pairs=defaultdict(Counter)
for pid in py:
    ys=sorted(py[pid])
    for a,b in zip(ys,ys[1:]):
        if a in PARTYLESS or b in PARTYLESS: continue
        p1,p2=py[pid][a]['party'],py[pid][b]['party']
        flow_pairs[(a,b)][(p1,p2)]+=1
        if p1!=p2:
            switches.append(dict(person_id=pid,name=persons[pid]['canonical_name'],y1=a,y2=b,
                from_party=p1,to_party=p2,won_before=py[pid][a]['outcome']=='Win',won_after=py[pid][b]['outcome']=='Win'))
print('switch events:',len(switches))

per=Counter(s['person_id'] for s in switches)
serial=[]
for pid,n in per.most_common(40):
    seq=[(y,py[pid][y]['party'],py[pid][y]['outcome']) for y in sorted(py[pid])]
    serial.append(dict(person_id=pid,name=persons[pid]['canonical_name'],n_switches=n,
                       wins=sum(1 for _,_,o in seq if o=='Win'),seq=seq))

loyalty={}
for (a,b),cnt in flow_pairs.items():
    if YEARS.index(b)-YEARS.index(a)!=1: continue
    for (p1,p2),n in cnt.items():
        if p1=='IND': continue
        loyalty.setdefault(p1,Counter()); loyalty[p1]['total']+=n
        if p1==p2: loyalty[p1]['stay']+=n
loy={p:dict(stay=v['stay'],total=v['total'],rate=round(v['stay']/v['total'],3)) for p,v in loyalty.items() if v['total']>=30}

seat_moves=[]
for pid in py:
    wins=[(y,py[pid][y]) for y in sorted(py[pid]) if py[pid][y]['outcome']=='Win']
    dists=set(r['district'] for _,r in wins if r['district'])
    if len(wins)>=2 and len(dists)>=2:
        seat_moves.append(dict(person_id=pid,name=persons[pid]['canonical_name'],
            moves=[(y,r['na'],r['district'],r['party']) for y,r in wins]))

turnover={}
for a,b in zip(YEARS,YEARS[1:]):
    wa={pid for pid in py if a in py[pid] and py[pid][a]['outcome']=='Win'}
    wb={pid for pid in py if b in py[pid] and py[pid][b]['outcome']=='Win'}
    recon=[pid for pid in wa if b in py[pid]]
    rewon=[pid for pid in recon if py[pid][b]['outcome']=='Win']
    turnover[f'{a}-{b}']=dict(winners=len(wa),ran_again=len(recon),rewon=len(rewon),
        reelection_rate=round(len(rewon)/max(1,len(recon)),3),
        newcomers=len([pid for pid in wb if all(y>=b for y in py[pid])]))
print('turnover:',json.dumps({k:v['reelection_rate'] for k,v in turnover.items()}))

json.dump(dict(longest=longest,switches=switches,serial=serial[:40],
               adjacent_flows={}, loyalty=loy,seat_moves=seat_moves,turnover=turnover),
          open(f'{BASE}/out/career_ext.json','w'),indent=1)
print('wrote career_ext.json')

# ---- dynasties.json rebuild (person ids stable; resolve override-merged ids) ----
ov=json.load(open(f'{BASE}/scripts_link/overrides.json'))
def resolver():
    m={}
    for mr in ov['merges']:
        grp=mr['ids']; live=[i for i in grp if i in persons]
        tgt=live[0] if live else grp[0]
        for i in grp: m[i]=tgt
    return m
res=resolver()
def rp(pid): return res.get(pid,pid) if pid not in persons else pid
dyn=json.load(open(f'{BASE}/scripts_link/dynasties_verified.json'))
out_fams=[]
for fam in dyn:
    nodes={}; edges=[]
    def addnode(pid):
        pi=persons.get(pid)
        if pi: nodes[pid]=dict(id=pid,name=pi['canonical_name'],wins=int(pi['n_wins']),
            win_years=pi['win_years'],years=pi['years'],parties=pi['parties'],districts=pi['districts'][:60])
        else: nodes[pid]=dict(id=pid,name=f'({pid} not found)',wins=0,win_years='',years='',parties='',districts='')
    for seed in fam.get('seeds',[]):
        sp=rp(seed)
        if sp in persons: addnode(sp)
    for e in fam['edges']:
        a,b=rp(e['a']),rp(e['b'])
        for pid in (a,b):
            if pid not in nodes: addnode(pid)
        if a!=b: edges.append(dict(a=a,b=b,rel=e['rel'],note=e['note'],src=e['src']))
    out_fams.append(dict(family=fam['family'],base=fam['base'],notes=fam.get('notes',''),
        nodes=list(nodes.values()),edges=edges,total_wins=sum(n['wins'] for n in nodes.values())))
json.dump(out_fams,open(f'{BASE}/out/dynasties_ext.json','w'),indent=1)
missing=[n['name'] for f in out_fams for n in f['nodes'] if 'not found' in n['name']]
print('families:',len(out_fams),'edges:',sum(len(f["edges"]) for f in out_fams),'missing:',missing)
