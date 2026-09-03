#!/usr/bin/env python3
"""
Build data/house/house.json — the full National Assembly (general + reserved
seats) for the five list-allocation elections, 2002–2024 (12th–16th NA).

Inputs
  hansard/linkage/members_na{12..16}.json   membership rolls (na.gov.pk)
  data/linked/candidacies_final.csv         general-seat results (site spine)
  data/linked/persons_final.csv             canonical person IDs

Outputs
  data/house/house.json                     everything house.html needs
  data/house/reserved_linkage.csv           audit trail: reserved member → person_id

Reserved-seat entitlement is computed with the largest-remainder (Hare quota)
rule on general seats won by parties (independents excluded), province by
province for the 60 women's seats and nationwide for the 10 non-Muslim seats.
That is the rule in s.104 Elections Act 2017 / Art. 51(6)(d)-(e); the ECP's
actual notified allocation additionally counts independents who joined a
party within three days of the result, which is why "entitlement on
election-day parties" and "ECP allocation" differ — the gap is shown, not
hidden.
"""
import csv, json, re, os, sys, collections, difflib

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
LINK = os.path.join(ROOT, 'hansard', 'linkage')
OUT = os.path.join(ROOT, 'data', 'house')
os.makedirs(OUT, exist_ok=True)

YEARS = {'2002': 12, '2008': 13, '2013': 14, '2018': 15, '2024': 16}
HOUSE = {'2002': 342, '2008': 342, '2013': 342, '2018': 342, '2024': 336}
GEN_SEATS = {'2002': 272, '2008': 272, '2013': 272, '2018': 272, '2024': 266}
# women's quota by province (Art. 51(3)); FATA and ICT carry no women's seats
WQUOTA = {
    '2002': {'Punjab': 35, 'Sindh': 14, 'Khyber Pakhtunkhwa': 8, 'Balochistan': 3},
    '2008': {'Punjab': 35, 'Sindh': 14, 'Khyber Pakhtunkhwa': 8, 'Balochistan': 3},
    '2013': {'Punjab': 35, 'Sindh': 14, 'Khyber Pakhtunkhwa': 8, 'Balochistan': 3},
    '2018': {'Punjab': 35, 'Sindh': 14, 'Khyber Pakhtunkhwa': 8, 'Balochistan': 3},
    '2024': {'Punjab': 32, 'Sindh': 14, 'Khyber Pakhtunkhwa': 10, 'Balochistan': 4},
}
NM_SEATS = 10
PROV_ORDER = ['Punjab', 'Sindh', 'Khyber Pakhtunkhwa', 'Balochistan']

# ---- party normalisation -------------------------------------------------
# site category keys (map.html COLORS) + a few extra small parties
CAT = {
    # spine (candidacies_final) labels
    'PMLN': 'PML-N', 'PPP': 'PPP', 'PTI': 'PTI', 'PMLQ': 'PML-Q', 'IND': 'IND', 'MQM': 'MQM',
    'MMA': 'MMA', 'JUIF': 'JUI-F', 'NA(alliance)': 'National Alliance', 'PMLF': 'PML-F',
    'ANP': 'ANP', 'BNP': 'BNP', 'BAP': 'BAP', 'QWP': 'QWP', 'PkMAP': 'PkMAP', 'PML': 'PML-Q',
    'PML-H': 'PML-J', 'PML-Z': 'PML-Z', 'NP': 'NP', 'JI': 'JI', 'IPP': 'IPP', 'JWP': 'JWP',
    'National Peoples Party': 'NPP', 'AML': 'AML', 'GDA': 'GDA', 'PAT': 'Other',
    'Pakistan Shia Political Party': 'Other', 'MQM-H': 'Other', 'BNP-A': 'BNP-A',
    'Awami Jamhuri Ittehad Pakistan': 'Other', 'APML': 'Other', 'MWM': 'MWM',
    # roll (na.gov.pk) labels
    'PML (Q)': 'PML-Q', 'PML(Q)': 'PML-Q', 'PPPP': 'PPP', 'PPPP (Patriot)': 'PPP-P',
    'PPPP (Petriot)': 'PPP-P', 'PML (N)': 'PML-N', 'PML(N)': 'PML-N', 'PML-N': 'PML-N',
    'MMAP': 'MMA', 'JUI-F': 'JUI-F', 'JUI (F)': 'JUI-F', 'JUI (P)': 'JUI-F', 'MQMP': 'MQM',
    'NA': 'National Alliance', 'PML (F)': 'PML-F', 'PML(F)': 'PML-F', 'PML-F': 'PML-F',
    'PML (J)': 'PML-J', 'PMAP': 'PkMAP', 'PKMAP': 'PkMAP', 'NPP': 'NPP', 'Ind': 'IND',
    'PPP (S)': 'PPP-S', 'PML (Z)': 'PML-Z', 'BNPM': 'BNP', 'MWMP': 'MWM', 'SIC': 'SIC',
    'PKNAP': 'PkNAP', 'AJIP': 'Other', 'AMLP': 'AML', 'QWP-S': 'QWP',
}
def cat(p):
    if p is None: return 'IND'
    p = p.strip()
    return CAT.get(p, p)

