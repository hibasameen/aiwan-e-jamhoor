# Aiwan-e-Jamhoor logo generator
# Fonts (variable TTFs) fetched via sparse clone of github.com/google/fonts:
#   ofl/cormorantgaramond/CormorantGaramond[wght].ttf  (English, wght=600)
#   ofl/notonastaliqurdu/NotoNastaliqUrdu[wght].ttf     (Urdu Nastaliq, wght=600)
# Deps: pip install uharfbuzz fonttools brotli --break-system-packages
# Both scripts are HarfBuzz-shaped then outlined to vector paths (no font dependency in output).
# Palette: green #14523a / #0d3b2a / #1e6a49, teal #1f9179, gold #b8912f, card #f7f4ec.

import io, math, uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen

def outline(path, text, wght=None, features=None):
    ft=TTFont(path)
    if wght is not None and 'fvar' in ft: instantiateVariableFont(ft,{'wght':wght},inplace=True)
    buf=io.BytesIO(); ft.save(buf); data=buf.getvalue()
    upm=ft['head'].unitsPerEm; order=ft.getGlyphOrder(); gs=ft.getGlyphSet(); glyf=ft.get('glyf')
    face=hb.Face(data); font=hb.Font(face)
    b=hb.Buffer(); b.add_str(text); b.guess_segment_properties()
    hb.shape(font,b,features or {"kern":True,"liga":True,"calt":True})
    glyphs=[]; penx=peny=0; minx=miny=1e9; maxx=maxy=-1e9
    for i,p in zip(b.glyph_infos,b.glyph_positions):
        gn=order[i.codepoint]; pen=SVGPathPen(gs); gs[gn].draw(pen); d=pen.getCommands()
        gx=penx+p.x_offset; gy=peny+p.y_offset
        if d: glyphs.append((gx,gy,d))
        if glyf is not None:
            g=glyf[gn]
            if getattr(g,'numberOfContours',0)>0:
                minx=min(minx,gx+g.xMin); maxx=max(maxx,gx+g.xMax); miny=min(miny,gy+g.yMin); maxy=max(maxy,gy+g.yMax)
        penx+=p.x_advance; peny+=p.y_advance
    return dict(glyphs=glyphs,upm=upm,bbox=(minx,miny,maxx,maxy),adv=penx)

def group(o,s,GX,GY,fill):
    inner="".join(f'<path transform="translate({gx},{gy})" d="{d}"/>' for gx,gy,d in o['glyphs'])
    return f'<g transform="translate({GX:.2f},{GY:.2f}) scale({s},{-s})" fill="{fill}">{inner}</g>'

# palette
GREEN='#14523a'; GREEN2='#0d3b2a'; GREEN3='#1e6a49'; TEAL='#1f9179'; TEAL2='#2aa588'
GOLD='#b8912f'; GOLD2='#caa23f'; CARD='#f7f4ec'; INK='#123c2b'; CHECK='#14523a'

cx,cy=250,158
def sector(r0,r1,a0,a1):
    a0r,a1r=math.radians(a0),math.radians(a1)
    xo0,yo0=cx+r1*math.cos(a0r),cy+r1*math.sin(a0r); xo1,yo1=cx+r1*math.cos(a1r),cy+r1*math.sin(a1r)
    xi0,yi0=cx+r0*math.cos(a0r),cy+r0*math.sin(a0r); xi1,yi1=cx+r0*math.cos(a1r),cy+r0*math.sin(a1r)
    large=1 if (a1-a0)>180 else 0
    if r0<=0.01: return f"M{cx:.2f},{cy:.2f} L{xo0:.2f},{yo0:.2f} A{r1:.2f},{r1:.2f} 0 {large} 1 {xo1:.2f},{yo1:.2f} Z"
    return (f"M{xo0:.2f},{yo0:.2f} A{r1:.2f},{r1:.2f} 0 {large} 1 {xo1:.2f},{yo1:.2f} L{xi1:.2f},{yi1:.2f} A{r0:.2f},{r0:.2f} 0 {large} 0 {xi0:.2f},{yi0:.2f} Z")

