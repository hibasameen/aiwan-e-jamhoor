#!/usr/bin/env python3
"""
Reconstruct the district units used to report the 1993 and 1997 National
Assembly returns, by dissolving present-day ADM2 polygons into them.

The unit set is YEAR-SPECIFIC: the returns for 1997 name Shangla, Hangu,
Malakand and Upper/Lower Dir separately, where 1993 folded them into Swat,
Kohat and Dir. So each year gets its own partition, and each partition is
asserted to cover every in-scope present-day district exactly once.

Gilgit-Baltistan and Azad Jammu & Kashmir are excluded: they elect no
National Assembly members.
"""
import json, re, io, collections
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.ops import unary_union
from shapely import make_valid
from shapely.geometry.polygon import orient

ADM2 = 'data/cod_PAK_ADM2.geojson'

GB = {'Astore','Diamir','Ghanche','Ghizer','Gilgit','Gupis-Yasin','Hunza','Kharmang',
      'Nagar','Rondu','Shigar','Skardu','Darel','Tangir'}
AJK = {'Bagh','Bhimber','Haveli','Jhelum Valley','Kotli','Mirpur','Muzaffarabad',
       'Neelum','Poonch','Sudhnoti'}

# present-day district -> the district it belonged to in Oct 1993 (researched, sourced)
PARENT = {
    'Chaman':'Killa Abdullah','Chiniot':'Jhang','Chitral Upper':'Chitral',
    'Duki':'Loralai','Harnai':'Sibi','Jamshoro':'Dadu',
    'Kambar Shahdad Kot':'Larkana','Kashmore':'Jacobabad',
    'Kohistan Upper':'Kohistan','Kolai Palas Kohistan':'Kohistan','Kohistan Lower':'Kohistan',
    'Korangi Karachi':'Karachi East','Lehri':'Sibi',
    'Matiari':'Hyderabad','Nankana Sahib':'Sheikhupura','Nushki':'Chagai',
    'Shaheed Sikandarabad':'Kalat','Sherani':'Zhob','Sohbatpur':'Jaffarabad',
    'Sujawal':'Thatta','Tando Allahyar':'Hyderabad','Tando Muhammad Khan':'Hyderabad',
    'Tor Ghar':'Mansehra','Washuk':'Kharan',
    # present-day name -> name used in the 1990s returns
    'Batagram':'Battagram','Kachhi':'Bolan','Buner':'Buner','Gwadar':'Gwadar',
    'D. I. Khan':'Dera Ismail Khan','Lasbela':'Lasbela','Leiah':'Layyah',
    'Shaheed Benazir Abad':'Nawabshah','Kech':'Turbat','Tharparkar':'Tharparkar',
    'Naushahro Feroze':'Naushero Feroz','Central Karachi':'Karachi Central',
    'East Karachi':'Karachi East','South Karachi':'Karachi South',
    'West Karachi':'Karachi West','Malir Karachi':'Malir',
    'Chitral Lower':'Chitral','Lower Dir':'Lower Dir','Upper Dir':'Upper Dir',
}
# units the 1993 returns had not yet split out: child unit -> 1993 unit.
# Malir is folded into Karachi East (Malir was notified in 1996, from Karachi East).
# Malakand is NOT folded: 1993's Malakand seat (NA-26) went to a by-election on
# 2 Dec 1993, so that territory has no general-election result and is drawn as no-poll.
FOLD_1993 = {'Shangla':'Swat','Hangu':'Kohat','Lower Dir':'Dir','Upper Dir':'Dir',
             'Malir':'Karachi East'}
FOLD_1997 = {}

TRIBAL = re.compile(r'Tribal Area \d\s*[-:]\s*(.+?) Agency')
FR_MARKER = 'Tribal Areas Attached To'
norm = lambda s: re.sub(r'[^a-z]', '', s.lower())

# return-side spellings that differ from the canonical unit name
CANON = {norm(k): v for k, v in {
    'Abbbottabad':'Abbottabad','Attok':'Attock','Batagram':'Battagram','Bunair':'Buner',
    'Gawadar':'Gwadar','Jhall Magsi':'Jhal Magsi','Muzaffaragarh':'Muzaffargarh',
    'Muzaffaragrah':'Muzaffargarh','Labdela':'Lasbela','Thar':'Tharparkar',
    'Kulachi':'Dera Ismail Khan','Mirpurkhas':'Mirpur Khas','Rahimyar Khan':'Rahim Yar Khan',
    'Umerkot':'Umer Kot','Naushero Feroz':'Naushero Feroz',
    'Malakand Protected Area':'Malakand',
}.items()}

def canon(nm):
    return CANON.get(norm(nm), nm)

def parse_units(cname):
    stem = re.sub(r'\s*[-–]?\s*(\d+|[IVXL]+)$', '', cname).strip()
    out = []
    for p in re.split(r'(?i)\s*-\s*cum\s*-\s*', stem):
        p = p.strip()
        if FR_MARKER in p: out.append('__FR__'); continue
        t = TRIBAL.match(p)
        out.append(t.group(1) if t else canon(p))
    return out

def rewind(g):
    g = make_valid(g)
    if g.geom_type == 'Polygon': return orient(g, sign=-1.0)
    polys = []
    for x in getattr(g, 'geoms', []):
        if x.geom_type == 'Polygon': polys.append(orient(x, sign=-1.0))
        elif x.geom_type == 'MultiPolygon': polys += [orient(p, sign=-1.0) for p in x.geoms]
    return MultiPolygon(polys)

