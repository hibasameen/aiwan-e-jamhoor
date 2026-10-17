#!/usr/bin/env python3
"""
Measure a 207-seat boundary layer against the checks in docs/BOUNDARIES_TODO.md
('Validate before shipping'), so that any two attempts can be compared on the
same terms.

    python3 scripts/boundaries/validate_1977.py LAYER.geojson [--year 1997] [--json out.json]

  seats        distinct NA numbers with geometry, of the 207
  national     IoU of the union against the 2002-delimitation union (the same
               territory), and the share of that territory covered
  duplicated   area claimed by more than one seat, as % of the union
  district     share of seats whose interior point lies in a district its
               name implies (xwalk_207map.json over districts_2015), the
               median miss for those that do not, and the median share of
               each seat's area inside its own districts
  cities       Karachi: IoU of NA-184..196 against the 2002 Karachi seats;
               Lahore: IoU of NA-92..100 against Lahore district; Peshawar
               NA-1, Rawalpindi NA-38, Faisalabad NA-63..65: share of area
               inside the seat's own district

Areas are computed in an equal-area projection (EPSG:6933).
"""
import os, sys, json, argparse
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import numpy as np
import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union
import build_reconstructed_geometry as brg

KM = 105.0
EA = 'EPSG:6933'
CITIES = {'Karachi': [f'NA-{n}' for n in range(184, 197)],
          'Lahore': [f'NA-{n}' for n in range(92, 101)],
          'Peshawar NA-1': ['NA-1'], 'Rawalpindi NA-38': ['NA-38'],
          'Faisalabad NA-63..65': ['NA-63', 'NA-64', 'NA-65']}


def ea(geoms):
    return gpd.GeoSeries(list(geoms), crs='EPSG:4326').to_crs(EA)


def validate(path, year='1997'):
    xw = json.load(open('data/wip/trace/xwalk_207map.json'))
    XW = xw.get(year, xw['base'])
    DIST = brg.load_districts()
    c02 = json.load(open('data/na_constituencies_2002delim.geojson'))['features']
    true = unary_union([shape(f['geometry']).buffer(0) for f in c02])
    karachi02 = unary_union([shape(f['geometry']).buffer(0) for f in c02
                             if f['properties']['dist'] == 'Karachi'])

    feats = json.load(open(path))['features']
    by = {}
    for f in feats:
        na = f['properties'].get('na')
        g = shape(f['geometry']).buffer(0)
        by[na] = unary_union([by[na], g]) if na in by else g
    seats = {k: v for k, v in by.items() if k in XW and not v.is_empty}
    U = unary_union(list(seats.values()))
    A = ea([U, true, U.intersection(true), U.union(true)]).area.values
    areas = ea(seats.values()).area.values
    out = {'layer': path, 'features': len(feats), 'seats': len(seats),
           'national_iou': round(A[2] / A[3], 3), 'coverage_pct': round(100 * A[2] / A[1], 1),
           'duplicated_pct': round(100 * (areas.sum() - A[0]) / A[0], 2)}

    inside, miss, share = 0, [], []
    for na, g in seats.items():
        ds = unary_union([DIST[d] for d in XW[na] if d in DIST])
        p = g.representative_point()
        d = ds.distance(p) * KM
        if d == 0:
            inside += 1
        else:
            miss.append(d)
        a = ea([g, g.intersection(ds)]).area.values
        share.append(a[1] / a[0] if a[0] else 0)
    out['in_district_pct'] = round(100 * inside / len(seats), 1)
    out['in_district_miss_median_km'] = round(float(np.median(miss)), 1) if miss else 0.0
    out['area_in_own_district_median_pct'] = round(100 * float(np.median(share)), 1)

    cities = {}
    for name, nas in CITIES.items():
        have = [seats[n] for n in nas if n in seats]
        rec = {'seats': f'{len(have)}/{len(nas)}'}
        if have:
            g = unary_union(have)
            if name == 'Karachi':
                ref = karachi02
            elif name == 'Lahore':
                ref = DIST['Lahore']
            else:
                ref = unary_union([DIST[d] for n in nas for d in XW[n][:1]])
            a = ea([g, ref, g.intersection(ref), g.union(ref)]).area.values
            if name in ('Karachi', 'Lahore'):
                rec['iou'] = round(a[2] / a[3], 3)
            rec['inside_own_district_pct'] = round(100 * a[2] / a[0], 1)
            rec['centroid_offset_km'] = round(g.centroid.distance(ref.centroid) * KM, 1) \
                if name in ('Karachi', 'Lahore') else None
        cities[name] = rec
    out['cities'] = cities
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('layer')
    ap.add_argument('--year', default='1997')
    ap.add_argument('--json')
    a = ap.parse_args()
    r = validate(a.layer, a.year)
    print(json.dumps(r, indent=1))
    if a.json:
        json.dump(r, open(a.json, 'w'), indent=1)
