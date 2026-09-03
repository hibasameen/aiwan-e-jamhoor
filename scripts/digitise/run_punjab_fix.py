#!/usr/bin/env python3
"""Recover the 5 Punjab districts that fell back to Voronoi in run_punjab.py
(Lahore, Multan, Bhakkar, Rawalpindi, Gujranwala — 35 seats).

Fixes over the original driver:
- dilation range extended to 11 (Gujranwala needs 9, Lahore's dark-line PBS
  sheet resolves its 14 regions only at ~11)
- Bhakkar: NA line crosses the grey desert hatch as a faint pink — relaxed
  red gates (s>30, v>50) recover it
- Multan: the Municipal-Corporation blob is bounded in GREEN, so free space
  leaks through it and NA-154/157 merge. The brown fill is added as a barrier
  and doubles as the city '__BLOB__' region (city seats NA-155/156, which the
  original JOBS wrongly listed as rural)
- per-district debug PNG + plotree Hungarian assignment as in run_punjab
"""
import json, csv, sys, os
BASE = '/root/aiwan'
sys.path.insert(0, f'{BASE}/scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping, Polygon, Point, GeometryCollection
from shapely.ops import unary_union, voronoi_diagram
from shapely import make_valid
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from split_district_by_sheet import fit_outline

SD = f'{BASE}/psheets'
os.makedirs(f'{BASE}/debug', exist_ok=True)

# sheet, district, seats, city seats, options
JOBS = [
 ('dis27.jpg', 'Rawalpindi', [f'NA-{i}' for i in range(57, 64)], ['NA-60', 'NA-61', 'NA-62'], {}),
 ('dis5.jpg', 'Gujranwala', [f'NA-{i}' for i in range(79, 85)], ['NA-81', 'NA-82'], {}),
 ('dis13.jpg', 'Lahore', [f'NA-{i}' for i in range(123, 137)], [], {'dark': True}),
 ('dis17.jpg', 'Multan', [f'NA-{i}' for i in range(154, 160)], ['NA-155', 'NA-156'], {'brown_blob': True}),
 # seeds: pixel points inside NA-97 (north, near its red label) and NA-98 (south)
 ('dis38.jpg', 'Bhakkar', ['NA-97', 'NA-98'], [], {'relaxed_red': True, 'brown_barrier': True,
                                                   'watershed_seeds': [(700, 300), (700, 850)]}),
]

DILS = (2, 3, 4, 5, 7, 9, 11, 13, 15)


def load_geo():
    gb = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
          for f in json.load(open(f'{BASE}/data/gb_PAK_ADM2.geojson'))['features']}
    cents = {r['seat']: (float(r['X']), float(r['Y']))
             for r in csv.DictReader(open(f'{BASE}/plotree_elections/essentials/NA_2018_centroids.csv'))}
    return gb, cents