# WIDER arc that curls up at the sides, like the reference (~196 deg)
a_start,a_end=-8.0,188.0
ncol=15; col_gap=1.6
rings=[58,96,134,172,210]           # 4 seat rings
ring_cols=[TEAL,GREEN3,TEAL,GREEN]  # inner -> outer (outer darkest)
span=a_end-a_start; step=span/ncol
core=f'<path d="{sector(0,rings[0]-3,a_start,a_end)}" fill="{GOLD}"/>'
tiles=[]
for ri in range(4):
    r0=rings[ri]+3; r1=rings[ri+1]-3; base=ring_cols[ri]
    for c in range(ncol):
        a0=a_start+c*step+col_gap/2; a1=a_start+(c+1)*step-col_gap/2; fill=base
        # scattered accents like the original mosaic
        if ri==3 and c in (6,7,8): fill=TEAL
        if ri==2 and c in (0,1,13,14): fill=GREEN
        if ri==1 and c in (4,10): fill=TEAL
        if ri==0 and c in (0,14): fill=GREEN3
        tiles.append(f'<path d="{sector(r0,r1,a0,a1)}" fill="{fill}"/>')
tiles_svg="\n".join(tiles)

# ---- isometric ballot box on a gold platform (like the reference) ----
w=46; th=24; bh=40; bt=cy-70          # box top apex y
# gold platform (trapezoid) under the box
plat=f'<path d="M{cx-64},{cy+16} L{cx+64},{cy+16} L{cx+42},{cy-8} L{cx-42},{cy-8} Z" fill="{GOLD2}"/>'
box=f'''<g>
  <!-- left & right body faces -->
  <path d="M{cx-w},{bt+th} L{cx},{bt+2*th} L{cx},{bt+2*th+bh} L{cx-w},{bt+th+bh} Z" fill="{GREEN2}"/>
  <path d="M{cx+w},{bt+th} L{cx},{bt+2*th} L{cx},{bt+2*th+bh} L{cx+w},{bt+th+bh} Z" fill="{GREEN}"/>
  <!-- top lid face (gold) -->
  <path d="M{cx},{bt} L{cx+w},{bt+th} L{cx},{bt+2*th} L{cx-w},{bt+th} Z" fill="{GOLD}"/>
  <!-- slot -->
  <path d="M{cx-16},{bt+th} L{cx},{bt+th-8} L{cx+16},{bt+th} L{cx},{bt+th+8} Z" fill="{GREEN2}"/>
  <!-- ballot card with check, tilted into slot -->
  <g transform="rotate(-8 {cx} {bt-20})">
    <rect x="{cx-24}" y="{bt-46}" width="48" height="54" rx="4" fill="{CARD}" stroke="{GREEN2}" stroke-width="2.4"/>
    <path d="M{cx-13},{bt-20} l9,10 l17,-20" fill="none" stroke="{CHECK}" stroke-width="5.4" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</g>'''

mark = f'<g>{core}\n{tiles_svg}\n{plat}\n{box}</g>'

# ---- wordmarks (outlined) ----
CG='/tmp/gf/ofl/cormorantgaramond/CormorantGaramond[wght].ttf'
NU='/tmp/gf/ofl/notonastaliqurdu/NotoNastaliqUrdu[wght].ttf'
eng=outline(CG,'Aiwan e Jamhoor',wght=600)
urd=outline(NU,'ایوانِ جمہور',wght=600)

tx=cx+250
sE=110/eng['upm']
engG=group(eng,sE,tx,cy+8,INK)
eng_left=tx+eng['bbox'][0]*sE; eng_right=tx+eng['bbox'][2]*sE; engW=eng_right-eng_left
rule=f'<line x1="{tx+2}" y1="{cy+34}" x2="{eng_right:.1f}" y2="{cy+34}" stroke="{GOLD}" stroke-width="2" opacity="0.6"/>'
# Urdu bigger, centered under english
sU=(engW*0.66)/urd['adv']
eng_center=(eng_left+eng_right)/2
GXu=eng_center - sU*(urd['bbox'][0]+urd['bbox'][2])/2
GYu=(cy+52) + sU*urd['bbox'][3]
urdG=group(urd,sU,GXu,GYu,GOLD)

VB_W=int(eng_right+30)
VB_H=int(max(cy+52 + sU*(urd['bbox'][3]-urd['bbox'][1]) + 16, cy+210+14))
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB_W} {VB_H}" role="img" aria-label="Aiwan e Jamhoor · ایوانِ جمہور">
{mark}
{engG}
{rule}
{urdG}
</svg>'''
open('/tmp/logo.svg','w').write(svg)
markonly=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="25 30 450 285" role="img" aria-label="Aiwan e Jamhoor">{mark}</svg>'
open('/tmp/logo_mark.svg','w').write(markonly)
print('VB',VB_W,VB_H)
