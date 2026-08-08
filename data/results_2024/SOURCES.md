# GE-2024 NA results — sources & caveats

- Candidate-level results for all 266 NA constituencies scraped from ElectionPakistani.com GE-2024 pages
  (https://www.electionpakistani.com/ge2024/result.html and per-constituency pages), July 2026.
- ElectionPakistani transcribes ECP results (Form-47 provisional consolidations); it is an unofficial source.
- PTI-backed winners appear as "Independent" (party as declared at the election). Post-election SIC/PTI
  affiliation is NOT reflected. MQM naming normalised to MQM-P downstream.
- Winner = highest votes on the page. Tally: IND 99, PML-N 78, PPP 54, MQM 17, JUI-F 6, PML-Q 3, IPP 3,
  MWM 1, PML-Z 1, BAP 1, BNP(M) 1, NP 1, PkMAP 1. Official GE-day tallies commonly cited (IND 101,
  PML-N 75, JUI-F 4, IPP 2...) differ slightly — ElectionPakistani reflects some post-recount/tribunal
  outcomes. Verify seat-by-seat against ECP Form-49/gazette before publication.
- Registered voters / votes polled / turnout not consistently available on source pages (blank columns).
- NA-82..NA-90 were fetched separately (agent run was interrupted); same source and format.

## Update (2 Aug 2026): official Form-47 extraction
- na_2024_form47_official.csv: extracted from 254 scanned official ECP Form-47 PDFs
  (user-provided, "National Assembly 2024" folder). Fields: polling stations, registered
  voters (m/f/t), votes polled (m/f/t), valid, rejected, turnout, winner/runner-up, form date.
  12 seats have no PDF: NA-1,2,4,7,8,12,14,16,19,20,21,22.
- Extraction by vision reading of Urdu scans in 13 batches; every row arithmetic-checked
  (valid+rejected=polled, m+f=totals, winner<=valid). ~20 seats carry flags (illegible
  fields or printed inconsistencies on the form itself) — see the flags column.
- Cross-check vs the ElectionPakistani scrape: same winner in 249/254 seats (198 with
  small vote differences — F47 provisional vs later revisions). FIVE genuine reversals,
  where the election-day Form-47 winner differs from the later result: NA-79, NA-81,
  NA-154, NA-251, NA-261. The app displays both in these seats.
- App now uses Form-47 official figures for registered voters, turnout, polling stations
  and rejected votes (254 seats).
