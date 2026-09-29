#!/usr/bin/env python3
"""
Add NA-95 and NA-96 (Gujranwala city, 2002 delimitation) to the shipped pages by
editing them in place. map.html is not rebuilt, because a clean rebuild would
lose the 2018 and 2024 patches (see README).

Run scripts/boundaries/split_gujranwala_2002.py first. This script reads its
output, data/na_constituencies_2002delim.geojson.

map.html
  window.GEOS['2002']  replace NA-97 and NA-98, append NA-95 and NA-96. The
                       embedded layer is the data file verbatim (checked), so
                       the four features are copied as they are.
  window.GXW           the "This ground, 1977-2024" crosswalk. Every entry that
                       involves the 2002 layer is recomputed with the rule that
                       reproduces all 7,110 existing entries (the target seat
                       with the largest overlap, share = round(100 * overlap /
                       source area)), and entries for NA-95/96 are added. The
                       script checks that nothing outside Gujranwala changes.
islam.html
  __GEO['2002']        this page has its own, more simplified copy of the
                       layer, so NA-97/98 are cut again here with the same city
                       shapes, leaving no gaps in this copy either.
  caption              the note saying NA-95/96 have no boundaries in 2002-2013
                       now says they are approximate.

Other text that still calls the seats missing (method.html,
docs/METHODOLOGY.md, docs/DATA_DICTIONARY.md, src/map_template.html) is left to
the maintainer.

Each text anchor must match exactly once. A page whose 2002 layer already has
NA-95 is skipped, so the script is safe to re-run.
"""
import json, os, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'boundaries'))
import split_gujranwala_2002 as SG                      # carve(), load_pp(), GRID, km2
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.geometry.polygon import orient
from shapely import make_valid, STRtree
from shapely.ops import unary_union

SEATS = ('NA-95', 'NA-96', 'NA-97', 'NA-98')
ISLAM_NOTE_OLD = 'Two Punjab seats (NA-95, NA-96) lack digitised boundaries in 2002–2013.'
ISLAM_NOTE_NEW = ('In 2002–2013 the two Gujranwala city seats (NA-95, NA-96) are built from '
                  'the provincial-assembly map and are approximate.')
LAYER = json.load(open('data/na_constituencies_2002delim.geojson', encoding='utf-8'))
NEW = {f['properties']['na']: f for f in LAYER['features'] if f['properties']['na'] in SEATS}
assert len(NEW) == 4, 'run scripts/boundaries/split_gujranwala_2002.py first'


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
    # these blobs round-trip byte-for-byte, so re-dumping touches nothing else
    assert json.dumps(obj, separators=(',', ':'), ensure_ascii=False) == body, key
    return obj, b, e


def dump(o):
    return json.dumps(o, separators=(',', ':'), ensure_ascii=False)


def wind(g, clockwise):
    parts = list(g.geoms) if g.geom_type == 'MultiPolygon' else [g]
    parts = [orient(p, sign=-1.0 if clockwise else 1.0) for p in parts]
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


def replace_once(s, a, b):
    n = s.count(a)
    assert n == 1, f'anchor found {n}x, expected 1: {a[:80]!r}'
    return s.replace(a, b)


