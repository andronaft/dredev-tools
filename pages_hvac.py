"""HVAC reference pages: a superheat and subcooling calculator per refrigerant, the body of the PT chart pages,
refrigerant comparisons, the target superheat calculator, two guides and the HVAC hub.

Every pressure comes from the PT tables build.py loads from hvac-charge-app (b.PT). The saturation maths below is the
same as assets/calc.js (tempAtPsia, psiaAt), so the worked examples, the tables and the live calculator agree;
tests/test_pages.py runs calc.js itself against these numbers. Other facts come from refdata.py with their source.
"""
import json
import math
import re
from html import escape as e

import guides
import refdata
from pagekit import (CSS, HVAC_NOTE, JS, REL, article_ld, byline, crumbs, dataset_ld, facts, plain, printbar, related,
                     src, table)

ATM = 14.695949
INHG = 0.4911541
STEP = 5

# One switch for the question "what is free on the web": refrigerants with a live calculator on their page.
# None means all of them. The app keeps R-410A, R-454B, R-32 and R-22 free and the rest in Pro; with a smaller set
# here the other pages keep the worked examples and tables and lose only the live calculator.
# Decided by Andrii on 12 Nov 2026: all refrigerants and the target superheat calculator stay live and free on the web.
LIVE_REFRIGERANTS = None
TARGET_SUPERHEAT_LIVE = True  # same question for the fixed-orifice target superheat calculator (Pro in the app)

HUB = "hvac/index.html"
MAIN_CALC = "hvac/superheat-subcooling-calculator.html"
PT_INDEX = "hvac/pt-chart/index.html"
CMP_INDEX = "hvac/compare/index.html"
TSH = "hvac/target-superheat-calculator.html"
BUBBLE_DEW = "hvac/bubble-point-vs-dew-point.html"
CHARGE_454B = "hvac/how-to-charge-r-454b-by-subcooling.html"

PURE = {"R-32", "R-22", "R-134a", "R-1234yf", "R-290", "R-600a", "R-744", "R-717", "R-12"}
PAIRS = [("R-454B", "R-410A"), ("R-32", "R-410A"), ("R-454B", "R-32"), ("R-407C", "R-22"), ("R-448A", "R-404A"),
         ("R-449A", "R-404A"), ("R-448A", "R-449A"), ("R-513A", "R-134a")]

# Example operating points for the worked examples: (evaporator saturation °F, condenser saturation °F, label).
# They are examples to show the arithmetic, not targets.
PROFILES = {
    "ac": (40, 110, "a comfort-cooling example"),
    "mt": (20, 105, "a medium-temperature refrigeration example"),
    "lt": (-10, 105, "a low-temperature refrigeration example"),
    "co2": (20, 70, "a subcritical CO2 example"),
}
PROFILE_OF = {
    "R-410A": "ac", "R-454B": "ac", "R-32": "ac", "R-22": "ac", "R-407C": "ac", "R-427A": "ac", "R-1234yf": "ac",
    "R-134a": "mt", "R-513A": "mt", "R-409A": "mt", "R-290": "mt", "R-600a": "mt", "R-717": "mt", "R-12": "mt",
    "R-404A": "lt", "R-507A": "lt", "R-448A": "lt", "R-449A": "lt", "R-452A": "lt", "R-407A": "lt", "R-408A": "lt",
    "R-744": "co2",
}


def slug(rid):
    return rid.lower()


def pt_path(rid):
    return f"hvac/pt-chart/{slug(rid)}.html"


def sh_path(rid):
    return f"hvac/superheat-calculator/{slug(rid)}.html"


def cmp_path(a, c):
    return f"hvac/compare/{slug(a)}-vs-{slug(c)}.html"


# ---------- PT maths, the same as assets/calc.js ----------

def cell_psia(p):
    """Absolute pressure of a printed cell: psig, or negative inches of mercury below one atmosphere."""
    return ATM + p if p >= 0 else ATM + p * INHG


def _inv(f):
    return 1 / (f + 459.67)


def temp_at_psia(curve, psia):
    ps = curve["psig"]
    if psia <= 0 or psia < cell_psia(ps[0]) - 1e-9 or psia > cell_psia(ps[-1]) + 1e-9:
        return None
    lp = math.log(psia)
    for i in range(len(ps) - 1):
        p0, p1 = math.log(cell_psia(ps[i])), math.log(cell_psia(ps[i + 1]))
        if lp <= p1 + 1e-12 or i == len(ps) - 2:
            t0 = curve["startF"] + i * STEP
            f = 0 if p1 == p0 else (lp - p0) / (p1 - p0)
            return 1 / (_inv(t0) + (_inv(t0 + STEP) - _inv(t0)) * f) - 459.67
    return None


def psia_at(curve, temp_f):
    end = curve["startF"] + STEP * (len(curve["psig"]) - 1)
    if temp_f < curve["startF"] - 1e-9 or temp_f > end + 1e-9:
        return None
    i = min(int(math.floor((temp_f - curve["startF"]) / STEP)), len(curve["psig"]) - 2)
    t0 = curve["startF"] + i * STEP
    p0, p1 = math.log(cell_psia(curve["psig"][i])), math.log(cell_psia(curve["psig"][i + 1]))
    f = (_inv(temp_f) - _inv(t0)) / (_inv(t0 + STEP) - _inv(t0))
    return math.exp(p0 + (p1 - p0) * f)


def curve(r, phase):
    """Superheat reads the dew curve, subcooling the bubble curve; single-column refrigerants use one curve."""
    return r["dew"] if phase == "dew" and r["dew"] else r["bubble"]


def sat_temp(r, phase, psig):
    return temp_at_psia(curve(r, phase), psig + ATM)


def trange(r):
    """Temperatures covered by both columns."""
    cs = [r["bubble"]] + ([r["dew"]] if r["dew"] else [])
    return max(c["startF"] for c in cs), min(c["startF"] + STEP * (len(c["psig"]) - 1) for c in cs)


def printed(r, phase, t):
    """The cell printed in the source chart at a 5 °F grid temperature, or None outside the column."""
    c = curve(r, phase)
    i, rem = divmod(t - c["startF"], STEP)
    return c["psig"][i] if rem == 0 and 0 <= i < len(c["psig"]) else None


def cell_text(p):
    return f"{abs(p):.1f}″ Hg vacuum" if p < 0 else f"{p:.1f} psig"


def f_to_c(f):
    return (f - 32) * 5 / 9


def glide(r):
    """Dew minus bubble temperature at one pressure, read off this chart: (at a 40 °F dew point, at a 105 °F bubble
    point). None for single-column refrigerants; an item is None where the chart does not reach."""
    if not r["dew"]:
        return None
    out = []
    for phase, t in (("dew", 40), ("bubble", 105)):
        p = psia_at(curve(r, phase), t)
        other = temp_at_psia(curve(r, "bubble" if phase == "dew" else "dew"), p) if p else None
        out.append(None if other is None else abs(t - other))
    return tuple(out)


def example(r):
    """Worked superheat and subcooling readings at the refrigerant's example operating point."""
    evap, cond, label = PROFILES[PROFILE_OF[r["id"]]]
    p_s = round(psia_at(curve(r, "dew"), evap) - ATM)
    sat_s = sat_temp(r, "dew", p_s)
    line_s = round(sat_s) + 12
    p_l = round(psia_at(r["bubble"], cond) - ATM)
    sat_l = sat_temp(r, "bubble", p_l)
    line_l = round(sat_l) - 10
    return {"label": label, "p_s": p_s, "sat_s": sat_s, "line_s": line_s, "sh": line_s - sat_s,
            "p_l": p_l, "sat_l": sat_l, "line_l": line_l, "sc": sat_l - line_l}


def pressure_rows(r):
    """Round gauge pressures across the working range, for the pressure to saturation temperature table."""
    lo_t, hi_t = trange(r)
    lo = max(0.0, psia_at(curve(r, "dew"), max(lo_t, -40)) - ATM)
    hi = psia_at(r["bubble"], min(hi_t, 130)) - ATM
    ps = []
    for step in (1, 2, 5, 10, 20, 25, 50, 100):
        ps = list(range(int(math.ceil(lo / step)) * step, int(hi) + 1, step))
        if len(ps) <= 16:
            break
    return ps


