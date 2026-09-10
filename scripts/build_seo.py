#!/usr/bin/env python3
"""Search metadata for the hand-written pages, plus per-year results CSVs.

Writes the <!-- SEO:START/END --> block into each page in BASE (title,
description, canonical, share tags, JSON-LD), regenerates sitemap.xml and
robots.txt, and exports one constituency-summary CSV per election from the
RESULTS literal embedded in the published map. The CSVs are what the Method
page's data catalogue points at; there are no generated result pages.

No network and no rebuilding the map: its boundary corrections must be retained.
Run again after publishing changes to map.html.
"""
import csv
import html
import json
import re
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://aiwan.adaad.org"
E = html.escape
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
LICENSE_NOTES = "https://github.com/hibasameen/aiwan-e-jamhoor/blob/main/docs/DATA_LICENSE.md"
SITE_NAME = "Aiwan-e-Jamhoor"
TAGLINE = "The People's House"
ADAAD = "https://adaad.org/"
# The same @ids adaad.org declares, so the three sites resolve to one publisher and one author.
PUBLISHER = {"@type": "Organization", "@id": ADAAD + "#publisher", "name": "Adaad", "url": ADAAD}
PERSON = {"@type": "Person", "@id": ADAAD + "about/#hiba-sameen", "name": "Hiba Sameen", "url": ADAAD + "about/", "sameAs": ["https://github.com/hibasameen", "https://www.linkedin.com/in/hiba-sameen-86750819/", "https://scholar.google.com/citations?user=FaZDLEUAAAAJ"]}
COOKMAN_YEARS = {"1993", "1997", "2002", "2008", "2013", "2018"}
CSV_DIR = "data/results_by_year"
BASE = {
    "index.html": ("Aiwan-e-Jamhoor — Pakistan Election Results, 1977–2024", "Explore Pakistan's National Assembly elections from 1977 to 2024: constituency results, candidates, vote margins and election history, with sources and caveats."),
    "map.html": ("Pakistan Election Results Map, 1977–2024 — Aiwan-e-Jamhoor", "Explore National Assembly constituency results across eleven Pakistan elections. Compare recorded winners, candidates, turnout and margins on each election's geography."),
    "candidates.html": ("Pakistan Election Candidates & Careers — Aiwan-e-Jamhoor", "Search National Assembly candidates and recorded electoral careers across Pakistan's elections, with linked constituencies, results and source limitations."),
    "house.html": ("Pakistan National Assembly: The House — Aiwan-e-Jamhoor", "Explore Pakistan's National Assembly membership and parliamentary record, with sources and methodology from Aiwan-e-Jamhoor."),
    "islam.html": ("Religious Parties in Pakistan Elections — Aiwan-e-Jamhoor", "Explore the electoral record of Pakistan's religious parties across National Assembly elections, with constituency results, definitions and historical context."),
    "about.html": ("About — Aiwan-e-Jamhoor", "About Aiwan-e-Jamhoor: Hiba Sameen's open archive of Pakistan's National Assembly elections since 1977, who built it, where the data comes from, and the licence. Published with Adaad."),
    "method.html": ("Pakistan Election Data: Sources, Methodology & Downloads — Aiwan-e-Jamhoor", "Sources, constituency boundary methods, result vintages, corrections and limitations behind Aiwan-e-Jamhoor's Pakistan election archive, with downloadable results by election year."),
}
VINTAGE = "These are the results recorded in this archive, which combines election returns with later corrections, recounts and tribunal outcomes. They are not a certified election-day return or a statement of who currently holds the seat."


def literal(text, marker):
    return json.JSONDecoder().raw_decode(text.split(marker, 1)[1].lstrip())[0]


