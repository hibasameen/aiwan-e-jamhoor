#!/usr/bin/env python3
"""
Fix the numbering foundation for the 207-seat (1985–1997) delimitation.

Finding: ElectionPakistani's 1985 pages use a 1977-style seat ordering, while
1988/1990/1993/1997 (and the Commons maps) share one numbering. This script:

 1. builds the seat->district crosswalk in MAP numbering from the 1988 names
    (+ per-year variants from the embedded RESULTS names for 1990/93/97)
    -> data/wip/trace/xwalk_207map.json
 2. builds the 1985 -> map-numbering concordance by matching seats within
    identical district groups (same delimitation => same seats per district),
    ordinal order on both sides -> data/results_1985/na_1985_to_207map.csv
 3. rebuilds the Voronoi fallback geometry in MAP numbering
    -> data/boundaries/na_207seat_1985-1997_reconstructed.geojson (overwrite)
"""
import json, csv, re, collections
import build_reconstructed_geometry as brg

DIST = brg.load_districts(); TN = set(DIST)
norm = lambda s: re.sub(r'[^a-z ]', '', s.lower()).strip()
KNOWN = {norm(k): k for k in TN}
MULTI = sorted([k for k in KNOWN if ' ' in k], key=len, reverse=True)
AGENCIES = ['Bajaur Agency', 'Khyber Agency', 'Kurram Agency', 'Mohmand Agency',
            'North Waziristan Agency', 'Orakzai Agency', 'South Waziristan Agency']
RENAME = {'lyallpur': 'Faisalabad', 'campbellpur': 'Attock', 'turbat': 'Kech',
          'gwadur': 'Gwadar', 'lasbla': 'Lasbela', 'sibbi': 'Sibi',
          'naseerabad': 'Nasirabad', 'nawabshah': 'Shaheed Benazirabad',
          'malir': 'Karachi', 'hyederabad': 'Hyderabad', 'sukkar': 'Sukkur',
          'chagai': 'Chaghi'}

# Era expansion: the 1980s districts named in the returns were later carved up.
# Each maps to the modern (2015-file) districts its territory comprised, so the
# seats cover the whole country and the canvas has no carved-district holes.
# FR regions are attached to the district whose seats they voted with.
EXPAND88 = {
 'Peshawar': ['Peshawar', 'Nowshera', 'FR Peshawar'],
 'Kohat': ['Kohat', 'Hangu', 'FR Kohat'],
 'Bannu': ['Bannu', 'Lakki Marwat', 'FR Bannu', 'FR Lakki Marwat'],
 'Dera Ismail Khan': ['Dera Ismail Khan', 'Tank', 'FR DI Khan', 'FR Tank'],
 'Abbottabad': ['Abbottabad', 'Haripur'],
 'Mansehra': ['Mansehra', 'Batagram', 'Tor Ghar'],
 'Swat': ['Swat', 'Buner', 'Shangla'],
 'Gujrat': ['Gujrat', 'Mandi Bahauddin'],
 'Sialkot': ['Sialkot', 'Narowal'],
 'Gujranwala': ['Gujranwala', 'Hafizabad'],
 'Sahiwal': ['Sahiwal', 'Pakpattan'],
 'Multan': ['Multan', 'Lodhran'],
 'Jhang': ['Jhang', 'Chiniot'],
 'Sheikhupura': ['Sheikhupura', 'Nankana Sahib'],
 'Sukkur': ['Sukkur', 'Ghotki'],
 'Larkana': ['Larkana', 'Kambar-Shahdadkot'],
 'Jacobabad': ['Jacobabad', 'Kashmore'],
 'Shaheed Benazirabad': ['Shaheed Benazirabad', 'Naushehro Feroze'],
 'Tharparkar': ['Tharparkar', 'Mirpurkhas', 'Umerkot'],
 'Hyderabad': ['Hyderabad', 'Tando Allah Yar', 'Tando Muhammad Khan', 'Matiari'],
 'Dadu': ['Dadu', 'Jamshoro'],
 'Thatta': ['Thatta', 'Sajawal'],
 'Chaghi': ['Chaghi', 'Nushki'],
 'Kharan': ['Kharan', 'Washuk'],
 'Kalat': ['Kalat', 'Mastung'],
 'Khuzdar': ['Khuzdar', 'Awaran'],
 'Loralai': ['Loralai', 'Barkhan', 'Musakhail'],
 'Zhob': ['Zhob', 'Killa Saifullah', 'Sherani'],
 'Pishin': ['Pishin', 'Killa Abdullah'],
 'Kachhi': ['Kachhi', 'Jhal Magsi'],
 'Sibi': ['Sibi', 'Harnai', 'Lehri', 'Ziarat'],
 'Jaffarabad': ['Jaffarabad', 'Sohbatpur'],
}

def expand(ds):
    out = []
    for d in ds:
        for e in EXPAND88.get(d, [d]):
            if e in TN and e not in out: out.append(e)
    return out

