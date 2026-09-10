#!/usr/bin/env python3
"""map.html: a page heading in the site's own design.

The September 2026 SEO pass gave the map an inline-styled <h1> that pointed at
the generated /elections/ archive; the archive is gone and so is that block.
This puts back what search engines (and screen readers) need — an <h1> and a
one-paragraph description — using the kicker / h1 / lede pattern the other
pages share, sized down so the map stays above the fold.
Usage: python3 scripts/patches/patch_map_heading.py [repo root]
"""
import sys, pathlib
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
p = ROOT / 'map.html'
t = p.read_text(encoding='utf-8')
if 'class="page-head"' in t:
    print('map already patched'); sys.exit(0)

CSS_ANCHOR = '.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:14px;margin-bottom:14px}\n'
CSS_NEW = CSS_ANCHOR + (
    '.page-head{margin:2px 0 18px}\n'
    ".page-head .kicker{font-family:'Space Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}\n"
    ".page-head h1{font-family:'EB Garamond',serif;font-weight:500;font-size:32px;line-height:1.12;margin:4px 0 4px}\n"
    ".page-head h1 .ur{font-family:'Noto Nastaliq Urdu',serif;font-size:21px;color:var(--gold);margin-inline-start:10px}\n"
    '.page-head .lede{font-size:15px;line-height:1.55;color:var(--ink-2);margin:0;max-width:78ch;text-wrap:pretty}\n'
    '@media (max-width:720px){.page-head h1{font-size:26px}.page-head h1 .ur{font-size:17px}.page-head .lede{font-size:14px}}\n'
)
HTML_ANCHOR = '<main>\n  <div class="toolbar">\n'
HTML_NEW = (
    '<main>\n'
    '  <div class="page-head">\n'
    '    <div class="kicker">Constituency results · National Assembly · 1977 – 2024</div>\n'
    '    <h1>Constituency Results<span class="ur">حلقہ وار نتائج</span></h1>\n'
    '    <p class="lede">Every National Assembly general election since 1977 — eleven of them — drawn on the constituency boundaries in force at the time. Pick a year, click a seat for the full candidate list and its history on the ground, or search by seat number. The address keeps the year and seat, so a view can be shared.</p>\n'
    '  </div>\n'
    '  <div class="toolbar">\n'
)
for a, name in ((CSS_ANCHOR, 'toolbar css'), (HTML_ANCHOR, 'main/toolbar html')):
    n = t.count(a)
    if n != 1:
        raise SystemExit(f'anchor {name!r} matched {n} times, expected 1')
t = t.replace(CSS_ANCHOR, CSS_NEW).replace(HTML_ANCHOR, HTML_NEW)
p.write_text(t, encoding='utf-8')
print('map patched')
