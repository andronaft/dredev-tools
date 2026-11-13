"""Trust pages of the calculator site: methodology and sources, checked examples, changelog.

build.py calls trust.build() after the calculator pages exist, because the checked examples are run through the
real assets/calc.js (tools/verify.mjs, needs node) against the built pages. A case outside its tolerance stops
the build, so the site never publishes a calculator that disagrees with its own source rows.

Facts here come from the app repos' docs/SOURCES.md files and from the code; dates are the days the sources were read.
"""
import json
import subprocess
from datetime import date

import guides

# (date, kind, text). Newest first. "Correction" marks a wrong number or a broken calculator that was fixed.
CHANGES = [
    ("2026-11-13", "New", "The superheat and subcooling calculator now covers all 22 refrigerants, and a link can open it "
     "on one of them (the PT chart pages do). R-410A, R-454B, R-32, R-22, R-134a and R-404A have a page of their own with "
     "worked examples and typical pressures."),
    ("2026-11-13", "New", "PT chart pages show pressures at common temperatures, safety class, GWP and lubricant with "
     "their sources, and print cleanly. New: refrigerant comparisons, a target superheat calculator for fixed-orifice "
     "systems, guides on bubble and dew points and on charging R-454B by subcooling, an NEC 310.16 ampacity chart, wire "
     "size by distance and voltage drop references."),
    ("2026-11-12", "Correction", "Lye calculator: the oil list and the SAP table were empty from 9 November 2026, "
     "so the page could not calculate anything. Fixed; the build now stops if the oil list is incomplete."),
    ("2026-11-12", "New", "Methodology and sources, checked examples and this changelog. One shared disclaimer and a "
     "\"Found an error?\" link on every calculator page. The author line links to a page about who makes these tools."),
    ("2026-11-12", "New", "Calculator pages got a quick answer, a chart of common cases and a worked example, "
     "computed with the same formulas as the live calculator."),
    ("2026-11-09", "Change", "The site moved from andronaft.github.io/dredev-tools to zhukovskyi.space/calculators. "
     "Old addresses forward to the new ones."),
    ("2026-10-26", "New", "First version: superheat and subcooling calculator, 22 refrigerant PT charts, voltage drop, "
     "wire size, AWG to mm², epoxy coverage, pool chemicals, baker's percentages, lye calculator and a Christmas countdown."),
]

