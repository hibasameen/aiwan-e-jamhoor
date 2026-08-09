#!/usr/bin/env python3
"""
Turn the merged traced boundary set into a complete tessellation of the
National Assembly area.

Why: warped raster traces cannot tile perfectly — the merged set covers only
~93% of the country (205 gap slivers, mostly around the inset cities and along
region seams) and spills past the true outline. On the map the gaps read as
missing seats.

Method (seed-guided, district-constrained allocation, ~1.1 km grid):
  1. rasterise the true NA area district by district (canvas)
  2. rasterise every seat's merged geometry as its SEED, smaller seats painted
     last so they survive overlaps
  3. inside each district, keep only seed pixels belonging to that district's
     own seats (kills cross-border bleed), then assign every remaining district
     pixel to the nearest kept seed (EDT); a district with no seeds falls back
     to nearest-seat-centroid
  4. vectorise per seat (with holes), simplify, wind CW for d3

Every seat keeps its provenance properties (src / approx / confidence).
Output: data/boundaries/na_207seat_1985-1997_tessellated.geojson
"""
import json, collections
import numpy as np, cv2
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.geometry.polygon import orient
import sys; sys.path.insert(0, 'scripts')
import build_reconstructed_geometry as brg

LON0, LON1, LAT0, LAT1, CELL = 60.5, 77.9, 23.5, 37.2, 0.01
W, H = int((LON1 - LON0) / CELL), int((LAT1 - LAT0) / CELL)

def to_px(lon, lat):
    return (lon - LON0) / CELL, (LAT1 - lat) / CELL

def rast(geom, val, img):
    dr = ImageDraw.Draw(img)
    if geom.geom_type == 'Polygon': polys = [geom]
    elif geom.geom_type == 'MultiPolygon': polys = list(geom.geoms)
    else:  # GeometryCollection etc: keep polygonal parts only
        polys = [g for g in getattr(geom, 'geoms', []) if g.geom_type == 'Polygon'] + \
                [q for g in getattr(geom, 'geoms', []) if g.geom_type == 'MultiPolygon' for q in g.geoms]
    for p in polys:
        for ring, v in [(p.exterior, val)] + [(r, 0) for r in p.interiors]:
            xy = np.asarray(ring.coords)
            X, Y = to_px(xy[:, 0], xy[:, 1])
            pts = list(zip(X.tolist(), Y.tolist()))
            if len(pts) > 2: dr.polygon(pts, fill=v)

