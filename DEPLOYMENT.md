# Deployment readiness

*Assessment as of 5 August 2026, against the site as it stands: `index.html`, `map.html`,
`dynasties.html`, `method.html`.*

## Verdict

**The application is functionally complete and deployable today as a static site.** All
four pages render with **zero JavaScript errors**, cross-link correctly, and are
self-contained: the map inlines D3 and every dataset (~3.8 MB), so there is no server, no
build step, and no runtime data fetch. The only external network dependency is Google
Fonts.

What stands between "works" and "a credible public launch" is packaging and a few editorial
choices — not engineering. Estimate: **a focused half-day**, most of it optional polish. The
checklist below is ordered by how much it matters.

---

## Verified working

- Four pages load clean in a headless Chromium render; no page errors, no broken references.
- Navigation is consistent across all pages (Home / Map / Dynasties / Method).
- Map: year switcher, party choropleth, click-to-isolate legend, constituency panel
  (candidates, turnout, margin, boundary provenance), table fallback, pan/zoom, light/dark.
- Data provenance and caveats are surfaced in-app (tooltips, panel notes, footer) and now in
  a full Method page.
- No `localhost`/absolute-path leakage; no `TODO`/placeholder text; no browser-storage
  beyond the theme preference (which degrades gracefully).

---

## Pre-launch checklist

### Should fix before launch

- [x] **Default map year — set to 2024 (done).** Previously `map.html` initialises `state.year:'2013'`. A visitor
      landing on the map sees the 2013 election, not the most recent. Unless this is a
      deliberate editorial choice, change the default to `'2024'` (one-line change in the
      `state` object). *Editorial call — flagged, not changed.*
- [x] **Social-share cards (done).** Added OG + Twitter tags and a branded og-image.png to all pages; set `og:url` and an absolute image URL after choosing a domain. Originally: None of the pages except the new `method.html` carry
      OpenGraph/Twitter meta. A civic-data project lives on being shared — add `og:title`,
      `og:description`, `og:image` (a rendered map thumbnail) and `twitter:card` to
      `index.html`, `map.html`, `dynasties.html`. Highest-leverage 20 minutes here.
- [ ] **Pick a host and a domain.** The site is static; any of GitHub Pages, Netlify,
      Cloudflare Pages or Vercel will serve it as-is and gzip/brotli the 3.8 MB map down to
      ~1 MB over the wire. Point `app/` at the host's publish directory.
- [ ] **Licensing files present.** `LICENSE` (MIT, code) and `DATA_LICENSE.md` (data
      provenance) are in this repo — make sure they ship with whatever you publish, given
      the GPL-3.0 upstream on the 2008–2018 results and 2002 boundaries.

### Nice to have

- [x] **Self-host the fonts (done).** Added `fonts/` (woff2, OFL) + `fonts/fonts.css`; the Google Fonts `<link>` is removed from every page. Originally: Google Fonts is the single external dependency and a minor
      privacy/latency/availability cost. Download the four families (incl. Noto Nastaliq
      Urdu) and serve them locally with `font-display:swap`; the design already degrades to
      system fonts if the request fails.
- [x] **`robots.txt` + `sitemap.xml` (done).** Added at the site root; replace `REPLACE-WITH-YOUR-DOMAIN` with the live host. Originally: Four URLs; trivial, helps indexing.
- [ ] **Analytics.** A privacy-respecting counter (e.g. Plausible/GoatCounter) if you want
      traffic numbers without cookies.
- [ ] **A visible "last updated" / version stamp** in the footer, so readers know the
      vintage of the data (important given the provisional 2024 figures).
- [ ] **404 page** in the site's style.

### Data-quality items (documented, not blockers)

These are known and disclosed in-app and in `METHODOLOGY.md`; none blocks launch, but each
is a natural post-launch improvement:

- [ ] **19 low-confidence 2024 boundaries** (Peshawar NA-28–32, Islamabad NA-46/47/48, and a
      few city splits) — resolvable with the ECP Form-7 final-delimitation sheets.
- [ ] **12 seats without an official 2024 Form-47** — rely on the transcription only.
- [ ] **"Declared vs current" for 2024** — tribunal reversals and the reserved-seat judgment
      are noted but not modelled as separate fields.

---

## Performance note

`map.html` is ~3.8 MB uncompressed (inlined data). This is fine for a static host with
compression — expect ~1 MB transferred and a fast first paint since there is no data
round-trip. If you ever want it lighter, the largest win is splitting the four boundary
layers out of the HTML and fetching the selected year's layer on demand; not necessary for
launch.
