#!/usr/bin/env python3
import csv, json
from collections import Counter
BASE='/sessions/eloquent-zen-cori/mnt/outputs/aej'
career=json.load(open(f'{BASE}/out/career_ext.json'))
dyn=json.load(open(f'{BASE}/out/dynasties_ext.json'))
persons=list(csv.DictReader(open(f'{BASE}/out/persons_ext.csv')))
cands=list(csv.DictReader(open(f'{BASE}/out/candidacies_ext.csv')))
car={}
for c in cands:
    car.setdefault(c['person_id'],[]).append([int(c['year']),c['na'],c['district'],c['party'],
        c['votes'] or '',c['rank'] or '',1 if c['outcome']=='Win' else 0])
people={p['person_id']:{'n':p['canonical_name'],'w':int(p['n_wins']),'c':sorted(car.get(p['person_id'],[]))} for p in persons}
embed=dict(longest=career['longest'][:60],serial=career['serial'][:25],loyalty=career['loyalty'],
    seat_moves=sorted(career['seat_moves'],key=lambda s:-len(s['moves']))[:40],turnover=career['turnover'])
sw=career['switches']
winsw=Counter((s['from_party'],s['to_party']) for s in sw if s['won_after'])
embed['top_win_switches']=[[a,b,n] for (a,b),n in winsw.most_common(18)]
allsw=Counter((s['from_party'],s['to_party']) for s in sw)
embed['top_all_switches']=[[a,b,n] for (a,b),n in allsw.most_common(18)]
pair=Counter(f"{s['y1']}-{s['y2']}" for s in sw)
embed['switch_pairs']=dict(pair)
tiles=[[f'{len(people):,}','linked persons'],[f'{len(cands):,}','candidacies · 11 elections'],
       [f'{len(sw):,}','party switches'],[f'{len(dyn)}','sourced families']]
tpl=open(f'{BASE}/candidates_template.html').read()
html=(tpl.replace('/*__CAREER__*/null',json.dumps(embed))
         .replace('/*__DYN__*/null',json.dumps(dyn))
         .replace('/*__PEOPLE__*/null',json.dumps(people,separators=(',',':')))
         .replace('/*__TILES__*/null',json.dumps(tiles)))
open(f'{BASE}/out/candidates_new.html','w').write(html)
print('wrote candidates_new.html',round(len(html)/1e6,2),'MB; tiles:',tiles)
