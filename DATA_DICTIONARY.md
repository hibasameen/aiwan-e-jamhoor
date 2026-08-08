# Data dictionary

Field-level schema for every dataset the application consumes or the pipeline produces.
See [`METHODOLOGY.md`](METHODOLOGY.md) for how each was built and
[`DATA_LICENSE.md`](DATA_LICENSE.md) for provenance and reuse terms.

---

## `data/results_all.json` — the results the app reads

A single JSON object, keyed by election year, then by seat number. Produced by
`scripts/build_results_json.py`. Compact keys keep the inlined app small.

```jsonc
{
  "2024": {
    "NA-127": {
      "name": "Lahore-XI",        // constituency title (delimitation-specific)
      "prov": "Punjab",           // province
      "wp":   "Pakistan Muslim League (N)",  // winning party (full name)
      "wn":   "Waheed Alam Khan", // winner name
      "wv":   102080,             // winning votes            (null if unknown)
      "ws":   63.8,               // winner vote share, %     (null if unknown)
      "reg":  330154,             // registered voters        (null; blank for 2024 scrape-only seats)
      "to":   49.2,               // turnout, %               (null if unknown)
      "mov":  35.2,               // margin of victory, %     (null if unknown)
      "nc":   22,                 // number of candidates
      "cands": [                  // top-6 candidates, descending by votes
        { "n": "Waheed Alam Khan", "p": "Pakistan Muslim League (N)", "v": 102080, "s": 63.8 }
      ]
    }
  }
}
```

| Key | Type | Meaning | Notes |
|-----|------|---------|-------|
| `name` | string | Constituency title | Delimitation-specific; from source, seat titles for 2024 KP settled against Form-47 scans |
| `prov` | string | Province | Punjab / Sindh / KP / Balochistan / Islamabad / FATA (2008–2018) |
| `wp` | string | Winning party (full name) | 2024 PTI-backed winners appear as `Independent` |
| `wn` | string | Winner name | |
| `wv` | int\|null | Winning votes | |
| `ws` | float\|null | Winner share, % | 2024: over total tabulated candidate votes, not registered |
| `reg` | int\|null | Registered voters | 2024: from official Form-47 where available, else `null` |
| `to` | float\|null | Turnout, % | 2024: official Form-47 where available, else `null` |
| `mov` | float\|null | Margin of victory, % | winner − runner-up |
| `nc` | int | Candidate count | |
| `cands` | array | Top-6 candidates | `n` name, `p` party, `v` votes, `s` share % |

Postponed seats (hatched in the app) are absent from the year's object; the app carries the
postponed list per year in its `YEARS` config.

---

## Boundary GeoJSON layers

All coordinates are WGS-84 lon/lat. Exterior rings are stored **clockwise** for d3-geo (see
`METHODOLOGY.md` §3.3). Each `Feature` has a `geometry` (Polygon or MultiPolygon) and the
`properties` below.

### 1990s districts, projected onto 2002 seats — `data/districts_1990s.geojson` + `data/na2002_from_1990s.json` (1993, 1997)

No constituency boundaries survive in geospatial form for the 1977 delimitation, under
which the 207-seat National Assembly was elected from 1977 to 1997. The Election
Commission first published constituency maps for the 2002 delimitation. The 1993 and
1997 maps are therefore **district aggregates, not constituency maps**, and are not
comparable seat-for-seat with 2002 onward.

Built by `scripts/build_1990s_districts.py`, which dissolves present-day ADM2 polygons
back into the district units the returns name. Gilgit-Baltistan and Azad Jammu &
Kashmir are excluded — they elect no National Assembly members. Each present-day
district is folded into its October 1993 parent using a researched, sourced lineage
(for example Nankana Sahib into Sheikhupura, Korangi into Karachi East, Chiniot into
Jhang, the three Kohistans into Kohistan). Every in-scope present-day district is
assigned to exactly one unit per year, so the partition has no holes.

The unit set is **year-specific**: the 1997 returns name Shangla, Hangu, Malakand and
Upper/Lower Dir separately where 1993 folded them into Swat, Kohat and Dir, reflecting
districts created in the mid-1990s. Geometry identical across both years is stored once
(`y: "*"`); where it differs, one feature per year.

Known limits, all deliberate:

| Limit | Effect |
|---|---|
| 29 of 202 seats (1993) and 36 of 204 (1997) spanned two or more districts | counted in every district they name, so unit seat counts sum above the national total |
| A district is filled by the party winning most of its seats | ties (16 in 1993, 11 in 1997) are broken by the larger combined winning vote and flagged in the panel |
| Karachi's five 1993 reporting units were not all districts | Central and Malir were notified in 1996; Jamshed Town moved South→East in 2013. Karachi equivalences are approximate |
| Frontier Regions seat (1997 NA-34) | unmappable — its territory is now interior to six districts. Omitted; 203 of 204 seats are mapped |
| 1993 Malakand (NA-26) | went to a by-election on 2 Dec 1993, so it has no general-election result and is drawn as no-poll |
| Lehri district | created 2013 from Sibi + Bolan, abolished 2018; folded wholly into Sibi |