# (calculator, page, tables and editions, assumptions, limits). Other modules may append their own rows.
METHODS = [
    ("Superheat &amp; subcooling calculator and PT charts", "hvac/superheat-subcooling-calculator.html",
     ["Pressure&ndash;temperature rows as printed by the manufacturer, one row every 5 &deg;F. The source of each "
      "refrigerant is listed under the table below and on its chart page.",
      "Gauge pressure is turned into absolute pressure with the standard atmosphere, 14.696 psia. Between rows the "
      "calculator interpolates along the vapor-pressure curve: straight in ln(P) against 1/T.",
      "For blends with glide, superheat is read from the vapor (dew) column and subcooling from the liquid (bubble) column.",
      "Cross-checks done in the HVAC Charge app the data comes from: Arkema's R-454B columns agree with Chemours' "
      "1 &deg;F table for Opteon&trade; XL41 within 0.06 psi, and the interpolated values agree with CoolProp 8.0 "
      "(NIST reference equations)."],
     ["Sea-level atmospheric pressure. The calculator does not correct a gauge reading for altitude.",
      "Readings are taken at the service valves, as the questions on the page describe."],
     ["Answers only inside the printed range of the chart; outside it the page says so instead of extrapolating.",
      "It reports superheat or subcooling. It does not tell you the target for a unit: that comes from the "
      "manufacturer's charging instructions.",
      "Handling refrigerants requires EPA Section 608 certification in the US."]),
    ("Wire size calculator", "electrical/wire-size-calculator.html",
     ["NEC (NFPA 70) 2023, Table 310.16: ampacities of copper and aluminum conductors in the 60, 75 and 90 &deg;C "
      "columns, 14 AWG to 500 kcmil.",
      "NEC 240.4(D) for small conductors, 334.80 for NM-B cable (60 &deg;C column), 210.19(A)(1) and 215.2 for the "
      "125 % continuous-load rule.",
      "Standard breaker ratings from 15 A to 600 A. A conductor may sit on the next standard breaker size above "
      "its ampacity, as the code allows up to 800 A."],
     ["30 &deg;C ambient and no more than three current-carrying conductors: no temperature or bundling correction.",
      "The lower of the insulation column and the terminal rating you pick (60 or 75 &deg;C).",
      "The optional voltage drop check uses 3 % at full load and unity power factor."],
     ["No derating, no motor or HVAC nameplate rules, no parallel conductors, nothing above 500 kcmil or 600 A.",
      "Local amendments and the edition your jurisdiction has adopted may differ from NEC 2023.",
      "It sizes the ungrounded conductors only; grounding conductors, conduit fill and box fill are not checked."]),
    ("Voltage drop calculator", "electrical/voltage-drop-calculator.html",
     ["NEC sizes: conductor areas from NEC Chapter 9, Table 8, with resistivity at 20 &deg;C (copper 0.017241, aluminum "
      "0.028264 &Omega;&middot;mm&sup2;/m) raised by 25 % for operating temperature.",
      "IEC sizes: IEC 60364-5-52, Annex G, with &rho; = 0.0225 &Omega;&middot;mm&sup2;/m for copper and 0.036 for aluminum, "
      "and a reactance of 0.08 m&Omega;/m on AC.",
      "The 3 % and 5 % limits are the NEC informational notes and the IEC 60364-5-52 guidance; they are recommendations."],
     ["One-way length; the formula counts the return conductor (or the three phases).",
     "A balanced load and one conductor per phase."],
     ["It checks voltage drop only. Size the conductor for ampacity and overcurrent protection as well.",
      "The NEC-mode result runs about 0.5 % above the rounded K-factor formula (K = 12.9)."]),
    ("AWG to mm&sup2; converter", "electrical/awg-to-mm2.html",
     ["NEC Chapter 9, Table 8: areas in circular mils, converted with 1 cmil = 0.000506707 mm&sup2;.",
      "Metric sizes are the IEC 60228 series."],
     ["Area only."],
     ["An equal or larger area does not prove equal ampacity: insulation, installation method and the code in force decide that."]),
    ("Epoxy coverage calculator", "coating/epoxy-coverage-calculator.html",
     ["One US gallon is 231 cubic inches, so it covers 1,604 sq ft at 1 mil. Gallons = area &times; mils &divide; "
      "(1,604 &times; solids by volume) &times; (1 + waste)."],
     ["Thickness is the dry film thickness. Solids by volume comes from the product's technical data sheet.",
      "Kits are rounded up to whole kits."],
     ["Surface profile and porosity are covered only by the waste percentage you enter.",
      "It does not know a product's recoat window, pot life or minimum film thickness: read the data sheet."]),
    ("Pool chemical calculator", "pool/pool-chemical-calculator.html",
     ["Doses come from stoichiometry: ppm &times; litres = milligrams, converted by molar mass and label strength.",
      "Liquid chlorine by trade percent; bleach by weight percent with the density formula used by Trouble Free "
      "Pool's Pool Math; baking soda as 84.007 g of NaHCO<sub>3</sub> per 50.04 g of CaCO<sub>3</sub>.",
      "Cross-checked against Pool Math's classic calculator (read 25 October 2026)."],
     ["Stabilizer and salt are taken as 99 % pure.", "The pool volume you enter is right."],
     ["It only raises free chlorine, total alkalinity, stabilizer and salt. It does not handle pH, calcium or CSI; the PoolPro app does.",
      "Dichlor and cal-hypo also add stabilizer or calcium; the page says so but does not count them.",
      "Add in portions and retest. Never mix chlorine products with each other or with acid."]),
    ("Baker's percentage calculator", "bread/bakers-percentage-calculator.html",
     ["Baker's percentages as defined by King Arthur Baking and the total-formula method: every ingredient is a share of the flour weight.",
      "True hydration = (water + water in the starter) &divide; (flour + flour in the starter)."],
     ["The starter percentage is a share of the flour in the bowl, as home recipes write it."],
     ["Arithmetic on your own numbers. It ships no fermentation times, temperatures or nutrition data."]),
    ("Lye calculator", "soap/lye-calculator.html",
     ["Saponification (SAP) values from the SoapCalc oil list, snapshot of 25 October 2026, for 19 common oils.",
      "NaOH SAP = KOH SAP &times; 39.997 &divide; 56.106 (molar masses). Lye = &Sigma;(oil grams &times; SAP) &times; "
      "(1 &minus; superfat) &divide; purity. Water follows from the lye concentration.",
      "In the Lye Calc app the same values are checked against a second published table and against published recipes."],
     ["Sodium hydroxide only on this page; the app also does KOH and dual lye."],
     ["Oils vary between suppliers and harvests: treat the result as a starting point and run a new recipe through a second calculator.",
      "Lye is caustic: gloves, goggles, ventilation, and always add lye to water."]),
]


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B %Y}"