def is_live(rid):
    return LIVE_REFRIGERANTS is None or rid in LIVE_REFRIGERANTS


def t1(x):
    return f"{x:.1f}"


def neg(x):
    """A value inside a subtraction: negatives go in brackets."""
    return f"({t1(x)})" if x < 0 else t1(x)


# ---------- shared blocks ----------

def hvac_links(b, skip=None):
    links = [(MAIN_CALC, "Superheat & subcooling calculator"), (TSH, "Target superheat (fixed orifice)"),
             (PT_INDEX, "PT charts"), (CMP_INDEX, "Refrigerant comparisons"), (BUBBLE_DEW, "Bubble point vs dew point"),
             (CHARGE_454B, "Charging R-454B by subcooling"), (HUB, "All HVAC tools")]
    return related("More HVAC tools", [l for l in links if l[0] != skip])


def chips(b, path_of, current=None, label=lambda rid: rid):
    links = "".join(f'<a href="{REL}{path_of(rid)}"{" aria-current=page" if rid == current else ""}>{label(rid)}</a>' for rid in b.PT)
    return f'<div class="chips">{links}</div>'


def pair_links(rid):
    return [(cmp_path(a, c), f"{a} vs {c}") for a, c in PAIRS if rid in (a, c)]


def safety_cell(r):
    rid, cls = r["id"], r["safety"]
    words = refdata.SAFETY_WORDS.get(cls, "")
    val = f"{cls} ({words})" if words else cls
    key = refdata.SAFETY_SOURCE.get(rid)
    if key:
        return val, f"ASHRAE Standard 34 class as listed by {src(key)}"
    if rid == "R-717":
        return val, f'ASHRAE Standard 34 class used in the app. {src("snap_industrial")} prints B2 for ammonia.'
    return val, "ASHRAE Standard 34 class"


def glide_text(r):
    g = glide(r)
    if g is None:
        return ("None: a single-component refrigerant has one saturation temperature at each pressure." if r["id"] in PURE
                else "The source chart prints one pressure column, used for both superheat and subcooling.")
    parts = []
    if g[0] is not None:
        parts.append(f"{g[0]:.1f} °F at a 40 °F dew point")
    if g[1] is not None:
        parts.append(f"{g[1]:.1f} °F at a 105 °F bubble point")
    return " and ".join(parts) + " (dew minus bubble temperature at the same pressure, computed from this chart)"


def fact_rows(b, r, with_source=True):
    rid = r["id"]
    val, s = safety_cell(r)
    rows = [("Safety class", val, s)]
    if rid in refdata.COMPOSITION:
        t, k = refdata.COMPOSITION[rid]
        rows.append(("Composition", e(t), src(k)))
    if rid in refdata.GWP:
        v, k, basis = refdata.GWP[rid]
        rows.append(("GWP (100-year)", f"{v} <span class=\"muted\">({e(basis)})</span>", src(k)))
    if rid in refdata.ODP:
        v, k = refdata.ODP[rid]
        rows.append(("Ozone depletion potential", v, src(k)))
    rows.append(("Temperature glide", glide_text(r), ""))
    if rid in refdata.OIL:
        t, k = refdata.OIL[rid]
        rows.append(("Compressor lubricant", e(t), src(k)))
    if rid in refdata.REPLACES:
        t, k = refdata.REPLACES[rid]
        rows.append(("Sold as a replacement for", e(t), src(k)))
    rows.append(("Typical use", e(r["use"]), ""))
    if with_source:
        rows.append(("Pressure data", e(r["source"]), ""))
    return rows


# ---------- PT chart page body (called from build.py) ----------

TYPICAL_F = [70, 80, 90, 95, 105]


def pt_page(b, rid, r):
    path = pt_path(rid)
    two = bool(r["dew"])
    lo, hi = trange(r)
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("PT charts", PT_INDEX), (f"{rid} PT chart", path)])

    def both(t):
        return printed(r, "bubble", t), printed(r, "dew", t)

    hot = next(t for t in (95, 80, 70) if lo <= t <= hi)
    cold = 40 if lo <= 40 <= hi else None
    bh, dh = both(hot)
    if two:
        ans = (f"at {hot} °F, {rid} is {cell_text(bh)} as saturated liquid (bubble point) and {cell_text(dh)} as saturated vapor (dew point)")
        if cold:
            bc, dc = both(cold)
            ans += f"; at {cold} °F it is {cell_text(bc)} and {cell_text(dc)}"
        ans += ". Use the vapor (dew) column for superheat and the liquid (bubble) column for subcooling."
    else:
        ans = f"at {hot} °F, the saturation pressure of {rid} is {cell_text(bh)}"
        if cold:
            ans += f"; at {cold} °F it is {cell_text(both(cold)[0])}"
        ans += ". The chart has one pressure column, used for both superheat and subcooling."

    typ = [t for t in TYPICAL_F if lo <= t <= hi]
    typ_rows = [[f"{t} °F", f"{f_to_c(t):.1f} °C", b.fmt_cell(printed(r, "bubble", t))] + ([b.fmt_cell(printed(r, "dew", t))] if two else [])
                for t in typ]
    typ_head = ["Temperature", "°C"] + (["Liquid (bubble), psig", "Vapor (dew), psig"] if two else ["Pressure, psig"])
    typ_html = (f'<section><h2>{rid} pressure at {", ".join(str(t) for t in typ[:-1])} and {typ[-1]} °F</h2>'
                f'<p class="muted">Saturation pressure at common outdoor and condensing temperatures, straight from the chart below.</p>'
                f'{table(typ_head, typ_rows)}</section>')

    safety_note = b.SAFETY_NOTES.get(r["safety"], "")
    glide_p = (f"<p>{rid} is a zeotropic blend with temperature glide, so the chart has two columns: use the <b>vapor (dew)</b> column "
               "for superheat and the <b>liquid (bubble)</b> column for subcooling.</p>") if two else ""
    cmp = pair_links(rid)
    cmp_html = ("<p>Compare: " + " · ".join(f'<a href="{REL}{p}">{t}</a>' for p, t in cmp) + "</p>") if cmp else ""
    cta = (f'<p class="btns"><a class="btn" href="{REL}{sh_path(rid)}">{rid} superheat &amp; subcooling calculator</a>'
           f'<button type="button" class="btn ghost" data-print>Print this chart</button></p>')

    vac = any(p < 0 for c in (r["bubble"], r["dew"]) if c for p in c["psig"])
    items = [(f"What is the pressure of {rid} at {hot} °F?",
              (f"{cell_text(bh)} as saturated liquid (bubble point) and {cell_text(dh)} as saturated vapor (dew point), from the {e(r['source'])}."
               if two else f"{cell_text(bh)} saturation pressure, from the {e(r['source'])}."))]
    if cold:
        bc, dc = both(cold)
        items.append((f"What is the pressure of {rid} at {cold} °F?",
                      f"{cell_text(bc)} liquid (bubble) and {cell_text(dc)} vapor (dew)." if two else f"{cell_text(bc)}."))
    if two:
        g = glide(r)
        gtxt = f" For {rid} the two differ by about {g[0]:.1f} °F at a 40 °F dew point." if g and g[0] is not None else ""
        items.append((f"How do I read the bubble and dew columns for {rid}?",
                      "A blend boils over a range of temperatures at one pressure. The bubble point is where the liquid starts to boil and "
                      "the dew point is where the last liquid has boiled off. Read the suction pressure in the vapor (dew) column to get the "
                      "saturation temperature for superheat, and the liquid-line pressure in the liquid (bubble) column for subcooling."
                      f"{gtxt} <a href=\"{REL}{BUBBLE_DEW}\">More on bubble and dew points</a>."))
    else:
        items.append((f"Why does the {rid} chart have one pressure column?",
                      (f"{rid} is a single-component refrigerant, so it boils and condenses at one temperature for each pressure."
                       if rid in PURE else
                       f"The source chart prints a single column for {rid}, and the same value is used for superheat and subcooling.")))
    if vac:
        items.append(("Why are some readings in inches of mercury?",
                      "Below atmospheric pressure a gauge reads vacuum. The chart prints those cells as inches of mercury (″ Hg) below one atmosphere instead of psig."))
    items.append(("Can I print this chart?",
                  "Yes. Use the Print button: the page prints as a clean table without the menus, with the source and the check date at the bottom."))
    items.append(("Where does the data come from?",
                  f"{e(r['source'])}, copied cell for cell every 5 °F." + (" Converted from absolute pressure (psia) to psig." if r["bubble"].get("converted") else "")
                  + " The calculator interpolates between the printed points along the vapor-pressure curve."))
    faq_html, faq_ld = b.faq(items)

    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">PT chart · ASHRAE {r["safety"]}</div>
