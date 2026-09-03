#!/usr/bin/env python3
"""
Segment a labelled Commons election map into constituency regions, then OCR the
NA number printed inside each one.

Regions are flat-filled and separated by dark borders, so connected components
of near-uniform colour give the constituencies. The printed label is the join
key, so no georeferencing is needed to compare against our own results.
"""
import sys, re, json, collections
import numpy as np
from PIL import Image
from scipy import ndimage
import pytesseract

DARK = 200          # sum(rgb) below this is border / text / background

def quantise(a, step=24):
    return (a.astype(int) // step * step).astype(np.uint8)

def segment(path, min_area=160):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im)
    H, W = a.shape[:2]
    lum = a.astype(int).sum(2)
    ink = lum < DARK                      # borders, text, black background
    q = quantise(a)
    key = (q[:, :, 0].astype(np.int32) << 16) | (q[:, :, 1].astype(np.int32) << 8) | q[:, :, 2]
    key[ink] = -1

    regions = []
    for colour in np.unique(key):
        if colour < 0: continue
        m = key == colour
        if m.sum() < min_area: continue
        lab, n = ndimage.label(m)
        for i, sl in enumerate(ndimage.find_objects(lab), start=1):
            comp = (lab[sl] == i)
            area = int(comp.sum())
            if area < min_area: continue
            ys, xs = sl
            cols = a[sl][comp]
            regions.append({'bbox': (xs.start, ys.start, xs.stop, ys.stop),
                            'area': area, 'mask_slice': sl, 'comp': comp,
                            'fill': np.median(cols, axis=0).astype(int)})
    return im, a, ink, regions

def ocr_region(a_int, r, scale=6):
    x0, y0, x1, y1 = r['bbox']
    sub = a_int[y0:y1, x0:x1]
    fill = r['fill']
    d = np.abs(sub - fill).sum(2)
    fillmask = d <= 90
    filled = ndimage.binary_fill_holes(fillmask)
    darker = sub.sum(2) < fill.sum() - 40
    base = (d > 60) & darker
    for ero in (3, 2, 1, 0):
        interior = ndimage.binary_erosion(filled, iterations=ero) if ero else filled
        txt = base & interior
        if txt.sum() < 12: continue
        ys, xs = np.where(txt)
        crop = txt[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3]
        if crop.size == 0 or min(crop.shape) < 3: continue
        for thick in (0, 1):
            c = ndimage.binary_dilation(crop, iterations=thick) if thick else crop
            img = Image.fromarray(np.where(c, 0, 255).astype('uint8'))
            for sc in (scale, scale + 4):
                big = img.resize((img.size[0] * sc, img.size[1] * sc), Image.LANCZOS)
                for psm in (7, 11, 6, 13):
                    t = pytesseract.image_to_string(
                        big, config=f'--psm {psm} -c tessedit_char_whitelist=NA-0123456789')
                    t = t.strip().replace(' ', '').replace('\n', '')
                    m = re.search(r'NA[-\u2013\u2014]?(\d{1,3})', t)
                    if m:
                        n_ = int(m.group(1))
                        if 1 <= n_ <= 300: return n_
    return None

def main(path, expect_max=207):
    im, a, ink, regions = segment(path)
    a_int = a.astype(int)
    regions.sort(key=lambda r: -r['area'])
    print(f'{path.split("/")[-1]}  {im.size[0]}x{im.size[1]}  regions>=400px: {len(regions)}')
    out, unread = {}, 0
    for r in regions:
        na = ocr_region(a_int, r)
        x0, y0, x1, y1 = r['bbox']
        comp = r['comp']
        col = tuple(int(v) for v in r['fill'])
        rec = {'hex': '#%02x%02x%02x' % col, 'area': r['area'],
               'cx': (x0 + x1) // 2, 'cy': (y0 + y1) // 2}
        if na is None:
            unread += 1; continue
        k = f'NA-{na}'
        if k not in out or r['area'] > out[k]['area']:
            out[k] = rec
    nums = sorted(int(k.split('-')[1]) for k in out)
    print(f'  labels read : {len(out)}   (regions with no readable label: {unread})')
    if nums:
        gaps = [n for n in range(1, expect_max + 1) if n not in nums]
        extra = [n for n in nums if n > expect_max]
        print(f'  range       : NA-{nums[0]}..NA-{nums[-1]}')
        print(f'  missing     : {len(gaps)} {gaps[:30]}{"..." if len(gaps)>30 else ""}')
        print(f'  above {expect_max}   : {extra[:10]}')
    cols = collections.Counter(v['hex'] for v in out.values())
    print(f'  fill colours: {len(cols)} | {cols.most_common(10)}')
    name = path.split('/')[-1].rsplit('.', 1)[0]
    json.dump(out, open(f'/home/claude/{name}_read.json', 'w'), indent=0)
    return out

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 207)
