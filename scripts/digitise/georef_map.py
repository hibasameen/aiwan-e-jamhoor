#!/usr/bin/env python3
"""
Georeference a labelled Commons election map by fitting its drawn National
Assembly area to the true one.

The map's party-coloured pixels and the union of the 2002-delimitation
constituencies describe the same territory — Pakistan minus Kashmir and
Gilgit-Baltistan — so the two masks can be aligned directly. Start from moments
(centroid, scale), then optimise a full affine on intersection-over-union.
"""
import json, io, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize
from shapely.geometry import shape
from shapely.ops import unary_union

C2002 = 'data/na_constituencies_2002delim.geojson'
KASHMIR_GREY = np.array([127, 127, 127])
DS = 8                     # work at 1/8 resolution while fitting

def party_mask(path):
    """Pixels belonging to a constituency fill: excludes borders, background,
    Kashmir grey and the hatched area."""
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    lum = a.sum(2)
    m = (lum >= 200) & (lum <= 720)                       # not black, not white
    m &= np.abs(a - KASHMIR_GREY).sum(2) > 60             # not Kashmir/GB grey
    m = ndimage.binary_closing(m, np.ones((7, 7)))
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    main = int(np.argmax(sizes)) + 1
    comps = sorted(((int(s), i + 1) for i, s in enumerate(sizes)), reverse=True)
    return (lab == main), comps, lab, a

def true_geom():
    g = json.load(io.open(C2002, encoding='utf-8'))['features']
    return unary_union([shape(f['geometry']).buffer(0) for f in g])

def rasterise(geom, params, shape_hw):
    """Draw `geom` (lon/lat) into an image-space grid using x = A^-1 (lon,lat)."""
    a, b, c, d, e, f = params
    det = a * e - b * d
    if abs(det) < 1e-12: return None
    H, W = shape_hw
    img = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(img)
    polys = geom.geoms if geom.geom_type == 'MultiPolygon' else [geom]
    for p in polys:
        # shapely hands back a new object on each .exterior access, so identity
        # checks fail — carry the fill value explicitly
        rings = [(p.exterior, 255)] + [(r, 0) for r in p.interiors]
        for ring, col in rings:
            xy = np.asarray(ring.coords)
            lon, lat = xy[:, 0] - c, xy[:, 1] - f
            X = (e * lon - b * lat) / det
            Y = (-d * lon + a * lat) / det
            pts = [(float(u), float(v)) for u, v in zip(X, Y)]
            if len(pts) > 2:
                dr.polygon(pts, fill=col)
    return np.asarray(img) > 127

def fit(mask, geom, verbose=True):
    small = mask[::DS, ::DS]
    H, W = small.shape
    ys, xs = np.where(small)
    # moment start: match centroid and scale, no rotation, y flipped
    mx, my = xs.mean(), ys.mean()
    b0 = geom.bounds
    glon, glat = (b0[0] + b0[2]) / 2, (b0[1] + b0[3]) / 2
    sx = (b0[2] - b0[0]) / (xs.max() - xs.min())
    sy = (b0[3] - b0[1]) / (ys.max() - ys.min())
    p0 = np.array([sx, 0.0, glon - sx * mx, 0.0, -sy, glat + sy * my])

    def loss(p):
        r = rasterise(geom, p, (H, W))
        if r is None: return 1.0
        inter = np.logical_and(r, small).sum()
        union = np.logical_or(r, small).sum()
        return 1.0 - inter / union if union else 1.0

    best = p0; bl = loss(p0)
    if verbose: print(f'   start IoU {1-bl:.4f}')
    for scale in (0.05, 0.02, 0.008):
        step = np.abs(best) * scale + np.array([1e-5, 1e-5, 1e-3, 1e-5, 1e-5, 1e-3])
        res = optimize.minimize(loss, best, method='Nelder-Mead',
                                options={'maxiter': 1600, 'xatol': 1e-7, 'fatol': 1e-6,
                                         'initial_simplex': np.vstack([best] + [best + np.eye(6)[i] * step[i] for i in range(6)])})
        if res.fun < bl: best, bl = res.x, res.fun
        if verbose: print(f'   refine  IoU {1-bl:.4f}')
    # rescale from the downsampled grid to full resolution
    a, b, c, d, e, f = best
    full = np.array([a / DS, b / DS, c, d / DS, e / DS, f])
    return full, 1 - bl

def px2lonlat(P, params):
    a, b, c, d, e, f = params
    x, y = P[:, 0], P[:, 1]
    return np.column_stack([a * x + b * y + c, d * x + e * y + f])

if __name__ == '__main__':
    path = sys.argv[1]
    mask, comps, lab, a = party_mask(path)
    print(f'{path.split("/")[-1]}: main constituency area {mask.sum():,} px')
    print(f'   largest components: {[c[0] for c in comps[:6]]}')
    geom = true_geom()
    params, iou = fit(mask, geom)
    print(f'\n   final IoU {iou:.4f}')
    print(f'   transform: lon = {params[0]:.3e}x + {params[1]:.3e}y + {params[2]:.4f}')
    print(f'              lat = {params[3]:.3e}x + {params[4]:.3e}y + {params[5]:.4f}')
    np.save(path.split('/')[-1].rsplit('.',1)[0] + '_affine.npy', params)
    # boundary agreement: distance from true outline to the fitted mask edge
    edge = mask ^ ndimage.binary_erosion(mask)
    ys, xs = np.where(edge)
    pts = px2lonlat(np.column_stack([xs, ys]), params)
    from shapely.geometry import Point
    bnd = geom.boundary
    samp = pts[::max(1, len(pts)//4000)]
    d = np.array([bnd.distance(Point(*p)) for p in samp]) * 105  # deg -> km
    print(f'   drawn edge vs true outline: median {np.median(d):.1f} km, p90 {np.percentile(d,90):.1f} km')
