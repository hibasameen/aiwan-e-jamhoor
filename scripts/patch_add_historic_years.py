#!/usr/bin/env python3
"""
Surgically add the pre-2002 elections (1977, 1985, 1988) to map.html and switch
1990/1993/1997 onto the reconstructed 207-seat boundaries.

- window.RESULTS  += 1977/1985/1988 (parsed JSON blob, merged, re-dumped)
- window.GEOS     += '200seat' (1977) and '207seat' (1985-1997) reconstructed FCs
- PARTY_CAT/COLORS/CAT_ORDER += historic parties (PNA, PML-J, IJM, PAI, ...)
- YEARS: add 1977/1985/1988; repoint 1990/1993/1997 to geo:'207seat', drop unit:'proj'
- YL: prepend 1977/1985/1988
- ELEC: add 1977/1985/1988 context cards

Every edit is asserted to occur exactly once. A timestamped backup is written first.
"""
import json, re, time, sys

MAP = 'map.html'
INJ = json.load(open('data/_map_inject/results_historic.json'))
RES_NEW, STATS = INJ['RESULTS'], INJ['STATS']

def rnd(o, nd=4):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list):  return [rnd(x, nd) for x in o]
    if isinstance(o, dict):  return {k: rnd(v, nd) for k, v in o.items()}
    return o

def load_geo(path, seats):
    gj = json.load(open(path))
    for f in gj['features']:
        n = int(f['properties']['na'].split('-')[1])
        prov = ('Khyber Pakhtunkhwa' if n <= 26 else 'FATA' if n <= 34 else
                'Islamabad Capital Territory' if n == 35 else 'Punjab' if n <= 150 else
                ('Sindh' if n <= (193 if seats == 200 else 196) else 'Balochistan'))
        f['properties'] = {'na': f['properties']['na'], 'prov': prov,
                           'dist': f['properties'].get('dist', ''), 'approx': True}
        f['geometry'] = rnd(f['geometry'])
    return gj

GEO200 = load_geo('data/boundaries/na_200seat_1977_reconstructed.geojson', 200)
GEO207 = load_geo('data/boundaries/na_207seat_1985-1997_reconstructed.geojson', 207)

txt = open(MAP, encoding='utf-8').read()
open(f'{MAP}.bak_{int(time.time())}', 'w', encoding='utf-8').write(txt)
lines = txt.split('\n')

def edit_blob(idx, prefix, mutate):
    line = lines[idx]
    assert line.startswith(prefix) and line.endswith(';'), f'line {idx+1} shape unexpected'
    obj = json.loads(line[len(prefix):-1])
    mutate(obj)
    lines[idx] = prefix + json.dumps(obj, separators=(',', ':'), ensure_ascii=False) + ';'

# --- RESULTS (line 206, idx 205) ---
def add_results(R):
    for y in ('1977', '1985', '1988'):
        R[y] = RES_NEW[y]
edit_blob(205, '<script>window.RESULTS=', add_results)

# --- GEOS (line 207, idx 206) ---
def add_geos(G):
    G['200seat'] = GEO200
    G['207seat'] = GEO207
edit_blob(206, 'window.GEOS=', add_geos)

txt = '\n'.join(lines)

def sub1(old, new):
    assert txt.count(old) == 1, f'expected 1 occurrence, found {txt.count(old)}:\n  {old[:90]}'
    return txt.replace(old, new)

# --- PARTY_CAT additions ---
txt = sub1("'PML-N':'PML-N'};",
  "'PML-N':'PML-N',"
  "'PNA':'PNA','Pakistan National Alliance':'PNA',"
  "'PML-J':'PML-J','Pakistan Muslim League (Junejo)':'PML-J',"
  "'IJM':'IJM','Islami Jamhoori Mahaz':'IJM',"
  "'PAI':'PAI','Pakistan Awami Ittehad':'PAI',"
  "'BNP':'BNP','JWP':'JWP','PPP-SB':'PPP-SB'};")

