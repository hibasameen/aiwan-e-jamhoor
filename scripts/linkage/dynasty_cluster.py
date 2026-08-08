#!/usr/bin/env python3
"""Dynasty clustering: family clusters of candidates sharing rare surname/clan tokens within a district."""
import csv, json
from collections import defaultdict, Counter

OUT = '/home/claude/aej/out'
cands = list(csv.DictReader(open(f'{OUT}/candidacies.csv')))
persons = {p['person_id']: p for p in csv.DictReader(open(f'{OUT}/persons.csv'))}

DIST_FIX = {'abbbottabad cum haripur':'abbottabad cum haripur','bahawlpur':'bahawalpur',
 'muzaffaragarh':'muzaffargarh','gujranwalla':'gujranwala','attok':'attock','mirpurkhas':'mirpur khas',
 'm b din':'mandi bahauddin','old dadu':'dadu','old badin':'badin','old shikarpur':'shikarpur',
 'old khairpur':'khairpur','old sukkur':'sukkur','old larkana':'larkana','sheikhupura':'shekhupura',
 'mandi bahauddin':'mandi bahauddin'}
def fixd(d): return DIST_FIX.get(d, d)

# token frequency at PERSON level (not candidacy) to measure true rarity
person_tokens = defaultdict(set)
person_last = defaultdict(set)   # surname-position tokens per person
for c in cands:
    toks = c['name_core'].split()
    person_tokens[c['person_id']].update(toks)
    # last-position token; if it's a stop-ish generic, also take second-to-last
    if toks:
        person_last[c['person_id']].add(toks[-1])
        if len(toks) >= 2:
            person_last[c['person_id']].add(toks[-2])  # allow penultimate (e.g. 'X Khan Leghari' variants, 'Y Bhutto Zardari')
tokf = Counter()
for pid, toks in person_tokens.items():
    for t in toks: tokf[t] += 1

STOP = {'muhammad','ahmed','ali','khan','hussain','shah','syed','malik','mian','sardar','haji','abdul',
 'ur','ul','din','uddin','ud','e','al','rehman','ullah','akhtar','iqbal','aslam','akram','arshad',
 'hassan','husan','raza','abbas','ashraf','anwar','aziz','bibi','begum','khatoon','fatima','sharif',
 'mehmood','mahmood','masood','tariq','nawaz','saeed','rashid','javed','naeem','nasir','amjad','ijaz',
 'riaz','imtiaz','shahzad','ramzan','ishaq','yousaf','younas','younis','usman','umar','omar','farooq',
 'siddique','sadiq','rafique','shafique','bashir','nazir','munir','zafar','mazhar','azhar','iftikhar',
 'gul','jan','bacha','rahim','karim','ghulam','noor','sultan','salim','saleem','waheed','wahid',
 'majeed','majid','hamid','khalid','shaukat','liaquat','liaqat','ilyas','ismail','ibrahim','yaqoob',
 'ayub','ayoub','sajjad','asad','azam','aman','amin','mumtaz','pervaiz','parvez','pervez','shahid',
 'zahid','abid','asif','atif','arif','kashif','naveed','waseem','wasim','nadeem','fareed','farid',
 'jamil','jameel','khalil','shakeel','adnan','imran','irfan','rizwan','kamran','salman','usama',
 'bhai','sahib','baba','khanum','dad','dost','mir','pir','wali','zaman','alam','aalam','akbar',
 'asghar','sher','shair','babar','tahir','taj','fazl','fida','sana','hanif','haneef','latif',
 'lateef','rauf','sattar','ghaffar','ghafoor','razzaq','rasheed','hameed','hafeez','shafi','elahi',
 'ahmad','husain','hussan','ahsan','ehsan','kamal','jamal','iqbal','qadir','qadeer','sadique','abdullah'}

