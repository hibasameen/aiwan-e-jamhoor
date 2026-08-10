#!/usr/bin/env python3
"""Extend the linked spine back to 1977/1985/1988/1990 WITHOUT disturbing existing person ids.

- Existing candidacies_final.csv rows keep their person_id (P*/PX*).
- New rows are linked among themselves (union-find, build_spine thresholds),
  then each historic cluster is conservatively matched to existing persons.
- Unmatched clusters get fresh ids H####.
Outputs: out/candidacies_ext.csv, out/persons_ext.csv, out/crossera_links.csv
"""
import csv, re, sys
from collections import defaultdict, Counter
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

BASE='/sessions/eloquent-zen-cori/mnt/outputs/aej'
# pull normalization helpers out of build_spine.py without running its pipeline
src=open(f'{BASE}/scripts_link/build_spine.py').read()
src=src.split('# ---------------- load candidacies')[0]
src=src.replace("DATA = '/home/claude/aej/data'","DATA=''").replace("OUT = '/home/claude/aej/out'","OUT=''")
src=src.replace("import os; os.makedirs(OUT, exist_ok=True)","")
src=src.replace("'begum','mrs'","'begum','mohtarma','mrs'")
ns={}
exec(src, ns)
norm_name, norm_party, district_base = ns['norm_name'], ns['norm_party'], ns['district_base']

# historic party normalization (year-aware where labels collide with modern ones)
def hist_party(year, raw):
    r=(raw or '').strip()
    key=r.lower()
    if year==1985 or not r: return 'NONP' if year==1985 else 'IND'
    fix={'independent':'IND','ind':'IND',
         'pml-q':'PML(Qayyum)','pmlq':'PML(Qayyum)',   # Qayyum League, not 2002 PMLQ
         'jui-f':'JUIF','juif':'JUIF','jui-h':'JUI-H','juih':'JUI-H','jui-d':'JUI-D',
         'jup-n':'JUP','jup':'JUP','hpg':'MQM','haq parast group':'MQM',
         'pkmap':'PkMAP','pna':'PNA','pda':'PDA','iji':'IJI','pai':'PAI','pat':'PAT',
         'anp':'ANP','tnfj':'TNFJ','ppp':'PPP'}
    return fix.get(key, r)

YEARS_OLD=[1977,1985,1988,1990]
old=[]
for y in YEARS_OLD:
    cname={r['na']:r['constituency_name'] for r in csv.DictReader(open(f'{BASE}/data/results_{y}/na_{y}_constituency.csv'))}
    for r in csv.DictReader(open(f'{BASE}/data/results_{y}/na_{y}_candidates.csv')):
        name=r['candidate_name'].strip()
        if not name: continue
        full,core,squash,distinct=norm_name(name)
        if not core: continue
        con=cname.get(r['na'],'')
        old.append(dict(year=str(y), na=r['na'], constituency=con, province='',
            district=district_base(con), name_raw=name, name_full=full, name_core=core,
            name_squash=squash, name_distinct=distinct,
            party=hist_party(y,r['party']), party_raw=r['party'],
            votes=r['votes'], share='', rank=r['rank'],
            outcome='Win' if r['rank']=='1' else 'Loss', src=f'ep{y}', person_id=''))
print('historic rows:', len(old), Counter(c['year'] for c in old))

# ---- union-find within historic rows (build_spine thresholds) ----
parent=list(range(len(old)))
def find(x):
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[rb]=ra

tok=Counter()
for c in old:
    for t in set(c['name_core'].split()): tok[t]+=1
def rare(c): return {t for t in c['name_core'].split() if tok[t]<=25 and len(t)>2}

blocks=defaultdict(list)
for i,c in enumerate(old):
    blocks[('d',c['district'])].append(i)
    blocks[('s',c['name_squash'])].append(i)
    for t in rare(c): blocks[('t',t)].append(i)
    if len(c['name_distinct'])>=8: blocks[('x',c['name_distinct'])].append(i)

