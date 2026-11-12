#!/usr/bin/env python3
"""Builds the static marketing site into ./site. It is served from zhukovskyi.space/calculators: the my_space repo
copies ./site with tools/sync_calculators.py. ./docs (GitHub Pages, the old address) only holds redirects to it.

Data comes straight from the app repos next to this folder (PT charts from hvac-charge-app, screenshots and icons
from fastlane), so the site never drifts from the apps. Store links live in config.json: fill them in and rebuild.

    python3 build.py
"""

import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, urljoin

import calcs_more
import guides
import trust

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # ~/Desktop/mobile_sub_app
OUT = HERE / "site"  # the real site, copied into my_space and served at base_url
LEGACY_OUT = HERE / "docs"  # GitHub Pages serves main:/docs: one redirect page per old address
CFG = json.loads((HERE / "config.json").read_text())
BASE = CFG["base_url"].rstrip("/")
TODAY = date.today().isoformat()
SITE = CFG["developer_site"].rstrip("/")  # the main site: apps, about, privacy
SITE_NAME = f'{CFG["brand"]} Tools'
# Structured data: the same @id as on the main site, so both sites describe one person and one publisher.
PERSON_ID = f"{SITE}/#person"
ORG_ID = f"{SITE}/#dredev"
# Pages the header and the footer of both sites link to.
ABOUT_URL = f"{SITE}/about/"
PRIVACY_URL = f"{SITE}/privacy/"
OG_IMAGE = "assets/og.jpg"  # 1200x630, made by tools/og_image.py
# lastmod per page: the day its content last changed, kept between builds by content hash (see lastmod()).
LASTMOD_FILE = HERE / "lastmod.json"
LASTMOD = json.loads(LASTMOD_FILE.read_text()) if LASTMOD_FILE.exists() else {}
LASTMOD_TOKEN = "@@LASTMOD@@"  # replaced in the finished page with that page's lastmod date
FREE_REFRIGERANTS = ["R-410A", "R-454B", "R-32", "R-22"]  # same free set as hvac-charge-app AppConfig

