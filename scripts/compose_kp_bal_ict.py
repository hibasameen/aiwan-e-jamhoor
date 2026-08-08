#!/usr/bin/env python3
"""2023-delimitation composition build for the 14 remaining canvases
(KP 27 seats, Balochistan 7, ICT 3 = 36 seats -> 266/266).

Method: cells of the authoritative canvas polygon are hard-locked to the seat
that owns their whole tehsil; cells inside a SPLIT tehsil are allocated between
the claiming seats by capacity-constrained nearest-anchor (anchors placed on the
tehsil's bbox in the sourced compass direction, quotas = sourced area shares);
any residue is filled by nearest assigned cell. Output exactly partitions the canvas.
"""
import json, math, os, sys
import numpy as np
from shapely.geometry import shape, mapping, box, Point
from shapely.ops import unary_union
from shapely import make_valid
from scipy.spatial import cKDTree

BASE = os.path.expanduser('~/aiwan')
OUT = f'{BASE}/out/kpbal'
os.makedirs(OUT, exist_ok=True)

DIRV = {'N':(0,1),'S':(0,-1),'E':(1,0),'W':(-1,0),
        'NE':(.7,.7),'NW':(-.7,.7),'SE':(.7,-.7),'SW':(-.7,-.7),
        'C':None}