<h1>{rid} PT Chart</h1>
<p class="lead">{rid} pressure–temperature chart in psig and °F/°C. {e(r["use"])}.{safety_note}</p>
<p class="answer"><strong>Quick answer:</strong> {ans}</p></div>
{byline(f"Every pressure on this page is a cell of the {e(r['source'])}.")}
{cta}
{typ_html}
<section><h2>{rid} at a glance</h2>{facts(fact_rows(b, r))}{cmp_html}</section>
<section class="fulltable"><h2>Full {rid} pressure–temperature table</h2>
<div class="prose">{glide_p}<p>Vacuum readings are shown in inches of mercury (″ Hg) below atmospheric pressure.</p></div>
{b.pt_table(r)}
<p class="note">Source: {e(r["source"])}.{" Converted from absolute pressure (psia) to psig." if r["bubble"].get("converted") else ""} {HVAC_NOTE}</p>
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p></section>
{b.promo("hvac-charge", "pt-" + slug(rid), f"Look up {rid} offline in the field and get superheat, subcooling and a charge call in seconds.")}
{faq_html}
<section><h2>Other refrigerants</h2>{b.chips(rid)}</section>
{hvac_links(b, PT_INDEX)}
"""
    ld = dataset_ld(b, path, f"{rid} pressure-temperature chart",
                    f"Saturation pressure of {rid} every 5 °F from {lo} °F to {hi} °F in psig"
                    + (", with separate liquid (bubble) and vapor (dew) columns." if two else "."),
                    r["source"],
                    [("Saturation temperature", "°F")] + ([("Bubble point pressure", "psig"), ("Dew point pressure", "psig")] if two else [("Saturation pressure", "psig")]))
    b.shell(path, f"{rid} PT Chart: Pressure Temperature Chart (psig, °F, °C)",
            f"{rid} pressure-temperature chart from {lo} °F to {hi} °F in psig with °C.{' Bubble and dew columns for the glide.' if two else ''} "
            f"Pressures at 70 to 105 °F, safety class and GWP with sources. Free, printable.",
            body, "t-hvac", None, [ld, crumb_ld, faq_ld], JS)


# ---------- superheat and subcooling calculator per refrigerant ----------

def sh_page(b, rid):
    r = b.PT[rid]
    path = sh_path(rid)
    two = bool(r["dew"])
    live = is_live(rid)
    ex = example(r)
    dew_name = "dew point" if two else "saturation temperature"
    bub_name = "bubble point" if two else "saturation temperature"
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("Superheat & subcooling", MAIN_CALC), (rid, path)])

    ans = (f"with {rid}, superheat = suction line temperature − {dew_name} at the suction pressure, and subcooling = {bub_name} at the "
           f"liquid pressure − liquid line temperature. Example: {ex['p_s']} psig on the suction side is {t1(ex['sat_s'])} °F saturated"
           f"{' vapor' if two else ''}, so a {ex['line_s']} °F suction line has {t1(ex['sh'])} °F of superheat.")

    calc = ""
    scripts = JS
    if live:
        calc = f"""
<div class="calc card">
<div class="fields">
<div class="full"><div class="seg" id="mode" role="group" aria-label="Measurement">
<button data-v="sh" aria-pressed="true">Superheat</button><button data-v="sc" aria-pressed="false">Subcooling</button></div></div>
<input type="hidden" id="ref" value="{rid}">
<div><label for="p" id="p-label">Suction pressure <small>(psig)</small></label><input id="p" inputmode="decimal" value="{ex['p_s']}"></div>
<div><label for="t" id="t-label">Suction line temp <small>(°F)</small></label><input id="t" inputmode="decimal" value="{ex['line_s']}"></div>
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
<div class="full"><h2 style="margin:0">{rid} PT lookup</h2></div>
<div class="full"><div class="seg" id="ptmode" role="group" aria-label="Lookup direction">
<button data-v="p2t" aria-pressed="true">Pressure → temp</button><button data-v="t2p" aria-pressed="false">Temp → pressure</button></div></div>
<div class="full"><label for="pt-in" id="pt-in-label">Pressure <small>(psig)</small></label><input id="pt-in" inputmode="decimal" value="{ex['p_s']}"></div>
</div>
<div class="result"><div class="eyebrow">Saturation</div><div class="rows" id="pt-out"></div></div>
</section>
"""
        data = json.dumps({rid: r}, separators=(",", ":"))
        preset = json.dumps({"sh": [ex["p_s"], ex["line_s"]], "sc": [ex["p_l"], ex["line_l"]]})
        scripts = (f"<script>window.PT_DATA = {data};window.HVAC_EXAMPLE = {preset};</script>"
                   f'<script src="{REL}assets/calc.js"></script>' + JS)

    sh_steps = [
        f"Suction (low-side) gauge pressure: {ex['p_s']} psig.",
        f"Saturation temperature at {ex['p_s']} psig in the {'vapor (dew) column' if two else 'chart'}: {t1(ex['sat_s'])} °F.",
        f"Suction line temperature near the service valve: {ex['line_s']} °F.",
        f"Superheat = {ex['line_s']} − {neg(ex['sat_s'])} = {t1(ex['sh'])} °F.",
    ]
    sc_steps = [
        f"Liquid (high-side) gauge pressure: {ex['p_l']} psig.",
        f"Saturation temperature at {ex['p_l']} psig in the {'liquid (bubble) column' if two else 'chart'}: {t1(ex['sat_l'])} °F.",
        f"Liquid line temperature near the service valve: {ex['line_l']} °F.",
        f"Subcooling = {t1(ex['sat_l'])} − {ex['line_l']} = {t1(ex['sc'])} °F.",
    ]
    rows = []
    for p in pressure_rows(r):
        d, bb = sat_temp(r, "dew", p), sat_temp(r, "bubble", p)
        if two:
            rows.append([f"{p}", "–" if d is None else t1(d), "–" if bb is None else t1(bb),
                         "–" if d is None or bb is None else t1(d - bb)])
        else:
            rows.append([f"{p}", "–" if bb is None else t1(bb), "–" if bb is None else t1(f_to_c(bb))])
    head = (["Pressure, psig", "Dew point, °F (for superheat)", "Bubble point, °F (for subcooling)", "Glide, °F"] if two
            else ["Pressure, psig", "Saturation temperature, °F", "°C"])
    guide = guides.guide(f"{rid} worked examples and saturation table", [
        f"<p>The readings below are {ex['label']}. They show the arithmetic; they are not charging targets.</p>",
        guides.example(f"{rid} superheat", sh_steps, f"Result: {t1(ex['sh'])} °F of superheat."),
        guides.example(f"{rid} subcooling", sc_steps, f"Result: {t1(ex['sc'])} °F of subcooling."),
        guides.table(f"{rid} saturation temperature by gauge pressure", head, rows,
                     f"Interpolated between the 5 °F points of the {e(r['source'])}, the same way the calculator does it. "
                     f'The full table by temperature is on the <a href="{REL}{pt_path(rid)}">{rid} PT chart</a>.'),
    ])

    special = ""
    if rid == "R-744":
        special = ("<p>The R-744 table ends at 85 °F, just below the critical point of CO2 (87.8 °F). Above it there is no saturation temperature, "
                   "so superheat and subcooling in this sense apply only to subcritical operation.</p>")
    target = f"""<section class="prose"><h2>What should {rid} superheat and subcooling be?</h2>
