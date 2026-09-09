#!/usr/bin/env python3
"""Build search-readable election results from the published explorer snapshot.

No network and no rebuilding the map: its boundary corrections must be retained.
Run again after publishing changes to map.html or the 2024 candidate CSV.
"""
import csv
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://aiwan.adaad.org"
E = html.escape
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
LICENSE_NOTES = "https://github.com/hibasameen/aiwan-e-jamhoor/blob/main/docs/DATA_LICENSE.md"
SITE_NAME = "Aiwan-e-Jamhoor"
TAGLINE = "The People's House"
OG_IMAGE = ORIGIN + "/og-image.png"
ADAAD = "https://adaad.org/"
# The same @ids adaad.org declares, so the three sites resolve to one publisher and one author.
PUBLISHER = {"@type": "Organization", "@id": ADAAD + "#publisher", "name": "Adaad", "url": ADAAD}
PERSON = {"@type": "Person", "@id": ADAAD + "about/#hiba-sameen", "name": "Hiba Sameen", "url": ADAAD + "about/", "sameAs": ["https://github.com/hibasameen", "https://www.linkedin.com/in/hiba-sameen-86750819/", "https://scholar.google.com/citations?user=FaZDLEUAAAAJ"]}
ICON = 'rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2064%2064%22%3E%3Crect%20width%3D%2264%22%20height%3D%2264%22%20rx%3D%2210%22%20fill%3D%22%2314523a%22/%3E%3Cg%20transform%3D%22translate%286%206%29%20scale%280.8125%29%22%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%2229%22%20fill%3D%22none%22%20stroke%3D%22%23f2efe6%22%20stroke-width%3D%221.8%22/%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%2226%22%20fill%3D%22none%22%20stroke%3D%22%23f2efe6%22%20stroke-width%3D%224.2%22%20stroke-dasharray%3D%223.4%203.4%22/%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%2223%22%20fill%3D%22none%22%20stroke%3D%22%23f2efe6%22%20stroke-width%3D%221.8%22/%3E%3Cg%20stroke%3D%22%23c9a13f%22%20stroke-width%3D%221.7%22%20fill%3D%22none%22%3E%3Cpath%20d%3D%22M13%2032%20H51%20M32%2013%20V51%20M15.55%2022.5%20L48.45%2041.5%20M22.5%2015.55%20L41.5%2048.45%20M22.5%2048.45%20L41.5%2015.55%20M15.55%2041.5%20L48.45%2022.5%22/%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%2219%22/%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%2213%22%20stroke-width%3D%222.2%22/%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%227%22/%3E%3C/g%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2232%22%20r%3D%223.6%22%20fill%3D%22%23c9a13f%22/%3E%3C/g%3E%3C/svg%3E"'
COOKMAN_YEARS = {"1993", "1997", "2002", "2008", "2013", "2018"}
BASE = {
    "index.html": ("Aiwan-e-Jamhoor — Pakistan Election Results, 1977–2024", "Explore Pakistan's National Assembly elections from 1977 to 2024: constituency results, candidates, vote margins and election history, with sources and caveats."),
    "map.html": ("Pakistan Election Results Map, 1977–2024 — Aiwan-e-Jamhoor", "Explore National Assembly constituency results across eleven Pakistan elections. Compare recorded winners, candidates, turnout and margins on each election's geography."),
    "candidates.html": ("Pakistan Election Candidates & Careers — Aiwan-e-Jamhoor", "Search National Assembly candidates and recorded electoral careers across Pakistan's elections, with linked constituencies, results and source limitations."),
    "house.html": ("Pakistan National Assembly: The House — Aiwan-e-Jamhoor", "Explore Pakistan's National Assembly membership and parliamentary record, with sources and methodology from Aiwan-e-Jamhoor."),
    "islam.html": ("Religious Parties in Pakistan Elections — Aiwan-e-Jamhoor", "Explore the electoral record of Pakistan's religious parties across National Assembly elections, with constituency results, definitions and historical context."),
    "about.html": ("About — Aiwan-e-Jamhoor", "About Aiwan-e-Jamhoor: Hiba Sameen's open archive of Pakistan's National Assembly elections since 1977, who built it, where the data comes from, and the licence. Published with Adaad."),
    "method.html": ("Pakistan Election Data: Sources & Methodology — Aiwan-e-Jamhoor", "Sources, constituency boundary methods, result vintages, corrections and limitations behind Aiwan-e-Jamhoor's Pakistan election archive."),
}
VINTAGE = "These are the results recorded in this archive, which combines election returns with later corrections, recounts and tribunal outcomes. They are not a certified election-day return or a statement of who currently holds the seat."
NOTE_2024 = "The 2024 candidate snapshot was compiled from ElectionPakistani in July 2026 and supplemented with ECP Form 47 figures where available. It includes the postponed NA-8 poll and later result changes. Candidate votes and the available official turnout figures can therefore refer to different stages of the result."


