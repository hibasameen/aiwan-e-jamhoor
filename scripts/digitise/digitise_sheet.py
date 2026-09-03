#!/usr/bin/env python3
"""
Digitise one ECP delimitation map sheet (district revenue map with colour-coded
NA constituencies and a printed UTM grid) into true-boundary GeoJSON.

Proven on the 2018 Quetta sheet (Balochistan/s15.jpg): NA-264/265/266 with ~46 m/px
working resolution (12.6 m/px if run at full resolution).

Pipeline
--------
1. Downsample sheet to ~3000 px wide; convert to HSV.
2. Colour-segment constituency fills: moderately saturated bright pixels binned by
   hue ranges (per-sheet `classes` mapping hue-range -> NA number). Morphological
   close/open; drop components < max(1500 px, 5% of the class's largest) — this
   removes legend swatches and noise. For classes that match decorative chrome
   (e.g. yellow title bars), keep only components embedded in the union of the
   other fills (>50% inside its 41-px dilation).
3. Georeference via the printed UTM grid: detect vertical/horizontal grid lines as
   peaks of column/row sums of a "grayish thin line" mask (low saturation,
   140<V<235) inside the map frame; uniform spacing validates detection; anchor
   pixel positions to the grid values read from the sheet (labels like 230000 E /
   3360000 N). Pixel->E,N is then an axis-aligned affine.
   UTM zone: try 41/42/43N, keep the one whose transformed centre lands nearest
   the district's known centroid (districts_2015.geojson).
4. Trace each class's external contours, transform to lon/lat (pyproj), make_valid,
   union, simplify(0.0008 deg), write GeoJSON with na/district/src properties.

Per-sheet inputs (from a metadata table, vision-read once per sheet):
  district name; grid: {x_px0, x_val0, px_per_unit... or two anchors per axis};
  classes: [{na, hue_lo, hue_hi}, ...]  (embedded-only flag for chrome-colliding hues)

QA per sheet: overlay against districts_2015 outline; IoU is expected ~0.6-0.8
because the 2015 layer is much cruder than the revenue maps — check for *systematic
shift* (bad) vs *detail mismatch* (fine). Legend-swatch leakage shows up as tiny
far-flung parts — the 5%-of-largest filter kills it.

Known variations to handle when scaling to all 114 sheets (2018) and the 2023 set:
different fill palettes per sheet, sheets with 4-14 seats (Lahore/Karachi), possible
inset boxes, grid label fonts, and sheets where two constituencies share similar
hues — fall back to LAB-space k-means seeded by legend swatch colours in that case.
"""
import cv2, numpy as np, json
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from shapely import make_valid
import pyproj


def segment_class(hsv_base, h, lo, hi, rel=0.05, minarea=1500):
    m = (hsv_base & (h >= lo) & (h <= hi)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    areas = [(stats[i][4], i) for i in range(1, n)]
    out = np.zeros_like(m)
    if not areas:
        return out
    amax = max(a for a, _ in areas)
    for a, i in areas:
        if a >= max(minarea, rel * amax):
            out[lab == i] = 1
    return out


def keep_embedded(mask, core_masks, dilate_px=41, minarea=1500):
    core = cv2.dilate((np.clip(sum(core_masks), 0, 1) * 255).astype(np.uint8),
                      np.ones((dilate_px, dilate_px), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = np.zeros_like(mask)
    for i in range(1, n):
        a = stats[i][4]
        if a >= minarea and ((lab == i) & (core > 0)).sum() > 0.5 * a:
            out[lab == i] = 1
    return out


def detect_grid(small, frame=(0.08, 0.94, 0.05, 0.97), frac=0.5, min_sep=40):
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    g = ((s < 40) & (v > 140) & (v < 235)).astype(np.uint8)
    H, W = g.shape
    m = np.zeros_like(g)
    m[int(frame[0] * H):int(frame[1] * H), int(frame[2] * W):int(frame[3] * W)] = 1
    g *= m

    def peaks(arr):
        thr = frac * arr.max()
        idx = np.where(arr > thr)[0]
        segs = []
        for i in idx:
            if not segs or i - segs[-1][-1] > min_sep:
                segs.append([i])
            else:
                segs[-1].append(i)
        return [int(np.mean(sg)) for sg in segs]
    return peaks(g.sum(0)), peaks(g.sum(1))


def transformer_for(district_centroid, sample_EN):
    best = None
    for zone in (41, 42, 43):
        tr = pyproj.Transformer.from_crs(f'EPSG:326{zone}', 'EPSG:4326', always_xy=True)
        lon, lat = tr.transform(*sample_EN)
        d = (lon - district_centroid[0]) ** 2 + (lat - district_centroid[1]) ** 2
        if best is None or d < best[0]:
            best = (d, zone, tr)
    return best[1], best[2]


def contours_to_feature(mask, px_to_EN, tr, props, minarea=1500, simplify=0.0008):
    mm = cv2.morphologyEx((mask * 255).astype(np.uint8), cv2.MORPH_CLOSE,
                          np.ones((15, 15), np.uint8))
    cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
    polys = []
    for c in cs:
        if cv2.contourArea(c) < minarea:
            continue
        p = c.reshape(-1, 2).astype(float)
        E, N = px_to_EN(p[:, 0], p[:, 1])
        lon, lat = tr.transform(E, N)
        polys.append(make_valid(Polygon(zip(lon, lat))))
    if not polys:
        return None
    g = make_valid(unary_union(polys)).simplify(simplify)
    return {'type': 'Feature', 'properties': props, 'geometry': mapping(g)}


# Example (Quetta 2018 pilot): see session notes / METHODOLOGY.md.
# Per-sheet drivers supply: image path, grid anchors, hue classes, district name.
