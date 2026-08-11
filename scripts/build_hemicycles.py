#!/usr/bin/env python3
"""
Regenerate the home-page hemicycle strip from the map's own results, so every
election on the map appears there too.

The arcs match the existing markup exactly: a half-annulus centred at (110,118)
with outer radius 104 and inner 54, swept from pi to 2pi, segments ordered by
seats won and separated by a small angular gap.

Each card also carries a national vote-share swing line: the two largest
absolute changes (percentage points of valid votes in directly contested
general seats) versus the preceding election. Lineage-linked comparisons
(IJI->PML-N, PPP->PDA->PPP, JUI-F<->MMA, 2018 PTI->2024 independents) are
marked with an asterisk; 1985 was non-party so 1988 is compared with 1977.
"""
import json, io, math, re

# swing baselines: which election each year is compared against
# (default: previous entry in YL; None = no swing line)
BASE_OVERRIDE = {'1977': None, '1985': None, '1988': '1977'}

# lineage links: {year: {successor_cat_in_year: predecessor_cat_in_base}}
LINEAGE = {
    '1990': {'PDA': 'PPP'},
    '1993': {'PML-N': 'IJI', 'PPP': 'PDA'},
    '2002': {'MMA': 'JUI-F'},
    '2008': {'JUI-F': 'MMA'},
    '2018': {'MMA': 'JUI-F'},
    '2024': {'PTI': 'PTI', 'JUI-F': 'MMA'},
}

# 2024 vote shares come from FAFEN's Form-47 compilation rather than our
# own per-seat totals, because FAFEN classifies each PTI-backed independent
# as PTI — the split we cannot derive from the returns, which record them
# only as independents. Source: FAFEN, "2024 National and Provincial
# Elections: Votes Polled and Party Shares in Votes and Seats" (Dec 2024),
# Table 1: NA valid votes 59,513,717 across 265 polled constituencies.
VOTE_OVERRIDE = {
    '2024': {'total': 59513717,
             'votes': {'PTI': 18032955, 'PML-N': 14121509, 'PPP': 8235875,
                       'IND': 7008715, 'TLP': 2918086}},
}

# categories whose vote is an estimate rather than a declared-label total.
PROXY_CATS = {}

# per-year override of which swings to display (default: top-2 by |Δ|).
# 2024: the residual-IND "swing" is an artifact of the proxy split, not a
# real movement away from independents — show the three main parties.
SWING_SHOW = {'2024': ['PTI', 'PML-N', 'PPP']}

# how a category is named on the card. 2024's PTI estimate is drawn from
# the independent line, so it is labelled as such.
DISPLAY_LABEL = {'2024': {'PTI': 'IND (PTI)'}}

# seat-side (hemicycle) overrides. 2024's independent bloc is split into
# PTI-backed and genuine, reconciled seat-by-seat against FAFEN:
#
#   FAFEN (265 seats, initial Final Consolidated Form-49 results)
#       88 PTI-backed + 13 genuine = 101 independents;  PML-N 75
#   - 3 ECP recounts that moved PTI-backed independents to PML-N:
#       NA-79 Gujranwala-III, NA-81 Gujranwala-V, NA-154 Lodhran-I
#       (upheld by the Supreme Court)      -> 85 PTI-backed; PML-N 78 ✓ ours
#   + 1 NA-8 Bajaur, postponed on 8 Feb and polled 21 Apr, so outside
#       FAFEN's 265. Won by Mubarak Zeb Khan, who beat the SIC/PTI-backed
#       Gul Zafar Khan, so he counts as genuine  -> 14 genuine
#   = 85 + 14 = 99 independents ✓ ours, across 266 seats ✓
#
# Wikipedia's 93-of-103 is the looser cross-check. Our data is later than
# FAFEN's brief (post-recount, plus the Bajaur by-poll), which is why the
# totals differ. 'cat' renames the data-cat attribute to dodge the
# dark-mode grey rule for IND.
SEAT_OVERRIDE = {'2024': {'IND': {'label': 'IND (PTI)',
                                  'colour': '#7a1f3d',
                                  'cat': 'PTI-IND'}}}

# {year: {cat: (seats_carved_off, new_cat)}} — the remainder keeps the
# original category (and so picks up SEAT_OVERRIDE above).
SEAT_SPLIT = {'2024': {'IND': (14, 'IND-true')}}

