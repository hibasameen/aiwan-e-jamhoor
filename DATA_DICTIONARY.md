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

### 2002 delimitation — `data/na_constituencies_2002delim.geojson` (2008, 2013)

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
