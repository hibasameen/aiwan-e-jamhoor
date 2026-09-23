#!/usr/bin/env python3
"""
Draw NA-95 (Gujranwala-I) and NA-96 (Gujranwala-II) on the 2002 layer and cut
them out of NA-97/NA-98, which cover the city in the rugpundit NA shapefile.

Sources
1. Seat composition: the ECP final list of constituencies, Gazette of Pakistan
   Extraordinary, 28 June 2002. The upstream repo has the scans in
   "Delimination Changes 2013/": NA.pdf p.34 (gazette p.864) and PP.pdf
   pp.25-26 (gazette pp.971-972). Both seats are whole census charges of
   Gujranwala city, and each is exactly two provincial seats:
       NA-95 = charges 12-23             = PP-91 (12-16,18) + PP-92 (17,19-23)
       NA-96 = charges 1-3, 8-11, 24-32  = PP-93 (24-26,29-32) + PP-94 (1-3,8-11,27,28)
       NA-97 = MC charges 4-7, 33, Gujranwala Cantt, Talwandi Rahwali QH, ...
             = PP-95 + PP-96
   The 2007 amendments (ECP, 21 May 2007: "NA Ammendments.pdf" and
   "PP Ammendments.pdf") go from NA-91 to NA-112 and from PP-83 to PP-124, so
   no Gujranwala seat changed and the same seats held for 2002, 2008 and 2013.
2. Geometry: rugpundit's provincial shapefile (Pakistan_PA.shp, GPL-3.0), by
   the same digitiser as the NA layer, has PP-91..PP-94. The extract is
   data/sources/rugpundit_pa_2002_gujranwala.geojson. Upstream tags PP-91..94
   as NA-98, which the gazette shows is wrong.
   NA-95 = PP-91 u PP-92 and NA-96 = PP-93 u PP-94, clipped to the old
   NA-97 u NA-98 so the layer keeps the same outline with no gaps. Snapping to
   the 1e-4 grid leaves sliver overlaps under 2 m wide; the manifest records
   them.
3. Cross-check only, not an input: the Saad Ali Khan Pakistan Commons map
   (CC BY-SA 4.0) draws the two seats in a GUJRANWALA inset and shows the city
   as a grey patch on the main map. The inset is fitted mask to mask
   (similarity transform optimised on IoU, as in BOUNDARIES_TODO.md) to the new
   city shape, and the main map is fitted on the Gujranwala district outline to
   find the patch. Results go in the manifest.

Run from anywhere:  python3 scripts/boundaries/split_gujranwala_2002.py
Writes the files below. If NA-95/96 are already in the layer, it only re-runs
the checks.
  data/na_constituencies_2002delim.geojson     (272 features)
  data/digitised/gujranwala_2002_split.json    (measurements)
  data/digitised/qa_gujranwala_2002.png        (QA figure)
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize
import shapely
from shapely import make_valid, set_precision
from shapely.geometry import shape, mapping, box, Polygon, MultiPolygon, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
os.chdir(ROOT)
LAYER = 'data/na_constituencies_2002delim.geojson'
PA_EXTRACT = 'data/sources/rugpundit_pa_2002_gujranwala.geojson'
COMMONS = 'data/sources/Pakistan_General_election_2002.png'
MANIFEST = 'data/digitised/gujranwala_2002_split.json'
QA_PNG = 'data/digitised/qa_gujranwala_2002.png'
GRID = 1e-4                       # the shipped layer's coordinate precision (4 dp)

GAZETTE = {
    'NA-95': {'name': 'Gujranwala-I', 'pp': ['PP-91', 'PP-92'],
              'charges': '12-23 of Gujranwala City'},
    'NA-96': {'name': 'Gujranwala-II', 'pp': ['PP-93', 'PP-94'],
              'charges': '1-3, 8-11, 24-32 of Gujranwala City'},
    'NA-97': {'name': 'Gujranwala-III', 'pp': ['PP-95', 'PP-96'],
              'charges': 'MC charges 4-7, 33; Gujranwala Cantt; Talwandi Rahwali QH; '
                         'Lohianwala PC; Bhatti Bhangoo, Nandipur, Basiwala PCs'},
}
SRC_CITY = ('rugpundit PA shapefile PP-{a} + PP-{b} (seat = those two PP seats per ECP gazette '
            '28 Jun 2002); cross-checked against Commons 2002 map inset')
SRC_CARVE = ('rugpundit NA shapefile minus the Gujranwala city seats NA-95/NA-96 '
             '(city had been absorbed into NA-97/NA-98 upstream)')

# local km frame for measurement
LAT0, LON0 = 32.15, 74.17
KY = 111.32
KX = KY * math.cos(math.radians(LAT0))
to_km = lambda g: affinity.affine_transform(g, [KX, 0, 0, KY, -LON0 * KX, -LAT0 * KY])
km2 = lambda g: to_km(g).area


def polygonal(g):
    g = make_valid(g)
    if g.geom_type in ('Polygon', 'MultiPolygon'):
        return g
    parts = []
    for x in getattr(g, 'geoms', []):
        if x.geom_type == 'Polygon': parts.append(x)
        elif x.geom_type == 'MultiPolygon': parts += list(x.geoms)
    return MultiPolygon(parts) if len(parts) > 1 else parts[0]


def clockwise(g):
    """d3-geo wants clockwise exteriors (see METHODOLOGY §4); the layer is stored that way."""
    g = polygonal(g)
    if g.geom_type == 'Polygon':
        return orient(g, sign=-1.0)
    return MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])


def drop_crumbs(g, min_km2=0.01):
    """Remove grid-snapping crumbs from a carved polygon; returns the area dropped."""
    g = polygonal(g)
    parts = list(g.geoms) if g.geom_type == 'MultiPolygon' else [g]
    keep = [p for p in parts if km2(p) >= min_km2]
    dropped = sum(km2(p) for p in parts if km2(p) < min_km2)
    g2 = keep[0] if len(keep) == 1 else MultiPolygon(keep)
    return g2, dropped


# ---------------------------------------------------------------- build
PP2NA = {'PP-91': 'NA-95', 'PP-92': 'NA-95', 'PP-93': 'NA-96', 'PP-94': 'NA-96',
         'PP-95': 'NA-97', 'PP-96': 'NA-97', 'PP-97': 'NA-98', 'PP-98': 'NA-98'}


def load_pp():
    return {f['properties']['PA']: set_precision(make_valid(shape(f['geometry'])), GRID)
            for f in json.load(open(PA_EXTRACT))['features']}


def carve(own97, own98, c95, c96, pa):
    """Split a layer's own NA-97/NA-98 into NA-95..98, which together cover the
    old NA-97 u NA-98 on the 1e-4 grid. c95/c96 are the city seats. pa is the PP
    polygons, used only to give stranded pieces to the right seat. The patch
    script also uses this on the copies of the layer inside the app pages."""
    own97 = set_precision(polygonal(own97), GRID)
    own98 = set_precision(polygonal(own98), GRID)
    U = shapely.union(own97, own98, grid_size=GRID)
    c95 = set_precision(polygonal(c95), GRID)
    c96 = set_precision(polygonal(c96), GRID)
    outside = km2(shapely.difference(shapely.union(c95, c96, grid_size=GRID), U, grid_size=GRID))
    n95 = shapely.intersection(c95, U, grid_size=GRID)
    n96 = shapely.difference(shapely.intersection(c96, U, grid_size=GRID), n95, grid_size=GRID)
    city = shapely.union(n95, n96, grid_size=GRID)
    n97 = shapely.difference(own97, city, grid_size=GRID)
    n98 = shapely.difference(shapely.difference(own98, city, grid_size=GRID), n97, grid_size=GRID)
    # Carving can strand small detached pieces of NA-97/NA-98 inside the city
    # notch, where the NA and PA digitisations do not quite register. Hand each
    # detached piece to the seat its PP polygon belongs to (per the gazette).
    cur = {'NA-95': n95, 'NA-96': n96, 'NA-97': n97, 'NA-98': n98}
    moved = []
    for n in ('NA-97', 'NA-98'):
        g = polygonal(cur[n])
        parts = sorted(getattr(g, 'geoms', [g]), key=lambda q: -q.area)
        for q in parts[1:]:
            share = {v: 0.0 for v in PP2NA.values()}
            for k, v in pa.items():
                share[PP2NA[k]] += q.intersection(v).area
            to = max(share, key=share.get)
            if to == n: continue
            cur[n] = shapely.difference(cur[n], q, grid_size=GRID)
            cur[to] = shapely.union(cur[to], q, grid_size=GRID)
            moved.append({'from': n, 'to': to, 'km2': round(km2(q), 3),
                          'pp_share': round(share[to] / q.area, 3)})
    crumbs, new = {}, {}
    for n in ('NA-95', 'NA-96', 'NA-97', 'NA-98'):
        new[n], crumbs[n] = drop_crumbs(cur[n])
    info = {
        'detached_pieces_reassigned': moved,
        'city_outside_old_NA97_98_km2': round(outside, 4),
        'city_taken_from_NA97_km2': round(km2(shapely.intersection(own97, city)), 2),
        'city_taken_from_NA98_km2': round(km2(shapely.intersection(own98, city)), 2),
        'crumbs_dropped_km2': {k: round(v, 4) for k, v in crumbs.items()},
    }
    return new, U, info


def build(feats):
    pa = load_pp()
    c95 = shapely.union(pa['PP-91'], pa['PP-92'], grid_size=GRID)
    c96 = shapely.union(pa['PP-93'], pa['PP-94'], grid_size=GRID)
    old = {n: shape(feats[n]['geometry']) for n in ('NA-97', 'NA-98')}
    new, U, info = carve(old['NA-97'], old['NA-98'], c95, c96, pa)
    return new, old, U, info


def validate(new, old, U, feats_all):
    # Check the geometry as it will be written. During the build shapely keeps
    # the 1e-4 grid on every result, which hides the thin slivers that snapping
    # leaves between NA-95 and NA-97.
    new = {n: shape(mapping(clockwise(g))) for n, g in new.items()}
    U = shape(mapping(U))
    res = {}
    for n, g in new.items():
        assert g.is_valid and g.geom_type in ('Polygon', 'MultiPolygon'), n
        res[n] = {'km2': round(km2(g), 2), 'parts': len(getattr(g, 'geoms', [g])),
                  'vertices': int(shapely.get_num_coordinates(g))}
    names = list(new)
    ov = 0.0
    for i in range(4):
        for j in range(i + 1, 4):
            ov += km2(new[names[i]].intersection(new[names[j]]))
    res['overlap_among_four_km2'] = round(ov, 5)
    Unew = unary_union(list(new.values()))
    res['union_symdiff_km2'] = round(km2(Unew.symmetric_difference(U)), 5)
    res['union_km2_before_after'] = [round(km2(U), 3), round(km2(Unew), 3)]
    # overlap with the neighbours must not grow
    nb = [n for n in feats_all if n not in new and shape(feats_all[n]['geometry']).intersects(U.buffer(0.01))]
    ob = sum(km2(make_valid(shape(feats_all[n]['geometry'])).intersection(U)) for n in nb)
    oa = sum(km2(make_valid(shape(feats_all[n]['geometry'])).intersection(Unew)) for n in nb)
    res['neighbour_overlap_km2_before_after'] = [round(ob, 4), round(oa, 4)]
    assert ov < 0.01, f'overlap among new seats {ov} km2'
    assert res['union_symdiff_km2'] < 0.05, res['union_symdiff_km2']
    assert oa <= ob + 1e-3
    return res


# ---------------------------------------------------------------- cross-checks on the Commons map
def commons_rgb():
    return np.asarray(Image.open(COMMONS).convert('RGB')).astype(int)


def raster(geom_km, p, hw):
    """Rasterise a km-frame geometry onto a pixel grid under the similarity
    km = R(th) * s * (x, -y) + t   (p = s, th, tx, ty)."""
    s, th, tx, ty = p
    H, W = hw
    img = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(img)
    ct, st = math.cos(th), math.sin(th)
    polys = geom_km.geoms if geom_km.geom_type == 'MultiPolygon' else [geom_km]
    for q in polys:
        for ring, col in [(q.exterior, 255)] + [(r, 0) for r in q.interiors]:
            xy = np.asarray(ring.coords) - [tx, ty]
            u = (ct * xy[:, 0] + st * xy[:, 1]) / s
            v = (-st * xy[:, 0] + ct * xy[:, 1]) / s
            dr.polygon([(float(a), float(-b)) for a, b in zip(u, v)], fill=col)
    return np.asarray(img) > 127


def px_to_km(p):
    s, th, tx, ty = p
    return [s * math.cos(th), s * math.sin(th), s * math.sin(th), -s * math.cos(th), tx, ty]


def fit_similarity(mask, target_km, starts_deg=(-15, 0, 15)):
    H, W = mask.shape
    ys, xs = np.where(mask)

    def loss(p):
        r = raster(target_km, p, (H, W))
        return 1 - (r & mask).sum() / (r | mask).sum()
    s0 = math.sqrt(target_km.area / mask.sum())
    cx, cy = target_km.centroid.x, target_km.centroid.y
    best, bl = None, 2
    for d in starts_deg:
        th = math.radians(d)
        u, v = xs.mean() * s0, -ys.mean() * s0
        p = np.array([s0, th, cx - (math.cos(th) * u - math.sin(th) * v),
                      cy - (math.sin(th) * u + math.cos(th) * v)])
        l = loss(p)
        for sc in (0.05, 0.02, 0.005):
            step = np.array([p[0] * sc, sc * 2, sc * 5, sc * 5])
            sim = np.vstack([p] + [p + np.eye(4)[i] * step[i] for i in range(4)])
            r = optimize.minimize(loss, p, method='Nelder-Mead',
                                  options={'initial_simplex': sim, 'maxiter': 3000,
                                           'xatol': 1e-6, 'fatol': 1e-7})
            if r.fun < l: p, l = r.x, r.fun
        if l < bl: best, bl = p, l
    return best, 1 - bl


def mask_to_km(mask, p, x0=0, y0=0):
    cells = [box(x - .5, y - .5, x + .5, y + .5) for y, x in zip(*np.where(mask))]
    return affinity.affine_transform(unary_union(cells), px_to_km(p))


def inset_check(a, city95_km, city96_km):
    """Gujranwala inset box on the 2002 map: NA-95 #484848, NA-96 #528d6b."""
    X0, Y0, X1, Y1 = 3090, 1880, 3470, 2240
    c = a[Y0:Y1, X0:X1]
    m95 = ndimage.binary_fill_holes((np.abs(c - [72, 72, 72]).sum(2) == 0))
    m96 = ndimage.binary_fill_holes((np.abs(c - [82, 141, 107]).sum(2) == 0))
    lab, _ = ndimage.label(m95); m95 = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1
    lab, _ = ndimage.label(m96); m96 = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1
    solid = ndimage.binary_fill_holes(ndimage.binary_closing(m95 | m96, np.ones((5, 5))))
    d95, d96 = ndimage.distance_transform_edt(~m95), ndimage.distance_transform_edt(~m96)
    g95, g96 = solid & (d95 <= d96), solid & (d96 < d95)
    city_km = city95_km.union(city96_km)
    p, iou = fit_similarity(solid, city_km)
    H, W = solid.shape
    r95, r96 = raster(city95_km, p, (H, W)), raster(city96_km, p, (H, W))
    iou_ = lambda x, y: float((x & y).sum() / (x | y).sum())
    both = (g95 | g96) & (r95 | r96)
    agree = float((((g95 & r95) | (g96 & r96)) & both).sum() / both.sum())
    # line distances (km)
    T = px_to_km(p)
    def pts_km(mask_edge):
        ys, xs = np.where(mask_edge)
        P = np.column_stack([xs, ys]).astype(float)
        return np.column_stack([T[0] * P[:, 0] + T[1] * P[:, 1] + T[4], T[2] * P[:, 0] + T[3] * P[:, 1] + T[5]])
    outline = solid ^ ndimage.binary_erosion(solid)
    inner = g95 & ndimage.binary_dilation(g96)
    shared = city95_km.boundary.intersection(city96_km.boundary)
    d_out = np.array([city_km.boundary.distance(Point(*q)) for q in pts_km(outline)])
    d_in = np.array([shared.distance(Point(*q)) for q in pts_km(inner)])
    geo95 = mask_to_km(g95, p); geo96 = mask_to_km(g96, p)
    return {
        'box_px': [X0, Y0, X1, Y1],
        'fit': 'similarity (scale, rotation, shift) on the NA-95 u NA-96 mask, Nelder-Mead on IoU',
        'scale_m_per_px': round(p[0] * 1000, 1), 'rotation_deg': round(math.degrees(p[1]), 1),
        'outline_iou': round(iou, 3),
        'iou_NA95': round(iou_(g95, r95), 3), 'iou_NA96': round(iou_(g96, r96), 3),
        'same_seat_share_of_common_area': round(agree, 3),
        'outline_distance_km_median_p90': [round(float(np.median(d_out)), 2), round(float(np.percentile(d_out, 90)), 2)],
        'split_line_distance_km_median_p90': [round(float(np.median(d_in)), 2), round(float(np.percentile(d_in, 90)), 2)],
        'inset_area_ratio_NA96_to_NA95': round(float(g96.sum() / g95.sum()), 3),
    }, (c, p, geo95, geo96)