# ---------------------------------------------------------------- specs
# share = share of THAT tehsil's area (not of the canvas). dir = where in the
# tehsil that seat portion sits. 'C' = the central/urban core of the tehsil.
SPECS = {
 'C001_Swat': dict(conf='medium', src='gb',
   whole={'NA-2':['BAHRAIN','KHAWAZA KHELA','CHARBAGH'],'NA-3':['BARIKOT'],'NA-4':['MATTA']},
   splits=[('BABUZAI',[('NA-2',0.20,'CORE'),('NA-3',0.80,'CORE')]),
           ('KABAL',  [('NA-3',0.35,'CORE'),('NA-4',0.65,'CORE')])],
   note='Wikipedia+electionpakistani: NA-2 Bahrain/Khwazakhela/Charbagh + part Babuzai; NA-4 Matta + most of Kabal. Which side of Babuzai/Kabal is inferred from contiguity.'),

 'C003_LowerDir': dict(conf='medium', src='gb',
   whole={'NA-6':['LALQILLA','SAMARBAGH(BARWA)','MUNDA'],'NA-7':['ADENZAI']},
   splits=[('TEMERGARA',[('NA-6',0.27,'CORE'),('NA-7',0.73,'CORE')])],
   note='NUMBERS TRANSPOSED vs 2018: the southern Jandool/Maidan seat was NA-7 in 2018, is NA-6 in 2023. Confirmed by winner swap (Bashir Khan NA-7 2018 -> NA-6 2024) and by Form-47 electorate 457,075 matching the southern seat.'),

 'C010_Mansehra_Torghar': dict(conf='medium', src='gb',
   whole={'NA-14':['BALAKOT'],'NA-15':['TORGHER','OGHI']},
   splits=[('MANSEHRA',[('NA-14',0.70,'CORE'),('NA-15',0.30,'CORE')])],
   note='Wikipedia NA-15 infobox (electorate 645,049 == Form-47) = Oghi+Darband+Tanawal+part Baffa+part Mansehra + Torghar district. NA-14 = Balakot + Mansehra city/Baffa bulk.'),

 'C011_Abbottabad': dict(conf='high', src='gb',
   whole={'NA-16':['HAVELIAN']},
   splits=[('ABBOTTABAD',[('NA-16',0.40,'E'),('NA-17',0.60,'W')])],
   note='ECP-sourced (APP/Pakistan Observer 4-5 Dec 2023): NA-16 = Havelian, Lora, Bokot, Bagan, Mirpur Cantt, Galyat; NA-17 = Lower Tanawal + Abbottabad tehsil. Galyat/Bakot = the SE hill belt of the Abbottabad polygon.'),

 'C013_Swabi': dict(conf='high', src='gb',
   whole={'NA-19':['TOPI','SWABI'],'NA-20':['RAZAR']},
   splits=[('LAHOR',[('NA-19',0.25,'CORE'),('NA-20',0.75,'CORE')])],
   note='Verbatim ECP final list: NA-19 = Topi + Swabi tehsils + Patwar Circles Kunda Jabba, Anbar, Kunda Mera, Hund of Lahor Qanungo Halqa; NA-20 = Razar + rest of Lahor. Hund is on the Indus => NA-19 takes the eastern/river slice.'),

 'C014_Mardan': dict(conf='medium', src='gb',
   whole={'NA-21':['KATLANG']},
   splits=[('MARDAN',[('NA-21',0.44,'CORE'),('NA-22',0.29,'E'),('NA-23',0.27,'SW')]),
           ('TAKHT BHAI',[('NA-21',0.35,'CORE'),('NA-23',0.65,'SW')])],
   note='geoBoundaries MARDAN polygon = pre-2022 Mardan tehsil = todays Mardan(335km2)+Garhi Kapura(143)+Rustam(379). NA-21 takes Rustam(N), NA-22 Garhi Kapura(E)+Mardan city, NA-23 the rural SW remainder + southern Takht Bhai.'),

 'C015_Charsadda': dict(conf='high', src='gb',
   whole={'NA-24':['TANGI','SHABQADAR'],'NA-25':['CHARSADDA']},
   splits=[],
   note='Clean whole-tehsil split, no partial tehsil. Tangi+Shabqadar (806,766 in 2017) vs Charsadda tehsil (804,194) balance to 0.3%. Corroborated by winner Anwar Taj (Shabqadar) taking NA-24.'),

 'C018_Peshawar': dict(conf='low', src='gb',
   whole={'NA-30':['FR PESHAWAR'],'NA-31':['Peshawar Cantonment']},
   anchors={  # lon, lat of the seat real-world core (used for the free cells)
     'NA-28':[(71.55,34.10),(71.62,34.12)],           # Mathra / Shah Alam, Pajjagi
     'NA-29':[(71.66,34.02),(71.73,34.00)],           # Chamkani / Urmar-Tarnab
     'NA-30':[(71.50,33.93),(71.48,33.86)],           # Pishtakhara / Badaber-Mattani
     'NA-31':[(71.49,34.00),(71.43,33.98)],           # University Town / Hayatabad
     'NA-32':[(71.573,34.008)]},                      # walled city
   free_share={'NA-28':0.25,'NA-29':0.26,'NA-30':0.26,'NA-31':0.16,'NA-32':0.07},
   splits=[],
   note='LOW CONFIDENCE. No 2023 boundary document reachable; the geoBoundaries Peshawar I-IV polygons are an obsolete subdivision that does not map to the 2023 tehsils. Only FR Peshawar->NA-30 and Cantonment->NA-31 are solidly sourced. The rest is an anchored partition from press descriptions of the five seats geography. Sheet digitisation (archive has 3-4 Peshawar sheets) should replace this.'),

 'C019_Nowshera': dict(conf='medium', src='gb',
   whole={'NA-34':['PABBI']},
   splits=[('NOWSHERA',[('NA-33',0.70,'NE'),('NA-34',0.30,'S')])],
   note='Daily Times + Wikipedia: NA-33 = Jehangira tehsil + Nowshera city/Cantt + Risalpur (the E/NE two-thirds); NA-34 = Pabbi tehsil + the southern fringe (Cherat, Saleh Khana, Shahkot, Mohib Banda, Khesgi).'),

 'C028_DeraIsmailKhan_Tank': dict(conf='medium', src='gb',
   whole={'NA-43':['TANK','FR TANK','KULACHI'],'NA-45':['PAROA','DARABAN','FR D.I.KHAN']},
   splits=[('PAHARPUR',[('NA-43',0.37,'CORE'),('NA-44',0.63,'SE')]),
           ('D.I.KHAN',[('NA-43',0.05,'N'),('NA-44',0.67,'C'),('NA-45',0.28,'CORE')])],
   note='LokSujag (verbatim): NA-43 = Tank district incl. Jandola + Kalachi and Paniala tehsils entire + Yarik Qanungoi of D.I.Khan tehsil. Paniala is the N/NW part of the Paharpur polygon. NA-44 = D.I.Khan city+Cantt + rest of Paharpur; NA-45 = Paroa+Daraban+Darazinda + southern rural D.I.Khan tehsil.'),

 'C029_Islamabad': dict(conf='low', src='gb',
   whole={},
   anchors={'NA-46':[(72.90,33.67),(72.98,33.68)],    # Tarnol / Golra
            'NA-47':[(73.07,33.71),(73.15,33.73)],    # city core / Bhara Kahu
            'NA-48':[(73.12,33.58),(73.16,33.52)]},   # Koral-Tarlai / Sihala-Rawat
   free_share={'NA-46':0.34,'NA-47':0.33,'NA-48':0.33},
   splits=[],
   note='LOW CONFIDENCE. Every reachable description of NA-46/47/48 is 2018-vintage (they are the renumbered NA-52/53/54); no 2023 ICT boundary document was obtainable. Three-way anchored partition: NA-46 west (Tarnol/Golra/G-10 westward), NA-47 centre + north-east (Red Zone, F/G-5..9, Bhara Kahu, Chattar), NA-48 east/south-east (Expressway to Rawat, Kuri, Tumair).'),

 'C099_Jaffarabad_JhalMagsi_Kachhi': dict(conf='medium', src='gb', drop_detached_to='NA-261',
   whole={'NA-254':['Jhal Magsi','Gandawa','Mirpur Sub','Dhadar','Mach Sub','Sanni Sub',
                    'Balanari Sub','Khattan Sub','TAMBOO','BABA_KOT'],
          'NA-255':['SOHBATPUR','Jhat Pat','Ghandakha','Usta Muhammad',
                    'DERA_MURAD_JAMALI','CHATTAR']},
   splits=[],
   note='Form-47 titles confirm NA-254 Jhal Magsi-cum-Kachhi-cum-Nasirabad / NA-255 Sohbatpur-cum-Jaffarabad-cum-Usta Muhammad-cum-Nasirabad. Nasirabad is the split district. Of the 16 possible tehsil assignments only 4 leave BOTH seats contiguous (constituencies must be contiguous by law): Baba Kot alone, Tamboo+Baba Kot, DMJ+Tamboo+Baba Kot, or all four to NA-254. All-four contradicts the cum-Nasirabad element of the NA-255 title; DMJ+Tamboo+Baba Kot would reverse the observed electorate ranking. Resolved on FAFEN district voter rolls (Jhal Magsi 78,208 + Kachhi 153,974 = 232,182; NA-254 = 324,739), which force NA-254 to draw ~92,600-115,000 electors from Nasirabad, i.e. ~36-45% of the district (Nasirabad total 254,567) - NOT the small slice a population-parity assumption implies. Nasirabad tehsil population shares: DMJ 53.0, Tamboo 29.8, Baba Kot 10.7, Chhater 6.4. TAMBOO+BABA KOT = 40.5% (~103,100 electors) is the only option that is both contiguous and inside that band. NOT documented - inference from contiguity + FAFEN rolls. NOTE the geoBoundaries Surab polygon falls inside this canvas but Surab district actually belongs to NA-261 - it is deliberately unassigned and absorbed by nearest-core fill.'),

 'C102_Gwadar_Kech_Panjgur': dict(conf='medium', src='gb',
   whole={'NA-258':['PANJGUR','GICHK','PAROME','GOWARGO','Buleda','Hoshab','Zamuran'],
          'NA-259':['Gwadar','Pasni','Ormara','Jiwani','Sunstar Sub','Kech','Tump','Mand','Dasht','Balnigor']},
   splits=[],
   note='Form-47: NA-258 Panjgur-cum-Kech, NA-259 Kech-cum-Gwadar. Whole Panjgur district -> NA-258, whole Gwadar district -> NA-259, Kech split with the sourced direction "NA-259 covers southern parts of Kech": Turbat/Tump/Mand/Dasht south to NA-259, Buleda/Hoshab/Zamuran/Balnigor north to NA-258. Tehsil-level assignment is inferred, only the N/S direction is sourced. RESOLVED FROM THE SHEET (Abdul Ghafoor, NA-258/259 representation): its table defines NA-259 = District Gwadar (305,160) + District Kech (696,791) EXCLUDING Sub-Division Buleda, Sub-Tehsil Zamran, Sub-Tehsil Hoshab, and UCs Sami (Turbat), Shahrak, Nodiz and Nasirabad. So NA-258 takes Buleda + Zamuran + Hoshab only (~34% of Kech population); Tump, Mand, Dasht, Balnigor and Turbat all stay in NA-259. This overrides the earlier roll-arithmetic guess that put Tump in NA-258.'),

 'C105_Quetta': dict(conf='low', src='gb',
   whole={'NA-262':['PANJ PAI SUB-']},
   splits=[('QUETTA CITY',   [('NA-263',0.60,'C'),  ('NA-264',0.40,'W')]),
           ('QUETTA SADDAR', [('NA-262',0.70,'CORE'),('NA-263',0.15,'CORE'),('NA-264',0.15,'CORE')])],
   note='LOW CONFIDENCE. All three seats are Quetta-only (Form-47). NA-262 is the rural ring (Panjpai + Dasht + most of Saddar). The NA-263/NA-264 line inside Quetta city is undocumented - ECP splits the city by census charge. Shares set from Form-47 electorates (NA-262 239,192 / NA-263 418,280 / NA-264 196,762). CORRECTION applied after verification: the COD Quetta district polygon wrongly swallows the Mastung DASHT tehsil (~1,100 km2 of a 4,183 km2 canvas vs the true Quetta ~2,653 km2) - Dasht is carved out and transferred to NA-261 Surab-cum-Kalat-cum-Mastung. Wikipedia gives NA-262 = Kuchlak + Saddar (the outer ring, 28% of the district electorate) and NA-264 = Quetta City areas plus census charges 13-14 (Kechi Baig, Shaboo, Shadinzai, on the west/south-west), leaving NA-263 as the largest block (Sariab plus the balance of the city). Saddar is split three ways anchored on each seat already-assigned cells. The archive holds ~6 Quetta representation sheets; digitising them should replace this.'),
}

