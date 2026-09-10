# Search discovery

python3 scripts/build_seo.py writes the search metadata block (title, description, canonical, share tags, JSON-LD) into each hand-written page, regenerates sitemap.xml and robots.txt, and exports one constituency-summary CSV per election to data/results_by_year/ from the RESULTS literal embedded in the published map. The Method page lists those CSVs under Downloads and carries a DataCatalog / Dataset graph for them, so the results are discoverable as datasets without a second set of pages. python3 scripts/check_seo.py validates the rendered metadata, structured data and download links. Both run in CI.

There are no generated results pages: the September 2026 /elections/ archive was removed because it duplicated the map in a different design. The map keeps year and seat in its shareable URL (?year=&seat=), which is the address to give for a specific result. What the archive contributed on-page — an <h1> and a crawlable description of the map — now lives in map.html's own page-head block (kicker / h1 / lede, the same pattern as the other pages; scripts/patches/patch_map_heading.py), and the per-year CSVs plus their Dataset markup live on the Method page. The legacy src/map_template.html has a different interface and is not a safe replacement for the currently patched map; do not run an old map rebuild as part of this workflow, and preserve or port syncResultUrl() when replacing the explorer.

Generated CSVs are committed because GitHub Pages serves this repository directly; CI checks that regeneration is deterministic. Analytics loads only on aiwan.adaad.org.

After publication, submit https://aiwan.adaad.org/sitemap.xml in Search Console. GoatCounter measures arrivals, not search impressions or ranking.
