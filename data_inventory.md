# Aiwan-e-Jamhoor — Data Availability Inventory

**Pakistan National Assembly elections since 2008: results, candidates, parties, and constituency boundaries**
*Compiled 19 July 2026*

---

## 1. The landscape at a glance

| | GE-2008 | GE-2013 | GE-2018 | GE-2024 |
|---|---|---|---|---|
| **Delimitation in force** | 2002 (272 general seats) | 2002 (272) | 2018 (272, post-2017 census) | 2022–23 (266, post-2023 census) |
| **Official ECP results** | PDFs on old site | Two-volume report + statistics PDFs | Form-47 PDFs + scanned Forms 45–49; brief machine-readable feed | EMS portal + scanned Forms 45–49 (image PDFs) |
| **Best machine-readable results** | Cookman `pakistan_elections` (candidate-level CSV) | Cookman `pakistan_elections` | Cookman `pakistan_election_results_2018` (candidate + constituency CSVs); polling-station-level CSVs also exist | **Gap** — no neutral consolidated open dataset; Gallup dashboard, FAFEN interface, Kaggle uploads, PTI Form-45 portal |
| **Polling-station-level data** | No | No | Yes (Cookman/Sonnet digitisation, USIP-funded) | Scans only (Form 45/48 PDFs) |
| **Constituency GIS (polygons)** | Yes — rugpundit + ALHASAN shapefiles (2002 delimitation) | Same | **Partial** — no clean public NA shapefile; geometry embedded in Dawn/plotree web-app; Punjab PA reconstruction exists | **Gap** — no public vector dataset of the 266 seats found |

Two structural facts shape everything: **ECP has never released official GIS files** (all boundary vectors in circulation are third-party digitisations of low-res PDF/JPG map sheets), and **constituency numbers are not comparable across delimitations** (NA-120 in 2013 ≠ NA-120 in 2018 ≠ anything in 2024; no official crosswalk exists).

---

## 2. Election results, candidates, and parties

### 2.1 ECP (official)

ECP's publications are authoritative but almost entirely PDF, much of it image scans. The site has migrated at least twice, so link rot is endemic — Wayback Machine often needed for 2008/2013-era pages. Note: ECP's site blocks automated fetching, so ECP links below were confirmed via search indexes, not fetched directly.

