#!/usr/bin/env python3
"""
Give every seat of the 207-seat layer the region its NA number is printed in.

Runs between merge_traced_v2.py and tessellate_207.py:

    merge_traced_v2.py -> fix_207seat_identity.py -> tessellate_207.py

audit_207_identity.py found 20 merged seats drawn from a region that the
Commons maps print with another number (or with none), and 8 seats left as
Voronoi fallbacks although their numbers are printed on the maps. This script

  1. sets the crosswalk entry for NA-120 from build_map_numbering.NAME88_FIX
     (the base entry came from a 1988 page title that repeats NA-94's), so the
     re-tiling keeps NA-120 in Multan-cum-Khanewal rather than Lahore;
  2. keeps every merged seat whose source region carries its own number;
  3. for the others, traces the region printed with the seat's number on the
     1993 map (the largest, where a number is printed twice), through the same
     transform the shipped traces used, cleaned and rounded as merge_traced_v2
     does, and gated as it is (within 40 km of the seat's districts);
  4. writes the merged set back and re-runs tessellate_207.py unchanged.

Seats it replaces get src commons-1993 (-inset for city boxes), approx false
and no confidence flag, since the number is read from the map exactly. Seats it
keeps are not touched. Re-running it on its own output changes nothing.

    python3 scripts/boundaries/fix_207seat_identity.py
"""
import os, sys, json
_here = os.path.dirname(os.path.abspath(__file__))
for _g in ('digitise', 'boundaries'):
    sys.path.insert(0, os.path.join(_here, '..', _g))
from shapely.geometry import mapping, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import audit_207_identity as A
import build_map_numbering as BM
import tessellate_207

MERGED = 'data/boundaries/na_207seat_1985-1997_traced.geojson'
XWALK = 'data/wip/trace/xwalk_207map.json'
KM, GATE = 105.0, 40.0


def rnd(o, nd=4):                                   # as merge_traced_v2.py
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list): return [rnd(x, nd) for x in o]
    if isinstance(o, dict): return {k: rnd(v, nd) for k, v in o.items()}
    return o


def clean(g):                                       # as merge_traced_v2.py
    g = g.buffer(0)
    if g.is_empty: return None
    if g.geom_type == 'Polygon': return orient(g, -1.0)
    if g.geom_type == 'MultiPolygon':
        return MultiPolygon([orient(p, -1.0) for p in g.geoms])
    return None


def fix_crosswalk():
    xw = json.load(open(XWALK))
    changed = []
    for na, name in BM.NAME88_FIX.items():
        ds = BM.attach({na: BM.expand(BM.resolve(name))})[na]
        assert all(xw[y][na] == ds for y in ('1990', '1993', '1997')), (na, ds)
        if xw['base'][na] != ds:
            changed.append((na, xw['base'][na], ds))
            xw['base'][na] = ds
    if changed:
        json.dump(xw, open(XWALK, 'w'))
    return xw['base'], changed


def main():
    base_xw, xw_changed = fix_crosswalk()
    for na, old, new in xw_changed:
        print(f'crosswalk {na}: {old} -> {new}')
    DIST = A.brg.load_districts()

    maps, off = A.load_maps()
    base = maps[A.BASE_YEAR]
    printed = {}
    for r in base['regions']:
        for na in set(r['exact']):
            if na not in printed or r['area'] > printed[na]['area']:
                printed[na] = r

    merged = json.load(open(MERGED))
    out, log = [], []
    for f in merged['features']:
        na, p = f['properties']['na'], f['properties']
        r = A.source_region(maps, off, f)
        if r is not None and sorted(set(r['exact'])) == [na]:
            out.append(f)
            continue
        if r is None:
            was = 'Voronoi fallback' if p['src'] == 'reconstructed' else f"{p['src']}, source region not found"
        else:
            was = (f"{p['src']}{', low confidence' if p.get('confidence') == 'low' else ''}, "
                   f"region printed {' '.join(sorted(set(r['exact']))) or '(none)'}")
        t = printed.get(na)
        g = clean(A.trace_region(base, t)) if t is not None else None
        if g is None:
            out.append(f)
            log.append((na, was, 'kept: no traceable printed region'))
            continue
        dist = unary_union([DIST[d] for d in base_xw[na] if d in DIST])
        d = dist.distance(g) * KM
        if d > GATE:
            out.append(f)
            log.append((na, was, f'kept: printed region {d:.0f} km from its districts'))
            continue
        src = f'commons-{A.BASE_YEAR}' + ('' if t['main'] else '-inset')
        out.append({'type': 'Feature', 'properties': {'na': na, 'src': src, 'approx': False},
                    'geometry': rnd(mapping(g))})
        log.append((na, was, f'now {src}, region printed {na}'))

    for na, was, now in log:
        print(f'{na:7} {was:58} -> {now}')
    merged['features'] = out
    json.dump(merged, open(MERGED, 'w'))
    print(f'wrote {MERGED}: {len(log)} seats changed')
    tessellate_207.main()


if __name__ == '__main__':
    main()