def seat_style(y, c, COL):
    if c == 'IND-true':
        return ('IND', COL.get('IND', COL['Other']), 'IND')
    o = SEAT_OVERRIDE.get(y, {}).get(c, {})
    return (o.get('label', c),
            o.get('colour', COL.get(c, COL['Other'])),
            o.get('cat', c))

MAP = 'map.html'
IDX = 'index.html'
OUT = 'index.html'

CX, CY, RO, RI, GAP = 110.0, 118.0, 104.0, 54.0, 0.0057

def pt(th, r):
    return f'{CX + r*math.cos(th):.1f} {CY + r*math.sin(th):.1f}'

def arcs(totals, n):
    out, th = [], math.pi
    for i, (cat, seats, colour) in enumerate(totals):
        span = math.pi * seats / n
        a0 = th + (GAP if i else 0.0)
        a1 = th + span
        if a1 <= a0: a1 = a0 + 1e-4
        out.append(
            f'<path d="M{pt(a0,RO)} A{RO:.0f} {RO:.0f} 0 0 1 {pt(a1,RO)} '
            f'L{pt(a1,RI)} A{RI:.0f} {RI:.0f} 0 0 0 {pt(a0,RI)} Z" '
            f'fill="{colour}" data-cat="{cat}" stroke="var(--surface)" stroke-width="0.6"/>')
        th = a1
    return ''.join(out)

def vote_shares(y, R, cat):
    """National % of valid votes by party category for one election.
    Uses VOTE_OVERRIDE where a published compilation supersedes our own
    per-seat totals (2024: FAFEN, which resolves PTI-backed independents)."""
    o = VOTE_OVERRIDE.get(y)
    if o:
        return {k: 100.0 * v / o['total'] for k, v in o['votes'].items()}
    t, tot = {}, 0
    for r in R[y].values():
        for c in r.get('cands') or []:
            v = c.get('v')
            if v is None:
                continue
            t[cat(c['p'])] = t.get(cat(c['p']), 0) + v
            tot += v
    return {k: 100.0 * v / tot for k, v in t.items()} if tot else {}

def swings(y, R, YL, cat):
    """Top-2 absolute vote-share swings for year y vs its baseline.
    Returns list of (cat, delta_pp, linked_flag)."""
    base = BASE_OVERRIDE.get(y, YL[YL.index(y) - 1] if YL.index(y) else None)
    if base is None:
        return None
    cur, prev = vote_shares(y, R, cat), vote_shares(base, R, cat)
    link = LINEAGE.get(y, {})
    consumed = set(link.values())
    rows = []
    for c in set(cur) | set(prev):
        if c == 'Other':
            continue
        if c in link:                       # successor vs mapped predecessor
            rows.append((c, cur.get(c, 0) - prev.get(link[c], 0), True))
        elif c in consumed:                 # predecessor absorbed by successor
            continue
        else:
            rows.append((c, cur.get(c, 0) - prev.get(c, 0), False))
    if y in SWING_SHOW:
        by_cat = {r[0]: r for r in rows}
        return [by_cat[c] for c in SWING_SHOW[y] if c in by_cat]
    rows.sort(key=lambda r: -abs(r[1]))
    return rows[:2]

def share_html(y, R, cat, COL):
    """Vote-share bar + labels: top-3 national shares of valid votes.
    Sits under the seat hemicycle so votes vs seats can be compared."""
    sh = vote_shares(y, R, cat)
    rows = sorted(((c, v) for c, v in sh.items() if c != 'Other'),
                  key=lambda kv: -kv[1])[:3]
    proxy = PROXY_CATS.get(y, set())
    lab_of = DISPLAY_LABEL.get(y, {})
    segs, labs = [], []
    for c, v in rows:
        name = lab_of.get(c, c)
        star = '*' if c in proxy and c not in lab_of else ''
        segs.append(f'<i style="width:{v:.1f}%;background:{COL.get(c, COL["Other"])}" '
                    f'title="{name} {v:.1f}% of votes"></i>')
        labs.append(f'{name}{star}&nbsp;<b>{v:.1f}%</b>')
    rest = 100.0 - sum(v for _, v in rows)
    if rest > 0.05:
        segs.append(f'<i class="rest" style="width:{rest:.1f}%" '
                    f'title="all others {rest:.1f}% of votes"></i>')
    return ('      <div class="hemi-share">\n'
            f'        <div class="sb">{"".join(segs)}</div>\n'
            f'        <div class="sl"><span class="k">vote share</span> {" · ".join(labs)}</div>\n'
            '      </div>\n')

