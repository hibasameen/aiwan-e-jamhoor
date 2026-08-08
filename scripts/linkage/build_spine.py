#!/usr/bin/env python3
"""Build unified candidacy table + cross-election person linkage spine.

Elections: GE 1993, 1997, 2002, 2008, 2013 (Cookman pk), 2018 (Cookman 2018), 2024 (scrape).
Output: candidacies.csv (one row per candidacy, with person_id), persons.csv.
"""
import csv, json, re, sys, unicodedata
from collections import defaultdict, Counter
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

DATA = '/home/claude/aej/data'
OUT = '/home/claude/aej/out'
import os; os.makedirs(OUT, exist_ok=True)

GE_DATES = {'10/6/93': 1993, '2/3/97': 1997, '10/10/02': 2002, '2/18/08': 2008, '5/11/13': 2013}

# ---------------- party normalization ----------------
PARTY_MAP = {
    'independents': 'IND', 'independent': 'IND',
    'pakistan peoples party parliamentarians': 'PPP', 'pakistan peoples party': 'PPP', 'ppp': 'PPP', 'pppp': 'PPP',
    'pakistan peoples party (shaheed bhutto)': 'PPP-SB',
    'pakistan muslim league (nawaz)': 'PMLN', 'pakistan muslim league (n)': 'PMLN', 'pml-n': 'PMLN',
    'pakistan muslim league (qaid-e-azam)': 'PMLQ', 'pakistan muslim league (q)': 'PMLQ', 'pml-q': 'PMLQ', 'pml': 'PMLQ*',
    'pakistan muslim league': 'PML', 'pakistan muslim league (j)': 'PMLJ', 'pakistan muslim league (junejo)': 'PMLJ',
    'pakistan muslim league (functional)': 'PMLF', 'pml-f': 'PMLF', 'pakistan muslim league (f)': 'PMLF',
    'pakistan muslim league (haqiqi)': 'PML-H', 'pakistan muslim league (zia-ul-haq shaheed)': 'PML-Z', 'pml-z': 'PML-Z',
    'pakistan muslim league-j (chataha group)': 'PMLJ',
    'pakistan tehreek-e-insaf': 'PTI', 'pti': 'PTI', 'pakistan tehreek-e-insaaf': 'PTI',
    'muttahida qaumi movement': 'MQM', 'muttahida qaumi movement pakistan': 'MQM', 'mqm': 'MQM', 'haq parast group': 'MQM',
    'mohajir qaumi movement (haqiqi)': 'MQM-H', 'haqiqi group': 'MQM-H',
    'jamiat ulema-e islam (fazl)': 'JUIF', 'jamiat ulema-e-islam (f)': 'JUIF', 'jui-f': 'JUIF', 'jamiat ulema-e-islam (fazl)': 'JUIF',
    'jamiat ulama-e-islam (sami)': 'JUIS', 'jui-s': 'JUIS',
    'jamaat-e-islami': 'JI', 'jamaat e islami': 'JI', 'jip': 'JI', 'jamaat-e-islami pakistan': 'JI',
    'pakistan islamic front': 'JI',  # 1993 JI front
    'muttahidda majlis-e-amal pakistan': 'MMA', 'muttahida majlis-e-amal pakistan': 'MMA', 'mma': 'MMA',
    'awami national party': 'ANP', 'anp': 'ANP',
    'tehreek-e-labbaik pakistan': 'TLP', 'tlp': 'TLP',
    'grand democratic alliance': 'GDA', 'gda': 'GDA',
    'balochistan awami party': 'BAP', 'bap': 'BAP',
    'balochistan national party': 'BNP', 'bnp': 'BNP', 'balochistan national party (mengal)': 'BNP',
    'balochistan national party (awami)': 'BNP-A',
    'national party': 'NP', 'np': 'NP',
    'pashtoonkhwa milli awami party': 'PkMAP', 'paktunkhwa milli awami party': 'PkMAP', 'pkmap': 'PkMAP',
    'qaumi watan party': 'QWP', 'qwp': 'QWP',
    'awami muslim league pakistan': 'AML', 'aml': 'AML',
    'all pakistan muslim league': 'APML', 'apml': 'APML',
    'pak sarzameen party': 'PSP', 'psp': 'PSP',
    'jamhoori wattan party': 'JWP', 'national alliance': 'NA(alliance)',
    'pakistan awami tehreek': 'PAT', 'pat': 'PAT',
    'sunni ittehad council': 'SIC', 'sic': 'SIC',
    'sunni tehreek': 'ST',
    'jamiat ulema-e-pakistan (noorani)': 'JUP',
    'pakistan awami ittehad': 'PAI', 'islami jamhoori mahaz': 'IJM',
    'pmml': 'PMML', 'pakistan markazi muslim league': 'PMML',
    'mwm': 'MWM', 'majlis-e-wahdat-e-muslimeen pakistan': 'MWM', 'majlis wahdat-e-muslimeen pakistan': 'MWM',
    'mqm-p': 'MQM', 'pakistan muslim league(z)': 'PML-Z', 'pakistan muslim league (z)': 'PML-Z',
    'istehkam-e-pakistan party': 'IPP', 'ipp': 'IPP',
    'tehreek-e-labbaik islam': 'TLI', 'pakistan rah-e-haq party': 'PRHP', 'prp': 'PRHP',
    'allah-o-akbar tehreek': 'AAT',
}

