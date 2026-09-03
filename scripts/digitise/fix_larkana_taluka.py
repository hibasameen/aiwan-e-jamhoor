#!/usr/bin/env python3
"""Upgrade NA-200/201 (Larkana) from district-wide centroid Voronoi to a
taluka-composition split. No ECP sheet exists for Larkana (dis16 missing), but
the 2018 composition is taluka-aligned (per the successor constituencies
NA-194/195 on Wikipedia): NA-200 = Ratodero taluka + part of Larkana taluka,
NA-201 = Dokri + Bakrani talukas + rest of Larkana taluka (incl. part of the
city). Talukas from geoBoundaries gbOpen ADM3, partitioned per-cell over the
Larkana district carve; the intra-Larkana-taluka line is a plotree-centroid
Voronoi (that part stays approx)."""
import json, csv, sys
BASE = '/root/aiwan'
sys.path.insert(0, f'{BASE}/scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping, Point, GeometryCollection, Polygon
from shapely.ops import unary_union, voronoi_diagram
from shapely import make_valid, contains_xy
from scipy.spatial import cKDTree
from run_sindh import build_districts


def partition(parent, targets, gn=520):
    minx, miny, maxx, maxy = parent.bounds
    gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
    XX, YY = np.meshgrid(gx, gy)
    fx, fy = XX.ravel(), YY.ravel()
    inp = contains_xy(parent, fx, fy)
    assign = np.full(fx.shape, -1, int); dist = np.full(fx.shape, np.inf)
    keys = list(targets)
    for i, k in enumerate(keys):
        g = targets[k]
        ins = contains_xy(g, fx, fy) & inp & (dist > 0)
        assign[ins] = i; dist[ins] = 0.0
        b = g.boundary
        segs = [b] if b.geom_type == 'LineString' else list(b.geoms)
        B = np.array([(x, y) for sg in segs for x, y in zip(*sg.xy)])
        dd, _ = cKDTree(B).query(np.stack([fx, fy], 1))
        upd = inp & (dist > 0) & (dd < dist)
        assign[upd] = i; dist[upd] = dd[upd]
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    out = {}
    for i, k in enumerate(keys):
        cm = (assign.reshape(gn, gn) == i).astype('uint8')
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = [make_valid(Polygon(zip(minx + c.reshape(-1, 2)[:, 0] * dx,
                                        miny + c.reshape(-1, 2)[:, 1] * dy)).buffer(max(dx, dy) * 0.6))
                 for c in cs if len(c) >= 4 and cv2.contourArea(c) >= 4]
        out[k] = make_valid(unary_union(polys).intersection(parent)) if polys else None
    return out


def main():
    D = build_districts()
    lark = D['Larkana']
    adm3 = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
            for f in json.load(open(f'{BASE}/data/gb_PAK_ADM3.geojson'))['features']}
    tal = {k: adm3[k] for k in ('LARKANA', 'RATODERO', 'BAKRANI TALUKS', 'DOKRI')}
    parts = partition(lark, tal)
    cents = {r['seat']: (float(r['X']), float(r['Y']))
             for r in csv.DictReader(open(f'{BASE}/plotree_elections/essentials/NA_2018_centroids.csv'))}
    # split the Larkana-taluka piece between the two seats by centroid Voronoi
    lt = parts['LARKANA']
    pts = [Point(*cents[s]) for s in ('NA-200', 'NA-201')]
    vor = voronoi_diagram(GeometryCollection(pts), envelope=lt.buffer(1.0))
    cells = list(vor.geoms)
    halves = {}
    for s, pt in zip(('NA-200', 'NA-201'), pts):
        cell = next((c for c in cells if c.contains(pt)), None) or min(cells, key=lambda c: c.distance(pt))
        halves[s] = make_valid(cell.intersection(lt))
    na200 = make_valid(unary_union([parts['RATODERO'], halves['NA-200']]))
    na201 = make_valid(unary_union([parts['DOKRI'], parts['BAKRANI TALUKS'], halves['NA-201']]))
    # exact coverage of the carve
    na201 = make_valid(unary_union([na201, lark.difference(unary_union([na200, na201]))]))
    na201 = make_valid(na201.difference(na200))
    src = ('taluka-composition (gb ADM3): NA-200=Ratodero+N Larkana taluka, '
           'NA-201=Dokri+Bakrani+S Larkana taluka; intra-taluka line plotree-Voronoi [approx]')
    v2 = json.load(open(f'{BASE}/data/na_2018delim_v2.geojson'))
    for f in v2['features']:
        na = f['properties']['na']
        if na in ('NA-200', 'NA-201'):
            g = na200 if na == 'NA-200' else na201
            f['properties'] = {'na': na, 'dist': f['properties'].get('dist', ''),
                               'approx': True, 'src': src}
            f['geometry'] = mapping(make_valid(g).simplify(0.0015))
    json.dump(v2, open(f'{BASE}/data/na_2018delim_v2.geojson', 'w'))
    a, b = na200.area / lark.area, na201.area / lark.area
    print(f'NA-200 share {a:.2f}, NA-201 share {b:.2f}')


if __name__ == '__main__':
    main()