<p>There is no single correct number for a refrigerant. The target belongs to the equipment: a fixed-orifice (piston) system is charged to a
target superheat from the manufacturer's charging table (<a href="{REL}{TSH}">target superheat calculator</a>), and a TXV or EEV system to the
target subcooling on the unit's data plate. Always use the manufacturer's numbers for the unit in front of you.</p>
{special}{f"<p>{b.SAFETY_NOTES[r['safety']].strip()}</p>" if r["safety"] in b.SAFETY_NOTES else ""}</section>"""

    items = [
        (f"How do I calculate superheat for {rid}?",
         f"Convert the suction pressure to the {'dew point (vapor column)' if two else 'saturation temperature'} with the {rid} PT chart and subtract it "
         f"from the suction line temperature. Example: {ex['p_s']} psig is {t1(ex['sat_s'])} °F, and a {ex['line_s']} °F line gives {t1(ex['sh'])} °F of superheat."),
        (f"How do I calculate subcooling for {rid}?",
         f"Convert the liquid pressure to the {'bubble point (liquid column)' if two else 'saturation temperature'} and subtract the liquid line temperature. "
         f"Example: {ex['p_l']} psig is {t1(ex['sat_l'])} °F, and a {ex['line_l']} °F liquid line gives {t1(ex['sc'])} °F of subcooling."),
        (f"What is the saturation temperature of {rid} at {ex['p_s']} psig?",
         (f"{t1(ex['sat_s'])} °F dew point (vapor) and {t1(sat_temp(r, 'bubble', ex['p_s']))} °F bubble point (liquid)." if two and sat_temp(r, "bubble", ex["p_s"]) is not None
          else f"{t1(ex['sat_s'])} °F ({t1(f_to_c(ex['sat_s']))} °C).")),
    ]
    if two:
        g = glide(r)
        items.append((f"Do I use the bubble or the dew column for {rid}?",
                      f"Dew (vapor) for superheat, bubble (liquid) for subcooling. {rid} is a blend with glide: "
                      f"{glide_text(r).split(' (')[0]}. Using the wrong column shifts the result by that much."))
    items.append((f"What superheat or subcooling should a {rid} system have?",
                  "It depends on the equipment, not on the refrigerant alone. Use the target superheat from the manufacturer's charging table for a "
                  "fixed-orifice system, or the target subcooling on the data plate for a TXV or EEV system."))
    items.append(("Where does the data come from?",
                  f"{e(r['source'])}. Between the printed 5 °F points the calculator interpolates along the vapor-pressure curve."))
    faq_html, faq_ld = b.faq(items)

    h1 = f"{rid} Superheat &amp; Subcooling Calculator" if live else f"{rid} Superheat &amp; Subcooling: Worked Examples and Chart"
    lead = (f"Enter gauge pressure and line temperature for {rid}. Saturation comes from the published {rid} PT chart"
            + (", with the dew point for superheat and the bubble point for subcooling." if two else "."))
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Free HVAC tool · ASHRAE {r["safety"]}</div>
<h1>{h1}</h1>
<p class="lead">{lead}</p>
<p class="answer"><strong>Quick answer:</strong> {ans}</p></div>
{calc}
{guide}
{target}
{b.promo("hvac-charge", "sh-" + slug(rid), f"{rid} on your phone, offline on the roof: superheat, subcooling, piston target superheat and an add/recover call.")}
<section><h2>Other refrigerants</h2>{chips(b, sh_path, rid)}</section>
{hvac_links(b)}
{faq_html}
<p class="note">{HVAC_NOTE}</p>
"""
    title = (f"{rid} Superheat & Subcooling Calculator | Free, with PT Lookup" if live
             else f"{rid} Superheat & Subcooling: Worked Examples and Saturation Chart")
    desc = (f"Free {rid} superheat and subcooling calculator: enter gauge pressure and line temperature. "
            f"Saturation from the published {rid} PT chart{', dew for superheat and bubble for subcooling' if two else ''}, "
            "with worked examples and a pressure table.")
    lds = ([b.webapp_ld(f"{rid} Superheat & Subcooling Calculator", path, desc)] if live else [article_ld(b, path, plain(h1), desc)]) + [crumb_ld, faq_ld]
    b.shell(path, title, desc, body, "t-hvac", "hvac" if live else None, lds, scripts)


# ---------- comparisons ----------

CMP_TEMPS = [-40, -20, 0, 20, 40, 50, 70, 80, 90, 95, 105, 115, 130]

PAIR_NOTES = {
    ("R-454B", "R-410A"): (
        f"R-454B is not a top-off or retrofit refrigerant for R-410A equipment. Chemours' R-454B guide says A2L refrigerants are for new "
        f"equipment only ({src('chemours_pt')}), and Arkema lists R-454B as an R-410A replacement for new equipment ({src('arkema_digest')}). "
        f"York's R-454B manual has the outdoor unit, indoor coil and metering device replaced together when an R-410A system is replaced ({src('york_yh9')})."),
    ("R-32", "R-410A"): (
        f"Arkema lists R-32 as a replacement for R-410A in new equipment ({src('arkema_digest')}). It is an A2L refrigerant, and Chemours' guide "
        f"states that A2L refrigerants are for new equipment only, not for retrofits ({src('chemours_pt')})."),
    ("R-454B", "R-32"): (
        f"Both are A2L refrigerants that Arkema lists as R-410A replacements for new equipment ({src('arkema_digest')}). They are not "
        "interchangeable: a unit is built, listed and charged for one of them, named on its data plate."),
    ("R-407C", "R-22"): (
        f"Arkema lists R-407C as a replacement and retrofit refrigerant for R-22 and says POE lubricant must be used with it ({src('arkema_digest')})."),
    ("R-448A", "R-404A"): (
        f"Arkema describes R-448A as designed to replace R-404A, R-507A, R-22 and the R-407 series, typically with POE oil ({src('arkema_digest')})."),
    ("R-449A", "R-404A"): (
        f"Arkema describes R-449A as designed to replace R-404A, R-507A, R-22 and the R-407 series, typically with POE oil ({src('arkema_digest')})."),
    ("R-448A", "R-449A"): (
        f"Arkema describes both as designed to replace R-404A, R-507A, R-22 and the R-407 series ({src('arkema_digest')}). They are different "
        "blends: charge the one named on the equipment's data plate or retrofit label, and do not top off one with the other."),
    ("R-513A", "R-134a"): (
        f"Arkema lists R-513A as a replacement for R-134a, except in automotive AC, typically with POE oil ({src('arkema_digest')})."),
}


def cmp_data(b, a, c):
    ra, rc = b.PT[a], b.PT[c]
    lo = max(trange(ra)[0], trange(rc)[0])
    hi = min(trange(ra)[1], trange(rc)[1])
    temps = [t for t in CMP_TEMPS if lo <= t <= hi]

    def rows(phase):
        out = []
        for t in temps:
            pa, pc = printed(ra, phase, t), printed(rc, phase, t)
            out.append((t, pa, pc, cell_psia(pa) - cell_psia(pc)))
        return out

    # The same gauge reading on both charts: how far apart the saturation temperatures are.
    p_s = round(psia_at(curve(rc, "dew"), 40) - ATM)
    p_l = round(psia_at(rc["bubble"], 105) - ATM)
    same = {"p_s": p_s, "a_s": sat_temp(ra, "dew", p_s), "c_s": sat_temp(rc, "dew", p_s),
            "p_l": p_l, "a_l": sat_temp(ra, "bubble", p_l), "c_l": sat_temp(rc, "bubble", p_l)}
    return {"temps": temps, "vapor": rows("dew"), "liquid": rows("bubble"), "same": same,
            "two": bool(ra["dew"] or rc["dew"])}


