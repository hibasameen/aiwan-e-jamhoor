# GE-1988 NA results — sources & caveats

- Candidate-level results for all 207 National Assembly constituencies from
  ElectionPakistani's GE-1988 pages (https://www.electionpakistani.com/ge1988/result.html
  and per-constituency `NA-{n}.htm` pages). The election was held on 16 November 1988.
- ElectionPakistani is an unofficial transcription of ECP returns.

## How it was built

- `scripts/scrape_ge1988.py` is the standalone scraper (urllib), the same shape as
  `scrape_ge1990.py`. Run it on any networked machine: `python3 scripts/scrape_ge1988.py`.
- The build sandbox cannot reach electionpakistani.com (proxy returns 403), so the pages
  were pulled with the fetch tool and cached one file per seat under `_cache/NA-{n}.md`,
  then converted to CSV by `scripts/parse_ge1988_cache.py`. That parser is offline and
  re-runnable, and it is what produced the committed CSVs.

## Coverage and gaps

- **All 207 seats parsed.** 1,186 candidate rows.
- **Registered electorate, votes polled and turnout are not published per seat**, so those
  columns are blank — the same situation as 1990/2024. (Published national turnout ≈ 43%.)
- **Five seats give the winner's name but no vote counts** — the source cells are empty.
  Votes are left blank, so share and margin are null for these seats:
  NA-165 Larkana II (Begum Ashraf Abbasi, PPP), NA-166 Larkana III (Mohtarma Benazir
  Bhutto, PPP), NA-167 Hyderabad I (Makhdoom Amin Fahim, PPP), NA-168 Hyderabad II
  (Aftab Ahmad Sheikh, Independent), NA-169 Hyderabad III (Rashid Ahmad Khan, PPP).
- **Five more seats list only the winning candidate** (with votes) and no other rows:
  NA-141, NA-142, NA-143 (Bahawalpur I–III), NA-194, NA-195 (Karachi East III–IV).
  These appear as single-candidate seats.
- **NA-135 (Muzaffargarh I)** was rendered by the fetcher without table delimiters; it was
  recovered by the parser's plain-line fallback and carries the full 8-candidate result.
- Two obvious source typos in the party column were normalised (`ppp`→PPP;
  `Indpendent`/`Indepdnent`→Independent).

## Manual-fill attempt for the 10 incomplete seats (2026-08-09)

Asked to fill the missing vote counts, we checked whether reliable figures are attributable
from Wikipedia (the chosen standard). Outcome: **no vote counts could be added.** Details:

- **NA-166 Larkana III (Benazir Bhutto).** The "Electoral history of Benazir Bhutto" article
  cites ElectionPakistani's (blank) NA-166 1988 page but shows **no distinct NA-166 1988
  table**. Its two 1988 tables were positively identified as other seats by cross-checking
  ElectionPakistani's own populated pages: the "53,425 / Mian Umar Hayyat / PAI / PDP" table
  is **NA-94 Lahore III**, and the "62,046 / IJI Jamshed Ahmad Khan 10,730" table is
  **NA-189 Karachi South I** (both fully present in our data already; Benazir won three seats
  in 1988 and vacated two). So Wikipedia yields nothing usable for NA-166 Larkana.
- **NA-165 (Ashraf Abbasi) and NA-167 (Makhdoom Amin Fahim).** Their Wikipedia biographies
  confirm the 1988 wins but give no constituency vote counts.
- **NA-141/142/143 Bahawalpur, NA-168/169 Hyderabad, NA-194/195 Karachi East.** No
  attributable per-seat 1988 table found.

Winners for all ten remain as recorded (now cross-corroborated for NA-165/166/167). Vote
counts stay blank. The only route to fill these accurately is the **ECP official 1988 report**
(constituency-wise result volume) or the **CLEA (Constituency-Level Elections Archive)**
Pakistan-1988 dataset; neither is reachable from here without the source file in hand.

## Party labelling

- Party tally as scraped: PPP 95, IJI 56, Independent 39, JUI-F 7, PAI 3, ANP 2, BNA 2,
  JUI-D 1, PDP 1, NPP-K 1 (sums to 207).
- Commonly published figures give roughly PPP 93–94, IJI 54–55 and **MQM 13**. This source
  does not use an MQM/HPG label for 1988: MQM's urban-Sindh winners (e.g. NA-194 Syed Amin
  ul Haq, NA-195 Mahmood Hussain Hashmi) are recorded as **Independent**, which is why the
  Independent bucket here is larger and MQM is absent. Treat the seat totals as the
  source's, not as official, and expect a party-mapping pass (as with HPG→MQM in 1990)
  before display.
- IJI is the PML-led alliance; it appears in this year and 1990 and should be shown in the
  PML-N colour with the alliance named in the legend, as done for 1990.