def norm_party(p):
    if not p: return 'IND'
    key = p.strip().lower()
    return PARTY_MAP.get(key, p.strip())

# ---------------- name normalization ----------------
HONORIFICS = {'haji','hajji','alhaj','al-haj','alhajj','alhaaj','al-haaj','elhaj','maulana','moulana','molana','maulvi','molvi','mufti','qari','hafiz',
    'dr','doctor','engineer','engr','prof','professor','justice','retd','advocate','barrister',
    'general','gen','major','maj','colonel','col','captain','capt','begum','mrs','mr','miss','ms',
    'senator','sahib','sb','shaheed','allama','agha?'}
HONORIFICS.discard('agha?')
TOKEN_FIX = {'mohammad':'muhammad','mohammed':'muhammad','muhammed':'muhammad','mohd':'muhammad','muhd':'muhammad','mohummad':'muhammad','muhammadd':'muhammad',
    'ch':'chaudhry','chaudhary':'chaudhry','chaudhari':'chaudhry','chaudry':'chaudhry','chowdhury':'chaudhry','chaudhri':'chaudhry','choudhry':'chaudhry','choudhary':'chaudhry',
    'sayed':'syed','sayyed':'syed','saiyed':'syed','sayad':'syed','syad':'syed',
    'sheikh':'shaikh','shiekh':'shaikh','shekh':'shaikh',
    'raheem':'rahim','kareem':'karim','abdal':'abdul','abdual':'abdul',
    'hussein':'hussain','husain':'hussain','hussian':'hussain','hossain':'hussain',
    'ahmad':'ahmed','ahmd':'ahmed',
    'khaan':'khan','khattak':'khatak','bhuttto':'bhutto',
    'yusuf':'yousaf','yousuf':'yousaf','yusaf':'yousaf','bux':'bakhsh','buksh':'bakhsh','baksh':'bakhsh',
    'mehar':'mahar','mehr':'mahar','laghari':'leghari','virk':'wirk','waraich':'warraich',
    'mahmood':'mehmood','mahmud':'mehmood','mehmud':'mehmood','jilani':'jillani','jeelani':'jillani','gillani':'gilani',
    'sana':'sana','fazal':'fazl','fazle':'fazl','fazal-e':'fazl',
    'ur':'ur','ul':'ul'}
# common "connector" bits that get glued: sana ullah / sanaullah; rehman/rahman
GLUE_FIX = [('rahman','rehman'), ('ullah','ullah')]