e = html.escape
pages: list[str] = []  # canonical URLs for the sitemap
page_dates: dict[str, str] = {}  # URL -> lastmod


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
    "poolpro": {
        "theme": "t-pool",
        "tagline": "Pool chemical calculator: exact doses for the products you own, CSI, a test log and a service route.",
        "intro": "PoolPro turns a pool test into exact doses for the chemicals already on your shelf, in the order to add them. "
                 "For pool owners and pool service techs. Offline, no account, no ads and no brand pushing.",
        "free": ["Doses for FC, pH, TA, calcium, CYA and salt", "Liquid chlorine, cal-hypo, dichlor, trichlor, acid, baking soda and more, or your own product",
                 "TFP-style FC/CYA targets and CSI", "Gallons, ounces and pounds, or litres and grams"],
        "pro": ["Unlimited pools, each with its own log", "Weekly service route with directions", "PDF report for every client visit", "CSV export of every test"],
        "calc": ("pool/pool-chemical-calculator.html", "Pool chemical calculator"),
        "icons": ["pool-chem-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "pool-chem-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "UtilitiesApplication",
        "privacy": f'{CFG["policy_base"]}/poolpro/privacy.html',
        "terms": f'{CFG["policy_base"]}/poolpro/terms.html',
    },
    "softwash": {
        "theme": "t-wash",
        "tagline": "Soft wash calculator: SH mix ratios, downstream strength, chemical cost and PDF quotes.",
        "intro": "For soft wash and pressure washing businesses. Mix sodium hypochlorite right, know the real strength that hits the wall, "
                 "and send a clean PDF quote before you leave the driveway.",
        "free": ["Tank mix: SH, water and surfactant from the SH you actually have", "One-tap targets for house, roof, concrete, fence and deck",
                 "Downstream and proportioner math: draw ratio to % at the surface", "Bucket test for your injector's real draw"],
        "pro": ["Unlimited quotes with your price", "PDF quotes with your company name", "Job history: quoted, booked, done", "Chemical load list for the truck"],
        "calc": None,
        "icons": ["softwash-calc-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "softwash-calc-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "BusinessApplication",
        "privacy": f'{CFG["policy_base"]}/softwash/privacy.html',
        "terms": f'{CFG["policy_base"]}/softwash/terms.html',
    },
    "roofcalc": {
        "theme": "t-roof",
        "tagline": "Roofing calculator: squares from the footprint and pitch, every material and PDF quotes.",
        "intro": "For roofers who bid jobs every week. Measure from the ground, get the squares and every material, "
                 "and send a PDF quote before you leave the driveway. No ads, works offline.",
        "free": ["Sloped area from length, span, overhang and pitch, gable or hip", "Eaves, rakes, ridge, hips and valleys worked out for you",
                 "Shingle bundles with waste by roof type", "Starter, ridge cap, drip edge, underlayment, ice & water and nails"],
        "pro": ["PDF quotes with your company name", "Saved estimates and supplier order list", "Multi-section roofs: house, garage, porch",
                "Tear-off tons and ice barrier by code"],
        "calc": None,
        "icons": ["roofcalc-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "roofcalc-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "BusinessApplication",
        "privacy": f'{CFG["policy_base"]}/roofcalc/privacy.html',
        "terms": f'{CFG["policy_base"]}/roofcalc/terms.html',
    },
    "slabcalc": {
        "theme": "t-slab",
        "tagline": "Concrete calculator: cubic yards and bags, rebar, mesh and forms on a feet-inch keypad. Pay once, no ads.",
        "intro": "For contractors and serious DIYers. Type 12' 6½\" in five taps and get yards, bags, rebar and forms while you type. "
                 "Pro is a one-time purchase.",
        "free": ["Slabs, footings, pads, columns, sonotubes and post holes", "Cubic yards, cubic feet or m³ with waste", "Ready-mix rounded to the next ¼ yard",
                 "80, 60 and 40 lb bags, or 25 and 30 kg"],
        "pro": ["Walls, stairs and every concrete shape", "Rebar grid: bars, sticks, laps and weight", "Wire mesh, form boards and stakes",
                "Ready-mix vs bags cost with your prices", "Jobs: every pour in one order"],
        "calc": None,
        "icons": ["slabcalc-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "slabcalc-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "UtilitiesApplication",
        "privacy": f'{CFG["policy_base"]}/slabcalc/privacy.html',
        "terms": f'{CFG["policy_base"]}/slabcalc/terms.html',
    },
    "paintbid": {
        "theme": "t-paint",
        "tagline": "Painting estimator: rooms, gallons, labor hours and PDF quotes. Works offline.",
        "intro": "For painting contractors. Walk the house, tap in the rooms, and send a clean PDF quote before you leave the driveway. "
                 "No login, no loading screens.",
        "free": ["Rooms, single walls, accent walls and exterior elevations", "Doors and windows by count, identical rooms at once",
                 "Walls, ceilings and trim with 1–3 coats and primer", "Exact gallons from your paint's coverage"],
        "pro": ["PDF quotes with your business name", "Price per room on every quote", "Unlimited saved jobs", "Paint store shopping list"],
        "calc": None,
        "icons": ["paintbid-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "paintbid-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "BusinessApplication",
        "privacy": f'{CFG["policy_base"]}/paintbid/privacy.html',
        "terms": f'{CFG["policy_base"]}/paintbid/terms.html',
    },
    "sitelog": {
        "theme": "t-site",
        "tagline": "Daily site reports and punch lists with photos. A PDF in one tap. Works offline.",
        "intro": "The fast, offline site diary for contractors who run their own jobs. Write the daily report in two minutes, "
                 "walk the site with a punch list, and send a clean PDF before you leave.",
        "free": ["Weather, crew and hours with man-hours added up", "Yesterday's crew already filled in", "Work done, deliveries, delays, inspections and photos",
                 "Punch list with photos, locations, trades and due dates"],
        "pro": ["Unlimited projects (free: 1)", "Unlimited photos on every report and snag", "Your logo on every PDF", "Punch list PDF for one trade at a time"],
        "calc": None,
        "icons": ["sitelog-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "sitelog-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "BusinessApplication",
        "privacy": f'{CFG["policy_base"]}/sitelog/privacy.html',
        "terms": f'{CFG["policy_base"]}/sitelog/terms.html',
    },
    "lye-calc": {
        "group": "makers",
        "theme": "t-soap",
        "tagline": "Lye calculator for soap making: NaOH, KOH, superfat, water, soap qualities and batch cost.",
        "intro": "A soap making calculator that gets the lye right and never loses your recipes. Add oils by weight or percent, "
                 "set superfat and water, and see exactly what to weigh.",
        "free": ["NaOH, KOH or dual lye, with lye purity", "Lye amounts from published SAP values", "Superfat, water and fragrance",
                 "Soap qualities and fatty acid profile", "78 oils, butters and fats; 8 starter recipes", "Save up to 5 recipes"],
        "pro": ["Unlimited saved recipes", "Batch cost and cost per bar", "Wholesale and retail prices with your profit per bar",
                "Printable recipe sheet (PDF)", "Resize any recipe to a new batch size"],
        "calc": ("soap/lye-calculator.html", "Lye calculator"),
        "icons": ["soapcalc-app/fastlane/metadata/android/en-US/images/icon.png"],
        "shots": "soapcalc-app/fastlane/metadata/android/en-US/images/phoneScreenshots",
        "category": "LifestyleApplication",
        "privacy": f'{CFG["policy_base"]}/lye-calc/privacy.html',
        "terms": f'{CFG["policy_base"]}/lye-calc/terms.html',
        "note": "Lye is caustic: wear gloves and goggles and check every recipe.",
    },
    "leben-in-deutschland": {
        "group": "everyday",
        "lang": "uk",
        "theme": "t-lid",
        "tagline": "Офіційні питання BAMF для тесту Leben in Deutschland з перекладом і поясненнями українською. Без реклами.",
        "intro": "На тесті питання лише німецькою. У застосунку ви бачите оригінальне німецьке питання, переклад українською, "
                 "а після відповіді — чому правильна саме ця відповідь. Так ви не зазубрюєте, а розумієте.",
        "free": ["Усі 300 загальних питань і по 10 для кожної з 16 федеральних земель", "Німецький оригінал і переклад українською",
                 "Пробний іспит: 33 питання, 60 хвилин (один на день)", "Мої помилки, навчання за темами, пошук і закладки",
                 "Без реклами, без акаунта, працює без інтернету"],
        "pro": ["Пояснення українською до всіх 460 питань", "Необмежені пробні іспити", "Розумне тренування: спершу помилки, потім нові питання"],
        "calc": None,
        "icons": ["lid-test-ua-app/fastlane/metadata/android/uk/images/icon.png", "lid-test-ua-app/tool/store/icon-1024.png"],
        "shots": "lid-test-ua-app/fastlane/metadata/android/uk/images/phoneScreenshots",
        "category": "EducationApplication",
        "privacy": f'{CFG["policy_base"]}/lid-test/privacy.html',
        "terms": f'{CFG["policy_base"]}/lid-test/terms.html',
        "note": "Неофіційний застосунок, не пов'язаний з BAMF.",
    },
}


def prep_images():
    """App icons for the promo blocks and the home page. Screenshots live on the apps' own pages on the main site."""
    for key, a in APPS.items():
        a["icon"] = image(a["icons"], f"{key}-icon.jpg", 192)


# ---------- page shell ----------

# Category links under the main menu. HVAC and Electrical go to their hub page once that module is in the repo.
SUBNAV = [
    ("HVAC", "hvac/" if (HERE / "pages_hvac.py").exists() else "hvac/superheat-subcooling-calculator.html"),
    ("Electrical", "electrical/" if (HERE / "pages_electrical.py").exists() else "electrical/voltage-drop-calculator.html"),
    ("Coatings", "coating/epoxy-coverage-calculator.html"),
    ("Pool", "pool/pool-chemical-calculator.html"),
    ("Baking", "bread/bakers-percentage-calculator.html"),
    ("Soap", "soap/lye-calculator.html"),
]
SUBNAV += calcs_more.SUBNAV  # roofing, concrete, shifts and the hobby categories
TRUST_PAGES = {"methodology.html", "verification.html", "changelog.html"}
DISCLAIMER = ("Reference only. A result depends on what you enter and on the published tables named on this page. "
              "Before you buy materials, size a circuit, charge a system or dose chemicals, check it against the code in force "
              "where you work, the product label and the manufacturer's instructions. These tools come with no warranty.")


def clean_links(text):
    """Internal links go to /dir/, never to /dir/index.html, so every page has one address."""
    def fix(m):
        pre, frag = m.group(1), m.group(2) or ""
        if "://" in pre and not pre.startswith(SITE):
            return m.group(0)
        return f'href="{pre or "./"}{frag}"'
    return re.sub(r'href="((?:[^"#?]*/)?)index\.html(#[^"]*)?"', fix, text)


def script_sources(scripts):
    """The text of the local scripts a page loads: a change in calc.js changes what the page answers."""
    out = []
    for name in re.findall(r'src="(?:\.\./)*assets/([^"]+)"', scripts):
        f = next((d / name for d in (OUT / "assets", HERE / "assets") if (d / name).exists()), None)
        out.append(f.read_text() if f else name)
    return out


def lastmod(url, *parts):
    """The day this page's content last changed, for the sitemap and dateModified. The hash covers the title,
    description, body, structured data and scripts; the shared header and footer are left out, so a menu change
    moves no dates. lastmod.json keeps hash and date between builds."""
    digest = hashlib.sha256("\x00".join(parts).encode()).hexdigest()[:16]
    if LASTMOD.get(url, {}).get("hash") != digest:
        LASTMOD[url] = {"hash": digest, "date": TODAY}
    page_dates[url] = LASTMOD[url]["date"]
    return page_dates[url]


def page_name(body, title):
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    return html.unescape(re.sub("<[^>]+>", "", h1.group(1))).strip() if h1 else title


def breadcrumb_ld(path, url, body, title):
    """BreadcrumbList from the crumbs people see on the page, ending with the page itself."""
    items = [("Home", f"{SITE}/"), ("Free tools", f"{BASE}/")]
    m = re.search(r'<div class="crumbs">(.*?)</div>', body, re.S)
    for href, name in re.findall(r'<a href="([^"]+)">([^<]+)</a>', m.group(1)) if m else []:
        target = urljoin(f"{BASE}/{path}", href)
        if target not in [u for _, u in items]:
            items.append((html.unescape(name), target))
    if url != f"{BASE}/":
        items.append((page_name(body, title), url))
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": target} for i, (name, target) in enumerate(items, 1)]}


def site_graph(url, title, desc, crumbs, mod, index):
    """Nodes every page shares: the page, its breadcrumbs, the publisher (Dre Dev) and the author.
    Index pages carry the full publisher record; the rest point to it by @id."""
    org = {"@type": "Organization", "@id": ORG_ID, "name": CFG["brand"], "url": ABOUT_URL}
    if index:
        org.update({"email": CFG["support_email"], "founder": {"@id": PERSON_ID}, "sameAs": CFG["same_as"]})
    person = {"@type": "Person", "@id": PERSON_ID, "name": guides.AUTHOR, "url": f"{SITE}/"}
    page = {"@type": "CollectionPage" if index else "WebPage", "@id": url, "url": url, "name": title, "description": desc,
            "isPartOf": {"@type": "WebSite", "@id": f"{BASE}/#website", "name": SITE_NAME, "url": f"{BASE}/",
                         "publisher": {"@id": ORG_ID}},
            "author": {"@id": PERSON_ID}, "publisher": {"@id": ORG_ID}, "dateModified": mod}
    return {"@context": "https://schema.org", "@graph": [page, crumbs, org, person]}


def error_mailto(url, name):
    """'Found an error?': an email with the page and the three things needed to check a report already laid out."""
    body = (f"Page: {url}\n\nWhat I entered:\n\nWhat the page showed:\n\n"
            "What I expected, and where that number comes from:\n")
    return f'mailto:{CFG["support_email"]}?subject={quote("Calculator error: " + name)}&amp;body={quote(body)}'


def trust_block(path, url, body, title, calc, rel):
    """Under every page: who made it, one shared disclaimer, and the way to the methodology, the checked
    examples, the changelog and an error report."""
    plain = path == "index.html" or path in TRUST_PAGES or calc == "xmas"
    by = ("" if plain or 'class="note byline"' in body else
          f'<p class="note">Made by <a href="{ABOUT_URL}">{guides.AUTHOR}</a> ({e(CFG["brand"])}). '
          f'How the numbers are checked: <a href="{rel}methodology.html">methodology and sources</a>.</p>')
    disclaimer = "" if plain else f'<p class="note disclaimer">{DISCLAIMER}</p>'
    links = " · ".join(f'<a href="{rel}{p}">{t}</a>' for p, t in (
        ("methodology.html", "Methodology and sources"), ("verification.html", "Checked examples"),
        ("changelog.html", "Changelog")) if p != path)
    return (f'<aside class="trust">{by}{disclaimer}<p class="note">{links} · '
            f'<a href="{error_mailto(url, page_name(body, title))}">Found an error? Tell me</a></p></aside>')


def shell(path, title, desc, body, theme="", calc=None, jsonld=None, scripts="", lang="en", canonical=None):
    depth = path.count("/")
    rel = "../" * depth
    home = rel or "./"
    own = f"{BASE}/{path}".replace("/index.html", "/")
    canonical = canonical or own
    body = clean_links(body.replace("{rel}", rel))
    scripts = scripts.replace("{rel}", rel)
    page_ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    mod = lastmod(own, title, desc, body, page_ld, scripts, *script_sources(scripts))
    graph = site_graph(own, title, desc, breadcrumb_ld(path, own, body, title), mod, path.endswith("index.html"))
    ld = f'<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False)}</script>' + page_ld.replace(LASTMOD_TOKEN, mod)
    calc_attr = f' data-calc="{calc}"' if calc else ""
    # Smart App Banner on iPhone, only where the page promotes an app that is on the App Store.
    ids = [m.group(1) for k in re.findall(r"<!-- app:([\w-]+) -->", body)
           if (m := re.search(r"/id(\d+)", CFG["apps"][k]["app_store_url"] or ""))]
    itunes = f'<meta name="apple-itunes-app" content="app-id={ids[0]}">\n' if ids else ""
    subnav = "".join(f'<a href="{rel}{p}">{t}</a>' for t, p in SUBNAV)
    doc = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SITE_NAME)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{itunes}<meta name="theme-color" content="#0e1116" media="(prefers-color-scheme: dark)">
<link rel="stylesheet" href="{rel}assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%23f59e0b'/%3E%3Cstop offset='1' stop-color='%23ef4444'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='32' height='32' rx='8' fill='url(%23g)'/%3E%3C/svg%3E">
{ld}
<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "83c899454bcd4d139b58edeea34eaac0"}}'></script><!-- End Cloudflare Web Analytics -->
</head>
<body class="{theme}"{calc_attr}>
<header class="top"><div class="wrap">
<a class="brand" href="{home}"><i></i>{e(SITE_NAME)}</a>
<nav aria-label="Main">
<a href="{SITE}/apps/">Apps</a>
<a href="{home}" aria-current="page">Free tools</a>
<a href="{SITE}/blog/" class="hide-sm">Blog</a>
<a href="{ABOUT_URL}">About</a>
</nav>
</div>
<div class="wrap"><nav class="subnav" aria-label="Calculators">{subnav}</nav></div></header>
<main class="wrap">
{body}
{trust_block(path, own, body, title, calc, rel)}
</main>
<footer><div class="wrap">
<span>© 2026 {e(CFG["brand"])} · apps and free tools by <a href="{ABOUT_URL}">{guides.AUTHOR}</a>. No account, no tracking cookies.</span>
<nav aria-label="Footer">
<a href="{ABOUT_URL}">About</a>
<a href="{SITE}/apps/">Apps</a>
<a href="{home}">Free tools</a>
<a href="{rel}methodology.html">Methodology</a>
<a href="{PRIVACY_URL}">Privacy</a>
<a href="{SITE}/testers/">Become a tester</a>
<a href="{SITE}/blog/">Blog</a>
<a href="https://github.com/andronaft">GitHub</a>
<a href="mailto:{CFG["support_email"]}">{CFG["support_email"]}</a>
</nav>
</div></footer>
{scripts}
</body>
</html>
"""
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc)
    if canonical == own:  # pages that point elsewhere stay out of the sitemap
        pages.append(canonical)


# ---------- shared blocks ----------

def store_buttons(key, source, lang="en"):
    c = CFG["apps"][key]
    btns = []
    play = f"https://play.google.com/store/apps/details?id={c['package']}&referrer=utm_source%3Ddredev-tools%26utm_campaign%3D{source}"
    if c["app_store_url"]:
        btns.append(f'<a class="btn" href="{c["app_store_url"]}">Download on the App Store</a>')
    if c["google_play_live"]:
        btns.append(f'<a class="btn" href="{play}">Get it on Google Play</a>')
    if not btns:
        uk = lang == "uk"
        dev = f'{CFG["developer_site"]}/apps/{c.get("site_slug", key)}/'
        if c["beta_group_url"]:
            btns.append(f'<a class="btn" href="{c["beta_group_url"]}">Join the free Android beta</a>')
        elif c.get("status") == "testing":
            # Closed test on Google Play: the app page on the developer site walks through joining the testers group first.
            btns.append(f'<a class="btn" href="{dev}">{"Стати тестером" if uk else "Become a tester, free"}</a>')
            btns.append(f'<a class="btn ghost" href="{CFG["tester_signup"]}" target="_blank" rel="noopener">{"iPhone? Записатися" if uk else "iPhone? Sign up"}</a>')
        else:
            label = "Отримати ранній доступ" if uk else "Get early access"
            btns.append(f'<a class="btn" href="{CFG["tester_signup"]}" target="_blank" rel="noopener">{label}</a>')
        if c.get("status") == "testing":
            soon = "Закритий тест у Google Play, App Store незабаром" if uk else "Closed test on Google Play &middot; App Store coming soon"
        else:
            soon = "App Store і Google Play: незабаром" if uk else "App Store &amp; Google Play: coming soon"
        btns.append(f'<span class="btn off">{soon}</span>')
    return f'<div class="btns">{"".join(btns)}</div>'


def promo(key, source, pitch):
    a, c = APPS[key], CFG["apps"][key]
    icon = f'<img class="icon" src="{{rel}}{a["icon"]}" alt="" width="72" height="72">' if a["icon"] else ""
    return f"""<!-- app:{key} --><section class="promo">{icon}<div>
<div class="eyebrow">The whole job, on your phone</div>
<h3>{e(c["name"])}</h3>
<p>{e(pitch)} <a href="{app_href(key)}">See what's inside</a>.</p>
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
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "author": {"@type": "Person", "@id": PERSON_ID, "name": guides.AUTHOR, "url": f"{SITE}/"},
            "publisher": {"@id": ORG_ID}, "dateModified": LASTMOD_TOKEN}


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
    ans, guide_html, extra_faq = guides.vd_guide()
    faq_html, faq_ld = faq(extra_faq + [
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
<p class="lead">Voltage drop in volts and percent, the voltage at the load and the smallest wire that stays under 3 %. NEC (AWG) or IEC (mm²), copper or aluminum.</p>{ans}</div>

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

{guide_html}
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
    ans, guide_html, extra_faq = guides.coat_guide()
    faq_html, faq_ld = faq(extra_faq + [
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
<p class="lead">How many gallons and kits of epoxy, polyaspartic or polyurea you need, from area, thickness in mils and solids by volume.</p>{ans}</div>

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

{guide_html}
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
        m = re.search(rf"Oil\('{oid}',\s*sapKoh: ([\d.]+).*?'en': '([^']+)'", src, re.S)
        if m:
            out.append({"id": oid, "sap": float(m.group(1)), "name": m.group(2)})
    # An empty list would publish a lye calculator with no oils to pick: stop the build instead.
    assert len(out) == len(LYE_OILS), f"oil_data.dart: found {len(out)} of {len(LYE_OILS)} oils"
    return out


def calc_page(path, title, desc, crumb, eyebrow, h1, lead, form, result, faq_items, theme, calc, promo_html="", extra_scripts="", note="", answer_guide=None):
    ans, guide_html, extra_faq = answer_guide or ("", "", [])
    faq_html, faq_ld = faq(faq_items + extra_faq)
    body = f"""
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › {crumb}</div>
<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{h1}</h1><p class="lead">{lead}</p>{ans}</div>
<div class="calc card"><div class="fields">{form}</div><div class="result" aria-live="polite">{result}</div></div>
{note}
{guide_html}
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
        "t-elec", "awg", answer_guide=guides.awg_guide(), promo_html=promo("electrician-calc", "awg", "Cable size with ampacity and derating, voltage drop and 21 calculators for NEC and IEC."))

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
        "t-elec", "wire", answer_guide=guides.wire_guide(), promo_html=promo("electrician-calc", "wire-size", "Full cable sizing with ambient and grouping derating, IEC and NEC, step-by-step working and PDF reports."))

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
        "t-pool", "pool", answer_guide=guides.pool_guide(),
        promo_html=calcs_more.app_promo("poolpro", "pool-calc", "Turn a pool test into exact doses for the chemicals already on your shelf, in the order to add them, with CSI and a test log."))

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
        "t-bread", "bread", answer_guide=guides.bread_guide(),
        promo_html=calcs_more.app_promo("levain", "bread", "Tell Levain when you want bread, and it reminds you of every feed, fold and bake step on the way."))

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
        "t-soap", "lye", answer_guide=guides.lye_guide(load_oils()),
        promo_html=calcs_more.app_promo("lye-calc", "lye", "Save your recipes, see soap qualities and the fatty acid profile, and get batch cost and cost per bar."),
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
# The apps have one page each, on the main site (/apps/<slug>/). This site used to keep its own copies at
# /calculators/apps/<key>.html: thin duplicates, removed. docs/ and the nginx config redirect the old addresses.

MAIN_SLUG = {"leben-in-deutschland": "lid-test"}


def main_app_url(key):
    """The app's page on the main site; the Ukrainian page of an app described here in Ukrainian."""
    lang = APPS[key].get("lang", "en")
    return f'{SITE}/apps/{MAIN_SLUG.get(key, key)}/' + ("" if lang == "en" else f"{lang}/")


def app_href(key):
    """Where links to an app go."""
    return main_app_url(key)


# ---------- Home ----------

CALCS = [
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
CALCS += calcs_more.HOME_CARDS  # hobby and trade calculators built by calcs_more.build()


def build_home():
    calcs = CALCS
    calc_cards = "".join(f'<a class="card {t}" href="{{rel}}{p}"><span class="tag">{tag}</span><h3>{e(h)}</h3><p>{e(d)}</p></a>' for p, tag, h, d, t in calcs)
    def app_cards(group):
        return "".join(
            f'<a class="card {a["theme"]}" href="{app_href(k)}">'
            + (f'<img class="appicon" src="{{rel}}{a["icon"]}" alt="" width="56" height="56" style="width:56px;height:56px;border-radius:14px;margin-bottom:10px">' if a["icon"] else "")
            + f'<h3>{e(CFG["apps"][k]["name"])}</h3><p>{e(a["tagline"])}</p></a>'
            for k, a in APPS.items() if a.get("group", "trades") == group)
    body = f"""
<div class="hero"><div class="eyebrow">{e(CFG["brand"])} Tools</div>
<h1>Field calculators for the trades</h1>
<p class="lead">Free, fast tools for HVAC techs, electricians and coating installers. Every number comes from published tables, and every tool has a phone app that works offline.</p></div>
<section><h2>Free calculators</h2><div class="grid">{calc_cards}</div></section>
<section id="apps"><h2>Apps for the trades</h2><div class="grid">{app_cards("trades")}</div></section>
<section><h2>Apps for makers</h2><div class="grid">{app_cards("makers")}</div></section>
<section><h2>Everyday apps</h2><div class="grid">{app_cards("everyday")}</div>
<p><a href="{{rel}}countdown/christmas-countdown.html">How many days until Christmas? Live countdown →</a></p></section>
<section class="prose"><h2>Why these tools</h2>
<p>No account, no ads, no data leaving your phone. Built by an independent developer, <a href="{ABOUT_URL}">Andrii Zhukovskyi</a>, who answers every email: <a href="mailto:{CFG["support_email"]}">{CFG["support_email"]}</a>.</p>
<p>Every table and formula names its source. The <a href="{{rel}}methodology.html">methodology</a> lists the editions and the limits, and the <a href="{{rel}}verification.html">checked examples</a> put a row from each source next to what the calculator answers.</p>
<p>Most of the apps are in a free closed test on Google Play right now, with the App Store next. <a href="{CFG["developer_site"]}/testers/">Become a tester</a> and get them before release.</p></section>
"""
    shell("index.html", f"{CFG['brand']} Tools: free calculators for HVAC, electrical and floor coating",
          "Free online calculators for the trades: superheat and subcooling, refrigerant PT charts, voltage drop and epoxy coverage, plus offline phone apps.",
          body)


def write_llms():
    """llms.txt (llmstxt.org): a plain summary for AI assistants, built around the apps.
    Apps people can install now get a full block (free vs Pro, the matching calculator); the rest a line each."""
    dev = CFG["developer_site"]

    def live(c):
        return c["google_play_live"] or c["app_store_url"]

    def state(c):
        if live(c):
            return "Available on " + " and ".join(x for x, ok in (("Google Play", c["google_play_live"]), ("the App Store", c["app_store_url"])) if ok) + "."
        return f"Android in a free closed test on Google Play ([how to join]({dev}/testers/)); App Store coming."

    def block(k, a):
        c = CFG["apps"][k]
        free = "\n".join(f"- {x}" for x in a["free"])
        pro = "\n".join(f"- {x}" for x in a["pro"])
        calc = f"\nFree in the browser, same formulas: [{a['calc'][1]}]({BASE}/{a['calc'][0]}).\n" if a.get("calc") else ""
        return (f"### {c['name']}\n\n{a['tagline']} {state(c)} Page: {main_app_url(k)}\n\n{a['intro']}\n\n"
                f"Free:\n{free}\n\nPro:\n{pro}\n{calc}")

    rank = {"trades": 0, "makers": 1, "everyday": 2}  # trades first: Pro tiers and calculators next to them
    ordered = sorted(APPS.items(), key=lambda kv: rank.get(kv[1].get("group", "trades"), 9))
    ready = [(k, a) for k, a in ordered if live(CFG["apps"][k]) or CFG["apps"][k].get("status") == "testing"]
    later = [(k, a) for k, a in ordered if (k, a) not in ready]
    now = "\n".join(block(k, a) for k, a in ready)
    soon = "\n".join(f'- [{CFG["apps"][k]["name"]}]({main_app_url(k)}): {a["tagline"]}' for k, a in later)
    calc_lines = "\n".join(f"- [{h}]({BASE}/{p.removesuffix('index.html')}): {d}" for p, _, h, d, _ in CALCS)
    pt_lines = ", ".join(f"[{rid}]({BASE}/hvac/pt-chart/{slug(rid)}.html)" for rid in PT)
    (OUT / "llms.txt").write_text(f"""# {CFG["brand"]} apps and free calculators for the trades

> Phone apps for HVAC techs, electricians, floor coating installers, roofers, concrete crews, pool techs, soft washers and makers, many with a free browser calculator that uses the same formulas. Numbers come from published tables (refrigerant PT data, NEC 310.16, IEC 60364). Every app works offline, has no account and no ads, and keeps data on the phone.

Android apps are in closed testing on Google Play and anyone can join for free: {dev}/testers/ . iPhone versions are on their way to the App Store. Made by Andrii Zhukovskyi ({dev}/). Support: {CFG["support_email"]}.

## Apps you can install now

{now}
## Free calculators

{calc_lines}

## Refrigerant PT charts

Pressure-temperature tables with bubble and dew columns: {pt_lines}.

## Coming soon

{soon}

## Optional

- [All {CFG["brand"]} apps]({dev}/apps/): the developer site, with screenshots.
- [Methodology and sources]({BASE}/methodology.html): which tables and editions the calculators use, their assumptions and limits.
- [Checked examples]({BASE}/verification.html): rows from the sources next to the calculators' answers.
- [About {CFG["brand"]}]({ABOUT_URL}): who makes the apps and the calculators.
""")


# Search and answer crawlers, named so that a later rule for "*" cannot shut them out by accident.
SEARCH_BOTS = "".join(f"User-agent: {b}\n" for b in ("OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Bingbot"))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(HERE / "assets", OUT / "assets")
    free = {rid: PT[rid] for rid in FREE_REFRIGERANTS}
    (OUT / "assets/pt-data.js").write_text(f"window.PT_DATA = {json.dumps(free, separators=(',', ':'))};\n")
    prep_images()
    build_home()
    calcs_more.build(sys.modules[__name__])  # hobby and trade calculators, embed copies
    build_hvac()
    build_vd()
    build_coat()
    build_countdown()
    build_more()
    trust.build(sys.modules[__name__])
    (OUT / "404.html").write_text((OUT / "index.html").read_text())
    (OUT / ".nojekyll").write_text("")
    if CFG.get("indexnow_key"):  # IndexNow (Bing, Yandex): the key file proves the site is ours
        (OUT / f'{CFG["indexnow_key"]}.txt').write_text(CFG["indexnow_key"])
    write_llms()
    # The live robots.txt is the main site's (my_space/build.py); this copy keeps the same rules.
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\n{SEARCH_BOTS}Allow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    urls = "".join(f"<url><loc>{u}</loc><lastmod>{page_dates[u]}</lastmod></url>" for u in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    # Keep hash and date only for pages that still exist.
    LASTMOD_FILE.write_text(json.dumps({u: LASTMOD[u] for u in sorted(page_dates)}, indent=1) + "\n")
    build_legacy()
    print(f"{len(pages)} pages, {len(PT)} PT charts -> {OUT}; redirects -> {LEGACY_OUT}")


def build_legacy():
    """GitHub Pages cannot send a 301, so every old address gets a page that points search engines at the
    new one (canonical) and sends people there at once (meta refresh, with a plain link as a fallback)."""
    if LEGACY_OUT.exists():
        shutil.rmtree(LEGACY_OUT)
    LEGACY_OUT.mkdir()

    def stub(rel, target):
        dest = LEGACY_OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved to {e(target)}</title>
<link rel="canonical" href="{e(target)}">
<meta http-equiv="refresh" content="0; url={e(target)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<p>This page has moved to <a href="{e(target)}">{e(target)}</a>.</p>
<script>location.replace({json.dumps(target)} + location.search + location.hash)</script>
</body>
</html>
''')

    for f in sorted(OUT.rglob("*.html")):
        rel = f.relative_to(OUT).as_posix()
        if rel == "404.html":
            continue
        stub(rel, f"{BASE}/{rel}".replace("/index.html", "/"))
    for key in APPS:  # the app pages this site no longer has
        stub(f"apps/{key}.html", main_app_url(key))
    stub("404.html", f"{BASE}/")
    (LEGACY_OUT / ".nojekyll").write_text("")
    (LEGACY_OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n")
    # Search Console verification files for the old address live at the repo root; Pages serves docs/.
    for f in HERE.glob("google*.html"):
        shutil.copy(f, LEGACY_OUT / f.name)


if __name__ == "__main__":
    main()
