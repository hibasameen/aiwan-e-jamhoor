# Data provenance & licensing

The **code** in this repository is MIT-licensed (`LICENSE`). The **data** is a mix of
third-party datasets and datasets derived here from them. Read this before redistributing
any data file.

## Derived datasets produced by this project

The results JSON and the reconstructed/digitised boundary layers are released for reuse
under **Creative Commons Attribution 4.0 (CC-BY-4.0)** — *subject to the upstream terms
below*, which travel with any derivative. Attribute as: *"Aiwan-e-Jamhoor, with upstream
sources as noted."*

Files: `data/results_all.json`, `data/na_2018delim_v2.geojson`,
`data/na_2023delim_true_full.geojson`, `data/na_2023delim_simplified.geojson`,
`data/na_2023delim_app.geojson`, `data/results_2024/*.csv`, `data/na_2024_districts.csv`,
and the `data/digitised/*` manifests.

## Upstream sources and their terms

| Source | Used for | License / terms |
|--------|----------|-----------------|
| [Colin Cookman — `pakistan_elections`](https://github.com/colincookman/pakistan_elections) | 2008, 2013 results | **GPL-3.0** |
| [Colin Cookman — `pakistan_election_results_2018`](https://github.com/colincookman/pakistan_election_results_2018) | 2018 results | **GPL-3.0** |
| [ElectionPakistani](https://www.electionpakistani.com/) | 2024 candidate transcription | Unofficial aggregator; transcribe-and-verify. Treat as facts (vote counts), not creative content |
| Official ECP Form-47 scans | 2024 official figures | Government electoral records; user-supplied scans |
| [rugpundit — `PakistanConstituencies2013`](https://github.com/rugpundit/PakistanConstituencies2013) | 2002-delimitation polygons | **GPL-3.0** |
| ECP 2018 & 2023 delimitation map sheets | 2018/2023 boundary digitisation | Government delimitation records |
| [geoBoundaries](https://www.geoboundaries.org/) | district base layer | **CC-BY-4.0** |
| [OCHA COD](https://data.humdata.org/) admin boundaries | district base layer | **CC-BY** (per HDX dataset) |
| 2015 CartoDB district digitisation (via plotree) | reconstruction base | attribution requested; no formal license stated |
| Dawn/plotree GE-2018 geometry (centroids only) | reconstruction seeds | no license stated; used as seed points, not redistributed |

### Practical implications

- The **GPL-3.0 upstream on the 2008–2018 results and the 2002 boundaries** is the binding
  constraint on redistributing those specific derived files. If that matters to your use,
  either honour GPL-3.0 for those files or regenerate them from a differently-licensed
  source.
- The **geoBoundaries/COD base layers are CC-BY** — attribution required, commercial use OK.
- **Avoid GADM** for any public/commercial deployment (non-commercial license); this project
  uses GADM 3.6 only in two narrow Karachi carves — note it if you rebuild.
- The 2024 results are **provisional** and predate the final gazette; see `METHODOLOGY.md` §9.

*Aiwan-e-Jamhoor is independent and not affiliated with the Election Commission of Pakistan.*