# --- COLORS additions ---
txt = sub1("'Other':'#00a3c7'};",
  "'PNA':'#2a7d6f','PML-J':'#6bbf59','IJM':'#c98500','PAI':'#8a6d1a',"
  "'BNP':'#5b7ba6','JWP':'#7d6bbf','PPP-SB':'#5a5a5a','Other':'#00a3c7'};")

# --- CAT_ORDER additions ---
txt = sub1(",'Other'];",
  ",'PNA','PML-J','IJM','PAI','BNP','JWP','PPP-SB','Other'];")

# --- YEARS: repoint the 1990s ---
D97 = "1985–1997 delimitation · reconstructed (approx)"
for yr, prev in (('1990', '1988'), ('1993', '1990'), ('1997', '1993')):
    old = ("'%s':{geo:'2002',delim:'2002 boundaries · 1990s district results',"
           "seats:207,postponed:[],prev:null,unit:'proj'}" % yr)
    new = "'%s':{geo:'207seat',delim:'%s',seats:207,postponed:[],prev:'%s'}" % (yr, D97, prev)
    txt = sub1(old, new)

# --- YEARS: add the three new years at the front ---
new_years = (
 "'1977':{geo:'200seat',delim:'1977 delimitation · reconstructed (approx)',seats:200,postponed:[],prev:null},"
 "'1985':{geo:'207seat',delim:'1985 non-party · 207-seat delim · reconstructed (approx)',seats:207,postponed:[],prev:null},"
 "'1988':{geo:'207seat',delim:'%s',seats:207,postponed:[],prev:'1985'}," % D97)
txt = sub1("const YEARS={'1990'", "const YEARS={" + new_years + "'1990'")

# --- YL: prepend ---
txt = sub1("const YL=['1990','1993','1997','2002','2008','2013','2018','2024'];",
           "const YL=['1977','1985','1988','1990','1993','1997','2002','2008','2013','2018','2024'];")

# --- ELEC: add three context cards ---
def elec(year, date, turnout, summary):
    s = STATS[year]
    return (f'"{year}":{{"date":{json.dumps(date)},"polled":{json.dumps(s["polled"])},'
            f'"postponed":"","turnout":{json.dumps(turnout)},"cands":{json.dumps(s["cands"])},'
            f'"tight":{json.dumps(s["tight"])},"summary":{json.dumps(summary)},"quotes":[]}}')

e1977 = elec('1977', '7 March 1977', '63%',
  "Zulfikar Ali Bhutto's PPP won a sweeping majority, but the opposition Pakistan National Alliance "
  "alleged systematic rigging and launched a mass protest movement. On 5 July 1977 the army chief "
  "General Zia-ul-Haq seized power and imposed martial law; Bhutto was later tried and hanged. The "
  "result is widely regarded as manipulated, and a large number of PPP candidates — including Bhutto "
  "at Larkana — were returned unopposed. Boundaries shown here are reconstructed and approximate.")
e1985 = elec('1985', '28 February 1985', '53%',
  "A non-party election held by General Zia after a 1984 referendum extended his rule: candidates "
  "contested as individuals with no party labels, and the Movement for the Restoration of Democracy "
  "boycotted. The result was a National Assembly of independents, from which Muhammad Khan Junejo was "
  "appointed prime minister. Because there were no party tickets, every seat is shown in the neutral "
  "independent colour. Boundaries are reconstructed and approximate.")
e1988 = elec('1988', '16 November 1988', '43%',
  "The first party-based election after General Zia died in an August 1988 air crash. Benazir Bhutto's "
  "PPP won the most seats and she became prime minister — the first woman to head a modern "
  "Muslim-majority state. The anti-PPP Islami Jamhoori Ittehad alliance was formed with covert ISI "
  "backing, as the Supreme Court later found in the Asghar Khan case. Boundaries are reconstructed and "
  "approximate.")
txt = sub1('const ELEC={"2008"', 'const ELEC={' + e1977 + ',' + e1985 + ',' + e1988 + ',"2008"')

open(MAP, 'w', encoding='utf-8').write(txt)
print('patched map.html OK  (+1977/1985/1988, 1990s repointed to 207-seat boundaries)')
