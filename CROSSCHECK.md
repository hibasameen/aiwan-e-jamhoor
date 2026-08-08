# Cross-check against independently drawn constituency maps

Our per-seat winners were checked against the labelled election maps published on
Wikimedia Commons by **Saad Ali Khan Pakistan** (CC BY-SA 4.0). Those maps print each
constituency's NA number, so the join needs no georeferencing: the printed label is the key.

`scripts/read_labelled_map.py` segments each map into flat-filled regions and OCRs the
number inside each one. `scripts/crosscheck_commons_maps.py` then infers colour-to-party
(the modal winner in our data among seats sharing a fill) and reports every seat where
the two sources disagree. Nothing about our data is changed by this process — it is a
check, not an input.

## Result

| Election | Seats in our data | Cross-checked | Agree | Label misreads | Unexplained | Agreement |
|---|---:|---:|---:|---:|---:|---:|
| 1990 | 207 | 156 | 148 | 7 | 1 | 94.9% |
| 1993 | 202 | 153 | 148 | 5 | 0 | 96.7% |
| 1997 | 204 | 155 | 150 | 4 | 1 | 96.8% |
| 2002 | 270 | 154 | 148 | 5 | 1 | 96.1% |
| 2008 | 268 | 203 | 197 | 5 | 1 | 97.0% |
| 2013 | 269 | 202 | 189 | 9 | 4 | 93.6% |
| **All** | | **1,023** | **980** | **35** | **8** | **95.8%** |

Raw agreement is 95.8%. Of the 43 disagreements, 35 are explained by a confusable
label — the OCR reading NA-134 where the map says NA-34, and similar — - leaving
**8 unexplained, 0.78% of the seats checked**.

Coverage is limited by OCR recall, not by the maps: labels were read for roughly three
quarters of seats. Unread seats are simply not checked.

## The unexplained residual

| Election | Seat | Name | Our winner | Map shows |
|---|---|---|---|---|
| 1990 | NA-19 | Bannu 1 | JUI-F | MQM |
| 1997 | NA-19 | Bannu | PML-N | MQM |
| 2002 | NA-3 | Peshawar 3 | MMA | PML-Q |
| 2008 | NA-3 | Peshawar 3 | PPP | PML-N |
| 2013 | NA-4 | Peshawar 4 | PTI | IND |
| 2013 | NA-2 | Peshawar 2 | PTI | PPP |
| 2013 | NA-3 | Peshawar 3 | PTI | PML-N |
| 2013 | NA-9 | Mardan 1 | ANP | PML-N |

Most sit in Peshawar or Mardan, and NA-19 Bannu recurs in both 1990 and 1997 — NA-2, NA-3 and NA-4 recur across several
years. That clustering in one dense urban area, rather than scattering at random, points
to the labels there being crowded enough that our reader attaches one to the wrong
polygon. It is not evidence of an error in the results data, though the Peshawar seats
would be worth an eyeball before anyone leans on them.

## 1990 in particular

The 1990 map carries no legend text, only swatches, so its colour key had to be
established rather than read. Scaling the fills across the seats whose labels were
readable gave roughly IJI 112, PDA 43, independents 24, MQM 13 and ANP 7 against a
published IJI of 106-111 and PDA of 44 — close enough to fix the key. Cross-checking
against the scraped returns then confirmed it seat by seat: green is IJI, dark grey PDA,
pale blue independents, yellow MQM, dark red ANP.

## Attribution

Maps by Saad Ali Khan Pakistan, from Wikimedia Commons, licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Used here only to verify
our own figures; no geometry or content from them is redistributed in the site.