def main():
    adm = json.load(io.open(ADM2, encoding='utf-8'))['features']
    res = json.load(open('results_all.json'))
    geoms = {f['properties']['shapeName']: make_valid(shape(f['geometry']))
             for f in adm if f['properties']['shapeName'] not in GB | AJK}
    print(f'in-scope present-day districts: {len(geoms)}')

    out_feats, agg, report, shapes = [], {}, {}, {}
    for y, fold in (('1993', FOLD_1993), ('1997', FOLD_1997)):
        # which units do this year's returns name?
        seats = collections.defaultdict(list); fr = []
        for na, v in res[y].items():
            us = parse_units(v['name'])
            for u in us:
                if u == '__FR__': fr.append(na)
                else: seats[u].append(na)
        # assign every present-day district to one of this year's units
        assign, unassigned = collections.defaultdict(list), []
        for nm, g in geoms.items():
            u = PARENT.get(nm, nm)
            u = fold.get(u, u)
            u = PARENT.get(u, u); u = fold.get(u, u)
            assign[u].append(nm)
            if u not in seats: unassigned.append((nm, u))
        report[y] = {'unitsNamed': len(seats), 'unitsWithGeometry': len(assign),
                     'namedButNoGeometry': sorted(set(seats) - set(assign)),
                     'districtsUnassigned': sorted(unassigned),
                     'frontierRegionSeats': fr}
        # dissolve + aggregate
        yd = {}
        for u, mods in assign.items():
            g = rewind(unary_union([geoms[m] for m in mods]).simplify(0.005, preserve_topology=True))
            shapes.setdefault(u, {})[y] = mapping(g)
            nas = seats.get(u, [])
            if not nas:                       # territory with no general-election result
                yd[u] = {'seats': 0, 'noPoll': True, 'mods': sorted(mods)}
                continue
            tally = collections.Counter(res[y][na]['wp'] for na in nas)
            topn = max(tally.values())
            leaders = [p for p, n in tally.items() if n == topn]
            # tie on seats -> the party with the larger combined winning vote in this unit
            votes = collections.Counter()
            for na in nas:
                r = res[y][na]
                if r['wp'] in leaders and r['wv']: votes[r['wp']] += r['wv']
            top = max(leaders, key=lambda p: votes.get(p, 0)) if len(leaders) > 1 else leaders[0]
            tos = [(res[y][na]['to'], res[y][na]['reg']) for na in nas
                   if res[y][na]['to'] and res[y][na]['reg']]
            regs = [res[y][na]['reg'] for na in nas if res[y][na]['reg']]
            yd[u] = {'seats': len(nas), 'wp': top,
                     'tied': len(leaders) > 1,
                     'tally': tally.most_common(),
                     'reg': sum(regs) if regs else None,
                     'to': round(sum(t*r for t, r in tos)/sum(r for _, r in tos), 1) if tos else None,
                     'mods': sorted(mods),
                     'nas': [{'na': na, 'name': res[y][na]['name'], 'wp': res[y][na]['wp'],
                              'wn': res[y][na]['wn'], 'ws': res[y][na]['ws'],
                              'mov': res[y][na]['mov'], 'to': res[y][na]['to'],
                              'shared': len(parse_units(res[y][na]['name'])) > 1}
                             for na in sorted(nas, key=lambda x: int(x.split('-')[1]))]}
        agg[y] = yd

    for y in ('1993', '1997'):
        r = report[y]
        print(f"\n{y}: units named {r['unitsNamed']} | with geometry {r['unitsWithGeometry']}"
              f" | tied {sum(1 for v in agg[y].values() if v.get('tied'))}")
        print(f"   named but no geometry : {r['namedButNoGeometry']}")
        print(f"   districts unassigned  : {[f'{a} (->{b})' for a,b in r['districtsUnassigned']]}")
        print(f"   Frontier Regions seat : {r['frontierRegionSeats']}")
        covered={n['na'] for v in agg[y].values() for n in v.get('nas',[])}
        print(f"   distinct seats covered: {len(covered)} of {len(res[y])}"
              f" | no-poll units: {[u for u,v in agg[y].items() if v.get('noPoll')]}")

    # dedupe: emit one feature per unit unless its geometry differs between years
    same = diff = 0
    for u, byyear in shapes.items():
        keys = list(byyear)
        if len(keys) == 2 and json.dumps(byyear[keys[0]]) == json.dumps(byyear[keys[1]]):
            out_feats.append({'type':'Feature','properties':{'u':u,'y':'*'},'geometry':byyear[keys[0]]}); same += 1
        else:
            for yy, gm in byyear.items():
                out_feats.append({'type':'Feature','properties':{'u':u,'y':yy},'geometry':gm}); diff += 1
    print(f'geometry dedupe: {same} units shared across years, {diff} year-specific features')
    gj = {'type':'FeatureCollection','features':out_feats}
    json.dump(gj, open('data/districts_1990s.geojson','w'), separators=(',',':'))
    json.dump(agg, open('data/districts_1990s_results.json','w'), separators=(',',':'))
    print(f"\nwrote d90.geojson ({len(out_feats)} features, {round(len(json.dumps(gj))/1e6,2)} MB) + d90_results.json")

if __name__ == '__main__':
    main()