def line_mask(img, opts):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    if opts.get('dark'):
        red = ((v < 110) & (s < 90)).astype(np.uint8)
    elif opts.get('relaxed_red'):
        red = ((((h <= 12) | (h >= 165)) & (s > 30) & (v > 50))).astype(np.uint8)
    else:
        red = ((((h <= 12) | (h >= 165)) & (s > 55) & (v > 60))).astype(np.uint8)
    brown = None
    if opts.get('brown_blob') or opts.get('brown_barrier'):
        brown = (((h >= 8) & (h <= 24) & (s > 60) & (v > 60) & (v < 230))).astype(np.uint8)
        brown = cv2.morphologyEx(brown, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        brown = cv2.morphologyEx(brown, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        if opts.get('brown_blob'):
            # blob use: keep only the large component(s) (the city corporation)
            n, lab, stats, _ = cv2.connectedComponentsWithStats(brown, 8)
            keep = np.zeros_like(brown)
            if n > 1:
                amax = max(stats[i][4] for i in range(1, n))
                for i in range(1, n):
                    if stats[i][4] > 0.25 * amax:
                        keep[lab == i] = 1
            brown = keep
    return red, brown


def region_masks(img, n_expect, opts):
    red, brown = line_mask(img, opts)
    H, W = red.shape
    barrier_extra = cv2.dilate(brown, np.ones((15, 15), np.uint8)) if brown is not None else None
    for dil in DILS:
        bar = cv2.dilate(red, np.ones((dil, dil), np.uint8))
        if barrier_extra is not None:
            bar = bar | barrier_extra
        free = (1 - bar).astype(np.uint8)
        margin = np.zeros_like(free)
        margin[:4, :] = 1; margin[-4:, :] = 1; margin[:, :4] = 1; margin[:, -4:] = 1
        n, lab, stats, cent = cv2.connectedComponentsWithStats(free, 4)
        outside = set(np.unique(lab[margin > 0]))
        regs = [(stats[i][4], i) for i in range(1, n) if i not in outside and stats[i][4] > 0.001 * H * W]
        regs.sort(reverse=True)
        # drop key-map inset / legend fragments: regions whose centroid falls
        # outside 1.2x the bbox of the three largest regions (the map body)
        if len(regs) >= 3:
            xs = []; ys = []
            for a, i in regs[:3]:
                x, y, w2, h2, _ = stats[i]
                xs += [x, x + w2]; ys += [y, y + h2]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            mx, my = 0.1 * (x1 - x0), 0.1 * (y1 - y0)
            regs = [(a, i) for a, i in regs
                    if (x0 - mx) <= cent[i][0] <= (x1 + mx) and (y0 - my) <= cent[i][1] <= (y1 + my)]
        if len(regs) >= n_expect and (n_expect < 2 or regs[n_expect - 1][0] >= opts.get('min_ratio', 0.0) * regs[0][0]):
            keep = regs[:max(n_expect, len([r for r in regs if r[0] > 0.005 * H * W]))]
            masks = [cv2.dilate((lab == i).astype(np.uint8), np.ones((dil + 1, dil + 1), np.uint8))
                     for a, i in keep]
            return masks, brown, dil
    return None, brown, None


def watershed_masks(img, opts):
    """Seeded watershed on the distance transform of the barrier mask: robust
    to small gaps in the NA line (a gap becomes a low-distance ridge where the
    two basins meet, so the boundary still forms there)."""
    from scipy import ndimage as ndi
    from skimage.segmentation import watershed
    red, brown = line_mask(img, opts)
    barrier = red.copy()
    if brown is not None:
        barrier |= cv2.dilate(brown, np.ones((15, 15), np.uint8))
    barrier = cv2.dilate(barrier, np.ones((3, 3), np.uint8))
    H, W = barrier.shape
    # map body via content blob (independent of gaps in the outer red boundary)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s2, v2 = hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    nonwhite = ((s2 > 28) | (v2 < 150)).astype(np.uint8)
    ff = max(3, int(0.02 * min(H, W)))
    nonwhite[:ff, :] = 0; nonwhite[-ff:, :] = 0; nonwhite[:, :ff] = 0; nonwhite[:, -ff:] = 0
    m2 = cv2.morphologyEx(nonwhite, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n2, lab2, stats2, _ = cv2.connectedComponentsWithStats(m2, 8)
    big = max(range(1, n2), key=lambda i: stats2[i][4])
    blobm = (lab2 == big).astype(np.uint8)
    blobm = cv2.morphologyEx(blobm, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    cs, _ = cv2.findContours(blobm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    region = np.zeros_like(blobm)
    cv2.drawContours(region, cs, -1, 1, -1)
    dist = cv2.distanceTransform((region & (1 - cv2.dilate(red, np.ones((3, 3), np.uint8)))).astype(np.uint8), cv2.DIST_L2, 5)
    markers = np.zeros((H, W), np.int32)
    for k, (sx, sy) in enumerate(opts['watershed_seeds'], start=1):
        cv2.circle(markers, (int(sx), int(sy)), 6, int(k), -1)
    labels = watershed(-dist, markers, mask=region > 0)
    masks = []
    for k in range(1, len(opts['watershed_seeds']) + 1):
        masks.append((labels == k).astype(np.uint8))
    return masks


def process(sheet, dname, seats, city, opts, gb, cents):
    img = cv2.imread(f'{SD}/{sheet}')
    if img is None:
        raise IOError(sheet)
    gbd = gb[dname]
    rural = [s for s in seats if s not in city]
    use_brown_blob = opts.get('brown_blob') and city
    n_regions = len(rural) + (0 if use_brown_blob else (1 if city else 0))
    if opts.get('watershed_seeds'):
        masks, brown, dil = watershed_masks(img, opts), None, 'ws'
        if len(masks) < n_regions or any(m.sum() < 5000 for m in masks):
            raise RuntimeError('watershed produced degenerate masks')
    else:
        masks, brown, dil = region_masks(img, n_regions, opts)
    if masks is None:
        raise RuntimeError('region extraction failed')
    masks = masks[:n_regions]
    if use_brown_blob:
        masks = masks + [brown]
    union = np.zeros_like(masks[0])
    for m in masks:
        union |= m
    union = cv2.morphologyEx((union * 255), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)) // 255
    px_to_metric, (KX, KY), rms = fit_outline(union, gbd)
    mcent = []
    for m in masks:
        ys, xs = np.nonzero(m)
        mcent.append(px_to_metric(np.array([[xs.mean(), ys.mean()]]))[0])
    mcent = np.array(mcent)
    targets = [np.array([cents[s][0] * KX, cents[s][1] * KY]) for s in rural]
    tnames = list(rural)
    if city:
        cc = np.array([[cents[s][0] * KX, cents[s][1] * KY] for s in city]).mean(0)
        targets.append(cc); tnames.append('__BLOB__')
    if use_brown_blob:
        # the brown mask IS the blob: assign rural regions among rural targets
        C = ((mcent[:-1, None, :] - np.array(targets[:-1])[None, :, :]) ** 2).sum(-1)
        ri, ti = linear_sum_assignment(C)
        assign = {tnames[t]: r for r, t in zip(ri, ti)}
        assign['__BLOB__'] = len(masks) - 1
    else:
        T = np.array(targets)
        C = ((mcent[:, None, :] - T[None, :, :]) ** 2).sum(-1)
        ri, ti = linear_sum_assignment(C)
        assign = {tnames[t]: r for r, t in zip(ri, ti)}
    pts, labs, order = [], [], []
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
    if city and '__BLOB__' in feats:
        blob = feats.pop('__BLOB__')
        feats.update(split_blob(blob, city, cents))
    missing = [s for s in seats if s not in feats or feats[s].is_empty]
    if missing:
        raise RuntimeError(f'missing {missing}')
    return feats, rms, dil


def split_blob(blob, city, cents, gn=260):
    """Split the city blob among city seats: per-cell nearest plotree centroid;
    if any seat ends up empty (centroid off-blob), fall back to k-means cells
    matched to centroids by Hungarian. Every seat is guaranteed a piece."""
    from shapely import contains_xy
    minx, miny, maxx, maxy = blob.bounds
    gx = np.linspace(minx, maxx, gn); gy = np.linspace(miny, maxy, gn)
    XX, YY = np.meshgrid(gx, gy)
    fx, fy = XX.ravel(), YY.ravel()
    inb = contains_xy(blob, fx, fy)
    P = np.stack([fx, fy], 1)
    T = np.array([cents[s] for s in city])
    lab = np.argmin(((P[:, None, :] - T[None, :, :]) ** 2).sum(-1), 1)
    counts = [(lab[inb] == k).sum() for k in range(len(city))]
    if min(counts) < 4:
        pts = P[inb]
        from scipy.cluster.vq import kmeans2
        cc, kl = kmeans2(pts, len(city), seed=7, minit='++')
        C = ((cc[:, None, :] - T[None, :, :]) ** 2).sum(-1)
        ri, ti = linear_sum_assignment(C)
        remap = {r: t for r, t in zip(ri, ti)}
        full = np.zeros(len(P), int)
        full[inb] = np.array([remap[k] for k in kl])
        lab = np.where(inb, full, -1)
    dx, dy = gx[1] - gx[0], gy[1] - gy[0]
    out = {}
    for k, s in enumerate(city):
        cm = np.zeros(len(P), np.uint8)
        cm[(lab == k) & inb] = 1
        cm = cm.reshape(gn, gn)
        cs, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        polys = []
        for c in cs:
            if len(c) < 4 or cv2.contourArea(c) < 4:
                continue
            q = c.reshape(-1, 2).astype(float)
            polys.append(make_valid(Polygon(zip(minx + q[:, 0] * dx, miny + q[:, 1] * dy)).buffer(max(dx, dy) * 0.7)))
        if polys:
            out[s] = make_valid(unary_union(polys).intersection(blob))
    # top-up any unclaimed blob slivers to nearest piece
    rem = make_valid(blob.difference(unary_union(list(out.values())))) if out else blob
    if not rem.is_empty:
        geoms = list(rem.geoms) if rem.geom_type in ('MultiPolygon', 'GeometryCollection') else [rem]
        for g in geoms:
            if g.geom_type != 'Polygon' or g.area == 0 or not out:
                continue
            near = min(out, key=lambda s2: out[s2].distance(g))
            out[near] = make_valid(unary_union([out[near], g]))
    return out


def debug_png(key, img, feats, geom, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 6))
    ax[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); ax[0].set_title(key); ax[0].axis('off')
    cmap = plt.get_cmap('tab20')
    for i, (na, g) in enumerate(sorted(feats.items())):
        gs = [g] if g.geom_type == 'Polygon' else list(g.geoms)
        for p in gs:
            if p.geom_type != 'Polygon' or p.is_empty:
                continue
            x, y = p.exterior.xy
            ax[1].fill(x, y, alpha=0.65, color=cmap(i % 20))
        c = g.representative_point()
        ax[1].annotate(na[3:], (c.x, c.y), fontsize=8, ha='center')
    b = geom.boundary
    for seg in ([b] if b.geom_type == 'LineString' else list(b.geoms)):
        x, y = seg.xy
        ax[1].plot(x, y, 'k-', lw=0.8)
    ax[1].set_aspect('equal'); ax[1].axis('off'); ax[1].set_title('output')
    plt.tight_layout(); plt.savefig(path, dpi=90); plt.close()


def main():
    gb, cents = load_geo()
    results, report = {}, []
    for sheet, dname, seats, city, opts in JOBS:
        try:
            feats, rms, dil = process(sheet, dname, seats, city, opts, gb, cents)
            tag = f'sheet-split (red-line trace): Punjab/{sheet}, outline-fit rms {rms:.1f}km'
            if opts.get('dark'):
                tag = f'sheet-split (black-line trace): Punjab/{sheet}, outline-fit rms {rms:.1f}km'
            if city:
                tag += f'; city seats {"/".join(city)} voronoi within true blob'
            for na, g in feats.items():
                src = tag if na not in city else tag + ' [city-approx]'
                results[na] = (g, src, na in city)
            report.append((dname, 'OK', f'dil {dil} rms {rms:.1f}'))
            img = cv2.imread(f'{SD}/{sheet}')
            debug_png(dname, img, feats, gb[dname], f'{BASE}/debug/punjab_{dname}.png')
        except Exception as e:
            report.append((dname, 'FAIL', str(e)[:90]))

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
    print('updated seats:', updated)


if __name__ == '__main__':
    main()
