#!/usr/bin/env python3
"""
Scrape the 1988 National Assembly results from ElectionPakistani, in the same
shape as data/results_1990/.

    python3 scripts/scrape_ge1988.py            # all 207 seats
    python3 scripts/scrape_ge1988.py 1 20       # a range, for a trial run

Writes data/results_1988/na_1988_candidates.csv and na_1988_constituency.csv.
Pages carry candidate names, parties and votes but no registered electorate or
turnout, so those columns are left blank — the same situation as 1990/2024.

Be polite: the default delay is 1s per page, so a full run takes ~4 minutes.
"""
import sys, os, re, time, csv
import urllib.request

BASE = 'https://www.electionpakistani.com/ge1988/NA-{}.htm'
OUT = 'data/results_1988'
UA = {'User-Agent': 'Aiwan-e-Jamhoor research scraper (contact: repository owner)'}
DELAY = 1.0

def fetch(n, tries=3):
    url = BASE.format(n)
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
            for enc in ('utf-8', 'cp1252', 'latin-1'):
                try: return url, raw.decode(enc)
                except UnicodeDecodeError: continue
            return url, raw.decode('utf-8', 'replace')
        except Exception as e:
            if k == tries - 1: return url, None
            time.sleep(2 * (k + 1))

CELL = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.I | re.S)
ROW  = re.compile(r'<tr[^>]*>(.*?)</tr>', re.I | re.S)
TAG  = re.compile(r'<[^>]+>')

def clean(s):
    s = TAG.sub(' ', s)
    s = (s.replace('&nbsp;', ' ').replace('&amp;', '&')
          .replace('&#39;', "'").replace('&quot;', '"'))
    return re.sub(r'\s+', ' ', s).strip()

def parse(html):
    """Return (constituency_name, [(name, party, votes), ...])."""
    title = ''
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
    if m: title = clean(m.group(1))
    best = []
    for rowhtml in ROW.findall(html):
        cells = [clean(c) for c in CELL.findall(rowhtml)]
        if len(cells) < 3: continue
        # a candidate row has a vote-like integer in one cell
        votes, vi = None, None
        for i, c in enumerate(cells):
            t = c.replace(',', '').replace('.', '')
            if t.isdigit() and 0 < int(t) < 1_000_000 and len(t) >= 2:
                votes, vi = int(t), i
        if votes is None: continue
        others = [c for i, c in enumerate(cells) if i != vi and c]
        if not others: continue
        name = others[0]
        party = others[1] if len(others) > 1 else ''
        if not re.search(r'[A-Za-z]', name): continue
        if re.match(r'(?i)total|valid|rejected|registered|turnout|polled', name): continue
        best.append((name, party, votes))
    return title, best

def main(lo=1, hi=207):
    os.makedirs(OUT, exist_ok=True)
    cand_rows, cons_rows, failed, thin = [], [], [], []
    for n in range(lo, hi + 1):
        url, html = fetch(n)
        if not html:
            failed.append(n); print(f'NA-{n}: FETCH FAILED'); continue
        title, cands = parse(html)
        if not cands:
            failed.append(n); print(f'NA-{n}: no candidate rows parsed  ({title[:60]})'); continue
        cands.sort(key=lambda x: -x[2])
        if len(cands) < 2: thin.append(n)
        na = f'NA-{n}'
        nm = re.sub(r'(?i)^.*?NA[-\s]?%d\s*' % n, '', title).split('Election')[0].strip(' -–:')
        for r, (cn, cp, cv) in enumerate(cands, 1):
            cand_rows.append({'na': na, 'candidate_name': cn, 'party': cp, 'votes': cv, 'rank': r})
        w, ru = cands[0], (cands[1] if len(cands) > 1 else ('', '', ''))
        cons_rows.append({'na': na, 'constituency_name': nm, 'province': '',
                          'winner_name': w[0], 'winner_party': w[1], 'winner_votes': w[2],
                          'runnerup_name': ru[0], 'runnerup_party': ru[1], 'runnerup_votes': ru[2],
                          'registered_voters': '', 'votes_polled': '', 'turnout_pct': ''})
        print(f'NA-{n}: {len(cands):>2} candidates | winner {w[0][:28]} ({w[1]}) {w[2]:,}')
        time.sleep(DELAY)

    with open(f'{OUT}/na_1988_candidates.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=['na', 'candidate_name', 'party', 'votes', 'rank'])
        wr.writeheader(); wr.writerows(cand_rows)
    with open(f'{OUT}/na_1988_constituency.csv', 'w', newline='', encoding='utf-8') as f:
        cols = ['na', 'constituency_name', 'province', 'winner_name', 'winner_party',
                'winner_votes', 'runnerup_name', 'runnerup_party', 'runnerup_votes',
                'registered_voters', 'votes_polled', 'turnout_pct']
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(cons_rows)

    print(f'\nseats written : {len(cons_rows)} of {hi - lo + 1}')
    print(f'candidate rows: {len(cand_rows)}')
    print(f'failed        : {failed}')
    print(f'only 1 candidate parsed (check these): {thin}')
    import collections
    print('party tally   :', collections.Counter(r["winner_party"] for r in cons_rows).most_common(12))

if __name__ == '__main__':
    a = [int(x) for x in sys.argv[1:3]] if len(sys.argv) > 2 else [1, 207]
    main(*a)
