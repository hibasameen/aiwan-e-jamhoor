#!/usr/bin/env python3
"""
Check the seat numbers of the 207-seat layer against the NA labels printed on
the Commons maps it was traced from.

Each seat of the merged trace (na_207seat_1985-1997_traced.geojson, the input
to tessellate_207.py) is one region of the 1990, 1993 or 1997 map. In the
shipped pipeline (trace_commons_full.py) the number on that region came from
tesseract or, where tesseract read nothing usable, from elimination or
north-to-south pairing inside the district. The labels are set in a 13-glyph
bitmap font, so scripts/digitise/map_labels.py reads every one exactly. This
script finds the region each seat was traced from and compares.

Linking a seat to its region needs no new fitting:

  main map  the shipped quadratic warp is cached (data/wip/trace/
            ge<year>_poly.npy). A region is the seat's source if its outline,
            traced and warped as trace_commons_full.py does it, matches the
            seat's merged geometry (IoU >= 0.9; all links come out at 1.000).
  boxes     the shipped inset affines were not saved, so each box's affine is
            recovered from its tesseract-labelled regions in the committed
            na_traced2_<year>.geojson (outline centroid -> feature centroid,
            least squares) and used the same way. The Peshawar and Rawalpindi
            boxes hold one seat each and are linked by their label.

The three maps are one drawing: every uniquely printed label sits at the same
pixel offset from its 1993 position (reported in the summary), so a region can
be read on all three maps. Each seat then gets three tests:

  printed   the label printed in its source region
  colour    the region's fill on the 1990, 1993 and 1997 maps, as a party (key:
            the modal recorded winner among exactly-labelled regions of that
            fill), against the winners of the seat's number and of the printed
            one. A year counts only where those two winners differ.
  district  share of the region, placed by the shipped transform, inside the
            districts each number's name implies (xwalk_207map.json), on the
            2023 district layer; names it lacks fall back to districts_2015.

The colour test confirms which region a printed label belongs to (the map's
author coloured each region by its label); only the district test is
independent of the map's own labelling, and it carries the warp's error
(median ~4.7 km).

The summary also places every printed label in the tessellated layer with the
shipped transform and reports which seat it lands in.

    python3 scripts/boundaries/audit_207_identity.py [--merged M --layer L]
                                                     [--crops [--compare L2]]

Writes seats_207.csv, regions_<year>.csv and summary.json to data/wip/identity
(--out), and with --crops one figure per group of disputed seats.
"""
import os, sys, csv, json, collections, argparse
_here = os.path.dirname(os.path.abspath(__file__))
for _g in ('digitise', 'boundaries'):
    sys.path.insert(0, os.path.join(_here, '..', _g))
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
import read_labelled_map as RL
import georef_refine as GR
import build_reconstructed_geometry as brg
from map_labels import read_labels

OUT = 'data/wip/identity'
BASE_YEAR = '1993'
YEARS = ('1990', '1993', '1997')
MERGED = 'data/boundaries/na_207seat_1985-1997_traced.geojson'
LAYER = 'data/boundaries/na_207seat_1985-1997_tessellated.geojson'
XWALK = 'data/wip/trace/xwalk_207map.json'
KM = 105.0
# the results files call the 1990 PPP-led alliance by either name
ALIAS = {'1990': {'PPP': 'PDA'}}
# xwalk_207map.json uses the 2015 district names; the 2023 layer renamed or
# split some. Names not listed and not in the 2023 layer fall back to 2015.
D23 = {'Bajaur Agency': ['Bajaur'], 'Batagram': ['Battagram'], 'Chaghi': ['Chagai'],
       'Chitral': ['Lower Chitral', 'Upper Chitral'], 'Khyber Agency': ['Khyber'],
       'Kohistan': ['Lower Kohistan', 'Upper Kohistan', 'Kolai Palas Kohistan'],
       'Kurram Agency': ['Kurram'], 'Mohmand Agency': ['Mohmand'], 'Orakzai Agency': ['Orakzai'],
       'North Waziristan Agency': ['North Waziristan'], 'South Waziristan Agency': ['South Waziristan'],
       'Tor Ghar': ['Torghar'], 'Kambar-Shahdadkot': ['Qambar Shahdadkot'],
       'Karachi': ['Karachi Central', 'Karachi East', 'Karachi South', 'Karachi West', 'Korangi', 'Malir'],
       'Mirpurkhas': ['Mirpur Khas'], 'Naushehro Feroze': ['Naushahro Feroze'], 'Sajawal': ['Sujawal'],
       'Tando Allah Yar': ['Tando Allahyar'], 'Musakhail': ['Musakhel'],
       # 2023 districts carved out of a 2015 one
       'Muzaffargarh': ['Muzaffargarh', 'Kot Addu'], 'Dera Ghazi Khan': ['Dera Ghazi Khan', 'Taunsa'],
       'Gujranwala': ['Gujranwala', 'Wazirabad'], 'Loralai': ['Loralai', 'Duki'],
       'Killa Abdullah': ['Killa Abdullah', 'Chaman']}


