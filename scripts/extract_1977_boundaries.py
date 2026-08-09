#!/usr/bin/env python3
"""
Extract true 1977-delimitation constituency boundaries from a labelled map.

  main map      georeferenced by fitting its party-coloured area to the union of
                the 2002 constituencies (same territory, no control points)
  inset boxes   each fitted separately, against the union of the districts its
                own seats belong to
  labels        OCR, then gated on whether the region actually lands in the
                district its number implies, then completed by elimination
  polygons      contours traced per region, simplified, pushed through the warp
"""
import json, io, re, sys, collections
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape, Polygon, Point, MultiPolygon, mapping
from shapely.ops import unary_union
import georef, georef2
from segment_map import segment, ocr_region

ADM2 = '/mnt/user-data/uploads/Aiwan-e-Jamhoor/data/cod_PAK_ADM2.geojson'
ALIAS = {'battagram':'batagram','bunair':'buner','gawadar':'gwadar','labdela':'lasbela',
 'thar':'tharparkar','turbat':'kech','nawabshah':'shaheedbenazirabad','layyah':'leiah',
 'bolan':'kachhi','deraismailkhan':'dikhan','abbbottabad':'abbottabad','attok':'attock',
 'muzaffaragarh':'muzaffargarh','malakandprotectedarea':'malakand','jhallmagsi':'jhalmagsi',
 'naushferoz':'naushahroferoze','naushroferoz':'naushahroferoze','karachicentral':'centralkarachi',
 'karachieast':'eastkarachi','karachisouth':'southkarachi','karachiwest':'westkarachi',
 'malir':'malirkarachi','dir':'lowerdir','kohistan':'kohistanlower','chitral':'chitrallower'}
norm = lambda s: re.sub(r'[^a-z]', '', s.lower())

def districts_of(name, DN):
    t = re.sub(r'\s*[-–]?\s*(\d+|[IVXL]+)$', '', name).strip()
    out = []
    for p in re.split(r'(?i)\s*-\s*cum\s*-\s*', t):
        k = norm(p.strip()); k = ALIAS.get(k, k)
        if k in DN: out.append(DN[k])
    return out