def mainmap_check(a, layer_feats, city_km):
    """Locate the grey city patch on the main map by fitting the drawn Gujranwala
    district (NA-97..101 + patch) to the layer's district outline."""
    X0, Y0, X1, Y1 = 2950, 1080, 3330, 1400
    c = a[Y0:Y1, X0:X1]
    key = (c[:, :, 0] << 16) | (c[:, :, 1] << 8) | c[:, :, 2]
    seeds = {'NA-98': (3122, 1222), 'NA-97': (3158, 1206), 'NA-99': (3195, 1255),
             'NA-100': (3115, 1258), 'NA-101': (3100, 1195), 'CITY': (3147, 1228)}
    masks = {}
    for k, (x, y) in seeds.items():
        x -= X0; y -= Y0
        lab, _ = ndimage.label(key == key[y, x])
        masks[k] = ndimage.binary_fill_holes(lab == lab[y, x])
    assert tuple(c[seeds['CITY'][1] - Y0, seeds['CITY'][0] - X0]) == (195, 195, 195)
    dist = np.zeros(c.shape[:2], bool)
    for m in masks.values(): dist |= m
    dist = ndimage.binary_fill_holes(ndimage.binary_closing(dist, np.ones((5, 5))))
    district = unary_union([make_valid(shape(layer_feats[n]['geometry'])) for n in
                            ('NA-95', 'NA-96', 'NA-97', 'NA-98', 'NA-99', 'NA-100', 'NA-101')])
    p, iou = fit_similarity(dist, to_km(district), starts_deg=(-10, 0, 10))
    patch = mask_to_km(ndimage.binary_dilation(masks['CITY'], iterations=1), p)
    return {
        'crop_px': [X0, Y0, X1, Y1],
        'district_fit_iou': round(iou, 3), 'scale_km_per_px': round(p[0], 3),
        'patch_px': int(masks['CITY'].sum()),
        'patch_centroid_lonlat': [round(patch.centroid.x / KX + LON0, 4), round(patch.centroid.y / KY + LAT0, 4)],
        'patch_centroid_offset_km': round(patch.centroid.distance(city_km.centroid), 2),
        'patch_inside_city_share': round(patch.intersection(city_km).area / patch.area, 3),
    }, patch