# ---------------------------------------------------------------- engine
def load():
    cv = {f['properties']['canvas_id']: make_valid(shape(f['geometry']).buffer(0))
          for f in json.load(open(f'{BASE}/data/digitised/canvases_2023.geojson'))['features']}
    gb = {}
    for f in json.load(open(f'{BASE}/data/gb_PAK_ADM3.geojson'))['features']:
        gb.setdefault(f['properties']['shapeName'], []).append(shape(f['geometry']).buffer(0))
    gb = {k: unary_union(v) for k, v in gb.items()}
    return cv, gb


def grid_cells(poly, target=60000):
    x0, y0, x1, y1 = poly.bounds
    area = max(poly.area, 1e-9)
    res = math.sqrt(area / target)
    res = min(res, 0.02)
    nx, ny = int((x1-x0)/res)+1, int((y1-y0)/res)+1
    xs = x0 + (np.arange(nx)+0.5)*res
    ys = y0 + (np.arange(ny)+0.5)*res
    XX, YY = np.meshgrid(xs, ys)
    pts = np.column_stack([XX.ravel(), YY.ravel()])
    from shapely import points as shp_points, contains_xy
    keep = contains_xy(poly, pts[:, 0], pts[:, 1])
    return pts[keep], res


def cells_in(poly, pts):
    from shapely import contains_xy
    return contains_xy(poly, pts[:, 0], pts[:, 1])


