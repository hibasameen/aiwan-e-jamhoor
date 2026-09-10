#!/usr/bin/env python3
"""Header shell: keep the nav on one line, identically on every page.

Before: nav links and the wordmark could break inside themselves whenever the
row ran short (Home/Constituency Results at laptop widths, because those two
pages also carry the 190px seat search), and the two-row layout only kicked
in at 1040px.

After: brand, nav and tools never shrink or wrap internally; <=1360px the row
tightens (gap 16, link padding 10, search 160px with a shorter placeholder);
<=1200px the existing two-row layout (brand + tools, nav on its own scrolling
row) takes over on all seven pages. Chromium's datalist dropdown arrow is
hidden on the header search (and it is 200px) so the placeholder is not clipped.
Every anchor must match exactly once or the file is left untouched.
Usage: python3 scripts/patches/patch_header_shell.py [repo root]
"""
import sys, pathlib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
PAGES = ['index', 'map', 'house', 'candidates', 'islam', 'method', 'about']

A_TOOLS = '.hdr-tools{display:flex;align-items:center;gap:8px}\n'
NEW_BASE = (
    '.brand{flex:none}.brand .wm{white-space:nowrap}\n'
    'nav.main{flex:none}nav.main a{white-space:nowrap}\n'
    '.hdr-tools{flex:none}.hdr-tools .hdr-search{width:200px}.hdr-search::-webkit-calendar-picker-indicator,.hdr-search::-webkit-search-cancel-button{-webkit-appearance:none;display:none}\n'
    '@media (max-width:1360px){.shell-in{gap:16px}nav.main a{padding:8px 10px}.hdr-tools .hdr-search{width:160px}}\n'
)
A_MQ_OLD = '/* ---- shared responsive header (identical on every page) ---- */\n@media (max-width:1040px){\n'
A_MQ_NEW = '/* ---- shared responsive header (identical on every page) ---- */\n@media (max-width:1200px){\n'
A_1040 = '  .brand{order:1} .hdr-tools{order:2;margin-left:auto} .spacer{display:none}\n'
NEW_1040 = A_1040 + '  .hdr-tools .hdr-search{width:200px}\n'
HOUSE_NAV_OLD = 'nav.main{display:flex;gap:2px;margin-left:6px;flex-wrap:wrap}\n'
HOUSE_NAV_NEW = 'nav.main{display:flex;gap:2px;margin-left:6px}\n'
PH_JS = ("<script>(function(){var i=document.querySelector('.hdr-search');if(!i)return;"
         "var m=matchMedia('(max-width:1360px) and (min-width:1200.02px)'),"
         "f=function(){i.placeholder=m.matches?'e.g. NA-127':'Seat, e.g. NA-127'};"
         "f();if(m.addEventListener)m.addEventListener('change',f);else m.addListener(f);})();</script>\n")

def once(text, needle, name, page):
    n = text.count(needle)
    if n != 1:
        raise SystemExit(f'{page}: anchor {name!r} matched {n} times, expected 1')

for pg in PAGES:
    p = ROOT / f'{pg}.html'
    t = p.read_text(encoding='utf-8')
    if '.brand{flex:none}' in t:
        print(pg, 'already patched'); continue
    once(t, A_TOOLS, 'hdr-tools', pg); once(t, A_MQ_OLD, 'shared header mq', pg); once(t, A_1040, 'mq body', pg)
    t = t.replace(A_TOOLS, A_TOOLS + NEW_BASE)
    t = t.replace(A_MQ_OLD, A_MQ_NEW)
    t = t.replace(A_1040, NEW_1040)
    if pg == 'house':
        once(t, HOUSE_NAV_OLD, 'house nav', pg)
        t = t.replace(HOUSE_NAV_OLD, HOUSE_NAV_NEW)
    if 'class="hdr-search"' in t:
        once(t, '</body>', 'body end', pg)
        t = t.replace('</body>', PH_JS + '</body>')
    p.write_text(t, encoding='utf-8')
    print(pg, 'patched')
