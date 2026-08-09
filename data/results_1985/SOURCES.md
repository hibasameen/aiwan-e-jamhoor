# GE-1985 NA results — sources & caveats

- Candidate-level results for all 207 National Assembly constituencies from
  ElectionPakistani's GE-1985 pages (`ge1985/NA-{n}.htm`). Election held 28 February 1985.
- **1985 was a non-party election** held under Zia-ul-Haq: every candidate stood as an
  individual, with no party affiliation on the ballot. The source pages therefore have a
  two-column table (Candidate, Votes) with **no party column**, and our `party` fields are
  left blank throughout. This is faithful to the source, not a gap.

## How it was built

- `scripts/scrape_ge1985.py` — standalone urllib scraper (207 seats), same shape as the
  other years. The build sandbox cannot reach electionpakistani.com (proxy 403), so pages
  were pulled with the fetch tool, cached one file per seat under `_cache/NA-{n}.md`, and
  converted by `scripts/parse_gecache.py 1985 207` (offline, re-runnable).

## Coverage and gaps

- **All 207 seats parsed.** 1,065 candidate rows.
- Registered electorate / votes polled / turnout are **not published per seat** → blank.
- **Nine winner-only seats** (source gives the winner but no vote counts, several explicitly
  marked "Un Contested"): NA-5, 28, 31, 154, 161, 165, 180, 203, 205. Votes left blank.
- **NA-189 and NA-201** were rendered by the fetcher without table pipes; both were recovered
  in full by the parser's plain-line fallback (5 and 4 candidates respectively).

## Boundaries

The 1985 constituencies are the **207-seat delimitation** (1981 census) that was used
unchanged for the 1985, 1988, 1990, 1993 and 1997 elections. A single boundary set therefore
serves all five of those years. (This is distinct from the 200-seat 1977 delimitation.)