def cmp_page(b, a, c):
    ra, rc = b.PT[a], b.PT[c]
    path = cmp_path(a, c)
    d = cmp_data(b, a, c)
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("Comparisons", CMP_INDEX), (f"{a} vs {c}", path)])

    def at(rows, t):
        return next(x for x in rows if x[0] == t)

    v40, l105 = at(d["vapor"], 40), at(d["liquid"], 105)
    pct = abs(l105[3]) / l105[2] * 100
    word = "lower" if v40[3] < 0 and l105[3] < 0 else "higher" if v40[3] > 0 and l105[3] > 0 else "close to, but not the same as,"
    than = f"{word} pressure than" if word in ("lower", "higher") else f"pressures {word}"
    ans = (f"at the same temperatures {a} runs at {than} {c}. As saturated vapor at 40 °F, {a} is {cell_text(v40[1])} against {cell_text(v40[2])} "
           f"({v40[3]:+.1f} psi). As saturated liquid at 105 °F, {a} is {cell_text(l105[1])} against {cell_text(l105[2])} "
           f"({l105[3]:+.1f} psi, about {pct:.0f} % {'lower' if l105[3] < 0 else 'higher'}).")

    def tbl(rows):
        return table(["Temperature", "°C", f"{a}, psig", f"{c}, psig", "Difference, psi"],
                     [[f"{t} °F", f"{f_to_c(t):.1f}", b.fmt_cell(pa), b.fmt_cell(pc), f"{diff:+.1f}"] for t, pa, pc, diff in rows])

    if d["two"]:
        tables = (f"<h3>Suction side: saturated vapor (dew point) pressure</h3>{tbl(d['vapor'])}"
                  f"<h3>Liquid line: saturated liquid (bubble point) pressure</h3>{tbl(d['liquid'])}")
    else:
        tables = f"<h3>Saturation pressure</h3>{tbl(d['liquid'])}"

    s = d["same"]
    same_rows = [
        ["Suction gauge", f"{s['p_s']} psig", f"{t1(s['a_s'])} °F", f"{t1(s['c_s'])} °F", f"{abs(s['a_s'] - s['c_s']):.1f} °F"],
        ["Liquid gauge", f"{s['p_l']} psig", f"{t1(s['a_l'])} °F", f"{t1(s['c_l'])} °F", f"{abs(s['a_l'] - s['c_l']):.1f} °F"],
    ]
    same_html = (f"<h3>Same gauge reading, different saturation temperature</h3>"
                 + table(["Reading", "Pressure", f"{a} saturation", f"{c} saturation", "Error with the wrong chart"], same_rows)
                 + f'<p class="note">Suction readings use the vapor (dew) column and liquid readings the liquid (bubble) column. '
                   f"The last column is how far off superheat or subcooling would be if the {c} chart were used on {a}, or the other way round.</p>")

    fa, fc = dict((l, (v, sc)) for l, v, sc in fact_rows(b, ra)), dict((l, (v, sc)) for l, v, sc in fact_rows(b, rc))
    labels = [l for l, _, _ in fact_rows(b, ra)] + [l for l, _, _ in fact_rows(b, rc) if l not in fa]

    def cell(f, l):
        if l not in f:
            return "<td>–</td>"
        v, sc = f[l]
        return f"<td>{v}{f'<small>{sc}</small>' if sc else ''}</td>"

    side = ('<div class="tablewrap facts cmp"><table><thead><tr><th></th>'
            f"<th>{a}</th><th>{c}</th></tr></thead><tbody>"
            + "".join(f'<tr><th scope="row">{l}</th>{cell(fa, l)}{cell(fc, l)}</tr>' for l in labels) + "</tbody></table></div>")

    note = PAIR_NOTES[(a, c)]
    items = [
        (f"Is {a} higher or lower pressure than {c}?",
         f"At 105 °F saturated liquid {a} is {cell_text(l105[1])} and {c} is {cell_text(l105[2])}, a difference of {l105[3]:+.1f} psi. "
         f"At 40 °F saturated vapor it is {cell_text(v40[1])} against {cell_text(v40[2])} ({v40[3]:+.1f} psi)."),
        (f"Can I use the {c} PT chart for {a}?",
         f"No. At {s['p_s']} psig on the suction side the two charts give {t1(s['a_s'])} °F for {a} and {t1(s['c_s'])} °F for {c}, so superheat would be off by "
         f"{abs(s['a_s'] - s['c_s']):.1f} °F. At {s['p_l']} psig on the liquid line subcooling would be off by {abs(s['a_l'] - s['c_l']):.1f} °F. Use the chart for the refrigerant in the system."),
        (f"Which has more temperature glide, {a} or {c}?",
         f"{a}: {glide_text(ra)[0].lower() + glide_text(ra)[1:]}. {c}: {glide_text(rc)[0].lower() + glide_text(rc)[1:]}."),
        (f"Can {a} replace {c} in an existing system?",
         f"{note} A changeover follows the refrigerant maker's and the equipment maker's instructions; this page only compares published pressure data."),
    ]
    faq_html, faq_ld = b.faq(items)

    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Refrigerant comparison</div>
<h1>{a} vs {c}: pressures, glide and safety class</h1>
<p class="lead">The published PT charts of {a} and {c} side by side at the same temperatures, with glide, safety class and GWP.</p>
<p class="answer"><strong>Quick answer:</strong> {ans}</p></div>
{byline(f"Pressures are cells of the {e(ra['source'])}" + (f" and the {e(rc['source'])}" if rc["source"] != ra["source"] else "") + "; differences are computed from them.")}
{printbar("Print this comparison")}
<section class="guide"><h2>{a} and {c} pressure at the same temperature</h2>
<p class="muted">Difference = {a} minus {c}, in psi. Vacuum cells are in inches of mercury.</p>
{tables}
{same_html}</section>
<section><h2>{a} and {c} side by side</h2>{side}</section>
<section class="prose"><h2>Can {a} replace {c}?</h2><p>{note}</p>
<p>A changeover follows the refrigerant maker's and the equipment maker's instructions. This page only compares the published pressure data.</p></section>
<section><h2>Calculators and full charts</h2><div class="chips">
<a href="{REL}{sh_path(a)}">{a} superheat &amp; subcooling</a><a href="{REL}{sh_path(c)}">{c} superheat &amp; subcooling</a>
<a href="{REL}{pt_path(a)}">{a} PT chart</a><a href="{REL}{pt_path(c)}">{c} PT chart</a></div></section>
{b.promo("hvac-charge", f"cmp-{slug(a)}-{slug(c)}", f"{a}, {c} and {len(b.PT) - 2} more refrigerants on your phone, offline: superheat, subcooling and PT lookup.")}
{faq_html}
{related("Other comparisons", [(cmp_path(x, y), f"{x} vs {y}") for x, y in PAIRS if (x, y) != (a, c)])}
{hvac_links(b, CMP_INDEX)}
<p class="note">{HVAC_NOTE}</p>
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p>
"""
    desc = (f"{a} vs {c}: saturation pressures at the same temperatures from the published PT charts, the difference in psi, "
            f"temperature glide, ASHRAE safety class and GWP, with sources.")
    ld = dataset_ld(b, path, f"{a} vs {c} pressure comparison", desc, ra["source"],
                    [("Saturation temperature", "°F"), (f"{a} pressure", "psig"), (f"{c} pressure", "psig"), ("Pressure difference", "psi")])
    b.shell(path, f"{a} vs {c}: Pressure Difference, Glide and Safety Class", desc, body, "t-hvac", None, [ld, crumb_ld, faq_ld], JS)


def cmp_index(b):
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("Comparisons", CMP_INDEX)])
    cards = ""
    for a, c in PAIRS:
        d = cmp_data(b, a, c)
        row = next(x for x in d["liquid"] if x[0] == 105)
        cards += (f'<a class="card" href="{REL}{cmp_path(a, c)}"><span class="tag">{b.PT[a]["safety"]} vs {b.PT[c]["safety"]}</span>'
                  f"<h3>{a} vs {c}</h3><p>At 105 °F liquid: {cell_text(row[1])} against {cell_text(row[2])} ({row[3]:+.1f} psi).</p></a>")
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Refrigerant comparisons</div><h1>Refrigerant comparisons</h1>
<p class="lead">Two refrigerants at the same temperatures: pressure difference, glide, safety class and GWP, from the published PT charts.</p></div>
<div class="grid">{cards}</div>
{hvac_links(b, CMP_INDEX)}
<p class="note">{HVAC_NOTE}</p>
"""
    b.shell(CMP_INDEX, "Refrigerant Comparisons: R-454B vs R-410A, R-32 vs R-410A and more",
            "Side-by-side refrigerant comparisons from published PT charts: R-454B vs R-410A, R-32 vs R-410A, R-407C vs R-22, R-448A and R-449A vs R-404A, R-513A vs R-134a.",
            body, "t-hvac", None, [crumb_ld])


# ---------- target superheat (fixed orifice) ----------

def load_tsh(b):
    """The charging table exactly as the app holds it (hvac-charge-app charge.dart, TargetSuperheatTable)."""
    text = (b.ROOT / "hvac-charge-app/lib/feature/engine/charge.dart").read_text()
    block = text[text.index("class TargetSuperheatTable"):text.index("static TargetSuperheat lookup")]

    def ints(name):
        return [int(x) for x in re.search(rf"{name} = \[([^\]]+)\]", block).group(1).split(",") if x.strip()]

    rows = re.findall(r"^\s*\[([^\[\]]+)\],?\s*$", block.split("superheatF = [", 1)[1], re.M)
    cells = [[None if x.strip() == "null" else int(x) for x in row.split(",") if x.strip()] for row in rows]
    return {"outdoorF": ints("outdoorF"), "wetBulbF": ints("wetBulbF"), "superheatF": cells}


