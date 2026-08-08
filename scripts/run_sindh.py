#!/usr/bin/env python3
"""Leg 4 driver: Sindh 2018. Sheets are COLOUR-FILLED (KP style) with NA callout
chips. Pipeline per multi-seat district: hue-word seat masks (one weak seat may be
taken as remainder) -> outline ICP+TPS fit to gbOpen district -> label-transfer
grid split -> plotree-centroid Hungarian QA. Single-seat districts are exact
gbOpen unions. Districts missing from gbOpen (Larkana, Sujawal, Karachi's six)
are carved from their gbOpen parent using the COD/gbHumanitarian 2022 layer, so
outer edges stay consistent with the other provinces. Larkana has no sheet
(dis16 absent) -> centroid-Voronoi fallback [approx].

Refactored per memory gotcha: all driver code under main(); importable safely.
"""
import json, csv, sys, os
BASE = '/root/aiwan'
sys.path.insert(0, f'{BASE}/scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping, Point, GeometryCollection
from shapely.ops import unary_union, voronoi_diagram
from shapely import make_valid
from scipy.optimize import linear_sum_assignment
from split_district_by_sheet import split_district, fit_outline  # noqa

SD = f'{BASE}/sheets'

# sheet, district-key, [(na, colour-word)] ; colour None/unknown -> remainder seat
JOBS = [
 ('dis22.jpg', 'Shikarpur',           [('NA-198','light blue'), ('NA-199','white')]),
 ('dis7.jpg',  'Kamber Shahdadkot',   [('NA-202','pale yellow'), ('NA-203','light blue')]),
 ('dis3.jpg',  'Ghotki',              [('NA-204','pale yellow'), ('NA-205','lavender')]),
 ('dis24.jpg', 'Sukkur',              [('NA-206','white'), ('NA-207','light blue')]),
 ('dis14.jpg', 'Khairpur',            [('NA-208','blue'), ('NA-209','tan'), ('NA-210','green')]),
 ('dis19.jpg', 'Naushahro Feroze',    [('NA-211','yellow'), ('NA-212','lavender')]),
 ('dis21.jpg', 'Shaheed Benazirabad', [('NA-213','yellow'), ('NA-214','pink')]),
 ('dis20.jpg', 'Sanghar',             [('NA-215','yellow'), ('NA-216','light green'), ('NA-217','blue')]),
 ('dis18.jpg', 'Mirpurkhas',          [('NA-218','green'), ('NA-219','white')]),
 ('dis27.jpg', 'Tharparkar',          [('NA-221','light blue'), ('NA-222','white')]),
 ('dis4.jpg',  'Hyderabad',           [('NA-225','light blue'), ('NA-226','green'), ('NA-227','pale yellow')]),
 ('dis1.jpg',  'Badin',               [('NA-229','salmon-pink'), ('NA-230','green')]),
 ('dis2.jpg',  'Dadu',                [('NA-234','yellow'), ('NA-235','white')]),
 # Karachi (district polygons COD-carved from the gbOpen Karachi blob)
 ('dis10.jpg', 'Malir Karachi',       [('NA-236','light blue'), ('NA-237','light green'), ('NA-238','pink')]),
 ('dis15.jpg', 'Korangi Karachi',     [('NA-239','yellow'), ('NA-240','light green'), ('NA-241','blue')]),
 ('dis9.jpg',  'East Karachi',        [('NA-242','white'), ('NA-243','green'), ('NA-244','magenta'), ('NA-245','yellow')]),
 ('dis11.jpg', 'South Karachi',       [('NA-246','pink'), ('NA-247','light blue')]),
 ('dis12.jpg', 'West Karachi',        [('NA-248','purple'), ('NA-249','teal'), ('NA-250','white'), ('NA-251','yellow'), ('NA-252','tan')]),
 ('dis8.jpg',  'Central Karachi',     [('NA-253','light blue'), ('NA-254','salmon-pink'), ('NA-255','green'), ('NA-256','yellow')]),
]

SINGLE = [  # na, gbOpen name or carved key
 ('NA-196', 'Jacobabad'), ('NA-197', 'Kashmore'), ('NA-220', 'Umerkot'),
 ('NA-223', 'Matiari'), ('NA-224', 'Tando Allahyar'), ('NA-228', 'Tando Muhammad Khan'),
 ('NA-231', 'Sujawal'), ('NA-232', 'Thatta'), ('NA-233', 'Jamshoro'),
]


def build_districts():
    gb = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
          for f in json.load(open(f'{BASE}/data/gb_PAK_ADM2.geojson'))['features']}
    cod = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
           for f in json.load(open(f'{BASE}/data/cod_PAK_ADM2.geojson'))['features']}
    D = {}
    for n in ('Jacobabad', 'Kashmore', 'Umerkot', 'Matiari', 'Tando Allahyar',
              'Tando Muhammad Khan', 'Jamshoro', 'Shikarpur', 'Ghotki', 'Sukkur',
              'Khairpur', 'Sanghar', 'Mirpurkhas', 'Tharparkar', 'Hyderabad',
              'Badin', 'Dadu'):
        D[n] = gb[n]
    D['Naushahro Feroze'] = gb['Naushehro Feroze']
    D['Shaheed Benazirabad'] = gb['Nawabshah']
    # carve Sujawal from Thatta, Larkana from Qambar Shahdadkot — per-cell
    # nearest partition (plain intersect/difference leaves seam slivers)
    def carve2(parent, cod_a, cod_b, gn=600):
        import numpy as np
        from shapely.geometry import Polygon
        from shapely import contains_xy
        import cv2
        from scipy.spatial import cKDTree
        minx, miny, maxx, maxy = parent.bounds
        gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
        XX, YY = np.meshgrid(gx, gy)
        fx, fy = XX.ravel(), YY.ravel()
        inp = contains_xy(parent, fx, fy)
        assign = np.full(fx.shape, -1, int); dist = np.full(fx.shape, np.inf)
        for i, g in enumerate((cod_a, cod_b)):
            ins = contains_xy(g, fx, fy) & inp & (dist > 0)
            assign[ins] = i; dist[ins] = 0.0
            b = g.boundary
            segs = [b] if b.geom_type == 'LineString' else list(b.geoms)
            B = np.array([(x, y) for sg in segs for x, y in zip(*sg.xy)])
            dd, _ = cKDTree(B).query(np.stack([fx, fy], 1))
            upd = inp & (dist > 0) & (dd < dist)
            assign[upd] = i; dist[upd] = dd[upd]
        dx, dy = gx[1] - gx[0], gy[1] - gy[0]
        halves = []
        for i in range(2):
            cm = (assign.reshape(gn, gn) == i).astype('uint8')
            cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
            polys = [make_valid(Polygon(zip(minx + c.reshape(-1, 2)[:, 0] * dx,
                                            miny + c.reshape(-1, 2)[:, 1] * dy)).buffer(max(dx, dy) * 0.6))
                     for c in cs if len(c) >= 4 and cv2.contourArea(c) >= 4]
            halves.append(make_valid(unary_union(polys).intersection(parent)) if polys else None)
        a, b2 = halves
        # exact complementary coverage without seam speckles: side B = largest
        # component of parent minus A; side A absorbs the boundary ring/fragments
        diff = make_valid(parent.difference(a))
        comps = list(diff.geoms) if diff.geom_type in ('MultiPolygon', 'GeometryCollection') else [diff]
        comps = [c for c in comps if c.geom_type == 'Polygon']
        b2 = max(comps, key=lambda c: c.area)
        a = make_valid(parent.difference(b2))
        return a, b2

    suj, tha = carve2(gb['Thatta'], cod['Sujawal'], cod['Thatta'])
    D['Sujawal'], D['Thatta'] = suj, tha
    lar, kam = carve2(gb['Qambar Shahdadkot'], cod['Larkana'], cod['Kambar Shahdad Kot'])
    D['Larkana'], D['Kamber Shahdadkot'] = lar, kam
    # partition the gbOpen Karachi blob among the six COD Karachi districts by
    # PER-CELL nearest distance (whole-component nearest assignment dumps the
    # big Kirthar remainder onto one district and warps its shape)
    import numpy as np
    from shapely.geometry import Polygon
    from shapely import contains_xy
    import cv2
    blob = gb['Karachi']
    # 2018-era targets: COD-2022 folds Keamari (2020, ex-West) into SOUTH, so
    # for West and South use GADM 3.6 (pre-Keamari, 2018 configuration)
    def _shape_safe(g):
        if g['type'] == 'MultiPolygon':
            g = dict(g, coordinates=[[r for r in poly if len(r) >= 4]
                                     for poly in g['coordinates']])
            g['coordinates'] = [p for p in g['coordinates'] if p and len(p[0]) >= 4]
        elif g['type'] == 'Polygon':
            g = dict(g, coordinates=[r for r in g['coordinates'] if len(r) >= 4])
        return make_valid(shape(g))
    gadm = {f['properties']['NAME_3']: _shape_safe(f['geometry'])
            for f in json.load(open(f'{BASE}/data/gadm36_PAK_adm3.json'))['features']
            if f['properties'].get('NAME_1') in ('Sind', 'Sindh')}
    targets = {'Central Karachi': cod['Central Karachi'], 'East Karachi': cod['East Karachi'],
               'Korangi Karachi': cod['Korangi Karachi'], 'Malir Karachi': cod['Malir Karachi'],
               'South Karachi': gadm['Karachi South'], 'West Karachi': gadm['Karachi west']}
    kk = ['Central Karachi', 'East Karachi', 'Korangi Karachi',
          'Malir Karachi', 'South Karachi', 'West Karachi']
    minx, miny, maxx, maxy = blob.bounds
    gn = 700
    gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
    XX, YY = np.meshgrid(gx, gy)
    fx, fy = XX.ravel(), YY.ravel()
    inblob = contains_xy(blob, fx, fy)
    assign = np.full(fx.shape, -1, dtype=int)
    dist = np.full(fx.shape, np.inf)
    from scipy.spatial import cKDTree
    for i, k in enumerate(kk):
        g = targets[k]
        ins = contains_xy(g, fx, fy) & inblob & (dist > 0)  # first-come: COD first
        assign[ins] = i; dist[ins] = 0.0
        b = g.boundary
        segs = [b] if b.geom_type == 'LineString' else list(b.geoms)
        B = np.array([(x, y) for sg in segs for x, y in zip(*sg.xy)])
        d, _ = cKDTree(B).query(np.stack([fx, fy], 1))
        upd = inblob & (assign == -1) if False else (inblob & (dist > 0) & (d < dist))
        assign[upd] = i; dist[upd] = d[upd]
    classes = assign.reshape(gn, gn)
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    pieces = {}
    for i, k in enumerate(kk):
        cm = (classes == i).astype('uint8')
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = []
        for c in cs:
            if len(c) < 4 or cv2.contourArea(c) < 4:
                continue
            q = c.reshape(-1, 2).astype(float)
            polys.append(make_valid(Polygon(zip(minx + q[:, 0] * dx, miny + q[:, 1] * dy)).buffer(max(dx, dy) * 0.6)))
        pieces[k] = make_valid(unary_union(polys).intersection(blob)) if polys else None
    # exact coverage: leftover slivers go to the nearest piece
    rem = make_valid(blob.difference(unary_union([p for p in pieces.values() if p is not None])))
    if not rem.is_empty:
        geoms = list(rem.geoms) if rem.geom_type in ('MultiPolygon', 'GeometryCollection') else [rem]
        for g in geoms:
            if g.geom_type != 'Polygon' or g.area == 0:
                continue
            near = min([k for k in kk if pieces[k] is not None], key=lambda k: pieces[k].distance(g))
            pieces[near] = make_valid(unary_union([pieces[near], g]))
    D.update(pieces)
    D['_karachi_fit_targets'] = targets
    return D


