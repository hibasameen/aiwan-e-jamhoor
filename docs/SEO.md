# Search discovery

python3 scripts/build_seo.py generates 11 election-year pages, 266 readable 2024 constituency pages, CSV downloads, an archive index and search metadata. It reads the JSON literal embedded in the published map plus the full 2024 candidate/Form 47 CSVs. It does not rebuild geometry or reconstruct elections from the incomplete four-year data/results_all.json.

Generated pages preserve the archive's mixed result vintages, the 1977 Qayyum League distinction, 1985 non-party status, missing historical turnout, five differing Form 47 winners, relevant transcription flags and upstream licensing/attribution. They are neither certified election-day returns nor current officeholder records. Older same-number seats are not asserted to be the same geography.

The published map now keeps year/seat in its shareable URL and links to readable results. The legacy src/map_template.html has a different interface and is not a safe replacement for the currently patched map. Do not run an old map rebuild as part of this publishing workflow. Preserve or port syncResultLink() when replacing the explorer.

Run python3 scripts/check_seo.py after generation. Generated HTML/CSVs are committed because GitHub Pages serves this repository directly; CI checks that regeneration is deterministic. Do not hand-edit generated result pages. Existing map/results data are unchanged. Analytics loads only on aiwan.adaad.org.

After publication, submit https://aiwan.adaad.org/sitemap.xml in Search Console and inspect an election-year URL and a seat URL. Track impressions/clicks for year, seat and candidate queries separately from branded searches. GoatCounter measures arrivals, not search impressions or ranking.