def _bracket(axis, x):
    for i in range(len(axis) - 1):
        if x <= axis[i + 1]:
            return i, i + 1, (x - axis[i]) / (axis[i + 1] - axis[i])
    return len(axis) - 2, len(axis) - 1, 1.0


def tsh_lookup(tbl, outdoor, wet_bulb):
    """('value', °F), ('none', None) where the table has a dash, or ('range', None) outside it. Mirrors the app."""
    od, wb, cells = tbl["outdoorF"], tbl["wetBulbF"], tbl["superheatF"]
    if outdoor < od[0] or outdoor > od[-1] or wet_bulb < wb[0] or wet_bulb > wb[-1]:
        return "range", None
    r0, r1, fr = _bracket(od, outdoor)
    c0, c1, fc = _bracket(wb, wet_bulb)
    corners = [cells[r0][c0], cells[r0][c1], cells[r1][c0], cells[r1][c1]]
    needed = [(1 - fr) * (1 - fc) > 1e-9, (1 - fr) * fc > 1e-9, fr * (1 - fc) > 1e-9, fr * fc > 1e-9]
    if any(n and v is None for n, v in zip(needed, corners)):
        return "none", None
    v = [x or 0 for x in corners]
    top = v[0] + (v[1] - v[0]) * fc
    bottom = v[2] + (v[3] - v[2]) * fc
    return "value", top + (bottom - top) * fr


TSH_EXAMPLE = (92, 65)  # outdoor dry bulb, indoor wet bulb: between cells on both axes


def tsh_page(b):
    path = TSH
    tbl = load_tsh(b)
    od, wb, cells = tbl["outdoorF"], tbl["wetBulbF"], tbl["superheatF"]
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("Target superheat", path)])
    ex_od, ex_wb = TSH_EXAMPLE
    _, ex_v = tsh_lookup(tbl, ex_od, ex_wb)
    r0, r1, _ = _bracket(od, ex_od)
    c0, c1, _ = _bracket(wb, ex_wb)
    _, at95 = tsh_lookup(tbl, 95, 66)
    _, at85 = tsh_lookup(tbl, 85, 66)

    grid = table(["Outdoor °F \\ indoor wet bulb °F"] + [str(x) for x in wb],
                 [[f"{o}"] + ["–" if v is None else str(v) for v in cells[i]] for i, o in enumerate(od)], "tsh")
    calc = ""
    scripts = JS
    if TARGET_SUPERHEAT_LIVE:
        calc = f"""
<div class="calc card">
<div class="fields">
<div><label for="tsh-od">Outdoor dry bulb <small>(°F)</small></label><input id="tsh-od" inputmode="decimal" value="{ex_od}"></div>
<div><label for="tsh-wb">Indoor wet bulb <small>(°F)</small></label><input id="tsh-wb" inputmode="decimal" value="{ex_wb}"></div>
<p class="note full">Outdoor: air entering the condenser. Indoor: wet bulb of the return air entering the evaporator coil.</p>
</div>
<div class="result" aria-live="polite">
<div class="eyebrow">Target superheat</div>
<div class="big" id="tsh-out">–</div>
<div class="rows"><div><span>In kelvin</span><span id="tsh-k">–</span></div>
<div><span>Table cells used</span><span id="tsh-cells">–</span></div></div>
<div id="tsh-msg" class="verdict"></div>
</div>
</div>
"""
        scripts = f"<script>window.TSH_TABLE = {json.dumps(tbl, separators=(',', ':'))};</script>" + JS

    ex = guides.example(f"{ex_od} °F outdoors, {ex_wb} °F indoor wet bulb", [
        f"{ex_od} °F lies between the {od[r0]} °F and {od[r1]} °F rows, and {ex_wb} °F between the {wb[c0]} °F and {wb[c1]} °F columns.",
        f"The four cells around the point are {cells[r0][c0]} and {cells[r0][c1]} °F ({od[r0]} °F row), {cells[r1][c0]} and {cells[r1][c1]} °F ({od[r1]} °F row).",
        f"Interpolating between them on both axes gives {t1(ex_v)} °F.",
    ], f"Result: target superheat of about {t1(ex_v)} °F at the low-side service port.")
    items = [
        ("What is target superheat?",
         "The superheat a fixed-orifice (piston) air conditioner should show at the suction service port when the charge is right. "
         "It changes with the load: the outdoor temperature and the wet bulb of the air entering the indoor coil."),
        ("How do I use the target?",
         "Per the charging procedure in the source document: run the system at least 10 minutes, measure the actual superheat at the suction service "
         f"port and compare it with the table. Higher than the target means the system needs refrigerant; lower means it has too much. "
         f'Work out the actual superheat with the <a href="{REL}{MAIN_CALC}">superheat calculator</a>.'),
        ("What does a dash in the table mean?",
         "The manufacturer gives no superheat target for those conditions, so the charge must not be set by superheat there. Weigh in the charge instead, "
         "or wait for conditions inside the table."),
        ("Does this work for TXV or EEV systems?",
         "No. An expansion valve holds superheat roughly constant, so those systems are charged by subcooling against the target on the unit's data plate."),
        ("Which wet bulb temperature do I use?",
         "The wet bulb of the air entering the indoor (evaporator) coil, measured in the return air close to the unit. The outdoor temperature is the dry bulb of the air entering the condenser."),
        ("Is this table right for my unit?",
         "It is one manufacturer's table, printed for Bryant 563C and 563G split systems. Other units have their own charging charts, often on the unit or in the "
         "installation instructions. Where your unit has its own chart, that chart governs."),
    ]
    faq_html, faq_ld = b.faq(items)
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Free HVAC tool</div>
<h1>Target Superheat Calculator (Fixed Orifice)</h1>
<p class="lead">Target superheat for a fixed-orifice (piston) air conditioner from the outdoor temperature and the indoor wet bulb, read from a manufacturer's superheat charging table.</p>
<p class="answer"><strong>Quick answer:</strong> at 95 °F outdoors and a 66 °F indoor wet bulb the table gives a target superheat of {at95:.0f} °F; at 85 °F outdoors
and the same wet bulb, {at85:.0f} °F. Hotter outdoors means a lower target, more humid return air a higher one.</p></div>
{calc}
<section class="guide"><h2>Superheat charging table</h2>
<p class="muted">Target superheat in °F at the low-side service port. Rows: outdoor dry bulb. Columns: wet bulb of the air entering the indoor coil. A dash means no target: do not charge by superheat there.</p>
{printbar("Print this table")}
{grid}
{ex}
{byline(f"Table values are copied from {src('bryant_tsh')}, the same table the HVAC Charge app uses. Between cells the calculator interpolates on both axes.")}
</section>
<section class="prose"><h2>Before you rely on it</h2>
<p>This is one manufacturer's charging table for specific fixed-orifice units. Your unit's own charging chart and installation instructions come first.
The source document also ties the table to indoor airflow close to the rated value, so check airflow before adjusting the charge.</p></section>
{b.promo("hvac-charge", "target-superheat", "Target superheat, actual superheat and a clear add or recover call in one screen, offline on the roof.")}
{faq_html}
{hvac_links(b, TSH)}
<p class="note">{HVAC_NOTE}</p>
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p>
"""
    desc = ("Free target superheat calculator for fixed-orifice (piston) air conditioners: enter outdoor dry bulb and indoor wet bulb. "
            "Values from a manufacturer's superheat charging table, with the full chart and a worked example.")
    lds = ([b.webapp_ld("Target Superheat Calculator (Fixed Orifice)", path, desc)] if TARGET_SUPERHEAT_LIVE else []) + [
        dataset_ld(b, path, "Target superheat charging table for fixed-orifice air conditioners", desc, refdata.SOURCES["bryant_tsh"][0],
                   [("Outdoor dry bulb temperature", "°F"), ("Indoor wet bulb temperature", "°F"), ("Target superheat", "°F")]), crumb_ld, faq_ld]
    b.shell(path, "Target Superheat Calculator and Chart (Fixed Orifice / Piston)", desc, body, "t-hvac", "tsh", lds, scripts)


# ---------- guide: bubble and dew points ----------

def bubble_dew_page(b):
    path = BUBBLE_DEW
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("Bubble point vs dew point", path)])
    r = b.PT["R-407C"]
    ex = example(r)
    wrong_s = sat_temp(r, "bubble", ex["p_s"])
    wrong_l = sat_temp(r, "dew", ex["p_l"])
    rows = []
    for rid, rr in b.PT.items():
        g = glide(rr)
        if g:
            rows.append([f'<a href="{REL}{pt_path(rid)}">{rid}</a>', "–" if g[0] is None else t1(g[0]), "–" if g[1] is None else t1(g[1])])
    single = ", ".join(rid for rid, rr in b.PT.items() if not rr["dew"])
    items = [
        ("Do I use bubble or dew for superheat?",
         "Dew. Superheat is measured on the suction line, where the refrigerant is vapor, so the saturation temperature comes from the vapor (dew) column."),
        ("Do I use bubble or dew for subcooling?",
         "Bubble. Subcooling is measured on the liquid line, so the saturation temperature comes from the liquid (bubble) column."),
        ("What is temperature glide?",
         "The difference between the dew point and the bubble point of a blend at the same pressure. For R-407C on this site's chart it is about "
         f"{t1(glide(r)[0])} °F at a 40 °F dew point."),
        ("What happens if I use the wrong column?",
         f"The result shifts by the glide. On R-407C at {ex['p_s']} psig the dew point is {t1(ex['sat_s'])} °F and the bubble point {t1(wrong_s)} °F, "
         f"so superheat read from the bubble column would be {t1(ex['sat_s'] - wrong_s)} °F too high."),
        ("Why do some charts have only one column?",
         f"Single-component refrigerants boil at one temperature for each pressure, and for some blends the source chart prints a single column. "
         f"On this site that is {single}."),
    ]
    faq_html, faq_ld = b.faq(items)
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">HVAC guide</div>
<h1>Bubble point vs dew point: how to read a PT chart for a blend</h1>
<p class="lead">Blends such as R-454B, R-407C and R-448A have two pressure columns. Here is which one to use, and how big the error is if you pick the wrong one.</p>
<p class="answer"><strong>Quick answer:</strong> use the <b>dew point</b> (vapor column) for superheat and the <b>bubble point</b> (liquid column) for subcooling.
The gap between them at one pressure is the temperature glide: about {t1(glide(b.PT["R-454B"])[0])} °F for R-454B and {t1(glide(r)[0])} °F for R-407C at a 40 °F dew point.</p></div>
{byline("Glide figures and examples are computed from the PT charts on this site.")}
<section class="prose"><h2>What the two columns mean</h2>
<p>A single-component refrigerant boils at one temperature for a given pressure. A zeotropic blend does not: its components boil off at different rates,
so at one pressure it boils over a range of temperatures.</p>
<ul>
<li><b>Bubble point</b> (saturated liquid): the temperature at which the liquid starts to boil. Chart column: liquid.</li>
<li><b>Dew point</b> (saturated vapor): the temperature at which the last liquid has boiled off, or at which vapor starts to condense. Chart column: vapor.</li>
</ul>
<p>Chemours prints the same rule in the key of its R-454B chart: saturated liquid pressure to calculate subcooling, saturated vapor pressure to calculate superheat ({src("chemours_pt")}).</p></section>
<section class="guide"><h2>Worked example with R-407C</h2>
{guides.example("superheat from the dew column", [
    f"Suction pressure: {ex['p_s']} psig.",
    f"Vapor (dew) column at {ex['p_s']} psig: {t1(ex['sat_s'])} °F. The bubble column at the same pressure reads {t1(wrong_s)} °F, which is the wrong value here.",
    f"Suction line temperature: {ex['line_s']} °F.",
    f"Superheat = {ex['line_s']} − {t1(ex['sat_s'])} = {t1(ex['sh'])} °F. With the bubble column it would come out as {t1(ex['line_s'] - wrong_s)} °F.",
], f"Result: {t1(ex['sh'])} °F of superheat.")}
{guides.example("subcooling from the bubble column", [
    f"Liquid pressure: {ex['p_l']} psig.",
    f"Liquid (bubble) column at {ex['p_l']} psig: {t1(ex['sat_l'])} °F. The dew column reads {t1(wrong_l)} °F.",
    f"Liquid line temperature: {ex['line_l']} °F.",
    f"Subcooling = {t1(ex['sat_l'])} − {ex['line_l']} = {t1(ex['sc'])} °F. With the dew column it would come out as {t1(wrong_l - ex['line_l'])} °F.",
], f"Result: {t1(ex['sc'])} °F of subcooling.")}
{guides.table("Temperature glide of the blends on this site", ["Refrigerant", "Glide at a 40 °F dew point, °F", "Glide at a 105 °F bubble point, °F"], rows,
              "Dew point minus bubble point at the same pressure, computed from each refrigerant's PT chart. A dash means the chart does not reach that point.")}
</section>
{b.promo("hvac-charge", "bubble-dew", "The app picks the right column for you: dew for superheat, bubble for subcooling, for every blend.")}
{faq_html}
{hvac_links(b, BUBBLE_DEW)}
<p class="note">{HVAC_NOTE}</p>
"""
    desc = ("Bubble point vs dew point on a refrigerant PT chart: use dew for superheat and bubble for subcooling. "
            "Worked R-407C example and the temperature glide of common blends, computed from published charts.")
    b.shell(path, "Bubble Point vs Dew Point: Reading a PT Chart for Blends (R-454B, R-407C)", desc, body, "t-hvac", None,
            [article_ld(b, path, "Bubble point vs dew point: how to read a PT chart for a blend", desc), crumb_ld, faq_ld], JS)