def literal(text, marker):
    return json.JSONDecoder().raw_decode(text.split(marker, 1)[1].lstrip())[0]


def ld(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def num(value, suffix=""):
    if value is None or value == "":
        return "Unavailable"
    return (f"{value:,}" if isinstance(value, int) else str(value)) + suffix


def metadata(title, desc, path, extra=None, tags=""):
    url = ORIGIN + path
    graph = [{"@type": "WebPage", "@id": url + "#page", "url": url, "name": title, "description": desc, "inLanguage": "en", "isPartOf": {"@id": ORIGIN + "/#website"}}]
    if path == "/":
        graph.append({"@type": "WebSite", "@id": ORIGIN + "/#website", "url": url, "name": SITE_NAME, "alternateName": ["Aiwan e Jamhoor", "ایوانِ جمہور", TAGLINE], "description": desc, "inLanguage": "en", "isPartOf": {"@id": ADAAD + "#website"}, "creator": PERSON, "publisher": PUBLISHER})
    if extra:
        graph.extend(extra if isinstance(extra, list) else [extra])
    return f'''<!-- SEO:START -->
<title>{E(title)}</title>
<meta name="description" content="{E(desc, quote=True)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{E(title, quote=True)}">
<meta property="og:description" content="{E(desc, quote=True)}">
<meta property="og:url" content="{url}">
<meta name="twitter:title" content="{E(title, quote=True)}">
<meta name="twitter:description" content="{E(desc, quote=True)}">
{tags}<script type="application/ld+json">{ld({"@context": "https://schema.org", "@graph": graph})}</script>
<!-- SEO:END -->'''


def patch_metadata(file, title, desc, path):
    text = file.read_text()
    text = re.sub(r"<!-- SEO:START -->.*?<!-- SEO:END -->\n?", "", text, flags=re.S)
    text = re.sub(r"<title>.*?</title>\s*", "", text, flags=re.S | re.I)
    text = re.sub(r'<meta\s+(?:name|property)=["\'](?:description|og:title|og:description|og:url|twitter:title|twitter:description)["\'][^>]*>\s*', "", text, flags=re.I)
    text = re.sub(r'<link\s+rel=["\']canonical["\'][^>]*>\s*', "", text, flags=re.I)
    tags = "" if "og:site_name" in text else f'<meta property="og:site_name" content="{SITE_NAME}">\n'
    text = text.replace("</head>", metadata(title, desc, path, tags=tags) + "\n</head>")
    text = text.replace("https://hibasameen.github.io/datadarbar/", "https://darbar.adaad.org/")
    text = text.replace("https://hibasameen.github.io/adaad-journal/", "https://adaad.org/")
    text = re.sub(r'<script\s+data-goatcounter="[^"]+"[^>]*></script>', '<script src="/assets/analytics.js" defer></script>', text)
    text = re.sub(r'<a href="/elections/">Results [Aa]rchive</a>\s*', "", text)
    text = re.sub(r'(<a[^>]*href="map\.html"[^>]*>Constituency Results</a>)', r'\1\n      <a href="/elections/">Results Archive</a>', text, count=1)
    file.write_text(text)


def table(headers, rows, caption):
    head = "".join(f'<th scope="col">{E(x)}</th>' for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap" role="region" aria-label="{E(caption)}" tabindex="0"><table><caption>{E(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def page(path, title, desc, body, extra=None):
    file = ROOT / path.strip("/") / "index.html"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{metadata(title, desc, path, extra)}
<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}"><meta property="og:image" content="{OG_IMAGE}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{OG_IMAGE}">
<link {ICON}>
<link rel="stylesheet" href="/fonts/fonts.css"><link rel="stylesheet" href="/assets/research.css">
</head><body><a class="skip" href="#content">Skip to results</a>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><symbol id="mk" viewBox="0 0 64 64"><circle cx="32" cy="32" r="29" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" stroke-width="4.2" stroke-dasharray="3.4 3.4"/><circle cx="32" cy="32" r="23" fill="none" stroke="currentColor" stroke-width="1.8"/><g stroke="#c9a13f" stroke-width="1.7" fill="none"><path d="M13 32 H51 M32 13 V51 M15.55 22.5 L48.45 41.5 M22.5 15.55 L41.5 48.45 M22.5 48.45 L41.5 15.55 M15.55 41.5 L48.45 22.5"/><circle cx="32" cy="32" r="19"/><circle cx="32" cy="32" r="13" stroke-width="2.2"/><circle cx="32" cy="32" r="7"/></g><circle cx="32" cy="32" r="3.6" fill="#c9a13f"/></symbol></svg>
<header><a class="brand" href="/"><svg class="mk" viewBox="0 0 64 64"><use href="#mk"></use></svg><span class="lockup"><span class="wm">{SITE_NAME}<span class="ur" lang="ur" dir="rtl">ایوانِ جمہور</span></span><span class="sub">{TAGLINE}</span></span></a><nav aria-label="Main"><a href="/">Home</a><a href="/map.html">Constituency Results</a><a href="/elections/">Results Archive</a><a href="/house.html">The House</a><a href="/candidates.html">Candidates</a><a href="/islam.html">Islam &amp; Politics</a><a href="/about.html">About</a><a href="/method.html">Method</a></nav></header>
<main id="content">{body}</main><footer><p>&copy; 2026 Hiba Sameen · Code: <a href="https://opensource.org/licenses/MIT">MIT Licence</a> · Derived data: <a href="{LICENSE}">CC BY 4.0</a>, subject to <a href="{LICENSE_NOTES}">upstream terms, including GPL for Cookman-derived results</a>. Credit the original sources and retain the result-vintage notes.</p><p><a href="/elections/">Results Archive</a> · <a href="/method.html">Method</a> · <a href="{ADAAD}">Adaad</a> · <a href="https://darbar.adaad.org/">Data Darbar: Pakistan statistics</a></p></footer><script src="/assets/analytics.js" defer></script></body></html>''')


def dataset(name, desc, path, download, year):
    return {"@type": "Dataset", "name": name, "description": desc + " " + VINTAGE, "url": ORIGIN + path, "creator": PERSON, "publisher": PUBLISHER, "license": LICENSE_NOTES if year in COOKMAN_YEARS else LICENSE, "isAccessibleForFree": True, "spatialCoverage": "Pakistan", "temporalCoverage": year, "isBasedOn": ORIGIN + "/method.html", "distribution": {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": ORIGIN + download}}


def write_csv(path, headers, rows):
    file = ROOT / path.strip("/")
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def seat_key(na):
    return int(na.split("-")[1])


def build():
    source = (ROOT / "map.html").read_text()
    results, elections = literal(source, "window.RESULTS="), literal(source, "const ELEC=")
    with (ROOT / "data/results_2024/na_2024_form47_official.csv").open() as handle:
        form47 = {r["na"]: r for r in csv.DictReader(handle)}
    candidates = defaultdict(list)
    with (ROOT / "data/results_2024/na_2024_candidates.csv").open() as handle:
        for row in csv.DictReader(handle):
            candidates[row["na"]].append(row)
    assert set(candidates) == set(results["2024"]), "2024 map/candidate seat coverage differs"
    year_links = []
    for year in sorted(results):
        seats, info = results[year], elections[year]
        path, download = f"/elections/{year}/", f"/elections/{year}/results.csv"
        title = f"Pakistan Election Results {year}: National Assembly — Aiwan-e-Jamhoor"
        desc = f"Pakistan's {year} National Assembly election: {len(seats)} constituency records, recorded winners, parties, votes, turnout and margins, with source and vintage notes."
        year_links.append(f'<li><a href="{path}">Pakistan election results {year}</a> — {len(seats)} constituency records</li>')
        rows, export = [], []
        for na in sorted(seats, key=seat_key):
            r = seats[na]
            target = f"/elections/2024/{na.lower()}/" if year == "2024" else f"/map.html?year={year}&amp;seat={na}"
            rows.append([f'<a href="{target}">{na} {E(r["name"])}</a>', E(r["wn"]), E(r["wp"]), E(num(r["wv"])), E(num(r.get("to"), "%")), E(num(r.get("mov"), " pp"))])
            export.append([year, na, r["name"], r["prov"], r["wn"], r["wp"], r["wv"], r.get("ws"), r.get("reg"), r.get("to"), r.get("mov"), r.get("nc")])
        write_csv(download, ["year", "seat", "constituency", "province", "recorded_winner", "party", "winner_votes", "winner_vote_share_pct", "registered_voters", "turnout_pct", "margin_pp", "candidate_count"], export)
        party_rows = [[E(p), str(n)] for p, n in Counter(r["wp"] for r in seats.values()).most_common()]
        caveat = NOTE_2024 if year == "2024" else "Seat numbers and boundaries change between elections. This table covers the constituency records available in the archive; it is not the total membership of the National Assembly. Missing values are shown as unavailable."
        if year == "1977":
            caveat += " PML-Q in 1977 means the Muslim League (Qayyum group), a 1970s faction, not the PML-Q founded in 2002."
        if year == "1985":
            caveat += " The 1985 election was non-party; Independent is not a party-affiliation claim."
        if int(year) <= 1990:
            caveat += " Registered-voter and turnout figures are unavailable for these individual constituency records."
        source_url = ("https://github.com/colincookman/pakistan_election_results_2018" if year == "2018" else "https://github.com/colincookman/pakistan_elections") if year in COOKMAN_YEARS else "https://www.electionpakistani.com/"
        source_name = "Colin Cookman’s Pakistan election datasets" if year in COOKMAN_YEARS else "ElectionPakistani"
        upstream_note = f'<p>These results derive from <a href="{source_url}">{source_name}</a>. ' + (f'Upstream GPL-3.0 terms apply when redistributing these derived files; the project’s CC BY notice is subject to those terms. Read the <a href="{LICENSE_NOTES}">data licence and attribution notes</a>.' if year in COOKMAN_YEARS else f'Read the <a href="{LICENSE_NOTES}">data licence and attribution notes</a>.') + '</p>'
        body = f'''<p class="crumb"><a href="/elections/">Results archive</a> / {year}</p><h1>Pakistan election results {year}</h1><p class="lede">National Assembly · Election date: {E(info['date'])} · {len(seats)} constituency records</p><p>{E(info['summary'])}</p><aside><h2>How to read this archive</h2><p>{VINTAGE}</p><p>{E(caveat)}</p></aside><p><a href="/map.html?year={year}">Explore the {year} election map</a> · <a href="{download}" download>Download the constituency summary CSV</a></p><h2>Recorded winners by party</h2><p>Counts cover the general-seat records below. Reserved seats and missing results are excluded.</p>{table(['Recorded party', 'Constituency records'], party_rows, f'{year}: parties of recorded winners')}<h2>Constituency results</h2>{table(['Constituency', 'Recorded winner', 'Party', 'Votes', 'Turnout', 'Margin'], rows, f'National Assembly results {year}')}<h2>Sources and definitions</h2>{upstream_note}<p>These values are the same as the published explorer. Margin is the winner–runner-up vote difference as a share of candidate votes, in percentage points. Turnout uses the available source denominator; it must not be reconstructed from a partial candidate list.</p><p><a href="/method.html">Full sources, coverage and corrections</a></p><h2>Cite this table</h2><p>Hiba Sameen / Aiwan-e-Jamhoor. Pakistan National Assembly election results {year}. <a href="{ORIGIN + path}">{ORIGIN + path}</a>. Cite with the archive's result-vintage qualifications.</p>'''
        page(path, title, desc, body, dataset(f"Pakistan National Assembly election results {year}", desc, path, download, year))

    for na in sorted(results["2024"], key=seat_key):
        r, rows = results["2024"][na], sorted(candidates[na], key=lambda x: int(x["rank"]))
        assert len(rows) == r["nc"], f"Candidate count mismatch: {na}"
        assert int(rows[0]["votes"]) == r["wv"] and rows[0]["candidate_name"] == r["wn"], f"Winner mismatch: {na}"
        path = f"/elections/2024/{na.lower()}/"
        download = path + "candidates.csv"
        title = f"{na} {r['name']} Election Result 2024 — Aiwan-e-Jamhoor"
        desc = f"{na} {r['name']}, Pakistan election 2024: recorded winner {r['wn']}, {r['wv']:,} votes, all {len(rows)} candidates, turnout and source notes."
        write_csv(download, ["na", "candidate_name", "party", "votes", "rank"], [[x[h] for h in ["na", "candidate_name", "party", "votes", "rank"]] for x in rows])
        total = sum(int(x["votes"]) for x in rows)
        candidate_rows = [[x["rank"], E(x["candidate_name"]), E(x["party"]), num(int(x["votes"])), f'{int(x["votes"]) / total * 100:.1f}%' if total else "Unavailable"] for x in rows]
        metrics = [("Registered voters", num(r.get("reg"))), ("Turnout", num(r.get("to"), "%")), ("Recorded margin", num(r.get("mov"), " percentage points")), ("Candidates", str(len(rows)))]
        metric_html = "".join(f"<div><dt>{label}</dt><dd>{E(value)}</dd></div>" for label, value in metrics)
        official = ""
        if r.get("f47w"):
            f = r["f47w"]
            official = f'<p class="source-alert"><strong>Different source stages:</strong> the ECP Form 47 return records {E(f["n"])} ({E(f["p"])}, {num(f["v"])} votes. The later candidate snapshot below records {E(r["wn"])} as winner. These two records are retained separately; neither is silently substituted for the other.</p>'
        flags = form47.get(na, {}).get("flags", "")
        if flags:
            quality = []
            for flag in flags.split(","):
                if flag == "valid+rej!=polled":
                    quality.append("Valid votes plus rejected votes do not equal the recorded polled total.")
                elif flag == "polled_m+f!=polled_total":
                    quality.append("Male and female polled-vote counts do not add to the recorded polled total.")
                elif flag == "multipage":
                    quality.append("The source return spans multiple pages.")
                elif flag.startswith("illegible:"):
                    quality.append("The source field “" + flag.split(":", 1)[1].replace("_", " ") + "” is illegible.")
                else:
                    quality.append("The Form 47 transcription flags: " + flag + ".")
            official += '<p class="source-alert"><strong>Form 47 transcription notes:</strong> ' + E(" ".join(quality)) + ' Figures above retain the explorer’s recorded values; flagged totals have not been recalculated.</p>'
        adjacent = [n for n in [f"NA-{seat_key(na)-1}", f"NA-{seat_key(na)+1}"] if n in results["2024"]]
        related = " · ".join(f'<a href="/elections/2024/{n.lower()}/">{n} {E(results["2024"][n]["name"])}</a>' for n in adjacent)
        body = f'''<p class="crumb"><a href="/elections/">Results archive</a> / <a href="/elections/2024/">2024 results</a> / {na}</p><h1>{na} {E(r['name'])} election result 2024</h1><p class="lede">National Assembly · {E(r['prov'])} · {E(r['name'])}</p><p><strong>Recorded winner: {E(r['wn'])}</strong> — {E(r['wp'])}, {num(r['wv'])} votes ({num(r['ws'], '%')} of candidate votes).</p><dl class="metrics">{metric_html}</dl><aside><h2>Result vintage and source differences</h2><p>{VINTAGE}</p><p>{NOTE_2024}</p>{official}</aside><p><a href="/map.html?year=2024&amp;seat={na}">Open {na} on the election map</a> · <a href="{download}" download>Download all candidates (CSV)</a></p><h2>All candidates and recorded votes</h2>{table(['Rank', 'Candidate', 'Party in source', 'Votes', 'Vote share'], candidate_rows, f'{na} {r["name"]}: 2024 candidate results')}<h2>Sources and definitions</h2><p>Candidate names, party labels and votes are retained from the <a href="/data/results_2024/na_2024_candidates.csv">published 2024 candidate dataset</a>. Vote shares use the total of those candidate votes and are rounded to one decimal place. The margin is expressed in percentage points. Party labels in this table follow the CSV source; the explorer may use expanded labels.</p><p>Registered voters and turnout reproduce the explorer's available official figures. Missing values mean unavailable. These boundaries apply to 2024; a seat with the same number in another election is not necessarily the same area.</p><p><a href="/method.html">Read the complete sources, method and corrections</a> · <a href="https://www.electionpakistani.com/ge2024/">ElectionPakistani 2024 returns</a> · <a href="/data/results_2024/na_2024_form47_official.csv">Available ECP Form 47 transcription</a></p><h2>Cite this result</h2><p>Hiba Sameen / Aiwan-e-Jamhoor. {na} {E(r['name'])}, National Assembly election 2024. <a href="{ORIGIN + path}">{ORIGIN + path}</a>. Include the result vintage when citing.</p><h2>Continue exploring</h2><p>{related}</p><p><a href="/elections/2024/">All 2024 constituency results</a></p>'''
        page(path, title, desc, body, dataset(f"{na} {r['name']} candidate results 2024", desc, path, download, "2024"))

    page("/elections/", "Pakistan Election Results, 1977–2024 — Aiwan-e-Jamhoor", "Browse eleven Pakistan National Assembly elections by year, with constituency results, recorded winners, source notes and downloadable tables.", f'<h1>Pakistan election results, 1977–2024</h1><p class="lede">National Assembly results by election year, with constituency tables you can read, cite and download.</p><p>{VINTAGE}</p><ul class="years">{"".join(year_links)}</ul><p>Each year uses the boundaries and constituency labels of its own archive. Coverage varies by election; the same seat number must not be treated as a continuous geographic history.</p><p><a href="/map.html">Explore the election map</a> · <a href="/method.html">Sources and methodology</a></p>')
    for name, (title, desc) in BASE.items():
        patch_metadata(ROOT / name, title, desc, "/" if name == "index.html" else "/" + name)
    # Keep future map builds' metadata in step without regenerating the patched map.
    template = ROOT / "src/map_template.html"
    if template.exists():
        patch_metadata(template, *BASE["map.html"], "/map.html")
    paths = ["/" if name == "index.html" else "/" + name for name in BASE]
    paths += ["/" + p.parent.relative_to(ROOT).as_posix() + "/" for p in (ROOT / "elections").rglob("index.html")]
    xml = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in sorted(paths):
        SubElement(SubElement(xml, "url"), "loc").text = ORIGIN + path
    (ROOT / "sitemap.xml").write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(xml, encoding="utf-8") + b"\n")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n")
    print(f"Built {len(results)} election years, {len(candidates)} constituency pages and {len(paths)} sitemap entries.")


if __name__ == "__main__":
    build()
