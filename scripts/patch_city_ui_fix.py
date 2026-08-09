#!/usr/bin/env python3
"""
UX fixes for the city-zoom feature:
  1. move the city chips OUT of the map overlay (they covered northern Pakistan
     on the default view) and INTO the toolbar, restyled as an inline group
  2. Escape key resets the zoom to the whole country
Asserts + backup.
"""
import time

MAP = 'map.html'
txt = open(MAP, encoding='utf-8').read()
open(f'{MAP}.bak_{int(time.time())}', 'w', encoding='utf-8').write(txt)

def sub1(old, new):
    global txt
    assert txt.count(old) == 1, f'want 1, got {txt.count(old)}: {old[:70]}'
    txt = txt.replace(old, new)

# 1a. restyle .citybtns (overlay -> inline toolbar group)
sub1(".citybtns{position:absolute;top:16px;right:16px;display:flex;flex-wrap:wrap;gap:4px;"
     "max-width:250px;justify-content:flex-end;z-index:2}",
     ".citybtns{display:flex;flex-wrap:wrap;align-items:center;gap:4px}")
sub1(".citybtns .clab{width:100%;text-align:right;font-size:9.5px;letter-spacing:.05em;"
     "text-transform:uppercase;color:var(--ink-3);margin-bottom:1px}",
     ".citybtns .clab{font-size:10px;letter-spacing:.05em;text-transform:uppercase;"
     "color:var(--ink-3);margin-right:2px}")

# 1b. remove the overlay div from the map-card
sub1('<button id="zreset">⌂</button></div>\n      <div class="citybtns" id="citybtns"></div>',
     '<button id="zreset">⌂</button></div>')

# 1c. add the chips into the toolbar, after the mode-note
sub1('<div class="mode-note" id="modenote"></div>',
     '<div class="mode-note" id="modenote"></div>\n    <div class="citybtns" id="citybtns"></div>')

# 2. Escape resets the zoom (ignored while typing in a field)
ANCHOR = ("all.onclick=()=>svg.transition().duration(650).call(zoom.transform,d3.zoomIdentity);"
          "el.appendChild(all);})();")
sub1(ANCHOR, ANCHOR +
     "\nwindow.addEventListener('keydown',e=>{if(e.key!=='Escape')return;"
     "const a=document.activeElement;if(a&&/INPUT|SELECT|TEXTAREA/.test(a.tagName))return;"
     "svg.transition().duration(500).call(zoom.transform,d3.zoomIdentity);});")

open(MAP, 'w', encoding='utf-8').write(txt)
print('city chips moved to toolbar; Escape-to-reset added;', len(txt) // 1024, 'KB')
