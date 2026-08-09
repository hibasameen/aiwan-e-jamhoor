# Pre-2002 NA constituency boundaries (reconstructed)

Two constituency boundary files for the delimitations used before the 2002 (272-seat) map:

| File | Seats | Elections it covers |
|------|-------|---------------------|
| `na_200seat_1977_reconstructed.geojson` | 200 (NA-1..200) | **1977 only** |
| `na_207seat_1985-1997_reconstructed.geojson` | 207 (NA-1..207) | **1985, 1988, 1990, 1993, 1997** |

## A note on the "1977 delimitation" naming

There were two different pre-2002 delimitations, not one:

- The **1977 election used 200 seats** (1972-census delimitation, older district names —
  Lyallpur = Faisalabad, Campbellpur = Attock, etc.).
- **1985 through 1997 used a 207-seat map** (1981-census delimitation).

So the map that actually ran "until 1997" is the 207-seat one, and 1977's 200-seat map was
used only that once. Both are provided here. (The repo's older `na_1977delim_*` WIP files use
"1977delim" loosely for the 207-seat pre-2002 map; these two files are named by seat count to
avoid that ambiguity.)

## How they were made — and how accurate they are

ECP never published GIS for these years, and no labelled Wikimedia Commons map exists before
1993, so raster-tracing (the method behind the 2023 boundaries) is not possible here. Instead
these are **reconstructed** with the project's source-free method (`build_reconstructed_geometry.py`,
driven by `build_historic_geometry.py`):

1. Each seat is assigned to the modern district(s) it occupies, read from the scraped
   constituency names (the exact crosswalk is saved as `results_<year>/na_<year>_seat_districts.csv`).
2. A seat that owns whole district(s) gets the district union — **boundary is district-accurate**.
3. Districts holding several seats are split by a **Voronoi diagram** — **within-district
   position is approximate** (hundreds of metres to kilometres off, worst inside big cities).

Every feature carries `properties.approx = true`. Properties: `na`, `dist` (districts), `approx`.

Additional caveats:

- District geometry is the 2015 CartoDB digitisation (`data/districts_2015.geojson`).
- **1977** districts were larger than today's; each is expanded to the union of the modern
  districts it later split into (e.g. Lyallpur → Faisalabad + Toba Tek Singh + Chiniot) so its
  seats spread over the right territory. The expansion map is in `build_historic_geometry.py`.
- **Tribal "Trial/Tribal Area" seats** name no agency, so all of them share the union of the
  seven FATA agencies and are Voronoi-split across it — placement is indicative only.

## NUMBERING WARNING (discovered 2026-08-09)

ElectionPakistani's **1985 pages use a different (1977-style) seat numbering** from the one
shared by 1988/1990/1993/1997 and the Commons maps (e.g. NA-47 = Gujrat in the 1985 pages but
Sargodha-1 in 1988–97; NA-85 = Lahore vs Sialkot-1). **No seat-level concordance is shipped**:
district-set matching cannot resolve identity where districts were re-carved between the eras
(Attock/Jhelum→Chakwal, Sukkur→Ghotki, Mansehra→Kohistan), and guessing would breach the
sourcing standard. Consequences for the app: 1985 renders on its own layer
(`na_207seat_1985numbering_reconstructed.geojson`, GEOS key `207seat85`) keyed by the source's
numbering, and the 1988↔1985 held/turned comparison is disabled. The crosswalk used for
tracing/validation is `data/wip/trace/xwalk_207map.json` (map numbering, from the 1988 scrape
plus per-year embedded names).

## Map-traced 207-seat set (preferred — now used by the live map)

`na_207seat_1985-1997_traced.geojson` supersedes the Voronoi version for 1985–1997. It is
traced from the labelled Wikimedia Commons result maps (`data/sources/Pakistan_General_election_
1990/1993/1997.png`) by `scripts/trace_commons_map.py` (segment → OCR the NA label →
georeference to the 2002-constituency union with `georef_map.py` + `georef_refine.py` →
contour-trace each region → warp to lon/lat), then merged best-per-seat across the three maps by
`scripts/merge_traced_boundaries.py`.

- Georeference quality: affine IoU ≈ 0.92 → quadratic warp ≈ 0.94; drawn-edge vs true outline
  **median ≈ 4.7 km, p90 ≈ 16 km**.
- **v2 (current, via `trace_commons_full.py` + `merge_traced_v2.py`): 199 of 207 real-traced.**
  Breakdown: **162** main-map traces, **21** city-inset traces, **16** low-confidence traces,
  **8** Voronoi fallbacks (NA-13, 50, 110, 120, 165, 166, 168, 197).
