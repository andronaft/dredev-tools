"""The open data page: the refrigerant pressure-temperature tables behind the PT charts as CSV and JSON files.

build.py passes itself in as `b` and calls build(b) once. The files are written from b.PT, the same tables the
charts and the calculator use, so the download cannot drift from the pages. Rows copied from a manufacturer's
table are not recalculated. The five refrigerants whose chart came from the NIST WebBook (R-290, R-600a, R-744,
R-717, R-12) are published here as values computed with CoolProp instead (coolprop-pt.json, written by
tools/coolprop_pt.py): NIST claims copyright in its Standard Reference Data, CoolProp is MIT-licensed, and the two
agree within 0.04 psi. The build stops if a computed value and the chart cell ever differ by more than rounding.
"""
import csv
import io
import json
from html import escape as e
from pathlib import Path

import guides
import opendata
from pagekit import CSS, HVAC_NOTE, REL, crumbs, person, related, table, url

PATH = "hvac/refrigerant-pt-data.html"
CSV_PATH = "hvac/data/refrigerant-pt.csv"
JSON_PATH = "hvac/data/refrigerant-pt.json"
NAME = "Refrigerant pressure-temperature (saturation) tables for 22 refrigerants"
VERSION = "1.0.0"
PUBLISHED = "2026-11-20"
LICENSE_NAME = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

# Source title as written in the app (hvac-charge-app/lib/feature/engine/pt.dart) -> (id in the files, what the
# source says its numbers are based on, address, day it was retrieved). From the app's docs/SOURCES.md. A source
# that is not listed here stops the build: a table must not be published without its provenance.
SOURCES = {
    "Arkema Forane® Pressure Temperature Chart (PPC/SDC 05-2025)": (
        "arkema-2025", "NIST REFPROP 10.0 (stated on the chart)",
        "https://forane.arkema.com/files/live/sites/shared_arkema/files/downloads/fluorochemicals/Forane%20Ref%20PT%20Regular%20Chart%20EN",
        "2026-10-25"),
    "Arkema Forane® Pressure-Temperature Wall Chart, Americas (2019)": (
        "arkema-2019", "NIST REFPROP 9.0 (stated on the chart)",
        "https://forane.arkema.com/files/live/sites/fluorogases_forane_arkema/files/downloads/literature/general-forane-literature/forane-wall-chart-americas.pdf",
        "2026-10-25"),
    "Chemours, Thermodynamic Properties of Opteon™ YF, Engineering (I/P) Units": (
        "chemours-yf", "Manufacturer saturation table, 1 °F steps, psia",
        "https://www.opteon.com/en/-/media/files/opteon/opteon-yf-thermodynamic-properties-eng.pdf",
        "2026-10-26"),
    "NIST Chemistry WebBook, SRD 69, saturation properties": (
        "nist-webbook", "NIST reference equations of state (Thermophysical Properties of Fluid Systems)",
        "https://webbook.nist.gov/chemistry/fluid/",
        "2026-10-26"),
}
COOLPROP = json.loads((Path(__file__).resolve().parent / "coolprop-pt.json").read_text())
COOLPROP_TITLE = f"CoolProp {COOLPROP['coolprop_version']}, saturation pressure computed for this data set"
SOURCES[COOLPROP_TITLE] = (
    "coolprop", "Open-source property library (MIT licence); Helmholtz-energy equations of state from the literature",
    "http://www.coolprop.org/", "2026-11-20")
COLUMNS = [
    ("refrigerant", "", "ASHRAE designation, for example R-454B."),
    ("safety_class", "", "ASHRAE Standard 34 safety class as used on the chart pages (A1, A2L, A3, B2L)."),
    ("temp_f", "°F", "Saturation temperature. One row every 5 °F, as the source charts are printed."),
    ("temp_c", "°C", "The same temperature in Celsius, rounded to 0.01."),
    ("liquid_psig", "psi, gauge", "Liquid (bubble point) pressure. For a refrigerant with one column this is the saturation pressure. Negative means below atmospheric pressure."),
    ("vapor_psig", "psi, gauge", "Vapor (dew point) pressure. Empty where the source prints one column, and for the few vapor cells left out (see below)."),
    ("liquid_psia", "psi, absolute", "liquid_psig + 14.695949."),
    ("vapor_psia", "psi, absolute", "vapor_psig + 14.695949."),
    ("liquid_kpa", "kPa, absolute", "liquid_psia × 6.894757."),
    ("vapor_kpa", "kPa, absolute", "vapor_psia × 6.894757."),
    ("source", "", "Id of the source of the row; the sources are listed below and in the JSON file."),
]
KPA_PER_PSI = 6.894757