# ---- pixel side ----------------------------------------------------------------
def rkey(r):
    return ','.join(map(str, r['bbox'])) + ':' + str(r['area'])


def land_components(a):
    """As in trace_commons_full.py: the main map is the largest component."""
    lum = a.sum(2)
    m = ndimage.binary_fill_holes(ndimage.binary_closing(lum >= 200, np.ones((9, 9))))
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return lab, int(np.argmax(sizes)) + 1


def pixel_polygon(r):
    """The region outline exactly as trace_commons_full.contours_ll draws it,
    left in pixel coordinates."""
    cs, _ = cv2.findContours(r['comp'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cs:
        if cv2.contourArea(c) < 25:
            continue
        c = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2).astype(float)
        if len(c) < 4:
            continue
        c[:, 0] += r['bbox'][0]
        c[:, 1] += r['bbox'][1]
        p = Polygon(c).buffer(0)
        if p.is_valid and p.area > 0:
            polys.append(p)
    return unary_union(polys) if polys else None


def deep_point(r):
    x0, y0 = r['bbox'][:2]
    m = np.pad(ndimage.binary_fill_holes(r['comp']), 1)
    d = ndimage.distance_transform_edt(m)
    yy, xx = np.unravel_index(np.argmax(d), d.shape)
    return np.array([x0 + xx - 1, y0 + yy - 1], float)


def warp_geom(g, f):
    def ring(c):
        return f(np.asarray(c.coords, float))
    ps = g.geoms if g.geom_type == 'MultiPolygon' else [g]
    return unary_union([Polygon(ring(p.exterior), [ring(i) for i in p.interiors]).buffer(0) for p in ps])


def trace_region(m, r):
    """Region r of map m in lon/lat, through the same transform the shipped
    traces used; None where its box has no recovered transform."""
    w = m['warps'].get(r['cid'])
    pp = pixel_polygon(r)
    return None if w is None or pp is None else warp_geom(pp, w)


def iou(a, b):
    u = a.union(b).area
    return a.intersection(b).area / u if u else 0.0


def results(year):
    al = ALIAS.get(year, {})
    out = {}
    for r in csv.DictReader(open(f'data/results_{year}/na_{year}_constituency.csv', encoding='utf-8')):
        w = r['winner_party'].strip()
        out[r['na']] = {'party': al.get(w, w), 'name': r['constituency_name'].strip()}
    return out


def audit_map(year):
    path = f'data/sources/Pakistan_General_election_{year}.png'
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    H, W = a.shape[:2]
    _, _, _, regions = RL.segment(path)
    cache = json.load(open(f'data/wip/trace/labels_{year}.json'))
    lab, main_cid = land_components(a)
    rid = np.full((H, W), -1, np.int32)
    for i, r in enumerate(regions):
        x0, y0, x1, y1 = r['bbox']
        rid[y0:y1, x0:x1][r['comp']] = i
        r['i'], r['key'] = i, rkey(r)
        r['ocr'] = cache.get(r['key'])
        sub = lab[y0:y1, x0:x1][r['comp']]
        sub = sub[sub > 0]
        r['cid'] = int(np.bincount(sub).argmax()) if len(sub) else 0
        r['main'] = r['cid'] == main_cid
        r['hex'] = '#%02x%02x%02x' % tuple(int(v) for v in r['fill'])
        r['exact'], r['words'] = [], []

    # exact labels, each attached to the region most of the pixels around it belong to
    words = [w for w in read_labels(a) if w['na']]
    for w in words:
        x0, y0, x1, y1 = w['bbox']
        win = rid[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3]
        v = win[win >= 0]
        w['rid'] = int(np.bincount(v).argmax()) if len(v) else -1
        w['share'] = float((v == w['rid']).mean()) if len(v) else 0.0
        if w['rid'] >= 0:
            regions[w['rid']]['exact'].append(w['na'])
            regions[w['rid']]['words'].append(w)

    # colour key for this map: modal recorded winner among exactly-labelled regions
    res = results(year)
    byc = collections.defaultdict(collections.Counter)
    for r in regions:
        for na in set(r['exact']):
            if res.get(na, {}).get('party'):
                byc[r['hex']][res[na]['party']] += 1
    key = {hx: c.most_common(1)[0][0] for hx, c in byc.items()}

    # link regions to the committed traced features of this map
    traced = json.load(open(f'data/wip/trace/na_traced2_{year}.geojson'))['features']
    tg = [(f['properties'], shape(f['geometry']).buffer(0)) for f in traced]
    tby = {p['na']: (p, g) for p, g in tg}
    coef = np.load(f'data/wip/trace/ge{year}_poly.npy')
    warps = {main_cid: lambda P: GR.forward(np.atleast_2d(np.asarray(P, float)), coef, 2)}
    ocr_best = {}
    for r in regions:
        if r['ocr'] and (r['ocr'] not in ocr_best or r['area'] > ocr_best[r['ocr']]['area']):
            ocr_best[r['ocr']] = r
    pairs = collections.defaultdict(list)
    for na, r in ocr_best.items():
        if r['main'] or na not in tby or not tby[na][0].get('inset'):
            continue
        pp = pixel_polygon(r)
        if pp is not None:
            c = tby[na][1].centroid
            pairs[r['cid']].append((pp.centroid.x, pp.centroid.y, c.x, c.y))
    for cid, P in pairs.items():
        if len(P) < 3:
            continue
        P = np.array(P)
        A, *_ = np.linalg.lstsq(np.column_stack([P[:, :2], np.ones(len(P))]), P[:, 2:], rcond=None)
        warps[cid] = (lambda A: lambda Q: np.column_stack(
            [np.atleast_2d(np.asarray(Q, float)), np.ones(len(np.atleast_2d(Q)))]) @ A)(A)
    for r in regions:
        r['ll'] = r['link'] = r['link_iou'] = None
        w = warps.get(r['cid'])
        if w is None:
            continue
        r['ll'] = w(deep_point(r))[0]
        pt = Point(*r['ll'])
        hit = [(p, g) for p, g in tg if bool(p.get('inset')) == (not r['main']) and g.contains(pt)]
        pp = pixel_polygon(r)
        if hit and pp is not None:
            r['link_iou'] = round(iou(warp_geom(pp, w), hit[0][1]), 3)
            if r['link_iou'] >= 0.9:
                r['link'] = hit[0][0]['na']
    for p, g in tg:
        if not p.get('inset') or any(r['link'] == p['na'] for r in regions):
            continue
        r = ocr_best.get(p['na'])
        if r is not None and not r['main'] and r['hex'] == p['hex'] and r['cid'] not in warps:
            r['link'] = p['na']
    unlinked = sorted({p['na'] for p, _ in tg} - {r['link'] for r in regions if r['link']},
                      key=lambda s: int(s[3:]))
    return {'year': year, 'a': a, 'rid': rid, 'regions': regions, 'words': words, 'key': key,
            'res': res, 'warps': warps, 'main_cid': main_cid, 'unlinked': unlinked, 'traced': tby}


def offsets(maps):
    """Pixel offset of each map from the base map, from the uniquely printed labels."""
    pos = {y: collections.defaultdict(list) for y in maps}
    for y, m in maps.items():
        for w in m['words']:
            pos[y][w['na']].append((w['cx'], w['cy']))
    out = {}
    for y in maps:
        d = collections.Counter()
        for na, v in pos[BASE_YEAR].items():
            if len(v) == 1 and len(pos[y].get(na, [])) == 1:
                (x0, y0), (x1, y1) = v[0], pos[y][na][0]
                d[(int(round(x1 - x0)), int(round(y1 - y0)))] += 1
        (off, n), = d.most_common(1)
        out[y] = {'offset': off, 'labels_agreeing': n, 'labels_compared': sum(d.values())}
    return out


def fill_on(m, r, off):
    """Party of region r (base-map pixels) as drawn on map m, shifted by off."""
    a = m['a']
    x0, y0, x1, y1 = r['bbox']
    ys, xs = np.nonzero(r['comp'])
    ys, xs = ys + y0 + off[1], xs + x0 + off[0]
    ok = (ys >= 0) & (ys < a.shape[0]) & (xs >= 0) & (xs < a.shape[1])
    px = a[ys[ok], xs[ok]]
    px = px[px.sum(1) >= 200]
    if not len(px):
        return '', ''
    v, c = np.unique(px, axis=0, return_counts=True)
    hx = '#%02x%02x%02x' % tuple(int(t) for t in v[c.argmax()])
    return hx, m['key'].get(hx, '')


# ---- geographic side -------------------------------------------------------------
def label_test(base, feats):
    """Where each label printed on the base map lands in a layer: its centre is
    carried by the shipped transform of the region it sits in, then matched to
    the layer polygon containing it. Returns [(printed, seat it lands in)];
    the seat is '' for a gap and None where the box has no recovered transform."""
    from shapely import STRtree
    geoms = [(f['properties']['na'], shape(f['geometry']).buffer(0)) for f in feats]
    tree = STRtree([g for _, g in geoms])
    out = []
    for w in base['words']:
        r = base['regions'][w['rid']] if w['rid'] >= 0 else None
        f = base['warps'].get(r['cid']) if r is not None else None
        if f is None:
            out.append((w['na'], None))
            continue
        pt = Point(*f(np.array([w['cx'], w['cy']]))[0])
        hit = [geoms[i][0] for i in tree.query(pt, predicate='within')]
        out.append((w['na'], hit[0] if hit else ''))
    return out


def label_score(hits):
    c = collections.Counter('no transform' if h is None else 'own seat' if h == na else
                            'gap' if h == '' else 'another seat' for na, h in hits)
    wrong = sorted([(na, h) for na, h in hits if h and h != na], key=lambda t: (int(t[0][3:]), int(t[1][3:])))
    return dict(c), wrong


def district_layer():
    d23 = {}
    for f in json.load(open('data/digitised/districts_2023.geojson'))['features']:
        n = f['properties']['district']
        g = make_valid(shape(f['geometry']))
        d23[n] = unary_union([d23[n], g]) if n in d23 else g
    d15 = brg.load_districts()

    def get(name):
        names = D23.get(name, [name])
        gs = [d23[n] for n in names if n in d23]
        return unary_union(gs) if gs else d15.get(name)
    return get


# ---- the audit -------------------------------------------------------------------
def load_maps():
    maps = {y: audit_map(y) for y in YEARS}
    return maps, offsets(maps)


def source_region(maps, off, f):
    """The base-map region a merged feature was traced from: on the feature's own
    map, the region whose traced outline matches it (IoU >= 0.9), then moved to
    the base map by that map's offset. None for a Voronoi fallback."""
    src = f['properties']['src']
    if not src.startswith('commons-'):
        return None
    y = src.split('-')[1]
    m, g = maps[y], shape(f['geometry']).buffer(0)
    box = src.endswith('-inset')
    best = None
    for r in m['regions']:
        if r['ll'] is None or r['main'] == box or not g.contains(Point(*r['ll'])):
            continue
        t = trace_region(m, r)
        if t is not None:
            v = iou(t, g)
            if v >= 0.9 and (best is None or v > best[0]):
                best = (v, r)
    if best is None:
        # the two one-seat boxes (Peshawar, Rawalpindi) have no recovered
        # transform; their seat is the box's only labelled region
        cand = [r for r in m['regions'] if not r['main'] and r['cid'] not in m['warps']
                and f['properties']['na'] in r['exact']]
        best = (None, max(cand, key=lambda r: r['area'])) if cand else None
    if best is None:
        return None
    r = best[1]
    if y == BASE_YEAR:
        return r
    dx, dy = off[y]['offset']
    x, yy = deep_point(r) - (dx, dy)
    k = maps[BASE_YEAR]['rid'][int(yy), int(x)]
    return maps[BASE_YEAR]['regions'][k] if k >= 0 else None


def audit(maps, off, merged, layer):
    """Per-seat table for one merged set and the layer tessellated from it."""
    base = maps[BASE_YEAR]
    XW = json.load(open(XWALK))['base']
    dget = district_layer()
    dcache = {}

    def seat_area(na):
        if na not in dcache:
            gs = [g for g in (dget(d) for d in XW.get(na, [])) if g is not None]
            dcache[na] = unary_union(gs) if gs else None
        return dcache[na]

    src_region = {f['properties']['na']: source_region(maps, off, f) for f in merged}
    drawn_as = collections.defaultdict(list)
    for na, r in src_region.items():
        if r is not None:
            drawn_as[r['key']].append(na)
    printed_at = collections.defaultdict(list)
    for r in base['regions']:
        for na in set(r['exact']):
            printed_at[na].append(r)
    props = {f['properties']['na']: f['properties'] for f in layer}

    def party(y, r):
        return fill_on(maps[y], r, off[y]['offset'])[1]

    def winner(y, na):
        return maps[y]['res'].get(na, {}).get('party', '')

    def district_share(r, na):
        """Share of base region r, placed by the shipped transform, inside na's districts."""
        g_area, g = seat_area(na), trace_region(base, r)
        if g_area is None or g is None or not g.area:
            return ''
        return round(g.intersection(g_area).area / g.area, 2)

    rows = []
    for n in range(1, 208):
        na = f'NA-{n}'
        p, r = props[na], src_region.get(na)
        row = {'na': na,
               'names_1990_93_97': ' / '.join(dict.fromkeys(maps[y]['res'].get(na, {}).get('name', '')
                                                             for y in YEARS)),
               'src': p['src'], 'confidence': p.get('confidence', ''),
               'source_region': '', 'part': '', 'tesseract_read': '', 'printed_in_region': '',
               'verdict': '', 'region_party_1990_93_97': '', 'winner_1990_93_97': '',
               'printed_winner_1990_93_97': '', 'colour_years_for_printed': '',
               'colour_years_for_layer': '', 'district_share_layer': '', 'district_share_printed': '',
               'printed_region_used_as': ' '.join('+'.join(drawn_as.get(t['key'], ['unused']))
                                                  for t in printed_at.get(na, [])) or 'not printed'}
        if r is None:
            row['verdict'] = 'Voronoi fallback'
            rows.append(row)
            continue
        printed = sorted(set(r['exact']), key=lambda s: int(s[3:]))
        z = next((t for t in printed if t != na), None)
        row.update(source_region=f'{BASE_YEAR}:{r["key"]}', part='main map' if r['main'] else 'city box',
                   printed_in_region=' '.join(printed),
                   verdict=('printed label agrees' if printed == [na] else
                            'region carries no label' if not printed else f'region is printed {z}'))
        row['tesseract_read'] = r['ocr'] or ''
        parties = [party(y, r) for y in YEARS]
        row['region_party_1990_93_97'] = ' / '.join(x or '?' for x in parties)
        row['winner_1990_93_97'] = ' / '.join(winner(y, na) or '?' for y in YEARS)
        fp = fl = 0
        if z:
            row['printed_winner_1990_93_97'] = ' / '.join(winner(y, z) or '?' for y in YEARS)
            for y, pt in zip(YEARS, parties):
                wx, wz = winner(y, na), winner(y, z)
                if pt and wx and wz and wx != wz:
                    fp += pt == wz
                    fl += pt == wx
            row['colour_years_for_printed'], row['colour_years_for_layer'] = fp, fl
            row['district_share_printed'] = district_share(r, z)
        row['district_share_layer'] = district_share(r, na)
        rows.append(row)

    # every seat: is its source region drawn in the colour of its own recorded winner?
    colour = {}
    for y in YEARS:
        c = collections.Counter()
        for na, r in src_region.items():
            w = winner(y, na)
            pt = party(y, r) if r is not None else ''
            c['no source region' if r is None else 'no result' if not w else
              'colour not in key' if not pt else 'agrees' if pt == w else 'disagrees'] += 1
        colour[y] = dict(c)
    hits = label_test(base, layer)
    lt, lt_wrong = label_score(hits)
    verdicts = collections.Counter('region is printed another number' if r['verdict'].startswith('region is')
                                   else r['verdict'] for r in rows)
    summary = {
        'offsets_from_1993': off,
        'labels_read': {y: len(m['words']) for y, m in maps.items()},
        'label_attachment_below_75pct': sorted({(w['na'], round(w['share'], 2)) for w in base['words']
                                                if w['share'] < 0.75}),
        'traced_features_linked': {y: f"{sum(1 for r in m['regions'] if r['link'])}/{len(m['traced'])}"
                                   for y, m in maps.items()},
        'verdicts': dict(verdicts),
        'disagreements': [r['na'] for r in rows if r['verdict'].startswith('region')],
        'fallbacks': [r['na'] for r in rows if r['verdict'] == 'Voronoi fallback'],
        'region_colour_vs_own_winner': colour,
        'printed_labels_in_layer': lt,
        'printed_labels_in_another_seat': [list(t) for t in lt_wrong],
    }
    return {'rows': rows, 'summary': summary, 'src_region': src_region, 'printed_at': printed_at,
            'drawn_as': drawn_as, 'layer': layer, 'maps': maps, 'off': off}


def write(res, out):
    os.makedirs(out, exist_ok=True)
    rows = res['rows']
    with open(f'{out}/seats_207.csv', 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    json.dump(res['summary'], open(f'{out}/summary.json', 'w'), indent=1)


def write_regions(maps, out):
    os.makedirs(out, exist_ok=True)
    for y in YEARS:
        m = maps[y]
        with open(f'{out}/regions_{y}.csv', 'w', newline='', encoding='utf-8') as fh:
            wr = csv.writer(fh)
            wr.writerow(['region', 'part', 'area_px', 'fill', 'fill_party', 'printed', 'tesseract',
                         'in_committed_trace_as', 'lon', 'lat'])
            for r in sorted(m['regions'], key=lambda r: -r['area']):
                if not (r['hex'] in m['key'] or r['exact'] or r['link']):
                    continue
                wr.writerow([r['key'], 'main' if r['main'] else 'box', r['area'], r['hex'],
                             m['key'].get(r['hex'], ''), ' '.join(sorted(set(r['exact']))),
                             r['ocr'] or '', r['link'] or '',
                             '' if r['ll'] is None else round(float(r['ll'][0]), 4),
                             '' if r['ll'] is None else round(float(r['ll'][1]), 4)])


def clusters(rows):
    """Disputed seats that share regions, grouped: a seat sits on the region
    printed with another number, so the two go together, and so on along the
    chain. Fallbacks whose printed region another seat took join the group."""
    adj = collections.defaultdict(set)
    for r in rows:
        if not (r['verdict'].startswith('region') or r['verdict'] == 'Voronoi fallback'):
            continue
        x = r['na']
        adj[x]
        for z in r['printed_in_region'].split():
            adj[x].add(z); adj[z].add(x)
        for w in r['printed_region_used_as'].replace('+', ' ').split():
            if w.startswith('NA-') and w != x:
                adj[x].add(w); adj[w].add(x)
    seen, out = set(), []
    for s in sorted(adj, key=lambda k: int(k[3:])):
        if s in seen:
            continue
        stack, comp = [s], set()
        while stack:
            v = stack.pop()
            if v not in comp:
                comp.add(v)
                stack += adj[v] - comp
        seen |= comp
        out.append(sorted(comp, key=lambda k: int(k[3:])))
    return out


def draw_clusters(res, out, after=None):
    """One figure per group: the Commons map with the regions involved, the
    audited layer, and (with after=) a second layer for comparison."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly
    maps, rows, printed_at, drawn = res['maps'], res['rows'], res['printed_at'], res['drawn_as']
    base = maps[BASE_YEAR]
    a = base['a']
    os.makedirs(out, exist_ok=True)
    byna = {r['na']: r for r in rows}
    layers = [('Shipped layer' if after else 'Layer', res['layer'])] + ([('After this fix', after)] if after else [])
    written = []
    for comp in clusters(rows):
        regs = {}
        for na in comp:
            r = res['src_region'].get(na)
            if r is not None:
                regs[r['key']] = r
            for t in printed_at.get(na, []):
                regs[t['key']] = t
        # city boxes and main map can be far apart: draw the main-map part only
        # when the group has one, plus a second map panel for a box
        parts = collections.defaultdict(dict)
        for k, r in regs.items():
            parts['main' if r['main'] else r['cid']][k] = r
        panels = list(parts.items())
        n = len(panels) + len(layers)
        fig, axes = plt.subplots(1, n, figsize=(5.6 * n, 6.4))
        for ax, (part, rr) in zip(axes, panels):
            bx = np.array([r['bbox'] for r in rr.values()])
            x0, y0 = max(0, bx[:, 0].min() - 30), max(0, bx[:, 1].min() - 30)
            x1, y1 = min(a.shape[1], bx[:, 2].max() + 30), min(a.shape[0], bx[:, 3].max() + 30)
            ax.imshow(a[y0:y1, x0:x1].astype(np.uint8), extent=(x0, x1, y1, y0), interpolation='nearest')
            for r in rr.values():
                pp = pixel_polygon(r)
                for g in (pp.geoms if pp.geom_type == 'MultiPolygon' else [pp]):
                    ax.add_patch(MPoly(np.asarray(g.exterior.coords), fill=False, ec='red', lw=1.4))
                tag = drawn.get(r['key'])
                # tag below the printed label, so the label stays readable
                ys, xs = np.nonzero(r['comp'])
                ws = r['words']
                px = (np.mean([w['cx'] for w in ws]), max(w['bbox'][3] for w in ws) + 10) if ws else \
                    tuple(deep_point(r))
                ax.annotate(('drawn as ' + '+'.join(tag)) if tag else 'not drawn', px, ha='center', va='top',
                            fontsize=7.5, color='white',
                            bbox=dict(boxstyle='round,pad=0.15', fc='#c62828' if tag else '#616161',
                                      ec='none', alpha=0.85))
            ax.set_xlim(x0, x1); ax.set_ylim(y1, y0)
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f'Commons {BASE_YEAR} map{"" if part == "main" else ", city box"}: '
                         'printed labels; red = regions involved', fontsize=8.5)
        # one extent for every layer panel: the group's seats in all layers,
        # plus where its printed labels fall
        lgeoms = [{f['properties']['na']: shape(f['geometry']) for f in feats} for _, feats in layers]
        pts = [Point(*base['warps'][t['cid']](np.array([w['cx'], w['cy']]))[0])
               for na in comp for t in printed_at.get(na, []) if t['cid'] in base['warps']
               for w in t['words'] if w['na'] == na]
        focus = unary_union([g[na] for g in lgeoms for na in comp if na in g] + pts)
        minx, miny, maxx, maxy = focus.buffer(0.12).bounds
        for ax, (title, feats), geoms in zip(axes[len(panels):], layers, lgeoms):
            for na, g in geoms.items():
                if not g.intersects(focus.buffer(0.4)):
                    continue
                inc = na in comp
                for q in (g.geoms if g.geom_type == 'MultiPolygon' else [g]):
                    ax.add_patch(MPoly(np.asarray(q.exterior.coords), fc='#f6d0cc' if inc else '#eeeeee',
                                       ec='#666666', lw=0.6))
                c = g.representative_point()
                if minx < c.x < maxx and miny < c.y < maxy:
                    ax.text(c.x, c.y, na, fontsize=7.5 if inc else 6, ha='center', va='center',
                            color='black' if inc else '#8a8a8a', weight='bold' if inc else 'normal')
            for na in comp:
                for t in printed_at.get(na, []):
                    w_ = base['warps'].get(t['cid'])
                    for wd in (t['words'] if w_ else []):
                        if wd['na'] == na:
                            ll = w_(np.array([wd['cx'], wd['cy']]))[0]
                            ax.plot(*ll, marker='o', ms=3.5, color='#1565c0')
                            ax.annotate(f'printed {na}', ll, xytext=(0, 5), textcoords='offset points',
                                        ha='center', fontsize=6.5, color='#1565c0')
            ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy)
            ax.set_aspect(1 / np.cos(np.radians((miny + maxy) / 2)))
            ax.tick_params(labelsize=6.5)
            ax.set_title(f'{title} (seat numbers in black);\nblue: printed labels placed by the shipped transform',
                         fontsize=8.5)
        lines = []
        for na in comp:
            r = byna[na]
            if r['verdict'].startswith('region is'):
                z = r['printed_in_region']
                lines.append(f"{na} was drawn on the region printed {z}. Region colour 1990/93/97: "
                             f"{r['region_party_1990_93_97']}; winners {na}: {r['winner_1990_93_97']}, "
                             f"{z}: {r['printed_winner_1990_93_97']}.")
            elif r['verdict'] == 'region carries no label':
                lines.append(f"{na} was drawn on a region with no label (grey placeholder).")
            elif r['verdict'] == 'Voronoi fallback':
                lines.append(f"{na} was a Voronoi fallback; its printed region was "
                             f"{'drawn as ' + r['printed_region_used_as'] if r['printed_region_used_as'] not in ('unused', 'not printed') else 'not used'}.")
        fig.text(0.008, 0.008, '\n'.join(lines) + '\nMap: Saad Ali Khan Pakistan, Wikimedia Commons, CC BY-SA 4.0.',
                 fontsize=7, va='bottom')
        fig.subplots_adjust(bottom=0.05 + 0.03 * len(lines), top=0.9, left=0.01, right=0.99, wspace=0.1)
        name = f'{out}/NA-' + '_'.join(k[3:] for k in comp) + '.png'
        fig.savefig(name, dpi=110)
        plt.close(fig)
        written.append(name)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--merged', default=MERGED, help='merged trace (default: %(default)s)')
    ap.add_argument('--layer', default=LAYER, help='layer tessellated from it (default: %(default)s)')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--crops', action='store_true', help='draw one figure per group of disputed seats')
    ap.add_argument('--compare', help='a second layer to draw beside the audited one in the figures')
    args = ap.parse_args()
    maps, off = load_maps()
    res = audit(maps, off, json.load(open(args.merged))['features'], json.load(open(args.layer))['features'])
    write(res, args.out)
    write_regions(maps, args.out)
    s = res['summary']
    print(json.dumps({k: s[k] for k in ('labels_read', 'traced_features_linked', 'verdicts',
                                        'region_colour_vs_own_winner', 'printed_labels_in_layer')}, indent=1))
    for r in res['rows']:
        if r['na'] in s['disagreements']:
            print(f"{r['na']:7} {r['verdict']:24} colour years printed/layer "
                  f"{r['colour_years_for_printed']}/{r['colour_years_for_layer']} | district share "
                  f"{r['district_share_layer']} vs printed {r['district_share_printed']} | "
                  f"region printed {r['na']} drawn as {r['printed_region_used_as']}")
    if args.crops:
        after = json.load(open(args.compare))['features'] if args.compare else None
        for name in draw_clusters(res, f'{args.out}/crops', after):
            print('wrote', name)


if __name__ == '__main__':
    main()
