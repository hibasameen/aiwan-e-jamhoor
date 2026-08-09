#!/usr/bin/env python3
"""
Reconstruct approximate NA constituency boundaries for the two pre-2002
delimitations, from the scraped constituency->district information:

  * 200-seat 1977 delimitation           -> na_200seat_1977_reconstructed.geojson
  * 207-seat 1985-1997 delimitation       -> na_207seat_1985-1997_reconstructed.geojson
    (identical seats in 1985, 1988, 1990, 1993 and 1997)

Method is the project's source-free reconstruction (see build_reconstructed_geometry.py):
group seats by the modern districts they occupy, take the district union, and split
multi-seat districts with a Voronoi diagram. ECP never published GIS for these years and
no labelled Commons map exists before 1993, so this is the only route; ALL features are
therefore properties.approx = true.

Accuracy notes
--------------
- District geometry is the 2015 CartoDB digitisation (data/districts_2015.geojson).
- The 1977 districts were larger than today's (they were subdivided later). For 1977 we
  expand each historic district to the union of the modern districts it became (EXPAND
  below) so its seats spread over the right territory; within-district position is still
  Voronoi-approximate. 1985-1997 names already match modern districts, so no expansion.
- Tribal "Trial/Tribal Area" seats name no agency, so all of them share the union of the
  seven FATA agencies and are Voronoi-split across it — placement is indicative only.

Also writes the exact seat->district crosswalk for each year (na_<year>_seat_districts.csv),
which is itself the reliable, non-approximate part of this output.
"""
import json, csv, re, os, sys
import build_reconstructed_geometry as brg

DIST = brg.load_districts()                     # 2015 districts: name -> geometry
TN = set(DIST)

# rename historic/spelling to the district-file name
RENAME = {'lyallpur': 'Faisalabad', 'campbellpur': 'Attock', 'turbat': 'Kech',
          'gwadur': 'Gwadar', 'lasbla': 'Lasbela', 'sibbi': 'Sibi',
          'naseerabad': 'Nasirabad', 'nawabshah': 'Shaheed Benazirabad'}

# 1977 historic district -> modern districts it later split into (only those in the file)
EXPAND = {
 'Faisalabad': ['Faisalabad', 'Toba Tek Singh', 'Chiniot'],
 'Sahiwal': ['Sahiwal', 'Okara', 'Pakpattan'],
 'Multan': ['Multan', 'Khanewal', 'Lodhran'],
 'Muzaffargarh': ['Muzaffargarh', 'Layyah'],
 'Dera Ghazi Khan': ['Dera Ghazi Khan', 'Rajanpur'],
 'Sargodha': ['Sargodha', 'Khushab'],
 'Mianwali': ['Mianwali', 'Bhakkar'],
 'Gujranwala': ['Gujranwala', 'Hafizabad'],
 'Sialkot': ['Sialkot', 'Narowal'],
 'Sheikhupura': ['Sheikhupura', 'Nankana Sahib'],
 'Sukkur': ['Sukkur', 'Ghotki'],
 'Larkana': ['Larkana', 'Kambar-Shahdadkot'],
 'Jacobabad': ['Jacobabad', 'Kashmore'],
 'Tharparkar': ['Tharparkar', 'Mirpurkhas', 'Umerkot'],
 'Dadu': ['Dadu', 'Jamshoro'],
 'Shaheed Benazirabad': ['Shaheed Benazirabad', 'Naushehro Feroze'],
}
AGENCIES = ['Bajaur Agency', 'Khyber Agency', 'Kurram Agency', 'Mohmand Agency',
            'North Waziristan Agency', 'Orakzai Agency', 'South Waziristan Agency']

norm = lambda s: re.sub(r'[^a-z ]', '', s.lower()).strip()
KNOWN_NORM = {norm(k): k for k in TN}
MULTI = sorted([k for k in KNOWN_NORM if ' ' in k], key=len, reverse=True)

def resolve(name, expand):
    t = re.sub(r'\s+(I{1,3}|IV|V?I{0,3}|IX|X{1,3}|\d+)$', '', name).strip()
    t = re.sub(r'(?i)\s*-?\s*cum\s*-?\s*', ' ', t)
    s = norm(t)
    found = []
    if re.search(r'trial|tribal', s):                 # unnamed tribal seat
        return list(AGENCIES)
    for m in MULTI:                                    # multiword district names first
        if re.search(r'\b' + re.escape(m) + r'\b', s):
            found.append(KNOWN_NORM[m]); s = re.sub(r'\b' + re.escape(m) + r'\b', ' ', s)
    for w in s.split():                                # single tokens (+ rename)
        if w == 'dir':                                 # historic Dir = Lower + Upper Dir
            found += ['Lower Dir', 'Upper Dir']; continue
        d = RENAME.get(w)
        if d is None and w in KNOWN_NORM:
            d = KNOWN_NORM[w]
        if d:
            found.append(d)
    # expand + validate against the district file
    out = []
    for d in found:
        for e in (EXPAND.get(d, [d]) if expand else [d]):
            if e in TN and e not in out:
                out.append(e)
    return out

def run(year, expand):
    C = list(csv.DictReader(open(f'data/results_{year}/na_{year}_constituency.csv')))
    seat_districts, cross = {}, []
    unresolved = []
    for r in C:
        ds = resolve(r['constituency_name'], expand)
        if not ds:
            unresolved.append((r['na'], r['constituency_name'])); continue
        seat_districts[r['na']] = ds
        cross.append({'na': r['na'], 'constituency_name': r['constituency_name'],
                      'districts': ';'.join(ds)})
    # crosswalk CSV
    with open(f'data/results_{year}/na_{year}_seat_districts.csv', 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=['na', 'constituency_name', 'districts'])
        wr.writeheader(); wr.writerows(cross)
    print(f'[{year}] resolved {len(seat_districts)}/{len(C)}  unresolved={unresolved}')
    # reconstructed polygons
    feats = brg.build(seat_districts, DIST)
    os.makedirs('data/boundaries', exist_ok=True)
    tag = '200seat_1977' if year == '1977' else '207seat_1985-1997'
    out = f'data/boundaries/na_{tag}_reconstructed.geojson'
    brg.write([{**f, 'approx': True} for f in feats], seat_districts, out)
    return out

if __name__ == '__main__':
    run('1977', expand=True)
    run('1985', expand=False)