seen=set(); links=0
FILLER={'muhammad','khan','hussain','ahmed','ali','shah','syed','mian','sardar','malik','haji','sahibzada'}
for key,idxs in blocks.items():
    if len(idxs)<2 or (len(idxs)>400 and key[0]!='d'): continue
    for ii in range(len(idxs)):
        for jj in range(ii+1,len(idxs)):
            i,j=idxs[ii],idxs[jj]
            if find(i)==find(j): continue
            pk=(min(i,j),max(i,j))
            if pk in seen: continue
            seen.add(pk)
            a,b=old[i],old[j]
            if a['year']==b['year']:
                # same-year multi-seat: exact squash + (same non-IND party or long rare name)
                if a['na']!=b['na'] and a['name_squash']==b['name_squash'] and (
                    (a['party']==b['party'] and a['party'] not in ('IND','NONP')) or
                    (len(a['name_squash'])>=14 and rare(a)&rare(b))):
                    union(i,j); links+=1
                continue
            same_dist=a['district']==b['district'] and a['district']
            s=max(fuzz.token_sort_ratio(a['name_core'],b['name_core']), fuzz.ratio(a['name_squash'],b['name_squash']))
            ok=False
            if a['name_squash']==b['name_squash'] and (same_dist or len(a['name_squash'])>=16): ok=True
            elif a['name_distinct'] and a['name_distinct']==b['name_distinct'] and len(a['name_distinct'])>=8 and (same_dist or len(a['name_distinct'])>=16): ok=True
            elif s>=93 and same_dist: ok=True
            elif s>=96 and rare(a)&rare(b): ok=True
            elif same_dist and len(a['name_squash'])>=10 and Levenshtein.distance(a['name_squash'],b['name_squash'])<=1: ok=True
            else:
                ta,tb=set(a['name_core'].split()),set(b['name_core'].split())
                if same_dist and min(len(ta),len(tb))>=3 and (ta<=tb or tb<=ta) and ((ta^tb)<=FILLER): ok=True
            if ok: union(i,j); links+=1
print('within-historic links:', links)

clusters=defaultdict(list)
for i in range(len(old)): clusters[find(i)].append(i)
print('historic clusters:', len(clusters))

# ---- index existing persons (1993-2024 spine) ----
cur=list(csv.DictReader(open(f'{BASE}/out/candidacies_final.csv')))
P=defaultdict(lambda: dict(squash=set(),distinct=set(),core=set(),dists=set(),years=set(),names=Counter()))
for c in cur:
    p=P[c['person_id']]
    p['squash'].add(c['name_squash']); p['distinct'].add(c['name_distinct'])
    p['core'].add(c['name_core']); p['dists'].add(c['district']); p['years'].add(int(c['year']))
    p['names'][c['name_raw']]+=1
sq_idx=defaultdict(set); di_idx=defaultdict(set)
for pid,p in P.items():
    for s in p['squash']: sq_idx[s].add(pid)
    for d in p['distinct']:
        if len(d)>=8: di_idx[d].add(pid)

def match_cluster(idxs):
    """Return (pid, evidence) or (None, reason)."""
    rows=[old[i] for i in idxs]
    dists={r['district'] for r in rows if r['district']}
    maxy=max(int(r['year']) for r in rows)
    cands=Counter()
    for r in rows:
        for pid in sq_idx.get(r['name_squash'],()): cands[pid]+=2
        if len(r['name_distinct'])>=8:
            for pid in di_idx.get(r['name_distinct'],()): cands[pid]+=1
    scored=[]
    for pid in cands:
        p=P[pid]
        gap=min(p['years'])-maxy
        dist_ok=bool(dists & p['dists'])
        exact_sq=any(r['name_squash'] in p['squash'] for r in rows)
        exact_di=any(len(r['name_distinct'])>=8 and r['name_distinct'] in p['distinct'] for r in rows)
        best_len=max((len(r['name_squash']) for r in rows if r['name_squash'] in p['squash']), default=0)
        ok=False; ev=''
        best_di=max((len(r['name_distinct']) for r in rows if r['name_distinct'] in p['distinct']), default=0)
        rare_shared=any(rare(r) & {t for c2 in p['core'] for t in c2.split()} for r in rows)
        if gap<=10:
            if exact_sq and (dist_ok or best_len>=14): ok=True; ev=f'sq{"+d" if dist_ok else ""}L{best_len}'
            elif exact_di and dist_ok: ok=True; ev='di+d'
        elif gap<=20:
            if exact_sq and dist_ok and best_di>=10: ok=True; ev=f'sq+d di{best_di} GAP{gap}'
        elif gap<=35:
            if exact_sq and dist_ok and best_di>=10 and rare_shared: ok=True; ev=f'sq+d+rare di{best_di} GAP{gap}'
        # gap>35: a 1977 candidate reappearing after 2013 is almost surely a namesake/heir
        if ok: scored.append((cands[pid],pid,ev,gap,dist_ok))
    BLOCK={('muhammadkhanjunejo'),('muhammadaslamkhankhatak')}  # PM Junejo d.1993; Aslam Khattak d.2008 pre-poll
    scored=[t for t in scored if not any(r['name_squash'] in BLOCK for r in rows)]
    if not scored: return None,'no-match'
    scored.sort(reverse=True)
    if len(scored)>1 and scored[0][0]==scored[1][0]: return None,'ambiguous'
    return scored[0][1], scored[0][2]

