"""Shared pieces for the hobby and trade calculator pages (pages_hobby.py, pages_trades.py, pages_embed.py).

Every page follows the Voltage Drop page: quick answer, calculator, tables of common cases, a worked example,
questions, author and date, and a link to the app. build.py owns the page shell, the sitemap and the home page;
this module only fills the body, so it is wired in with one call: calcs_more.build(build module).
"""
import json
import re
from html import escape as e

import guides

B = None  # the build module (shell, faq, webapp_ld, promo, image, CFG, BASE, OUT), set by init()
CHECKED = "12 November 2026"  # the day the web sources quoted on these pages were read
EMBEDS = []  # (name, title, full page path, height): calculators that also get a bare page for iframes

# Apps that have no entry in build.APPS yet. Names are the store titles (my_space/src/apps.json).
MORE_APPS = {
    "ferment": ("Ferment: Fermentation Tracker", "ferment", "ferment-app"),
    "growlab": ("GrowLab: Hydroponic Nutrients", "growlab", "growlab-app"),
    "wickcalc": ("WickCalc: Candle Calculator", "wickcalc", "wickcalc-app"),
    "dial-in": ("Dial In: Espresso Shot Log", "dial-in", "dialin-coffee-app"),
    "rowkeeper": ("RowKeeper: Row Counter", "rowkeeper", "rowcounter-app"),
    "shiftwise": ("ShiftWise: Shift Work Calendar", "shiftwise", "shift-calendar-app"),
    "levain": ("Levain: Sourdough Starter", "levain", "sourdough-app"),
}
_icons = {}


def init(b):
    global B
    B = b
    EMBEDS.clear()
    _icons.clear()


def src(text, checked=CHECKED):
    """A table's source line: where the numbers come from and the day the source was read."""
    return f"Source: {text}. Checked {checked}."


def table(caption, head, rows, note=""):
    return guides.table(caption, head, rows, note)


def app_promo(key, source, pitch):
    """The app block under a calculator. Apps known to build.py get its promo(); the others link to their page
    on the developer site, which shows where the app can be installed today."""
    if key in B.APPS:
        return B.promo(key, source, pitch)
    name, slug, repo = MORE_APPS[key]
    if key not in _icons:
        _icons[key] = B.image([f"{repo}/fastlane/metadata/android/en-US/images/icon.png"], f"{key}-icon.jpg", 192)
    icon = f'<img class="icon" src="{{rel}}{_icons[key]}" alt="" width="72" height="72">' if _icons[key] else ""
    url = f'{B.CFG["developer_site"]}/apps/{slug}/'
    return f"""<section class="promo">{icon}<div>
<div class="eyebrow">The whole hobby, on your phone</div>
<h3>{e(name)}</h3>
<p>{e(pitch)}</p>
<div class="btns"><a class="btn" href="{url}">See the app</a></div>
</div></section>"""


def related(title, links):
    """Links to sibling pages: [(path, label)]."""
    chips = "".join(f'<a href="{{rel}}{p}">{e(label)}</a>' for p, label in links)
    return f'<section><h2>{e(title)}</h2><div class="chips">{chips}</div></section>'


CSS = '<link rel="stylesheet" href="{rel}assets/calc-more.css">'


def scripts(data=None):
    d = f"<script>window.CALC_DATA = {json.dumps(data, separators=(',', ':'))};</script>" if data is not None else ""
    return d + '<script src="{rel}assets/calc-more.js"></script>'


def page(path, title, desc, crumb, eyebrow, h1, lead, answer, parts, faq_items, theme, app=None, calc=None, form="", result="",
         guide_h2="Charts and worked example", note="", data=None, extra="", embed=None):
    """One page in the Voltage Drop pattern. [parts] are guides.table() / guides.example() blocks; [app] is
    (key, utm source, pitch); [embed] is (name, iframe height) for calculators offered on the embed page."""
    faq_html, faq_ld = B.faq(faq_items)
    card = f'<div class="calc card"><div class="fields">{form}</div><div class="result" aria-live="polite">{result}</div></div>' if calc else ""
    body = f"""
{CSS}
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › {crumb}</div>
<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{h1}</h1><p class="lead">{lead}</p>{guides.answer(answer)}</div>
{card}
{note}
{guide(guide_h2, parts)}
{extra}
{app_promo(*app) if app else ""}
{faq_html}
"""
    plain_h1 = re.sub("<[^>]+>", "", h1)
    B.shell(path, title, desc, body, theme, calc, [B.webapp_ld(plain_h1, path, desc), faq_ld] if calc else [article_ld(plain_h1, path, desc), faq_ld],
            scripts(data) if calc else "")
    if embed and calc:
        name, height = embed
        embed_page(name, plain_h1, path, theme, calc, card, data)
        EMBEDS.append((name, plain_h1, path, height))


def guide(h2, parts):
    """The charts section with the author line. These calculators are not in the site's checked examples
    (verification.json covers calc.js), so the line says what was checked: the apps' control values and the sources."""
    by = (f'<p class="note byline">Made and checked by <a href="{guides.ABOUT}">{guides.AUTHOR}</a>. The source of each table is named under it; '
          f'assumptions and limits are in the <a href="{{rel}}methodology.html">methodology</a>. The formulas are the same as in the matching '
          f'{e(B.CFG["brand"])} app and are tested against its control values. Web sources were read on {CHECKED}.</p>')
    return f'<section class="guide"><h2>{h2}</h2>{"".join(parts)}{by}</section>'


def article_ld(name, path, desc):
    """Reference pages without a live calculator (charts): an Article with the same author and date."""
    ld = B.webapp_ld(name, path, desc)
    return {"@context": "https://schema.org", "@type": "Article", "headline": name, "url": ld["url"], "description": desc,
            "author": ld["author"], "publisher": ld["publisher"], "dateModified": ld["dateModified"]}


def embed_page(name, title, full_path, theme, calc, card, data):
    """A bare copy of a calculator for iframes on other sites: no header, footer or analytics, a credit line
    with the brand name only, noindex and a canonical link to the full page. Not in the sitemap."""
    full = f"{B.BASE}/{full_path}"
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{full}">
<link rel="stylesheet" href="../assets/style.css">
<link rel="stylesheet" href="../assets/calc-more.css">
</head>
<body class="{theme} embed" data-calc="{calc}">
<main class="wrap">
<h1 class="embed-title">{e(title)}</h1>
{card}
<p class="powered">Powered by <a href="{full}" target="_blank" rel="noopener">{e(B.CFG["brand"])} Tools</a></p>
</main>
{scripts(data).replace("{rel}", "../")}
</body>
</html>
"""
    dest = B.OUT / "embed" / f"{name}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc)


def n(x, d=0):
    return guides.fmt(x, d)


def trim(x, d=2):
    """1.50 → 1.5, 2.00 → 2."""
    return f"{x:,.{d}f}".rstrip("0").rstrip(".")