COMMON_TOKENS = {'muhammad','ahmed','ali','khan','hussain','shah','syed','malik','mian','sardar','haji','abdul','ur','ul','din','uddin','ud','e','al'}

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def norm_name(raw):
    s = strip_accents(raw or '').lower()
    s = re.sub(r'[^a-z\s\-]', ' ', s)
    s = s.replace('-', ' ')
    toks = [TOKEN_FIX.get(t, t) for t in s.split()]
    toks = [t.replace('rahman','rehman') for t in toks]
    full = ' '.join(toks)
    core_t = [t for t in toks if t not in HONORIFICS and len(t) > 1]  # drop honorifics + initials
    core = ' '.join(core_t)
    squash = core.replace(' ', '')
    # distinct form: also drop ultra-common lead token 'muhammad'
    dist_t = [t for t in core_t if t not in ('muhammad', 'mian')]
    distinct = ''.join(dist_t)
    return full, core, squash, distinct

def district_base(name):
    """Reduce constituency name to its district-ish base."""
    s = strip_accents(name or '').lower()
    s = re.sub(r'\(.*?\)', ' ', s)
    s = s.replace('-', ' ').replace('cum', ' cum ')
    s = re.sub(r'[^a-z\s]', ' ', s)
    toks = [t for t in s.split() if t not in {'i','ii','iii','iv','v','vi','vii','viii','ix','x','xi','xii','xiii','xiv','xv','xvi','xvii','xviii','xix','xx','xxi'}]
    s = ' '.join(toks)
    # normalize common district spellings
    s = s.replace('dera ismail khan','di khan').replace('d i khan','di khan').replace('dikhan','di khan')
    s = s.replace('dera ghazi khan','dg khan').replace('d g khan','dg khan')
    s = s.replace('tribal area','ta').replace('tribal areas','ta')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# ---------------- load candidacies ----------------
cands = []  # dicts
def add(year, na, cname, prov, name, party, votes, share, rank, outcome, src):
    if not name or not name.strip(): return
    full, core, squash, distinct = norm_name(name)
    if not core: return
    cands.append(dict(year=year, na=na, constituency=cname, province=prov or '', district=district_base(cname),
        name_raw=name.strip(), name_full=full, name_core=core, name_squash=squash, name_distinct=distinct,
        party=norm_party(party), party_raw=(party or '').strip(),
        votes=votes, share=share, rank=rank, outcome=outcome, src=src))

for r in csv.DictReader(open(f'{DATA}/cookman_pk_candidate_data.csv')):
    if r['assembly'] != 'National': continue
    y = GE_DATES.get(r['election_date'])
    if not y: continue
    if r['contest_status'] not in ('Contested',''): pass
    add(y, r['constituency_number'], r['constituency_name'], r['province'], r['candidate_name'],
        r['candidate_party'], r['candidate_votes'], r['candidate_share'], r['candidate_rank'], r['outcome'], 'cookman')

for r in csv.DictReader(open(f'{DATA}/cookman_2018_candidate.csv')):
    if r['assembly'] != 'National': continue
    add(2018, r['constituency_code'], r['constituency_name'], r['province'], r['candidate_name'],
        r['candidate_party'], r['candidate_votes'], r['candidate_share'], r['candidate_rank'], r['outcome'], 'cookman18')

for r in csv.DictReader(open(f'{DATA}/results_2024/na_2024_candidates.csv')):
    add(2024, r['na'], '', '', r['candidate_name'], r['party'], r['votes'], '', r['rank'],
        'Win' if r['rank']=='1' else 'Loss', 'ep2024')

# fill 2024 constituency names/province from constituency file
cmeta = {r['na']: r for r in csv.DictReader(open(f'{DATA}/results_2024/na_2024_constituency.csv'))}
for c in cands:
    if c['year']==2024 and c['na'] in cmeta:
        m = cmeta[c['na']]
        c['constituency'] = m['constituency_name']; c['province'] = m['province']
        c['district'] = district_base(m['constituency_name'])

print(f'candidacies: {len(cands)}')
print(Counter(c['year'] for c in cands))

# ---------------- token idf for rarity ----------------
tok_count = Counter()
for c in cands:
    for t in set(c['name_core'].split()):
        tok_count[t] += 1
N = len(cands)
def rare_tokens(c):
    return {t for t in c['name_core'].split() if tok_count[t] <= 60 and len(t) > 2}