# Scraped page titles truncated some composite seat names, orphaning districts.
# Attachments are grounded in the source's own 1988 index page listing:
#   NA-197 "Quetta Chagai", NA-206 "Lasbela Gwadur", NA-203 "Jaffarabad"
#   (the Jaffarabad seat covered the wider Naseerabad division area).
ATTACH = {'NA-197': ['Chaghi', 'Nushki'], 'NA-206': ['Gwadar'], 'NA-203': ['Nasirabad']}

def attach(xwalk):
    for na, extra in ATTACH.items():
        if na in xwalk:
            for d in extra:
                if d in TN and d not in xwalk[na]: xwalk[na].append(d)
    return xwalk
PHRASES = {'di khan': 'Dera Ismail Khan', 'dg khan': 'Dera Ghazi Khan',
           'rahimyar khan': 'Rahim Yar Khan'}
STRIP = re.compile(r'\b(i{1,3}|iv|v i{0,3}|vi{1,3}|ix|x i{0,3}|xi{1,3}|\d+|general|full|cum|vote)\b')

def resolve(name):
    s = norm(re.sub(r'(?i)-?cum-?', ' ', name))
    s = STRIP.sub(' ', s)
    if re.search(r'trial|tribal', s): return list(AGENCIES)
    s = re.sub(r'karachi\s+(west|east|central|south)', 'karachi', s)
    s = s.replace('malakand protected area', 'malakand')
    found0 = []
    for ph, d in PHRASES.items():
        if ph in s:
            found0.append(d); s = s.replace(ph, ' ')
    found = list(found0)
    for m in MULTI:
        if re.search(r'\b' + re.escape(m) + r'\b', s):
            found.append(KNOWN[m]); s = re.sub(r'\b' + re.escape(m) + r'\b', ' ', s)
    for w in s.split():
        if w == 'dir': found += ['Lower Dir', 'Upper Dir']; continue
        d = RENAME.get(w) or KNOWN.get(w)
        if d: found.append(d)
    out = []
    for d in found:
        if d in TN and d not in out: out.append(d)
    return out

def load_names_88():
    return {r['na']: r['constituency_name']
            for r in csv.DictReader(open('data/results_1988/na_1988_constituency.csv'))}

def embedded_results():
    L = open('map.html', encoding='utf-8').read().split('\n')
    return json.loads(L[205][len('<script>window.RESULTS='):-1])

def main():
    n88 = load_names_88()
    R = embedded_results()
    # --- 1. map-numbering crosswalks
    xw = {}
    base = {}
    unresolved = []
    for n in range(1, 208):
        na = f'NA-{n}'
        ds = expand(resolve(n88.get(na, '')))
        if not ds: unresolved.append((na, n88.get(na))); continue
        base[na] = ds
    print('1988 base xwalk:', len(base), 'unresolved:', unresolved)
    xw['base'] = attach(base)
    for y in ('1990', '1993', '1997'):
        d = {}
        for n in range(1, 208):
            na = f'NA-{n}'
            nm = (R.get(y, {}).get(na) or {}).get('name')
            ds = expand(resolve(nm)) if nm else None
            d[na] = ds if ds else base.get(na, [])
        xw[y] = attach(d)
    json.dump(xw, open('data/wip/trace/xwalk_207map.json', 'w'))
    print('wrote xwalk_207map.json (base + per-year)')

    # --- 2. NO 1985 concordance is shipped. District-set matching cannot give
    # seat-level identity where districts were themselves re-carved between the
    # numbering eras (Attock/Jhelum->Chakwal, Sukkur->Ghotki, Mansehra->Kohistan
    # splits...). Guessed pairings would violate the project's sourcing standard,
    # so 1985 keeps its own numbering and its own geometry layer.
    with open('data/results_1985/na_1985_to_207map.csv', 'w', newline='') as f:
        f.write('# DEPRECATED - no concordance shipped. ElectionPakistani 1985 numbering\n'
                '# differs from the 1988-1997 numbering; a seat-level mapping cannot be\n'
                '# derived reliably where districts were re-carved between the eras.\n')

    # --- 3a. Voronoi fallback in MAP numbering (for the traced 1988-97 set)
    feats = brg.build(base, DIST)
    brg.write([{**f, 'approx': True} for f in feats], base,
              'data/boundaries/na_207seat_map_reconstructed.geojson')

    # --- 3b. Voronoi in ELECTIONPAKISTANI-1985 numbering (1985's own layer)
    x85 = {r['na']: expand(r['districts'].split(';'))
           for r in csv.DictReader(open('data/results_1985/na_1985_seat_districts.csv'))}
    # same orphaned districts in the 1985 numbering: Quetta-Chagai is NA-197,
    # Lasbela-Gwadar NA-206 there too; the Naseerabad-division seat is NA-203.
    for na, extra in (('NA-197', ['Chaghi', 'Nushki']), ('NA-206', ['Gwadar']),
                      ('NA-203', ['Nasirabad', 'Jaffarabad', 'Sohbatpur'])):
        if na in x85:
            for d in extra:
                if d in TN and d not in x85[na]: x85[na].append(d)
    feats85 = brg.build(x85, DIST)
    brg.write([{**f, 'approx': True} for f in feats85], x85,
              'data/boundaries/na_207seat_1985numbering_reconstructed.geojson')

if __name__ == '__main__':
    import sys; sys.path.insert(0, 'scripts')
    main()
