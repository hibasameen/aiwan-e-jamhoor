#!/usr/bin/env python3
"""Add a per-election context card ("This election") to the map's side column,
and a sourced "The four elections" section to the Method page.

Every conduct claim is attributed to a named observer body with a link; the site
takes no verdict of its own. Stats are computed from our own results data
(scripts/summarise_elections.py) and cross-checked against official figures.
"""
import json, re, sys

ROOT = "mnt/Aiwan-e-Jamhoor"

# ---------------------------------------------------------------- data --------
ELEC = {
 "2008": {
  "date": "18 February 2008",
  "polled": "268 of 272",
  "postponed": "4 seats did not poll",
  "turnout": "44%",
  "cands": "2,180",
  "tight": "62",
  "summary": (
    "Polling was pushed from 8 January to 18 February after Benazir Bhutto was assassinated "
    "on 27 December 2007; four seats, including the one she would have contested, did not poll "
    "on the day. The vote was run by an Election Commission appointed under Pervez Musharraf, "
    "with the judges dismissed in the November 2007 emergency still not restored. PTI, "
    "Jamaat-e-Islami and the rest of the APDM bloc boycotted. Pakistan was suspended from the "
    "Commonwealth at the time, so no Commonwealth group observed."),
  "quotes": [
    {"who": "EU Election Observation Mission", "when": "Final report, April 2008",
     "q": "a level playing field was not provided during the campaign",
     "url": "http://www.eods.eu/library/eu_eom_pakistan_final_report.pdf"},
    {"who": "Democracy International", "when": "US observation mission, 2008",
     "q": "the elections provided a genuine opportunity for Pakistani voters to express their will",
     "url": "https://democracyinternational.com/media/U.S.%20Election%20Observation%20Mission%20to%20Pakistan%20General%20Elections%202008%20Final%20Report.pdf"},
  ],
 },
 "2013": {
  "date": "11 May 2013",
  "polled": "269 of 272",
  "postponed": "3 seats did not poll",
  "turnout": "55%",
  "cands": "4,496",
  "tight": "52",
  "summary": (
    "The first time an elected civilian government in Pakistan completed its term and handed "
    "power to another. Turnout was the highest since 1977. The campaign was not equally free: "
    "the Pakistani Taliban attacked the three outgoing coalition parties — ANP, MQM and PPP — "
    "while their opponents campaigned openly. PTI alleged rigging in four constituencies; a "
    "three-judge commission examined the claims in 2015. Around 500 polling stations recorded "
    "no women voting at all."),
  "quotes": [
    {"who": "EU Election Observation Mission", "when": "Final report, 2013",
     "q": "The high number of attacks affected campaigning and unbalanced the playing field",
     "url": "https://www.eeas.europa.eu/sites/default/files/pakistan_eom_final_report_eng_1.pdf"},
    {"who": "Judicial Commission of inquiry", "when": "Three Supreme Court judges, July 2015",
     "q": "in large part organised and conducted fairly and in accordance with the law",
     "url": "https://www.dawn.com/news/1195875"},
  ],
 },
 "2018": {
  "date": "25 July 2018",
  "polled": "270 of 272",
  "postponed": "2 seats did not poll",
  "turnout": "52%",
  "cands": "3,431",
  "tight": "79",
  "summary": (
    "Nawaz Sharif was disqualified from office for life in April and jailed twelve days before "
    "the poll. Some 370,000 troops were deployed, many stationed inside polling stations and "
    "given magisterial powers. On election night the Election Commission's new Result "
    "Transmission System collapsed and results ran days late. Observers drew a sharp line "
    "between the campaign, which they criticised heavily, and the conduct of voting itself, "
    "which they largely praised — while faulting the count."),
  "quotes": [
    {"who": "EU Election Observation Mission", "when": "Final report, October 2018",
     "q": "There was no level playing field for electoral contestants",
     "url": "https://www.eods.eu/library/final_report_pakistan_2018_english.pdf"},
    {"who": "EU Election Observation Mission", "when": "On polling day itself",
     "q": "Voting was assessed as well-conducted and transparent",
     "url": "https://www.eods.eu/library/final_report_pakistan_2018_english.pdf"},
    {"who": "Human Rights Commission of Pakistan", "when": "Pre-poll statement, 16 July 2018",
     "q": "blatant, aggressive and unabashed attempts to manipulate the outcome",
     "url": "https://hrcp-web.org/hrcpweb/attempts-to-maneuver-polls-unacceptable-hrcp/"},
  ],
 },
 "2024": {
  "date": "8 February 2024",
  "polled": "265 of 266",
  "postponed": "NA-8 Bajaur postponed",
  "turnout": "48%",
  "cands": "5,112",
  "tight": "68",
  "summary": (
    "The Supreme Court stripped PTI of its bat symbol on 13 January; its candidates contested as "
    "independents under individual symbols, which is how the returns record them. Polling in "
    "NA-8 Bajaur was called off after a candidate was shot dead. Mobile networks were shut down "
    "nationwide on polling day, results came roughly fifteen hours past the legal deadline, and "
    "the gap between polling-station Form 45s and consolidated Form 47s became the central "
    "dispute. The EU sent only a small expert mission, whose report has never been published."),
  "quotes": [
    {"who": "European Union", "when": "High Representative, 9 February 2024",
     "q": "We regret the lack of a level playing field",
     "url": "https://www.consilium.europa.eu/en/press/press-releases/2024/02/09/pakistan-statement-by-the-high-representative-on-behalf-of-the-european-union-on-the-general-elections/"},
    {"who": "Commonwealth Observer Group", "when": "Final report, published September 2025",
     "q": "impinged on the credibility, transparency and inclusiveness of the electoral process",
     "url": "https://thecommonwealth.org/news/cog-releases-final-report-pakistan-2024-general-elections"},
    {"who": "Human Rights Commission of Pakistan", "when": "Election report, February 2024",
     "q": "The integrity of the 2024 elections was compromised",
     "url": "https://www.thenews.com.pk/print/1158869-hrcp-releases-2024-election-report-demands-independent-audit"},
  ],
 },
}

