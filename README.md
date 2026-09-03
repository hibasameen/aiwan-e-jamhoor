# Aiwan-e-Jamhoor — ایوانِ جمہور

**The People's House** — an open record of Pakistan's National Assembly general elections
since 1977: eleven elections, every seat, every candidate, every vote count, drawn on the
constituency boundaries that were in force at the time.

Live at **[aiwan.adaad.org](https://aiwan.adaad.org/)**. This repository holds the site,
the data pipeline, the derived datasets and the methodology. It is a companion to
[Adaad](https://adaad.org/), a monthly data journal of Pakistan, alongside
[Data Darbar](https://darbar.adaad.org/).

> **Not affiliated with the Election Commission of Pakistan.** Boundaries are unofficial
> digitisations, traces and reconstructions; 2024 results are provisional; 1977–1997 results
> come from transcriptions and carry no per-seat turnout. Read
> [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) before citing, and
> [`docs/CORRECTIONS.md`](docs/CORRECTIONS.md) for what has been found wrong and fixed.

## The site

Static, self-contained pages; open the folder directly or serve it.

| Page | What it shows |
|------|---------------|
| `index.html` | Home — the House, election by election |
| `map.html` | Constituency results — eleven elections seat by seat, with seat histories that follow the ground rather than the number |
| `house.html` | The Full House — reserved seats for women and non-Muslims, 1977–2024: how they were filled, entitlement against ECP allocation, who held them |
| `candidates.html` | Candidates — careers, party switching, political families, linked across elections back to 1977 |
| `islam.html` | Islam & the Ballot — the religious vote by sect and by seat, 1988–2024 |
| `about.html` · `method.html` | What this is, who built it, sources, method and limitations |

```bash
python3 -m http.server 8000    # then open http://localhost:8000
```

Every chart exports as PNG and CSV, and every view has a share link that reopens the page
on the same tab and selection.

## Coverage

| Election | Seats | Boundary layer | How it was made |
|----------|-------|----------------|-----------------|
| 1977 | 200 | 1977 delimitation | reconstructed, approximate |
| 1985 | 207 | 1985 delimitation (non-party) | reconstructed, approximate, source numbering |
| 1988 · 1990 · 1993 · 1997 | 207 | 1985–1997 delimitation | traced from the published maps |
| 2002 · 2008 · 2013 | 272 | 2002 delimitation | third-party digitisation |
| 2018 | 272 | 2018 delimitation | digitised from ECP sheets |
| 2024 | 266 | 2023 delimitation | digitised; 203 seats high confidence, 44 medium, 19 low |

Korangi's three 2024 seats (NA-232 to NA-234) are reconstructed from the Form-7 town
compositions, because the published shapefile had them wrong.

## Repository layout

```
├── index.html · map.html · house.html · candidates.html · islam.html · about.html · method.html
├── docs/
│   ├── METHODOLOGY.md          the method, in full (authoritative)
│   ├── DATA_DICTIONARY.md      schema of every dataset
│   ├── DATA_LICENSE.md         provenance and upstream licences
│   ├── CORRECTIONS.md          the corrections log
│   ├── CROSSCHECK.md · BOUNDARIES_TODO.md · DEPLOYMENT.md · data_inventory.md
├── data/
│   ├── results_<year>/         per-seat results, 1977–2024
│   ├── results_all.json        every election, one file
│   ├── linked/                 the candidate spine: persons, candidacies, family clusters
│   ├── house/                  reserved-seat rosters and allocations
│   ├── boundaries/ · digitised/  constituency geometry by delimitation
│   └── sources/                curated inputs
├── hansard/linkage/            National Assembly membership rolls, 2nd–9th assemblies (see below)
├── scripts/                    the pipeline: scrape → results → boundaries → linkage → house → app
├── brand/ · fonts/             site assets
└── LICENSE · CITATION.cff · Makefile · requirements.txt
```

Large raw archives (ECP delimitation sheets, Form-47 scans, third-party district base
layers) are git-ignored; `docs/data_inventory.md` and `docs/DATA_LICENSE.md` say where each
comes from.

## Rebuilding

```bash
pip install -r requirements.txt
npm install -g mapshaper && npm install d3@7
make            # results → geometry → app
```

Two things that will bite (details in `docs/METHODOLOGY.md`): every GeoJSON must have
clockwise exterior rings and be `make_valid`-ed or d3-geo draws a filled rectangle; and the
shipped 2018 and 2024 layers were patched in surgically, so fix `scripts/build/build_map.py`'s
inputs before attempting a clean rebuild.

## Where this is going: the debates

The results tell you who was sent to the House. The next ambition is to record what they
did there. The National Assembly publishes its debates as scanned PDFs, in Urdu and English,
going back decades, and almost none of it is searchable. The plan is to digitise those
proceedings, structure them sitting by sitting and speech by speech, and link every speaker
to the same member record that the election pages already use, so that a constituency's
history runs from the ballot to the floor of the House.

The first piece is in place: `hansard/linkage/` holds the Assembly's own membership rolls
for the 2nd to 9th National Assemblies (1962–1997), transcribed from na.gov.pk, which
extend the member record back past the 2002 rolls the site already used. The rest is in
progress and will appear here as it is checked.

## Licensing

Code is MIT (`LICENSE`). Derived data is CC BY 4.0 **subject to upstream terms**: the
2008–2018 results derive from Colin Cookman's GPL-3.0 datasets and the 2002 boundaries from
a GPL-3.0 shapefile. Read [`docs/DATA_LICENSE.md`](docs/DATA_LICENSE.md) before
redistributing. Cite with `CITATION.cff`.

Corrections and questions: the About page says how to reach us. Errors are logged in
[`docs/CORRECTIONS.md`](docs/CORRECTIONS.md) with the evidence and the fix.
