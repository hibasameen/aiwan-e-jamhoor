#!/usr/bin/env python3
"""
Assemble the self-contained map app (aiwan_e_jamhoor_map.html).

Pipeline (run from the project root):
  1. python3 scripts/build_results_json.py            -> results_all.json
  2. python3 scripts/build_reconstructed_geometry.py  -> na_2018delim_raw.geojson,
                                                         na_2024delim_raw.geojson
  3. mapshaper <raw> -simplify 15% keep-shapes -clean -o precision=0.0001 <simplified>
     (12% for the 2002-delimitation file, which is denser)
  4. python3 scripts/build_map.py                     -> aiwan_e_jamhoor_map.html

This script re-winds every polygon's exterior ring clockwise (d3-geo treats
RFC-7946 CCW rings as sphere-inverted -> the map renders as a filled rectangle
otherwise), repairs invalid geometries (make_valid; bowties are common in the
digitised 2002 shapefile), then inlines D3 + all data into map_template.html.
D3 is inlined (not CDN-linked) so the file works offline / behind firewalls.
"""
import json
from shapely.geometry import shape, mapping, MultiPolygon
from shapely import make_valid
from shapely.geometry.polygon import orient

def rewind(inp, outp, expect=None):
    gj = json.load(open(inp))
    for f in gj['features']:
        g = make_valid(shape(f['geometry']))
        if g.geom_type == 'Polygon':
            g = orient(g, sign=-1.0)
        elif g.geom_type == 'MultiPolygon':
            g = MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
        else:  # GeometryCollection from make_valid — keep polygonal parts
            polys = []
            for x in g.geoms:
                if x.geom_type == 'Polygon': polys.append(orient(x, sign=-1.0))
                elif x.geom_type == 'MultiPolygon': polys += [orient(p, sign=-1.0) for p in x.geoms]
            g = MultiPolygon(polys)
        f['geometry'] = mapping(g)
    json.dump(gj, open(outp, 'w'), separators=(',', ':'))
    n = len(gj['features'])
    assert expect is None or n == expect, f'{outp}: {n} features, expected {expect}'
    print(outp, n)

if __name__ == '__main__':
    rewind('na_2002delim_simplified.geojson', 'na_2002delim_d3.geojson', 270)
    rewind('data/na_2018delim_simplified.geojson', 'na_2018delim_d3.geojson', 272)
    rewind('na_2024delim_simplified.geojson', 'na_2024delim_d3.geojson', 266)

    tpl = open('map_template.html').read()
    d3src = open('node_modules/d3/dist/d3.min.js').read()
    tpl = tpl.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>',
                      '<script>' + d3src + '</script>')
    out = (tpl.replace('/*__RESULTS__*/', open('results_all.json').read())
              .replace('/*__GEO2002__*/', open('na_2002delim_d3.geojson').read())
              .replace('/*__GEO2018__*/', open('na_2018delim_d3.geojson').read())
              .replace('/*__GEO2024__*/', open('na_2024delim_d3.geojson').read()))
    open('aiwan_e_jamhoor_map.html', 'w').write(out)
    print('aiwan_e_jamhoor_map.html', round(len(out) / 1e6, 2), 'MB')