# ---------- article: charging R-454B by subcooling ----------

def charge_454b_page(b):
    path = CHARGE_454B
    r = b.PT["R-454B"]
    ex = example(r)
    wrong = sat_temp(r, "dew", ex["p_l"])
    target = 12  # the rating-plate value assumed in the worked example
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB), ("Charging R-454B by subcooling", path)])
    items = [
        ("What subcooling should an R-454B system have?",
         "The value on the outdoor unit's rating plate or charging label. It differs from model to model, so there is no number that fits every R-454B unit."),
        ("Which PT column do I use for R-454B subcooling?",
         f"The liquid (bubble) column. At {ex['p_l']} psig it reads {t1(ex['sat_l'])} °F; the vapor (dew) column reads {t1(wrong)} °F at the same pressure."),
        ("Can I add R-454B as a vapor?",
         "No. R-454B is a blend, and the equipment and refrigerant makers require it to leave the cylinder as liquid."),
        ("Can I top off an R-410A system with R-454B?",
         "No. R-454B is for equipment designed for it. Chemours states that A2L refrigerants are for new equipment only, not for retrofits."),
        ("How long should the system run before I check the charge?",
         "Follow the unit's instructions. Carrier's R-454B heat pump instructions call for at least 15 minutes of operation before checking the charge."),
    ]
    faq_html, faq_ld = b.faq(items)
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">HVAC guide</div>
<h1>How to charge an R-454B system by subcooling</h1>
<p class="lead">The subcooling method for R-454B units with a TXV or EEV, step by step, with the manufacturer documents behind each step.</p>
<p class="answer"><strong>Quick answer:</strong> read the liquid-line pressure, convert it to the saturated liquid (bubble) temperature on the R-454B chart,
subtract the liquid line temperature, and compare the result with the target subcooling on the unit's rating plate. Add or recover refrigerant, as liquid, until it matches.</p></div>
<p class="callout"><strong>The target is on the equipment, not on this page.</strong> Target subcooling, the allowed tolerance and the conditions for charging come from the
rating plate, charging label and installation instructions of the unit you are working on. The numbers below are examples of the arithmetic only.
Refrigerant work requires EPA Section 608 certification in the US, and R-454B is an A2L (mildly flammable) refrigerant with its own handling rules.</p>
{byline("Each step cites the manufacturer document it was read in. The example uses the R-454B PT chart on this site.")}

