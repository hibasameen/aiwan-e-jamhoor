#!/usr/bin/env python3
"""
Parse cached GE-1988 constituency pages into the data/results_1988/ CSVs.

The live pages (https://www.electionpakistani.com/ge1988/NA-{n}.htm) are not
reachable from the build sandbox, so they are fetched with the web_fetch tool
and cached one file per seat at data/results_1988/_cache/NA-{n}.md. This script
reads that cache and writes na_1988_candidates.csv / na_1988_constituency.csv,
in the identical shape to results_1990/. Re-runnable and offline.

    python3 scripts/parse_ge1988_cache.py

Registered electorate, votes polled and turnout are not published per seat, so
those columns are left blank — same as 1990/2024.
"""
import os, re, csv, glob, collections

CACHE = 'data/results_1988/_cache'
OUT = 'data/results_1988'
STAR = re.compile(r'\*+')

# The source has a few casing/spelling slips in the party column.
PARTY_FIX = {'ppp': 'PPP', 'indpendent': 'Independent', 'independant': 'Independent',
             'indepdnent': 'Independent', 'indenpendent': 'Independent'}

def fix_party(p):
    return PARTY_FIX.get(p.lower(), p)

def cells_of(line):
    """Split a markdown table row into cleaned cells."""
    line = line.strip()
    if not line.startswith('|'):
        return None
    parts = [STAR.sub('', c).strip() for c in line.strip('|').split('|')]
    return parts

def is_sep(parts):
    return all(re.fullmatch(r':?-{2,}:?', c or '-') for c in parts)

SKIP = re.compile(r'(?i)^(candidate\s*name|total|valid|rejected|registered|turnout|polled)')

def parse_pipe(text):
    """Parse the standard markdown pipe table. votes may be None when the
    source leaves the vote cell blank (winner named but count not published)."""
    cands, named = [], []
    for line in text.splitlines():
        parts = cells_of(line)
        if not parts or len(parts) < 3 or is_sep(parts):
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
        party = fix_party(others[1]) if len(others) > 1 else ''
        if votes is not None:
            cands.append((name, party, votes))
        else:
            named.append((name, party, None))
    if not cands and named:      # winner named but source omits vote counts
        cands = named[:1]
    return cands

def parse_plain(text):
    """Fallback for pages rendered without pipes: a 'Candidate Name Party Votes'
    header followed by name/party/votes each on its own line (e.g. NA-135)."""
    lines = [l.strip() for l in text.splitlines()]
    start = None
    for i, l in enumerate(lines):
        if re.search(r'(?i)candidate\s*name\s+party\s+votes', l):
            start = i + 1
            break
    if start is None:
        return []
    seq = [l for l in lines[start:] if l]
    cands = []
    for i in range(0, len(seq) - 2, 3):
        name, party, votes = seq[i], seq[i + 1], seq[i + 2].replace(',', '')
        if not votes.isdigit() or not re.search(r'[A-Za-z]', name) or SKIP.match(name):
            break
        cands.append((name, fix_party(party), int(votes)))
    return cands

def parse(text):
    """Return (title, [(name, party, votes), ...]) from one cached page."""
    title = ''
    m = re.search(r'^title:\s*(.+)$', text, re.I | re.M)
    if m:
        title = m.group(1).strip()
    else:  # plain-rendered pages carry no frontmatter; use the heading line
        m = re.search(r'^(NA[-\s]?\d+.*?Detail Election Result.*)$', text, re.I | re.M)
        if m:
            title = m.group(1).strip()
    cands = parse_pipe(text)
    if not cands:
        cands = parse_plain(text)
    return title, cands

def const_name(title, n):
    nm = re.sub(r'(?i)^.*?NA[-\s]?%d\s*' % n, '', title)
    nm = re.split(r'(?i)\bDetail\b|\bElection\b|\bResult\b', nm)[0]
    return nm.strip(' -–:')

def main():
    cand_rows, cons_rows, missing, thin = [], [], [], []
    for n in range(1, 208):
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
    with open(f'{OUT}/na_1988_candidates.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=['na', 'candidate_name', 'party', 'votes', 'rank'])
        wr.writeheader(); wr.writerows(cand_rows)
    with open(f'{OUT}/na_1988_constituency.csv', 'w', newline='', encoding='utf-8') as f:
        cols = ['na', 'constituency_name', 'province', 'winner_name', 'winner_party',
                'winner_votes', 'runnerup_name', 'runnerup_party', 'runnerup_votes',
                'registered_voters', 'votes_polled', 'turnout_pct']
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(cons_rows)

    print(f'\nseats written : {len(cons_rows)} of 207')
    print(f'candidate rows: {len(cand_rows)}')
    print(f'missing/failed: {missing}')
    print(f'only 1 candidate (check): {thin}')
    print('party tally   :', collections.Counter(r["winner_party"] for r in cons_rows).most_common(12))

if __name__ == '__main__':
    main()
