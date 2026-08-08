# Aiwan-e-Jamhoor — Methodology & Data Documentation

*Covers everything built in the July 2026 sessions: the data inventory, the results
database for 2008–2024, the constituency geometries for all three delimitations,
and the interactive map app.*

---

## 1. What exists and where

```
Aiwan-e-Jamhoor/
├── aiwan_e_jamhoor_map.html      # the app — 4 elections, self-contained (D3 inlined)
├── data_inventory.md             # survey of all known data sources (July 2026)
├── METHODOLOGY.md                # this file
├── map_template.html             # app source (data placeholders, un-inlined)
├── scripts/
│   ├── build_results_json.py           # CSV sources -> results_all.json
│   ├── build_reconstructed_geometry.py # 2018 & 2023 delimitation polygons
│   └── build_map.py                    # rewind + inline -> final HTML
└── data/
    ├── cookman_pk_candidate_data.csv       # 1970–2013 candidate-level (Cookman)
    ├── cookman_pk_constituency_data.csv    # 1970–2013 constituency-level (Cookman)
    ├── cookman_2018_candidate.csv          # GE-2018 candidate-level (Cookman)
    ├── cookman_2018_constituency.csv       # GE-2018 constituency-level (Cookman)
    ├── results_2024/                       # GE-2024 scrape (see its SOURCES.md)
    │   ├── na_2024_constituency.csv        #   one row per seat, winner/runner-up
    │   └── na_2024_candidates.csv          #   candidate-level, all 266 seats
    ├── na_2024_districts.csv               # 2023-delim seat -> district mapping
    ├── na_constituencies_2002delim.geojson # 2002 delimitation (rugpundit, simplified)
    ├── na_2018delim_simplified.geojson     # 2018 delimitation (reconstructed)
    ├── na_2024delim_simplified.geojson     # 2023 delimitation (reconstructed)
    ├── na_2002delim_source_shapefile.zip   # rugpundit original shapefile
    └── districts_2015.geojson              # district layer used for reconstruction
```

## 2. Results data

| Year | Source | Unit | Coverage | Provenance quality |
|---|---|---|---|---|
| 2008 | Cookman `pakistan_elections` | candidate | 268/272 GE-day (NA-37, 42, 119, 207 postponed; NA-230 row deduped) | ECP publications, transcribed; Cookman documents errors |
| 2013 | same | candidate | 269/272 (NA-38, 83, 254 postponed) | same |
| 2018 | Cookman `pakistan_election_results_2018` | candidate | 270/272 (NA-60, 103 postponed) | ECP's short-lived machine-readable feed; **provisional**, snapshot Sep 2018 |
| 2024 | ElectionPakistani scrape (this project) | candidate | 266/266 | **unofficial transcription of ECP Form-47**; some post-recount outcomes baked in |

**Aug 2026 upgrade:** 254 official scanned Form-47s (user-provided) were extracted into
`data/results_2024/na_2024_form47_official.csv` — official registered voters, turnout,
polling stations, rejected votes now power the app's 2024 panels; five election-day
winners later reversed (NA-79, 81, 154, 251, 261) are flagged in-app. Also on disk (user-
provided, not yet digitised): ECP 2018 delimitation district map sheets (114 high-res JPGs
WITH coordinate grids — georeferencable) and the full 2023 delimitation Form-7 archive
(~13 GB) — the raw material for true boundary digitisation.

2024 caveats (also in `data/results_2024/SOURCES.md`): our winner tally is IND 99,
PML-N 78, PPP 54, MQM 17, JUI-F 6, PML-Q 3, IPP 3, MWM/PML-Z/BAP/BNP-M/NP/PkMAP 1 each.
Commonly cited GE-day tallies (IND 101, PML-N 75, JUI-F 4, IPP 2…) differ on a handful
of seats — the source reflects some recounts/tribunal outcomes. PTI-backed winners are
recorded as **Independent** (party as declared); post-election SIC affiliation is not
applied. Registered voters/turnout were not on the source pages, so 2024 shares are of
total tabulated candidate votes (not registered voters), and turnout is blank.

