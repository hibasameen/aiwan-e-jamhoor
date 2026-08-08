#!/usr/bin/env python3
"""
Build the 2023-delimitation district layer and digitisation canvases.

- Base: COD ADM2 (geoBoundaries-style shapeName), filtered to the 4 provinces + ICT.
- Renames to the canonical district names of data/na_2024_districts.csv (final delim).
- New-district carves needed at CANVAS level only (a canvas = connected component of
  seats over shared districts; districts inside one canvas never need carving):
    * Taunsa   <- TAUNSA tehsil (gb ADM3) cut from Dera Ghazi Khan     [approx]
    * Kot Addu <- KOT ADDU tehsil (gb ADM3) cut from Muzaffargarh     [approx]
    * Wazirabad<- WAZIRABAD tehsil (gb ADM3) cut from Gujranwala      [approx: Alipur
                  Chatha membership unresolved -> flagged, refined by sheet pass]
    * Keamari  : NOT carved; Keamari + Karachi West form one merged canvas (their
                 sheets define the split).
  Lehri -> merged into Sibi [flag], Shaheed Sikandarabad -> merged into Nasirabad [flag].
- The union of all districts is snapped to the na_2018delim_v2 national outline:
  leftover slivers of the outline are assigned to the nearest district (fill-holes rule),
  district parts outside the outline are clipped off. So the 2023 layer partitions the
  exact same national geometry as the 2018 layer.
Outputs:
  out/districts_2023.geojson  (one feature per canonical district, props: district,
                               province, flags)
  out/canvases_2023.geojson   (one feature per canvas: canvas_id, districts, seats,
                               n_seats)
  out/seats_2023_scaffold.geojson (single-seat canvases resolved to final seat
                               geometry, src='district-composition (final delim)';
                               multi-seat canvases pending)
"""
import json, csv, collections, sys
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import make_valid

D = 'data'; OUT = 'out'

GB_AJK = {  # COD shapeNames outside the 4 provinces + ICT (Gilgit-Baltistan & AJK)
 'Astore','Bagh','Bhimber','Darel','Diamir','Ghanche','Ghizer','Gilgit','Gupis-Yasin',
 'Haveli','Hunza','Jhelum Valley','Kharmang','Kotli','Mirpur','Muzaffarabad','Nagar',
 'Neelum','Poonch','Rondu','Shigar','Skardu','Sudhnoti','Tangir'}

RENAME = {
 'Batagram':'Battagram','D. I. Khan':'Dera Ismail Khan','Tor Ghar':'Torghar',
 'Chitral Lower':'Lower Chitral','Chitral Upper':'Upper Chitral',
 'Kohistan Lower':'Lower Kohistan','Kohistan Upper':'Upper Kohistan',
 'Leiah':'Layyah','Kambar Shahdad Kot':'Qambar Shahdadkot',
 'Shaheed Benazir Abad':'Shaheed Benazirabad','Umer Kot':'Umerkot',
 'Central Karachi':'Karachi Central','East Karachi':'Karachi East',
 'South Karachi':'Karachi South','West Karachi':'Karachi West',
 'Malir Karachi':'Malir','Korangi Karachi':'Korangi','Chagai':'Chagai',
 'Nasirabad':'Nasirabad',
}
MERGE = {'Lehri':'Sibi','Shaheed Sikandarabad':'Nasirabad'}  # flagged approximations
# South Waziristan stays whole (NA-42 unions Lower+Upper).

def load(fn):
    return json.load(open(f'{D}/{fn}'))

