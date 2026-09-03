# National Assembly membership files (`members_na{1..16}.json`)

Full membership of every National Assembly of Pakistan, 1947–present, including
reserved seats. Built 2026-09-01.

## Sources

| Assemblies | Source | Form |
|---|---|---|
| 1–12 | `na.gov.pk/uploads/former-members/*.pdf` (linked from `content.php?id=121`) | scanned PDF, text extracted |
| 13 | `na.gov.pk/en/former-old.php?id=1` | HTML table |
| 14, 15 | `na.gov.pk/en/former.php?id=11` / `?id=20` | HTML table |
| 16 | `na.gov.pk` current members list | HTML |

Every file carries its own `source`, `run_date` and `notes`.

## Schema

`members_na1`–`members_na15` use a wrapper object:

```
{schema_version, source, run_date, assembly, notes[], members[]}
```

`members_na16.json` is a bare array (built earlier, left as-is).

Member record:

| field | notes |
|---|---|
| `name` | as printed; OCR stray internal spaces collapsed ("Moham m ad" → "Mohammad"), nothing else corrected. May be `null` where the source printed a seat with no name. |
| `na_id` | na.gov.pk profile uid — **assemblies 13–16 only**, `null` for 1–12. **Not stable across assemblies** (Ghulam Ahmad Bilour is uid 1 in the 13th, 1016 in the 14th) and unrelated to the candidate IDs in `data/`. |
| `seat` | `NA-n` where the source gives one, else `null`. Seat numbers mean different ground in each delimitation. |
| `seat_type` | `general` \| `reserved_women` \| `reserved_nonmuslim` — assigned from the source's own section headings, never inferred. |
| `province` | For reserved women, the province of the quota. For non-Muslim seats, `null` (nationwide). |
| `party` | `null` for assemblies 1–5 and 7 (no party column in those PDFs). |
| `elected_via` | `general` \| `by_election` \| `indirect` \| `nominated` |
| `remarks` | office held, "Resigned", "Disqualified", "Passed Away", community (7th), etc. |
| `raw_constituency` | the constituency string as printed, where it differs from `seat`. |

## Reserved seats mean four different things across this span

Read `seat_type` in the light of the regime in force. **Do not pool these
categories across eras without saying which mechanism produced them.**

- **1947–1958 (1st–2nd Constituent Assemblies)** — no reserved women's or
  minority seats in the source at all. All records `general`.
- **1962–1969 (3rd–4th)** — indirect election by the Basic Democracies
  electoral college; 6 women's seats, split 3 East Bengal / 3 West Pakistan,
  headed "Women's Constituency". West Pakistan was One Unit, so `province` is
  `null` for its general seats.
- **1972–1977 (5th–6th)** — small indirectly-elected women's contingent plus
  separate minority constituencies. The 6th Assembly PDF's own party-position
  table cites 10 women's and 6 minority seats but **names none of them**, so
  the 6th has no reserved-seat records. Genuine source gap, not a parse failure.
- **1985–1997 (7th–11th)** — non-Muslim members were **directly elected on
  nationwide separate electorates**, not allocated from lists. They are still
  tagged `reserved_nonmuslim`, but they are real election results and belong in
  vote-share work in a way that later list seats do not. Women's seats: 20 in
  the 7th–8th, then the provision **lapsed** — the 9th, 10th and 11th have no
  women's section whatsoever.
- **2002–present (12th–16th)** — the modern regime. 60 women's seats allocated
  proportionally by province (Punjab 35 / Sindh 14 / KP 8 / Balochistan 3) and
  10 non-Muslim seats allocated proportionally nationwide, on party lists.

## Counts

| Asm | Years | Total | General | Women | Non-Muslim |
|---|---|---|---|---|---|
| 1 | 1947–54 | 95 | 95 | – | – |
| 2 | 1955–58 | 90 | 90 | – | – |
| 3 | 1962–65 | 157 | 151 | 6 | – |
| 4 | 1965–69 | 163 | 157 | 6 | – |
| 5 | 1972–77 | 169 | 156 | 6 | 7 |
| 6 | 1977 | 200 | 200 | – | – |
| 7 | 1985–88 | 237 | 207 | 21 | 9 |
| 8 | 1988–90 | 239 | 207 | 22 | 10 |
| 9 | 1990–93 | 201 | 192 | – | 9 |
| 10 | 1993–96 | 217 | 207 | – | 10 |
| 11 | 1997–99 | 208 | 198 | – | 10 |
| 12 | 2002–07 | 341 | 271 | 60 | 10 |
| 13 | 2008–13 | 361 | 283 | 67 | 11 |
| 14 | 2013–18 | 363 | 290 | 63 | 10 |
| 15 | 2018–23 | 359 | 286 | 63 | 10 |
| 16 | 2024– | 332 | 262 | 60 | 10 |

Totals exceed the size of the House because they include by-election entrants
and replacements alongside the members they replaced — these are cumulative
membership rolls, not snapshots. Filter on `elected_via == "general"` for a
first-day composition, and expect it still to overcount where the source lists
a replacement without marking the original.

## Known problems

- **8th Assembly women (REVIEW FLAG)** — 22 records against a 20-seat
  allocation. Names are distinct, but the final two Balochistan entries are the
  same pair listed in the 7th Assembly PDF and reuse serial numbers 235–236.
  Possible source-layout leakage. Unresolved; flagged in the file's `notes`.
- **12th Assembly OCR** — in roughly 5–10% of general-seat records the
  constituency label is crammed onto the front of `name` with no honorific to
  split on, leaving `raw_constituency` empty. Seat, party and province are
  unaffected. Needs a cleanup pass before names are used for linkage.
- **Vacant seats** — the 9th (15 seats), 11th (9) and 12th (NA-35) print
  "Vacant"; these are omitted from `members[]` and listed by name in `notes`.
- **Missing general seats** — 13th: NA-42, NA-69; 14th: NA-38. Absent from the
  source lists, likely postponed polls.
- **14th minority members** are all labelled "RS(Minority) Khyber Pukhtunkhwa"
  on the site — a data-entry artifact; these are nationwide seats, so
  `province` is `null`.
- **One Unit era** — `province` is `null` for West Pakistan general seats in
  the 3rd and 4th assemblies; the source gives no sub-province breakdown.
- Assemblies 1–2 have **no constituency codes at all** (address column only),
  and their numbering has gaps where section-heading totals exceed printed names.

## Not yet done

- Resolving `name` → canonical Aiwan-e-Jamhoor person IDs (see the `mp-linkage`
  conventions). Nothing here is linked to `data/` candidate records yet.
- Party attribution for assemblies 1–5 and 7.
- Reconciling reserved-seat allocations against ECP notifications — relevant
  mainly for 2024, where the SIC litigation means the final allocation does not
  follow from a proportional calculation on general-seat wins.