Supplementary polls for GE-day-postponed seats are labelled "By-Election" in Cookman's
data and are deliberately excluded — the map shows strictly election-day outcomes
(postponed seats are hatched).

## 3. Constituency geometry — the three delimitations

**2002 delimitation (GE-2002/2008/2013).** `rugpundit/PakistanConstituencies2013`
shapefile — an unofficial digitisation of ECP's low-resolution map sheets. 270 of 272
seats have polygons; **NA-95 and NA-96 (Gujranwala urban) are missing** (the city area
sits inside the NA-97/98 polygons); their results remain searchable in the app. 34
features had invalid (bowtie) rings, repaired with `make_valid`.

**2018 and 2023 delimitations (GE-2018/GE-2024): reconstructed.** ECP has never
released GIS for these; no complete public vector file exists (verified July 2026).
Reconstruction (in `scripts/build_reconstructed_geometry.py`):

1. Seat→district tables: 2018 from the Dawn/plotree repo (`NA_seats_2018.csv`);
   2024 built for this project from ElectionPakistani + Wikipedia per-constituency
   pages (`data/na_2024_districts.csv`, 266 rows, 21 multi-district seats).
2. Seats sharing any district are merged into connected components (this handles
   "X-cum-Y" seats that partially overlap neighbouring districts).
3. One-seat components take the exact district union — **boundary is
   district-accurate**. Multi-seat components are partitioned by a Voronoi diagram
   clipped to the component, seeded by: (a) Dawn/plotree 2018 seat centroids
   (2018 map; and 2024 where the district's seat count is unchanged — 217 of 266
   seats), (b) own district-union centroids for cum-seats, (c) k-means cell centres
   (Karachi's 22 and Sanghar's 2 seats in 2024), ordered N→S/W→E to mimic ECP
   numbering.
4. District base layer is the 2015 CartoDB digitisation shipped with the plotree
   repo; districts created after 2015 (Kot Addu, Wazirabad, Murree, Keamari, Duki,
   Hub, Chaman, …) are mapped to their parent districts — full list in the script.

**Accuracy statement:** district-level edges are as good as the 2015 district layer;
within-district splits are approximate (hundreds of metres to kilometres off, worst
inside Karachi/Lahore). Every split feature carries `approx: true` and the app
surfaces this in tooltips and notes. These files are for visualisation, not for
spatial-join analysis at sub-district precision.

**Known limitation:** in 2024 multi-seat districts whose seat count changed since
2018 (Karachi, Sanghar), the assignment of seat numbers to k-means cells follows
geographic ordering conventions, not ECP's actual maps — treat intra-Karachi seat
placement as indicative only. Upgrading these to faithful boundaries requires
digitising ECP's Form-7 map sheets (or PBS shapefiles: request via pbs@pbs.gov.pk).

### 2018 delimitation upgraded to TRUE boundaries (Aug 2026, legs 1-4)