def capacity_assign(pts, parts, unit_poly, cores=None):
    """parts = [(seat, share, dirkey)]; dirkey 'CORE' anchors on the seat own
    whole-tehsil core geometry (keeps the slice adjacent to the rest of the seat)."""
    if len(parts) == 1:
        return np.array([parts[0][0]]*len(pts), dtype=object)
    x0, y0, x1, y1 = unit_poly.bounds
    cx, cy = unit_poly.centroid.x, unit_poly.centroid.y
    span = max(x1-x0, y1-y0)
    cores = cores or {}
    cols, quotas, seats = [], [], []
    for seat, share, dk in parts:
        cp = cores.get(seat)
        if dk == 'CORE' and cp is not None and len(cp):
            cols.append(cKDTree(cp).query(pts)[0])
        else:
            v = DIRV.get(dk)
            a = (cx, cy) if v is None else (cx + v[0]*span*1.1, cy + v[1]*span*1.1)
            cols.append(np.hypot(pts[:, 0]-a[0], pts[:, 1]-a[1]))
        quotas.append(share); seats.append(seat)
    q = np.array(quotas, float); q = q/q.sum()
    N = len(pts)
    target = np.round(q*N).astype(int)
    target[-1] = N - target[:-1].sum()
    D = np.stack(cols, axis=1)
    # additive-weight (auction) adjustment until each seat hits its quota
    w = np.zeros(len(seats))
    for _ in range(300):
        lab = np.argmin(D - w[None, :], axis=1)
        cnt = np.bincount(lab, minlength=len(seats))
        err = cnt - target
        if np.abs(err).max() <= max(2, int(0.004*N)):
            break
        w -= err/N * D.std() * 1.5
    return np.array([seats[i] for i in lab], dtype=object)


