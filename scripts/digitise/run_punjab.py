#!/usr/bin/env python3
"""Leg 3 driver: Punjab 2018. Sheets are LINE-BOUNDED (thick red NA boundaries,
no colour fills, 1200-1600 px). Pipeline per district:
red-line barrier mask -> interior connected components = seat regions ->
outline ICP+TPS fit to geoBoundaries district -> Hungarian assignment of regions
to seats by Dawn/plotree 2018 centroids -> label-transfer grid split (seamless).
City districts (Rawalpindi/Faisalabad/Gujranwala): rural regions matched first;
leftover blob split by Voronoi of the city seats' centroids (blob outline true).
Lahore (black-line PBS sheet) attempted with a dark-line variant.
"""
import json, csv, sys
sys.path.insert(0, 'scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping, Polygon, Point, GeometryCollection, MultiPolygon
from shapely.ops import unary_union, voronoi_diagram
from shapely import make_valid
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from split_district_by_sheet import fit_outline

SD = '/mnt/user-data/uploads/Aiwan-e-Jamhoor/2018 Delimitation/Punjab'
gb = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
      for f in json.load(open('data/gb_PAK_ADM2.geojson'))['features']}
old = json.load(open('data/districts_2015.geojson'))
d15 = {}
for f in old['features']:
    g = make_valid(shape(f['geometry']))
    n = f['properties']['districts']
    d15[n] = unary_union([d15[n], g]) if n in d15 else g
cents = {r['seat']: (float(r['X']), float(r['Y']))
         for r in csv.DictReader(open('data/plotree_elections/essentials/NA_2018_centroids.csv'))}

# harmonize gb: carve Chiniot (from Jhang) and Nankana Sahib (from Sheikhpura)
def carve(parent_gb, child_15):
    piece = make_valid(gb[parent_gb].intersection(d15[child_15].buffer(0.01)))
    rest = make_valid(gb[parent_gb].difference(piece))
    return rest, piece
if 'Chiniot' in d15:
    gb['Jhang'], gb['Chiniot'] = carve('Jhang', 'Chiniot')
if 'Nankana Sahib' in d15:
    gb['Sheikhpura'], gb['Nankana Sahib'] = carve('Sheikhpura', 'Nankana Sahib')

GBN = {'Sheikhupura': 'Sheikhpura', 'Vehari': 'Vihari', 'Mandi Bahauddin': 'Mandi Bahauddin',
       'Toba Tek Singh': 'Toba Tek Singh'}

