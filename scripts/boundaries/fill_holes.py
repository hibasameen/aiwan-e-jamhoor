#!/usr/bin/env python3
"""Close internal gaps in na_2018delim_v2.geojson so all boundaries tile
contiguously. Main source: NA-51's six FR strips were built from the 2015
district layer while the KP districts they were carved from are gbOpen-shaped,
leaving misalignment voids (plus assorted small carve slivers elsewhere).

Rule per hole in the national union: if NA-51 borders it, the hole is FR
misalignment and joins NA-51; otherwise it joins the neighbouring seat with the
longest shared boundary. Iterates until no hole > 0.05 km^2 remains."""
import json, sys
BASE = '/root/aiwan'
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union
from shapely import make_valid

def main():
    v2 = json.load(open(f'{BASE}/data/na_2018delim_v2.geojson'))
    geoms = {f['properties']['na']: make_valid(shape(f['geometry'])) for f in v2['features']}
    for it in range(4):
        tot = make_valid(unary_union(list(geoms.values())))
        polys = [tot] if tot.geom_type == 'Polygon' else [p for p in tot.geoms if p.geom_type == 'Polygon']
        holes = []
        for p in polys:
            for ring in p.interiors:
                h = make_valid(Polygon(ring))
                if h.area > 5e-6:
                    holes.append(h)
        if not holes:
            break
        print(f'iter {it}: {len(holes)} holes')
        for h in holes:
            hb = h.buffer(0.003)
            cands = [na for na, g in geoms.items() if g.intersects(hb)]
            if not cands:
                continue
            if 'NA-51' in cands:
                owner = 'NA-51'
            else:
                owner = max(cands, key=lambda na: geoms[na].buffer(0.002).intersection(hb).area)
            geoms[owner] = make_valid(unary_union([geoms[owner], h]))
            print(f'  hole ~{h.area*111*104:.1f} km2 at ({h.centroid.x:.2f},{h.centroid.y:.2f}) -> {owner}')
    for f in v2['features']:
        na = f['properties']['na']
        f['geometry'] = mapping(geoms[na])
    json.dump(v2, open(f'{BASE}/data/na_2018delim_v2.geojson', 'w'))
    tot = make_valid(unary_union(list(geoms.values())))
    polys = [tot] if tot.geom_type == 'Polygon' else [p for p in tot.geoms if p.geom_type == 'Polygon']
    rem = sum(1 for p in polys for r in p.interiors if Polygon(r).area > 5e-6)
    print('remaining holes >~0.05km2:', rem)

if __name__ == '__main__':
    main()