def main():
    D = build_districts()
    cents = {r['seat']: (float(r['X']), float(r['Y']))
             for r in csv.DictReader(open(f'{BASE}/plotree_elections/essentials/NA_2018_centroids.csv'))}

    results, report = {}, []

    for na, key in SINGLE:
        tag = 'district-exact union (geoBoundaries ADM2)'
        if key in ('Sujawal', 'Thatta'):
            tag = 'district-exact (geoBoundaries ADM2; Sujawal carved via COD 2022)'
        results[na] = (D[key], tag, False)
        report.append((key, 'OK', 'exact'))

    for sheet, key, legend in JOBS:
        seats = [na for na, _ in legend]
        try:
            leg = [{'na': na, 'colour': col} for na, col in legend]
            feats, rms = split_district(f'{SD}/{sheet}', leg, D[key])
            missing = [s for s in seats if s not in feats or feats[s].is_empty]
            if missing:
                raise RuntimeError(f'missing {missing}')
            # Hungarian QA vs plotree centroids
            lat0 = D[key].centroid.y
            KX, KY = 111.32 * np.cos(np.radians(lat0)), 110.57
            P = np.array([[feats[s].centroid.x * KX, feats[s].centroid.y * KY] for s in seats])
            T = np.array([[cents[s][0] * KX, cents[s][1] * KY] for s in seats])
            C = ((P[:, None, :] - T[None, :, :]) ** 2).sum(-1)
            ri, ti = linear_sum_assignment(C)
            perm = {seats[r]: seats[t] for r, t in zip(ri, ti)}
            qa = 'centroid-QA ok' if all(k == v for k, v in perm.items()) else f'CENTROID-QA MISMATCH {perm}'
            tag = f'sheet-split (colour-fill): Sindh/{sheet}, outline-fit rms {rms:.1f}km'
            if key.endswith('Karachi'):
                tag += '; district COD-carved from gbOpen Karachi'
            for s in seats:
                results[s] = (feats[s], tag, False)
            report.append((key, 'OK', f'rms {rms:.1f} | {qa}'))
        except Exception as e:
            report.append((key, 'FAIL', str(e)[:90]))

    # Larkana: no sheet -> Voronoi of the 2 plotree centroids
    lark = D['Larkana']
    pts = [Point(*cents[s]) for s in ('NA-200', 'NA-201')]
    vor = voronoi_diagram(GeometryCollection(pts), envelope=lark.buffer(1.0))
    cells = list(vor.geoms)
    for s, pt in zip(('NA-200', 'NA-201'), pts):
        cell = next((c for c in cells if c.contains(pt)), None) or min(cells, key=lambda c: c.distance(pt))
        results[s] = (make_valid(cell.intersection(lark)),
                      'district-Voronoi (no ECP sheet for Larkana; plotree centroids) [approx]', True)
    report.append(('Larkana', 'VORONOI', 'no sheet (dis16 absent)'))

    v2 = json.load(open(f'{BASE}/data/na_2018delim_v2.geojson'))
    updated = 0
    for f in v2['features']:
        na = f['properties']['na']
        if na in results:
            g, src, approx = results[na]
            f['properties'] = {'na': na, 'dist': f['properties'].get('dist', ''),
                               'approx': bool(approx), 'src': src}
            f['geometry'] = mapping(make_valid(g).simplify(0.0015))
            updated += 1
    json.dump(v2, open(f'{BASE}/data/na_2018delim_v2.geojson', 'w'))

    print('=== report ===')
    for r in report:
        print(*r)
    print('updated seats:', updated, '/', len(results))
    return results, report


if __name__ == '__main__':
    main()