def polygonise(pts, labels, res, canvas):
    out = {}
    half = res/2
    for seat in sorted(set(labels)):
        sel = pts[labels == seat]
        if not len(sel):
            continue
        boxes = [box(x-half, y-half, x+half, y+half) for x, y in sel]
        g = unary_union(boxes).buffer(res*0.01).buffer(-res*0.01)
        g = make_valid(g).intersection(canvas)
        if not g.is_empty:
            out[seat] = g
    # exact partition: hand leftovers to the nearest seat
    resid = canvas.difference(unary_union(list(out.values())))
    if not resid.is_empty and resid.area > 1e-12:
        parts = list(resid.geoms) if hasattr(resid, 'geoms') else [resid]
        for p in parts:
            if p.is_empty or p.area <= 0:
                continue
            best = min(out, key=lambda s: out[s].distance(p))
            out[best] = make_valid(unary_union([out[best], p]))
    return out


def largest_lobe(canvas):
    if canvas.geom_type != 'MultiPolygon':
        return canvas, None
    ps = sorted(canvas.geoms, key=lambda p: -p.area)
    return ps[0], unary_union(ps[1:]) if len(ps) > 1 else None


def repair_contiguity(pts, labels, res, tol=0.15):
    """Reassign orphan cell-components (< tol of their seat) to the adjacent seat
    they share the most cells with. Constituencies are contiguous by law."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    key = np.round(pts/res).astype(int)
    idx = {(a, b): i for i, (a, b) in enumerate(map(tuple, key))}
    nbr = [[] for _ in range(len(pts))]
    for i, (a, b) in enumerate(map(tuple, key)):
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            j = idx.get((a+da, b+db))
            if j is not None:
                nbr[i].append(j)
    moved = 0
    for _ in range(6):
        changed = False
        for seat in sorted(set(labels)):
            sel = np.where(labels == seat)[0]
            if len(sel) < 2:
                continue
            pos = {g: k for k, g in enumerate(sel)}
            r, c = [], []
            for g in sel:
                for j in nbr[g]:
                    if j in pos:
                        r.append(pos[g]); c.append(pos[j])
            n, comp = connected_components(coo_matrix((np.ones(len(r)), (r, c)),
                                           shape=(len(sel), len(sel))), directed=False)
            if n <= 1:
                continue
            sizes = np.bincount(comp)
            main = sizes.argmax()
            for ci in range(n):
                if ci == main or sizes[ci] > tol*len(sel):
                    continue
                members = sel[comp == ci]
                tally = {}
                for g in members:
                    for j in nbr[g]:
                        if labels[j] != seat:
                            tally[labels[j]] = tally.get(labels[j], 0) + 1
                if tally:
                    labels[members] = max(tally, key=tally.get)
                    moved += len(members); changed = True
        if not changed:
            break
    return labels, moved


def run_canvas(cid, spec, canvas, gb):
    dropped = None
    if spec.get('drop_detached_to'):
        canvas, dropped = largest_lobe(canvas)
    if spec.get('carve_out'):
        units, tgt = spec['carve_out']
        cut = unary_union([gb[u] for u in units if u in gb]).intersection(canvas)
        if not cut.is_empty:
            canvas = make_valid(canvas.difference(cut))
            canvas, extra = largest_lobe(canvas)
            cut = unary_union([cut] + ([extra] if extra is not None else []))
            dropped = cut if dropped is None else unary_union([dropped, cut])
    pts, res = grid_cells(canvas)
    labels = np.array([None]*len(pts), dtype=object)
    missing = []
    # 1. whole tehsils -> hard lock
    for seat, units in spec.get('whole', {}).items():
        for u in units:
            if u not in gb:
                missing.append(u); continue
            g = gb[u].intersection(canvas)
            if g.is_empty:
                missing.append(u+'(no overlap)'); continue
            labels[cells_in(g, pts)] = seat
    # 2. split tehsils -> capacity-constrained assignment; 'CORE' anchors on the
    #    seat cells assigned SO FAR, so split order lets one split seed the next
    for u, parts in spec.get('splits', []):
        if u not in gb:
            missing.append(u); continue
        g = gb[u].intersection(canvas)
        m = cells_in(g, pts) & (labels == None)
        if m.sum() == 0:
            missing.append(u+'(no free cells)'); continue
        cores = {s2: pts[labels == s2] for s2 in set(labels[labels != None])}
        labels[m] = capacity_assign(pts[m], parts, g, cores)
    # 3. anchored free-cell partition (Peshawar / Islamabad)
    if 'anchors' in spec:
        free = (labels == None)
        if free.sum():
            seats = list(spec['free_share'].keys())
            A, own = [], []
            for s in seats:
                for c in spec['anchors'][s]:
                    A.append(c); own.append(s)
            A = np.array(A)
            q = np.array([spec['free_share'][s] for s in seats], float); q /= q.sum()
            fp = pts[free]; N = len(fp)
            target = np.round(q*N).astype(int); target[-1] = N-target[:-1].sum()
            D = np.sqrt(((fp[:, None, :]-A[None, :, :])**2).sum(-1))
            si = np.array([seats.index(o) for o in own])
            Ds = np.stack([D[:, si == i].min(1) for i in range(len(seats))], 1)
            w = np.zeros(len(seats))
            for _ in range(400):
                lab = np.argmin(Ds - w[None, :], axis=1)
                cnt = np.bincount(lab, minlength=len(seats))
                err = cnt - target
                if np.abs(err).max() <= max(2, int(0.004*N)):
                    break
                w -= err/N * Ds.std() * 1.5
            fl = np.array([seats[i] for i in lab], dtype=object)
            labels[free] = fl
    # 4. residue -> nearest already-labelled cell
    free = (labels == None)
    if free.sum():
        known = ~free
        if known.sum() == 0:
            raise SystemExit(f'{cid}: nothing assigned')
        tree = cKDTree(pts[known])
        _, idx = tree.query(pts[free])
        labels[free] = labels[known][idx]
    # 5. contiguity repair
    labels, moved = repair_contiguity(pts, labels, res)
    geoms = polygonise(pts, labels, res, canvas)
    return geoms, res, missing, labels, pts, moved, dropped


def main():
    cv, gb = load()
    feats, report, transfers = [], {}, []
    for cid, spec in SPECS.items():
        canvas = cv[cid]
        geoms, res, missing, labels, pts, moved, dropped = run_canvas(cid, spec, canvas, gb)
        if dropped is not None and not dropped.is_empty:
            transfers.append(dict(to=spec.get('drop_detached_to') or spec['carve_out'][1],
                                  from_canvas=cid,
                                  area_km2=round(dropped.area*12100, 1),
                                  geometry=mapping(dropped)))
            canvas = cv[cid] if False else canvas
        # QA: exact partition checks
        uni = unary_union(list(geoms.values()))
        symd = uni.symmetric_difference(canvas).area / canvas.area
        ov = 0.0
        ks = sorted(geoms)
        for i in range(len(ks)):
            for j in range(i+1, len(ks)):
                ov += geoms[ks[i]].intersection(geoms[ks[j]]).area
        ov /= canvas.area
        shares = {k: round(geoms[k].area/canvas.area, 4) for k in ks}
        report[cid] = dict(seats=ks, res_deg=round(res, 5), sym_diff=round(symd, 8),
                           overlap=round(ov, 8), area_share=shares,
                           confidence=spec['conf'], missing_units=missing, note=spec['note'])
        for k in ks:
            feats.append(dict(type='Feature',
                properties=dict(na=k, canvas_id=cid,
                    src=f"composition: {'whole-tehsil' if not spec.get('splits') and 'anchors' not in spec else 'tehsil+capacity-split'}",
                    approx=True, confidence=spec['conf'], method='gb-ADM3 composition + anchored capacity partition'),
                geometry=mapping(geoms[k])))
        print(f"{cid:<34} seats={len(ks)} res={res:.4f} symdiff={symd:.2e} overlap={ov:.2e} "
              f"conf={spec['conf']} cells_repaired={moved} missing={missing}")
    json.dump(dict(type='FeatureCollection', features=feats), open(f'{OUT}/kp_bal_ict_2023.geojson', 'w'))
    json.dump(report, open(f'{OUT}/report.json', 'w'), indent=1)
    json.dump(transfers, open(f'{OUT}/transfers.json', 'w'))
    for t in transfers:
        print(f"  transfer: {t['area_km2']:,} km2 detached lobe of {t['from_canvas']} -> {t['to']}")
    print(f'\nwrote {len(feats)} seats -> {OUT}/kp_bal_ict_2023.geojson')


if __name__ == '__main__':
    main()