# 2024: 85 of the 99 independents were PTI-backed (reconciled seat-by-seat
# against FAFEN; see scripts/build/build_hemicycles.py SEAT_SPLIT)
PTI_IND_2024 = 85

# ---- official ECP allocation (per Wikipedia results tables, sourced to ECP)
OFFICIAL = {
    '2002': {'PML-Q': (23, 4), 'PPP': (14, 2), 'MMA': (12, 2), 'PML-N': (3, 1), 'National Alliance': (3, 0),
             'MQM': (3, 1), 'PML-F': (1, 0), 'PML-J': (1, 0)},
    '2008': {'PPP': (23, 4), 'PML-N': (17, 3), 'PML-Q': (10, 2), 'MQM': (5, 1), 'ANP': (3, 0),
             'MMA': (1, 0), 'PML-F': (1, 0)},
    '2013': {'PML-N': (34, 6), 'PPP': (8, 1), 'PTI': (6, 1), 'MQM': (4, 1), 'JUI-F': (3, 1),
             'PML-F': (1, 0), 'JI': (1, 0), 'PkMAP': (1, 0), 'NPP': (1, 0)},
    '2018': {'PTI': (28, 5), 'PML-N': (16, 2), 'PPP': (9, 2), 'MMA': (2, 1), 'GDA': (1, 0),
             'MQM': (1, 0), 'PML-Q': (1, 0), 'BAP': (1, 0), 'BNP': (1, 0)},
    # 2024: the allocation as finally notified after the Supreme Court's
    # 27 June 2025 review verdict restored the ECP's March 2024 distribution;
    # taken from the 16th NA roll itself (60 + 10, all assigned).
    '2024': None,
}
# 2024 first-round ECP allocation (before the 4 Mar 2024 decision to
# redistribute the seats claimed by SIC), per Wikipedia/ECP: 39 women, 6 non-Muslim
OFFICIAL_2024_FIRST = {'PML-N': (19, 4), 'PPP': (12, 2), 'MQM': (4, 0), 'JUI-F': (2, 0),
                       'IPP': (1, 0), 'PML-Q': (1, 0)}
# independents who joined a party within the 3-day window (Wikipedia, sourced to ECP)
JOINERS = {'2002': 'no figure found', '2008': '7 → PPP, 3 → PML-N', '2013': '19 → PML-N',
           '2018': '9 → PTI', '2024': '≈8 → PML-N; 84–88 → SIC (disallowed)'}

# ---- women / non-Muslims on GENERAL seats (hand-verified, election-day winners)
WOMEN_GENERAL = {
    '2002': ['NA-59', 'NA-69', 'NA-87', 'NA-90', 'NA-117', 'NA-130', 'NA-147', 'NA-176', 'NA-177',
             'NA-213', 'NA-223', 'NA-225', 'NA-272'],
    '2008': ['NA-69', 'NA-78', 'NA-87', 'NA-90', 'NA-92', 'NA-102', 'NA-111', 'NA-115', 'NA-130',
             'NA-169', 'NA-177', 'NA-213', 'NA-223', 'NA-225'],
    '2013': ['NA-69', 'NA-88', 'NA-102', 'NA-207', 'NA-213', 'NA-225'],
    '2018': ['NA-77', 'NA-115', 'NA-191', 'NA-208', 'NA-216', 'NA-230', 'NA-232', 'NA-271'],
    '2024': ['NA-30', 'NA-67', 'NA-73', 'NA-112', 'NA-119', 'NA-156', 'NA-158', 'NA-181', 'NA-185',
             'NA-202', 'NA-209', 'NA-232'],
}
NONMUSLIM_GENERAL = {'2018': ['NA-222'], '2024': ['NA-215']}   # Mahesh Kumar Malani, Tharparkar

