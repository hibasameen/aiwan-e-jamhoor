#!/usr/bin/env python3
"""
Parse cached ElectionPakistani constituency pages into data/results_{year}/ CSVs.

Generalised version of parse_ge1988_cache.py, used for the years whose live pages
are unreachable from the build sandbox (fetched with the web_fetch tool and cached
one file per seat at data/results_{year}/_cache/NA-{n}.md).

    python3 scripts/parse_gecache.py 1985 207
    python3 scripts/parse_gecache.py 1977 200

Writes na_{year}_candidates.csv and na_{year}_constituency.csv, identical schema to
results_1988/. Registered electorate / votes polled / turnout are not published per
seat, so those columns are left blank.
"""
import os, re, csv, sys, collections

STAR = re.compile(r'\*+')
PARTY_FIX = {'ppp': 'PPP', 'indpendent': 'Independent', 'independant': 'Independent',
             'indepdnent': 'Independent', 'indenpendent': 'Independent'}
SKIP = re.compile(r'(?i)^(candidate\s*name|party(\s*name)?|votes?|vote|total|valid|rejected|'
                  r'registered|turnout|polled|home\s*page|privacy|disclaimer|policy|'
                  r'general election|na[\s-]?\d+\s|\[|!\[|http)')
# prose/blurb that must never be mistaken for a candidate name
PROSE = re.compile(r'(?i)detail|complete|elected|\bresult\b|constituency|provide|'
                   r'information|consolidated|general election|votes detail')

def fix_party(p):
    return PARTY_FIX.get(p.lower(), p)

def has_party_col(text):
    """1977/1988 pages carry a Party column; the non-party 1985 pages do not."""
    return bool(re.search(r'(?i)party\s*name|\|\s*\*\*\s*party', text))

def cells_of(line):
    line = line.strip()
    if not line.startswith('|'):
        return None
    return [STAR.sub('', c).strip() for c in line.strip('|').split('|')]

def is_sep(parts):
    return all(re.fullmatch(r':?-{2,}:?', c or '-') for c in parts)

def parse_pipe(text, has_party):
    cands, named = [], []
    for line in text.splitlines():
        parts = cells_of(line)
        # >=2 so the non-party 1985 pages (Candidate | Votes, no Party column) parse too
        if not parts or len(parts) < 2 or is_sep(parts):
            continue
        votes, vi = None, None
        for i, c in enumerate(parts):
            t = c.replace(',', '').replace('.', '')
            if t.isdigit() and 0 < int(t) < 1_000_000 and len(t) >= 2:
                votes, vi = int(t), i
        others = [c for i, c in enumerate(parts) if i != vi and c] if vi is not None \
                 else [c for c in parts if c]
        if not others:
            continue
        name = others[0]
        if not re.search(r'[A-Za-z]', name) or SKIP.match(name):
            continue
        party = (fix_party(others[1]) if len(others) > 1 else '') if has_party else ''
        if votes is not None:
            cands.append((name, party, votes))
        elif len(name) <= 45 and not PROSE.search(name):
            # winner named but no count (uncontested, or source blank).
            # gate on a plausible person-name so the blurb/footer never leaks in.
            named.append((name, party, None))
    if not cands and named:
        cands = named[:1]
    return cands

def parse_plain(text, has_party):
    """Fallback for pages the fetcher rendered without pipe rows: header and each
    cell on its own line. Handles both the single-line header ('Candidate Name
    Party Votes') and the split header ('Candidate Name |' / 'Party Name |' /
    'Vote |')."""
    cells = []
    for l in text.splitlines():
        c = re.sub(r'\|\s*$', '', l).strip()          # drop trailing pipe
        c = STAR.sub('', c).strip()
        if c:
            cells.append(c)
    # locate header
    start = ncols = None
    for i, c in enumerate(cells):
        lc = c.lower()
        if re.match(r'candidate\s*name', lc):
            if 'vote' in lc:                            # single-line header
                ncols = 3 if 'party' in lc else 2
                start = i + 1
            else:                                       # split header lines follow
                j = i + 1
                while j < len(cells) and re.fullmatch(r'(?i)party(\s*name)?|votes?|vote', cells[j]):
                    j += 1
                ncols = max(2, j - i)
                start = j
            break
    if start is None:
        return []
    votecol = ncols - 1
    cands = []
    for k in range(start, len(cells) - (ncols - 1), ncols):
        grp = cells[k:k + ncols]
        name = grp[0]
        if not re.search(r'[A-Za-z]', name) or SKIP.match(name):
            break                                       # hit footer / next section
        vtxt = grp[votecol].replace(',', '')
        votes = int(vtxt) if vtxt.isdigit() else None
        party = fix_party(grp[1]) if (has_party and ncols >= 3) else ''
        cands.append((name, party, votes))
    return cands