# ---------------- pairwise matching (union-find) ----------------
parent = list(range(len(cands)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[rb] = ra

def sim(a, b):
    """Similarity score between two candidacies (different years)."""
    s1 = fuzz.token_sort_ratio(a['name_core'], b['name_core'])
    s2 = fuzz.ratio(a['name_squash'], b['name_squash'])
    return max(s1, s2)

def compatible(a, b):
    # same year -> never same person (can't contest twice? actually CAN contest multiple seats same year!)
    # Pakistani law allows multiple-seat candidacy. So same-year same-name in different seats may be same person.
    return True

# blocking sets
blocks = defaultdict(list)
for i, c in enumerate(cands):
    blocks[('d', c['district'])].append(i)          # same district base
    for t in rare_tokens(c):
        blocks[('t', t)].append(i)                   # shared rare token, nationwide
    blocks[('s', c['name_squash'])].append(i)        # exact squash
    if len(c['name_distinct']) >= 8:
        blocks[('x', c['name_distinct'])].append(i)  # distinct-form exact

pairs_checked = set()
links = 0
for key, idxs in blocks.items():
    if len(idxs) < 2: continue
    if len(idxs) > 400 and key[0] != 'd': continue  # token too common after all
    for ii in range(len(idxs)):
        for jj in range(ii+1, len(idxs)):
            i, j = idxs[ii], idxs[jj]
            if find(i) == find(j): continue
            pk = (min(i,j), max(i,j))
            if pk in pairs_checked: continue
            pairs_checked.add(pk)
            a, b = cands[i], cands[j]
            same_dist = a['district'] == b['district'] and a['district']
            same_prov = a['province'] and a['province'][:4] == b['province'][:4]
            s = sim(a, b)
            # thresholds
            ok = False
            if a['name_squash'] == b['name_squash'] and (same_dist or (len(a['name_squash'])>=12 and same_prov) or len(a['name_squash'])>=16):
                ok = True
            elif a['name_distinct'] and a['name_distinct'] == b['name_distinct'] and len(a['name_distinct']) >= 8 and (same_dist or (same_prov and len(a['name_distinct'])>=12) or len(a['name_distinct'])>=16):
                ok = True  # initials/muhammad-dropped exact match
            elif s >= 93 and same_dist:
                ok = True
            elif s >= 96 and same_prov and rare_tokens(a) & rare_tokens(b):
                ok = True
            elif fuzz.ratio(a['name_distinct'], b['name_distinct']) >= 95 and len(a['name_distinct'])>=10 and (same_dist or same_prov and rare_tokens(a) & rare_tokens(b)):
                ok = True
            elif same_dist and len(a['name_squash'])>=10 and Levenshtein.distance(a['name_squash'], b['name_squash']) <= 1:
                ok = True  # single-typo variants within district
            else:
                FILLER = {'muhammad','khan','hussain','ahmed','ali','shah','syed','mian','sardar','malik','haji','sahibzada','sahabzada'}
                ta, tb = set(a['name_core'].split()), set(b['name_core'].split())
                if same_dist and min(len(ta),len(tb)) >= 3 and (ta <= tb or tb <= ta) and ((ta ^ tb) <= FILLER):
                    ok = True  # same name minus dropped common filler token(s) (e.g. 'khan', 'hussain')
            if ok:
                union(i, j); links += 1
print(f'links made: {links}, pairs checked: {len(pairs_checked)}')

# ---------------- same-year multi-seat merging ----------------
# A person may contest several seats in the same election. Same exact squash + same non-IND party + same year -> same person.
byys = defaultdict(list)
for i, c in enumerate(cands):
    if c['party'] != 'IND':
        byys[(c['year'], c['party'], c['name_squash'])].append(i)
ms = 0
for key, idxs in byys.items():
    for j in idxs[1:]:
        if find(idxs[0]) != find(j): union(idxs[0], j); ms += 1
print(f'multi-seat same-year merges: {ms}')

# ---------------- curated closed groups for major leaders ----------------
# selector: rows matching are ONE person; rows unioned into their root but NOT matching are split back out.
def mk(sel_squash=None, sel_distinct=None, parties=None):
    def f(c):
        if parties and c['party'] not in parties: return False
        if sel_squash and c['name_squash'] in sel_squash: return True
        if sel_distinct and c['name_distinct'] in sel_distinct: return True
        return False
    return f
MANUAL = {
    'IMRAN_KHAN': mk(sel_squash={'imrankhan','imranahmedkhanniazi','imranahmadkhanniazi','imrankhanniazi'}, parties={'PTI'}),
    'NAWAZ_SHARIF': mk(sel_distinct={'nawazsharif'}, parties={'PMLN'}),
    'SHAHBAZ_SHARIF': mk(sel_distinct={'shahbazsharif','shehbazsharif'}, parties={'PMLN'}),
    'BENAZIR_BHUTTO': mk(sel_distinct={'benazirbhutto'}, parties={'PPP'}),
    'PERVEZ_MUSHARRAF': mk(sel_distinct={'pervezmusharraf'}, parties={'APML'}),
    'SHUJAAT_HUSSAIN': mk(sel_distinct={'chaudhryshujaathussain','shujaathussain'}, parties={'PMLN','PMLQ'}),
}
manual_of = {}
for mname, sel in MANUAL.items():
    idxs = [i for i, c in enumerate(cands) if sel(c)]
    for i in idxs: manual_of[i] = mname
    print('manual', mname, len(idxs), 'rows, years', sorted(set(cands[i]['year'] for i in idxs)))

# ---------------- build persons ----------------
groups = defaultdict(list)
for i in range(len(cands)):
    key = ('M', manual_of[i]) if i in manual_of else ('U', find(i), manual_of.get(find(i), ''))
    # if root row itself is manual but this row isn't, keep this row separate from the manual person
    if i not in manual_of:
        root = find(i)
        # group non-manual rows by (root, 'nonmanual'); manual rows peel off by name
        key = ('U', root)
    groups[key].append(i)

persons = []
for gid, idxs in groups.items():
    members = [cands[i] for i in idxs]
    years = sorted(set(m['year'] for m in members))
    # canonical name: most frequent raw among winners, else longest raw
    wins = [m for m in members if m['outcome']=='Win']
    pool = wins if wins else members
    canon = Counter(m['name_raw'] for m in pool).most_common(1)[0][0]
    pid = f'P{len(persons):05d}'
    for i in idxs: cands[i]['person_id'] = pid
    win_years = sorted(set(m['year'] for m in wins))
    persons.append(dict(person_id=pid, canonical_name=canon, n_candidacies=len(members),
        n_wins=len(wins), n_win_years=len(win_years), win_years='|'.join(map(str,win_years)),
        years='|'.join(map(str,years)),
        parties='|'.join(sorted(set(m['party'] for m in members))),
        districts='|'.join(sorted(set(m['district'] for m in members if m['district']))),
        provinces='|'.join(sorted(set(m['province'] for m in members if m['province']))) ))

print(f'persons: {len(persons)}; multi-election persons: {sum(1 for p in persons if "|" in p["years"])}')
print(f'multi-win persons: {sum(1 for p in persons if p["n_wins"]>1)}')

with open(f'{OUT}/candidacies.csv','w',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(cands[0].keys()))
    w.writeheader(); w.writerows(cands)
with open(f'{OUT}/persons.csv','w',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(persons[0].keys()))
    w.writeheader(); w.writerows(persons)

# quick sanity: top multi-win persons
top = sorted(persons, key=lambda p: (-p['n_win_years'], -p['n_wins']))[:25]
for p in top:
    print(p['n_win_years'], p['n_wins'], p['canonical_name'], p['years'], p['parties'][:50])
# spot checks
for probe in ('nawaz sharif','imran','bilour','asfandyar','shahbaz sharif','bhutto zardari'):
    hits = [p for p in persons if probe in norm_name(p['canonical_name'])[1]]
    for p in sorted(hits, key=lambda p:-p['n_candidacies'])[:3]:
        print('PROBE', probe, '->', p['canonical_name'], p['years'], 'wins:', p['win_years'])
