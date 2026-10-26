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

ATM_PSIA = 14.695949
PSI_PER_INHG = 0.4911541
SAFETY_NOTES = {
    "A2L": " It is an A2L (mildly flammable) refrigerant: follow A2L handling and equipment rules.",
    "A3": " It is an A3 (highly flammable) refrigerant: only for equipment designed for it, with A3 handling rules.",
    "B2L": " It is a B2L refrigerant (toxic, mildly flammable): for trained industrial technicians only.",
}


def load_pt():
    engine = ROOT / "hvac-charge-app/lib/feature/engine"
    sources = dict(re.findall(r"(\w+)\(\s*'([^']+)',\s*'[^']+',?\s*\)", (engine / "pt.dart").read_text()))
    out = {}
    for block in re.split(r"\nconst \w+ = Refrigerant\(", (engine / "pt_data.dart").read_text())[1:]:
        def field(name):
            m = re.search(rf"{name}: '([^']*)'", block)
            return m.group(1) if m else ""

        def curve(name):
            # Tolerates one-line and dart-format literals, the old `psig:` and the current `cells:` field.
            # Absolute tables (psia) are converted to the printed gauge convention: psig, or negative inches of Hg.
            m = re.search(rf"{name}: PtCurve\(([^\]]+\])", block)
            if not m:
                return None
            body = m.group(1)
            start = int(re.search(r"startF: (-?\d+)", body).group(1))
            cells = [float(x) for x in re.search(r"(?:psig|cells): \[([^\]]+)\]", body).group(1).split(",") if x.strip()]
            if re.search(r"absolute: true", body):
                cells = [round(p - ATM_PSIA, 1) if p >= ATM_PSIA else round(-(ATM_PSIA - p) / PSI_PER_INHG, 1) for p in cells]
            return {"startF": start, "psig": cells, "converted": bool(re.search(r"absolute: true", body))}

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
        "pro": [f"All {len(PT)} refrigerants: R-404A, R-134a, R-407C, R-448A, R-1234yf, R-290, CO2 and more",
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
    "days-until": {
        "group": "everyday",
        "theme": "t-days",
        "tagline": "Countdown widgets for Christmas, trips, birthdays and weddings. Count up from any date, too.",
        "intro": "Add an event in seconds, pick an emoji and a theme, and keep the number of days right on your home screen. "
                 "Ready-made templates for Christmas, New Year, birthdays, trips and baby due dates.",
        "free": ["Countdown cards with a live timer down to the second", "Home screen widgets", "Count down or count up from any date",
                 "11 templates, including Christmas and New Year", "Notes and reminders for every event", "English, Ukrainian, Spanish, German and Portuguese"],
        "pro": ["Any event on any widget", "Your own photo as the background on cards and widgets", "6 premium themes",
                "Reminders 1 day, 1 week or 1 month before", "Milestones: 100, 500, 1000 days and every anniversary"],
        "calc": ("countdown/christmas-countdown.html", "Live Christmas countdown"),
        "icons": ["Countdown_to_events/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "Countdown_to_events/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "LifestyleApplication",
    },
    "focus-sprint": {
        "group": "everyday",
        "theme": "t-focus",
        "tagline": "An ADHD-friendly focus timer: tiny sprints, a kind buddy and a soft app shield. No guilt.",
        "intro": "Starting is the hard part, so Focus Sprint makes it tiny: tap \"Just 5 minutes\" and Spark, your focus buddy, keeps you company "
                 "until the timer ends. Ended early? You keep your XP. Got distracted? Spark says something kind and you try again.",
        "free": ["Sprints from \"Just 5 minutes\" to 50 minutes", "Energy check that suggests a sprint length", "Spark, a body-doubling buddy",
                 "Soft app shield and a parking lot for stray thoughts", "Forgiving streaks, XP, badges and quests", "Home screen widget, calm noise, breathing breaks"],
        "pro": ["Peak-hour insights: when your brain is sharpest", "Custom sprint lengths", "Unlimited apps on your shield"],
        "calc": None,
        "icons": ["adhd_neurodiversity/store/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "adhd_neurodiversity/store/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "ProductivityApplication",
        "privacy": "https://andronaft.github.io/focus-sprint-legal/privacy.html",
        "terms": "https://andronaft.github.io/focus-sprint-legal/terms.html",
        "note": "Focus Sprint is a productivity tool, not a medical device.",
    },
    "water-buddy": {
        "group": "everyday",
        "theme": "t-water",
        "tagline": "A cute water tracker: fill up Buddy, hit your daily goal, unlock outfits and keep your streak.",
        "intro": "Drinking enough water is easier with a friend. Buddy is a little water drop who fills up every time you drink and gets happier as you go. "
                 "Log a glass in one tap, hit your goal and celebrate with confetti.",
        "free": ["One-tap logging with a glass, a bottle or any amount", "Daily goal based on your weight and activity",
                 "Gentle reminders, only while you are awake", "Streaks, weekly chart, light and dark themes"],
        "pro": ["30-day history and insights", "Your own reminder schedule", "Custom cup sizes", "Every Buddy outfit, unlocked"],
        "calc": None,
        "icons": ["marketing/site/assets-src/water-buddy/icon.png"],
        "shots": "marketing/site/assets-src/water-buddy",
        "category": "HealthApplication",
        "privacy": "https://andronaft.github.io/app_politics_terms/water-buddy/privacy/",
        "terms": "https://andronaft.github.io/app_politics_terms/water-buddy/terms/",
    },
    "fastwise": {
        "group": "everyday",
        "theme": "t-fast",
        "tagline": "Intermittent fasting made simple: a plan that fits you, a live timer and help when hunger hits.",
        "intro": "Intermittent fasting is about when you eat, not what you eat. Fastwise shows how long you've fasted, what your body is likely "
                 "doing right now, and helps you through the hard moments.",
        "free": ["A short quiz picks your plan: 14:10, 16:8 and more", "One-tap timer with fasting phases", "\"I'm hungry\" tips and a what-can-I-drink guide",
                 "Streaks, weekly chart and weight log", "Home screen widget (Android)"],
        "pro": ["See which fast length makes you feel best", "Deeper progress and history"],
        "calc": None,
        "icons": ["fasting_tracker_app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "fasting_tracker_app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "HealthApplication",
        "note": "Fastwise does not give medical advice. Talk to your doctor before fasting if you have a health condition.",
    },
}


def prep_images():
    for key, a in APPS.items():
        a["icon"] = image(a["icons"], f"{key}-icon.jpg", 192)
        d = ROOT / a["shots"]
        files = sorted(f for f in d.glob("*") if f.suffix.lower() in (".png", ".jpg", ".jpeg") and f.stem != "icon")[:6] if d.exists() else []
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
<span>© 2026 {e(CFG["brand"])}. Free tools and offline apps. No account, no tracking cookies.</span>
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

{promo("hvac-charge", "hvac-calc", f"Same numbers on your phone, offline on the roof, plus {len(PT)} refrigerants, piston target superheat and an add/recover call.")}

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
        a2l = SAFETY_NOTES.get(r["safety"], "")
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
<p class="note">Source: {e(r["source"])}.{" Converted from absolute pressure (psia) to psig." if r["bubble"].get("converted") else ""} Reference only; verify against the equipment manufacturer's data.</p>
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
          f"Free pressure-temperature charts for {len(PT)} refrigerants, including the new A2L refrigerants R-454B and R-32.",
          f'<div class="hero"><h1>Refrigerant PT charts</h1><p class="lead">Pressure–temperature tables for {len(PT)} refrigerants.</p></div><div class="grid">{index_rows}</div>',
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


# ---------- More calculators: AWG, wire size, pool, bread, lye ----------

LYE_OILS = ["olive", "coconut76", "palm", "palm_kernel", "castor", "shea", "cocoa", "mango_butter", "lard", "tallow_beef",
            "almond", "avocado", "sunflower", "sunflower_ho", "rice_bran", "canola", "babassu", "soybean", "beeswax"]


def load_oils():
    """SAP values (g KOH per g oil) for common oils from Lye Calc's generated table (SoapCalc oil list, see its docs/SOURCES.md)."""
    src = (ROOT / "soapcalc-app/lib/feature/oil_data.dart").read_text()
    out = []
    for oid in LYE_OILS:
        m = re.search(rf"Oil\('{oid}', sapKoh: ([\d.]+).*?'en': '([^']+)'", src)
        if m:
            out.append({"id": oid, "sap": float(m.group(1)), "name": m.group(2)})
    return out


def calc_page(path, title, desc, crumb, eyebrow, h1, lead, form, result, faq_items, theme, calc, promo_html="", extra_scripts="", note=""):
    faq_html, faq_ld = faq(faq_items)
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › {crumb}</div>
<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{h1}</h1><p class="lead">{lead}</p></div>
<div class="calc card"><div class="fields">{form}</div><div class="result" aria-live="polite">{result}</div></div>
{note}
{promo_html}
{faq_html}
"""
    shell(path, title, desc, body, theme, calc, [webapp_ld(h1, path, desc), faq_ld], extra_scripts + '<script src="{rel}assets/calc.js"></script>')


def build_more():
    calc_page(
        "electrical/awg-to-mm2.html", "AWG to mm² Converter (and mm² to AWG) | Wire Size Chart",
        "Convert AWG and kcmil wire sizes to mm² and back, with circular mils and the next standard metric size. NEC Chapter 9 Table 8 areas.",
        "Electrical", "Free electrical tool", "AWG to mm² converter",
        "American wire gauge and kcmil to square millimetres and back, with the next standard IEC size.",
        """<div class="full"><label for="awg">Wire size (AWG / kcmil)</label><select id="awg"></select></div>
<div class="full"><label for="mm2">Or enter mm²</label><input id="mm2" inputmode="decimal" value="4"></div>""",
        """<div class="eyebrow">AWG → mm²</div><div class="big" id="awg-mm2">–</div>
<div class="rows"><div><span>Circular mils</span><span id="awg-cmil">–</span></div>
<div><span>Next standard metric size</span><span id="awg-iec">–</span></div>
<div><span>mm² → smallest AWG that is not smaller</span><span id="mm2-awg">–</span></div>
<div><span>mm² → closest AWG</span><span id="mm2-near">–</span></div></div>""",
        [("Is 2.5 mm² the same as 14 AWG?", "Close but not equal: 14 AWG is 2.08 mm² and 12 AWG is 3.31 mm². When you replace a metric cable with AWG wire, pick the size that is not smaller and check ampacity and voltage drop for your circuit."),
         ("Where do these numbers come from?", "Areas are from NEC Chapter 9, Table 8 (circular mils), converted with 1 cmil = 0.000506707 mm². Metric sizes are the IEC 60228 series.")],
        "t-elec", "awg",
        promo("electrician-calc", "awg", "Cable size with ampacity and derating, voltage drop and 21 calculators for NEC and IEC."))

    calc_page(
        "electrical/wire-size-calculator.html", "Wire Size Calculator (NEC 310.16) | What Size Wire Do I Need?",
        "Free NEC wire size calculator: breaker size, copper or aluminum conductor from Table 310.16 with 75 °C terminations, 125 % for continuous loads and an optional voltage drop check.",
        "Electrical", "Free electrical tool", "Wire size calculator (NEC)",
        "The smallest copper or aluminum conductor for your load and breaker, by NEC Table 310.16, with an optional 3 % voltage drop check.",
        """<div><label for="amps">Load <small>(A)</small></label><input id="amps" inputmode="decimal" value="24"></div>
<div><label for="wire">Wire type</label><select id="wire"><option value="nmb">NM-B (Romex)</option><option value="thhn" selected>THHN / THWN-2</option><option value="thwn">THW / THWN</option><option value="uf">UF-B</option></select></div>
<div class="full"><div class="seg" id="cond" role="group" aria-label="Conductor"><button data-v="cu" aria-pressed="true">Copper</button><button data-v="al" aria-pressed="false">Aluminum</button></div></div>
<div class="full"><label>Continuous load (3 h or more)?</label><div class="seg" id="cont" role="group" aria-label="Continuous load"><button data-v="no" aria-pressed="true">No</button><button data-v="yes" aria-pressed="false">Yes, ×125 %</button></div></div>
<div><label for="term">Terminal rating</label><select id="term"><option value="60">60 °C</option><option value="75" selected>75 °C</option></select></div>
<div><label for="phase">Supply</label><select id="phase"><option value="single">1-phase</option><option value="three">3-phase</option><option value="dc">DC</option></select></div>
<div><label for="len">Length <small>(ft, one way, optional)</small></label><input id="len" inputmode="decimal" placeholder="e.g. 80"></div>
<div><label for="volts">Voltage <small>(V)</small></label><input id="volts" inputmode="decimal" value="240"></div>""",
        """<div class="eyebrow">Wire size</div><div class="big" id="ws-size">–</div>
<div class="rows"><div><span>Breaker</span><span id="ws-ocpd">–</span></div>
<div><span>Design current</span><span id="ws-design">–</span></div>
<div><span>By ampacity</span><span id="ws-amp">–</span></div>
<div><span>Voltage drop (≤ 3 %)</span><span id="ws-drop">–</span></div></div>
<p class="note">Assumes 30 °C ambient and no more than 3 current-carrying conductors. Check local code, equipment ratings and derating.</p>""",
        [("What size wire for a 30 amp breaker?", "With copper THHN and 75 °C terminations, 10 AWG (35 A at 75 °C, and 240.4(D) limits 10 AWG copper to 30 A). Long runs may need a larger size for voltage drop."),
         ("Why 125 % for continuous loads?", "NEC 210.19(A)(1) and 215.2 require conductors for continuous loads (3 hours or more, like EV chargers and water heaters) to carry 125 % of the continuous current."),
         ("Why does NM-B use the 60 °C column?", "NEC 334.80 limits NM cable ampacity to the 60 °C column, even though the conductors are rated 90 °C.")],
        "t-elec", "wire",
        promo("electrician-calc", "wire-size", "Full cable sizing with ambient and grouping derating, IEC and NEC, step-by-step working and PDF reports."))

    calc_page(
        "pool/pool-chemical-calculator.html", "Pool Chemical Calculator: Chlorine, Baking Soda, Stabilizer, Salt",
        "Free pool chemical calculator: how much liquid chlorine, bleach, cal-hypo, baking soda, stabilizer (CYA) or salt to add for your pool volume.",
        "Pool", "Free pool tool", "Pool chemical calculator",
        "How much chlorine, baking soda, stabilizer or salt to add, from your pool's volume and your test results.",
        """<div class="full"><div class="seg" id="punit" role="group" aria-label="Volume unit"><button data-v="gal" aria-pressed="true">US gallons</button><button data-v="l" aria-pressed="false">Litres</button></div></div>
<div class="full"><label for="pvol">Pool volume</label><input id="pvol" inputmode="decimal" value="15000"></div>
<div class="full"><label for="pwhat">Raise</label><select id="pwhat"><option value="fc">Free chlorine (FC)</option><option value="ta">Total alkalinity (baking soda)</option><option value="cya">Stabilizer (CYA)</option><option value="salt">Salt (for salt systems)</option></select></div>
<div class="full" id="pprod-row"><label for="pprod">Chlorine product</label><select id="pprod"><option value="liquid10">Liquid chlorine 10 %</option><option value="liquid125">Liquid chlorine 12.5 %</option><option value="bleach6">Bleach 6 %</option><option value="bleach825">Bleach 8.25 %</option><option value="calhypo65">Cal-hypo 65 %</option><option value="dichlor">Dichlor 56 %</option></select></div>
<div><label for="pfrom">Current <small>(ppm)</small></label><input id="pfrom" inputmode="decimal" value="2"></div>
<div><label for="pto">Target <small>(ppm)</small></label><input id="pto" inputmode="decimal" value="5"></div>""",
        """<div class="eyebrow">Add</div><div class="big" id="p-amount">–</div>
<div class="rows"><div><span>Metric</span><span id="p-alt">–</span></div></div>
<p class="note">Add in portions and retest. Never mix chlorine products with each other or with acid. Dichlor and cal-hypo also add CYA and calcium.</p>""",
        [("How much liquid chlorine to raise FC by 1 ppm?", "About 12.8 fl oz of 10 % liquid chlorine per 10,000 US gallons. Bleach is weaker: 6 % bleach needs roughly 21 fl oz for the same rise."),
         ("What FC should I aim for?", "It depends on your stabilizer (CYA) level: the higher the CYA, the more free chlorine you need. PoolPro uses Trouble Free Pool's FC/CYA chart for targets."),
         ("Where does the math come from?", "Chlorine strength follows the same bleach density formula as TFP Pool Math; baking soda raises total alkalinity by 1 ppm per 1.68 mg per litre; stabilizer and salt are added at their label purity.")],
        "t-pool", "pool")

    calc_page(
        "bread/bakers-percentage-calculator.html", "Baker's Percentage Calculator for Sourdough (with True Hydration)",
        "Free sourdough calculator: flour, water, starter and salt from baker's percentages, by flour weight or total dough weight, with true hydration including the starter.",
        "Bread", "Free baking tool", "Baker's percentage calculator",
        "Grams of flour, water, starter and salt from your hydration and percentages, and the true hydration with the starter counted.",
        """<div class="full"><div class="seg" id="bmode" role="group" aria-label="Size by"><button data-v="flour" aria-pressed="true">By flour</button><button data-v="dough" aria-pressed="false">By dough weight</button></div></div>
<div class="full" id="b-flour-row"><label for="bflour">Flour <small>(g)</small></label><input id="bflour" inputmode="decimal" value="500"></div>
<div class="full" id="b-dough-row" hidden><label for="bdough">Total dough <small>(g)</small></label><input id="bdough" inputmode="decimal" value="900"></div>
<div><label for="bhyd">Hydration <small>(%)</small></label><input id="bhyd" inputmode="decimal" value="75"></div>
<div><label for="bst">Starter <small>(% of flour)</small></label><input id="bst" inputmode="decimal" value="20"></div>
<div><label for="bsth">Starter hydration <small>(%)</small></label><input id="bsth" inputmode="decimal" value="100"></div>
<div><label for="bsalt">Salt <small>(%)</small></label><input id="bsalt" inputmode="decimal" value="2"></div>
<div class="full"><label>Count the starter's flour and water?</label><div class="seg" id="bcount" role="group" aria-label="Count starter"><button data-v="no" aria-pressed="true">No</button><button data-v="yes" aria-pressed="false">Yes (true hydration)</button></div></div>""",
        """<div class="eyebrow">Weigh out</div><div class="big" id="b-flour">–</div>
<div class="rows"><div><span>Water</span><span id="b-water">–</span></div><div><span>Starter</span><span id="b-starter">–</span></div>
<div><span>Salt</span><span id="b-salt">–</span></div><div><span>Total dough</span><span id="b-total">–</span></div>
<div><span>True hydration (starter included)</span><span id="b-true">–</span></div></div>""",
        [("What are baker's percentages?", "Every ingredient is written as a percentage of the flour weight, with flour at 100 %. 500 g flour at 75 % hydration means 375 g water."),
         ("What is true hydration?", "The water from both the bowl and the starter divided by all the flour, including the flour in the starter. A 75 % dough with 20 % starter at 100 % hydration is about 75 % either way; stiff starters lower it."),
         ("How much starter should I use?", "Most sourdough recipes use 10–25 % starter. Less starter means a longer, slower rise.")],
        "t-bread", "bread")

    calc_page(
        "soap/lye-calculator.html", "Lye Calculator for Cold Process Soap (NaOH) | Free",
        "Free lye calculator for cold process soap: grams of sodium hydroxide and water for your oils, superfat and lye concentration. SAP values for 19 common oils.",
        "Soap", "Free soap making tool", "Lye calculator (NaOH)",
        "Sodium hydroxide and water for your oils, with superfat and lye concentration. Always double-check before you weigh lye.",
        """<div class="full" id="oils"></div>
<div class="full"><button type="button" class="btn ghost" id="add-oil">+ Add oil</button></div>
<div><label for="sf">Superfat <small>(%)</small></label><input id="sf" inputmode="decimal" value="5"></div>
<div><label for="conc">Lye concentration <small>(%)</small></label><input id="conc" inputmode="decimal" value="33"></div>
<div><label for="purity">NaOH purity <small>(%)</small></label><input id="purity" inputmode="decimal" value="100"></div>""",
        """<div class="eyebrow">Weigh out</div><div class="big" id="l-naoh">–</div>
<div class="rows"><div><span>Water</span><span id="l-water">–</span></div><div><span>Oils</span><span id="l-oils">–</span></div>
<div><span>Water : lye</span><span id="l-ratio">–</span></div><div><span>Batch</span><span id="l-batch">–</span></div></div>
<p class="note">Lye is caustic: gloves, goggles, ventilation, and always add lye to water, never water to lye.</p>""",
        [("How is the lye amount calculated?", "Lye = Σ (oil grams × SAP value) × (1 − superfat) ÷ purity. SAP values are in grams of KOH per gram of oil and are converted to NaOH by molar mass (39.997 / 56.106)."),
         ("What superfat should I use?", "5 % is a common starting point for bar soap: a little oil stays unsaponified for a milder bar. Salt bars and 100 % coconut soaps often use 15–20 %."),
         ("Where do the SAP values come from?", "From the SoapCalc oil list, cross-checked against published saponification values. Oils from different suppliers vary, so treat results as a starting point.")],
        "t-soap", "lye",
        extra_scripts=f'<script>window.OILS = {json.dumps(load_oils())};</script>')


# ---------- Countdown ----------

def build_countdown():
    path = "countdown/christmas-countdown.html"
    faq_html, faq_ld = faq([
        ("How many days until Christmas?",
         "The counter at the top of this page shows the exact days, hours, minutes and seconds until 25 December in your own time zone, "
         "and updates live. After Christmas it switches to next year's date."),
        ("How many sleeps until Christmas?",
         "Sleeps are the nights left before Christmas morning: on Christmas Eve there is one sleep left. The page shows them under the main counter."),
        ("How do I put a Christmas countdown on my home screen?",
         "Install Days Until, tap + and pick the Christmas template, then long-press your home screen, choose Widgets and add the Days Until widget. "
         "The number of days updates by itself every day."),
        ("Can I count down to New Year too?",
         "Yes. The page shows a New Year countdown below the Christmas one, and Days Until has a New Year template as well as birthdays, trips and weddings."),
    ])
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › Countdown</div>
<div class="hero"><div class="eyebrow">Live countdown</div>
<h1>How many days until Christmas?</h1>
<p class="lead">The exact time left until 25 December in your time zone. Keep this page open, or put the countdown on your phone's home screen.</p></div>

<div class="calc card">
<div class="result" aria-live="polite">
<div class="eyebrow">Christmas</div>
<div class="big" id="cd-xmas-days">–</div>
<div class="rows">
<div><span>Hours · minutes · seconds</span><span id="cd-xmas-hms">–</span></div>
<div><span>Sleeps until Christmas</span><span id="cd-xmas-sleeps">–</span></div>
<div><span>Date</span><span id="cd-xmas-date">–</span></div>
</div></div>
<div class="result" aria-live="polite">
<div class="eyebrow">New Year</div>
<div class="big" id="cd-ny-days">–</div>
<div class="rows">
<div><span>Hours · minutes · seconds</span><span id="cd-ny-hms">–</span></div>
<div><span>Date</span><span id="cd-ny-date">–</span></div>
</div></div>
</div>

{promo("days-until", "xmas-countdown", "Put the Christmas countdown on your home screen as a widget, and add trips, birthdays and weddings too.")}

<section class="prose"><h2>Add a Christmas countdown widget</h2>
<ol>
<li>Install Days Until and open it.</li>
<li>Tap <b>+</b> and pick the <b>Christmas</b> template (🎄). The date fills in by itself.</li>
<li>Long-press your home screen, tap <b>Widgets</b>, find <b>Days Until</b> and drag it onto the screen.</li>
<li>Tap the widget to choose the Christmas event. The number of days updates every day.</li>
</ol></section>
{faq_html}
"""
    shell(path, "How Many Days Until Christmas? Live Countdown & Widget",
          "Live countdown to Christmas and New Year in your time zone: days, hours, minutes, seconds and sleeps. Put it on your home screen with a widget.",
          body, "t-days", "xmas", [faq_ld], '<script src="{rel}assets/calc.js"></script>')


# ---------- App pages ----------

def build_apps():
    for key, a in APPS.items():
        c = CFG["apps"][key]
        path = f"apps/{key}.html"
        icon = f'<img class="appicon" src="{{rel}}{a["icon"]}" alt="{e(c["short"])} icon" width="72" height="72">' if a["icon"] else ""
        shots = "".join(f'<img src="{{rel}}{s}" alt="{e(c["short"])} screenshot {i + 1}" loading="lazy" width="220">' for i, s in enumerate(a["screens"]))
        privacy = a.get("privacy") or f'{CFG["policy_base"]}/{key}/privacy.html'
        terms = a.get("terms") or f'{CFG["policy_base"]}/{key}/terms.html'
        calc = (f'<section><h2>Try it in your browser</h2><p><a class="btn ghost" href="{{rel}}{a["calc"][0]}">{a["calc"][1]} →</a></p></section>'
                if a.get("calc") else "")
        note = f' {e(a["note"])}' if a.get("note") else ""
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
{calc}
<p class="note">No account. Your data stays on your device.{note} <a href="{privacy}">Privacy</a> · <a href="{terms}">Terms</a> · <a href="mailto:{CFG["support_email"]}">Support</a></p>
"""
        shell(path, f"{c['name']} — app for iPhone and Android", a["tagline"], body, a["theme"], jsonld=[ld])


# ---------- Home ----------

def build_home():
    calcs = [
        ("hvac/superheat-subcooling-calculator.html", "HVAC", "Superheat & subcooling calculator", "R-454B, R-32, R-410A, R-22 with PT lookup.", "t-hvac"),
        ("hvac/pt-chart/index.html", "HVAC", "Refrigerant PT charts", f"{len(PT)} refrigerants, bubble and dew columns.", "t-hvac"),
        ("electrical/voltage-drop-calculator.html", "Electrical", "Voltage drop calculator", "AWG or mm², copper or aluminum, minimum size for 3 %.", "t-elec"),
        ("coating/epoxy-coverage-calculator.html", "Coatings", "Epoxy coverage calculator", "Gallons and kits from area, mils and solids.", "t-coat"),
        ("electrical/wire-size-calculator.html", "Electrical", "Wire size calculator", "NEC 310.16 conductor and breaker, with voltage drop.", "t-elec"),
        ("electrical/awg-to-mm2.html", "Electrical", "AWG to mm² converter", "AWG and kcmil to mm² and back.", "t-elec"),
        ("pool/pool-chemical-calculator.html", "Pool", "Pool chemical calculator", "Chlorine, baking soda, stabilizer and salt doses.", "t-pool"),
        ("bread/bakers-percentage-calculator.html", "Baking", "Baker's percentage calculator", "Sourdough flour, water, starter and salt.", "t-bread"),
        ("soap/lye-calculator.html", "Soap", "Lye calculator", "NaOH and water for cold process soap.", "t-soap"),
        ("countdown/christmas-countdown.html", "Countdown", "Days until Christmas", "Live countdown to Christmas and New Year.", "t-days"),
    ]
    calc_cards = "".join(f'<a class="card {t}" href="{{rel}}{p}"><span class="tag">{tag}</span><h3>{e(h)}</h3><p>{e(d)}</p></a>' for p, tag, h, d, t in calcs)
    def app_cards(group):
        return "".join(
            f'<a class="card {a["theme"]}" href="{{rel}}apps/{k}.html">'
            + (f'<img class="appicon" src="{{rel}}{a["icon"]}" alt="" width="56" height="56" style="width:56px;height:56px;border-radius:14px;margin-bottom:10px">' if a["icon"] else "")
            + f'<h3>{e(CFG["apps"][k]["name"])}</h3><p>{e(a["tagline"])}</p></a>'
            for k, a in APPS.items() if a.get("group", "trades") == group)
    body = f"""
<div class="hero"><div class="eyebrow">{e(CFG["brand"])} Tools</div>
<h1>Field calculators for the trades</h1>
<p class="lead">Free, fast tools for HVAC techs, electricians and coating installers. Every number comes from published tables, and every tool has a phone app that works offline.</p></div>
<section><h2>Free calculators</h2><div class="grid">{calc_cards}</div></section>
<section id="apps"><h2>Apps for the trades</h2><div class="grid">{app_cards("trades")}</div></section>
<section><h2>Everyday apps</h2><div class="grid">{app_cards("everyday")}</div>
<p><a href="{{rel}}countdown/christmas-countdown.html">How many days until Christmas? Live countdown →</a></p></section>
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
    build_countdown()
    build_more()
    build_apps()
    (OUT / "404.html").write_text((OUT / "index.html").read_text())
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    urls = "".join(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    print(f"{len(pages)} pages, {len(PT)} PT charts -> {OUT}")


if __name__ == "__main__":
    main()
