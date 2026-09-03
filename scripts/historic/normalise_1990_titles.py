#!/usr/bin/env python3
"""
Normalise the scraped 1990 constituency titles into the same convention the
1993 and 1997 returns use, so the existing district pipeline handles 1990
without modification.

ElectionPakistani page titles carry residue ("Lahore I Full", "Rawalpindi II
Result GE") and write cross-district seats as a space-separated list of
districts ("Sibi Kohlu Dera Bugti Ziarat") rather than with "-cum-". District
names are recovered by greedy longest-match against the vocabulary already
established for 1993, so multi-word districts (Dera Ghazi Khan, Toba Tek Singh)
are not split by accident.
"""
import csv, io, re, json, collections, sys

JUNK = re.compile(r'(?i)\b(complete|full|general|vote|votes|result|results|ge|detail|'
                  r'election|constituency|na|19\d\d|20\d\d)\b')
# the FATA block is NA-27..NA-34 in this delimitation; the ordinal gives the agency
TRIBAL = {1:'Mohmand',2:'Kurram',3:'Orakzai',4:'North Waziristan',
          5:'South Waziristan',6:'Bajaur',7:'Khyber',8:'__FR__'}
ROMAN = {'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,'ix':9,'x':10,
         'xi':11,'xii':12,'xiii':13,'xiv':14,'xv':15}
ALIAS = {'hyederabad':'Hyderabad','sukkar':'Sukkur','dikhan':'Dera Ismail Khan',
         'dgkhan':'Dera Ghazi Khan','naushero feroze':'Naushero Feroz','kachhi':'Bolan',
         'gawadar':'Gwadar','attok':'Attock','abbbottabad':'Abbottabad',
         'muzaffaragarh':'Muzaffargarh','labdela':'Lasbela','thar':'Tharparkar',
         'jhall magsi':'Jhal Magsi','bunair':'Buner','batagram':'Battagram',
         'mirpurkhas':'Mirpur Khas','rahimyar khan':'Rahim Yar Khan','umerkot':'Umer Kot',
         'malakand protected area':'Malakand','dikhan':'Dera Ismail Khan',
         'dgkhan':'Dera Ghazi Khan','digkhan':'Dera Ghazi Khan'}
norm = lambda s: re.sub(r'[^a-z]', '', s.lower())

def build_vocab(units_path):
    d = json.load(io.open(units_path, encoding='utf-8'))
    vocab = set(d['1993']) | set(d['1997'])
    vocab |= {'Dera Ismail Khan', 'Dera Ghazi Khan', 'Islamabad'}
    return sorted(vocab, key=lambda s: -len(s))     # longest first for greedy match

def split_districts(text, vocab):
    """Greedily consume known district names from the front of `text`."""
    toks = [t for t in re.split(r'[\s,]+', text) if t]
    out, i = [], 0
    while i < len(toks):
        hit = None
        for take in range(min(4, len(toks) - i), 0, -1):
            cand = ' '.join(toks[i:i + take])
            c = ALIAS.get(cand.lower().strip(), ALIAS.get(norm(cand), cand))
            for v in vocab:
                if norm(v) == norm(c):
                    hit = (v, take); break
            if hit: break
        if hit:
            out.append(hit[0]); i += hit[1]
        else:
            out.append(None); i += 1          # unrecognised token
    return out

def normalise(title, vocab, na=None):
    t = title.replace('.', ' ')
    t = re.sub(r'(?i)^\s*na[-\s]?\d+\s*', '', t)      # leading "NA-122 "
    t = JUNK.sub(' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' -–:')
    ordinal = None
    m = re.search(r'\s([IVXL]+|\d{1,2})$', t, re.I)
    if m:
        tok = m.group(1)
        ordinal = int(tok) if tok.isdigit() else ROMAN.get(tok.lower())
        if ordinal: t = t[:m.start()].strip()
    if re.match(r'(?i)^tribal\s*area', t):
        n = ordinal or ((int(na.split('-')[1]) - 26) if na else None)
        ag = TRIBAL.get(n)
        if ag == '__FR__':
            return 'Tribal Area 8: Tribal Areas Attached To Peshawar, Kohat, Bannu, Dera Ismail Khan, Tank And Lakki Marwat Districts', 0, t
        if ag: return f'Tribal Area {n} - {ag} Agency', 0, t
    parts = split_districts(t, vocab)
    good = [p for p in parts if p]
    unknown = len(parts) - len(good)
    if not good: return None, unknown, t
    name = '-Cum-'.join(good)
    if ordinal and len(good) == 1: name = f'{name} {ordinal}'
    return name, unknown, t

def main(cs, units, write=False):
    vocab = build_vocab(units)
    rows = list(csv.DictReader(io.open(cs, encoding='utf-8')))
    bad, changed = [], 0
    for r in rows:
        new, unknown, residue = normalise(r['constituency_name'], vocab, r['na'])
        if new is None or unknown:
            bad.append((r['na'], r['constituency_name'], new, residue)); continue
        if new != r['constituency_name']: changed += 1
        r['constituency_name'] = new
    print(f'normalised {changed} of {len(rows)} titles')
    print(f'could not fully resolve: {len(bad)}')
    for na, old, new, res in bad: print(f'   {na:<8} {old!r:<42} -> {new!r}  residue={res!r}')
    cnt = collections.Counter()
    for r in rows:
        for p in re.split(r'(?i)\s*-\s*cum\s*-\s*',
                          re.sub(r'\s*(\d+)$', '', r['constituency_name'])): cnt[p.strip()] += 1
    print(f'distinct districts after normalisation: {len(cnt)}')
    if write and not bad:
        with io.open(cs, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print('written')
    return bad

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], write='--write' in sys.argv)
