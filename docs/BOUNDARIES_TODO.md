# Recovering true pre-2002 constituency boundaries

**Status: extractor runs end to end and produces 162 of 207 seats for 1997. Not shipped — see 'Where it stands'.** 1990, 1993 and 1997
are still drawn as district aggregates projected onto the 2002 shapes. This note
records what works, with measurements, and what remains.

## Why this is possible

The 1977 delimitation — 207 general seats, used 1977 to 1997 — was never
published in geospatial form. But `data/sources/` holds labelled constituency
maps for 1990, 1993 and 1997 (Saad Ali Khan Pakistan, CC BY-SA 4.0, ~3,500 px)
which draw those boundaries and **print each seat's NA number inside its
region**, so identity does not have to be inferred.

Their fidelity is measured: `CROSSCHECK.md` reports 1,023 seats checked across
six elections at 99.2% consistency with our independent results.

## What works

**Segmentation and labelling** — `scripts/read_labelled_map.py` finds the
flat-filled regions and OCRs the number inside each. On the 1997 map: 366
regions, 157 labels read (~76%).

**Georeferencing** — `scripts/georef_map.py` and `scripts/georef_refine.py`.
The insight that makes it work: the map's party-coloured pixels and the union of
`data/na_constituencies_2002delim.geojson` describe *the same territory* —
Pakistan's National Assembly area, excluding Kashmir and Gilgit-Baltistan — so
the two masks can be aligned directly, no control points needed. Kashmir and GB
are `#7f7f7f` grey plus diagonal hatching and are excluded from the mask.

Fit quality on the 1997 map:

| Stage | IoU | Median edge error | p90 |
|---|---|---|---|
| Moment start | 0.62 | — | — |
| Affine, optimised on IoU | 0.919 | 7.1 km | 23.9 km |
| Quadratic warp | 0.934 | 4.8 km | 16.8 km |

For contrast, the approach tried first — control points from each labelled
region's district centroid — reached only 24-39 km median. **Do not go back to
control points.** Fit mask to mask.

**End-to-end check.** Pushing each labelled region's centroid through the warp,
66% land inside the district their own name says, and the misses sit a median of
18.6 km away. The failures are diagnostic rather than random:

- The extreme ones are known OCR misreads — NA-19 Bannu lands 1,315 km out,
  NA-4 Nowshera 890 km, NA-134 Rajanpur 862 km. These are the same seats flagged
  as label misreads in `CROSSCHECK.md`.
- The Lahore seats (NA-93, 94, 95) land ~490 km out because they are drawn in
  the **Lahore inset box**, not on the main map. This is expected and confirms
  each inset needs its own transform.

## Where it stands

`scripts/extract_1977_boundaries.py` runs the whole pipeline and writes
`data/wip/na_1977delim_1997_partial.geojson`. On the 1997 map:

- main-map georeference **IoU 0.942**
- OCR read 208 of 366 regions
- 50 labels rejected by the distance gate, 15 recovered by elimination
- **163 of 207 seats identified, 162 polygons built**
- union covers 84% of the country, IoU 0.812 against the true outline, and only
  0.6% of area is duplicated between seats — so what is produced is structurally
  sound, with Balochistan seats largest and Lahore seats smallest, as expected

It is **not** wired into the map, because swapping it in would leave 45 seats
blank — worse than the district aggregate it would replace.

The two things blocking completion:

1. **Inset fits are poor.** Main map 0.942, but Karachi 0.154 and the other
   boxes 0.63-0.75. Fitting an inset against the union of its seats' *modern*
   districts is the wrong target — those extents have changed, and for Karachi
   they include rural area the inset does not draw. Try fitting against the
   drawn area's own convex structure, or against 2002-delimitation seats
   restricted to that city, or hand-place two or three control points per inset.
2. **Label recovery stalls.** Elimination only added 15. It needs the inset
   transforms first, since most rejected labels are inset seats whose positions
   are currently wrong.

## What remains

1. **Per-inset transforms.** Five city boxes are separate connected components.
   On the 1997 map: Karachi at `x[44,1126] y[2298,2921]`, plus boxes at
   `x[3018,3334] y[1045,1378]`, `x[1475,1672] y[390,522]`,
   `x[2527,2716] y[1261,1419]`, `x[2692,2798] y[1028,1118]`. Legend swatches are
   50x44 px. Fit each the same way, against the union of the districts it covers
   rather than the whole country.
2. **Correct the OCR misreads before using labels as truth.** A label is
   suspect when its region lands far from the district its number implies. That
   distance is now computable, so it can gate acceptance: reject, then re-read or
   resolve by elimination within the district.
3. **Lift recall from 76% to complete.** Remaining regions can be resolved by
   elimination — we know how many seats each district had and which numbers are
   still unassigned — plus adjacency.
4. **Trace the regions.** Contour each region and simplify, but trace the border
   *network* once and assemble polygons from it, rather than tracing regions
   independently, or every shared boundary produces slivers and overlaps.
5. **Validate before shipping.** 207 polygons per year; no overlaps beyond
   tolerance; union matches the national outline; each seat inside the district
   its name says; and the party colours implied by the new geometry still
   reproduce `CROSSCHECK.md`.

## Accuracy expectations

A ~5 km median is fine for rural seats, which run tens of kilometres across, and
too coarse for urban ones — but urban seats are exactly the ones drawn in the
insets, where a dedicated transform on a zoomed drawing should do much better.
Some residual is irreducible: this is a hand-drawn map, not a survey. Whatever
ships should carry its measured error, not be presented as exact.

## When it lands

Replace the projection for 1990, 1993 and 1997: set `YEARS[y].unit` away from
`'proj'`, point `geo` at the new layer, drop the `XW` apportionment path and the
district-outline overlay, restore the normal per-seat detail panel, and remove
the `Y.unit!=='proj'` guard that currently suppresses the district line. Keep
`scripts/build_1990s_districts.py` — the aggregates stay the honest fallback for
any year that fails validation. Update `DATA_DICTIONARY.md`, and add the
CC BY-SA attribution and share-alike note for derived geometry to
`DATA_LICENSE.md`.