STOP |= {'adv','advt','advocate','rtd','ret','retired','justice','brig','col','capt','maj','gen',
 'rana','rai','mir','khawaja','kh','nawab','nawabzada','sahibzada','sahabzada','makhdoom','makhdoomzada',
 'makhdom','pirzada','zada','khel','qazi','agha','arbab','chaudhry','shaikh','ansari','ata','atta',
 'mustafa','nisar','sohail','aftab','shabbir','shabir','munawar','khurram','murtaza','shoukat','haider',
 'hyder','zulfiqar','zulfikar','nasrullah','amanullah','saifullah','saif','sadar','jaffar','jafar',
 'haq','bakhsh','niaz','jamshed','shahnawaz','sarwar','yousaf','talib','qasim','hashim','feroz',
 'firdous','shakoor','sabir','zahoor','manzoor','maqbool','maqsood','mansoor','masud','naseer',
 'nazeer','naseem','waqar','wazir','yahya','zia','zahir','zaheer','shamim','saleh','salahuddin',
 'sikandar','sikander','sultan','suleman','sulaiman','tanveer','tanvir','ubaid','umer','waqas',
 'ejaz','aijaz','ayaz','azeem','basit','bilal','danish','faisal','fahad','ghazanfar','gohar',
 'habib','hafiz','hamza','haroon','ihsan','ikram','irshad','ishtiaq','jahangir','jehangir','junaid',
 'kaleem','kamil','khizar','luqman','mobeen','mohsin','moin','mubashir','mudassar','mujahid',
 'mukhtar','muzaffar','nabeel','nadir','naseer','obaid','qamar','rafiq','rehmat','sami','shafqat',
 'shahbaz','shehbaz','sharafat','tabish','talha','touqeer','toqeer','waleed','yasir','zubair','begum'}

def surname_tokens(pid):
    """Candidate's family-marker tokens: rare tokens in surname position only."""
    toks = set()
    for t in person_last[pid]:
        if t in STOP or len(t) < 3: continue
        if tokf[t] <= 120:   # borne by <=120 persons nationally
            toks.add(t)
    return toks

# district(s) per person
pdist = defaultdict(set)
pwins = Counter(); pcont = Counter()
for c in cands:
    if c['district']: pdist[c['person_id']].add(fixd(c['district']))
    pcont[c['person_id']] += 1
    if c['outcome']=='Win': pwins[c['person_id']] += 1

# build edges: two persons share a district AND a rare token
tok_dist_persons = defaultdict(set)   # (token, district) -> persons
for pid in person_tokens:
    st = surname_tokens(pid)
    for d in pdist[pid]:
        for t in st:
            tok_dist_persons[(t,d)].add(pid)

parent = {}
def find(x):
    parent.setdefault(x,x)
    while parent[x]!=x:
        parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[rb]=ra

edges = defaultdict(set)  # pair -> shared (token,district)
for (t,d), pids in tok_dist_persons.items():
    if len(pids) < 2 or len(pids) > 8: continue   # >8 sharing a token in one district = probably a tribe, not a family
    pl = sorted(pids)
    for i in range(len(pl)):
        for j in range(i+1,len(pl)):
            edges[(pl[i],pl[j])].add((t,d))
for (a,b) in edges: union(a,b)

clusters = defaultdict(set)
for pid in parent: clusters[find(pid)].add(pid)

rows = []
for root, pids in clusters.items():
    if len(pids) < 2: continue
    wins = sum(pwins[p] for p in pids)
    winners = [p for p in pids if pwins[p] > 0]
    toks = Counter()
    for (a,b), shared in edges.items():
        if a in pids and b in pids:
            for (t,d) in shared: toks[t]+=1
    years = set()
    for p in pids:
        for y in persons[p]['years'].split('|'):
            if y: years.add(int(y))
    dists = set()
    for p in pids: dists |= pdist[p]
    rows.append(dict(
        cluster_id=f'F{len(rows):04d}',
        family_tokens='|'.join(t for t,_ in toks.most_common(4)),
        districts='|'.join(sorted(dists))[:80],
        n_members=len(pids), n_winners=len(winners), total_wins=wins,
        span=f'{min(years)}-{max(years)}' if years else '',
        members='; '.join(f"{persons[p]['canonical_name']} ({pwins[p]}W/{pcont[p]}C, {persons[p]['parties']})" for p in sorted(pids, key=lambda x:-pwins[x])[:14]),
        member_ids='|'.join(sorted(pids)),
    ))

rows.sort(key=lambda r: (-r['n_winners'], -r['total_wins']))
print(f'clusters with >=2 members: {len(rows)}')
print(f'clusters with >=2 winners: {sum(1 for r in rows if r["n_winners"]>=2)}')
with open(f'{OUT}/family_clusters.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows[:30]:
    print(f"\n[{r['cluster_id']}] tokens={r['family_tokens']} dist={r['districts'][:40]} members={r['n_members']} winners={r['n_winners']} wins={r['total_wins']} span={r['span']}")
    print('   ', r['members'][:300])
