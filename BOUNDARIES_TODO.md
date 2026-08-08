# Recovering true pre-2002 constituency boundaries

**Status: not done.** 1990, 1993 and 1997 are currently drawn as district
aggregates projected onto the 2002 constituency shapes. That is deliberate and
documented in `DATA_DICTIONARY.md`, but it means the outlines on screen for
those years are 2002 boundaries, not the boundaries those elections were fought
on. This note records what is already built, the obstacle that stopped the work,
and what a proper job requires. It is written so someone can resume cold.

## Why this is now possible

The 1977 delimitation — 207 general seats, used from 1977 through 1997 — was
never published in geospatial form. But `data/sources/` holds labelled
constituency maps for 1990, 1993 and 1997 (Saad Ali Khan Pakistan, CC BY-SA 4.0,
~3,500 px) which draw those boundaries and **print each seat's NA number inside
its region**. That printed number is the join key, so identity does not have to
be inferred.

Their fidelity is measured, not assumed: `CROSSCHECK.md` reports 1,023 seats
checked across six elections at 99.2% consistency with our independent results
once OCR misreads are allowed for. These are accurate drawings.

## What already works

`scripts/read_labelled_map.py` segments a map into flat-filled regions and OCRs
the NA number inside each. On the 1997 map it finds 366 regions and reads 157
labels (~76%). Each region yields a pixel mask, a bounding box and a fill
colour. This is the hard half of the extraction and it is done.

## The obstacle: georeferencing

Region masks are in image coordinates. Turning them into real geometry needs a
transform from pixels to lon/lat, and the cheap approach does not work.

Tried: use each labelled region's district (known from the returns) and that
district's true centroid as a control point, then fit a polynomial warp.

| Control points | Best fit | Median error | p90 |
|---|---|---|---|
| 144 (all labelled regions) | cubic | 39 km | — |
| 24 (single-seat districts only, Karachi excluded) | cubic | 24 km | 184 km |

Constituency work needs error well under ~5 km, so this is an order of magnitude
short. Two causes: a district centroid is not a seat centroid, and a few misread
labels drag the fit hard (NA-4 Nowshera lands 582 km out).

**Do not pursue centroid control points.** Use outline matching instead.

## The plan

1. **Build the constituency-area mask.** Select pixels close to a known party
   fill, which excludes the borders and, importantly, Kashmir and
   Gilgit-Baltistan — those are `#7f7f7f` grey and diagonal hatching, and are not
   part of the National Assembly area or of the 2002 outline we fit against.
2. **Exclude the insets.** The five city boxes and the legend are separate
   connected components. On the 1997 map, land components are: the main landmass
   at `x[121,3468] y[90,2400]`; Karachi at `x[44,1126] y[2298,2921]`; and smaller
   boxes at `x[3018,3334] y[1045,1378]`, `x[1475,1672] y[390,522]`,
   `x[2527,2716] y[1261,1419]`, `x[2692,2798] y[1028,1118]`. Legend swatches are
   50x44 px. Each inset needs its **own** transform — they are drawn at a
   different scale from the main map.
3. **Fit the transform by outline.** Take the outer contour of the main-map mask
   and fit it to the true national outline (union of
   `data/na_constituencies_2002delim.geojson`, bounds
   `60.879, 23.695, 75.375, 36.909`). Coarse align on moments and bounding box,
   then refine with ICP. Thousands of unambiguous points beats two dozen noisy
   ones. Validate on held-out points before trusting it.
4. **Trace the regions.** Contour each region mask and simplify, but do it so
   neighbours share edges — trace the border network once and assemble polygons
   from it, rather than tracing each region independently, or you get slivers and
   overlaps along every shared boundary.
5. **Finish the labelling.** OCR recall is ~76%. The rest can come from
   elimination inside a district (we know how many seats each district had and
   which numbers are missing) plus adjacency. Every region must end up with
   exactly one NA number, and every NA number used once.
6. **Validate before shipping.** Suggested gates: 207 polygons per year; no
   overlaps beyond a small tolerance; the union matches the national outline to a
   few km; each seat's polygon falls inside the district its name says; and the
   party colours implied by the new geometry still reproduce `CROSSCHECK.md`.

## When it lands

Replace the projection for 1990, 1993 and 1997: set `YEARS[y].unit` away from
`'proj'`, point `geo` at the new layer, drop the `XW` apportionment path and the
district-outline overlay, and restore the normal per-seat detail panel. Keep
`scripts/build_1990s_districts.py` — the district aggregates remain the honest
fallback if any year fails validation. Update `DATA_DICTIONARY.md`, and add the
CC BY-SA attribution and share-alike note for the derived geometry to
`DATA_LICENSE.md`.
