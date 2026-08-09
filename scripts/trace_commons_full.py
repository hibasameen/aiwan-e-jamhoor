#!/usr/bin/env python3
"""
Full trace of a labelled Commons election map: main map + EVERY inset box,
label gating, and district-elimination gap fill.

Improvements over trace_commons_map.py:
  * all land components are found; any box holding >=2 regions or >=1 label is an
    inset and is fitted (affine) to the union of the districts of ITS OWN seats
    (legend swatches hold one unlabelled region each, so they are excluded)
  * OCR labels are gated: a label whose region lands >60 km from its own
    district is discarded (catches misreads)
  * unlabelled regions are assigned by elimination: warp the region's centroid,
    find its district, and if exactly one of that district's seats is still
    unassigned, it's a match (confidence normal). If several seats of one
    district are missing, regions and seat numbers are paired in numbering order
    (N->S, W->E) and marked confidence:'low'
  * OCR results are cached (data/wip/trace/labels_<year>.json) so re-runs are fast

Output: data/wip/trace/na_traced2_<year>.geojson

    python3 scripts/trace_commons_full.py 1997
"""
import sys, os, json, collections
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import Polygon, Point, MultiPolygon, mapping
from shapely.ops import unary_union
sys.path.insert(0, 'scripts')
import read_labelled_map as RL
import georef_map as G
import georef_refine as GR
import build_reconstructed_geometry as brg

WIP = 'data/wip/trace'
KM = 105.0                      # deg -> km, mid latitudes

def load_xwalk(year):
    """Seat->district crosswalk in the MAP numbering (1988-1997 share it).
    Per-year variants handle renames like Narowal / Malir-cum. Built by
    build_map_numbering.py from the 1988 scrape + embedded RESULTS names."""
    xw = json.load(open('data/wip/trace/xwalk_207map.json'))
    return xw.get(year, xw['base'])

def land_components(a):
    lum = a.sum(2)
    m = ndimage.binary_fill_holes(ndimage.binary_closing(lum >= 200, np.ones((9, 9))))
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return lab, sizes

def comp_of(r, lab):
    x0, y0, x1, y1 = r['bbox']
    sub = lab[y0:y1, x0:x1][r['comp']]
    sub = sub[sub > 0]
    if not len(sub): return 0
    v, c = np.unique(sub, return_counts=True)
    return int(v[c.argmax()])

def contours_ll(comp, ox, oy, warp):
    m = comp.astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < 25: continue
        c = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2).astype(float)
        if len(c) < 4: continue
        c[:, 0] += ox; c[:, 1] += oy
        out.append(warp(c))
    return out

def polygonise(rings):
    polys = []
    for ll in rings:
        try:
            p = Polygon(ll).buffer(0)
            if p.is_valid and p.area > 0: polys.append(p)
        except Exception: pass
    return unary_union(polys) if polys else None

def affine_warp(params):
    a, b, c, d, e, f = params
    return lambda pts: np.column_stack([a*pts[:,0]+b*pts[:,1]+c, d*pts[:,0]+e*pts[:,1]+f])

