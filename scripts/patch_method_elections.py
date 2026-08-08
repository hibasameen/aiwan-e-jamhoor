#!/usr/bin/env python3
"""Add a sourced 'The four elections' section to method.html (anchor #elections)
and mirror a condensed version into METHODOLOGY.md."""

ROOT = "mnt/Aiwan-e-Jamhoor"

def edit(path, reps):
    s = open(path, encoding="utf-8").read()
    for a, b in reps:
        n = s.count(a)
        assert n == 1, f"{path}: anchor matched {n}x (expected 1): {a[:70]!r}"
        s = s.replace(a, b, 1)
    open(path, "w", encoding="utf-8").write(s)
    print(f"{path}: {len(reps)} edits ok")

# --------------------------------------------------------------- method.html --
SECTION = '''
    <h2 id="elections"><span class="n">08</span>The four elections</h2>
    <p>A seat map flattens an election into a colour. It cannot show that one campaign was fought
    under a boycott, another under a bombing campaign aimed at three particular parties, and a third
    with the largest party stripped of its ballot symbol. This section records those circumstances
    for each election, so that the map is read with them rather than without them.</p>

    <p>The standard here is the same one the boundary work uses: <strong>we report what named
    observers concluded, quote them, and link the source.</strong> Aiwan-e-Jamhoor offers no verdict
    of its own on whether an election was free or fair, and publishes no aggregate "fairness score" —
    the judgements below belong to the bodies that made them, they do not always agree, and where
    they disagree that disagreement is itself the finding. Seats-polled, candidate and margin figures
    are computed from this project's own results data; turnout is our registered-voter-weighted
    figure, which tracks the official numbers closely.</p>

    <table>
      <thead><tr><th>Election</th><th>Date</th><th class="mono">Seats polled</th><th class="mono">Turnout</th><th class="mono">Candidates</th><th class="mono">Won by &lt;5%</th></tr></thead>
      <tbody>
        <tr><td>2008</td><td>18 Feb 2008</td><td class="mono">268 of 272</td><td class="mono">44%</td><td class="mono">2,180</td><td class="mono">62</td></tr>
        <tr><td>2013</td><td>11 May 2013</td><td class="mono">269 of 272</td><td class="mono">55%</td><td class="mono">4,496</td><td class="mono">52</td></tr>
        <tr><td>2018</td><td>25 Jul 2018</td><td class="mono">270 of 272</td><td class="mono">52%</td><td class="mono">3,431</td><td class="mono">79</td></tr>
        <tr><td>2024</td><td>8 Feb 2024</td><td class="mono">265 of 266</td><td class="mono">48%</td><td class="mono">5,112</td><td class="mono">68</td></tr>
      </tbody>
    </table>

    <h3>2008 — the postponed election</h3>
    <p>Polling was moved from 8 January to 18 February after Benazir Bhutto was assassinated on
    27 December 2007. Four constituencies did not poll on the day, among them the seat she would have
    contested; polling in Kurram was also postponed after a bombing outside a candidate's office two
    days before the vote. The election was administered by a Commission appointed under Pervez
    Musharraf, with the judges dismissed in the November 2007 emergency still not restored, and it was
    boycotted by PTI, Jamaat-e-Islami and the rest of the All Parties Democratic Movement. Pakistan
    was suspended from the Commonwealth at the time, so no Commonwealth group observed.</p>
    <p>The <a href="http://www.eods.eu/library/eu_eom_pakistan_final_report.pdf">EU Election
    Observation Mission</a> concluded in its April 2008 final report that &ldquo;a level playing field
    was not provided during the campaign,&rdquo; citing abuse of state resources and bias in the state
    media, while assessing voting and counting more favourably. The US mission fielded by
    <a href="https://democracyinternational.com/media/U.S.%20Election%20Observation%20Mission%20to%20Pakistan%20General%20Elections%202008%20Final%20Report.pdf">Democracy
    International</a> found that &ldquo;the elections provided a genuine opportunity for Pakistani
    voters to express their will,&rdquo; alongside &ldquo;significant procedural irregularities.&rdquo;
    Turnout is usually given as about 44 per cent; the Election Commission does not appear to have
    published a single official national figure.</p>

    <h3>2013 — the first civilian handover</h3>
    <p>For the first time, an elected civilian government in Pakistan completed its term and handed
    power to another. Turnout, at about 55 per cent, was the highest since 1977. But the campaign was
    not equally free for everyone contesting it: the Pakistani Taliban attacked the three parties of
    the outgoing coalition — ANP, MQM and PPP — while their opponents campaigned openly, a
    distinction observers treated as central rather than incidental.</p>
    <p>The <a href="https://www.eeas.europa.eu/sites/default/files/pakistan_eom_final_report_eng_1.pdf">EU
    Election Observation Mission</a> found that &ldquo;the high number of attacks affected campaigning
    and unbalanced the playing field,&rdquo; and separately recorded roughly eleven million fewer
    registered women than men. The <a href="https://thecommonwealth.org/news/pakistan-general-elections-2013-interim-statement">Commonwealth
    Observer Group</a> called the elections &ldquo;notable progress for Pakistan towards holding fully
    democratic elections.&rdquo; PTI alleged rigging in four constituencies; a commission of three
    Supreme Court judges reported in July 2015 that the election had been
    <a href="https://www.dawn.com/news/1195875">&ldquo;in large part organised and conducted fairly and
    in accordance with the law,&rdquo;</a> while holding that PTI had not been unjustified in asking.
    Around 500 polling stations recorded no women voting at all, and re-polling was ordered in several
    places on that ground.</p>

    <h3>2018 — two verdicts on one election</h3>
    <p>Nawaz Sharif was disqualified from public office for life in April 2018 and jailed twelve days
    before the poll. Around 370,000 troops were deployed, many stationed inside polling stations and
    granted magisterial powers. On election night the Commission's new Result Transmission System
    stopped working shortly before midnight, the statutory 2 a.m. deadline for provisional results was
    missed, and final results were not consolidated until 7 August.</p>
    <p>What makes 2018 instructive is that the observers reached two different verdicts about the same
    election, and both belong in the record. On the campaign, the
    <a href="https://www.eods.eu/library/final_report_pakistan_2018_english.pdf">EU Election Observation
    Mission</a> was blunt: &ldquo;There was no level playing field for electoral contestants.&rdquo; On
    the day itself the same mission found that &ldquo;voting was assessed as well-conducted and
    transparent,&rdquo; while faulting the count, which it judged positively in only two-thirds of
    observations, concluding that tabulation &ldquo;lacked transparency.&rdquo; Its chief observer
    nonetheless called the results credible. Before the vote, the
    <a href="https://hrcp-web.org/hrcpweb/attempts-to-maneuver-polls-unacceptable-hrcp/">Human Rights
    Commission of Pakistan</a> had warned of &ldquo;blatant, aggressive and unabashed attempts to
    manipulate the outcome.&rdquo; The domestic network
    <a href="https://fafen.org/fafens-preliminary-election-observation-report/">FAFEN</a>, with nearly
    20,000 observers, reported that election day was &ldquo;better managed, relatively peaceful and
    free of any major controversy.&rdquo; One caveat on coverage: EU observers did not deploy in
    Balochistan for security reasons, which is where the worst poll-day violence occurred.</p>

    <h3>2024 — an election without a symbol</h3>
    <p>On 13 January 2024 the Supreme Court restored the Election Commission's ruling that PTI's
    intra-party elections were invalid, and the party lost its cricket-bat symbol for the election.
    Its candidates contested as independents, each assigned a different symbol from the free pool —
    which is how the returns record them, and why the independent column on the 2024 map is what it
    is. Losing party status also cost PTI its claim on reserved seats, the question that went back to
    the Supreme Court in July 2024 and was reversed again on review in June 2025. Polling in NA-8
    Bajaur was called off after a candidate was shot dead while canvassing.</p>
    <p>Mobile networks were shut down nationwide on polling day, which the interior ministry justified
    on security grounds and which disabled the Commission's own results-management system; 16 people
    were killed in poll-day violence regardless. Results ran roughly fifteen hours past the legal
    deadline. The central dispute afterwards concerned the gap between the polling-station count
    (Form 45) and the consolidated constituency result (Form 47) — allegations that remain
    unadjudicated, with no tribunal or court having confirmed systematic rigging, and which this
    project's own comparison of 254 official Form 47s against a transcription of the published results
    can speak to only partially: identical winners in 249 of 254 seats, five later reversed.</p>
    <p>The EU did not send a full observation mission in 2024, only a small expert mission whose report
    has never been published; access to it was refused in 2025 on international-relations grounds. The
    <a href="https://www.consilium.europa.eu/en/press/press-releases/2024/02/09/pakistan-statement-by-the-high-representative-on-behalf-of-the-european-union-on-the-general-elections/">EU's
    High Representative</a> said on 9 February that &ldquo;we regret the lack of a level playing
    field.&rdquo; The <a href="https://thecommonwealth.org/news/cog-releases-final-report-pakistan-2024-general-elections">Commonwealth
    Observer Group</a>, in a final report not published until September 2025, found that institutional
    decisions &ldquo;impinged on the credibility, transparency and inclusiveness of the electoral
    process.&rdquo; The <a href="https://www.thenews.com.pk/print/1158869-hrcp-releases-2024-election-report-demands-independent-audit">Human
    Rights Commission of Pakistan</a> concluded that &ldquo;the integrity of the 2024 elections was
    compromised,&rdquo; and called for an independent audit.</p>

    <div class="callout">
      <span class="lbl">What we do not do</span>
      We do not rank the four elections against one another, and we do not convert these findings into
      a score. Observer missions differ in mandate, coverage and access — the EU covered no polling
      stations in Balochistan in 2018 and sent no public mission at all in 2024 — so the absence of a
      finding is not evidence of its absence. Read the quotations as what a named body concluded on a
      stated date, nothing more and nothing less.
    </div>
'''