# ---- name folding ----------------------------------------------------------
HON = r"^(?:(?:mr|mrs|ms|miss|mst|dr|prof|engr|haji|janab|mohtarma|muhtarma|madam|begum|syeda|syed|sayyeda|sardar|sardarzada|mian|ch|chaudhry|chaudhary|chaudry|malik|maulana|molana|mufti|sahibzada|sahibzadi|pir|makhdoom|nawab|nawabzada|nawabzadi|rana|raja|rao|rai|sheikh|shaikh|khawaja|kh|capt|major|col|justice|retd|r|adv|advocate|barrister|hafiz|qari|shahzadi|alhaj|al-haj)\.?\s+)+"
def fold(n):
    n = (n or '').lower()
    n = re.sub(r'^(women|balochistan|sindh|punjab|nwfp)[\w\s\-]*?[ivx]+\s+', '', n)   # 12th 'Women Punjab-III ' prefix
    n = re.sub(r'\(.*?\)', ' ', n)
    n = n.replace('&', ' ').replace(',', ' ')
    n = re.sub(r'\bmoham+[ae]d\b|\bmohd\b|\bmuhammed\b', 'muhammad', n)
    n = re.sub(r'\bhussein\b|\bhusain\b', 'hussain', n)
    n = re.sub(r'\bur[- ]?rehman\b|\bur[- ]?rahman\b|\brehman\b', 'rahman', n)
    n = re.sub(r'\bahmad\b', 'ahmed', n)
    n = re.sub(r'\bfahmida\b', 'fehmida', n)
    n = re.sub(r"[^a-z\s]", ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    n = re.sub(HON, '', n)
    return n
def squash(n): return fold(n).replace(' ', '')
def fix_ocr(n):
    # collapse stray internal spaces the 12th PDF left inside words ("Tehm ina")
    return re.sub(r'\b([A-Z][a-z]{1,4}) ([a-z]{2,})\b', lambda m: m.group(1)+m.group(2), n or '')

# ---- load spine ------------------------------------------------------------
cands = list(csv.DictReader(open(os.path.join(ROOT, 'data/linked/candidacies_final.csv'), encoding='utf-8')))
persons = {r['person_id']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data/linked/persons_final.csv'), encoding='utf-8'))}
by_sq = collections.defaultdict(set)
for r in cands:
    by_sq[r['name_squash']].add(r['person_id'])
    by_sq[squash(r['name_raw'])].add(r['person_id'])
for pid, p in persons.items():
    by_sq[squash(p['canonical_name'])].add(pid)
sq_keys = list(by_sq.keys())

def link(name):
    s = squash(name)
    if not s or len(s) < 8 or len(fold(name).split()) < 2: return None, 'none'
    ids = by_sq.get(s, set())
    if len(ids) == 1: return next(iter(ids)), 'exact'
    if len(ids) > 1: return None, 'ambiguous'
    m = difflib.get_close_matches(s, sq_keys, n=2, cutoff=0.92)
    if len(m) >= 1:
        ids = by_sq[m[0]]
        if len(ids) == 1 and (len(m) == 1 or by_sq[m[1]] == ids):
            return next(iter(ids)), 'fuzzy'
    return None, 'none'

def career(pid):
    rows = [r for r in cands if r['person_id'] == pid]
    return {'contested': sorted({int(r['year']) for r in rows}),
            'won': sorted({int(r['year']) for r in rows if r['outcome'] == 'Win'}),
            'name': persons[pid]['canonical_name'] if pid in persons else None}

def norm_prov(p):
    if not p: return None
    p = p.lower()
    if 'punjab' in p: return 'Punjab'
    if 'sindh' in p: return 'Sindh'
    if 'khyber' in p or 'nwfp' in p: return 'Khyber Pakhtunkhwa'
    if 'baloch' in p: return 'Balochistan'
    if 'islamabad' in p or 'fata' in p: return 'ICT/FATA'
    return p

# ---- largest remainder ------------------------------------------------------
def lr(basis, seats):
    """basis: {party: general seats}. Returns {party: seats} by Hare quota + largest remainders."""
    basis = {k: v for k, v in basis.items() if v > 0 and k not in ('IND', 'IND-true')}
    tot = sum(basis.values())
    if tot == 0: return {}
    q = {k: v * seats / tot for k, v in basis.items()}
    alloc = {k: int(q[k]) for k in q}
    rem = seats - sum(alloc.values())
    for k in sorted(q, key=lambda k: (-(q[k] - int(q[k])), -basis[k], k))[:rem]:
        alloc[k] += 1
    return {k: v for k, v in alloc.items() if v}

# ---- build per year ---------------------------------------------------------
audit = []
out = {'meta': {'house': HOUSE, 'general': GEN_SEATS, 'wquota': WQUOTA, 'nm_seats': NM_SEATS,
                'joiners': JOINERS, 'official_2024_first': OFFICIAL_2024_FIRST,
                'pti_ind_2024': PTI_IND_2024}, 'years': {}}
for y, asm in YEARS.items():
    raw = json.load(open(os.path.join(LINK, f'members_na{asm}.json'), encoding='utf-8'))
    members = raw['members'] if isinstance(raw, dict) else raw
    notes = raw.get('notes', []) if isinstance(raw, dict) else []

    # -- general seats from the spine
    wins = [r for r in cands if r['year'] == y and r['outcome'] == 'Win']
    gen_by_prov = collections.defaultdict(collections.Counter)
    gen_total = collections.Counter()
    winners = collections.defaultdict(list)
    for r in wins:
        c = cat(r['party'])
        if y == '2008' and c == 'JUI-F': c = 'MMA'     # JUI-F contested 2008 under the MMA name; ECP books it as MMA
        gen_total[c] += 1; gen_by_prov[norm_prov(r['province'])][c] += 1
        if not (y == '2024' and c == 'IND'):            # 2024 independents are not attributed PTI/non-PTI seat by seat
            winners[c].append({'na': r['na'], 'name': r['name_raw']})
    for c in winners: winners[c].sort(key=lambda w: int(w['na'].split('-')[1]))
    gen_display = dict(gen_total)
    if y == '2024':
        gen_display['PTI-IND'] = PTI_IND_2024
        gen_display['IND'] = gen_total['IND'] - PTI_IND_2024

    # -- reserved members from the roll
    women, nonmus = [], []
    w12 = [m for m in members if m['seat_type'] == 'reserved_women']
    for i, m in enumerate(members):
        if m['seat_type'] == 'general': continue
        name = fix_ocr(m['name'] or '')
        name_clean = re.sub(r'^(?:Women|Balochistan|Sindh|Punjab|NWFP)[\w\s\-]*?[IVX]+\s+', '', name).strip()
        prov = norm_prov(m.get('province'))
        if asm == 12 and m['seat_type'] == 'reserved_women':
            k = w12.index(m)   # PDF order = Punjab 35 / Sindh 14 / NWFP 8 / Balochistan 3
            prov = 'Punjab' if k < 35 else 'Sindh' if k < 49 else 'Khyber Pakhtunkhwa' if k < 57 else 'Balochistan'
        pid, how = link(name_clean)
        rec = {'name': name_clean, 'party': cat(m.get('party')), 'party_raw': m.get('party'),
               'province': prov if m['seat_type'] == 'reserved_women' else None,
               'na_id': m.get('na_id'), 'elected_via': m.get('elected_via'),
               'remarks': m.get('remarks') or None, 'person_id': pid}
        if pid:
            rec['career'] = career(pid)
        audit.append({'year': y, 'assembly': asm, 'seat_type': m['seat_type'], 'name': name_clean,
                      'party': rec['party'], 'person_id': pid or '', 'method': how,
                      'canonical': persons.get(pid, {}).get('canonical_name', '') if pid else ''})
        (women if m['seat_type'] == 'reserved_women' else nonmus).append(rec)

    # -- entitlement on election-day parties
    ent_w = {}
    for p in PROV_ORDER:
        ent_w[p] = lr(gen_by_prov[p], WQUOTA[y][p])
    ent_nm = lr(gen_total, NM_SEATS)
    ent_w_tot = collections.Counter()
    for p in ent_w:
        for k, v in ent_w[p].items(): ent_w_tot[k] += v

    # -- 2024 counterfactual: PTI-backed independents counted as one party
    cf = None
    if y == '2024':
        # province split of PTI-backed independents per ECP/Wikipedia: Punjab 55, KP 37, Balochistan 1 (=93);
        # scaled to our reconciled 85 (3 Punjab recounts to PML-N, Bajaur genuine) -> Punjab 52, KP 32, Balochistan 1
        cf_prov = {p: collections.Counter(gen_by_prov[p]) for p in PROV_ORDER}
        split = {'Punjab': 52, 'Khyber Pakhtunkhwa': 32, 'Balochistan': 1}
        for p, n in split.items():
            cf_prov[p]['PTI-IND'] = n; cf_prov[p]['IND'] -= n
        cf_tot = collections.Counter(gen_total); cf_tot['PTI-IND'] = PTI_IND_2024; cf_tot['IND'] -= PTI_IND_2024
        cfw = {p: lr(cf_prov[p], WQUOTA[y][p]) for p in PROV_ORDER}
        cfw_tot = collections.Counter()
        for p in cfw:
            for k, v in cfw[p].items(): cfw_tot[k] += v
        cf = {'women_by_prov': cfw, 'women': dict(cfw_tot), 'nonmuslim': lr(cf_tot, NM_SEATS),
              'basis_split': split}

    # -- official allocation
    if OFFICIAL[y]:
        off = {k: {'women': v[0], 'nonmuslim': v[1]} for k, v in OFFICIAL[y].items()}
    else:
        cw = collections.Counter(r['party'] for r in women); cn = collections.Counter(r['party'] for r in nonmus)
        off = {k: {'women': cw.get(k, 0), 'nonmuslim': cn.get(k, 0)} for k in set(cw) | set(cn)}

    # -- women & non-Muslims on general seats
    wg = [{'na': r['na'], 'name': r['name_raw'], 'party': cat(r['party']), 'province': norm_prov(r['province']),
           'person_id': r['person_id']} for r in wins if r['na'] in WOMEN_GENERAL[y]]
    ng = [{'na': r['na'], 'name': r['name_raw'], 'party': cat(r['party']), 'person_id': r['person_id']}
          for r in wins if r['na'] in NONMUSLIM_GENERAL.get(y, [])]
    assert len(wg) == len(WOMEN_GENERAL[y]), (y, len(wg))

    out['years'][y] = {
        'assembly': asm, 'polled': len(wins),
        'general': gen_display, 'winners': dict(winners), 'general_by_prov': {p: dict(c) for p, c in gen_by_prov.items()},
        'reserved_women': women, 'reserved_nonmuslim': nonmus,
        'entitlement': {'women_by_prov': ent_w, 'women': dict(ent_w_tot), 'nonmuslim': ent_nm},
        'counterfactual': cf, 'official': off,
        'women_general': wg, 'nonmuslim_general': ng,
        'roll_notes': notes,
    }
    # console summary
    print(f"\n== {y} (NA-{asm}) general {len(wins)} | roll women {len(women)} nm {len(nonmus)}")
    print("  entitlement W:", dict(ent_w_tot), " NM:", ent_nm)
    print("  official    W:", {k: v['women'] for k, v in off.items()}, " NM:", {k: v['nonmuslim'] for k, v in off.items()})
    if cf: print("  counterfactual W:", cf['women'], " NM:", cf['nonmuslim'])
    lk = collections.Counter(a['method'] for a in audit if a['year'] == y)
    print("  linkage:", dict(lk))

json.dump(out, open(os.path.join(OUT, 'house.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
with open(os.path.join(OUT, 'reserved_linkage.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(audit[0].keys())); w.writeheader(); w.writerows(audit)
print('\nwrote', os.path.join(OUT, 'house.json'), os.path.getsize(os.path.join(OUT, 'house.json')), 'bytes')