def swing_html(y, R, YL, cat):
    if y == '1985':
        return '      <div class="hemi-swing">non-party — swing n/a</div>\n'
    rows = swings(y, R, YL, cat)
    if not rows:
        return '      <div class="hemi-swing">series baseline</div>\n'
    bits = []
    for c, d, linked in rows:
        arrow = '▲' if d >= 0 else '▼'
        cls = 'up' if d >= 0 else 'dn'
        lab_of = DISPLAY_LABEL.get(y, {})
        name = lab_of.get(c, c)
        star = '' if c in lab_of else ('*' if linked or c in PROXY_CATS.get(y, ()) else '')
        bits.append(f'{name} <span class="{cls}">{arrow}{abs(d):.1f}</span>{star}')
    vs = ' vs 1977' if y == '1988' else ''
    return ('      <div class="hemi-swing"><span class="k">swing, pp</span> '
            f'{" · ".join(bits)}{vs}</div>\n')

def main():
    s = io.open(MAP, encoding='utf-8').read()
    dec = json.JSONDecoder()
    R, _ = dec.raw_decode(s, s.index('{', s.find('window.RESULTS=')))
    i = s.find('const PARTY_CAT='); CAT = eval(s[i + len('const PARTY_CAT='):s.index('};', i) + 1])
    i = s.find('const COLORS='); COL = eval(s[i + len('const COLORS='):s.index('};', i) + 1])
    i = s.find('CAT_ORDER='); ORDER = eval(s[i + len('CAT_ORDER='):s.index('];', i) + 1])
    i = s.find('const YL='); YL = eval(s[i + len('const YL='):s.index('];', i) + 1])
    cat = lambda p: CAT.get(p, 'Other')

    cards = []
    for y in reversed(YL):          # newest first
        res = R[y]
        t = {}
        for r in res.values(): t[cat(r['wp'])] = t.get(cat(r['wp']), 0) + 1
        for c, (n_off, new_c) in SEAT_SPLIT.get(y, {}).items():
            if t.get(c, 0) > n_off:
                t[c] -= n_off
                t[new_c] = t.get(new_c, 0) + n_off
        rows = sorted(t.items(), key=lambda kv: (-kv[1], ORDER.index(kv[0]) if kv[0] in ORDER else 99))
        n = sum(v for _, v in rows)
        totals = [(seat_style(y, c, COL)[2], v, seat_style(y, c, COL)[1])
                  for c, v in rows]
        top, second = rows[0], (rows[1] if len(rows) > 1 else None)
        t_lab, t_col, t_cat = seat_style(y, top[0], COL)
        s_lab = seat_style(y, second[0], COL)[0] if second else None
        cards.append(
            f'      <a class="hemi" href="map.html?year={y}">\n'
            f'      <svg viewBox="0 0 220 126" role="img" aria-label="{y} seat share">\n'
            f'        {arcs(totals, n)}\n'
            f'        <line x1="110" y1="8" x2="110" y2="66" stroke="var(--ink)" stroke-width="1.2"/>\n'
            f'      </svg>\n'
            f'      <div class="hemi-year"><span class="yr">{y}</span>'
            f'<span class="seats">{n} seats</span></div>\n'
            f'      <div class="hemi-top"><span class="sw" data-cat="{t_cat}" '
            f'style="background:{t_col}"></span>'
            f'<span>{t_lab}</span><span class="n">{top[1]}</span></div>\n'
            + (f'      <div class="hemi-runner">then {s_lab} {second[1]}</div>\n' if second else '')
            + share_html(y, R, cat, COL)
            + swing_html(y, R, YL, cat)
            + '    </a>')

    idx = io.open(IDX, encoding='utf-8').read()
    a = idx.index('<div class="hemis">')
    b = idx.index('<div class="strip-note">')
    head = idx[:a]
    tail = idx[b:]
    block = '<div class="hemis">\n' + '\n'.join(cards) + '\n    </div>\n\n    '
    idx = head + block + tail
    io.open(OUT, 'w', encoding='utf-8').write(idx)
    print(f'rebuilt {len(cards)} hemicycles: {", ".join(reversed(YL))}')
    for y, c in zip(reversed(YL), cards):
        m = re.search(r'<span class="seats">(\d+) seats', c)
        t = re.search(r'<span>([^<]+)</span><span class="n">(\d+)', c)
        print(f'   {y}: {m.group(1):>3} seats | top {t.group(1)} {t.group(2)}')

if __name__ == '__main__':
    main()