def title_of(r):
    """The source title of a refrigerant's rows in the files (not always the source of the chart on the site)."""
    title = COOLPROP_TITLE if r["id"] in COOLPROP["psia"] else r["source"]
    if title not in SOURCES:
        raise SystemExit(f'pages_data.py: no provenance entry for the PT source "{title}" ({r["id"]})')
    return title


def source_of(r):
    return SOURCES[title_of(r)]


def used_sources(b):
    used = {}
    for r in b.PT.values():
        used.setdefault(title_of(r), []).append(r["id"])
    return used


def gauge_psi(b, cell):
    """A chart cell as true gauge pressure in psi. The tables keep vacuum cells as negative inches of mercury."""
    return cell if cell >= 0 else cell * b.PSI_PER_INHG


def records(b):
    """One row per refrigerant and temperature, over every temperature at least one column has."""
    out = []
    for rid, r in b.PT.items():
        bub, dew = r["bubble"], r["dew"]
        sid = source_of(r)[0]
        for i, cell in enumerate(bub["psig"]):
            t = bub["startF"] + 5 * i
            liquid = round(gauge_psi(b, cell), 2)
            psia = None
            if rid in COOLPROP["psia"]:
                psia = COOLPROP["psia"][rid][str(t)]
                if abs(psia - b.ATM_PSIA - liquid) > 0.06:
                    raise SystemExit(f"pages_data.py: CoolProp and the chart disagree for {rid} at {t} °F: {psia - b.ATM_PSIA:.3f} vs {liquid}")
                liquid = round(psia - b.ATM_PSIA, 2)
            vapor = None
            if dew:
                j = (t - dew["startF"]) // 5
                if 0 <= j < len(dew["psig"]):
                    vapor = round(gauge_psi(b, dew["psig"][j]), 2)
            row = {"refrigerant": rid, "safety_class": r["safety"], "temp_f": t, "temp_c": round((t - 32) * 5 / 9, 2),
                   "liquid_psig": liquid, "vapor_psig": vapor,
                   "liquid_psia": round(psia if psia is not None else liquid + b.ATM_PSIA, 2), "vapor_psia": None if vapor is None else round(vapor + b.ATM_PSIA, 2)}
            row["liquid_kpa"] = round(row["liquid_psia"] * KPA_PER_PSI, 1)
            row["vapor_kpa"] = None if vapor is None else round(row["vapor_psia"] * KPA_PER_PSI, 1)
            row["source"] = sid
            out.append(row)
    return out


