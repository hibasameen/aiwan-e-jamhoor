#!/usr/bin/env python3
"""
Refine the affine georeference with a quadratic warp.

Fitting in the forward direction — pushing the drawn mask's pixels out to
lon/lat and comparing against the true area rasterised on a fixed grid — means
the transform never has to be inverted, so it can be any polynomial.
"""
import json, io, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize
import georef_map as georef

LON0, LON1, LAT0, LAT1, CELL = 60.0, 76.5, 22.5, 37.5, 0.02

def grid_shape():
    return (int((LAT1 - LAT0) / CELL), int((LON1 - LON0) / CELL))

def true_grid(geom):
    H, W = grid_shape()
    img = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(img)
    polys = geom.geoms if geom.geom_type == 'MultiPolygon' else [geom]
    for p in polys:
        for ring, col in [(p.exterior, 255)] + [(r, 0) for r in p.interiors]:
            xy = np.asarray(ring.coords)
            X = (xy[:, 0] - LON0) / CELL
            Y = (LAT1 - xy[:, 1]) / CELL
            pts = [(float(u), float(v)) for u, v in zip(X, Y)]
            if len(pts) > 2: dr.polygon(pts, fill=col)
    return np.asarray(img) > 127

def basis(x, y, deg):
    cols = [np.ones_like(x), x, y]
    if deg >= 2: cols += [x * x, x * y, y * y]
    return np.column_stack(cols)

def forward(P, coef, deg):
    return basis(P[:, 0], P[:, 1], deg) @ coef

def iou_of(P, coef, deg, T):
    H, W = T.shape
    ll = forward(P, coef, deg)
    gx = ((ll[:, 0] - LON0) / CELL).astype(int)
    gy = ((LAT1 - ll[:, 1]) / CELL).astype(int)
    ok = (gx >= 0) & (gx < W) & (gy >= 0) & (gy < H)
    M = np.zeros_like(T)
    M[gy[ok], gx[ok]] = True
    M = ndimage.binary_closing(M, np.ones((3, 3)))
    M = ndimage.binary_fill_holes(M)
    return (M & T).sum() / max(1, (M | T).sum()), M

def refine(mask, geom, affine, deg=2, step=4):
    T = true_grid(geom)
    ys, xs = np.where(mask[::step, ::step])
    P = np.column_stack([xs * step, ys * step]).astype(float)
    a, b, c, d, e, f = affine
    coef = np.zeros((6 if deg >= 2 else 3, 2))
    coef[0] = [c, f]; coef[1] = [a, d]; coef[2] = [b, e]
    base, _ = iou_of(P, coef, deg, T)
    print(f'   affine on this grid: IoU {base:.4f}')
    scale = np.array([1.0, 1e-3, 1e-3, 1e-7, 1e-7, 1e-7])[:coef.shape[0]]

    def loss(v):
        i, _ = iou_of(P, v.reshape(coef.shape), deg, T)
        return 1 - i
    best, bl = coef.copy(), 1 - base
    for mult in (1.0, 0.3, 0.1):
        s = np.repeat(scale[:, None], 2, axis=1).ravel() * mult
        simplex = np.vstack([best.ravel()] + [best.ravel() + np.eye(best.size)[i] * s[i]
                                              for i in range(best.size)])
        r = optimize.minimize(loss, best.ravel(), method='Nelder-Mead',
                              options={'maxiter': 4000, 'fatol': 1e-7, 'xatol': 1e-9,
                                       'initial_simplex': simplex})
        if r.fun < bl: best, bl = r.x.reshape(coef.shape), r.fun
        print(f'   quadratic refine:   IoU {1-bl:.4f}')
    return best, 1 - bl, T

if __name__ == '__main__':
    path = sys.argv[1]
    name = path.split('/')[-1].rsplit('.', 1)[0]
    mask, comps, lab, a = georef.party_mask(path)
    geom = georef.true_geom()
    affine = np.load(f'{name}_affine.npy')
    coef, iou, T = refine(mask, geom, affine)
    np.save(f'{name}_poly.npy', coef)
    print(f'\n   final IoU {iou:.4f}')
    # boundary error, measured properly
    from shapely.geometry import Point
    edge = mask ^ ndimage.binary_erosion(mask)
    ys, xs = np.where(edge)
    idx = np.linspace(0, len(xs) - 1, min(3000, len(xs))).astype(int)
    P = np.column_stack([xs[idx], ys[idx]]).astype(float)
    ll = forward(P, coef, 2)
    bnd = geom.boundary
    dist = np.array([bnd.distance(Point(*p)) for p in ll]) * 105
    print(f'   drawn edge vs true outline: median {np.median(dist):.1f} km, '
          f'p75 {np.percentile(dist,75):.1f}, p90 {np.percentile(dist,90):.1f}')
