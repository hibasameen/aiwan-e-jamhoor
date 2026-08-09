#!/usr/bin/env python3
"""
Add 1977 / 1985 / 1988 hemicycle cards to index.html, matching the existing
static hemicycle SVGs (cx=110, cy=118, outer R=104, inner r=54, 180deg->0deg,
segments largest-first). Colours/categories come from map.html's PARTY_CAT/COLORS.
Inserted right after the 1990 card. A backup is written first.
"""
import json, re, math, time, collections

# --- read PARTY_CAT / COLORS from the (already patched) map.html ---
mt = open('map.html', encoding='utf-8').read()
def jsdict(name):
    s = mt[mt.index('const ' + name + '='):]
    s = s[s.index('{'): s.index('};') + 1]
    return dict(re.findall(r"'([^']*)':'([^']*)'", s))
PARTY_CAT, COLORS = jsdict('PARTY_CAT'), jsdict('COLORS')
cat = lambda p: PARTY_CAT.get(p, 'Other')
col = lambda c: COLORS.get(c, COLORS.get('Other', '#00a3c7'))

R = json.load(open('data/_map_inject/results_historic.json'))['RESULTS']

CX, CY, OR_, IR = 110.0, 118.0, 104.0, 54.0
def pt(r, deg):
    a = math.radians(deg)
    return f'{CX + r*math.cos(a):.1f} {CY - r*math.sin(a):.1f}'

def hemi_svg(tally, total):
    # tally: list of (cat, seats) largest-first
    segs, ang = [], 180.0
    for c, n in tally:
        span = 180.0 * n / total
        a0, a1 = ang, ang - span            # angle decreases left->right
        d = (f'M{pt(OR_,a0)} A{OR_:.0f} {OR_:.0f} 0 0 1 {pt(OR_,a1)} '
             f'L{pt(IR,a1)} A{IR:.0f} {IR:.0f} 0 0 0 {pt(IR,a0)} Z')
        segs.append(f'<path d="{d}" fill="{col(c)}" data-cat="{c}" '
                    f'stroke="var(--surface)" stroke-width="0.6"/>')
        ang = a1
    return ''.join(segs)

def card(year, seats_label, runner_text):
    res = R[year]
    t = collections.Counter(cat(r['wp']) for r in res.values())
    tally = sorted(t.items(), key=lambda kv: -kv[1])
    total = sum(t.values())
    top_c, top_n = tally[0]
    svg = hemi_svg(tally, total)
    return f'''      <a class="hemi" href="map.html?year={year}">
      <svg viewBox="0 0 220 126" role="img" aria-label="{year} seat share">
        {svg}
        <line x1="110" y1="8" x2="110" y2="66" stroke="var(--ink)" stroke-width="1.2"/>
      </svg>
      <div class="hemi-year"><span class="yr">{year}</span><span class="seats">{seats_label}</span></div>
      <div class="hemi-top"><span class="sw" data-cat="{top_c}" style="background:{col(top_c)}"></span><span>{top_c}</span><span class="n">{top_n}</span></div>
      <div class="hemi-runner">{runner_text}</div>
    </a>
'''

def runner(year):
    res = R[year]
    t = collections.Counter(cat(r['wp']) for r in res.values())
    tally = sorted(t.items(), key=lambda kv: -kv[1])
    if year == '1985':
        return 'non-party election'
    return f'then {tally[1][0]} {tally[1][1]}'

blocks = (card('1988', '207 seats', runner('1988'))
          + card('1985', '207 seats', runner('1985'))
          + card('1977', '200 seats', runner('1977')))

html = open('index.html', encoding='utf-8').read()
open(f'index.html.bak_{int(time.time())}', 'w', encoding='utf-8').write(html)

anchor = 'then PDA 42</div>\n      <div class="hemi-runner"></div>\n    </a>\n'
# The 1990 card ends with its runner text then </a>; find a robust anchor.
m = re.search(r'(<a class="hemi" href="map\.html\?year=1990">.*?</a>\n)', html, re.S)
assert m, '1990 card not found'
end = m.end()
new = html[:end] + blocks + html[end:]
assert new.count('year=1977"') == 1 and new.count('year=1985"') == 1 and new.count('year=1988"') == 1
open('index.html', 'w', encoding='utf-8').write(new)
print('inserted 1988/1985/1977 hemicycles after 1990')
print('tallies:',
      {y: sorted(collections.Counter(cat(r['wp']) for r in R[y].values()).items(), key=lambda kv:-kv[1])
       for y in ('1977','1985','1988')})
