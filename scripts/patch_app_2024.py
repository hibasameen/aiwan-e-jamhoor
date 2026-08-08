#!/usr/bin/env python3
"""Surgically swap the 2024 boundary layer inside the built app and add the
provisional-boundary treatment, without rebuilding 2002/2018 from source
(the shipped app carries a newer 2018 layer than build_map.py references)."""
import json, re, sys
from shapely.geometry import shape, mapping, MultiPolygon
from shapely import make_valid
from shapely.geometry.polygon import orient

SRC = '/mnt/user-data/uploads/Aiwan-e-Jamhoor/aiwan_e_jamhoor_map.html'
OUT = '/root/aiwan/aiwan_e_jamhoor_map.html'
NEW = '/root/aiwan/data/na_2023delim_app.geojson'

s = open(SRC).read()
print(f'source app {len(s)/1e6:.2f} MB')

# ---- 1. rewind the new layer clockwise for d3-geo (CCW rings render inverted)
gj = json.load(open(NEW))
for f in gj['features']:
    g = make_valid(shape(f['geometry']))
    if g.geom_type == 'Polygon':
        g = orient(g, sign=-1.0)
    elif g.geom_type == 'MultiPolygon':
        g = MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
    else:
        polys = []
        for x in getattr(g, 'geoms', []):
            if x.geom_type == 'Polygon': polys.append(orient(x, sign=-1.0))
            elif x.geom_type == 'MultiPolygon': polys += [orient(p, sign=-1.0) for p in x.geoms]
        g = MultiPolygon(polys)
    f['geometry'] = mapping(g)
assert len(gj['features']) == 266, len(gj['features'])
newjson = json.dumps(gj, separators=(',', ':'))
print(f'new 2024 layer {len(newjson)/1e6:.2f} MB, 266 seats, rings rewound CW')

# ---- 2. find the '2024': {...} value inside the GEOS object and replace it
i = s.find("const GEOS = {")
assert i > 0, 'GEOS not found'
k = s.find("'2024':", i)
assert k > 0, "'2024' key not found"
b = s.find('{', k)
depth, j, instr, esc = 0, b, False, False
while j < len(s):
    c = s[j]
    if instr:
        if esc: esc = False
        elif c == '\\': esc = True
        elif c == '"': instr = False
    else:
        if c == '"': instr = True
        elif c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: break
    j += 1
old = s[b:j+1]
print(f'replacing embedded 2024 layer: {len(old)/1e6:.2f} MB -> {len(newjson)/1e6:.2f} MB')
assert '"FeatureCollection"' in old or "'FeatureCollection'" in old or 'features' in old
s = s[:b] + newjson + s[j+1:]

# ---- 3. same UI patches as map_template.html
PATCHES = [
("""#map .cst{stroke:var(--stroke);stroke-width:.45;cursor:pointer}
#map .cst:hover{stroke:var(--ink-1);stroke-width:1.1}""",
 """#map .cst{stroke:var(--stroke);stroke-width:.45;cursor:pointer}
#map .cst.prov{stroke:var(--ink-3);stroke-width:.6;stroke-dasharray:2.4 1.9}
#map .cst:hover{stroke:var(--ink-1);stroke-width:1.1}"""),

("'2024': {geo:'2024', delim:'2023 delimitation (reconstructed boundaries)', seats:266, postponed:[], missing_geom:[]}",
 "'2024': {geo:'2024', delim:'2023 delimitation (ECP sheets + composition)', seats:266, postponed:[], missing_geom:[]}"),

("""    .attr('class','cst').attr('d', path)""",
 """    .attr('class','cst').attr('d', path)
    .classed('prov', d=>d.properties.confidence==='low')"""),

("""  if(d.properties.approx) html += `<div class="t2" style="opacity:.75">Boundary within district: approximate</div>`;""",
 """  const bn = boundaryNote(d.properties);
  if(bn) html += `<div class="t2" style="opacity:.75">${bn}</div>`;"""),

("""// ---------- detail ----------""",
 """// ---------- boundary provenance ----------
function boundaryNote(p){
  if(year!=='2024') return p && p.approx ? 'Boundary within district: approximate' : '';
  if(!p) return '';
  if(p.confidence==='low')    return 'Internal boundaries provisional — district edges are exact, the lines between seats are not';
  if(p.confidence==='medium') return 'Boundary from the published seat composition; the line inside a split tehsil is inferred';
  return p.src && p.src.indexOf('district-composition')===0
    ? 'Boundary exact — this seat is a whole district'
    : 'Boundary digitised from the ECP delimitation sheet';
}

// ---------- detail ----------"""),

("""    ${where? `<div class="dmeta" style="margin-top:2px">${where}</div>`:''}""",
 """    ${where? `<div class="dmeta" style="margin-top:2px">${where}</div>`:''}
    ${(()=>{const bn=boundaryNote(f&&f.properties); return bn? `<div class="dmeta" style="margin-top:2px;opacity:.7">${bn}</div>`:'';})()}"""),
]
for a, b_ in PATCHES:
    n = s.count(a)
    assert n == 1, f'patch anchor found {n}x, expected 1: {a[:70]!r}'
    s = s.replace(a, b_)

# 2024 note (match the old text loosely, it is long)
m = re.search(r"'2024': `Boundaries: <b>reconstructed</b>[^`]*`", s)
assert m, '2024 note not found'
NOTE2024 = ("'2024': `Boundaries: <b>true 2023-delimitation lines</b>, all 266 seats — 203 digitised from "
 "ECP delimitation sheets or exact whole-district seats, 44 built from the published seat composition, and "
 "<b>19 provisional</b> (shown with a <b>dashed border</b>: Peshawar, Islamabad, Faisalabad and Gujranwala "
 "city seats, Sheikhupura, Korangi) where no boundary document was reachable and the lines between seats are "
 "inferred. District-level edges are exact throughout. Results: ElectionPakistani transcription cross-checked "
 "against 254 official scanned Form-47s (registered voters, turnout, polling stations, rejected votes shown are "
 "official Form-47 figures). Most winning independents were PTI-backed (shown as IND). Five seats flagged where "
 "the election-day Form-47 winner was later reversed.`")
s = s[:m.start()] + NOTE2024 + s[m.end():]

open(OUT, 'w').write(s)
print(f'wrote {OUT}  {len(s)/1e6:.2f} MB')
for k2 in ['cst.prov', 'boundaryNote', 'true 2023-delimitation lines', "classed('prov'"]:
    print(f'  {k2}: {s.count(k2)}')