- **Every inset box is handled** (the earlier version placed only Karachi and left the smaller
  city boxes warped to wrong locations). Each map carries five insets — Karachi (IoU ≈ 0.58),
  Lahore (0.72), Faisalabad (0.55–0.59), Peshawar (0.74), Rawalpindi (0.51) — each fitted
  separately to its own seats' districts, so the zoomed cities land at their true locations.
- **Gap fill:** unlabelled regions were assigned by district elimination (unique missing seat in
  the region's district ⇒ confident) and, where several seats of one district were missing, by
  N→S/W→E ordinal pairing — those 16 carry `properties.confidence:"low"` and render dashed in
  the app. The trace geometry of low-confidence seats is real; only the NA attribution within
  the district is inferred.
- **Placement validation:** any candidate polygon sitting >40 km from its own district was
  demoted (this caught NA-120, misread and misplaced ~300 km in all three maps).
- 1977 stays Voronoi (`na_200seat_1977_reconstructed.geojson`) — no pre-1990 Commons map exists.
- `na_207seat_map_reconstructed.geojson` is the Voronoi set in map numbering (fallback source);
  the old `na_207seat_1985-1997_reconstructed.geojson` filename is retired.

## Tessellated final layer (what the live map ships)

`na_207seat_1985-1997_tessellated.geojson` — the merged traced set post-processed by
`scripts/tessellate_207.py` into a complete tiling of the NA area, because warped raster
traces cannot tile on their own (the raw merge left ~7% of the country in 205 gap slivers,
which on the map read as missing seats). Method: 1.1 km grid; every seat's merged geometry
is a seed; each district's pixels are assigned to the nearest seed among that district's own
seats (so seats never leak across district lines); a seat whose seed was lost gets one planted
at its traced centroid (only NA-100 needed this). Result: **overlap factor 1.000, coverage
~97% of the true area** (the remainder is hairline border seams at grid resolution, invisible
under the app's stroke). Provenance properties (`src`, `approx`, `confidence`) survive.

Two era corrections feed this (in `build_map_numbering.py`):
- **EXPAND88** — the 1980s districts named in the returns were later carved up (Nowshera from
  Peshawar, Buner/Shangla from Swat, Haripur, Batagram, Lakki Marwat, Tank, Hangu, Narowal,
  Hafizabad, Mandi Bahauddin, Pakpattan, Lodhran, Chiniot, Nankana, Ghotki, Kashmore,
  Kambar-Shahdadkot, Naushehro Feroze, Mirpurkhas/Umerkot, the Tando districts, Jamshoro,
  Sajawal, Nushki, Washuk, Mastung, Awaran, Barkhan/Musakhail, Killa Saifullah/Sherani,
  Killa Abdullah, Jhal Magsi, Harnai/Lehri/Ziarat, Sohbatpur; FR regions attach to their
  adjoining districts). Each era district expands to its modern parts so no carved-out area
  is orphaned.
- **ATTACH** — scraped page titles truncated three composite seat names, so per the source's
  own index listing: NA-197 gets Chagai+Nushki ("Quetta Chagai"), NA-206 gets Gwadar
  ("Lasbela Gwadur"), NA-203 gets Nasirabad (the Naseerabad-division seat).

The 1985 layer (`na_207seat_1985numbering_reconstructed.geojson`) is rebuilt with the same
expansions, so it is also hole-free.

## 1977 and 1985 era layers — full-coverage rebuild (`patch_era_layers.py`)

The original 1977 build covered only ~53% of the country (its expansion table was
Punjab/Sindh-only). Both era layers now cover **100%**:

- Era carve-outs common to both: Peshawar+=Charsadda (1988), Mardan+=Swabi (1988),
  Multan+=Khanewal (1985), Jhelum+=Chakwal (1985 — Chakwal came mainly from Jhelum, partly
  Attock; assigned to Jhelum as a documented approximation).
- 1977 only: Kohat+=Karak (1982), Sargodha+=Khushab (1982), Sukkur+=Shikarpur (1977).
- **1977 Balochistan had only 7 seats, labelled Quetta/Sibi/Kalat — they covered whole
  divisions.** NA-194–196 span the Quetta Division districts, NA-197–198 the Sibi Division,
  NA-199–200 the Kalat Division (each listed explicitly in the script).
- Tribal seats in both eras carry the FR regions alongside the seven agencies.

`_preview.png` is a quick render of both files for eyeballing.
