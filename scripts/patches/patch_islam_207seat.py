#!/usr/bin/env python3
"""
Islam & the Ballot: draw 1988–1997 on the 207-seat constituency layer
(GEOS['207seat'] in map.html, map-traced/tessellated) instead of 1990s districts.

Per-seat religio-political shares are computed from map.html's window.RESULTS
(the site's canonical per-seat results), with the same party->bloc labels the
page already uses (PSECT keys). Replaces __MAPS[1988..1997] (mode 'na'), adds
__GEO['207'], repoints CFG, and updates the caption. Idempotent.
"""
import json, os, re, collections
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
os.chdir(ROOT)
isl = open('islam.html', encoding='utf-8').read()
if "'1988':{g:'207'}" in isl:
    print('already patched'); raise SystemExit
mp = open('map.html', encoding='utf-8').read()

def blob(src, key):
    m = re.search(r'(?:window\.|const |var )' + key + r'\s*=\s*', src); i = m.end(); j = src.index('\n', i)
    return json.loads(src[i:j].rstrip(';')), i, j
RES, _, _ = blob(mp, 'RESULTS')
GEOS, _, _ = blob(mp, 'GEOS')
geo207 = GEOS['207seat']
for f in geo207['features']:
    f['properties'] = {'na': f['properties']['na'], 'prov': f['properties'].get('prov'), 'approx': f['properties'].get('approx', False)}

# party label (as in RESULTS) -> bloc label used on the page (PSECT key)
LAB = {
    '1988': {'JUI-F': 'JUI-F', 'JUI-D': 'JUI (other factions)', 'JUI': 'JUI (other factions)',
             'TNFJ': 'TNFJ / Islami Tehreek', 'PAT': 'PAT (Minhaj)', 'JAHP': 'Ahl-e-Hadith parties'},
    '1990': {'JUI-F': 'JUI-F', 'JUP-N': 'JUP', 'JUP-Niazi': 'JUP', 'PAT': 'PAT (Minhaj)', 'JUI': 'JUI (other factions)'},
    '1993': {'Pakistan Islamic Front': 'Jamaat-e-Islami', 'Islami Jamhoori Mahaz': 'IJM (JUI-F-led, 1993)',
             'Jamiat Ulama-e-Islam (Sami)': 'MDM (1993)', 'Jamiat-e-Mashaikh Pakistan': 'Other Barelvi'},
    '1997': {'Jamiat Ulema-e Islam (Fazl)': 'JUI-F', 'Jamiat Ulama-e-Islam (Sami)': 'JUI-S', 'Jamaat-e-Islami': 'Jamaat-e-Islami',
             'Jamiat-e-Mashaikh Pakistan': 'Other Barelvi'},
}
PSECT = json.loads(re.search(r'var PSECT=(\{.*?\});', isl).group(1))
def prov(p):
    p = (p or '').lower()
    return 'Punjab' if 'punjab' in p else 'Sindh' if 'sindh' in p else 'Khyber Pakhtunkhwa' if ('khyber' in p or 'nwfp' in p) else 'Balochistan' if 'baloch' in p else 'Islamabad / FATA' if p else ''

M, i, j = blob(isl, '__MAPS')
for y, lab in LAB.items():
    data = {}
    for na, d in RES[y].items():
        tot = sum((c.get('v') or 0) for c in d['cands'])
        ps, sects = collections.Counter(), collections.Counter()
        for c in d['cands']:
            k = lab.get(c['p'])
            if not k: continue
            sh = round(100.0 * (c.get('v') or 0) / tot, 1) if tot else 0.0
            if sh <= 0: continue
            ps[k] += sh; sects[PSECT[k]] += sh
        pct = round(sum(ps.values()), 1)
        top = max(sects, key=sects.get) if sects else None
        won = 1 if lab.get(d.get('wp')) else 0
        data[na] = {'pct': pct, 'top': top, 'sects': {k: round(v, 1) for k, v in sects.items()},
                    'ps': {k: round(v, 1) for k, v in ps.items()}, 'name': d.get('name', ''), 'won': won, 'prov': prov(d.get('prov'))}
    M[y] = {'mode': 'na', 'data': data}
    print(y, len(data), 'seats;', sum(1 for v in data.values() if v['won']), 'won;', 'max', max(v['pct'] for v in data.values()))
isl = isl[:i] + json.dumps(M, ensure_ascii=False, separators=(',', ':')) + ';' + isl[j:]

G, i, j = blob(isl, '__GEO')
G['207'] = geo207
isl = isl[:i] + json.dumps(G, ensure_ascii=False, separators=(',', ':')) + ';' + isl[j:]

old = "var CFG={'1988':{g:'1990s',gy:'1990'},'1990':{g:'1990s',gy:'1990'},'1993':{g:'1990s',gy:'1993'},'1997':{g:'1990s',gy:'1997'},"
assert isl.count(old) == 1
isl = isl.replace(old, "var CFG={'1988':{g:'207'},'1990':{g:'207'},'1993':{g:'207'},'1997':{g:'207'},")
old2 = "1988–1997 are shown by district (the 1977-delimitation constituency boundaries are not fully digitised); district figures aggregate the NA seats covering that district."
assert isl.count(old2) == 1
isl = isl.replace(old2, "1988–1997 are drawn on the 207-seat delimitation of 1985–1997, traced from labelled result maps and tessellated to fill the country — reliable to the district, approximate inside it (see Method §04). Seats the source omits (1993, 1997 by-elections) are blank.")
open('islam.html', 'w', encoding='utf-8').write(isl)
print('islam.html patched;', len(isl) / 1e6, 'MB')
