# scripts/ — what lives where

`make` drives only `build/`. Everything else is upstream data preparation or a one-off
that was run once and kept for the record.

**Folders group scripts that import each other.** Each script that imports a sibling
starts with a short path shim that puts every `scripts/<group>/` directory on
`sys.path`, so a script can be run from anywhere:

```bash
python3 scripts/build/build_map.py        # from the project root
```

This replaced the old hard-coded `sys.path.insert(0, 'scripts')` lines, which only
worked when run from the project root (and one of which pointed at `/root/aiwan/scripts`,
a path that no longer exists).

---

## `build/` — 4 scripts

The shipped pipeline. These are the four scripts `make` actually runs; everything else is
upstream of them or a one-off.

| script | purpose |
|---|---|
| `build_2024_layer.py` | Prepare the app's 2024 layer from the true 2023-delimitation boundaries |
| `build_hemicycles.py` | Regenerate the home-page hemicycle strip from the map's own results, so every election on the map appears there too |
| `build_map.py` | Assemble the self-contained map app (aiwan_e_jamhoor_map.html) |
| `build_results_json.py` | Build results_all.json — per-year, per-constituency results powering the map app |

## `scrape/` — 6 scripts

Result scrapers and their offline cache parsers, for the pre-2002 elections. Scrapers need
network; the `parse_*` companions do not.

| script | purpose |
|---|---|
| `parse_ge1988_cache.py` | Parse cached GE-1988 constituency pages into the data/results_1988/ CSVs |
| `parse_gecache.py` | Parse cached ElectionPakistani constituency pages into data/results_{year}/ CSVs |
| `scrape_ge1977.py` | Scrape the 1977 (non-party) National Assembly results from ElectionPakistani |
| `scrape_ge1985.py` | Scrape the 1985 (non-party) National Assembly results from ElectionPakistani |
| `scrape_ge1988.py` | Scrape the 1988 National Assembly results from ElectionPakistani, in the same shape as data/results_1990/ |
| `scrape_ge1990.py` | Scrape the 1990 National Assembly results from ElectionPakistani, in the same shape as data/results_2024/ |

## `historic/` — 5 scripts

Reconstruction of the pre-2002 reporting units and the projection of 1993/1997 district results
onto 2002 constituencies.

| script | purpose |
|---|---|
| `build_1990s_districts.py` | Reconstruct the district units used to report the 1993 and 1997 National Assembly returns, by dissolving present-day ADM2 polygons into them |
| `build_1990s_projection.py` | Project the 1993 and 1997 district-level results onto the 2002-delimitation constituencies by areal apportionment |
| `build_historic_results_json.py` | Convert the scraped results_{1977,1985,1988} CSVs into the window.RESULTS schema used by map.html, and emit per-year headline stats for the ELEC conte |
| `labels_1990.py` | 1990 constituency labels from the 9th National Assembly roster (Wikipedia) |
| `normalise_1990_titles.py` | Normalise the scraped 1990 constituency titles into the same convention the 1993 and 1997 returns use, so the existing district pipeline handles 1990 |

## `boundaries/` — 15 scripts

Constituency geometry: Voronoi reconstruction, tracing of the labelled Commons maps,
tessellation, and assembly of the 266-seat 2023 layer.