- **Hub:** [General elections index](https://ecp.gov.pk/general-elections) · [GE-2024 page](https://ecp.gov.pk/general-elections-2024) · [Party position](https://ecp.gov.pk/party-position) · [Electoral databases](https://ecp.gov.pk/electoral-databases)
- **GE-2008:** consolidated results/candidate PDFs, e.g. [ge2008-g1.pdf](https://ecp.gov.pk/storage/files/1/ge2008-g1.pdf). No polling-station data.
- **GE-2013:** official report [Vol I](https://ecp.gov.pk/storage/files/1/ger-1.pdf) (narrative) and [Vol II](https://ecp.gov.pk/storage/files/1/ger-2.pdf) (constituency result annexes); statistics PDFs (party-wise vote bank, turnout with gender split). No polling-station-level release — a known gap.
- **GE-2018:** [Form-47 provisional results](https://ecp.gov.pk/general-election-2018-provisional-result-form-47); [scanned Forms 45/46/47/48/49](https://ecp.gov.pk/ge-2018-scanned-forms-form-4546474849) per constituency. ECP also briefly published machine-readable candidate-level results in mid-2018 (since removed) — this feed is what Cookman and others scraped.
- **GE-2024:** [EMS results portal](https://www.elections.gov.pk/national-assembly) (per-constituency pages, NA + 4 PAs); [scanned Forms 45–49](https://ecp.gov.pk/form4546474849). All image PDFs, not machine-readable. By-elections: [bye-elections pages](https://ecp.gov.pk/bye-elections-2024) with Form-47 PDFs per event.

**Form hierarchy** (matters for what "the result" means): Form-45 = polling-station count → 46 = ballot account → 47 = provisional constituency consolidation → 48 = consolidated station-wise → 49 = final gazetted result. Most datasets in circulation (Gallup 2024, media portals, Cookman's initial 2018 scrape) are Form-47-derived provisional figures, not the final Form-49/gazette numbers.

### 2.2 Colin Cookman's GitHub — the backbone open series

All CSV, GPL-3.0, documented. This is the single best starting point for your database.

| Repo | Coverage | Unit | Notes |
|---|---|---|---|
| [pakistan_elections](https://github.com/colincookman/pakistan_elections) | National elections **1970–2013** (incl. 2008, 2013) | Candidate & constituency | From ECP site/gazettes + FAFEN/CWS 1970–2008 compendium. README candid about transcription errors |
| [pakistan_election_results_2018](https://github.com/colincookman/pakistan_election_results_2018) | GE-2018, NA + all 4 PAs | Candidate & constituency | `pk_candidate_data_2018.csv`, `pk_constituency_data_2018.csv` (registered voters, turnout, valid/rejected, margins) + vote-discrepancy documentation. Provisional as of Sep 2018 |
| [pakistan_polling_stations_2018](https://github.com/colincookman/pakistan_polling_stations_2018) | GE-2018 | **Polling station** | Forms 28/45/48 digitised from scans (USIP-funded, with Luke Sonnet). ~200–230MB CSVs on OSF with codebooks. Includes **census-block ↔ polling-station ↔ constituency linkage** — the key crosswalk asset. No lat/lon coordinates |
| [pakistan_candidate_registry_18](https://github.com/colincookman/pakistan_candidate_registry_18) / [pakistan_candidate_scrutiny_18](https://github.com/colincookman/pakistan_candidate_scrutiny_18) | GE-2018 | Candidate | Nomination and scrutiny (assets/education) data |
| [pakistan_census](https://github.com/colincookman/pakistan_census) | 2017 census | Census block | For constituency–census linkage |

**No Cookman GE-2024 repo exists** as of this check.

### 2.3 FAFEN

- [GE-2024 NA results assessment](https://fafen.org/assessing-national-ge-2024-assembly-election-results/) — interactive per-constituency query tool (registered voters, turnout, invalid/rejected votes and whether they exceeded the margin, comparisons to 2013/2018). Closest thing to a neutral 2024 constituency-level compilation, but no bulk download exposed.
- [GE-2024 party votes/seat shares analysis](https://fafen.org/fafen-releases-analysis-of-party-votes-and-seat-shares-in-ge-2024/) · [preliminary observation report](https://fafen.org/wp-content/uploads/2024/02/FAFEN-Preliminary-Report-on-Observation-of-GE-2024-1.pdf) · [2018 results analysis](https://fafen.org/2018-general-election-results-analysis/) (the 2018 portal Cookman cross-checked against is now defunct).
- [openparliament.pk](http://openparliament.pk/) — MNA profiles and parliamentary performance; good for winner/party crosswalks, not raw returns.
- The FAFEN/Church World Service **"Electoral History of Pakistan 1970–2008"** compendium underlies most pre-2013 digitisations; circulates as PDF only.

### 2.4 Gallup Pakistan

- [Electoral History Dashboard 1970–2018](https://galluppakistandigitalanalytics.com/gallup-pakistan-electoral-history-dashboard/) — 11 general elections, ECP-derived, interactive.
- [GE-2024 dashboard](https://galluppakistandigitalanalytics.com/general-elections-2024-pakistan-dashboard/) — Form-47-based: constituency scorecards, seats/vote shares, margins, turnout, rejected votes, postal ballots. Visualisation-first; limited export.

### 2.5 Academic / international

- **[CLEA](https://electiondataarchive.org/data-and-documentation/)** (Constituency-Level Elections Archive, U. Michigan) — includes Pakistan NA elections at constituency × candidate/party level, harmonised party codes, Stata/CSV. Free with registration. Confirm whether the current release includes 2024.
- **[IPU Parline](https://data.ipu.org/parliament/PK/PK-LC01/election/PK-LC01-E20240208/)** — national-level seat totals, women's representation, back to the 1970s. CSV/XLS export.
- **Harvard Dataverse** — replication archives per paper (e.g., Cheema/Khan/Liaqat/Mohmand APSR 2023, polling-station-level women's turnout in Lahore GE-2018). No standing Pakistan portal; search per paper.

### 2.6 Unofficial aggregators (useful, verify before trusting)

- **[ElectionPakistani.com](https://www.electionpakistani.com/)** — HTML tables, 1970–2024, candidate-level, including the **only consolidated by-election series since 2008**. Unofficial transcription; scrape-and-verify.
- **[uns1/PakElection2018](https://github.com/uns1/PakElection2018)** — independent GE-2018 scrape (270/272 NA seats, snapshot 29 Jul 2018) with HDI linkage; useful for cross-validation against Cookman (different scrape dates → different provisional figures).
- **[Open Data Pakistan](https://opendata.com.pk/dataset?tags=elections)** — Election Database 1970–2018 (SPSS), Elections-2018 findings (CSV/XLSX), plus the ALHASAN GIS files (§3).
- **Kaggle** — several 1970–2018 and 2024 uploads of mixed quality/provenance ([1970–2018](https://www.kaggle.com/datasets/tahminashoaib86/pakistan-general-elections-dataset-1970-2018), [Forms-45 2024](https://www.kaggle.com/datasets/nhussainzaidi/forms-45-pakistan-general-elections-2024)).
- **Wikipedia** — per-constituency articles (NA-1…NA-266) and members-of-assembly lists; CC-BY-SA; citation quality varies.

### 2.7 GE-2024 special situation

There is **no neutral, consolidated, machine-readable GE-2024 results dataset** equivalent to Cookman's 2018 work. What exists:

- ECP EMS + Form scans (official, image PDFs; the EMS failure and >3-day delay is itself a documented caveat).
- Gallup dashboard and FAFEN interface (Form-47-derived, no bulk export).
- **[PTI Form-45 portal](https://insafpk.github.io/form45-portal/)** — the largest Form-45 digitisation (179 NA+KP seats, alleging discrepancies vs Form-47 on 87); partisan provenance, treat as claims data with evidence images.
- **[Pattan audit reports](https://pattan.org/v2/ge-2024/)** — Form-47 audit ("78% deficient"), Form-45 audit, constituency case studies; PDF reports, no dataset.
- Election tribunals altered several results after Feb 2024, and the reserved-seat allocation changed with the July 2024 Supreme Court judgment — any static 2024 dataset diverges from current seat-holders. Your database will need a "results as declared" vs "current holder" distinction.

---

## 3. Constituency boundaries and maps over time

### 3.1 Official ECP delimitation material (the ground truth, but not GIS)

ECP output per delimitation = per-constituency **PDF/JPG map sheets** + written descriptions (Form-5 in 2018, Form-7 in 2023) listing the tehsils/patwar circles/census charges composing each seat.

- **2023 delimitation (GE-2024, 266 seats):** [Final delimitation with maps](https://ecp.gov.pk/delimitation-2023) — Form-7 bundles per province, corrigenda, court-remand revisions. A [single-PDF compendium of all 2024 NA map sheets](https://www.scribd.com/document/701904896/Pakistan-National-Assembly-2024-Constituency-all-maps) circulates on Scribd. [FAFEN's delimitation analysis](https://fafen.org/wp-content/uploads/2024/02/240202-GE-2024-Delimitation-of-Constituencies.pdf) tabulates the changes.
- **2018 delimitation (GE-2018, 272 seats):** [Final delimitation 2018](https://ecp.gov.pk/final-delimitation-2018) · [2018 maps](https://ecp.gov.pk/delimitation-2018-maps) — per-district JPG/PDF sheets.
- **2002 delimitation (GE-2002/2008/2013):** no live ECP page; survives via archive.org and third-party digitisations.
- ECP/NADRA built an **internal GIS** for the 2018 and 2022 delimitations (UNDP-supported polling-station geotagging) but has never released vectors.

### 3.2 Available vector data by delimitation vintage

**2002 delimitation (covers GE-2008 and GE-2013) — good coverage:**

- **[rugpundit/PakistanConstituencies2013](https://github.com/rugpundit/PakistanConstituencies2013)** — shapefiles for NA (272) + all PAs. Digitised from ECP raster maps; GPL-3.0; the de-facto standard file in research. README is candid: not official, boundaries approximate.
- **ALHASAN Systems shapefiles** (compiled pre-GE-2013, CC-BY): [NA boundaries](https://opendata.com.pk/dataset/national-constituency-boundaries-pakistan) ([direct ZIP](https://opendata.com.pk/dataset/e263730b-1492-466d-8452-e1c95d9a69bd/resource/c5f54f30-fd7f-45df-8426-faf71f726871/download/national-constituency-boundary.zip)) and [PA boundaries](https://opendata.com.pk/dataset/provincial-regional-constituency-boundaries-pakistan) ([direct ZIP](https://opendata.com.pk/dataset/97db56cb-d9e7-47f4-aed4-b2e550171e9d/resource/e083bb31-519e-4d92-bdea-c518ff03e3ff/download/provincial-constituency-boundary.zip)). Also on [HDX](https://data.humdata.org/dataset/national-constituency-boundaries-pakistan).

**2018 delimitation (covers GE-2018) — partial, no clean public NA shapefile:**

- The Dawn/plotree GE-2018 interactive map embeds the 272-seat geometry inside its web-app assets: [plotree/elections](https://github.com/plotree/elections) (fork of [hasankhalid/electionMap](https://github.com/hasankhalid/electionMap)); successor archive at [elections.plotree.fun](https://elections.plotree.fun/) covers 1970–2024. Geometry is extractable from the repo's TopoJSON but no license is stated — worth contacting the authors.
- **[Mamooralikhan/punjab-pp-boundaries](https://github.com/Mamooralikhan/punjab-pp-boundaries)** — Punjab PA only (297 seats), reconstructed via Voronoi tessellation of GPS-located polling stations plus georeferenced ECP map sheets (~200–1,000 m accuracy, method fully documented, CC-BY-4.0). Matters because **the method is extendable to NA seats**.
- Wikimedia Commons has hand-drawn SVG maps per delimitation (not georeferenced — usable for schematic maps, not spatial joins).

**2023 delimitation (covers GE-2024, 266 seats) — genuine gap:**

- **No public vector dataset found** as of July 2026. [rugpundit/PakistanConstituencies2023](https://github.com/rugpundit/PakistanConstituencies2023) exists but is an empty placeholder — watch it. News interactives (Geo, Dunya, Business Recorder) and an [ArcGIS Experience dashboard](https://experience.arcgis.com/experience/21a68bd1caad4d02a41eff9d2435a3dc/) display 2024 constituencies but publish no downloads.

### 3.3 Supporting layers for crosswalks and reconstruction

- **Polling-station points:** [ALHASAN polling-station GIS points](https://opendata.com.pk/dataset/pakistan-polling-stations) ([direct ZIP](https://opendata.com.pk/dataset/0965cf0d-abce-49fe-ab80-333ed598d137/resource/8fe02e7a-8dc5-4109-b184-7b6fa486797e/download/polling_station_pakistan.zip), pre-GE-2018, CC-BY); ECP polling-scheme PDFs (some with GPS columns); [PakVoter polling schemes](https://pakvoter.org/polling-schemes/) for all 272 GE-2018 NA seats.
- **Admin boundaries:** [OCHA COD adm0–3](https://data.humdata.org/dataset/pakistan-administrative-level-0-1-2-and-3-boundary-polygons-lines-and-central-places); [geoBoundaries](https://data.humdata.org/dataset/geoboundaries-admin-boundaries-for-pakistan) (CC-BY); GADM (non-commercial license — avoid for a public site); [ALHASAN union-council boundaries](https://data.humdata.org/dataset/pakistan-union-council-boundaries-along-with-other-admin-boundaries-dataset) — UC level is what the Form-5/7 written descriptions reference, making it the key layer for faithful digitisation.
- **Census geography:** [PBS GIS page](https://www.pbs.gov.pk/gis/) — 2023 census enumeration blocks (185,489) and the **Delimitation Plan 2023** exist digitally, but public downloads are PDF only; **shapefiles available on request to pbs@pbs.gov.pk** (worth an email). 2017 census tabular data: [colincookman/pakistan_census](https://github.com/colincookman/pakistan_census).
- **The crosswalk problem:** NA numbering changes across delimitations and there is no official concordance. The census-block ↔ polling-station ↔ constituency linkage in Cookman's polling-station repo is the best bridge for 2018; UC/census-block layers are the stable spine for any 2013↔2018↔2024 crosswalk. The FATA→KP merger (2018) is the biggest discontinuity.

---

## 4. What this means for Aiwan-e-Jamhoor

**Ready to use now:** Cookman's three results repos give you candidate-level NA results for 2008, 2013, and 2018 in tidy CSVs; rugpundit + ALHASAN give you 2002-delimitation polygons for the 2008/2013 maps. That's two of your four elections fully mappable almost immediately.

**Requires assembly:** GE-2018 maps need the plotree/Dawn TopoJSON extracted (or an NA-level Voronoi reconstruction from polling-station points). GE-2024 needs both a results dataset (scrape ECP EMS / digitise Form-47s / negotiate FAFEN export) and boundary digitisation from ECP Form-7 map sheets — nobody has published either openly, which also means **building them would make Aiwan-e-Jamhoor the reference source**.

**Data-model implications from the caveats:**

1. Store results with a **source + form-type + snapshot-date** provenance field (Form-47 provisional vs Form-49 final vs tribunal-revised differ, especially for 2018 and 2024).
2. Treat **delimitation vintage as a first-class entity** — constituencies belong to a delimitation, not to "the NA" — so NA-120 (2002), NA-120 (2018), and NA-120 (2023) never collide.
3. Keep a **caveats layer**: boundary polygons are unofficial digitisations (hundreds of metres of error, worst in Karachi/Lahore urban seats); 2018/2024 results carry documented discrepancies.
4. Licenses are workable: Cookman GPL-3.0, ALHASAN CC-BY, geoBoundaries CC-BY. Avoid GADM (non-commercial) for a public site; get permission for plotree geometry.

**Sensible next steps** (in rough order): download and stage the Cookman CSVs + 2002-delimitation shapefiles; extract/verify the 2018 NA geometry from the plotree repo; email PBS for census/delimitation shapefiles; scrape ECP EMS constituency pages for 2024 Form-47 figures; then digitise the 2024 boundaries from Form-7 sheets against the UC layer.

---

## 5. Verification note

Links marked as ECP could not be fetched directly (ECP blocks automated access) and were confirmed via search indexes — expect some link rot given ECP's site migrations; the Wayback Machine holds copies of most older pages. GitHub, Open Data Pakistan, FAFEN, Gallup, PakVoter, PBS, and plotree links were fetched and verified during this research (July 2026). HDX links exist but the site blocks automated access; the Open Data Pakistan mirrors were verified with working direct ZIPs.
