#!/usr/bin/env python3
"""
Regenerate the home-page hemicycle strip from the map's own results, so every
election on the map appears there too.

The arcs match the existing markup exactly: a half-annulus centred at (110,118)
with outer radius 104 and inner 54, swept from pi to 2pi, segments ordered by
seats won and separated by a small angular gap.
"""
import json, io, math, re

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
    for y in YL:
        res = R[y]
        t = {}
        for r in res.values(): t[cat(r['wp'])] = t.get(cat(r['wp']), 0) + 1
        rows = sorted(t.items(), key=lambda kv: (-kv[1], ORDER.index(kv[0]) if kv[0] in ORDER else 99))
        n = sum(v for _, v in rows)
        totals = [(c, v, COL.get(c, COL['Other'])) for c, v in rows]
        top, second = rows[0], (rows[1] if len(rows) > 1 else None)
        cards.append(
            f'      <a class="hemi" href="map.html?year={y}">\n'
            f'      <svg viewBox="0 0 220 126" role="img" aria-label="{y} seat share">\n'
            f'        {arcs(totals, n)}\n'
            f'        <line x1="110" y1="8" x2="110" y2="66" stroke="var(--ink)" stroke-width="1.2"/>\n'
            f'      </svg>\n'
            f'      <div class="hemi-year"><span class="yr">{y}</span>'
            f'<span class="seats">{n} seats</span></div>\n'
            f'      <div class="hemi-top"><span class="sw" data-cat="{top[0]}" '
            f'style="background:{COL.get(top[0], COL["Other"])}"></span>'
            f'<span>{top[0]}</span><span class="n">{top[1]}</span></div>\n'
            + (f'      <div class="hemi-runner">then {second[0]} {second[1]}</div>\n' if second else '')
            + '    </a>')

    idx = io.open(IDX, encoding='utf-8').read()
    a = idx.index('<div class="hemis">')
    b = idx.index('<div class="strip-note">')
    head = idx[:a]
    tail = idx[b:]
    block = '<div class="hemis">\n' + '\n'.join(cards) + '\n    </div>\n\n    '
    idx = head + block + tail
    io.open(OUT, 'w', encoding='utf-8').write(idx)
    print(f'rebuilt {len(cards)} hemicycles: {", ".join(YL)}')
    for y, c in zip(YL, cards):
        m = re.search(r'<span class="seats">(\d+) seats', c)
        t = re.search(r'<span>([^<]+)</span><span class="n">(\d+)', c)
        print(f'   {y}: {m.group(1):>3} seats | top {t.group(1)} {t.group(2)}')

if __name__ == '__main__':
    main()
