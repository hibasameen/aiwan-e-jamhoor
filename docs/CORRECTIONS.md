# Corrections log

Reader-reported and self-found errors in the published data, with what was wrong, what the evidence is, and how it was fixed. Newest first.

## 2026-09-03 — GE-2008, NA-147 Okara-V: winner's name

**Reported by** @megadelusion on X, 14 Aug 2026 ("in 2008, this seat was won by Khurram Jahangir Wattoo, not Zafar Yasin Wattoo", citing ElectionPakistani).

**What was wrong.** Our 2008 record (from Colin Cookman's ECP-derived file) gave the winner as "Muhammad Zafar Yasin Wattoo", Independent, 84,778 votes. The votes and the rest of the candidate list are right; the name is not.

**What happened.** Mian Manzoor Ahmad Khan Wattoo contested both NA-146 and NA-147 on 18 February 2008 as an independent and won both (46,941 and 84,778). He kept NA-146 and vacated NA-147. In the by-election that followed, his son Khurram Jahangir Wattoo (PPP) won with 79,195 against Zafar Yasin Wattoo (Independent, 15,965). ElectionPakistani shows that by-election in place of the general-election result — hence the reader's version — and Cookman's file carries the by-election loser's name against the general-election winner's votes.

**Evidence.** Geo TV's 2008 results page for NA-147 (Wayback, 24 Sep 2015): "Mian Manzoor Ahmed Wattoo, Independent, 83,412" provisional, with the same nine-candidate list as Cookman; the National Assembly's 13th-Assembly roll (NA-146 Manzoor Ahmad Wattoo, NA-147 Khuram Jehangir Wattoo, PPPP); Wikipedia, "Khurram Jahangir Wattoo", citing the ECP General Election 2008 Report Vol. II for the by-election figures; ElectionPakistani ge2008/NA-147.htm.

**Fix.** `scripts/patches/patch_na147_2008.py` corrects the name in `candidacies_final.csv` (person now P01417, Manzoor Wattoo), removes the phantom person P04634, and patches `results_all.json`, `results_2008_2013.json`, `map.html`, `candidates.html`; house.html rebuilt. Manzoor Wattoo's 2008 record now shows two wins. The by-election itself is not in the data (the site records general elections only).

**Follow-up.** Manzoor Wattoo is still split across three person IDs in the spine (1988/1993 as "Mian Manzoor Ahmad Khan", 1990 as "…Watto"); a merge is queued in `scripts/linkage/overrides.json` for the next spine rebuild.