def main():
    cod = load('cod_PAK_ADM2.geojson')
    gb3 = load('gb_PAK_ADM3.geojson')
    na18 = load('na_2018delim_v2.geojson')

    # ---- canonical district polygons -------------------------------------
    geoms = {}
    for f in cod['features']:
        n = f['properties']['shapeName']
        if n in GB_AJK:
            continue
        n = RENAME.get(n, n)
        n = MERGE.get(n, n)
        g = make_valid(shape(f['geometry']))
        geoms[n] = make_valid(geoms[n].union(g)) if n in geoms else g

    tehsil = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
              for f in gb3['features']}
    carves = [('Taunsa','Dera Ghazi Khan','TAUNSA'),
              ('Kot Addu','Muzaffargarh','KOT ADDU'),
              ('Wazirabad','Gujranwala','WAZIRABAD')]
    flags = collections.defaultdict(list)
    for new, parent, teh in carves:
        t = tehsil[teh].intersection(geoms[parent])
        geoms[new] = make_valid(t)
        geoms[parent] = make_valid(geoms[parent].difference(t))
        flags[new].append('carved-from-tehsil-approx')
        flags[parent].append(f'minus-{new}-approx')
    flags['Sibi'].append('includes-Lehri')
    flags['Nasirabad'].append('includes-Shaheed-Sikandarabad')

    # ---- seat compositions & canvases ------------------------------------
    # composition-level aliases: new districts without own geometry resolve to the
    # COD parent; in every case parent and child sit in the same seat or canvas.
    ALIAS = {'Hub':'Lasbela','Surab':'Kalat','Usta Muhammad':'Jaffarabad',
             'Lower South Waziristan':'South Waziristan',
             'Upper South Waziristan':'South Waziristan',
             'Murree':'Rawalpindi','Talagang':'Chakwal','Keamari':'Karachi West'}
    rows = list(csv.DictReader(open(f'{D}/na_2024_districts.csv')))
    seat_ds = {r['na']: sorted({ALIAS.get(d.strip(), d.strip())
                                for d in r['districts'].split(';')}) for r in rows}
    seat_meta = {r['na']: r for r in rows}
    missing = sorted({d for ds in seat_ds.values() for d in ds if d not in geoms})
    if missing:
        print('MISSING district geoms:', missing); sys.exit(1)

    parentmap = {}
    def find(x):
        while parentmap.setdefault(x, x) != x:
            parentmap[x] = parentmap[parentmap[x]]; x = parentmap[x]
        return x
    def union_(a, b): parentmap[find(a)] = find(b)
    d2s = collections.defaultdict(list)
    for na, ds in seat_ds.items():
        for d in ds: d2s[d].append(na)
    for d, ss in d2s.items():
        for s in ss[1:]: union_(ss[0], s)
    # forced merge: Keamari + Karachi West one canvas
    union_('NA-242', 'NA-244')
    comps = collections.defaultdict(list)
    for na in seat_ds: comps[find(na)].append(na)

    # ---- snap partition to 2018 national outline -------------------------
    outline = make_valid(unary_union([make_valid(shape(f['geometry']))
                                      for f in na18['features']])).buffer(0)
    # clip districts to outline
    for n in list(geoms):
        geoms[n] = make_valid(geoms[n].intersection(outline))
    # assign outline slivers not covered by any district to nearest district
    covered = make_valid(unary_union(list(geoms.values())))
    leftovers = make_valid(outline.difference(covered)).buffer(0)
    pieces = ([leftovers] if leftovers.geom_type == 'Polygon'
              else list(getattr(leftovers, 'geoms', [])))
    big = [p for p in pieces if p.area > 1e-6]
    print(f'{len(big)} leftover slivers > ~0.1km2 to assign')
    for p in big:
        # longest shared boundary wins; fallback nearest centroid
        best, bl = None, -1
        for n, g in geoms.items():
            if p.distance(g) > 0.05: continue
            l = p.buffer(0.002).intersection(g).area
            if l > bl: bl, best = l, n
        if best is None:
            best = min(geoms, key=lambda n: geoms[n].distance(p))
        geoms[best] = make_valid(geoms[best].union(p))

    prov = {}
    for na, ds in seat_ds.items():
        for d in ds: prov[d] = seat_meta[na]['province']

    import os; os.makedirs(OUT, exist_ok=True)
    dj = {'type':'FeatureCollection','features':[
        {'type':'Feature','properties':{'district':n,'province':prov.get(n,'?'),
                                        'flags':';'.join(flags.get(n,[]))},
         'geometry':mapping(geoms[n])} for n in sorted(geoms)]}
    json.dump(dj, open(f'{OUT}/districts_2023.geojson','w'))

    def nakey(na): return int(na.split('-')[1])
    canv_feats, seat_feats = [], []
    for i, seats in enumerate(sorted(comps.values(), key=lambda c: nakey(c[0]))):
        seats = sorted(seats, key=nakey)
        ds = sorted(set(d for s in seats for d in seat_ds[s]))
        if find('NA-242') == find(seats[0]) and 'Karachi West' not in ds:
            pass
        g = make_valid(unary_union([geoms[d] for d in ds]))
        cid = f'C{i:03d}_' + '_'.join(ds[:3]).replace(' ','')
        canv_feats.append({'type':'Feature','properties':{
            'canvas_id':cid,'districts':';'.join(ds),'seats':';'.join(seats),
            'n_seats':len(seats)},'geometry':mapping(g)})
        if len(seats) == 1:
            na = seats[0]
            seat_feats.append({'type':'Feature','properties':{
                'na':na,'name':seat_meta[na]['constituency_name'],
                'province':seat_meta[na]['province'],
                'districts':';'.join(ds),
                'src':'district-composition (final delim 2023)',
                'approx':bool(any(flags.get(d) for d in ds)),
                'flags':';'.join(sum([flags.get(d,[]) for d in ds],[]))},
                'geometry':mapping(g)})
    json.dump({'type':'FeatureCollection','features':canv_feats},
              open(f'{OUT}/canvases_2023.geojson','w'))
    json.dump({'type':'FeatureCollection','features':seat_feats},
              open(f'{OUT}/seats_2023_scaffold.geojson','w'))
    print(f'{len(geoms)} districts, {len(canv_feats)} canvases, '
          f'{len(seat_feats)} single-seat geometries done')
    ms = [f for f in canv_feats if f['properties']['n_seats']>1]
    print(f'{len(ms)} multi-seat canvases covering '
          f'{sum(f["properties"]["n_seats"] for f in ms)} seats pending')

if __name__ == '__main__':
    main()