def parse(text):
    title = ''
    m = re.search(r'^title:\s*(.+)$', text, re.I | re.M)
    if m:
        title = m.group(1).strip()
    else:
        m = re.search(r'^(NA[-\s]?\d+.*?Detail Election Result.*)$', text, re.I | re.M)
        if m:
            title = m.group(1).strip()
    hp = has_party_col(text)
    cands = parse_pipe(text, hp)
    if not cands:
        cands = parse_plain(text, hp)
    return title, cands

def const_name(title, n):
    nm = re.sub(r'(?i)^.*?NA[-\s]?%d\s*' % n, '', title)
    nm = re.split(r'(?i)\bDetail\b|\bElection\b|\bResult\b', nm)[0]
    return nm.strip(' -–:')

def main(year, hi):
    OUT = f'data/results_{year}'
    CACHE = f'{OUT}/_cache'
    cand_rows, cons_rows, missing, thin = [], [], [], []
    for n in range(1, hi + 1):
        path = f'{CACHE}/NA-{n}.md'
        if not os.path.exists(path):
            missing.append(n); continue
        text = open(path, encoding='utf-8').read()
        title, cands = parse(text)
        if not cands:
            missing.append(n); print(f'NA-{n}: no candidates parsed ({title[:50]})'); continue
        cands.sort(key=lambda x: (x[2] is not None, x[2] or 0), reverse=True)
        if len(cands) < 2:
            thin.append(n)
        na = f'NA-{n}'
        nm = const_name(title, n)
        blank = lambda v: '' if v is None else v
        for r, (cn, cp, cv) in enumerate(cands, 1):
            cand_rows.append({'na': na, 'candidate_name': cn, 'party': cp, 'votes': blank(cv), 'rank': r})
        w, ru = cands[0], (cands[1] if len(cands) > 1 else ('', '', None))
        cons_rows.append({'na': na, 'constituency_name': nm, 'province': '',
                          'winner_name': w[0], 'winner_party': w[1], 'winner_votes': blank(w[2]),
                          'runnerup_name': ru[0], 'runnerup_party': ru[1], 'runnerup_votes': blank(ru[2]),
                          'registered_voters': '', 'votes_polled': '', 'turnout_pct': ''})

    os.makedirs(OUT, exist_ok=True)
    with open(f'{OUT}/na_{year}_candidates.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=['na', 'candidate_name', 'party', 'votes', 'rank'])
        wr.writeheader(); wr.writerows(cand_rows)
    with open(f'{OUT}/na_{year}_constituency.csv', 'w', newline='', encoding='utf-8') as f:
        cols = ['na', 'constituency_name', 'province', 'winner_name', 'winner_party',
                'winner_votes', 'runnerup_name', 'runnerup_party', 'runnerup_votes',
                'registered_voters', 'votes_polled', 'turnout_pct']
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(cons_rows)

    print(f'\n[{year}] seats written : {len(cons_rows)} of {hi}')
    print(f'[{year}] candidate rows: {len(cand_rows)}')
    print(f'[{year}] missing/failed: {missing}')
    print(f'[{year}] only 1 candidate (check): {thin}')
    print(f'[{year}] party tally   :', collections.Counter(r["winner_party"] for r in cons_rows).most_common(12))

if __name__ == '__main__':
    y = sys.argv[1]
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 207
    main(y, hi)