# sheet, district, seats(range), city_seats (on companion sheet / inside blob)
JOBS = [
 ('dis35.jpg','Attock',['NA-55','NA-56'],[]),
 ('dis27.jpg','Rawalpindi',[f'NA-{i}' for i in range(57,64)],['NA-60','NA-61','NA-62']),
 ('dis39.jpg','Chakwal',['NA-64','NA-65'],[]),
 ('dis9.jpg','Jhelum',['NA-66','NA-67'],[]),
 ('dis7.jpg','Gujrat',[f'NA-{i}' for i in range(68,72)],[]),
 ('dis32.jpg','Sialkot',[f'NA-{i}' for i in range(72,77)],[]),
 ('dis22.jpg','Narowal',['NA-77','NA-78'],[]),
 ('dis5.jpg','Gujranwala',[f'NA-{i}' for i in range(79,85)],['NA-81','NA-82']),
 ('dis16.jpg','Mandi Bahauddin',['NA-85','NA-86'],[]),
 ('dis30.jpg','Sargodha',[f'NA-{i}' for i in range(88,93)],[]),
 ('dis12.jpg','Khushab',['NA-93','NA-94'],[]),
 ('dis20.jpg','Mianwali',['NA-95','NA-96'],[]),
 ('dis38.jpg','Bhakkar',['NA-97','NA-98'],[]),
 ('dis1.jpg','Chiniot',['NA-99','NA-100'],[]),
 ('dis3.jpg','Faisalabad',[f'NA-{i}' for i in range(101,111)],['NA-107','NA-108','NA-109','NA-110']),
 ('dis33.jpg','Toba Tek Singh',['NA-111','NA-112','NA-113'],[]),
 ('dis8.jpg','Jhang',['NA-114','NA-115','NA-116'],[]),
 ('dis21.jpg','Nankana Sahib',['NA-117','NA-118'],[]),
 ('dis31.jpg','Sheikhupura',[f'NA-{i}' for i in range(119,123)],[]),
 ('dis13.jpg','Lahore',[f'NA-{i}' for i in range(123,137)],[]),
 ('dis10.jpg','Kasur',[f'NA-{i}' for i in range(137,141)],[]),
 ('dis23.jpg','Okara',[f'NA-{i}' for i in range(141,145)],[]),
 ('dis24.jpg','Pakpattan',['NA-145','NA-146'],[]),
 ('dis29.jpg','Sahiwal',['NA-147','NA-148','NA-149'],[]),
 ('dis11.jpg','Khanewal',[f'NA-{i}' for i in range(150,154)],[]),
 ('dis17.jpg','Multan',[f'NA-{i}' for i in range(154,160)],[]),
 ('dis15.jpg','Lodhran',['NA-160','NA-161'],[]),
 ('dis34.jpg','Vehari',[f'NA-{i}' for i in range(162,166)],[]),
 ('dis36.jpg','Bahawalnagar',[f'NA-{i}' for i in range(166,170)],[]),
 ('dis37.jpg','Bahawalpur',[f'NA-{i}' for i in range(170,175)],[]),
 ('dis25.jpg','Rahim Yar Khan',[f'NA-{i}' for i in range(175,181)],[]),
 ('dis19.jpg','Muzaffargarh',[f'NA-{i}' for i in range(181,187)],[]),
 ('dis14.jpg','Layyah',['NA-187','NA-188'],[]),
 ('dis2.jpg','Dera Ghazi Khan',[f'NA-{i}' for i in range(189,193)],[]),
 ('dis26.jpg','Rajanpur',['NA-193','NA-194','NA-195'],[]),
]