| script | purpose |
|---|---|
| `assemble_2023_partial.py` | Assemble all resolved 2023-delimitation seats into na_2023delim_true_partial.geojson: - 38 single-seat canvases from out/seats_2023_scaffold.geojson - |
| `assemble_266.py` | Merge the 36 new KP/Balochistan/ICT seats into the 230-seat partial layer, clean slivers/overlaps, and verify a 266-seat exact national partition |
| `build_historic_geometry.py` | Reconstruct approximate NA constituency boundaries for the two pre-2002 delimitations, from the scraped constituency->district information: * 200-seat |
| `build_map_numbering.py` | Fix the numbering foundation for the 207-seat (1985–1997) delimitation |
| `build_reconstructed_geometry.py` | Reconstruct approximate NA constituency boundaries for the 2018 and 2023 delimitations |
| `crosscheck_commons_maps.py` | Cross-check our results against the labelled Commons maps |
| `extract_1977_boundaries.py` | Extract true 1977-delimitation constituency boundaries from a labelled map |
| `fill_holes.py` | Close internal gaps in na_2018delim_v2.geojson so all boundaries tile contiguously |
| `merge_traced_boundaries.py` | Merge the three traced Commons maps (1990/1993/1997 |
| `merge_traced_v2.py` | Merge the v2 traces (na_traced2_{1990,1993,1997}.geojson) into the final 207-seat boundary set, with placement validation |
| `patch_finalize_boundaries.py` | Final boundary fix in map.html: * GEOS['207seat'] <- merged v2 traced set (162 main + 21 inset + 16 low-conf + 8 Voronoi), correct inset placement, va |
| `patch_swap_traced.py` | Swap the all-Voronoi GEOS['207seat'] in map.html for the map-traced boundary set (176 traced from the 1990/93/97 Commons maps + 31 reconstructed fallb |
| `tessellate_207.py` | Turn the merged traced boundary set into a complete tessellation of the National Assembly area |
| `trace_commons_full.py` | Full trace of a labelled Commons election map: main map + EVERY inset box, label gating, and district-elimination gap fill |
| `trace_commons_map.py` | Trace true constituency polygons from a labelled Commons election map |

## `digitise/` — 19 scripts

Digitisation of the ECP delimitation map sheets — the georeferencing toolkit plus the per-
province drivers and their fix-ups. This is the heaviest, most manual part of the project.

| script | purpose |
|---|---|
| `audit_city_districts.py` | Audit our 2024 constituency partition against the PBS/ECP "Preliminary Delimitation 2023" district maps Hib saved in "sources/2023 Delimitation/NA/" |
| `build_2023_canvases.py` | Build the 2023-delimitation district layer and digitisation canvases |
| `compose_kp_bal_ict.py` | 2023-delimitation composition build for the 14 remaining canvases (KP 27 seats, Balochistan 7, ICT 3 = 36 seats -> 266/266) |
| `digitise_quetta.py` | Sheet-digitise the Quetta 3-seat canvas from the ECP representation sheet (Muhammad Mobeen Khilji, NA-262/263/264) |
| `digitise_sheet.py` | Digitise one ECP delimitation map sheet (district revenue map with colour-coded NA constituencies and a printed UTM grid) into true-boundary GeoJSON |
| `fix_dgkhan.py` | DG Khan (NA-189..192) re-split |
| `fix_karachi_canvases.py` | Rebuild the six Karachi 2023 canvases from the 2018 layer's district footprints |
| `fix_larkana_taluka.py` | Upgrade NA-200/201 (Larkana) from district-wide centroid Voronoi to a taluka-composition split |
| `georef_map.py` | Georeference a labelled Commons election map by fitting its drawn National Assembly area to the true one |
| `georef_refine.py` | Refine the affine georeference with a quadratic warp |
| `read_labelled_map.py` | Segment a labelled Commons election map into constituency regions, then OCR the NA number printed inside each one |
| `rebuild_malir_from_prelim.py` | Rebuild NA-229/230/231 (District Malir, 2023 delimitation) from the PBS/ECP "District Malir — Preliminary Delimitation 2023" map supplied by Hib |
| `rebuild_malir_v2.py` | Malir rebuild v2 from the PBS/ECP prelim-2023 map |
| `run_kp_fata_ict.py` | Leg 2 driver: upgrade all KP + FATA + ICT 2018 seats in na_2018delim_v2.geojson |
| `run_punjab.py` | Leg 3 driver: Punjab 2018 |
| `run_punjab_fix.py` | Recover the 5 Punjab districts that fell back to Voronoi in run_punjab.py (Lahore, Multan, Bhakkar, Rawalpindi, Gujranwala — 35 seats) |
| `run_sindh.py` | Leg 4 driver: Sindh 2018 |
| `run_sindh2.py` | Sindh v2: fixes over run_sindh.py: - content-blob union for outline fit on sheets with weak/absent fills (use_blob) - relaxed saturation gates for pal |
| `split_district_by_sheet.py` | Split a known district polygon along the internal constituency lines of an ungridded ECP delimitation sheet |

## `patches/` — 9 scripts

Surgical edits applied to already-built HTML. They rewrite the shipped files in place rather
than regenerating them — see the build gotchas in README.md before running any of these.

| script | purpose |
|---|---|
| `patch_2024_city_detail.py` | Restore digitised detail to the 2024 city constituencies in map.html |
| `patch_add_historic_years.py` | Surgically add the pre-2002 elections (1977, 1985, 1988) to map.html and switch 1990/1993/1997 onto the reconstructed 207-seat boundaries |
| `patch_app_2024.py` | Surgically swap the 2024 boundary layer inside the built app and add the provisional-boundary treatment, without rebuilding 2002/2018 from source (the |
| `patch_city_ui_fix.py` | UX fixes for the city-zoom feature: 1 |
| `patch_city_zoom.py` | Add "zoom to city" chips to the map: Karachi, Lahore, Islamabad-Rawalpindi, Faisalabad, Peshawar, Quetta, plus a Whole-country reset |
| `patch_election_notes.py` | Add a per-election context card ("This election") to the map's side column, and a sourced "The four elections" section to the Method page |
| `patch_era_layers.py` | Rebuild the 1977 (200-seat) and 1985 (own-numbering 207-seat) Voronoi layers with full era coverage, then swap them into map.html |
| `patch_home_hemicycles.py` | Add 1977 / 1985 / 1988 hemicycle cards to index.html, matching the existing static hemicycle SVGs (cx=110, cy=118, outer R=104, inner r=54, 180deg->0d |
| `patch_method_elections.py` | Add a sourced 'The four elections' section to method.html (anchor #elections) and mirror a condensed version into docs/METHODOLOGY.md |

## `linkage/` — 8 scripts

Candidate/person linkage spine across elections, and the careers & dynasties explorer built on
top of it.

| script | purpose |
|---|---|
| `apply_overrides.py` | Apply agent-verified splits and merges to the spine; rebuild persons; emit dynasties.json |
| `build_candidates.py` | — |
| `build_explorer.py` | Assemble the self-contained careers & dynasties explorer HTML |
| `build_spine.py` | Build unified candidacy table + cross-election person linkage spine |
| `career_analysis.py` | Career analysis from the linked spine: party switching, longest-serving, seat moves |
| `career_ext.py` | Career analysis over the 1977-2024 extended spine |
| `dynasty_cluster.py` | Dynasty clustering: family clusters of candidates sharing rare surname/clan tokens within a district |
| `extend_spine.py` | Extend the linked spine back to 1977/1985/1988/1990 WITHOUT disturbing existing person ids |

Also: `candidates_template.html`, `dynasties_verified.json`, `explorer_template.html`, `overrides.json`.

---

## Known broken

`boundaries/extract_1977_boundaries.py` imports `georef`, `georef2` and `segment_map`,
none of which exist anywhere in the repo. It was already broken before this
reorganisation and is kept only for the record. The working equivalents are
`digitise/georef_map.py`, `digitise/georef_refine.py` and `digitise/read_labelled_map.py`.

`patches/patch_election_notes.py` references `scripts/summarise_elections.py` in its
docstring; that file does not exist either.