# ---------------------------------------------------------------- QA figure
def qa_figure(feats, new, inset_res, inset_aux, patch_km, main_res):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly
    col = {'NA-95': '#3b6fb6', 'NA-96': '#6cbf84', 'NA-97': '#e7c23c', 'NA-98': '#e39b5b'}
    fig, axs = plt.subplots(1, 3, figsize=(20, 7.4))

    def draw(ax, g, fc, ec='#444', lw=1.0, alpha=1.0, tf=lambda x: x, ls='-', zorder=1):
        g = tf(g)
        for q in (g.geoms if g.geom_type == 'MultiPolygon' else [g]):
            ax.add_patch(MPoly(np.asarray(q.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw,
                               alpha=alpha, ls=ls, zorder=zorder))

    # 1. context: new tiling in km
    ax = axs[0]
    for n in ('NA-99', 'NA-100', 'NA-101', 'NA-113'):
        draw(ax, make_valid(shape(feats[n]['geometry'])), '#eeeeee', tf=to_km)
        rp = to_km(make_valid(shape(feats[n]['geometry']))).representative_point()
        ax.text(rp.x, rp.y, n, ha='center', fontsize=9, color='#777', clip_on=True)
    for n, g in new.items():
        draw(ax, g, col[n], tf=to_km, zorder=2)
    for n, g in new.items():
        rp = to_km(g).representative_point()
        ax.text(rp.x, rp.y, n, ha='center', va='center', fontsize=10, weight='bold', zorder=5)
    ax.set_xlim(-25, 22); ax.set_ylim(-20, 22); ax.set_aspect(1)
    ax.set_title('2002 layer after the split (km from 74.17E, 32.15N)', fontsize=11)

    # 2. the split over the georeferenced Commons inset
    ax = axs[1]
    c, p, geo95, geo96 = inset_aux
    from matplotlib.transforms import Affine2D
    T = px_to_km(p)
    H, W = c.shape[:2]
    warp = Affine2D(np.array([[T[0], T[1], T[4]], [T[2], T[3], T[5]], [0, 0, 1]]))
    ax.imshow(c.astype(np.uint8), extent=[0, W, H, 0], alpha=0.55, zorder=0,
              transform=warp + ax.transData)
    draw(ax, new['NA-95'], 'none', ec='#0b3d91', lw=2.2, tf=to_km, zorder=3)
    draw(ax, new['NA-96'], 'none', ec='#0b6b2b', lw=2.2, tf=to_km, ls='--', zorder=3)
    for n in ('NA-95', 'NA-96'):
        rp = to_km(new[n]).representative_point()
        ax.text(rp.x, rp.y, n, ha='center', fontsize=10, weight='bold', color='#111', zorder=5)
    cc = to_km(new['NA-95'].union(new['NA-96'])).bounds
    ax.set_xlim(cc[0] - 4, cc[2] + 4); ax.set_ylim(cc[1] - 3, cc[3] + 3); ax.set_aspect(1)
    ax.set_title('Shipped NA-95 (blue) / NA-96 (green, dashed) over the Commons 2002 inset\n'
                 f"fitted by similarity: outline IoU {inset_res['outline_iou']}, "
                 f"same-seat share {inset_res['same_seat_share_of_common_area']:.0%}", fontsize=10)

    # 3. location check against the main-map patch
    ax = axs[2]
    for n, g in new.items():
        draw(ax, g, col[n], tf=to_km, alpha=0.8)
        rp = to_km(g).representative_point()
        ax.text(rp.x, rp.y, n, ha='center', fontsize=10, weight='bold')
    draw(ax, patch_km, 'none', ec='red', lw=2.0, zorder=4)
    ax.plot(*patch_km.centroid.xy, 'r+', ms=14, mew=2, zorder=5)
    ax.set_xlim(-12, 12); ax.set_ylim(-8, 12); ax.set_aspect(1)
    ax.set_title("Commons main-map city patch (red, 0.55 km/px local fit)\n"
                 f"centroid {main_res['patch_centroid_offset_km']} km from the shipped city's; "
                 f"district fit IoU {main_res['district_fit_iou']}", fontsize=10)
    fig.suptitle('Gujranwala NA-95/NA-96 (2002 delimitation) - rugpundit PP-91..94 per ECP gazette 28 Jun 2002; '
                 'confidence: medium', fontsize=13, weight='bold')
    fig.text(0.5, 0.01, 'Middle panel background: Gujranwala inset of "Pakistan General election 2002" by Saad Ali Khan '
             'Pakistan, Wikimedia Commons, CC BY-SA 4.0. This figure is shared under CC BY-SA 4.0.',
             ha='center', fontsize=9, color='#555')
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(QA_PNG, dpi=90)
    print('wrote', QA_PNG)


# ---------------------------------------------------------------- main
def main():
    gj = json.load(open(LAYER))
    feats = {f['properties']['na']: f for f in gj['features']}
    applied = 'NA-95' in feats
    if applied:
        print('NA-95/NA-96 already present - re-running the checks only')
        new = {n: polygonal(shape(feats[n]['geometry'])) for n in ('NA-95', 'NA-96', 'NA-97', 'NA-98')}
        build_info, val = None, None
    else:
        assert len(gj['features']) == 270, len(gj['features'])
        new, old, U, build_info = build(feats)
        val = validate(new, old, U, feats)
        print('build:', build_info)
        print('validate:', val)

    a = commons_rgb()
    k95, k96 = to_km(new['NA-95']), to_km(new['NA-96'])
    inset_res, inset_aux = inset_check(a, k95, k96)
    print('inset check:', inset_res)
    layer_for_check = dict(feats)
    for n, g in new.items():
        layer_for_check[n] = {'geometry': mapping(g)}
    main_res, patch = mainmap_check(a, layer_for_check, k95.union(k96))
    print('main-map check:', main_res)

    if not applied:
        base = {'prov': 'Punjab', 'dist': 'Gujranwala', 'teh': 'Gujranwala'}
        out = []
        for f in gj['features']:
            n = f['properties']['na']
            if n in ('NA-97', 'NA-98'):
                f = {'type': 'Feature', 'geometry': mapping(clockwise(new[n])),
                     'properties': dict(f['properties'], src=SRC_CARVE)}
            out.append(f)
        for n, (a_, b_) in (('NA-95', ('91', '92')), ('NA-96', ('93', '94'))):
            out.append({'type': 'Feature', 'geometry': mapping(clockwise(new[n])),
                        'properties': dict(na=n, **base, approx=True, confidence='medium',
                                           src=SRC_CITY.format(a=a_, b=b_))})
        # round-trip check: exteriors clockwise, 272 features, unique seats
        for f in out:
            g = shape(f['geometry'])
            for q in (g.geoms if g.geom_type == 'MultiPolygon' else [g]):
                assert not q.exterior.is_ccw, f['properties']['na']
        assert len(out) == 272 and len({f['properties']['na'] for f in out}) == 272
        gj['features'] = out
        s = json.dumps(gj, ensure_ascii=False, separators=(',', ':'))
        open(LAYER, 'w', encoding='utf-8').write(s)
        print('wrote', LAYER, len(out), 'features')

    manifest = {
        'what': 'NA-95/NA-96 (Gujranwala city) added to the 2002-delimitation layer; NA-97/NA-98 carved',
        'seat_composition_source': 'ECP final list of constituencies, Gazette of Pakistan Extraordinary, '
                                   '28 June 2002 (NA list; PP list pp.971-972), as scanned in '
                                   'rugpundit/PakistanConstituencies2013 "Delimination Changes 2013/"',
        'gazette': GAZETTE,
        'geometry_source': 'rugpundit/PakistanConstituencies2013 @ c0138f0, Pakistan_PA.shp PP-91..PP-94 (GPL-3.0); '
                           'extract ' + PA_EXTRACT,
        'confidence': {'NA-95': 'medium', 'NA-96': 'medium',
                       'why': 'composition exact (gazette) and location confirmed; the drawn lines are a coarse '
                              'unofficial digitisation (8-16 vertices per PP seat) and an independent drawing '
                              'agrees only moderately on the outline and the NA-95/96 line'},
        'build': build_info, 'validation': val,
        'crosscheck_commons_inset_2002': inset_res,
        'crosscheck_commons_mainmap_2002': main_res,
        'note_2008_2013_maps': 'the 2008 and 2013 Commons maps reuse the same inset drawing (single fill, '
                               'black NA-95/96 line) - not independent evidence',
    }
    if applied and os.path.exists(MANIFEST):
        prev = json.load(open(MANIFEST))
        manifest['build'], manifest['validation'] = prev.get('build'), prev.get('validation')
    json.dump(manifest, open(MANIFEST, 'w'), indent=1, ensure_ascii=False)
    print('wrote', MANIFEST)
    qa_figure(feats, new, inset_res, inset_aux, patch, main_res)


if __name__ == '__main__':
    main()