def region_masks(img, n_expect, dark=False):
    """Barrier = thick red (or dark) lines; return list of region masks sorted by area."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    H, W = h.shape
    if dark:
        red = ((v < 110) & (s < 90)).astype(np.uint8)
    else:
        red = ((((h <= 12) | (h >= 165)) & (s > 55) & (v > 60))).astype(np.uint8)
    for dil in (2, 3, 4, 5):
        bar = cv2.dilate(red, np.ones((dil, dil), np.uint8))
        free = (1 - bar).astype(np.uint8)
        margin = np.zeros_like(free); margin[:4, :] = 1; margin[-4:, :] = 1; margin[:, :4] = 1; margin[:, -4:] = 1
        n, lab, stats, _ = cv2.connectedComponentsWithStats(free, 4)
        outside = set(np.unique(lab[margin > 0]))
        regs = [(stats[i][4], i) for i in range(1, n) if i not in outside and stats[i][4] > 0.001 * H * W]
        regs.sort(reverse=True)
        if len(regs) >= n_expect:
            keep = regs[:max(n_expect, len([r for r in regs if r[0] > 0.005 * H * W]))]
            masks = []
            for a, i in keep:
                m = (lab == i).astype(np.uint8)
                masks.append(cv2.dilate(m, np.ones((dil + 1, dil + 1), np.uint8)))  # reclaim barrier width
            return masks
    return None

def process(sheet, dname, seats, city):
    img = cv2.imread(f'{SD}/{sheet}')
    if img is None:
        raise IOError(sheet)
    gbd = gb[GBN.get(dname, dname)]
    rural = [s for s in seats if s not in city]
    n_regions = len(rural) + (1 if city else 0)
    masks = region_masks(img, n_regions, dark=(dname == 'Lahore'))
    if masks is None:
        raise RuntimeError('region extraction failed')
    masks = masks[:n_regions]
    union = np.zeros_like(masks[0])
    for m in masks:
        union |= m
    union = cv2.morphologyEx((union * 255), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)) // 255
    px_to_metric, (KX, KY), rms = fit_outline(union, gbd)
    # region centroids -> metric
    mcent = []
    for m in masks:
        ys, xs = np.nonzero(m)
        mcent.append(px_to_metric(np.array([[xs.mean(), ys.mean()]]))[0])
    mcent = np.array(mcent)
    # target centroids: rural seats + (blob = mean of city centroids)
    targets = [np.array([cents[s][0] * KX, cents[s][1] * KY]) for s in rural]
    tnames = list(rural)
    if city:
        cc = np.array([[cents[s][0] * KX, cents[s][1] * KY] for s in city]).mean(0)
        targets.append(cc); tnames.append('__BLOB__')
    T = np.array(targets)
    C = ((mcent[:, None, :] - T[None, :, :]) ** 2).sum(-1)
    ri, ti = linear_sum_assignment(C)
    assign = {}
    for r, t in zip(ri, ti):
        assign[tnames[t]] = r
    # label transfer grid
    pts, labs = [], []
    order = []
    for k, (name, ridx) in enumerate(sorted(assign.items(), key=lambda x: x[0])):
        m = masks[ridx]
        ys, xs = np.nonzero(m)
        step = max(1, len(xs) // 15000)
        pts.append(np.stack([xs[::step], ys[::step]], 1)); labs.append(np.full(len(xs[::step]), k))
        order.append(name)
    P = np.concatenate(pts); L = np.concatenate(labs)
    M = px_to_metric(P); tree = cKDTree(M)
    minx, miny, maxx, maxy = gbd.bounds
    gn = 480
    gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
    XX, YY = np.meshgrid(gx, gy)
    _, gi = tree.query(np.stack([XX.ravel() * KX, YY.ravel() * KY], 1))
    classes = L[gi].reshape(gn, gn)
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    feats = {}
    for k, name in enumerate(order):
        cm = (classes == k).astype(np.uint8)
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = []
        for c in cs:
            if len(c) < 4 or cv2.contourArea(c) < 9:
                continue
            q = c.reshape(-1, 2).astype(float)
            polys.append(make_valid(Polygon(zip(minx + q[:, 0] * dx, miny + q[:, 1] * dy)).buffer(max(dx, dy) * 0.6)))
        if polys:
            feats[name] = make_valid(unary_union(polys).intersection(gbd))
    # blob -> voronoi split among city seats
    if city and '__BLOB__' in feats:
        blob = feats.pop('__BLOB__')
        pts2 = [Point(*cents[s]) for s in city]
        vor = voronoi_diagram(GeometryCollection(pts2), envelope=blob.buffer(1.0))
        cells = list(vor.geoms)
        for s, pt in zip(city, pts2):
            cell = next((c for c in cells if c.contains(pt)), None) or min(cells, key=lambda c: c.distance(pt))
            feats[s] = make_valid(cell.intersection(blob))
    missing = [s for s in seats if s not in feats or feats[s].is_empty]
    if missing:
        raise RuntimeError(f'missing {missing}')
    return feats, rms

results, report = {}, []
for sheet, dname, seats, city in JOBS:
    try:
        feats, rms = process(sheet, dname, seats, city)
        tag = f'sheet-split (red-line trace): Punjab/{sheet}, outline-fit rms {rms:.1f}km'
        if city:
            tag += f'; city seats {"/".join(city)} voronoi within true blob'
        for na, g in feats.items():
            src = tag if na not in city else tag + ' [city-approx]'
            results[na] = (g, src, na in city)
        report.append((dname, 'OK', f'rms {rms:.1f}'))
    except Exception as e:
        report.append((dname, 'FALLBACK', str(e)[:70]))

# Hafizabad single seat
results['NA-87'] = (gb['Hafizabad'], 'district-exact union (geoBoundaries ADM2)', False)

v2 = json.load(open('data/na_2018delim_v2.geojson'))
for f in v2['features']:
    na = f['properties']['na']
    if na in results:
        g, src, approx = results[na]
        f['properties'] = {'na': na, 'dist': f['properties'].get('dist', ''), 'approx': bool(approx), 'src': src}
        f['geometry'] = mapping(make_valid(g).simplify(0.0015))
json.dump(v2, open('data/na_2018delim_v2.geojson', 'w'))
print('=== report ===')
for r in report:
    print(*r)
print('updated seats:', len(results))
