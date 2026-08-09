# GE-1977 NA results — sources & caveats

- Candidate-level results for all 200 National Assembly constituencies from
  ElectionPakistani's GE-1977 pages (`ge1977/NA-{n}.htm`). Election held 7 March 1977.
- **Historical caveat.** The 1977 election returned a large PPP majority and was immediately
  contested: the opposition Pakistan National Alliance (PNA) alleged systematic rigging, mass
  protests followed, and General Zia-ul-Haq imposed martial law in July 1977. Treat these as
  the *transcribed official result*, which is widely regarded as manipulated — not as a clean
  record of voter intent.

## How it was built

- `scripts/scrape_ge1977.py` — standalone urllib scraper (200 seats). The build sandbox
  cannot reach electionpakistani.com (proxy 403), so pages were pulled with the fetch tool,
  cached under `_cache/NA-{n}.md`, and converted by `scripts/parse_gecache.py 1977 200`.

## Coverage and gaps

- **All 200 seats parsed.** 649 candidate rows.
- Registered electorate / votes polled / turnout are **not published per seat** → blank.
- **Nineteen winner-only seats** — mostly PPP candidates returned **unopposed**, a defining
  (and much-criticised) feature of 1977: NA-154, 155, 157, 158, 159, 163, 164, 165, 166, 171,
  175, 176, 177, 178, 180, 197, 198, 199, 200. Votes left blank. NA-163 Larkana is Zulfiqar
  Ali Bhutto's own uncontested seat.
- **NA-21 and NA-141** were rendered without table pipes and recovered by the plain-line
  fallback (full candidate lists).

## Party labelling

- Tally as scraped: **PPP 156, PNA 36, Independent 7, PML-Q 1** (sums to 200). This tracks the
  commonly cited 1977 outcome (PPP ~155, PNA ~36).
- **"PML-Q" here means Pakistan Muslim League (Qayyum group)** — the faction led by Abdul
  Qayyum Khan that existed in the 1970s (NA-1 winner Muhammad Yousaf Khattak). It is **not**
  the modern PML-Q founded in 2002; do not merge them.
- The PNA (Pakistan National Alliance) was the nine-party opposition alliance; it appears only
  in this year.

## Boundaries

1977 used the **200-seat delimitation** (1972 census), with older district names — Lyallpur
(now Faisalabad), Campbellpur (now Attock), Lyallpur/Sahiwal splits, etc. This is a *different*
delimitation from the 207-seat map used in 1985–1997.