<section class="prose"><h2>Before you start</h2>
<ul>
<li><b>Confirm the method.</b> Carrier's instructions require the subcooling method for units with a cooling-mode TXV and send you to the rating plate for the
required subcooling ({src("carrier_ph5")}). Lennox puts the target subcooling values on the unit's charging label ({src("lennox_ml13")}).
A fixed-orifice system is charged by superheat instead: see the <a href="{REL}{TSH}">target superheat calculator</a>.</li>
<li><b>A2L precautions.</b> The manufacturers' instructions call for non-sparking tools, a refrigerant detector before and during the work, no open flames or
other ignition sources except while brazing, and never a flame for leak checking ({src("carrier_ph5")}); a well-ventilated work area ({src("lennox_ml13")});
and service equipment rated for R-454B ({src("york_yh9")}). Lennox notes that R-454B cylinders have a ¼″ left-hand flare connection.</li>
<li><b>Conditions.</b> Carrier calls conditions favorable for checking the charge when the outdoor temperature is between 70 °F and 100 °F and the indoor
temperature between 70 °F and 80 °F; outside that range its instructions have the charge weighed in for the line length and checked again later ({src("carrier_ph5")}).
Other makers set their own limits, so read the instructions for your unit.</li>
</ul></section>

<section class="prose"><h2>Steps</h2>
<ol>
<li>Run the system in cooling until it is stable. Carrier specifies at least 15 minutes before checking the charge ({src("carrier_ph5")}).</li>
<li>Read the liquid-line (high-side) pressure at the liquid service valve.</li>
<li>Measure the liquid line temperature close to the same valve, with the probe well insulated from the air.</li>
<li>Convert the pressure to the saturated liquid temperature with the <a href="{REL}{pt_path("R-454B")}">R-454B PT chart</a>. R-454B is a blend, so use the liquid
(bubble) column. Chemours' chart says the same: saturated liquid pressure for subcooling, saturated vapor for superheat ({src("chemours_pt")}).</li>
<li>Subcooling = saturated liquid temperature − liquid line temperature. The <a href="{REL}{sh_path("R-454B")}">R-454B calculator</a> does both steps.</li>
<li>Compare with the target on the rating plate or charging label. Carrier allows a tolerance of ±3 °F around its target ({src("carrier_ph5")}); use the tolerance your unit's instructions give.</li>
<li>Subcooling below the target: add refrigerant. Above the target: recover some. Charge R-454B as liquid only ({src("carrier_llg")}, {src("lennox_ml13")}, {src("chemours_pt")}),
in small steps, and let the system settle again before you take the next reading.</li>
</ol></section>

<section class="guide"><h2>Worked example</h2>
<p>An example of the arithmetic, not a target. Suppose the rating plate of the unit asks for {target} °F of subcooling.</p>
{guides.example("R-454B subcooling", [
    f"Liquid pressure at the service valve: {ex['p_l']} psig.",
    f"Liquid (bubble) column of the R-454B chart at {ex['p_l']} psig: {t1(ex['sat_l'])} °F. (The vapor column reads {t1(wrong)} °F; using it would overstate subcooling by {t1(wrong - ex['sat_l'])} °F.)",
    f"Liquid line temperature: {ex['line_l']} °F.",
    f"Subcooling = {t1(ex['sat_l'])} − {ex['line_l']} = {t1(ex['sc'])} °F.",
    f"Against the {target} °F target that is {abs(ex['sc'] - target):.1f} °F {'over' if ex['sc'] > target else 'under'}, inside a ±3 °F tolerance, so the charge stays as it is.",
], f"Result: {t1(ex['sc'])} °F of subcooling.")}
</section>

<section><h2>R-454B at a glance</h2>{facts(fact_rows(b, r))}
<p>R-454B is not a retrofit for R-410A equipment: Chemours states that A2L refrigerants are for new equipment only ({src("chemours_pt")}).
See <a href="{REL}{cmp_path("R-454B", "R-410A")}">R-454B vs R-410A</a> for the pressure difference.</p></section>
{b.promo("hvac-charge", "charge-454b", "Type the pressure and line temperature; the app reads the R-454B bubble point and shows subcooling against your nameplate target.")}
{faq_html}
{hvac_links(b, CHARGE_454B)}
<p class="note">{HVAC_NOTE}</p>
"""
    desc = ("How to charge an R-454B air conditioner or heat pump by subcooling: the steps, which PT column to use and a worked example, "
            "with manufacturer sources. Targets always come from the unit's rating plate.")
    b.shell(path, "How to Charge an R-454B System by Subcooling (Step by Step)", desc, body, "t-hvac", None,
            [article_ld(b, path, "How to charge an R-454B system by subcooling", desc), crumb_ld, faq_ld], JS)


# ---------- hub ----------

def hub_page(b):
    crumb_html, crumb_ld = crumbs(b, [("Tools", "index.html"), ("HVAC", HUB)])
    cards = [
        (MAIN_CALC, "Calculator", "Superheat & subcooling calculator", "R-410A, R-454B, R-32 and R-22 in one tool, with PT lookup."),
        (TSH, "Calculator", "Target superheat (fixed orifice)", "From outdoor temperature and indoor wet bulb, with the full charging table."),
        (PT_INDEX, "Charts", "Refrigerant PT charts", f"{len(b.PT)} refrigerants, every 5 °F, printable."),
        (CMP_INDEX, "Comparisons", "Refrigerant comparisons", "R-454B vs R-410A, R-32 vs R-410A and more: pressure, glide, safety class."),
        (BUBBLE_DEW, "Guide", "Bubble point vs dew point", "Which column of a blend's PT chart to use, with the size of the error."),
        (CHARGE_454B, "Guide", "Charging R-454B by subcooling", "The steps and the manufacturer documents behind them."),
    ]
    grid = "".join(f'<a class="card" href="{REL}{p}"><span class="tag">{tag}</span><h3>{e(h)}</h3><p>{e(d)}</p></a>' for p, tag, h, d in cards)
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Free HVAC tools</div><h1>HVAC calculators and refrigerant charts</h1>
<p class="lead">Superheat, subcooling, target superheat and PT charts for {len(b.PT)} refrigerants. Every pressure comes from a published manufacturer or NIST table.</p></div>
<div class="grid">{grid}</div>
<section><h2>Superheat &amp; subcooling calculator by refrigerant</h2>{chips(b, sh_path)}</section>
<section><h2>PT chart by refrigerant</h2>{b.chips()}</section>
<section><h2>Comparisons</h2><div class="chips">{"".join(f'<a href="{REL}{cmp_path(a, c)}">{a} vs {c}</a>' for a, c in PAIRS)}</div></section>
{b.promo("hvac-charge", "hvac-hub", f"All {len(b.PT)} refrigerants, piston target superheat and an add/recover call on your phone, offline.")}
<p class="note">{HVAC_NOTE}</p>
"""
    b.shell(HUB, "HVAC Calculators and Refrigerant PT Charts | Free",
            f"Free HVAC tools: superheat and subcooling calculators for {len(b.PT)} refrigerants, target superheat for fixed-orifice systems, PT charts and refrigerant comparisons.",
            body, "t-hvac", None, [crumb_ld])


# Cards in the same shape as build.CALCS (path, tag, title, text, theme), for the home page and llms.txt.
CARDS = [
    (HUB, "HVAC", "All HVAC tools", "Calculators, PT charts, comparisons and guides in one place.", "t-hvac"),
    (TSH, "HVAC", "Target superheat calculator", "Fixed-orifice target from outdoor temperature and indoor wet bulb.", "t-hvac"),
    (CMP_INDEX, "HVAC", "Refrigerant comparisons", "R-454B vs R-410A, R-32 vs R-410A and more.", "t-hvac"),
    (BUBBLE_DEW, "HVAC", "Bubble point vs dew point", "Which PT column to use for a blend.", "t-hvac"),
    (CHARGE_454B, "HVAC", "Charging R-454B by subcooling", "Step by step, with manufacturer sources.", "t-hvac"),
]


def build(b):
    """Everything except the PT chart pages, which build.build_hvac() makes one by one through pt_page()."""
    hub_page(b)
    for rid in b.PT:
        sh_page(b, rid)
    for a, c in PAIRS:
        cmp_page(b, a, c)
    cmp_index(b)
    tsh_page(b)
    bubble_dew_page(b)
    charge_454b_page(b)