def land_components(path):
    """All drawn land, split into main map / insets / legend swatches."""
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    lum = a.sum(2)
    m = (lum >= 200)
    m = ndimage.binary_closing(m, np.ones((9, 9)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    comps = []
    for k in order:
        if sizes[k] < 3000: break
        sl = ndimage.find_objects(lab)[k]
        comps.append({'id': int(k) + 1, 'px': int(sizes[k]), 'slice': sl,
                      'bbox': (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)})
    return lab, comps

def which_comp(r, lab):
    x0, y0, x1, y1 = r['bbox']
    sub = lab[y0:y1, x0:x1][r['comp']]
    sub = sub[sub > 0]
    if not len(sub): return 0
    v, c = np.unique(sub, return_counts=True)
    return int(v[c.argmax()])

def fit_region_group(mask, target, label=''):
    aff, iou1 = georef.fit(mask, target, verbose=False)
    coef, iou2, _ = georef2.refine(mask, target, aff, deg=2, step=2)
    print(f'      {label}: IoU {iou1:.3f} -> {iou2:.3f}')
    return coef

def main(path, year, expect=207, outdir='/home/claude'):
    print(f'=== {path.split("/")[-1]}  ({year}) ===')
    res = json.load(open('/home/claude/new_years.json'))[year]
    adm = json.load(io.open(ADM2, encoding='utf-8'))['features']
    D = {f['properties']['shapeName']: shape(f['geometry']).buffer(0) for f in adm}
    DN = {norm(k): k for k in D}

    im, a, ink, regions = segment(path)
    a_int = a.astype(int)
    lab, comps = land_components(path)
    main_id = comps[0]['id']
    print(f'  regions {len(regions)} | land components {len(comps)} | main = {comps[0]["px"]:,} px')

    for r in regions:
        r['comp_id'] = which_comp(r, lab)
        x0, y0, x1, y1 = r['bbox']
        r['cx'], r['cy'] = (x0 + x1) / 2, (y0 + y1) / 2

    # ---- OCR every region
    for r in regions:
        n = ocr_region(a_int, r)
        r['na'] = f'NA-{n}' if n else None
    got = sum(1 for r in regions if r['na'])
    print(f'  OCR read {got} of {len(regions)} regions')

    # ---- main-map transform
    mask, _, _, _ = georef.party_mask(path)
    target = georef.true_geom()
    print('  fitting transforms:')
    T = {main_id: fit_region_group(mask, target, 'main map')}

    # ---- inset transforms, from the districts their own labels imply
    for c in comps[1:]:
        cid = c['id']
        inside = [r for r in regions if r['comp_id'] == cid and r['na'] and r['na'] in res]
        if len(inside) < 3: continue
        ds = []
        for r in inside: ds += districts_of(res[r['na']]['name'], DN)
        ds = [D[d] for d in set(ds)]
        if not ds: continue
        sub = np.zeros_like(mask)
        for r in regions:
            if r['comp_id'] != cid: continue
            x0, y0, x1, y1 = r['bbox']
            sub[y0:y1, x0:x1] |= r['comp']
        sub = ndimage.binary_fill_holes(ndimage.binary_closing(sub, np.ones((5, 5))))
        try:
            T[cid] = fit_region_group(sub, unary_union(ds), f'inset {cid} ({len(inside)} seats)')
        except Exception as ex:
            print(f'      inset {cid}: fit failed ({ex})')

    # ---- reject labels whose region lands nowhere near its own district
    def centre_ll(r):
        c = T.get(r['comp_id'])
        if c is None: return None
        return georef2.forward(np.array([[r['cx'], r['cy']]], float), c, 2)[0]
    bad = 0
    for r in regions:
        if not r['na'] or r['na'] not in res: continue
        ll = centre_ll(r)
        if ll is None: r['na'] = None; continue
        ds = districts_of(res[r['na']]['name'], DN)
        if not ds: continue
        d = min(D[x].distance(Point(*ll)) for x in ds) * 105
        r['dist_km'] = d
        if d > 60: r['na'] = None; bad += 1
    print(f'  rejected {bad} labels that landed >60 km from their own district')

    # ---- complete by elimination: which district does an unlabelled region sit in?
    seats_by_d = collections.defaultdict(set)
    for na, v in res.items():
        for d in districts_of(v['name'], DN): seats_by_d[d].add(na)
    taken = {r['na'] for r in regions if r['na']}
    filled = 0
    for r in sorted([r for r in regions if not r['na']], key=lambda r: -r['area']):
        ll = centre_ll(r)
        if ll is None: continue
        p = Point(*ll)
        here = [d for d in D if D[d].contains(p)]
        if not here:
            here = sorted(D, key=lambda d: D[d].distance(p))[:1]
        cand = set()
        for d in here: cand |= (seats_by_d.get(d, set()) - taken)
        if len(cand) == 1:
            r['na'] = cand.pop(); taken.add(r['na']); filled += 1
    print(f'  filled {filled} more by elimination -> {len(taken)} of {expect} seats identified')

    # ---- trace contours and push them through the warp
    feats, skipped = [], 0
    byna = collections.defaultdict(list)
    for r in regions:
        if r['na']: byna[r['na']].append(r)
    for na, rs in byna.items():
        polys = []
        for r in rs:
            c = T.get(r['comp_id'])
            if c is None: continue
            x0, y0, x1, y1 = r['bbox']
            m = np.zeros((y1 - y0 + 4, x1 - x0 + 4), np.uint8)
            m[2:-2, 2:-2] = r['comp'].astype(np.uint8)
            cont, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for k in cont:
                if cv2.contourArea(k) < 30: continue
                k = cv2.approxPolyDP(k, 1.2, True).reshape(-1, 2).astype(float)
                if len(k) < 4: continue
                k[:, 0] += x0 - 2; k[:, 1] += y0 - 2
                ll = georef2.forward(k, c, 2)
                try:
                    p = Polygon(ll).buffer(0)
                    if p.is_valid and p.area > 0: polys.append(p)
                except Exception: pass
        if not polys: skipped += 1; continue
        g = unary_union(polys)
        feats.append({'type': 'Feature',
                      'properties': {'na': na, 'name': res.get(na, {}).get('name', ''),
                                     'src': 'commons-1977'},
                      'geometry': mapping(g)})
    print(f'  polygons built: {len(feats)} (skipped {skipped})')
    gj = {'type': 'FeatureCollection', 'features': feats}
    out = f'{outdir}/na_1977delim_{year}.geojson'
    json.dump(gj, open(out, 'w'), separators=(',', ':'))
    print(f'  wrote {out}  ({len(json.dumps(gj))/1e6:.2f} MB)')
    return gj

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 207)
