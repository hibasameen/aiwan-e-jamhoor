#!/usr/bin/env python3
"""
Add "zoom to city" chips to the map: Karachi, Lahore, Islamabad-Rawalpindi,
Faisalabad, Peshawar, Quetta, plus a Whole-country reset. Each flies the existing
d3 zoom to a fixed geographic box, so it works for every election year regardless
of that year's NA numbering. Asserts + backup.
"""
import time

MAP = 'map.html'
txt = open(MAP, encoding='utf-8').read()
open(f'{MAP}.bak_{int(time.time())}', 'w', encoding='utf-8').write(txt)

def sub1(old, new):
    global txt
    assert txt.count(old) == 1, f'want 1, got {txt.count(old)}: {old[:70]}'
    txt = txt.replace(old, new)

# 1. CSS (after the .delim rule)
DELIM_CSS = (".delim{position:absolute;bottom:14px;left:16px;font-size:11.5px;color:var(--ink-3);"
             "background:var(--surface);padding:4px 8px;border:1px solid var(--line-2);border-radius:2px}")
CITY_CSS = ("\n.citybtns{position:absolute;top:16px;right:16px;display:flex;flex-wrap:wrap;gap:4px;"
            "max-width:250px;justify-content:flex-end;z-index:2}"
            "\n.citybtns .clab{width:100%;text-align:right;font-size:9.5px;letter-spacing:.05em;"
            "text-transform:uppercase;color:var(--ink-3);margin-bottom:1px}"
            "\n.citybtns button{border:1px solid var(--line);background:var(--surface);color:var(--ink-2);"
            "font:600 11px Archivo,sans-serif;padding:5px 9px;border-radius:2px;cursor:pointer}"
            "\n.citybtns button:hover{background:var(--ink);color:var(--page)}")
sub1(DELIM_CSS, DELIM_CSS + CITY_CSS)

# 2. HTML container (after the zoombtns div)
ZOOMBTNS = ('<div class="zoombtns" id="zoombtns"><button id="zin">+</button>'
            '<button id="zout">−</button><button id="zreset">⌂</button></div>')
sub1(ZOOMBTNS, ZOOMBTNS + '\n      <div class="citybtns" id="citybtns"></div>')

# 3. JS: cities + zoomCity + build chips (after the zreset handler)
ZRESET = "document.getElementById('zreset').onclick=()=>svg.transition().call(zoom.transform,d3.zoomIdentity);"
CITY_JS = ZRESET + """
const CITIES=[['Karachi',[66.55,24.70,67.67,25.74]],['Lahore',[73.92,31.17,74.74,31.82]],
['Islamabad–Rawalpindi',[72.54,32.97,73.73,34.12]],['Faisalabad',[72.60,30.57,73.78,31.89]],
['Peshawar',[71.17,33.53,71.95,34.42]],['Quetta',[66.14,29.71,67.53,30.57]]];
function zoomCity(b){paths(state.year);const gp=projs[YEARS[state.year].geo];if(!gp)return;
  const pj=gp.projection(),p0=pj([b[0],b[3]]),p1=pj([b[2],b[1]]);
  const bw=Math.abs(p1[0]-p0[0])||1,bh=Math.abs(p1[1]-p0[1])||1;
  const cx=(p0[0]+p1[0])/2,cy=(p0[1]+p1[1])/2;
  const k=Math.max(1,Math.min(14,0.9*Math.min(W/bw,H/bh)));
  svg.transition().duration(650).call(zoom.transform,
    d3.zoomIdentity.translate(W/2,H/2).scale(k).translate(-cx,-cy));}
(function(){const el=document.getElementById('citybtns');if(!el)return;
  const lab=document.createElement('span');lab.className='clab';lab.textContent='Zoom to city';el.appendChild(lab);
  CITIES.forEach(c=>{const btn=document.createElement('button');btn.textContent=c[0];
    btn.setAttribute('aria-label','Zoom to '+c[0]);btn.onclick=()=>zoomCity(c[1]);el.appendChild(btn);});
  const all=document.createElement('button');all.textContent='Whole country';
  all.onclick=()=>svg.transition().duration(650).call(zoom.transform,d3.zoomIdentity);el.appendChild(all);})();"""
sub1(ZRESET, CITY_JS)

# 4. hide the chips in table mode, alongside the zoom buttons
TOGGLE = "document.getElementById('zoombtns').style.display=state.tableMode?'none':'flex';"
sub1(TOGGLE, TOGGLE +
     "\n  {const cb=document.getElementById('citybtns');if(cb)cb.style.display=state.tableMode?'none':'flex';}")

open(MAP, 'w', encoding='utf-8').write(txt)
print('city-zoom chips added; map.html', len(txt) // 1024, 'KB')