TOC_ANCHOR = '      <li><a href="#limits">Limitations</a></li>'
TOC_NEW = ('      <li><a href="#elections">The four elections</a></li>\n'
           '      <li><a href="#limits">Limitations</a></li>')

LIMITS_ANCHOR = '    <h2 id="limits"><span class="n">08</span>Limitations, in one place</h2>'
LIMITS_NEW = SECTION + '\n    <h2 id="limits"><span class="n">09</span>Limitations, in one place</h2>'

SOURCES_ANCHOR = '    <h2 id="sources"><span class="n">09</span>Sources</h2>'
SOURCES_NEW = '    <h2 id="sources"><span class="n">10</span>Sources</h2>'

edit(f"{ROOT}/method.html", [
    (TOC_ANCHOR, TOC_NEW),
    (SOURCES_ANCHOR, SOURCES_NEW),   # renumber before inserting, so anchors stay unique
    (LIMITS_ANCHOR, LIMITS_NEW),
])

# ------------------------------------------------------------ METHODOLOGY.md --
MD_ANCHOR = None
MD_NEW = """
## 9. The four elections — circumstances and observer findings

A seat map cannot show that one campaign was fought under a boycott, another under a bombing
campaign aimed at three named parties, and a third with the largest party stripped of its ballot
symbol. The app carries a per-election context card (map page, right column) and the Method page
carries the full account. The standard is the same one used for boundaries: **report what named
observers concluded, quote them, link the source, and offer no verdict of our own.** No aggregate
"fairness score" is published.

| Election | Date | Seats polled | Turnout | Candidates | Won by <5% |
|---|---|---|---|---|---|
| 2008 | 18 Feb 2008 | 268 of 272 | 44% | 2,180 | 62 |
| 2013 | 11 May 2013 | 269 of 272 | 55% | 4,496 | 52 |
| 2018 | 25 Jul 2018 | 270 of 272 | 52% | 3,431 | 79 |
| 2024 | 8 Feb 2024 | 265 of 266 | 48% | 5,112 | 68 |

Seats-polled, candidate counts and margins are computed from `data/results_all.json`; turnout is the
registered-voter-weighted figure from our own data, which tracks the official numbers (2008 ~44%,
2013 55.0% ECP, 2018 51.9–52.1%, 2024 47.6% FAFEN-from-ECP).

- **2008** — poll moved from 8 Jan to 18 Feb after Benazir Bhutto's assassination; 4 seats did not
  poll; boycotted by PTI, JI and the APDM; no Commonwealth observation (Pakistan was suspended).
  EU EOM: "a level playing field was not provided during the campaign." Democracy International:
  "the elections provided a genuine opportunity for Pakistani voters to express their will."
- **2013** — first civilian-to-civilian handover; highest turnout since 1977; TTP violence targeted
  ANP, MQM and PPP specifically. EU EOM: "The high number of attacks affected campaigning and
  unbalanced the playing field." 2015 judicial commission: "in large part organised and conducted
  fairly and in accordance with the law." ~500 polling stations recorded zero women voting.
- **2018** — Nawaz Sharif disqualified for life and jailed 12 days before the poll; ~370,000 troops
  deployed, many inside polling stations; the RTS collapsed on election night. Two distinct verdicts
  from the same mission: EU EOM "There was no level playing field for electoral contestants" on the
  campaign, but "Voting was assessed as well-conducted and transparent" on the day, with the count
  faulted. EU observers did not cover Balochistan.
- **2024** — Supreme Court stripped PTI of its symbol on 13 Jan; candidates ran as independents;
  NA-8 Bajaur postponed after a candidate was killed; nationwide mobile shutdown on polling day;
  results ~15 hours late; Form-45 vs Form-47 dispute unadjudicated. EU High Representative: "We
  regret the lack of a level playing field." Commonwealth (final report Sept 2025): "impinged on the
  credibility, transparency and inclusiveness of the electoral process." HRCP: "The integrity of the
  2024 elections was compromised."

Caveat carried in the app: observer missions differ in mandate, coverage and access, so the absence
of a finding is not evidence of its absence."""

mp=f"{ROOT}/METHODOLOGY.md"
ms=open(mp,encoding="utf-8").read()
assert "## 9. The four elections" not in ms, "already appended"
open(mp,"a",encoding="utf-8").write("\n"+MD_NEW+"\n")
print(f"{mp}: elections section appended")
print("done")