def edit(path, reps):
    s = open(path, encoding="utf-8").read()
    for a, b in reps:
        n = s.count(a)
        assert n == 1, f"{path}: anchor matched {n}x (expected 1): {a[:70]!r}"
        s = s.replace(a, b, 1)
    open(path, "w", encoding="utf-8").write(s)
    print(f"{path}: {len(reps)} edits ok")

# ---------------------------------------------------------------- map.html ----
MAP = f"{ROOT}/map.html"

CSS_ANCHOR = "#map .cst{cursor:pointer}"
CSS_ADD = CSS_ANCHOR + """
.estat{display:grid;grid-template-columns:repeat(2,1fr);gap:10px 14px;margin:12px 0 14px}
.estat div span{display:block;font-family:'Space Mono',monospace;font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3)}
.estat div b{font-family:'Space Mono',monospace;font-size:15px;font-weight:700;color:var(--ink)}
.esum{font-size:12.8px;line-height:1.62;color:var(--ink-2);margin:0 0 12px}
.eq{border-left:2px solid var(--gold);padding:0 0 0 11px;margin:11px 0}
.eq .qt{font-family:'EB Garamond',serif;font-size:14.5px;line-height:1.45;color:var(--ink)}
.eq .qw{font-size:11.5px;color:var(--ink-3);margin-top:3px}
.eq .qw a{color:var(--ink-3);text-decoration:underline;text-underline-offset:2px}
.emore{font-size:11.5px}
.emore a{text-decoration:underline;text-underline-offset:2px}"""

HTML_ANCHOR = '      <div class="card" id="detail" style="flex:1"></div>'
HTML_ADD = HTML_ANCHOR + '\n      <div class="card" id="elecnote"></div>'

JS_ANCHOR = "function renderAll(){renderToolbar();if(state.tableMode){renderTable();}else{renderMap();}renderLegend();renderDetail();renderSearch();}"
JS_ADD = (
  "const ELEC=" + json.dumps(ELEC, ensure_ascii=False, separators=(",", ":")) + ";\n"
  "function renderElection(){\n"
  "  const e=ELEC[state.year]; const el=document.getElementById('elecnote'); if(!e||!el) return;\n"
  "  const q=e.quotes.map(x=>`<div class=\"eq\"><div class=\"qt\">&ldquo;${x.q}&rdquo;</div>"
  "<div class=\"qw\">${x.who} · <a href=\"${x.url}\" target=\"_blank\" rel=\"noopener\">${x.when}</a></div></div>`).join('');\n"
  "  el.innerHTML=`<div class=\"k\">This election · ${state.year}</div>\n"
  "  <div class=\"estat\">\n"
  "    <div><span>Seats polled</span><b>${e.polled}</b></div>\n"
  "    <div><span>Turnout</span><b>${e.turnout}</b></div>\n"
  "    <div><span>Candidates</span><b>${e.cands}</b></div>\n"
  "    <div><span>Won by under 5%</span><b>${e.tight}</b></div>\n"
  "  </div>\n"
  "  <p class=\"esum\">${e.summary}</p>\n"
  "  <div class=\"k\" style=\"margin-bottom:2px\">What observers said</div>\n"
  "  ${q}\n"
  "  <div class=\"emore\"><a href=\"method.html#elections\">Full account, with sources &rarr;</a></div>`;\n"
  "}\n"
  "function renderAll(){renderToolbar();if(state.tableMode){renderTable();}else{renderMap();}renderLegend();renderDetail();renderElection();renderSearch();}"
)

edit(MAP, [(CSS_ANCHOR, CSS_ADD), (HTML_ANCHOR, HTML_ADD), (JS_ANCHOR, JS_ADD)])
print("map.html patched: per-election card wired into renderAll()")
