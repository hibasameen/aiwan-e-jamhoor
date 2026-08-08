# GE-1990 NA results — sources & caveats

- Candidate-level results for all 207 National Assembly constituencies scraped from
  ElectionPakistani's GE-1990 pages (https://www.electionpakistani.com/ge1990/result.html
  and per-constituency pages) by `scripts/scrape_ge1990.py`.
- ElectionPakistani is an unofficial transcription of ECP returns.
- **Registered electorate, votes polled and turnout are not published per seat** for 1990,
  so those columns are blank — the same situation as the 2024 source. Published national
  turnout was 45.17%.
- Four seats were not parsed automatically and were entered by hand. NA-27, NA-34 and
  NA-91 were returned **unopposed**, so the source shows "Uncontested" where a vote count
  would be; NA-143's source row is malformed and carries no votes at all. Winners for all
  four are corroborated by the Wikipedia roster of the 9th National Assembly. Votes are
  left blank for these seats, so share and margin are null.
- **Constituency names come from the Wikipedia 9th National Assembly roster**, not from the
  scraped page titles. The scraped titles carry residue ("Lahore I Full") and, more
  importantly, do not name cross-district seats properly, writing them as a bare list. The
  roster labels them with "-cum-", which the district pipeline needs. Two corrections were
  applied: the roster labels NA-177 "Jamshoro", a district created in 2004, so it is
  recorded as Dadu; and the eight tribal seats are expanded to the agency naming used in
  the 1993 and 1997 returns.
- Party tally as scraped: IJI 103, PDA 42, Independent 24, HPG 15, ANP 6, JUI-F 6, PPP 3,
  JUP-N 3, JWP 2, PNP 2, PKMAP 1. Commonly published figures give IJI 106 and PDA 44;
  note that PDA 42 plus PPP 3 is 45, so part of the gap is alliance labelling. Treat the
  seat totals as the source's, not as official.
- HPG (Haq Parast Group) is the MQM's ballot designation and is mapped to MQM for display.
  IJI and PDA are shown in the PML-N and PPP colours: they are those parties' alliances,
  they appear in no other year, and the legend names them explicitly.
- Cross-checked against the independently drawn 1990 constituency map — see CROSSCHECK.md.