# ------------------------------------------------------------------ map.html
def patch_map():
    s = open('map.html', encoding='utf-8').read()
    GEOS, b, e = blob(s, 'window.GEOS=')
    feats = GEOS['2002']['features']
    names = [f['properties']['na'] for f in feats]
    if 'NA-95' in names:
        print('map.html: 2002 layer already has NA-95 - skipped')
        return
    assert len(feats) == 270
    # the embedded 2002 layer must be the pre-split data file, feature for feature
    idx = {n: i for i, n in enumerate(names)}
    old = {n: make_valid(shape(feats[idx[n]]['geometry'])) for n in ('NA-97', 'NA-98')}
    U_old = old['NA-97'].union(old['NA-98'])
    U_new = unary_union([shape(NEW[n]['geometry']) for n in SEATS])
    sd = SG.km2(U_old.symmetric_difference(U_new))
    assert sd < 1e-3, f'embedded NA-97/98 differ from the layer the split was cut from ({sd} km2)'
    for n in ('NA-97', 'NA-98'):
        feats[idx[n]] = NEW[n]
    feats += [NEW['NA-95'], NEW['NA-96']]
    print(f'map.html: GEOS[2002] 270 -> {len(feats)} features (union change {sd:.5f} km2)')

    # ---- GXW crosswalk
    GXW, gb, ge = blob(s, 'window.GXW=')
    layers = {}
    for L, fc in GEOS.items():
        d = {f['properties']['na']: make_valid(shape(f['geometry'])) for f in fc['features']}
        nm = list(d)
        layers[L] = (d, nm, STRtree([d[n] for n in nm]))

    def best(src, L):
        d, nm, tree = layers[L]
        hits = [(src.intersection(d[nm[i]]).area, nm[i]) for i in tree.query(src)]
        hits = [h for h in hits if h[0] > 0]
        if not hits: return None
        a, n = max(hits)
        return f'{n}|{round(100 * a / src.area)}'

    city_zone = U_new.buffer(0.02)
    changed, added = [], 0
    for L, entries in GXW.items():
        d = layers[L][0]
        if L == '2002':
            order = list(next(iter(entries.values())).keys())
            for n in SEATS:
                rec = {t: best(d[n], t) for t in order}
                assert all(rec.values()), (n, rec)
                if n not in entries: added += 1
                elif entries[n] != rec: changed.append(('2002', n, entries[n], rec))
                entries[n] = rec
            continue
        for n, rec in entries.items():
            if '2002' not in rec: continue
            v = best(d[n], '2002')
            if v != rec['2002']:
                assert d[n].intersects(city_zone), f'{L} {n}: 2002 match moved outside Gujranwala'
                changed.append((L, n, rec['2002'], v))
                rec['2002'] = v
    for c in changed: print('   GXW', c)
    print(f'map.html: GXW - {added} entries added, {len(changed)} updated, all inside Gujranwala')

    # splice GXW first (it sits after GEOS in the file), then GEOS
    assert gb > e
    s = s[:gb] + dump(GXW) + s[ge:]
    s = s[:b] + dump(GEOS) + s[e:]
    open('map.html', 'w', encoding='utf-8').write(s)
    print(f'map.html written, {len(s)/1e6:.2f} MB')


# ------------------------------------------------------------------ islam.html
def patch_islam():
    s = open('islam.html', encoding='utf-8').read()
    G, b, e = blob(s, 'var __GEO=')
    feats = G['2002']['features']
    names = [f['properties']['na'] for f in feats]
    if 'NA-95' in names:
        print('islam.html: 2002 layer already has NA-95 - skipped')
        return
    assert len(feats) == 270
    idx = {n: i for i, n in enumerate(names)}
    own = {n: shape(feats[idx[n]]['geometry']) for n in ('NA-97', 'NA-98')}
    cw = not own['NA-97'].exterior.is_ccw          # keep this copy's own winding (planar, evenodd)
    new, U, info = SG.carve(own['NA-97'], own['NA-98'],
                            shape(NEW['NA-95']['geometry']), shape(NEW['NA-96']['geometry']),
                            SG.load_pp())
    Unew = unary_union(list(new.values()))
    assert SG.km2(Unew.symmetric_difference(U)) < 1e-3
    for i, n in enumerate(SEATS):
        for m in SEATS[i + 1:]:
            assert SG.km2(new[n].intersection(new[m])) < 1e-3
    assert info['city_outside_old_NA97_98_km2'] < 0.05, info
    print('islam.html: carve', info)

    def feat(n):
        p = {k: NEW[n]['properties'][k] for k in ('na', 'prov', 'dist', 'teh')}
        return {'type': 'Feature', 'geometry': mapping(wind(new[n], cw)), 'properties': p}
    for n in ('NA-97', 'NA-98'):
        feats[idx[n]] = feat(n)
    feats += [feat('NA-95'), feat('NA-96')]
    s = s[:b] + dump(G) + s[e:]
    s = replace_once(s, ISLAM_NOTE_OLD, ISLAM_NOTE_NEW)
    open('islam.html', 'w', encoding='utf-8').write(s)
    print(f'islam.html written, 2002 layer {len(feats)} features, caption updated')


if __name__ == '__main__':
    patch_map()
    patch_islam()