`data/districts_1990s_results.json` holds the per-unit aggregate: seat count, plurality
party, full tally, registered electorate, electorate-weighted turnout, the present-day
districts composing the unit, and the underlying seat list.

**How they are drawn.** The map does not draw these district units directly. Instead
`scripts/build_1990s_projection.py` projects each district result onto the 2002
constituencies (`data/na2002_from_1990s.json`), so all years from 1993 to 2013 share one
set of shapes. For each 2002 seat and each district it overlaps, the share of the
district assumed to fall inside the seat is `area(seat n district) / area(district)`;
that share of the district's registered electorate is split between parties in
proportion to the seats they won there, and the largest total shades the seat. The
district outlines are drawn over the fills so the real unit of information stays visible.

This assumes uniform electorate density within each source district. It is exact where a
2002 seat lies inside one district — 183 of 270 seats in 1993, 191 in 1997 — and weakest
in Balochistan, where 2002 seats span several sparsely populated districts. Winner-takes-all
assignment was rejected because it orphaned 13 districts' results entirely. The stored
record keeps `pur`, the winning party's share of the apportioned weight, and `one`, whether
the seat sits inside a single district; the hover text reports both. **These seats did not
exist in 1993 or 1997: the fill is the surrounding district's result, not the seat's.**

### 2002 delimitation — `data/na_constituencies_2002delim.geojson` (2002, 2008, 2013)

| Property | Type | Meaning |
|----------|------|---------|
| `na` | string | Seat number, e.g. `NA-127` |
| `prov` | string | Province |
| `dist` | string | District |
| `teh` | string | Tehsil (where present in source) |

270 of 272 seats (NA-95, NA-96 absent from source; results still searchable).

### 2018 delimitation — `data/na_2018delim_v2.geojson` (2018)

272 seats, digitised from ECP 2018 map sheets (`METHODOLOGY.md` §4). Carries `na`, `dist`,
province, and an `approx` flag on Voronoi-split city seats.

### 2023 delimitation — `data/na_2023delim_app.geojson` (2024)

The layer the app ships, produced by `scripts/build_2024_layer.py`.

| Property | Type | Meaning |
|----------|------|---------|
| `na` | string | Seat number |
| `dist` | string\|null | District label (carried from prior layer) |
| `approx` | bool | Internal line is approximate |
| `confidence` | string | `high` (203) · `medium` (44) · `low` (19) — see §5.6 |
| `src` | string | Provenance tag (sheet-split / district-composition / composition / voronoi …) |
| `rms_km` | float\|null | Outline-fit RMS error in km, for sheet-digitised seats |

Related files: `na_2023delim_true_full.geojson` (full-resolution 266-seat partition, the
authoritative geometry) and `na_2023delim_simplified.geojson` (2.2 MB, app-ready before the
`build_2024_layer` property pass).

---

## Source & intermediate CSVs

### `data/results_2024/na_2024_form47_official.csv`

254 seats read from official scanned ECP Form-47 forms. Every row arithmetic-checked.

`na, constituency_name, ps_total, reg_male, reg_female, reg_total, polled_male,
polled_female, polled_total, valid_votes, rejected_votes, turnout_pct, winner_name,
winner_party, winner_votes, runnerup_name, runnerup_party, runnerup_votes, n_candidates,
form_date, flags`

`flags` is non-empty (~20 seats) where a field on the form is illegible or internally
inconsistent. 12 seats have no form (NA-1, 2, 4, 7, 8, 12, 14, 16, 19, 20, 21, 22).

### `data/results_2024/na_2024_constituency.csv` / `na_2024_candidates.csv`

The ElectionPakistani transcription: one row per seat (winner/runner-up) and one row per
candidate (`na, candidate_name, party, votes`). Source and caveats in
`data/results_2024/SOURCES.md`.

### `data/na_2024_districts.csv`

The 2023-delimitation seat → district crosswalk (266 rows; 21 multi-district "cum" seats),
built for this project. Columns: `na`, `districts` (semicolon-separated). Drives the canvas
construction in `build_2023_canvases.py` and the reconstruction seeds.

### Cookman inputs (2008–2018)

`data/cookman_pk_candidate_data.csv`, `cookman_pk_constituency_data.csv` (1970–2013) and the
`cookman_2018_*` files. Upstream schema documented in Cookman's repositories; the columns the
pipeline reads are listed in `scripts/build_results_json.py`.

### `data/digitised/kp_bal_ict_seat_manifest.csv`

Per-seat provenance for the 36 KP/Balochistan/ICT seats built by composition: method,
sourced composition, confidence, and notes.