def main(year):
    path = f'data/sources/Pakistan_General_election_{year}.png'
    print(f'== full trace {year} ==')
    XW = load_xwalk(year)
    DIST = brg.load_districts()
    dist_items = list(DIST.items())

    im, a, ink, regions = RL.segment(path)
    a_int = a.astype(int)

    # ---- OCR with cache
    os.makedirs(WIP, exist_ok=True)
    cpath = f'{WIP}/labels_{year}.json'
    cache = json.load(open(cpath)) if os.path.exists(cpath) else {}
    hit = 0
    for r in regions:
        key = ','.join(map(str, r['bbox'])) + ':' + str(r['area'])
        if key in cache:
            r['na'] = cache[key]; hit += 1
        else:
            n = RL.ocr_region(a_int, r)
            r['na'] = f'NA-{n}' if n else None
            cache[key] = r['na']
    json.dump(cache, open(cpath, 'w'))
    print(f'   OCR: {sum(1 for r in regions if r["na"])} labelled of {len(regions)} regions (cache hits {hit})')

    # ---- components
    lab, sizes = land_components(a_int)
    for r in regions:
        r['cid'] = comp_of(r, lab)
    main_cid = int(np.argmax(sizes)) + 1
    by_comp = collections.defaultdict(list)
    for r in regions:
        by_comp[r['cid']].append(r)

    # ---- main warp (cache npy)
    afp, plp = f'{WIP}/ge{year}_affine.npy', f'{WIP}/ge{year}_poly.npy'
    mask, comps, _, _ = G.party_mask(path)
    geom = G.true_geom()
    if os.path.exists(plp):
        coef = np.load(plp)
    else:
        affine, iou = G.fit(mask, geom, verbose=False)
        np.save(afp, affine)
        coef, iou2, _ = GR.refine(mask, geom, affine, deg=2, step=4)
        np.save(plp, coef)
        print(f'   main georef IoU {iou2:.3f}')
    warps = {main_cid: (lambda pts: GR.forward(pts, coef, 2))}

    # ---- inset warps
    inset_cids = []
    for cid, rs in by_comp.items():
        if cid in (0, main_cid): continue
        labs = [r for r in rs if r['na'] and r['na'] in XW]
        if len(rs) < 2 and not labs: continue          # legend swatch / noise
        if not labs: continue
        # majority geographic cluster: OCR misreads inside an inset would pull in
        # far-away districts and wreck the fit — keep only districts within
        # 150 km of the modal district, and void the outlier labels
        freq = collections.Counter(d for r in labs for d in XW[r['na']])
        d0 = freq.most_common(1)[0][0]
        cluster = {d for d in freq if DIST[d].distance(DIST[d0]) * KM < 150}
        for r in labs:
            if not any(d in cluster for d in XW[r['na']]):
                r['na'] = None
        labs = [r for r in rs if r['na'] and r['na'] in XW]
        if not labs: continue
        ds = sorted(cluster)
        target = unary_union([DIST[d] for d in ds])
        sub = np.zeros(mask.shape, bool)
        for r in rs:
            x0, y0, x1, y1 = r['bbox']
            sub[y0:y1, x0:x1] |= r['comp']
        sub = ndimage.binary_fill_holes(ndimage.binary_closing(sub, np.ones((5, 5))))
        try:
            aff, iou = G.fit(sub, target, verbose=False)
        except Exception as e:
            print(f'   inset comp {cid}: fit error {e}'); continue
        if iou < 0.22:
            print(f'   inset comp {cid}: fit too poor (IoU {iou:.2f}) — skipped'); continue
        warps[cid] = affine_warp(aff)
        inset_cids.append(cid)
        print(f'   inset comp {cid}: {len(labs)} labels, districts {ds[:4]}{"…" if len(ds)>4 else ""}, IoU {iou:.2f}')

    def centre_ll(r):
        w = warps.get(r['cid'])
        if w is None: return None
        x0, y0, x1, y1 = r['bbox']
        return w(np.array([[(x0+x1)/2.0, (y0+y1)/2.0]], float))[0]

    # ---- gate labels (main map only; inset labels vouched by the inset fit)
    dropped = 0
    for r in regions:
        if not r['na'] or r['na'] not in XW: continue
        ll = centre_ll(r)
        if ll is None: r['na'] = None; continue
        dmin = min(DIST[d].distance(Point(*ll)) for d in XW[r['na']] if d in DIST) * KM
        if r['cid'] == main_cid and dmin > 60:
            r['na'] = None; dropped += 1
    print(f'   gated out {dropped} misread labels')

    # keep the largest region per NA
    best = {}
    for r in regions:
        if r['na'] and r['na'] in XW and r['cid'] in warps:
            if r['na'] not in best or r['area'] > best[r['na']]['area']:
                best[r['na']] = r
    taken = set(best)

    # ---- elimination fill
    seats_by_d = collections.defaultdict(set)
    for na, ds in XW.items():
        for d in ds: seats_by_d[d].add(na)
    cand_regions = [r for r in regions if not r['na'] and r['cid'] in warps and r['area'] > 400]
    for r in cand_regions:
        r['ll'] = centre_ll(r)
    changed, rounds = True, 0
    filled_hi = 0
    while changed and rounds < 6:
        changed = False; rounds += 1
        for r in sorted(cand_regions, key=lambda r: -r['area']):
            if r['na'] or r['ll'] is None: continue
            p = Point(*r['ll'])
            here = [d for d, g in dist_items if g.contains(p)]
            if not here:
                d, g = min(dist_items, key=lambda kv: kv[1].distance(p))
                if g.distance(p) * KM > 40: continue
                here = [d]
            cands = set()
            for d in here: cands |= (seats_by_d.get(d, set()) - taken)
            if len(cands) == 1:
                r['na'] = cands.pop(); r['conf'] = 'ok'
                best[r['na']] = r; taken.add(r['na']); filled_hi += 1; changed = True
    print(f'   elimination filled {filled_hi} (unique-district)')

    # low-confidence pairing: several missing seats in one district
    missing = collections.defaultdict(list)     # district -> [na,...] unassigned
    for na, ds in XW.items():
        if na in taken: continue
        for d in ds: missing[d].append(na)
    filled_lo = 0
    for d, nas in missing.items():
        rs = [r for r in cand_regions if not r['na'] and r['ll'] is not None
              and DIST[d].distance(Point(*r['ll'])) * KM < 15]
        nas = sorted(set(nas) - taken, key=lambda k: int(k.split('-')[1]))
        rs = [r for r in rs if r not in [best.get(n) for n in taken]]
        if not nas or len(rs) < len(nas): continue
        rs = sorted(rs, key=lambda r: -r['area'])[:len(nas)]
        rs = sorted(rs, key=lambda r: (-r['ll'][1], r['ll'][0]))   # N->S, W->E
        for na, r in zip(nas, rs):
            if na in taken or r['na']: continue
            r['na'] = na; r['conf'] = 'low'
            best[na] = r; taken.add(na); filled_lo += 1
    print(f'   low-confidence pairing filled {filled_lo}')

    # ---- build features
    feats = []
    for na, r in best.items():
        w = warps[r['cid']]
        x0, y0 = r['bbox'][0], r['bbox'][1]
        g = polygonise(contours_ll(r['comp'], x0, y0, w))
        if g is None or g.is_empty: continue
        pr = {'na': na, 'src': f'commons-{year}', 'inset': r['cid'] != main_cid,
              'hex': '#%02x%02x%02x' % tuple(int(v) for v in r['fill'])}
        if r.get('conf') == 'low': pr['confidence'] = 'low'
        feats.append({'type': 'Feature', 'properties': pr, 'geometry': mapping(g)})

    nums = sorted(int(f['properties']['na'].split('-')[1]) for f in feats)
    gaps = [n for n in range(1, 208) if n not in nums]
    out = f'{WIP}/na_traced2_{year}.geojson'
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w'))
    print(f'   TOTAL {len(feats)} seats -> {out}')
    print(f'   still missing {len(gaps)}: {gaps}')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1997')
