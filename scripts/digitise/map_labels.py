#!/usr/bin/env python3
"""
Read the NA labels printed on the labelled Commons election maps (1990, 1993,
1997) exactly, without OCR.

The labels are set in a 9-px bitmap font of 13 glyphs (N, A, hyphen, 0-9) with
1-px strokes, and every glyph is a separate ink component, so each one is
looked up in a table. This reads all 210 labels on each of the three maps;
NA-39 wraps onto two lines and is joined.

    from map_labels import read_labels
    words = read_labels(rgb_array)   # [{'na', 'text', 'bbox', 'cx', 'cy'}, ...]
"""
import re
import numpy as np
from scipy import ndimage

# 9 px tall, 1 px strokes. Identical on the 1990, 1993 and 1997 maps.
FONT = {
    'N': ['##...###', '.#....#.', '.##...#.', '.#.#..#.', '.#..#.#.', '.#..#.#.', '.#...##.', '.#....#.', '###...#.'],
    'A': ['....#....', '....#....', '...#.#...', '...#.#...', '..#...#..', '..#####..', '.#.....#.', '.#.....#.', '###...###'],
    '-': ['##'],
    '1': ['.#.', '##.', '.#.', '.#.', '.#.', '.#.', '.#.', '.#.', '###'],
    '2': ['.###.', '#...#', '....#', '....#', '...#.', '...#.', '..#..', '.#..#', '#####'],
    '3': ['.###.', '#...#', '....#', '...#.', '..##.', '....#', '....#', '....#', '####.'],
    '4': ['....#.', '...##.', '..#.#.', '..#.#.', '.#..#.', '#...#.', '######', '....#.', '....#.'],
    '5': ['..###', '..#..', '.##..', '...#.', '....#', '....#', '....#', '...#.', '###..'],
    '6': ['..###', '.#...', '#....', '#.##.', '##..#', '#...#', '#...#', '#...#', '.###.'],
    '7': ['#####', '#...#', '...#.', '...#.', '...#.', '..#..', '..#..', '..#..', '.#...'],
    '8': ['.###.', '#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#', '.###.'],
    '9': ['.###.', '#...#', '#...#', '#...#', '#...#', '.####', '...#.', '..#..', '##...'],
    '0': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
}
_GLYPH = {}
for ch, rows in FONT.items():
    bm = np.array([[c == '#' for c in r] for r in rows])
    _GLYPH[(bm.shape, bm.tobytes())] = ch


def read_labels(a):
    """Every 'NA-nnn' printed on the map, with its pixel box."""
    ink = a.sum(2) < 200
    lab, n = ndimage.label(ink, structure=np.ones((3, 3)))
    gl = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h > 12 or w > 10:
            continue
        bm = lab[sl] == i
        ch = _GLYPH.get((bm.shape, bm.tobytes()))
        if ch:
            gl.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, ch))
    words = []
    for g in gl:
        if g[4] != 'N':
            continue
        x0, y0, x1, y1, _ = g
        seq = [g]
        while True:
            last = seq[-1]
            nxt = [h for h in gl if last[2] - 1 <= h[0] <= last[2] + 3
                   and y0 - 1 <= h[1] <= y0 + 6 and h is not last]
            if not nxt:
                break
            seq.append(min(nxt, key=lambda h: h[0]))
        text = ''.join(h[4] for h in seq)
        if text == 'NA-':
            # label wrapped onto two lines in a narrow seat (NA-39 on all
            # three maps): take the digits set on the next line down
            below = sorted([h for h in gl if h[4].isdigit() and y0 + 10 <= h[1] <= y0 + 14
                            and x0 - 6 <= h[0] <= seq[-1][2] + 6], key=lambda h: h[0])
            if below:
                seq += below
                text += ''.join(h[4] for h in below)
        m = re.fullmatch(r'NA-(\d{1,3})', text)
        bx = (min(h[0] for h in seq), min(h[1] for h in seq),
              max(h[2] for h in seq), max(h[3] for h in seq))
        words.append({'text': text, 'na': f'NA-{int(m.group(1))}' if m else None,
                      'bbox': bx, 'cx': (bx[0] + bx[2]) / 2, 'cy': (bx[1] + bx[3]) / 2})
    return words
