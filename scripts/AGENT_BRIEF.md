# Sindh 2023-delimitation sheet-digitisation brief (per-canvas agent)

You are digitising ONE canvas (a district or district-group) of Pakistan's 2023
National Assembly delimitation from a scanned ECP district map sheet. Everything
happens in /home/claude/aiwan. Python has cv2, numpy, scipy, shapely, matplotlib,
PIL installed (pip --break-system-packages for anything else).

## Inputs
- Sheet image(s): sheets/sindh/<given in your task>. These are photos/scans of ECP
  "Preliminary Delimitation 2023" district maps: constituencies are colour-washed
  regions labelled NA-XXX; there may be a legend, scale bar, tables, urban insets.
  Some are skewed photos (perspective), some rotated.
- Canvas polygon: out/canvases_2023.geojson — feature where properties.seats
  contains your seats (semicolon-joined). Its geometry is the authoritative
  lon/lat footprint. Your output seats must EXACTLY partition it.
- Toolkit: scripts/split_district_by_sheet.py (import from it; add scripts/ to
  sys.path). Its split_district(img_path, legend, district_geom) does:
  colour-mask per seat -> union-outline similarity-ICP fit (4 rotation starts) to
  the canvas polygon -> TPS refine -> nearest-label transfer on a dense grid ->
  per-seat polygons intersected with the canvas. Legend entries look like
  {'na':'NA-194','colour':'pink'} with colour words from its HUE_WORDS table.
  You may also write your own segmentation if the helper's HSV gates fail —
  reuse fit_outline() for the geo-fit regardless.

## Procedure
1. LOOK at the sheet first (downscale to ~1500px, Read the png). Note: which NA
   seats are shown, what colour each is, scan rotation, insets/tables to crop,
   whether the district outline is complete. If two sheets are listed, pick the
   more complete/higher-res one; use the other as cross-check.
2. Build the legend (seat -> colour word). If colours are ambiguous, sample BGR
   values from inside each labelled region (you know roughly where labels sit
   from step 1) and extend/replace HUE_WORDS ranges accordingly.
3. Run the split against the canvas polygon. If the sheet has a large white/urban
   inset or table panels, crop them out first (cv2 slice) so the outline fit sees
   only the district body.
4. QA (mandatory, iterate until passing):
   - piece count == seat count; no empty seats;
   - union of seats == canvas polygon (split_district guarantees coverage; verify
     symmetric-difference area < 1e-6);
   - per-seat area share on sheet vs output should agree within ~10-15 percentage
     points (big drift = bad fit or mask leakage);
   - render overlay PNG: canvas outline + coloured seats + seat labels at
     representative points; view it yourself and sanity-check against the sheet
     (same neighbour relations, same rough shapes, correct N/S/E/W placement).
   - fit rms (km) reported by fit_outline: <3 km good for rural districts,
     <1.5 km for Karachi districts. If ICP lands on a flipped/displaced fit
     (rms fine but overlay obviously wrong), try restricting start rotations,
     cropping tighter, or anchor-based Procrustes on known feature points.
5. Outputs (write exactly these):
   - out/sindh/<CID>.geojson : FeatureCollection, one feature per seat,
     properties {na, src:'sheet-split: <sheetfile>, outline-fit',
     approx:false, rms_km:<float>}, geometry in lon/lat. CID = the canvas_id
     from canvases_2023.geojson.
   - out/sindh/qa_<CID>.png : the overlay described above.
   - out/sindh/<CID>.report.json : {canvas_id, seats:[...], sheet_used,
     rms_km, area_share_sheet:{na:frac}, area_share_out:{na:frac},
     issues:[strings], confidence:'high'|'medium'|'low'}

## Known gotchas (hard-won on the 2018 sheets — do not rediscover)
- Legend swatches & map chrome poison colour masks: component-filter (drop
  components < max(1500px, 5% of largest)) and crop the frame.
- A seat with weak/unreliable colour: segment the OTHER seats well and take the
  weak one as remainder of the canvas (split_district does this if you pass its
  colour as None-matching word or omit it from `good`).
- If the union of colour masks covers <65% of the sheet's district body, the
  masks are wrong (partial colour union gives a deceptively low ICP rms on a
  blob fit). Fix masks before trusting the fit.
- Rotated scans are common: fit_outline already multi-starts 0/90/180/270.
  Perspective-skewed photos: deskew with cv2.getPerspectiveTransform from the
  map frame corners if the fit is poor.
- Karachi sheets may be street maps with subtle colour washes: reduce the
  saturation gate (s>15) and raise morphology kernel sizes.
- Always work at ~3000px width (load_small); full-res only if masks are noisy.

## Report back (final message = data, not prose)
Return the report.json content plus one line on what you'd redo. Do NOT copy
files anywhere else; do NOT touch files outside out/sindh/ and /tmp.
