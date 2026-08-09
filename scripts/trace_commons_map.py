#!/usr/bin/env python3
"""
Trace true constituency polygons from a labelled Commons election map.

Pipeline (uses read_labelled_map + georef_map + georef_refine):
  1. segment the map into flat-filled regions; OCR the NA-xx label in each
  2. georeference the MAIN map to lon/lat (affine -> quadratic warp) against the
     2002-constituency union
  3. the Karachi inset is a separate box at its own scale, fitted separately to
     the union of the 2002 Karachi-district constituencies
  4. trace each region's contour, push it through the right warp -> polygon

Writes data/wip/trace/na_traced_<year>.geojson (labelled seats only; gaps and
un-inset seats are reported for follow-up).

    python3 scripts/trace_commons_map.py 1997
"""
import sys, json, collections
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape, Polygon, MultiPolygon, mapping, Point
from shapely.ops import unary_union
sys.path.insert(0, 'scripts')
import read_labelled_map as RL
import georef_map as G
import georef_refine as GR

KARACHI_DISTRICTS = {'Karachi Central', 'Karachi East', 'Karachi South', 'Karachi West',
                     'Karachi Malir', 'Malir', 'Karachi'}

def karachi_union():
    """Union of the 2002 constituencies that sit in Karachi (target for the inset)."""
    feats = json.load(open(G.C2002, encoding='utf-8'))['features']
    ks = [shape(f['geometry']).buffer(0) for f in feats
          if 'karachi' in ((f['properties'].get('dist') or '') + ' ' +
                           (f['properties'].get('prov') or '')).lower()]
    return unary_union(ks) if ks else None

def contours_ll(comp, ox, oy, warp):
    """External contours of a region mask -> list of lon/lat rings."""
    m = comp.astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < 25:
            continue
        c = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2).astype(float)
        if len(c) < 4:
            continue
        c[:, 0] += ox; c[:, 1] += oy
        out.append(warp(c))
    return out

def polygonise(rings):
    polys = []
    for ll in rings:
        try:
            p = Polygon(ll).buffer(0)
            if p.is_valid and p.area > 0:
                polys.append(p)
        except Exception:
            pass
    if not polys:
        return None
    return unary_union(polys)

def main(year):
    path = f'data/sources/Pakistan_General_election_{year}.png'
    print(f'== tracing {year} ==')
    im, a, ink, regions = RL.segment(path)
    a_int = a.astype(int)
    regions.sort(key=lambda r: -r['area'])

    # main-map georeference
    mask, comps, lab, _ = G.party_mask(path)
    geom = G.true_geom()
    affine, iou = G.fit(mask, geom, verbose=False)
    coef, iou2, T = GR.refine(mask, geom, affine, deg=2, step=4)
    warp_main = lambda pts: GR.forward(pts, coef, 2)
    print(f'   main georef IoU {iou2:.3f}')

    # inset box = 2nd largest filled component (the Karachi rectangle)
    inset_bbox = None
    if len(comps) > 1:
        _, cid = comps[1]
        ys, xs = np.where(lab == cid)
        inset_bbox = (xs.min(), ys.min(), xs.max(), ys.max())
        print(f'   inset box at x[{inset_bbox[0]}..{inset_bbox[2]}] y[{inset_bbox[1]}..{inset_bbox[3]}]')

    def in_inset(r):
        if not inset_bbox: return False
        cx, cy = (r['bbox'][0] + r['bbox'][2]) / 2, (r['bbox'][1] + r['bbox'][3]) / 2
        x0, y0, x1, y1 = inset_bbox
        return x0 <= cx <= x1 and y0 <= cy <= y1

    # label every region, split into main vs inset
    labelled = {}
    for r in regions:
        na = RL.ocr_region(a_int, r)
        if na is None:
            continue
        k = f'NA-{na}'
        r['inset'] = in_inset(r)
        if k not in labelled or r['area'] > labelled[k]['area']:
            labelled[k] = r
    main_seats = {k: r for k, r in labelled.items() if not r['inset']}
    inset_seats = {k: r for k, r in labelled.items() if r['inset']}
    print(f'   labelled: {len(labelled)}  (main {len(main_seats)}, inset {len(inset_seats)})')

    # fit the inset separately: its regions -> Karachi union
    warp_inset = None
    if inset_seats:
        sub = np.zeros(mask.shape, bool)
        for r in inset_seats.values():
            x0, y0, x1, y1 = r['bbox']
            sub[y0:y1, x0:x1] |= r['comp']
        sub = ndimage.binary_fill_holes(ndimage.binary_closing(sub, np.ones((5, 5))))
        kar = karachi_union()
        if kar is not None and sub.sum() > 500:
            aff_i, io_i = G.fit(sub, kar, verbose=False)
            warp_inset = lambda pts: GR.forward(pts, np.vstack([[aff_i[2], aff_i[5]],
                                       [aff_i[0], aff_i[3]], [aff_i[1], aff_i[4]]]), 1)
            print(f'   inset georef IoU {io_i:.3f} against Karachi union')

    feats, skipped = [], []
    for k, r in labelled.items():
        warp = warp_inset if r['inset'] else warp_main
        if warp is None:
            skipped.append(k); continue
        x0, y0 = r['bbox'][0], r['bbox'][1]
        g = polygonise(contours_ll(r['comp'], x0, y0, warp))
        if g is None or g.is_empty:
            skipped.append(k); continue
        feats.append({'type': 'Feature',
                      'properties': {'na': k, 'src': f'commons-{year}',
                                     'inset': bool(r['inset']),
                                     'hex': '#%02x%02x%02x' % tuple(int(v) for v in r['fill'])},
                      'geometry': mapping(g)})

    nums = sorted(int(f['properties']['na'].split('-')[1]) for f in feats)
    gaps = [n for n in range(1, 208) if n not in nums]
    out = f'data/wip/trace/na_traced_{year}.geojson'
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w'))
    print(f'   traced {len(feats)} seats -> {out}')
    print(f'   missing {len(gaps)}: {gaps}')
    return out, feats

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1997')