The user-provided ECP 2018 delimitation district sheets (114 JPGs) were digitised
province by province into `data/na_2018delim_v2.geojson` (272 features - this file
now feeds the app's 2018 layer; the Voronoi reconstruction is retired for 2018).
District base layer: geoBoundaries gbOpen ADM2 (126 units), harmonised where it
lags real districts (Chiniot/Nankana carved via the 2015 layer in Punjab; Larkana
and Sujawal carved from Qambar-Shahdadkot/Thatta via the COD-2022 layer, per-cell
nearest partition; the single gbOpen "Karachi" blob partitioned per-cell among the
six 2018 Karachi districts using COD-2022 - except Karachi West/South, which use
GADM 3.6 because COD-2022 folds Keamari, created 2020 from West, into South).

- **Leg 1 Balochistan:** Quetta sheet grid-georeferenced (`digitise_sheet.py`);
  other 15 districts single/merged-seat exact gb unions.
- **Leg 2 KP/FATA/ICT:** colour-fill sheets split by hue masks + outline ICP+TPS
  fit + label-transfer (`split_district_by_sheet.py`); NA-38/39 DI Khan Voronoi.
- **Leg 3 Punjab:** red-line sheets - barrier mask -> interior components ->
  Hungarian assignment to Dawn/plotree centroids (`run_punjab.py`). The 5
  districts that initially failed (Lahore, Multan, Bhakkar, Rawalpindi,
  Gujranwala - 35 seats) were recovered in `run_punjab_fix.py`: dilation range
  extended to 15 (Lahore's black-line PBS sheet needs ~11); key-map-inset
  regions dropped; Multan's green-bounded Municipal blob added as barrier and
  used directly as the city '__BLOB__' (city seats corrected to NA-155/156);
  Bhakkar split by seeded watershed on the distance transform (its NA line
  fades under the desert hatch and the orange municipal patches, so region
  growing cannot cut it); city blobs split per-cell by nearest plotree centroid
  with a k-means fallback. Only city-voronoi seats remain `approx` in these
  districts (NA-60/61/62, 81/82, 155/156, plus Faisalabad's 107-110 from the
  original leg).
- **Leg 4 Sindh** (`run_sindh.py` + `run_sindh2.py`): 28 colour-fill sheets, 61
  seats, all sheet-split except Larkana (sheet missing -> centroid Voronoi,
  NA-200/201 `approx`). Sheet colours (verified visually per callout arrow) are
  authoritative for seat identity; plotree centroids are QA-only, except to break
  true ICP rotation ambiguity (elongated districts fit equally well flipped -
  rms within 25% -> centroid cost decides). Hard-won mechanics in `run_sindh2.py`:
  callout-chip removal (rect-in-whitespace heuristics), content-blob outline for
  sheets with pale/absent fills (partial colour unions fit with deceptively low
  rms - coverage <65% of the drawing forces the blob), labelled pixels mapping
  outside the district dropped (chips/insets), distance-cutoff NN transfer so a
  weak seat takes only unclaimed area inside the sheet's own polygon. Outline-fit
  rms 0.2-7.2 km (median ~2.9); expect boundary error of the same order.
  QA renders: `data/digitised/qa_sindh_2018.png` (+ per-province QA PNGs).
- **Larkana (no sheet):** upgraded from district Voronoi to taluka composition
  (`fix_larkana_taluka.py`): NA-200 = Ratodero taluka + N part of Larkana
  taluka, NA-201 = Dokri + Bakrani + the rest (geoBoundaries ADM3 talukas,
  per-cell partition; composition per the successor seats NA-194/195). Only the
  intra-Larkana-taluka line remains a centroid Voronoi -> both stay `approx`.

## 4. The app (`aiwan_e_jamhoor_map.html`)

Single self-contained file (D3 v7 inlined, ~3.9 MB): year switcher (2008/2013/2018/
2024), party-colour choropleth with seat-count summary bar and legend (click a party
to isolate its seats), hover tooltips, click/search → full constituency panel
(top-6 candidates, turnout, margin), sortable table view (accessibility fallback),
pan/zoom, light/dark theme. Postponed seats are hatched.

Party colour design: brand-convention hues (PML-N dark green, PPP black, PTI maroon,
MQM magenta, JUI-F/MMA amber, ANP red, PML-Q light green, IND grey, BAP slate,
IPP olive, Other cyan), tuned so the normal-vision floor passes the dataviz
validator; residual CVD-confusable pairs are geographically non-adjacent, and the
table view + tooltips are the mandated fallback. PPP/IND get dark-mode overrides
(near-white / dark grey) since pure black vanishes on the dark surface.

**2024 layer upgraded (Aug 2026):** the year-2024 view no longer uses the old
district-Voronoi `na_2024delim_simplified.geojson` (82 KB of very coarse shapes). It now
carries the **true 2023-delimitation boundaries** for all 266 seats, simplified to ~1.15 MB
(`mapshaper -simplify 4% -clean -o precision=0.001`; keep-shapes off — the cell-grid
polygonisation leaves 467k staircase vertices that Visvalingam crushes safely, verified
0 dropped features, 0 overlap residue, area preserved to 4 km² in 894,295).

Each seat carries a normalised `confidence` (`scripts/build_2024_layer.py`): **high 203**
(ECP sheet-digitised, or an exact whole-district seat), **medium 44** (built from the
published seat composition — the line inside a split tehsil is inferred), **low 19**
(Peshawar NA-28–32, Islamabad NA-46/47/48, Faisalabad NA-101–104, Gujranwala NA-78/80,
Sheikhupura NA-115/116, Korangi NA-232–234). Low-confidence seats render with a **dashed
grey border** (`.cst.prov`, declared before the `:hover`/`.sel` rules so those still win on
colour and width while the dash persists), and every seat gets a provenance line in the
tooltip and the constituency panel via `boundaryNote()`.

Because the shipped app already carried a newer 2018 layer than `build_map.py` references,
the swap was done **surgically on the built HTML** (`scripts/patch_app_2024.py`: brace-matched
replacement of the `'2024'` value inside the inlined `GEOS` object, plus the six UI patches,
each asserted to match exactly once). Rebuilding from `build_map.py` would regress 2018 —
fix that script's 2018 input path before ever running a full rebuild.

Rendering gotcha worth remembering: d3-geo treats RFC-7946 counter-clockwise
exterior rings as sphere-inverted — every GeoJSON fed to the app must be re-wound
clockwise (`build_map.py` does this), and invalid bowtie polygons must be
`make_valid`-ed first or the map renders as a filled rectangle.

## 5. Rebuild from scratch

```bash
pip install geopandas shapely pandas --break-system-packages
npm install -g mapshaper && npm install d3@7
python3 scripts/build_results_json.py
python3 scripts/build_reconstructed_geometry.py
mapshaper na_2018delim_raw.geojson -simplify 15% keep-shapes -clean -o precision=0.0001 data/na_2018delim_simplified.geojson
mapshaper na_2024delim_raw.geojson -simplify 15% keep-shapes -clean -o precision=0.0001 na_2024delim_simplified.geojson
python3 scripts/build_map.py
```

## 6. Roadmap notes

- **Upgrade 2024 results to official:** cross-check against ECP Form-49/gazette
  (image PDFs) or FAFEN's constituency tool; add registered voters/turnout.
- **Track post-election changes:** tribunal reversals and the July 2024 reserved-seat
  judgment mean "declared" ≠ "current" — model them as separate fields.
- **True 2018/2024 boundaries:** digitise ECP Form-7 map sheets against the
  union-council layer, or obtain PBS delimitation shapefiles on request.
- **By-elections:** ElectionPakistani has the only consolidated series since 2008.
- **Database design implication:** treat delimitation vintage as a first-class
  entity — NA-120 (2002) ≠ NA-120 (2018) ≠ NA-120 (2023); never join on seat number
  across vintages.

## 7. 2023 delimitation — true boundaries (Aug 2026, in progress)

Same exercise as §3 but for the 2023 delimitation (GE-2024, 266 seats). Raw
material: the "2023 Delimitation" archive (~13 GB) is the ECP **representations**
(objection filings) — each attaches a scan of the official district delimitation
sheet ("Preliminary Delimitation 2023"). ~2,850 files; NA-level sheets exist for
~45 of the 70 multi-seat district groups. Caveats: sheets are the *preliminary*
delimitation (FAFEN: 66 NA seats revised in the final list — Punjab 43, Sindh 11,
Balochistan 7, KP 5; headline changes NA-81 −Hafizabad, NA-253 +Ziarat, NA-265
Pishin-only); coverage exists only where someone objected.

Structure (from `na_2024_districts.csv`, which is final-delimitation): seats
partition into 109 connected components ("canvases") over shared districts —
38 single-seat canvases need **no digitisation** (whole-district compositions),
71 multi-seat canvases (228 seats) need internal lines. Scripts:

- `build_2023_canvases.py`: COD ADM2 base (renames to final-delim names; Lehri→Sibi
  and Shaheed Sikandarabad→Nasirabad flagged), tehsil carves for Taunsa/Kot Addu/
  Wazirabad (gb ADM3, approx), Keamari+West merged canvas, Murree+Rawalpindi and
  Chakwal+Talagang merged; partition snapped to the 2018 layer's national outline
  (sym-diff 0.0). Outputs `data/digitised/districts_2023.geojson`,
  `canvases_2023.geojson`, and the 38 resolved single seats.
- **KARACHI GOTCHA:** COD ADM2 is structurally wrong in Karachi — the real
  Keamari/Mauripur peninsula sits inside COD "South Karachi" (IoU vs truth:
  South 0.17, West 0.28, Malir 0.67). `fix_karachi_canvases.py` rebuilds the six
  district footprints from the 2018 layer's sheet-fitted seat unions
  (Malir=236-238, Korangi=239-241, East=242-245, South=246-247,
  West+Keamari=248-252, Central=253-256) and re-partitions the Karachi block.
- Sheet digitisation reuses `split_district_by_sheet.py` (no printed grids on 2023
  sheets → outline-fit ICP+TPS). Per-canvas agents; brief in `scripts/AGENT_BRIEF.md`.
- No-sheet canvases: **taluka-composition rebuild** from the final delimitation's
  verbal composition (Wikipedia/DBpedia/Dawn per seat; gb ADM3 talukas; partial
  talukas split per-cell nearest between whole-taluka cores) — `approx:true`.

**Status: COMPLETE — 266/266 seats resolved (Aug 2026). See §8 for KP/Balochistan/ICT.**

Punjab (Aug 2026, same session): all 36 multi-seat canvases done — 29 sheet-digitised
(rms 0.7–5.8 km; incl. Lahore all-14-seats from full-district colour sheets, Rawalpindi
with the prelim→final NA-54..57 renumbering mapped and verified via 2024 winners,
Kasur's final-list revision reconstructed, Okara's hand-marked 'MODIFIED' prelim→final
patches applied), 7 by tehsil-composition (Narowal, Pakpattan, Rajanpur, Vehari,
Sheikhupura-low, Sialkot hybrid, Faisalabad city seats voronoi-low). Per-canvas
reports/QA in `data/digitised/punjab_2023_digitisation.zip`; QA render
`qa_punjab_2023.png`. Punjab flags: Gujranwala NA-78/80 city split undrawn (equal-area
median, approx); Faisalabad NA-101..104 city voronoi (low); Sheikhupura NA-115/116
invented city disc (low); Bahawalpur NA-168 outline ±2-4 km; RYK internal lines ±2-4 km
(sheets disagree, IoU 0.39-0.85); DG Khan mountain-strip lines up to ±10 km.

**Earlier status: Sindh complete (61/61 seats)** — 13 canvases sheet-digitised (rms
0.2–3.2 km; per-canvas reports + QA in `data/digitised/sindh_2023_digitisation.zip`),
6 by taluka composition (Qambar, Benazirabad, Tharparkar, Badin, Dadu, Korangi-low),
7 single-seat. Assembled with 38 scaffold singles into
`data/na_2023delim_true_partial.geojson` (92/266 seats, exact partition, sliver
cleanup ≤1 km² parts reassigned by longest shared boundary). QA:
`data/digitised/qa_sindh_2023.png`, `qa_scaffold_2023.png`.

Open flags: Naushahro Feroze sheets disagree (printed prelim used; check final);
Karachi East sheet is an applicant proposal; C094 West/Keamari internal lines carry
1–2 km uncertainty (canvas footprint vs sheets); Karachi South NA-239 clipped at
canvas west wall (~4 km²; real Lyari ~8 km²); creek-island assignments (NA-229/230)
nearest-label only; verify Sindh's 11 final-list revisions seat-by-seat.

Next: Punjab (largest: Lahore 14, Faisalabad 10 — thin sheet coverage), KP,
Balochistan (Quetta 3 + NA-254/255, NA-258/259 cum splits), Islamabad (no sheets —
composition rebuild); then final-list verification pass, `-clean` simplify,
app integration with `approx` flags per seat.


## 8. 2023 delimitation — KP, Balochistan, Islamabad (Aug 2026): 266/266 complete

The last 14 canvases (36 seats) were built by **tehsil composition**, not sheet
digitisation — the ECP representation archive was unreachable for this session, and
four of the canvases (Swabi, Charsadda, Lower Dir, ICT) have no sheets in any case.
Output: `data/na_2023delim_true_full.geojson` (all 266, exact partition),
`na_2023delim_simplified.geojson` (2.2 MB, app-ready),
`data/digitised/kp_bal_ict_*` (per-seat geometry, manifest CSV, report, QA render).

### Method
`scripts/compose_kp_bal_ict.py`. Each canvas polygon is cell-gridded (~60k cells);
cells inside a tehsil wholly owned by one seat are hard-locked to it; cells in a
**split** tehsil are allocated by capacity-constrained nearest-anchor, where the
quota is the sourced area/population share and the anchor is either a compass point
or — preferably — the seat's already-assigned cells (`'CORE'`), which keeps the slice
adjacent to the rest of the seat. Residue goes to the nearest assigned cell, then a
**contiguity repair** pass reassigns orphan components (<15% of a seat) to the
neighbour they share most cells with. Constituencies are contiguous by law, so a
fragmented output is a signal that the *composition hypothesis* is wrong, not that the
geometry needs smoothing — this caught two real errors (below).
`scripts/assemble_266.py` merges with the 230-seat partial, resolves overlaps and
slivers, and verifies: 266/266 seats, no gaps, sym-diff vs the 2018 national outline
0.0003%.

### Two COD district-layer errors found and fixed
Both are canvases swallowing a neighbouring district, inherited from COD ADM2:
- **C099** carried a detached 4,126 km² western lobe = **Surab district**, which
  belongs to NA-261 Surab-cum-Kalat-cum-Mastung. Transferred to NA-261.
- **C105 Quetta** carried 1,120 km² of **Dasht tehsil, which is in MASTUNG district**,
  not Quetta (canvas 4,183 km² vs Quetta's true ~2,653). Carved out to NA-261.
The `carve_out` / `drop_detached_to` spec fields handle both. **Check the other
Balochistan canvases for the same class of error** — COD ADM2 predates the 2017–22
district creations (Surab, Usta Muhammad, Sohbatpur, Hub, Duki…).

### Findings worth not re-deriving
- **Lower Dir NA-6/NA-7 were TRANSPOSED between 2018 and 2023.** The southern
  Jandool/Maidan seat (Lal Qilla + Samarbagh + Munda + part Balambat) was NA-7 in 2018
  and is **NA-6** in 2023. Verified three ways: Dawn's June-2018 final-plan text; both
  principals of the 2018 NA-7 contest (Bashir Khan, Sirajul Haq) moving to NA-6 in 2024;
  Form-47 electorates. Anything joining 2018 NA-6/7 geography to 2024 results is backwards.
- **KP seat titles** (from our own Form-47 scans, authoritative): NA-14 *Mansehra* and
  NA-15 *Mansehra-cum-Torghar* (not Mansehra-I/II); **NA-43 is Tank-cum-D.I. Khan** —
  the Tank seat is the LOWEST of the three DIK-area numbers, NA-44/45 are D.I. Khan-I/II.
- **Nasirabad split (NA-254/255):** resolved on FAFEN district voter rolls, not on
  population parity. Jhal Magsi 78,208 + Kachhi 153,974 = 232,182 vs NA-254's 324,739
  forces ~92–115k Nasirabad electors (36–45% of the district) into NA-254. Only
  **Tamboo + Baba Kot** (40.5%) is both inside that band and contiguous.
- **Quetta:** all three seats lie wholly inside Quetta district — there is no
  Quetta-cum-Chagai/Nushki seat. NA-262 is the outer ring (Kuchlak/Saddar/Panjpai,
  28% of the district electorate), NA-264 the Quetta City + charges 13–14 block,
  NA-263 the largest (Sariab + balance of city).
- The **ECP Form-7 (final delimitation 2023)** is the one document that would settle
  every remaining flag. It is unreachable from the sandbox: ecp.gov.pk serves a
  robots.txt that 500s (WebFetch refuses the domain), and archive.org/DocumentCloud/
  CORS proxies are all blocked by egress policy. **Fetch it from a browser and drop the
  PDF in the project folder** — landing page `ecp.gov.pk/final-delimitation-2023-form-7-national-assembly`.

### Confidence flags (per-seat, in the geojson `confidence` property)
- **high (9 seats)** — NA-16/17 (ECP text via APP/Pakistan Observer), NA-19/20 (verbatim
  ECP final-list patwar circles), NA-24/25 (clean whole-tehsil split, no partial tehsil),
  **NA-262/263/264 (SHEET-DIGITISED, see below)**.
- **medium (19)** — Swat, Lower Dir, Mansehra, Mardan, Nowshera, DIK/Tank, NA-254/255,
  NA-258/259. Tehsil-level composition sourced; the line *inside* a split tehsil is inferred.
- **low (8)** — **Peshawar NA-28..32** and **Islamabad NA-46/47/48**. Anchored partitions
  from press descriptions only. Peshawar's geoBoundaries polygons are an obsolete
  subdivision that does not map to the 2023 tehsils; every reachable ICT description is
  2018-vintage (they are the renumbered NA-52/53/54).

### Sheets DO resolve these — three read this session
Late in the session the device bridge returned and three Balochistan representation
sheets were pulled from the archive. They overturned two inferences and confirmed one:
- **Quetta NA-262/263/264 — now SHEET-DIGITISED** (`scripts/digitise_quetta.py`, sheet
  "Muhammad Mobeen Khilji …NA-262,263,264 Quetta"; yellow/blue/green colour masks, outline
  ICP+TPS fit, rms 3.25 km, contiguity-repaired). NA-262 is the outer ring (west Panjpai
  lobe + north arc + the whole eastern arm), NA-263 the central urban band, NA-264 the
  southern block. Sheet-printed populations 890,833 / 819,201 / 885,458 sum to 2,595,492
  = Quetta district, confirming all three seats are Quetta-only. **The sheet also REFUTED
  a verification-agent claim that the eastern DASHT lobe is Mastung territory** — the ECP
  outline plainly includes it, so no carve-out is applied. Only the Surab lobe (C099) is
  a genuine COD error.
- **Kech split NA-258/259 — RESOLVED.** The NA-259 sheet carries an explicit table:
  NA-259 = District Gwadar (305,160) + District Kech (696,791) **excluding** Sub-Division
  Buleda, Sub-Tehsil Zamran, Sub-Tehsil Hoshab, and UCs Sami (Turbat), Shahrak, Nodiz and
  Nasirabad. So NA-258 takes **Buleda + Zamuran + Hoshab only**; Turbat, Tump, Mand, Dasht
  and Balnigor all stay in NA-259. This overturned an earlier roll-arithmetic guess that
  had put Tump in NA-258.
- **NA-254/255**: the sheet found is an objector's *proposal* (Usta Muhammad to NA-254,
  Nasirabad whole to NA-255) that was NOT adopted — the final titles split Nasirabad. It
  does give official district populations: Kachhi 442,612, Jhal Magsi 203,368, Usta
  Muhammad 292,060, Sohbat Pur 240,106, Jaffarabad 302,498, Nasirabad 563,377. The
  Tamboo+Baba Kot allocation stands (contiguity + FAFEN rolls).

**Lesson:** always read the sheet before trusting composition arithmetic *or* a
verification agent — two of the three sheets changed the answer. `_samples/bal` and
`_samples/kp` under "2023 Delimitation" hold the extracted Balochistan and Peshawar
sheets (~600 MB; safe to delete once digitised).

### Next
1. **Sheet-digitise Peshawar NA-28..32** — the last 5 low-confidence seats with sheets
   available. `_samples/kp` already holds the extracted Peshawar files (mostly PK-level;
   check for an NA-level sheet). Reuse `scripts/digitise_quetta.py` as the template.
2. **Islamabad NA-46/47/48** has no sheets — needs the ECP Form-7 or the 2023 ICT local-
   government UC delimitation (archive.org has the latter).
3. Unverified links: **Garhi Kapura → NA-22** (Mardan); which side of Babuzai/Kabal (Swat);
   the Paniala-vs-Paharpur boundary (NA-43/44); the Nasirabad tehsil split (NA-254/255).
4. Integrate into the app: `na_2023delim_simplified.geojson` with the per-seat `confidence`
   property surfaced (hatch or outline the `low` seats so readers know which lines are soft).


## 9. The four elections — circumstances and observer findings

A seat map cannot show that one campaign was fought under a boycott, another under a bombing
campaign aimed at three named parties, and a third with the largest party stripped of its ballot
symbol. The app carries a per-election context card (map page, right column) and the Method page
carries the full account. The standard is the same one used for boundaries: **report what named
observers concluded, quote them, link the source, and offer no verdict of our own.** No aggregate
"fairness score" is published.

| Election | Date | Seats polled | Turnout | Candidates | Won by <5% |
|---|---|---|---|---|---|
| 2008 | 18 Feb 2008 | 268 of 272 | 44% | 2,180 | 62 |
| 2013 | 11 May 2013 | 269 of 272 | 55% | 4,496 | 52 |
| 2018 | 25 Jul 2018 | 270 of 272 | 52% | 3,431 | 79 |
| 2024 | 8 Feb 2024 | 265 of 266 | 48% | 5,112 | 68 |

Seats-polled, candidate counts and margins are computed from `data/results_all.json`; turnout is the
registered-voter-weighted figure from our own data, which tracks the official numbers (2008 ~44%,
2013 55.0% ECP, 2018 51.9–52.1%, 2024 47.6% FAFEN-from-ECP).

- **2008** — poll moved from 8 Jan to 18 Feb after Benazir Bhutto's assassination; 4 seats did not
  poll; boycotted by PTI, JI and the APDM; no Commonwealth observation (Pakistan was suspended).
  EU EOM: "a level playing field was not provided during the campaign." Democracy International:
  "the elections provided a genuine opportunity for Pakistani voters to express their will."
- **2013** — first civilian-to-civilian handover; highest turnout since 1977; TTP violence targeted
  ANP, MQM and PPP specifically. EU EOM: "The high number of attacks affected campaigning and
  unbalanced the playing field." 2015 judicial commission: "in large part organised and conducted
  fairly and in accordance with the law." ~500 polling stations recorded zero women voting.
- **2018** — Nawaz Sharif disqualified for life and jailed 12 days before the poll; ~370,000 troops
  deployed, many inside polling stations; the RTS collapsed on election night. Two distinct verdicts
  from the same mission: EU EOM "There was no level playing field for electoral contestants" on the
  campaign, but "Voting was assessed as well-conducted and transparent" on the day, with the count
  faulted. EU observers did not cover Balochistan.
- **2024** — Supreme Court stripped PTI of its symbol on 13 Jan; candidates ran as independents;
  NA-8 Bajaur postponed after a candidate was killed; nationwide mobile shutdown on polling day;
  results ~15 hours late; Form-45 vs Form-47 dispute unadjudicated. EU High Representative: "We
  regret the lack of a level playing field." Commonwealth (final report Sept 2025): "impinged on the
  credibility, transparency and inclusiveness of the electoral process." HRCP: "The integrity of the
  2024 elections was compromised."

Caveat carried in the app: observer missions differ in mandate, coverage and access, so the absence
of a finding is not evidence of its absence.
