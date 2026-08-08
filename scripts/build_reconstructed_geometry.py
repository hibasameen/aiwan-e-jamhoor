#!/usr/bin/env python3
"""
Reconstruct approximate NA constituency boundaries for the 2018 and 2023 delimitations.

Method
------
Both delimitations allocate NA seats to districts (with a few seats spanning 2+
districts, named "X-cum-Y"). ECP has never published GIS files, so we reconstruct:

1. Group seats by the districts they occupy; merge groups that share any district
   into connected components (handles "cum" seats overlapping single-district seats).
2. A component with one seat gets the exact union of its districts (boundary is
   district-accurate).
3. A component with k>1 seats is split by a Voronoi diagram over k seed points,
   clipped to the component region. Seeds, in order of preference:
     a. the Dawn/plotree GE-2018 seat centroids when the component's seat count
        matches the 2018 grouping (keeps intra-city layout consistent with the
        2018 web map, which followed ECP numbering);
     b. the centroid of the seat's own district-union (for multi-district "cum"
        seats inside a bigger component);
     c. k-means cell centres over the region (Karachi 2024 = 22 seats vs 21 in
        2018; Sanghar 2024), ordered north->south then west->east to mimic ECP
        numbering direction.
4. Exterior rings are wound clockwise (shapely orient sign=-1) because d3-geo
   treats RFC-7946 counter-clockwise polygons as sphere-inverted.

Accuracy: district-level boundaries are as good as the source district file
(2015 CartoDB digitisation); within-district splits are APPROXIMATE — hundreds
of metres to kilometres off, worst inside big cities. All split features carry
properties.approx = true.

Inputs
------
- data/districts_2015.geojson              (from plotree pakistan_districts.topojson)
- data/plotree_elections/essentials/NA_seats_2018.csv       (2018 seat -> district)
- data/plotree_elections/essentials/NA_2018_centroids.csv   (2018 seat centroids)
- data/na_2024_districts.csv               (2024 seat -> district, scraped/verified)

Outputs
-------
- na_2018delim_raw.geojson  (272 features)
- na_2024delim_raw.geojson  (266 features)
Post-process with:
  mapshaper <raw> -simplify 15% keep-shapes -clean -o precision=0.0001 <simplified>
then re-wind for d3 (see rewind() here or scripts/build_map.py).
"""
import json, csv, sys
import numpy as np
from collections import defaultdict
from shapely.geometry import shape, mapping, Point, MultiPolygon, GeometryCollection
from shapely.ops import unary_union, voronoi_diagram
from shapely import make_valid
from shapely.geometry.polygon import orient

BASE = '.'

# ---- district name harmonisation --------------------------------------------
# new districts (created after the 2015 district file) -> parent in the file
NEW2OLD = {'Murree':'Rawalpindi','Talagang':'Chakwal','Wazirabad':'Gujranwala','Kot Addu':'Muzaffargarh',
 'Taunsa':'Dera Ghazi Khan','Keamari':'Karachi','Upper South Waziristan':'South Waziristan Agency',
 'Lower South Waziristan':'South Waziristan Agency','South Waziristan Upper':'South Waziristan Agency',
 'South Waziristan Lower':'South Waziristan Agency','Upper Chitral':'Chitral','Lower Chitral':'Chitral',
 'Hub':'Lasbela','Usta Muhammad':'Jaffarabad','Surab':'Kalat','Chaman':'Killa Abdullah',
 'North Waziristan':'North Waziristan Agency','Kacchi':'Kachhi','Karachi East':'Karachi','Karachi West':'Karachi',
 'Karachi Central':'Karachi','Karachi South':'Karachi','Korangi':'Karachi','Malir':'Karachi',
 'Shaheed Benazirabad':'Nawabshah','Kolai Palas':'Kohistan','Upper Kohistan':'Kohistan','Lower Kohistan':'Kohistan',
 'Central Kurram':'Kurram Agency','Kurram':'Kurram Agency','Orakzai':'Orakzai Agency','Khyber':'Khyber Agency',
 'Mohmand':'Mohmand Agency','Bajaur':'Bajaur Agency','Duki':'Loralai','Sohbatpur':'Jaffarabad',
 'Shaheed Sikandarabad':'Kalat','Lehri':'Sibi',
 # spelling variants
 'Tando Allahyar':'Tando Allah Yar','Mirpur Khas':'Mirpurkhas','Battagram':'Batagram',
 'Chagai':'Chaghi','Musakhel':'Musakhail','Qambar Shahdadkot':'Kambar-Shahdadkot','Torghar':'Tor Ghar',
 'Naushahro Feroze':'Naushehro Feroze','Kolai Palas Kohistan':'Kohistan','Sujawal':'Sajawal'}

def load_districts():
    gj = json.load(open(f'{BASE}/data/districts_2015.geojson'))
    dist = {}
    for f in gj['features']:
        g = make_valid(shape(f['geometry']))
        n = f['properties']['districts']
        dist[n] = unary_union([dist[n], g]) if n in dist else g
    return dist

def resolve(d, tnames):
    d = d.strip()
    if d in tnames: return d
    if d in NEW2OLD: return NEW2OLD[d]
    raise KeyError(f'unknown district: {d}')

# ---- seat -> district tables -------------------------------------------------
def seats_2018(tnames):
    FIX = {'Kacchi':'Kachhi'}
    def parts(name):
        return [FIX.get(p.strip(), p.strip()) for p in name.split(' - ')] if name.strip() else []
    out = {}
    for r in csv.DictReader(open(f'{BASE}/data/plotree_elections/essentials/NA_seats_2018.csv')):
        out[r['Seat']] = sorted({resolve(d, tnames) for d in parts(r['PrimaryDistrict']) + parts(r['SeconDistrict'])})
    return out