def run_cases(b):
    """Every case of verification.json through assets/calc.js. Returns {case id: result}."""
    try:
        out = subprocess.run(["node", str(b.HERE / "tools/verify.mjs"), str(b.OUT)], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("build.py needs node to run the checked examples (tools/verify.mjs)")
    if out.returncode:
        raise SystemExit(f"tools/verify.mjs failed:\n{out.stderr}")
    results = {r["id"]: r for r in json.loads(out.stdout)}
    bad = [f'{i}: got "{r["text"]}"' for i, r in results.items() if not r["ok"]]
    if bad:
        raise SystemExit("Checked examples outside their tolerance:\n  " + "\n  ".join(bad))
    return results


def ul(items):
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def methodology(b, spec, results):
    e = b.e
    by_source = {}
    for rid, r in b.PT.items():
        by_source.setdefault(r["source"], []).append(rid)
    pt_rows = "".join(f"<tr><td>{e(src)}</td><td>{', '.join(ids)}</td></tr>" for src, ids in by_source.items())
    sections = "".join(f"""
<section class="method"><h2><a href="{{rel}}{page}">{name}</a></h2>
<h3>Tables and formulas</h3>{ul(tables)}
<h3>Assumptions</h3>{ul(assume)}
<h3>Limits</h3>{ul(limits)}
</section>""" for name, page, tables, assume, limits in METHODS)
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › Methodology</div>
<div class="hero"><div class="eyebrow">How these tools are made</div>
<h1>Methodology and sources</h1>
<p class="lead">Which published tables and editions each calculator uses, what it assumes, and where it stops. If a number here is wrong, I want to know.</p></div>

<section class="prose"><h2>How the numbers are made and checked</h2>
<p>Every calculator on this site uses a published table or a formula that is named on its page and listed below. The browser calculators run the same formulas as the {e(b.CFG["brand"])} phone apps.</p>
<p>They are checked in two ways. Each app has its own tests against the published values. On this site, {len(spec["cases"])} <a href="{{rel}}verification.html">checked examples</a> put a row from a source next to the calculator's answer; they run through the calculator code every time the site is built, and the build stops if one is outside its tolerance.</p>
<p>The tools are made and checked by <a href="{b.ABOUT_URL}">{guides.AUTHOR}</a>, the developer. "Checked" means compared with the sources below. No outside trade professional has reviewed these pages yet. The sources were last read against the examples on {long_date(spec["checked"])}.</p>
<p>The code that builds the site, the formulas and the examples are public: <a href="https://github.com/andronaft/dredev-tools">github.com/andronaft/dredev-tools</a>.</p></section>

<section class="prose"><h2>Limits that apply to every tool</h2>
<p>{b.DISCLAIMER}</p>
<p>Found a wrong number? <a href="{b.error_mailto(f"{b.BASE}/methodology.html", "Methodology")}">Send it with the page, what you entered and the source you compared with</a>. Corrections are listed in the <a href="{{rel}}changelog.html">changelog</a>.</p></section>
{sections}
<section><h2>Sources of the refrigerant PT charts</h2>
<div class="tablewrap"><table class="wraps"><thead><tr><th>Source</th><th>Refrigerants</th></tr></thead><tbody>{pt_rows}</tbody></table></div>
<p class="note">Arkema and Bryant/Carrier documents were retrieved on 25 October 2026; Chemours Opteon&trade; YF and the NIST Chemistry WebBook on 26 October 2026.</p></section>
"""
    b.shell("methodology.html", "Methodology and sources of the Dre Dev calculators",
            "Which tables and editions the calculators use (NEC 2023, IEC 60364, Arkema PT charts, SoapCalc, Pool Math), "
            "what they assume, where they stop and how every number is checked.", body)


def verification(b, spec, results):
    e = b.e
    groups = {}
    for c in spec["cases"]:
        groups.setdefault(c["calc"], []).append(c)
    used = []
    blocks = ""
    for key, cases in groups.items():
        calc = spec["calculators"][key]
        rows = ""
        for c in cases:
            r = results[c["id"]]
            if c["source"] not in used:
                used.append(c["source"])
            ref = f'<sup>[{used.index(c["source"]) + 1}]</sup>'
            allowed = "exact match" if "expect_text" in c else (
                f'within {c["tolerance"]:g} {e(c["unit"])}' if c["tolerance"] else "exact match")
            note = f'<br><small>{e(c["note"])}</small>' if c.get("note") else ""
            rows += (f'<tr><td>{e(c["title"])}{note}</td><td>{e(c["source_says"])} {ref}</td>'
                     f'<td><b>{e(r["text"])}</b></td><td>{allowed}</td></tr>')
        blocks += f"""
<section><h2><a href="{{rel}}{calc["page"]}">{e(calc["name"])}</a></h2>
<div class="tablewrap"><table class="wraps"><thead><tr><th>Example</th><th>The source says</th><th>The calculator answers</th><th>Allowed difference</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>"""
    sources = "".join(f"<li>{e(spec['sources'][s])}</li>" for s in used)
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › <a href="{{rel}}methodology.html">Methodology</a> › Checked examples</div>
<div class="hero"><div class="eyebrow">Source row → calculator answer</div>
<h1>Checked examples</h1>
<p class="lead">{len(spec["cases"])} rows from the published sources, each next to what the calculator answers for the same input. The answers on this page are produced by the calculators' own code when the site is built.</p></div>
<section class="prose">
<p>If an answer falls outside the allowed difference, the build stops and nothing is published. Where the calculator and the source differ on purpose, the row says why. The sources were last read against these rows on {long_date(spec["checked"])}.</p>
<p>You can repeat any row yourself: open the calculator, enter the example and compare. The same list runs as an automated test in the <a href="https://github.com/andronaft/dredev-tools">public repository</a> (<code>verification.json</code>).</p></section>
{blocks}
<section class="prose"><h2>Sources</h2><ol>{sources}</ol></section>
"""
    b.shell("verification.html", "Checked examples: source rows next to the calculators' answers",
            f"{len(spec['cases'])} examples from NEC tables, manufacturer PT charts, Pool Math and SoapCalc, each next to the "
            "answer the Dre Dev calculator gives for the same input.", body)


def changelog(b):
    e = b.e
    rows = "".join(f'<tr><td>{long_date(d)}</td><td>{kind}</td><td>{e(text)}</td></tr>' for d, kind, text in CHANGES)
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › <a href="{{rel}}methodology.html">Methodology</a> › Changelog</div>
<div class="hero"><div class="eyebrow">What changed and when</div>
<h1>Changelog</h1>
<p class="lead">New calculators, changed formulas and corrected mistakes, newest first. A correction says what was wrong and for how long.</p></div>
<div class="tablewrap"><table class="wraps"><thead><tr><th>Date</th><th>Kind</th><th>What changed</th></tr></thead><tbody>{rows}</tbody></table></div>
<section class="prose"><p>Found something wrong? <a href="{b.error_mailto(f"{b.BASE}/changelog.html", "Changelog")}">Tell me</a>: the page, what you entered, what it showed and the source you compared with. Confirmed mistakes are fixed and listed here.</p></section>
"""
    b.shell("changelog.html", "Changelog of the Dre Dev calculators: new tools and corrections",
            "What changed on the Dre Dev calculator pages and when: new calculators, changed formulas and corrected mistakes.", body)


def build(b):
    spec = json.loads((b.HERE / "verification.json").read_text())
    results = run_cases(b)
    methodology(b, spec, results)
    verification(b, spec, results)
    changelog(b)