def main():
    XW = json.load(open('data/wip/trace/xwalk_207map.json'))['base']
    DIST = brg.load_districts()
    merged = json.load(open('data/boundaries/na_207seat_1985-1997_traced.geojson'))['features']
    props = {f['properties']['na']: f['properties'] for f in merged}
    geoms = {f['properties']['na']: shape(f['geometry']).buffer(0) for f in merged}
    seat_id = {f'NA-{n}': n for n in range(1, 208)}

    # 1. district raster
    dnames = sorted({d for ds in XW.values() for d in ds if d in DIST})
    dix = {d: i + 1 for i, d in enumerate(dnames)}
    dimg = Image.new('I', (W, H), 0)
    for d in dnames:
        rast(DIST[d], dix[d], dimg)
    drast = np.asarray(dimg)
    canvas = drast > 0
    print(f'grid {W}x{H} | canvas px {canvas.sum():,} | districts {len(dnames)}')

    # 2. seed raster (smaller seats last)
    simg = Image.new('I', (W, H), 0)
    for na in sorted(geoms, key=lambda k: -geoms[k].area):
        rast(geoms[na], seat_id[na], simg)
    seeds = np.asarray(simg).copy()

    # 3. district-constrained allocation, with guaranteed seeding: a seat whose
    # traced seed was overpainted or fell outside its districts gets a synthetic
    # seed planted at (the in-district pixel nearest to) its own centroid, so
    # every seat always ends up with territory.
    out = np.zeros((H, W), np.int16)
    seats_by_d = collections.defaultdict(set)
    for na, ds in XW.items():
        for d in ds: seats_by_d[d].add(seat_id[na])
    # first pass: who has seed pixels inside their own districts?
    present = set()
    for d in dnames:
        dm = drast == dix[d]
        own = np.where(np.isin(seeds, list(seats_by_d[d])) & dm, seeds, 0)
        present |= set(np.unique(own)) - {0}
    homeless = {sid for na, sid in seat_id.items()} - present
    print('seats needing synthetic seeds:', sorted(f'NA-{s}' for s in homeless))
    # plant synthetic seeds (in the seat's largest own district)
    id2na = {v: k for k, v in seat_id.items()}
    for sid in homeless:
        na = id2na[sid]
        ds = sorted(XW[na], key=lambda d: -DIST[d].area)
        planted = False
        for d in ds:
            dm = drast == dix[d]
            ys, xs = np.where(dm)
            if not len(ys): continue
            c = geoms[na].centroid
            px, py = to_px(c.x, c.y)
            i = int(np.argmin((xs - px) ** 2 + (ys - py) ** 2))
            y0, x0 = ys[i], xs[i]
            seeds[max(0, y0-2):y0+3, max(0, x0-2):x0+3] = sid
            planted = True; break
        if not planted: print('  could not plant', na)
    # second pass: allocate
    for d in dnames:
        dm = drast == dix[d]
        own = np.where(np.isin(seeds, list(seats_by_d[d])) & dm, seeds, 0)
        if (own > 0).any():
            _, (iy, ix) = ndimage.distance_transform_edt(own == 0, return_indices=True)
            out[dm] = own[iy[dm], ix[dm]]
        else:
            ys, xs = np.where(dm)
            cents = [(sid, geoms[id2na[sid]].centroid) for sid in seats_by_d[d]]
            P = np.column_stack([LON0 + xs * CELL, LAT1 - ys * CELL])
            D = np.stack([np.hypot(P[:, 0] - c.x, P[:, 1] - c.y) for _, c in cents])
            out[ys, xs] = np.array([sid for sid, _ in cents])[D.argmin(0)]
    assert (out[canvas] > 0).all(), 'unassigned canvas pixels'
    HOMELESS_NAS = {id2na[s] for s in homeless}

    # 4. vectorise with holes
    feats = []
    for na, sid in seat_id.items():
        m = (out == sid).astype(np.uint8)
        if not m.any():
            print('WARN empty:', na); continue
        cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        outers = []
        for i, c in enumerate(cs):
            if hier[0][i][3] != -1: continue          # holes handled via parent
            if cv2.contourArea(c) < 4: continue
            ext = c.reshape(-1, 2).astype(float)
            ring = np.column_stack([LON0 + ext[:, 0] * CELL, LAT1 - ext[:, 1] * CELL])
            holes = []
            j = hier[0][i][2]
            while j != -1:
                hc = cs[j].reshape(-1, 2).astype(float)
                if cv2.contourArea(cs[j]) >= 4:
                    holes.append(np.column_stack([LON0 + hc[:, 0] * CELL, LAT1 - hc[:, 1] * CELL]))
                j = hier[0][j][0]
            try:
                p = Polygon(ring, holes).buffer(0)
                if not p.is_empty: outers.append(p)
            except Exception: pass
        if not outers:
            print('WARN no polygon:', na); continue
        g = outers[0] if len(outers) == 1 else MultiPolygon(
            [q for p in outers for q in (p.geoms if p.geom_type == 'MultiPolygon' else [p])])
        g = g.simplify(0.004).buffer(0)
        if g.geom_type == 'Polygon': g = orient(g, -1.0)
        else: g = MultiPolygon([orient(p, -1.0) for p in g.geoms])
        pr = dict(props[na]); pr['na'] = na
        if na in HOMELESS_NAS: pr['confidence'] = 'low'   # territory by allocation only
        def rr(o):
            if isinstance(o, float): return round(o, 4)
            if isinstance(o, list): return [rr(x) for x in o]
            if isinstance(o, dict): return {k: rr(v) for k, v in o.items()}
            return o
        feats.append({'type': 'Feature', 'properties': pr, 'geometry': rr(mapping(g))})

    out_path = 'data/boundaries/na_207seat_1985-1997_tessellated.geojson'
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(out_path, 'w'))
    print(f'wrote {out_path}: {len(feats)} seats, {len(json.dumps(feats)) // 1024} KB')

if __name__ == '__main__':
    main()
