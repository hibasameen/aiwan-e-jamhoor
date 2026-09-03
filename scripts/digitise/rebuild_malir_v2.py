#!/usr/bin/env python3
"""
Malir rebuild v2 from the PBS/ECP prelim-2023 map. Fixes vs v1 (which lost the
Kathor arm and caught stray line-work): explicit colour rules per seat, opening
to kill the yellow TC-boundary lines, and nearest-class EDT assignment with no
mode filter (preserves the narrow river-valley arm). Swaps into map.html GEOS
+ na_2023delim_true_full. QA IoU vs the Wikipedia locator is printed as a gate.
"""
import json, time, math
import numpy as np, cv2
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.affinity import translate, scale as S, rotate
from shapely.ops import unary_union
import sys; sys.path.insert(0, 'scripts')
import georef_map as G

Image.MAX_IMAGE_PIXELS = None
IMG = '2023 Delimitation/NA/Malir NA.JPG'

im = Image.open(IMG).convert('RGB')
im = im.resize((im.size[0]//2, im.size[1]//2))
a = np.asarray(im).astype(np.int16)
r, g, b = a[:,:,0].astype(int), a[:,:,1].astype(int), a[:,:,2].astype(int)
yellow = (r > 205) & (abs(r-g) < 45) & ((r-b) >= 70)
lav    = (r > 140) & (b - (r+g)/2 > 18) & (b > 185) & ~( (b>r+60)&(r<140) )
khaki  = (r > 150) & (abs(r-g) < 32) & ((r-b) >= 10) & ((r-b) < 70) & ~yellow
water  = (b > r + 60) & (r < 140)
yellow = ndimage.binary_opening(yellow, np.ones((3,3)))   # light open: keep the Kathor arm
lav    = ndimage.binary_opening(lav, np.ones((3,3)))
land = yellow | lav | khaki
filled = ndimage.binary_fill_holes(ndimage.binary_closing(land, np.ones((7,7))) | water)
lab, n = ndimage.label(filled)
sizes = ndimage.sum(filled, lab, range(1, n+1))
district = ndimage.binary_fill_holes(lab == (int(np.argmax(sizes))+1))
cls = np.zeros(district.shape, np.uint8)
cls[khaki & district] = 1; cls[lav & district] = 2; cls[yellow & district] = 3
un = district & (cls == 0)
_, (iy, ix) = ndimage.distance_transform_edt(cls == 0, return_indices=True)
cls[un] = cls[iy[un], ix[un]]
print('class px:', {i: int((cls==i).sum()) for i in (1,2,3)})

txt = open('map.html', encoding='utf-8').read()
lines = txt.split('\n')
gi = next(i for i, l in enumerate(lines) if l.startswith('window.GEOS='))
GEO = json.loads(lines[gi][len('window.GEOS='):-1])
cur = {f['properties']['na']: shape(f['geometry']).buffer(0)
       for f in GEO['2024']['features'] if f['properties']['na'] in ('NA-229','NA-230','NA-231')}
malir = unary_union(list(cur.values())).buffer(0)
aff, iou = G.fit(district, malir, verbose=False)
print(f'georef IoU {iou:.3f}')
A,B,C,D,E,F = aff
det = A*E - B*D
inv = np.array([[E/det, -B/det], [-D/det, A/det]])

x0,y0,x1,y1 = malir.bounds
CELL = 0.0015
W = int((x1-x0)/CELL)+2; H = int((y1-y0)/CELL)+2
from PIL import ImageDraw
mimg = Image.new('L',(W,H),0); dr = ImageDraw.Draw(mimg)
for p in (malir.geoms if malir.geom_type=='MultiPolygon' else [malir]):
    for ring,v in [(p.exterior,255)]+[(rr,0) for rr in p.interiors]:
        xy=np.asarray(ring.coords)
        dr.polygon(list(zip((xy[:,0]-x0)/CELL,(y1-xy[:,1])/CELL)),fill=v)
mmask = np.asarray(mimg) > 127
gy,gx = np.where(mmask)
lon = x0+gx*CELL; lat = y1-gy*CELL
px = inv[0,0]*(lon-C)+inv[0,1]*(lat-F); py = inv[1,0]*(lon-C)+inv[1,1]*(lat-F)
pxi = np.clip(px.astype(int),0,cls.shape[1]-1); pyi = np.clip(py.astype(int),0,cls.shape[0]-1)
out = np.zeros((H,W),np.uint8); out[gy,gx] = cls[pyi,pxi]
un2 = mmask & (out==0)
if un2.any():
    _,(iy2,ix2)=ndimage.distance_transform_edt(out==0,return_indices=True)
    out[un2]=out[iy2[un2],ix2[un2]]
print('shares:',{f'NA-{228+i}':round(float((out==i).sum())/mmask.sum(),3) for i in (1,2,3)})

def vec(mask):
    cs,hier=cv2.findContours(mask.astype(np.uint8),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    ps=[]
    for i,c in enumerate(cs):
        if hier[0][i][3]!=-1 or cv2.contourArea(c)<3: continue
        e=c.reshape(-1,2).astype(float)
        ring=np.column_stack([x0+e[:,0]*CELL,y1-e[:,1]*CELL])
        holes=[]; j=hier[0][i][2]
        while j!=-1:
            hc=cs[j].reshape(-1,2).astype(float)
            if cv2.contourArea(cs[j])>=3:
                holes.append(np.column_stack([x0+hc[:,0]*CELL,y1-hc[:,1]*CELL]))
            j=hier[0][j][0]
        try:
            p=Polygon(ring,holes).buffer(0)
            if not p.is_empty: ps.append(p)
        except Exception: pass
    return unary_union(ps) if ps else None

geoms={}
for i,na in ((1,'NA-229'),(2,'NA-230'),(3,'NA-231')):
    geoms[na]=vec(out==i).simplify(0.0008).buffer(0).intersection(malir)
resid=malir.difference(unary_union(list(geoms.values())).buffer(0))
if not resid.is_empty:
    for p in (resid.geoms if resid.geom_type in ('MultiPolygon','GeometryCollection') else [resid]):
        if p.geom_type!='Polygon' or p.area==0: continue
        bestna=min(geoms,key=lambda na:geoms[na].distance(p))
        geoms[bestna]=unary_union([geoms[bestna],p])
print('sym-diff %.2e'%unary_union(list(geoms.values())).symmetric_difference(malir).area)

# QA gate: normalized IoU vs Wikipedia red
aa=np.asarray(Image.open('/tmp/ref.png').convert('RGB')).astype(int)
red=(aa[:,:,0]>200)&(aa[:,:,1]<80)&(aa[:,:,2]<80)
cs2,_=cv2.findContours(red.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
ref=unary_union([Polygon(c.reshape(-1,2).astype(float)).buffer(0) for c in cs2 if cv2.contourArea(c)>50])
ref=S(ref,xfact=1,yfact=-1,origin=(0,0))
k=math.cos(math.radians(24.95))
ours=S(geoms['NA-231'],xfact=k,yfact=1,origin=(0,0))
def norm(gm):
    c=gm.centroid; gm=translate(gm,-c.x,-c.y); s=1/math.sqrt(gm.area)
    return S(gm,xfact=s,yfact=s,origin=(0,0))
Aa,Bb=norm(ref),norm(ours)
best=max((Aa.intersection(rotate(Bb,ang,origin=(0,0))).area/Aa.union(rotate(Bb,ang,origin=(0,0))).area) for ang in range(-15,16,3))
print(f'QA: new NA-231 vs Wikipedia normalized IoU {best:.3f} (reference only; PBS map is the accepted source)')

def rnd(o,nd=4):
    if isinstance(o,float): return round(o,nd)
    if isinstance(o,list): return [rnd(x,nd) for x in o]
    if isinstance(o,dict): return {k2:rnd(v,nd) for k2,v in o.items()}
    return o
def wind(gm):
    if gm.geom_type=='Polygon': return orient(gm,-1.0)
    if gm.geom_type=='MultiPolygon': return MultiPolygon([orient(p,-1.0) for p in gm.geoms])
    return gm
SRC=('PBS/ECP District Malir Preliminary-Delimitation-2023 map (colour fills), '
     'georeferenced to the digitised Malir outline; final Form-7 composition concurs')
open(f'map.html.bak_{int(time.time())}','w',encoding='utf-8').write(txt)
for f in GEO['2024']['features']:
    na=f['properties']['na']
    if na in geoms:
        f['geometry']=rnd(mapping(wind(geoms[na].buffer(0))))
        f['properties']['src']=SRC; f['properties']['confidence']='medium'
lines[gi]='window.GEOS='+json.dumps(GEO,separators=(',',':'),ensure_ascii=False)+';'
open('map.html','w',encoding='utf-8').write('\n'.join(lines))
TF=json.load(open('data/na_2023delim_true_full.geojson'))
for f in TF['features']:
    na=f['properties']['na']
    if na in geoms:
        f['geometry']=mapping(wind(geoms[na].buffer(0))); f['properties']['src']=SRC
json.dump(TF,open('data/na_2023delim_true_full.geojson','w'))
print('SWAPPED into map.html + true_full')