def ld(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


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


def patch_metadata(file, title, desc, path, extra=None):
    text = file.read_text()
    text = re.sub(r"<!-- SEO:START -->.*?<!-- SEO:END -->\n?", "", text, flags=re.S)
    text = re.sub(r"<title>.*?</title>\s*", "", text, flags=re.S | re.I)
    text = re.sub(r'<meta\s+(?:name|property)=["\'](?:description|og:title|og:description|og:url|twitter:title|twitter:description)["\'][^>]*>\s*', "", text, flags=re.I)
    text = re.sub(r'<link\s+rel=["\']canonical["\'][^>]*>\s*', "", text, flags=re.I)
    tags = "" if "og:site_name" in text else f'<meta property="og:site_name" content="{SITE_NAME}">\n'
    text = text.replace("</head>", metadata(title, desc, path, extra, tags=tags) + "\n</head>")
    text = text.replace("https://hibasameen.github.io/datadarbar/", "https://darbar.adaad.org/")
    text = text.replace("https://hibasameen.github.io/adaad-journal/", "https://adaad.org/")
    text = re.sub(r'<script\s+data-goatcounter="[^"]+"[^>]*></script>', '<script src="/assets/analytics.js" defer></script>', text)
    # The generated results archive (September 2026) is gone: its nav entry with it.
    text = re.sub(r'\s*<a href="/elections/">Results [Aa]rchive</a>', "", text)
    file.write_text(text)


def dataset(year, seats, info, download):
    source_url = ("https://github.com/colincookman/pakistan_election_results_2018" if year == "2018" else "https://github.com/colincookman/pakistan_elections") if year in COOKMAN_YEARS else "https://www.electionpakistani.com/"
    return {"@type": "Dataset", "@id": ORIGIN + download + "#dataset", "name": f"Pakistan National Assembly election results {year}", "description": f"Pakistan's {year} National Assembly election ({info['date']}): {len(seats)} constituency records with recorded winner, party, votes, vote share, registered voters, turnout, margin and candidate count. {VINTAGE}", "url": ORIGIN + "/method.html#downloads", "creator": PERSON, "publisher": PUBLISHER, "license": LICENSE_NOTES if year in COOKMAN_YEARS else LICENSE, "isAccessibleForFree": True, "spatialCoverage": "Pakistan", "temporalCoverage": year, "isBasedOn": source_url, "distribution": {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": ORIGIN + download}}


def build():
    source = (ROOT / "map.html").read_text()
    results, elections = literal(source, "window.RESULTS="), literal(source, "const ELEC=")
    out = ROOT / CSV_DIR
    out.mkdir(parents=True, exist_ok=True)
    datasets = []
    for year in sorted(results):
        seats, info = results[year], elections[year]
        download = f"/{CSV_DIR}/{year}.csv"
        with (out / f"{year}.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["year", "seat", "constituency", "province", "recorded_winner", "party", "winner_votes", "winner_vote_share_pct", "registered_voters", "turnout_pct", "margin_pp", "candidate_count"])
            for na in sorted(seats, key=lambda s: int(s.split("-")[1])):
                r = seats[na]
                writer.writerow([year, na, r["name"], r["prov"], r["wn"], r["wp"], r["wv"], r.get("ws"), r.get("reg"), r.get("to"), r.get("mov"), r.get("nc")])
        datasets.append(dataset(year, seats, info, download))
    catalog = {"@type": "DataCatalog", "@id": ORIGIN + "/method.html#catalog", "name": "Aiwan-e-Jamhoor election results by year", "url": ORIGIN + "/method.html#downloads", "creator": PERSON, "publisher": PUBLISHER, "dataset": datasets}
    for name, (title, desc) in BASE.items():
        patch_metadata(ROOT / name, title, desc, "/" if name == "index.html" else "/" + name, catalog if name == "method.html" else None)
    # Keep future map builds' metadata in step without regenerating the patched map.
    template = ROOT / "src/map_template.html"
    if template.exists():
        patch_metadata(template, *BASE["map.html"], "/map.html")
    paths = ["/" if name == "index.html" else "/" + name for name in BASE]
    xml = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in sorted(paths):
        SubElement(SubElement(xml, "url"), "loc").text = ORIGIN + path
    (ROOT / "sitemap.xml").write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(xml, encoding="utf-8") + b"\n")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n")
    print(f"Wrote {len(datasets)} results CSVs, {len(paths)} sitemap entries.")


if __name__ == "__main__":
    build()