def seats_2024(tnames):
    out = {}
    for r in csv.DictReader(open(f'{BASE}/data/na_2024_districts.csv')):
        out[r['na']] = sorted({resolve(d, tnames) for d in r['districts'].split(';')})
    return out

def centroids_2018():
    return {r['seat']: (float(r['X']), float(r['Y']))
            for r in csv.DictReader(open(f'{BASE}/data/plotree_elections/essentials/NA_2018_centroids.csv'))}

# ---- component construction --------------------------------------------------
def components(seat_districts):
    """Union-find over seats sharing any district."""
    parent = {}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    by_district = defaultdict(list)
    for s, ds in seat_districts.items():
        parent[s] = s
        for d in ds: by_district[d].append(s)
    for seats in by_district.values():
        for s in seats[1:]: union(seats[0], s)
    comp = defaultdict(list)
    for s in seat_districts: comp[find(s)].append(s)
    return list(comp.values())

def kmeans_seeds(poly, k, seed=42):
    rng = np.random.default_rng(seed)
    minx, miny, maxx, maxy = poly.bounds
    pts = []
    while len(pts) < max(400, 40 * k):
        xs = rng.uniform(minx, maxx, 1000); ys = rng.uniform(miny, maxy, 1000)
        for x, y in zip(xs, ys):
            if poly.contains(Point(x, y)): pts.append((x, y))
            if len(pts) >= max(400, 40 * k): break
    P = np.array(pts)
    C = P[rng.choice(len(P), k, replace=False)]
    for _ in range(30):
        a = ((P[:, None, :] - C[None, :, :]) ** 2).sum(-1).argmin(1)
        C = np.array([P[a == i].mean(0) if (a == i).any() else C[i] for i in range(k)])
    return [tuple(c) for c in C]

def build(seat_districts, dist, cents18=None, group18=None, own_cents=None):
    """Return list of {'na','geom','approx'} covering all seats.
    own_cents: per-seat centroids for THIS delimitation (used for 2018, where the
    Dawn/plotree centroids cover every seat). cents18+group18: predecessor-seat
    seeding for a later delimitation."""
    feats = []
    for seats in components(seat_districts):
        seats.sort(key=lambda x: int(x.split('-')[1]))
        all_ds = sorted({d for s in seats for d in seat_districts[s]})
        region = make_valid(unary_union([dist[d] for d in all_ds]))
        if len(seats) == 1:
            feats.append({'na': seats[0], 'geom': region, 'approx': False})
            continue
        # seeds
        seeds, used18 = [], False
        if own_cents is not None and all(s in own_cents for s in seats):
            seeds = [own_cents[s] for s in seats]
        if not seeds and cents18 is not None and group18 is not None:
            key = frozenset(all_ds)
            s18 = sorted(group18.get(key, []), key=lambda x: int(x.split('-')[1]))
            if len(s18) == len(seats):
                seeds = [cents18[s] for s in s18]; used18 = True
        if not seeds:
            # per-seat: centroid of own district union; identical district-sets share -> kmeans that subset
            from collections import Counter
            sig = Counter(tuple(seat_districts[s]) for s in seats)
            if all(v == 1 for v in sig.values()):
                seeds = [unary_union([dist[d] for d in seat_districts[s]]).centroid.coords[0] for s in seats]
            else:
                seeds = kmeans_seeds(region, len(seats))
                seeds.sort(key=lambda p: (-p[1], p[0]))  # N->S, W->E like ECP numbering
        pts = [Point(*s) for s in seeds]
        vor = voronoi_diagram(GeometryCollection(pts), envelope=region.buffer(1.0))
        cells = list(vor.geoms)
        for s, pt in zip(seats, pts):
            cell = next((c for c in cells if c.contains(pt)), None) or min(cells, key=lambda c: c.distance(pt))
            piece = make_valid(cell.intersection(region))
            feats.append({'na': s, 'geom': piece, 'approx': True})
    return feats

def fix_orient(g):
    if g.geom_type == 'Polygon': return orient(g, sign=-1.0)
    if g.geom_type == 'MultiPolygon': return MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
    polys = []
    for x in getattr(g, 'geoms', []):
        if x.geom_type == 'Polygon': polys.append(orient(x, sign=-1.0))
        elif x.geom_type == 'MultiPolygon': polys += [orient(p, sign=-1.0) for p in x.geoms]
    return MultiPolygon(polys)

def write(feats, seat_districts, path):
    out = {'type': 'FeatureCollection', 'features': []}
    for f in feats:
        if f['geom'].is_empty:
            print('WARN empty geometry:', f['na']); continue
        out['features'].append({'type': 'Feature',
            'properties': {'na': f['na'], 'dist': ' / '.join(seat_districts[f['na']]), 'approx': f['approx']},
            'geometry': mapping(fix_orient(f['geom']))})
    json.dump(out, open(path, 'w'))
    print(path, len(out['features']), 'features,',
          sum(1 for x in out['features'] if x['properties']['approx']), 'approx')

if __name__ == '__main__':
    dist = load_districts()
    tnames = set(dist)
    sd18 = seats_2018(tnames)
    cents = centroids_2018()
    g18 = defaultdict(list)
    for s, ds in sd18.items(): g18[frozenset(ds)].append(s)

    write(build(sd18, dist, own_cents=cents), sd18, 'na_2018delim_raw.geojson')
    sd24 = seats_2024(tnames)
    write(build(sd24, dist, cents, g18), sd24, 'na_2024delim_raw.geojson')