def csv_text(rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    names = [c[0] for c in COLUMNS]
    w.writerow(names)
    for row in rows:
        w.writerow(["" if row[n] is None else row[n] for n in names])
    return buf.getvalue()


def citation(b):
    return (f"{guides.AUTHOR} ({PUBLISHED[:4]}). {NAME} (version {VERSION}) [Data set]. {b.CFG['brand']}. "
            f"{url(b, PATH)}")


def json_obj(b, rows):
    used = used_sources(b)
    return {
        "name": NAME, "version": VERSION, "published": PUBLISHED, "url": url(b, PATH),
        "license": LICENSE_NAME, "license_url": LICENSE_URL, "cite_as": citation(b),
        "notes": "Pressures are saturation pressures every 5 °F. Gauge pressure is relative to the standard atmosphere, "
                 "14.695949 psia; negative gauge values are below atmospheric pressure. A null vapor value means the "
                 "source prints one column for that refrigerant, or that cell was left out. Reference data: verify "
                 "against the equipment manufacturer's data before acting on it.",
        "columns": [{"name": n, "unit": u, "description": d} for n, u, d in COLUMNS],
        "sources": [{"id": SOURCES[s][0], "title": s, "basis": SOURCES[s][1], "url": SOURCES[s][2], "retrieved": SOURCES[s][3],
                     "refrigerants": ids} for s, ids in used.items()],
        "refrigerants": [{"id": rid, "safety_class": r["safety"], "use": r["use"], "columns": 2 if r["dew"] else 1,
                          "source": source_of(r)[0]} for rid, r in b.PT.items()],
        "rows": rows,
    }


def long_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    months = "January February March April May June July August September October November December".split()
    return f"{d} {months[m - 1]} {y}"


def build(b):
    rows = records(b)
    text = csv_text(rows)
    dest = b.OUT / CSV_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    (b.OUT / JSON_PATH).write_text(json.dumps(json_obj(b, rows), ensure_ascii=False, separators=(",", ":")) + "\n")

    n = len(b.PT)
    two = sum(1 for r in b.PT.values() if r["dew"])
    used = used_sources(b)
    source_rows = [[f'<code>{SOURCES[s][0]}</code>', f'<a href="{e(SOURCES[s][2])}" rel="noopener">{e(s)}</a>', e(SOURCES[s][1]),
                    ", ".join(ids), long_date(SOURCES[s][3])] for s, ids in used.items()]
    column_rows = [[f"<code>{name}</code>", e(unit) or "–", e(desc)] for name, unit, desc in COLUMNS]
    ref_rows = []
    for rid, r in b.PT.items():
        bub = r["bubble"]
        end = bub["startF"] + 5 * (len(bub["psig"]) - 1)
        ref_rows.append([f'<a href="{REL}hvac/pt-chart/{b.slug(rid)}.html">{rid}</a>', r["safety"], "Liquid and vapor" if r["dew"] else "One",
                         f'{bub["startF"]} to {end} °F', f"<code>{source_of(r)[0]}</code>"])
    sample = "\n".join(text.splitlines()[:4])
    cite = citation(b)
    bibtex = (f"@misc{{zhukovskyi_refrigerant_pt_{PUBLISHED[:4]},\n  author = {{{guides.AUTHOR}}},\n  title = {{{NAME}}},\n"
              f"  year = {{{PUBLISHED[:4]}}},\n  version = {{{VERSION}}},\n  publisher = {{{b.CFG['brand']}}},\n"
              f"  howpublished = {{\\url{{{url(b, PATH)}}}}},\n  note = {{Data set, {LICENSE_NAME}}}\n}}")
    desc = (f"Saturation pressure against temperature for {n} refrigerants, every 5 °F, as CSV and JSON: R-454B, R-32, R-410A, R-22, "
            f"R-134a, R-404A and more. Sources named per row, {LICENSE_NAME}.")
    body = f"""{CSS}
{crumbs([("Tools", "index.html"), ("HVAC", "hvac/index.html"), ("PT data", PATH)])}
<div class="hero"><div class="eyebrow">Open data</div>
<h1>Refrigerant PT data: CSV and JSON</h1>
<p class="lead">The pressure-temperature tables behind the PT charts and the superheat calculator on this site, as two files:
{n} refrigerants, {len(rows):,} rows, one row every 5 °F. Free to use with credit.</p>
<p class="btns"><a class="btn" href="{REL}{CSV_PATH}" download>Download CSV</a> <a class="btn ghost" href="{REL}{JSON_PATH}" download>Download JSON</a></p></div>

<section class="prose"><h2>What is in the files</h2>
<p>Saturation pressure at each temperature for {n} refrigerants. {two} of them are blends with two columns, liquid (bubble point) and vapor
(dew point); the other {n - two} have one column. Both files hold the same rows. The JSON file also carries the column descriptions, the
list of sources and one line per refrigerant.</p>
<pre class="sample">{e(sample)}</pre></section>

<section><h2>Columns</h2>
{table(["Column", "Unit", "Meaning"], column_rows, "datacols")}</section>

<section><h2>Where the numbers come from</h2>
<p class="muted">Nothing in the files was measured by me. {n - len(COOLPROP["psia"])} refrigerants are read from three published manufacturer tables; {len(COOLPROP["psia"])} are computed with the open-source CoolProp library. Each row names its source.</p>
{table(["Id in the files", "Source", "What the source says it is based on", "Refrigerants", "Retrieved"], source_rows, "datacols")}
<div class="prose">
<p>How the values got here:</p>
<ul>
<li>The Arkema charts print gauge pressure (psig) every 5 °F, and inches of mercury below one atmosphere for vacuum cells. A script read both
PDFs cell by cell; the values were copied, not recalculated. In the files the vacuum cells are converted to negative psi (1 inHg = 0.4911541 psi),
so one column has one unit.</li>
<li>The Chemours table gives absolute pressure (psia). The 5 °F rows were kept and turned into gauge pressure by subtracting
the standard atmosphere, 14.695949 psi, then rounded the way the printed charts are: to 0.1 psi above atmospheric pressure and to 0.1 inHg below it.
The source itself gives more digits.</li>
<li>{", ".join(COOLPROP["psia"])} are computed: saturation pressure of the pure fluid at each temperature with CoolProp {COOLPROP["coolprop_version"]}
(<code>PropsSI("P", "T", T, "Q", 0, fluid)</code>), kept to 0.01 psi. The PT charts on this site for these five were read from the NIST Chemistry
WebBook; the computed values agree with them within 0.04 psi, and the build stops if a row ever differs from its chart cell by more than rounding.
The files carry the computed values so that every number in them is either a manufacturer's printed cell or the output of MIT-licensed software.</li>
<li>The absolute columns (<code>psia</code>, <code>kpa</code>) and <code>temp_c</code> are plain unit conversions of the columns next to them.</li>
<li>R-427A is taken from the 2019 Arkema chart, because the 2025 edition prints two cells of another refrigerant in its 150 °F row.</li>
<li>A few vapor cells of R-448A, R-449A and R-452A, and the rows of R-513A below −20 °F, are left out: the 2025 chart prints those vacuum cells in a unit that
does not match its legend, so they were not re-interpreted. That is why some <code>vapor_psig</code> cells are empty and R-513A starts at −20 °F.</li>
</ul>
<p>Checks, as listed in the <a href="{REL}methodology.html">methodology</a>: Arkema's R-454B columns agree with Chemours' 1 °F table for Opteon™ XL41
within 0.06 psi, and values interpolated between rows agree with CoolProp 8.0 (NIST reference equations). No outside trade professional or
laboratory has reviewed the files.</p></div></section>

<section><h2>Refrigerants</h2>
{table(["Refrigerant", "Safety class", "Columns", "Range", "Source"], ref_rows)}</section>

<section class="prose"><h2>Licence</h2>
<p>This compilation (the selection, the checks, the unit conversions, the file layout and the documentation) is published under
<a href="{LICENSE_URL}" rel="license noopener">Creative Commons Attribution 4.0 International ({LICENSE_NAME})</a>: copy it, change it and use it in
any product, commercial ones included, as long as you give credit as shown below.</p>
<p>The values in the <code>arkema-…</code> and <code>chemours-yf</code> rows were published by Arkema and Chemours. I claim no rights in their
numbers and cannot grant any; if you republish the files, keep the <code>source</code> column so the origin stays visible. The <code>coolprop</code>
rows are my own computation with <a href="http://www.coolprop.org/" rel="noopener">CoolProp</a> (MIT licence) and are covered by the licence above.</p></section>

<section class="prose"><h2>How to cite</h2>
<p>In text:</p>
<pre class="sample">{e(cite)}</pre>
<p>BibTeX:</p>
<pre class="sample">{e(bibtex)}</pre>
<p>On a web page a link is enough: <code>&lt;a href="{url(b, PATH)}"&gt;Refrigerant PT data, {b.CFG['brand']}&lt;/a&gt;</code>. If your work depends on
one refrigerant, cite the manufacturer's table or CoolProp from the list above as well.</p></section>

<section class="prose"><h2>Limits</h2>
<p>{HVAC_NOTE}</p>
<p>The tables stop where the printed charts stop; there is no extrapolation. Gauge pressure assumes sea level. Version {VERSION},
published {long_date(PUBLISHED)}. Corrections are listed in the <a href="{REL}changelog.html">changelog</a>.
Found a wrong cell? <a href="{b.error_mailto(url(b, PATH), "Refrigerant PT data")}">Send the refrigerant, the temperature and the source you compared with</a>.</p></section>
{related("Uses this data", [("hvac/pt-chart/index.html", "PT charts"), ("hvac/superheat-subcooling-calculator.html", "Superheat & subcooling calculator"),
                            ("hvac/compare/index.html", "Refrigerant comparisons"), ("methodology.html", "Methodology and sources")])}
"""
    ld = {"@context": "https://schema.org", "@type": "Dataset", "@id": url(b, PATH) + "#dataset", "name": NAME, "description": desc,
          "url": url(b, PATH), "version": VERSION, "datePublished": PUBLISHED, "dateModified": b.LASTMOD_TOKEN,
          "license": LICENSE_URL, "isAccessibleForFree": True, "inLanguage": "en",
          "creator": person(b), "publisher": {"@id": b.ORG_ID},
          "keywords": ["refrigerant", "pressure-temperature chart", "saturation pressure", "bubble point", "dew point", "HVAC",
                       "R-454B", "R-32", "R-410A", "R-134a"],
          "citation": cite,
          "isBasedOn": [SOURCES[s][2] for s in used],
          "variableMeasured": [{"@type": "PropertyValue", "name": name, **({"unitText": unit} if unit else {}), "description": d}
                               for name, unit, d in COLUMNS],
          "distribution": [
              {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{b.BASE}/{CSV_PATH}"},
              {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{b.BASE}/{JSON_PATH}"}]}
    ld.update(opendata.doi_props("refrigerant-pt"))
    b.shell(PATH, "Refrigerant PT Chart Data: CSV and JSON, 22 Refrigerants (CC BY)", desc, body, "t-hvac", None, [ld])
