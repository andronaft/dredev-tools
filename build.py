#!/usr/bin/env python3
"""Builds the static marketing site into ./docs (served by GitHub Pages from main:/docs).

Data comes straight from the app repos next to this folder (PT charts from hvac-charge-app, screenshots and icons
from fastlane), so the site never drifts from the apps. Store links live in config.json: fill them in and rebuild.

    python3 build.py
"""

import html
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # ~/Desktop/mobile_sub_app
OUT = HERE / "docs"  # GitHub Pages serves main:/docs
CFG = json.loads((HERE / "config.json").read_text())
BASE = CFG["base_url"].rstrip("/")
TODAY = date.today().isoformat()
FREE_REFRIGERANTS = ["R-410A", "R-454B", "R-32", "R-22"]  # same free set as hvac-charge-app AppConfig

e = html.escape
pages: list[str] = []


# ---------- data ----------

def load_pt():
    engine = ROOT / "hvac-charge-app/lib/feature/engine"
    sources = dict(re.findall(r"(\w+)\(\s*'([^']+)',\s*'[^']+',?\s*\)", (engine / "pt.dart").read_text()))
    out = {}
    for block in re.split(r"\nconst \w+ = Refrigerant\(", (engine / "pt_data.dart").read_text())[1:]:
        def field(name):
            m = re.search(rf"{name}: '([^']*)'", block)
            return m.group(1) if m else ""

        def curve(name):
            # Tolerates both one-line and dart-format multi-line literals (trailing commas included).
            m = re.search(rf"{name}: PtCurve\(\s*startF: (-?\d+),\s*psig: \[([^\]]+)\]", block)
            return None if not m else {"startF": int(m.group(1)), "psig": [float(x) for x in m.group(2).split(",") if x.strip()]}

        src = re.search(r"source: PtSource\.(\w+)", block).group(1)
        rid = field("id")
        out[rid] = {
            "id": rid,
            "safety": field("safety"),
            "use": field("use"),
            "source": sources.get(src, src),
            "bubble": curve("bubble"),
            "dew": curve("dew"),
        }
    return out


PT = load_pt()


def slug(rid):
    return rid.lower()


# ---------- images ----------

def image(src_candidates, dest_name, width):
    """Copies the first existing image, resized to [width] px, into public/img. Returns the relative path or None."""
    for c in src_candidates:
        p = ROOT / c
        if p.exists():
            dest = OUT / "img" / dest_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", "--resampleWidth", str(width), str(p), "--out", str(dest)],
                check=True, capture_output=True,
            )
            return f"img/{dest_name}"
    return None


# ---------- app copy ----------