crossera=[]; new_pid=0
for root,idxs in clusters.items():
    pid,ev=match_cluster(idxs)
    if pid is None:
        new_pid+=1; pid=f'H{new_pid:04d}'
    else:
        rows=[old[i] for i in idxs]
        crossera.append(dict(pid=pid, existing=P[pid]['names'].most_common(1)[0][0],
            hist_name=rows[0]['name_raw'], hist_years='|'.join(sorted({r['year'] for r in rows})),
            hist_dists='|'.join(sorted({r['district'] for r in rows})),
            exist_years='|'.join(map(str,sorted(P[pid]['years']))),
            exist_dists='|'.join(sorted(P[pid]['dists'])), evidence=ev))
    for i in idxs: old[i]['person_id']=pid
print('clusters linked to existing persons:', len(crossera), '; new historic persons:', new_pid)

# ---- write extended spine ----
allrows=cur+old
allrows.sort(key=lambda c:(int(c['year']),c['na']))
with open(f'{BASE}/out/candidacies_ext.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(cur[0].keys())); w.writeheader(); w.writerows(allrows)

groups=defaultdict(list)
for c in allrows: groups[c['person_id']].append(c)
persons=[]
for pid,members in groups.items():
    wins=[m for m in members if m['outcome']=='Win']
    pool=wins if wins else members
    canon=Counter(m['name_raw'] for m in pool).most_common(1)[0][0]
    years=sorted(set(int(m['year']) for m in members))
    win_years=sorted(set(int(m['year']) for m in wins))
    persons.append(dict(person_id=pid, canonical_name=canon, n_candidacies=len(members),
        n_wins=len(wins), n_win_years=len(win_years), win_years='|'.join(map(str,win_years)),
        years='|'.join(map(str,years)), parties='|'.join(sorted(set(m['party'] for m in members))),
        districts='|'.join(sorted(set(m['district'] for m in members if m['district']))),
        provinces='|'.join(sorted(set(m['province'] for m in members if m['province']))) ))
with open(f'{BASE}/out/persons_ext.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(persons[0].keys())); w.writeheader(); w.writerows(persons)
with open(f'{BASE}/out/crossera_links.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(crossera[0].keys())); w.writeheader(); w.writerows(crossera)
print('persons total:', len(persons))

# sanity probes
for probe in ('bilour','benazir','nawaz sharif','jatoi','wali khan','junejo','bhutto'):
    hits=[p for p in persons if probe in norm_name(p['canonical_name'])[1] and int(p['n_wins'])>0]
    for p in sorted(hits,key=lambda p:-int(p['n_candidacies']))[:4]:
        print('PROBE',probe,'->',p['canonical_name'],p['years'],'wins:',p['win_years'])
# long-gap links to eyeball
print('\n1977-gap links:')
for r in crossera:
    if 'GAP' in r['evidence']: print(' ',r['hist_name'],r['hist_years'],'->',r['existing'],r['exist_years'],r['evidence'])
