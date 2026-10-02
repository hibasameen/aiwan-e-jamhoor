#!/usr/bin/env python3
"""
Put the renumbered 207-seat layer into the shipped pages, editing them in place
as the other patches do (map.html is not rebuilt; see README).

Run scripts/boundaries/fix_207seat_identity.py first; this script reads its
output, data/boundaries/na_207seat_1985-1997_tessellated.geojson.

map.html
  window.GEOS['207seat']  replaced by the data file, with the prov property
                          patch_finalize_boundaries.py adds.
  window.GXW              the "This ground" crosswalk. Every entry from or to
                          the 207-seat layer is recomputed with the rule the
                          existing entries follow (target seat with the largest
                          overlap, share = round(100 * overlap / source area));
                          the rule is first checked against all of them on the
                          embedded layer. Only entries touching changed seats
                          may move.
islam.html
  __GEO['207']            the same geometry, with na, prov and approx only, as
                          patch_islam_207seat.py writes it.

Every blob must round-trip byte for byte before it is replaced. Re-running on
patched pages changes nothing.
"""
import json, os
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
os.chdir(ROOT)
from shapely.geometry import shape
from shapely import make_valid, STRtree
from shapely.ops import unary_union

LAYER = 'data/boundaries/na_207seat_1985-1997_tessellated.geojson'


def brace_span(s, b):
    """[b, e) of the JSON object starting at s[b] == '{' (string-aware)."""
    assert s[b] == '{'
    depth, j, instr, esc = 0, b, False, False
    while j < len(s):
        c = s[j]
        if instr:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': instr = False
        else:
            if c == '"': instr = True
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0: return b, j + 1
        j += 1
    raise ValueError('unbalanced')


def blob(s, key):
    i = s.index(key)
    assert s.count(key) == 1, key
    b, e = brace_span(s, i + len(key))
    body = s[b:e]
    obj = json.loads(body)
    assert json.dumps(obj, separators=(',', ':'), ensure_ascii=False) == body, key
    return obj, b, e


def dump(o):
    return json.dumps(o, separators=(',', ':'), ensure_ascii=False)


def prov(na):                                   # as patch_finalize_boundaries.load()
    n = int(na.split('-')[1])
    return ('Khyber Pakhtunkhwa' if n <= 26 else 'FATA' if n <= 34 else
            'Islamabad Capital Territory' if n == 35 else 'Punjab' if n <= 150 else
            'Sindh' if n <= 196 else 'Balochistan')


def new_layer():
    gj = json.load(open(LAYER, encoding='utf-8'))
    for f in gj['features']:
        f['properties']['prov'] = prov(f['properties']['na'])
    return gj


def patch_map(NEW):
    s = open('map.html', encoding='utf-8').read()
    GEOS, b, e = blob(s, 'window.GEOS=')
    old = {f['properties']['na']: f for f in GEOS['207seat']['features']}
    new = {f['properties']['na']: f for f in NEW['features']}
    assert len(old) == len(new) == 207 and set(old) == set(new)
    changed = sorted((na for na in new if new[na] != old[na]), key=lambda k: int(k[3:]))
    if not changed:
        print('map.html: 207seat already matches the data file - skipped')
        return
    print(f'map.html: {len(changed)} of 207 seats change: {" ".join(k[3:] for k in changed)}')

    GXW, gb, ge = blob(s, 'window.GXW=')

    def layers_of(G):
        out = {}
        for L, fc in G.items():
            d = {f['properties']['na']: make_valid(shape(f['geometry'])) for f in fc['features']}
            nm = list(d)
            out[L] = (d, nm, STRtree([d[n] for n in nm]))
        return out

    def best(layers, src, L):
        d, nm, tree = layers[L]
        hits = [(src.intersection(d[nm[i]]).area, nm[i]) for i in tree.query(src)]
        hits = [h for h in hits if h[0] > 0]
        if not hits: return None
        a, n = max(hits)
        return f'{n}|{round(100 * a / src.area)}'

    def entries_207(layers):
        """Every GXW value from or to the 207-seat layer, as {(layer, seat, target): value}."""
        out = {}
        d207 = layers['207seat'][0]
        for L, entries in GXW.items():
            for na, rec in entries.items():
                for t in rec:
                    if L == '207seat':
                        out[(L, na, t)] = best(layers, d207[na], t)
                    elif t == '207seat':
                        out[(L, na, t)] = best(layers, layers[L][0][na], '207seat')
        return out

    # the rule must reproduce every existing 207-seat entry on the embedded layer
    before = entries_207(layers_of(GEOS))
    bad = [(k, v, GXW[k[0]][k[1]][k[2]]) for k, v in before.items() if GXW[k[0]][k[1]][k[2]] != v]
    assert not bad, f'GXW rule does not reproduce {len(bad)} entries, e.g. {bad[:3]}'
    print(f'map.html: GXW rule reproduces all {len(before)} existing 207-seat entries')

    GEOS['207seat'] = NEW
    after = entries_207(layers_of(GEOS))
    zone = unary_union([make_valid(shape(old[na]['geometry'])) for na in changed] +
                       [make_valid(shape(new[na]['geometry'])) for na in changed])
    moved = []
    for (L, na, t), v in after.items():
        if GXW[L][na][t] != v:
            src = shape(new[na]['geometry']) if L == '207seat' else shape(
                next(f for f in GEOS[L]['features'] if f['properties']['na'] == na)['geometry'])
            assert (L == '207seat' and na in changed) or make_valid(src).intersects(zone), \
                f'{L} {na} -> {t} moved but does not touch a changed seat'
            moved.append((L, na, t, GXW[L][na][t], v))
            GXW[L][na][t] = v
    for m in moved:
        print('   GXW', m)
    print(f'map.html: GXW - {len(moved)} entries updated, all on or next to changed seats')

    assert gb > e                     # GXW sits after GEOS: splice it first
    s = s[:gb] + dump(GXW) + s[ge:]
    s = s[:b] + dump(GEOS) + s[e:]
    open('map.html', 'w', encoding='utf-8').write(s)
    print(f'map.html written, {len(s) / 1e6:.2f} MB')


def patch_islam(NEW):
    s = open('islam.html', encoding='utf-8').read()
    G, b, e = blob(s, 'var __GEO=')
    feats = [{'type': 'Feature', 'properties': {'na': f['properties']['na'], 'prov': f['properties']['prov'],
                                                'approx': f['properties'].get('approx', False)},
              'geometry': f['geometry']} for f in NEW['features']]
    old = {f['properties']['na']: f for f in G['207']['features']}
    # islam.html carries map.html's layer verbatim; check that on the unchanged seats
    same = [f for f in feats if f == old.get(f['properties']['na'])]
    if len(same) == len(feats):
        print('islam.html: __GEO[207] already matches - skipped')
        return
    G['207'] = {**G['207'], 'features': feats}
    s = s[:b] + dump(G) + s[e:]
    open('islam.html', 'w', encoding='utf-8').write(s)
    print(f'islam.html: __GEO[207] - {len(feats) - len(same)} seats changed; written, {len(s) / 1e6:.2f} MB')


if __name__ == '__main__':
    NEW = new_layer()
    patch_map(json.loads(json.dumps(NEW)))
    patch_islam(NEW)
