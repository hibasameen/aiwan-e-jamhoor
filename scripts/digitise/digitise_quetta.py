#!/usr/bin/env python3
"""Sheet-digitise the Quetta 3-seat canvas from the ECP representation sheet
(Muhammad Mobeen Khilji, NA-262/263/264). Yellow=NA-262, blue=NA-263, green=NA-264;
populations printed on the sheet: 890,833 / 819,201 / 885,458 (total 2,595,492 =
Quetta district 2023 census, confirming all three seats are Quetta-only)."""
import sys, json, os
sys.path.insert(0, '/root/aiwan/scripts')
import numpy as np, cv2
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import make_valid
from split_district_by_sheet import load_small, fit_outline

BASE='/root/aiwan'
SHEET=f'{BASE}/sheets/bal/quetta_na262_264.jpg'
cv_=json.load(open(f'{BASE}/data/digitised/canvases_2023.geojson'))
canvas=[make_valid(shape(f['geometry']).buffer(0)) for f in cv_['features']
        if f['properties']['canvas_id']=='C105_Quetta'][0]

img=load_small(SHEET, 3000)
H,W=img.shape[:2]
img=img[int(.03*H):int(.99*H), int(.20*W):]          # drop the legend box (top-left)
hsv=cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
h,s,v=[hsv[...,i].astype(int) for i in range(3)]

MASKS={
 'NA-262': (h>=20)&(h<=38)&(s>90)&(v>120),                 # yellow
 'NA-263': (h>=95)&(h<=125)&(s>70)&(v>90),                 # blue
 'NA-264': (h>=45)&(h<=90)&(s>40)&(v>90),                  # green
}
def clean(m):
    m=cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9,9),np.uint8))
    m=cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
    if n<=1: return m
    big=st[1:,cv2.CC_STAT_AREA].max()
    keep=np.zeros_like(m)
    for i in range(1,n):
        if st[i,cv2.CC_STAT_AREA]>=max(2500,0.05*big): keep[lab==i]=1
    return keep
M={k:clean(m) for k,m in MASKS.items()}
for k,m in M.items(): print(f'  {k} mask px {m.sum():,} ({m.sum()/m.size:.1%} of sheet)')
union=np.clip(sum(M.values()),0,1).astype(np.uint8)
union=cv2.morphologyEx(union, cv2.MORPH_CLOSE, np.ones((25,25),np.uint8))
print(f'  union {union.sum():,} px')

px_to_metric,(KX,KY),rms = fit_outline(union, canvas)
print('fit rms (km):', round(rms,3))

# map every masked pixel to lon/lat, nearest-label a dense grid over the canvas
ys,xs=np.nonzero(union)
lab=np.empty(len(xs),dtype=object)
for k,m in M.items(): lab[m[ys,xs]>0]=k
ok=lab!=None
pts=np.column_stack([xs[ok],ys[ok]]).astype(float)
lab=lab[ok]
ll=px_to_metric(pts); ll=np.column_stack([ll[:,0]/KX, ll[:,1]/KY])
from scipy.spatial import cKDTree
tree=cKDTree(ll)

x0,y0,x1,y1=canvas.bounds
res=0.0018
gx=np.arange(x0,x1,res); gy=np.arange(y0,y1,res)
GX,GY=np.meshgrid(gx,gy); G=np.column_stack([GX.ravel(),GY.ravel()])
from shapely import contains_xy
keep=contains_xy(canvas,G[:,0],G[:,1]); G=G[keep]
_,idx=tree.query(G); L=lab[idx]
# contiguity repair (constituencies are contiguous by law); kills nearest-label speckle
sys.path.insert(0,'/root/aiwan/scripts')
from compose_kp_bal_ict import repair_contiguity
L,moved = repair_contiguity(G, np.array(L,dtype=object), res, tol=0.15)
print('contiguity repair moved', moved, 'cells')

from shapely.geometry import box
out={}
half=res/2
for k in M:
    sel=G[L==k]
    if not len(sel): continue
    g=unary_union([box(x-half,y-half,x+half,y+half) for x,y in sel])
    out[k]=make_valid(g.buffer(res*.01).buffer(-res*.01)).intersection(canvas)
resid=canvas.difference(unary_union(list(out.values())))
if not resid.is_empty and resid.area>0:
    parts=list(resid.geoms) if hasattr(resid,'geoms') else [resid]
    for p in parts:
        if p.area<=0: continue
        b=min(out,key=lambda s:out[s].distance(p)); out[b]=make_valid(unary_union([out[b],p]))

sheet_share={k:M[k].sum()/union.sum() for k in M}
print('\nseat        sheet%   output%   pop-share(sheet)')
POP={'NA-262':890833,'NA-263':819201,'NA-264':885458}
tp=sum(POP.values())
for k in sorted(out):
    print(f'{k}   {sheet_share[k]*100:7.1f} {out[k].area/canvas.area*100:9.1f} {POP[k]/tp*100:12.1f}')
feats=[dict(type='Feature',properties=dict(na=k,canvas_id='C105_Quetta',
        src='sheet-split: Mobeen Khilji NA-262,263,264 Quetta, outline-fit',
        approx=False,confidence='high',method='colour-mask + outline ICP/TPS fit',
        rms_km=round(rms,3) if rms is not None else None),
        geometry=mapping(out[k])) for k in sorted(out)]
json.dump(dict(type='FeatureCollection',features=feats), open(f'{BASE}/out/kpbal/quetta_sheet.geojson','w'))
print('\nwrote out/kpbal/quetta_sheet.geojson')