APPS = {
    "hvac-charge": {
        "theme": "t-hvac",
        "tagline": "Superheat, subcooling and PT charts for R-454B, R-32, R-410A and more. Offline, no account.",
        "intro": "Built for service techs on the roof, not in the office. Enter gauge pressure and line temperature; "
                 "saturation, superheat and subcooling update as you type, from published manufacturer PT charts.",
        "free": ["Superheat and subcooling with R-410A, R-454B, R-32 and R-22", "Pressure ↔ temperature lookup with bubble and dew points",
                 "Works offline, no login, no ads"],
        "pro": ["All 16 refrigerants: R-404A, R-134a, R-407C, R-448A, R-449A, R-513A and more",
                "Target superheat for fixed-orifice (piston) systems from the manufacturer charging table",
                "Clear add / recover call against the target", "Saved readings with notes to share with the office or customer"],
        "calc": ("hvac/superheat-subcooling-calculator.html", "Superheat & subcooling calculator"),
        "icons": ["hvac-charge-app/fastlane/metadata/android/en-US/images/icon.png", "hvac-charge-app/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png"],
        "shots": "hvac-charge-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "UtilitiesApplication",
    },
    "electrician-calc": {
        "theme": "t-elec",
        "tagline": "Wire size, voltage drop, panel planner and 21 electrical calculators. NEC and IEC 60364.",
        "intro": "Real ampacity tables, correction factors and protection checks with every step shown. "
                 "NEC (AWG, feet) or IEC 60364 (mm², metres), picked from your region and switched with one tap.",
        "free": ["Cable size with ampacity, derating and voltage-drop check", "Voltage drop: volts, %, end voltage, minimum size",
                 "Power and Ohm's law for DC, single and three phase"],
        "pro": ["Panel planner: circuits to breakers, cables and RCD groups", "Motor circuits, fault level, load schedule, PF correction",
                "Earth fault loop, earthing conductors and electrodes", "Solar PV strings, battery and backup power sizing",
                "Unlimited projects with PDF reports"],
        "calc": ("electrical/voltage-drop-calculator.html", "Voltage drop calculator"),
        "icons": ["Calculator_for_electrical/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "Calculator_for_electrical/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "UtilitiesApplication",
    },
    "coatcalc": {
        "theme": "t-coat",
        "tagline": "Epoxy and polyaspartic floor calculator: kits, flake, dew point and PDF quotes.",
        "intro": "For garage-floor and concrete-coating installers. Order the right number of kits, check if you can coat today, "
                 "and send a professional quote before you leave the driveway.",
        "free": ["Coverage: gallons and kits from area, mils, solids and waste, with a save-a-kit tip", "Flake pounds and bags",
                 "Dew point: can I coat today?", "Job estimate with materials and cost"],
        "pro": ["Crack and joint filler, cove and stem wall, partial-kit A:B mixer", "Pot life and recoat times adjusted for temperature",
                "PDF quotes, saved jobs and a supplier order list", "Client price on every estimate"],
        "calc": ("coating/epoxy-coverage-calculator.html", "Epoxy coverage calculator"),
        "icons": ["coatcalc-app/fastlane/metadata/android/en-US/images/icon.png", "coatcalc-app/docs/app_icon_1024.png"],
        "shots": "coatcalc-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "BusinessApplication",
    },
}


def prep_images():
    for key, a in APPS.items():
        a["icon"] = image(a["icons"], f"{key}-icon.jpg", 192)
        d = ROOT / a["shots"]
        files = sorted(d.glob("*.png"))[:6] if d.exists() else []
        a["screens"] = [image([str(f.relative_to(ROOT))], f"{key}-{i + 1}.jpg", 440) for i, f in enumerate(files)]


# ---------- page shell ----------

def shell(path, title, desc, body, theme="", calc=None, jsonld=None, scripts=""):
    depth = path.count("/")
    rel = "../" * depth
    canonical = f"{BASE}/{path}".replace("/index.html", "/")
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    calc_attr = f' data-calc="{calc}"' if calc else ""
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta name="theme-color" content="#0e1116" media="(prefers-color-scheme: dark)">
<link rel="stylesheet" href="{rel}assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%23f59e0b'/%3E%3Cstop offset='1' stop-color='%23ef4444'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='32' height='32' rx='8' fill='url(%23g)'/%3E%3C/svg%3E">
{ld}
</head>
<body class="{theme}"{calc_attr}>
<header class="top"><div class="wrap">
<a class="brand" href="{rel}index.html"><i></i>{e(CFG["brand"])} Tools</a>
<nav>
<a href="{rel}hvac/superheat-subcooling-calculator.html">HVAC</a>
<a href="{rel}electrical/voltage-drop-calculator.html">Electrical</a>
<a href="{rel}coating/epoxy-coverage-calculator.html" class="hide-sm">Coatings</a>
<a href="{rel}index.html#apps">Apps</a>
</nav>
</div></header>
<main class="wrap">
{body.replace("{rel}", rel)}
</main>
<footer><div class="wrap">
<span>© 2026 {e(CFG["brand"])}. Free tools for the trades. No account, no tracking cookies.</span>
<span><a href="mailto:{CFG["support_email"]}">{CFG["support_email"]}</a></span>
</div></footer>
{scripts.replace("{rel}", rel)}
</body>
</html>
"""
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc)
    pages.append(canonical)


# ---------- shared blocks ----------

def store_buttons(key, source):
    c = CFG["apps"][key]
    btns = []
    play = f"https://play.google.com/store/apps/details?id={c['package']}&referrer=utm_source%3Ddredev-tools%26utm_campaign%3D{source}"
    if c["app_store_url"]:
        btns.append(f'<a class="btn" href="{c["app_store_url"]}">Download on the App Store</a>')
    if c["google_play_live"]:
        btns.append(f'<a class="btn" href="{play}">Get it on Google Play</a>')
    if not btns:
        if c["beta_group_url"]:
            btns.append(f'<a class="btn" href="{c["beta_group_url"]}">Join the free Android beta</a>')
        else:
            subject = f"Beta: {c['short']}"
            btns.append(f'<a class="btn" href="mailto:{CFG["support_email"]}?subject={subject.replace(" ", "%20")}">Get early access</a>')
        btns.append('<span class="btn off">App Store &amp; Google Play: coming soon</span>')
    return f'<div class="btns">{"".join(btns)}</div>'


def promo(key, source, pitch):
    a, c = APPS[key], CFG["apps"][key]
    icon = f'<img class="icon" src="{{rel}}{a["icon"]}" alt="" width="72" height="72">' if a["icon"] else ""
    return f"""<section class="promo">{icon}<div>
<h3>{e(c["name"])}</h3>
<p>{e(pitch)} <a href="{{rel}}apps/{key}.html">See what's inside</a>.</p>
{store_buttons(key, source)}
</div></section>"""


def faq(items):
    blocks = "".join(f"<details><summary>{e(q)}</summary><p>{a}</p></details>" for q, a in items)
    ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in items],
    }
    return f'<section class="faq"><h2>Questions</h2>{blocks}</section>', ld


def webapp_ld(name, path, desc):
    return {"@context": "https://schema.org", "@type": "WebApplication", "name": name, "url": f"{BASE}/{path}",
            "description": desc, "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}


# ---------- HVAC ----------

def fmt_cell(p):
    return f'<td class="vac">{abs(p):.1f}″ Hg</td>' if p < 0 else f"<td>{p:.1f}</td>"


def pt_table(r):
    b, d = r["bubble"], r["dew"]
    start = max(b["startF"], d["startF"]) if d else b["startF"]
    end = min(b["startF"] + 5 * (len(b["psig"]) - 1), d["startF"] + 5 * (len(d["psig"]) - 1)) if d else b["startF"] + 5 * (len(b["psig"]) - 1)
    head = "<th>°F</th><th>°C</th>" + ("<th>Liquid (bubble), psig</th><th>Vapor (dew), psig</th>" if d else "<th>Pressure, psig</th>")
    rows = []
    for t in range(start, end + 1, 5):
        cells = fmt_cell(b["psig"][(t - b["startF"]) // 5])
        if d:
            cells += fmt_cell(d["psig"][(t - d["startF"]) // 5])
        rows.append(f"<tr><td>{t}</td><td>{(t - 32) * 5 / 9:.1f}</td>{cells}</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def chips(current=None):
    links = "".join(
        f'<a href="{{rel}}hvac/pt-chart/{slug(rid)}.html"{" aria-current=page" if rid == current else ""}>{rid}</a>' for rid in PT
    )
    return f'<div class="chips">{links}</div>'


def build_hvac():
    path = "hvac/superheat-subcooling-calculator.html"
    options = "".join(f'<option value="{rid}">{rid}{" (glide)" if PT[rid]["dew"] else ""}</option>' for rid in FREE_REFRIGERANTS)
    faq_html, faq_ld = faq([
        ("How do you calculate superheat?",
         "Read the suction (low-side) pressure and convert it to the saturation temperature with the refrigerant's PT chart. "
         "Measure the suction line temperature near the service valve. Superheat = suction line temperature − saturation temperature. "
         "For blends with glide such as R-454B or R-407C, use the <b>dew point</b> (vapor) column."),
        ("How do you calculate subcooling?",
         "Read the liquid (high-side) pressure and convert it to the saturation temperature. Measure the liquid line temperature near the "
         "service valve. Subcooling = saturation temperature − liquid line temperature. For blends with glide, use the <b>bubble point</b> (liquid) column."),
        ("Should I charge by superheat or subcooling?",
         "Fixed-orifice (piston) systems are charged by superheat against a target from the outdoor and indoor conditions. TXV and EEV systems "
         "are charged by subcooling against the target on the outdoor unit's nameplate or the manufacturer's charging chart. Always follow the "
         "manufacturer's instructions for the specific unit."),
        ("Is R-454B a drop-in for R-410A?",
         "No. R-454B is an A2L (mildly flammable) refrigerant for equipment designed for it, with its own pressures, glide and safety requirements. "
         "Use the R-454B chart, not the R-410A one, and follow the A2L handling rules."),
        ("Where does this PT data come from?",
         "From the published Arkema Forane® pressure–temperature charts (NIST REFPROP data). Between the printed 5 °F points the calculator "
         "interpolates along the vapor-pressure curve. It is a reference tool: verify against the equipment manufacturer's data."),
    ])
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › HVAC</div>
<div class="hero"><div class="eyebrow">Free HVAC tool</div>
<h1>Superheat &amp; Subcooling Calculator</h1>
<p class="lead">Enter gauge pressure and line temperature. Get saturation, superheat or subcooling instantly for R-410A, R-454B, R-32 and R-22, from published PT charts.</p></div>

<div class="calc card">
<div class="fields">
<div class="full"><div class="seg" id="mode" role="group" aria-label="Measurement">
<button data-v="sh" aria-pressed="true">Superheat</button><button data-v="sc" aria-pressed="false">Subcooling</button></div></div>
<div class="full"><label for="ref">Refrigerant</label><select id="ref">{options}</select></div>
<div><label for="p" id="p-label">Suction pressure <small>(psig)</small></label><input id="p" inputmode="decimal" value="130"></div>
<div><label for="t" id="t-label">Suction line temp <small>(°F)</small></label><input id="t" inputmode="decimal" value="55"></div>
</div>
<div class="result" aria-live="polite">
<div id="out-title" class="eyebrow">Superheat</div>
<div class="big" id="out">–</div>
<div class="rows"><div><span>In kelvin</span><span id="out-c"></span></div>
<div><span id="sat-label">Saturation temp</span><span id="sat">–</span></div></div>
<div id="hvac-warn" class="verdict"></div>
</div>
</div>

<section class="calc card" style="margin-top:20px">
<div class="fields">
<div class="full"><h2 style="margin:0">PT lookup</h2></div>
<div class="full"><div class="seg" id="ptmode" role="group" aria-label="Lookup direction">
<button data-v="p2t" aria-pressed="true">Pressure → temp</button><button data-v="t2p" aria-pressed="false">Temp → pressure</button></div></div>
<div class="full"><label for="pt-in" id="pt-in-label">Pressure <small>(psig)</small></label><input id="pt-in" inputmode="decimal" value="120"></div>
</div>
<div class="result"><div class="eyebrow">Saturation</div><div class="rows" id="pt-out"></div></div>
</section>

{promo("hvac-charge", "hvac-calc", "Same numbers on your phone, offline on the roof, plus 16 refrigerants, piston target superheat and an add/recover call.")}

<section><h2>PT charts</h2><p class="muted">Full pressure–temperature tables, −50 °F to 150 °F.</p>{chips()}</section>
{faq_html}
<p class="note">Reference only. Verify against the equipment manufacturer's charging instructions. Handling refrigerants requires EPA Section 608 certification in the US.</p>
"""
    shell(path, "Superheat & Subcooling Calculator (R-454B, R-32, R-410A) | Free",
          "Free superheat and subcooling calculator with PT lookup for R-454B, R-32, R-410A and R-22. Bubble and dew points from published PT charts.",
          body, "t-hvac", "hvac",
          [webapp_ld("Superheat & Subcooling Calculator", path, "Superheat, subcooling and PT lookup for common refrigerants."), faq_ld],
          '<script src="{rel}assets/pt-data.js"></script><script src="{rel}assets/calc.js"></script>')

    for rid, r in PT.items():
        p = f"hvac/pt-chart/{slug(rid)}.html"
        glide = (f"<p>{rid} is a zeotropic blend with temperature glide, so the chart has two columns: use the <b>vapor (dew)</b> column "
                 "for superheat and the <b>liquid (bubble)</b> column for subcooling.</p>") if r["dew"] else ""
        a2l = " It is an A2L (mildly flammable) refrigerant: follow A2L handling and equipment rules." if r["safety"] == "A2L" else ""
        in_calc = rid in FREE_REFRIGERANTS
        cta = (f'<p><a class="btn" href="{{rel}}hvac/superheat-subcooling-calculator.html">Calculate superheat &amp; subcooling with {rid}</a></p>'
               if in_calc else "")
        body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › <a href="{{rel}}hvac/superheat-subcooling-calculator.html">HVAC</a> › PT charts</div>
<div class="hero"><div class="eyebrow">PT chart · ASHRAE {r["safety"]}</div>
<h1>{rid} PT Chart</h1>
<p class="lead">{rid} pressure–temperature chart in psig and °F/°C. {e(r["use"])}.{a2l}</p></div>
<div class="prose">{glide}<p>Vacuum readings are shown in inches of mercury (″ Hg) below atmospheric pressure.</p></div>
{cta}
{pt_table(r)}
<p class="note">Source: {e(r["source"])}. Reference only; verify against the equipment manufacturer's data.</p>
{promo("hvac-charge", "pt-" + slug(rid), f"Look up {rid} offline in the field and get superheat, subcooling and a charge call in seconds.")}
<section><h2>Other refrigerants</h2>{chips(rid)}</section>
"""
        shell(p, f"{rid} PT Chart: Pressure Temperature Chart (psig, °F, °C)",
              f"{rid} pressure-temperature chart from -50 °F to 150 °F in psig with °C.{' Bubble and dew columns for the glide.' if r['dew'] else ''} Free, printable.",
              body, "t-hvac")

    index_rows = "".join(
        f'<a class="card" href="{{rel}}hvac/pt-chart/{slug(rid)}.html"><span class="tag">{r["safety"]}</span><h3>{rid} PT chart</h3><p>{e(r["use"])}</p></a>'
        for rid, r in PT.items())
    shell("hvac/pt-chart/index.html", "Refrigerant PT Charts: R-454B, R-32, R-410A, R-22 and more",
          "Free pressure-temperature charts for 16 refrigerants, including the new A2L refrigerants R-454B and R-32.",
          f'<div class="hero"><h1>Refrigerant PT charts</h1><p class="lead">Pressure–temperature tables for 16 refrigerants.</p></div><div class="grid">{index_rows}</div>',
          "t-hvac")


# ---------- Electrical ----------

def build_vd():
    path = "electrical/voltage-drop-calculator.html"
    faq_html, faq_ld = faq([
        ("What is the voltage drop formula?",
         "For copper under the NEC, VD = 2 × K × I × L / CM for single phase and 1.732 × K × I × L / CM for three phase, with K ≈ 12.9 Ω·cmil/ft, "
         "I the load current, L the one-way length in feet and CM the conductor area in circular mils. This calculator uses the equivalent "
         "IEC 60364-5-52 Annex G method with conductor reactance, which matches the K-factor result within about 0.5 % at unity power factor."),
        ("What voltage drop is acceptable?",
         "The NEC informational notes recommend no more than 3 % on a branch circuit and 5 % for feeder plus branch combined. "
         "IEC 60364-5-52 suggests 3 % for lighting and 5 % for other uses on installations supplied from the public network."),
        ("Is the length one way or round trip?",
         "Enter the one-way length from the panel to the load. The formula already counts both conductors (or the three phases)."),
        ("Why does power factor matter?",
         "On AC circuits the drop depends on resistance and reactance. With motor loads (power factor below 1) the reactive part grows, "
         "which matters most on large conductors."),
    ])
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › Electrical</div>
<div class="hero"><div class="eyebrow">Free electrical tool</div>
<h1>Voltage Drop Calculator</h1>
<p class="lead">Voltage drop in volts and percent, the voltage at the load and the smallest wire that stays under 3 %. NEC (AWG) or IEC (mm²), copper or aluminum.</p></div>

<div class="calc card">
<div class="fields">
<div class="full"><div class="seg" id="std" role="group" aria-label="Standard">
<button data-v="nec" aria-pressed="true">NEC · AWG · ft</button><button data-v="iec" aria-pressed="false">IEC · mm² · m</button></div></div>
<div class="full"><div class="seg" id="supply" role="group" aria-label="Supply">
<button data-v="single" aria-pressed="true">1-phase</button><button data-v="three" aria-pressed="false">3-phase</button><button data-v="dc" aria-pressed="false">DC</button></div></div>
<div class="full"><div class="seg" id="cond" role="group" aria-label="Conductor">
<button data-v="cu" aria-pressed="true">Copper</button><button data-v="al" aria-pressed="false">Aluminum</button></div></div>
<div><label for="size">Wire size</label><select id="size"></select></div>
<div><label for="len">Length <small id="len-unit">(ft, one way)</small></label><input id="len" inputmode="decimal"></div>
<div><label for="amps">Load <small>(A)</small></label><input id="amps" inputmode="decimal" value="16"></div>
<div><label for="volts">Voltage <small>(V)</small></label><input id="volts" inputmode="decimal"></div>
<div class="full"><label for="pf">Power factor <small>(1 for resistive loads, ~0.85 for motors)</small></label><input id="pf" inputmode="decimal" value="1"></div>
</div>
<div class="result" aria-live="polite">
<div class="eyebrow">Voltage drop</div>
<div class="big" id="vd-pct">–</div>
<div class="rows">
<div><span>Drop</span><span id="vd-v">–</span></div>
<div><span>Voltage at load</span><span id="vd-end">–</span></div>
<div><span>Smallest size for ≤ 3 %</span><span id="vd-min">–</span></div>
</div>
<div id="vd-verdict" class="verdict"></div>
<p class="note">Checks voltage drop only. Size the wire for ampacity and overcurrent protection too.</p>
</div>
</div>

{promo("electrician-calc", "vd-calc", "Wire size with ampacity and derating, panel planner, motors, solar and 21 calculators with step-by-step working and PDF reports.")}
{faq_html}
"""
    shell(path, "Voltage Drop Calculator (NEC & IEC) | AWG and mm², Free",
          "Free voltage drop calculator for AWG and mm² wire, copper or aluminum, single phase, three phase and DC. Shows % drop, load voltage and the minimum wire size.",
          body, "t-elec", "vd",
          [webapp_ld("Voltage Drop Calculator", path, "Voltage drop for NEC and IEC wire sizes."), faq_ld],
          '<script src="{rel}assets/calc.js"></script>')


# ---------- Coatings ----------

def build_coat():
    path = "coating/epoxy-coverage-calculator.html"
    faq_html, faq_ld = faq([
        ("How much epoxy do I need per square foot?",
         "One US gallon spread 1 mil thick covers 1,604 sq ft. Divide by the thickness in mils and multiply by the solids by volume: "
         "a 100 % solids epoxy at 10 mils covers about 160 sq ft per gallon, a 50 % solids product at the same dry thickness covers half that."),
        ("What does solids by volume mean?",
         "It is the share of the liquid that stays on the floor after the solvent or water evaporates. You will find it on the product's "
         "technical data sheet (TDS). Thickness here is the dry film thickness (DFT)."),
        ("How much waste should I allow?",
         "Installers commonly add 5–15 % for porous concrete, the roller and the bucket. Profiled or very porous slabs take more."),
        ("How many kits should I order?",
         "Divide the gallons needed by the kit size and round up. The calculator also tells you when you are just over a kit boundary, "
         "so you can decide whether a little less waste or thickness saves one kit."),
    ])
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › Coatings</div>
<div class="hero"><div class="eyebrow">Free coatings tool</div>
<h1>Epoxy Floor Coverage Calculator</h1>
<p class="lead">How many gallons and kits of epoxy, polyaspartic or polyurea you need, from area, thickness in mils and solids by volume.</p></div>

<div class="calc card">
<div class="fields">
<div class="full"><div class="seg" id="unit" role="group" aria-label="Area unit">
<button data-v="ft2" aria-pressed="true">sq ft</button><button data-v="m2" aria-pressed="false">m²</button></div></div>
<div><label for="area">Floor area <small id="area-unit">(sq ft)</small></label><input id="area" inputmode="decimal" value="480"></div>
<div><label for="mils">Thickness <small>(mils DFT)</small></label><input id="mils" inputmode="decimal" value="10"></div>
<div><label for="solids">Solids by volume <small>(%)</small></label><input id="solids" inputmode="decimal" value="100"></div>
<div><label for="waste">Waste <small>(%)</small></label><input id="waste" inputmode="decimal" value="10"></div>
<div><label for="kit">Kit size <small>(gal)</small></label><input id="kit" inputmode="decimal" value="1.5"></div>
<div><label for="price">Kit price <small>($, optional)</small></label><input id="price" inputmode="decimal" placeholder="e.g. 189"></div>
</div>
<div class="result" aria-live="polite">
<div class="eyebrow">Material needed</div>
<div class="big" id="c-gal">–</div>
<div class="rows">
<div><span>In litres</span><span id="c-l">–</span></div>
<div><span>Kits to order</span><span id="c-kits">–</span></div>
<div><span>Spread rate</span><span id="c-rate">–</span></div>
<div><span>Material cost</span><span id="c-cost">–</span></div>
</div>
<div id="c-tip" class="verdict"></div>
</div>
</div>

{promo("coatcalc", "coat-calc", "Flake, crack filler, cove base, dew point and pot life, then a PDF quote with your client price in one tap.")}
{faq_html}
"""
    shell(path, "Epoxy Floor Coverage Calculator: Gallons & Kits | Free",
          "Free epoxy coverage calculator: gallons and kits from square feet, mils and solids by volume, with waste. For epoxy, polyaspartic and polyurea floors.",
          body, "t-coat", "coat",
          [webapp_ld("Epoxy Floor Coverage Calculator", path, "Gallons and kits of floor coating from area, mils and solids."), faq_ld],
          '<script src="{rel}assets/calc.js"></script>')


# ---------- App pages ----------

def build_apps():
    for key, a in APPS.items():
        c = CFG["apps"][key]
        path = f"apps/{key}.html"
        icon = f'<img class="appicon" src="{{rel}}{a["icon"]}" alt="{e(c["short"])} icon" width="72" height="72">' if a["icon"] else ""
        shots = "".join(f'<img src="{{rel}}{s}" alt="{e(c["short"])} screenshot {i + 1}" loading="lazy" width="220">' for i, s in enumerate(a["screens"]))
        policy = f'{CFG["policy_base"]}/{key}'
        ld = {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": c["name"], "operatingSystem": "iOS, Android",
              "applicationCategory": a["category"], "description": a["tagline"], "url": f"{BASE}/{path}",
              "publisher": {"@type": "Organization", "name": CFG["brand"]}, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
        body = f"""
<div class="hero">{icon}
<h1 style="margin-top:14px">{e(c["name"])}</h1>
<p class="lead">{e(a["tagline"])}</p>
<div style="margin-top:20px">{store_buttons(key, "app-page")}</div></div>
{f'<section class="shots">{shots}</section>' if shots else ""}
<section class="prose"><p>{e(a["intro"])}</p></section>
<section class="grid">
<div class="card"><span class="tag">Free</span><ul class="ticks">{"".join(f"<li>{e(x)}</li>" for x in a["free"])}</ul></div>
<div class="card"><span class="tag">Pro</span><ul class="ticks">{"".join(f"<li>{e(x)}</li>" for x in a["pro"])}</ul></div>
</section>
<section><h2>Try it in your browser</h2><p><a class="btn ghost" href="{{rel}}{a["calc"][0]}">{a["calc"][1]} →</a></p></section>
<p class="note">No account. Your data stays on your device. <a href="{policy}/privacy.html">Privacy</a> · <a href="{policy}/terms.html">Terms</a> · <a href="mailto:{CFG["support_email"]}">Support</a></p>
"""
        shell(path, f"{c['name']} — app for iPhone and Android", a["tagline"], body, a["theme"], jsonld=[ld])


# ---------- Home ----------

def build_home():
    calcs = [
        ("hvac/superheat-subcooling-calculator.html", "HVAC", "Superheat & subcooling calculator", "R-454B, R-32, R-410A, R-22 with PT lookup.", "t-hvac"),
        ("hvac/pt-chart/index.html", "HVAC", "Refrigerant PT charts", "16 refrigerants, bubble and dew columns.", "t-hvac"),
        ("electrical/voltage-drop-calculator.html", "Electrical", "Voltage drop calculator", "AWG or mm², copper or aluminum, minimum size for 3 %.", "t-elec"),
        ("coating/epoxy-coverage-calculator.html", "Coatings", "Epoxy coverage calculator", "Gallons and kits from area, mils and solids.", "t-coat"),
    ]
    calc_cards = "".join(f'<a class="card {t}" href="{{rel}}{p}"><span class="tag">{tag}</span><h3>{e(h)}</h3><p>{e(d)}</p></a>' for p, tag, h, d, t in calcs)
    app_cards = "".join(
        f'<a class="card {a["theme"]}" href="{{rel}}apps/{k}.html">'
        + (f'<img class="appicon" src="{{rel}}{a["icon"]}" alt="" width="56" height="56" style="width:56px;height:56px;border-radius:14px;margin-bottom:10px">' if a["icon"] else "")
        + f'<h3>{e(CFG["apps"][k]["name"])}</h3><p>{e(a["tagline"])}</p></a>'
        for k, a in APPS.items())
    body = f"""
<div class="hero"><div class="eyebrow">{e(CFG["brand"])} Tools</div>
<h1>Field calculators for the trades</h1>
<p class="lead">Free, fast tools for HVAC techs, electricians and coating installers. Every number comes from published tables, and every tool has a phone app that works offline.</p></div>
<section><h2>Free calculators</h2><div class="grid">{calc_cards}</div></section>
<section id="apps"><h2>Apps</h2><div class="grid">{app_cards}</div></section>
<section class="prose"><h2>Why these tools</h2>
<p>No account, no ads, no data leaving your phone. Built by an independent developer who answers every email: <a href="mailto:{CFG["support_email"]}">{CFG["support_email"]}</a>.</p></section>
"""
    shell("index.html", f"{CFG['brand']} Tools: free calculators for HVAC, electrical and floor coating",
          "Free online calculators for the trades: superheat and subcooling, refrigerant PT charts, voltage drop and epoxy coverage, plus offline phone apps.",
          body)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(HERE / "assets", OUT / "assets")
    free = {rid: PT[rid] for rid in FREE_REFRIGERANTS}
    (OUT / "assets/pt-data.js").write_text(f"window.PT_DATA = {json.dumps(free, separators=(',', ':'))};\n")
    prep_images()
    build_home()
    build_hvac()
    build_vd()
    build_coat()
    build_apps()
    (OUT / "404.html").write_text((OUT / "index.html").read_text())
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    urls = "".join(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    print(f"{len(pages)} pages, {len(PT)} PT charts -> {OUT}")


if __name__ == "__main__":
    main()
