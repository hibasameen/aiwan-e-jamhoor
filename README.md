# Aiwan-e-Jamhoor — ایوانِ جمہور

**The People's House** — an interactive record of Pakistan's National Assembly general
elections since 1977: eleven elections, every seat, every candidate, every party, mapped on
the constituency boundaries that were actually in force at each election.

This is the project's working repository — the static site, the data-processing and
map-building code, the derived datasets, and the full methodology.

> **Not affiliated with the Election Commission of Pakistan.** Constituency boundaries are
> unofficial digitisations/reconstructions/traces; 2024 results are provisional; results for
> 1977–1990 come from an unofficial transcription and carry no per-seat turnout. See
> [`METHODOLOGY.md`](METHODOLOGY.md) and [`DEPLOYMENT.md`](DEPLOYMENT.md) for the full list
> of limitations before citing.

## The site

Five static, self-contained pages (open directly, or serve the folder):

| File | Page |
|------|------|
| `index.html` | Home — the House election by election |
| `map.html` | The map — eleven elections, seat by seat (D3 + all data inlined, ~7 MB) |
| `candidates.html` | Dynasties — careers, party switching, political families |
| `about.html` | About — what this is, who built it, sources, licence |
| `method.html` | Method & sources — the methodology, in the site's style |

```bash
python3 -m http.server 8000    # then open http://localhost:8000
```

Everything the map needs is inlined, so it also runs offline and from any static host.

## Repository layout

```
Aiwan-e-Jamhoor/
├── index.html · map.html · candidates.html · about.html · method.html
├── og-image.png                     social-share card
├── METHODOLOGY.md                   full methodology (authoritative)
├── DATA_DICTIONARY.md               schema of every dataset
├── DEPLOYMENT.md                    deployment readiness + checklist
├── DATA_LICENSE.md                  data provenance + upstream licenses
├── data_inventory.md               survey of Pakistan election data sources
├── LICENSE · CITATION.cff · requirements.txt · Makefile
├── map_template.html                un-inlined app source (data placeholders)
├── brand/                           brand assets
├── scripts/                         the data & map pipeline
└── data/                            derived datasets + curated inputs
```

Large raw ECP source archives (delimitation sheets, Form-47 scans) and the big third-party
district base layers are **git-ignored** — they exceed hosting limits and carry their own
terms. `data_inventory.md` and `DATA_LICENSE.md` say where to obtain each.

## Rebuilding the data & maps

```bash
pip install -r requirements.txt
npm install -g mapshaper && npm install d3@7
make            # results -> baseline geometry -> app  (see Makefile)
```

Two non-negotiable build gotchas (details in `METHODOLOGY.md`):

- **d3-geo winding** — every GeoJSON must have clockwise exterior rings
  (`shapely.orient(sign=-1)`) and be `make_valid`-ed, or the map renders as a filled
  rectangle.
- **Do not do a naïve full rebuild.** The shipped app carries a newer 2018 layer than
  `scripts/build_map.py` references; the 2024 layer was swapped in **surgically** by
  `scripts/patch_app_2024.py`. Fix `build_map.py`'s 2018 input path before ever running a
  clean rebuild, or you will regress 2018.

## Data & results at a glance

| Year | Seats shown | Boundary vintage | Boundary confidence |
|------|-------------|------------------|---------------------|
| 2008 | 268 (4 postponed) | 2002 | third-party digitisation |
| 2013 | 269 (3 postponed) | 2002 | third-party digitisation |
| 2018 | 270 (2 postponed) | 2018 | digitised from ECP sheets |
| 2024 | 266 | 2023 | 203 high · 44 medium · 19 low |

## Licensing

Code is MIT (`LICENSE`). Derived data is CC-BY-4.0 **subject to upstream terms** — the
2008–2018 results derive from Colin Cookman's GPL-3.0 datasets and the 2002 boundaries from
a GPL-3.0 shapefile. Read [`DATA_LICENSE.md`](DATA_LICENSE.md) before redistributing data.

## Making this a git repository

```bash
git init -b main
git add .
git commit -m "Aiwan-e-Jamhoor: site, data pipeline, methodology & docs"
git remote add origin <your-remote-url>
git push -u origin main
```

If the folder lives in iCloud Drive, consider moving it to a normal local path first —
iCloud's file syncing and a live `.git` directory don't always coexist happily.
