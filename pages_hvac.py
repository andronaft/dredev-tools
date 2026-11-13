"""HVAC reference pages: the superheat and subcooling calculator for every refrigerant, six refrigerant pages with
their own worked examples and text, the body of the PT chart pages, refrigerant comparisons, the target superheat
calculator, two guides and the HVAC hub.

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

# What is free on the web. Decided by Andrii on 12 Nov 2026: every refrigerant in the calculator and the target superheat
# calculator stay live and free on the site. The app keeps R-410A, R-454B, R-32 and R-22 free and the rest in Pro.
TARGET_SUPERHEAT_LIVE = True  # the fixed-orifice target superheat calculator (Pro in the app)

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
        rows.append(("GWP (100-year)", f"{v} <span class=\"muted\">per US EPA ({e(basis)})</span>",
                     f"{src(k)}. Every GWP on this site is EPA's figure; refrigerant makers' literature can differ by a unit or two."))
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
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("PT charts", PT_INDEX), (f"{rid} PT chart", path)])

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
    cta = (f'<p class="btns"><a class="btn" href="{REL}{calc_href(rid)}">{rid} superheat &amp; subcooling calculator</a>'
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
                  + " The calculator interpolates between the printed points along the vapor-pressure curve."
                  + (f" {refdata.PT_NOTES[rid][0]}" if rid in refdata.PT_NOTES else "")))
    faq_html, faq_ld = b.faq(items)
    pt_note = ""
    if rid in refdata.PT_NOTES:
        text_, keys = refdata.PT_NOTES[rid]
        pt_note = f'\n<p class="note"><strong>Why this differs from the newest printed chart.</strong> {text_} Sources: {"; ".join(src(k) for k in keys)}.</p>'

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
<p class="note">Source: {e(r["source"])}.{" Converted from absolute pressure (psia) to psig." if r["bubble"].get("converted") else ""} {HVAC_NOTE}</p>{pt_note}
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
            body, "t-hvac", None, [ld, faq_ld], JS)


# ---------- superheat and subcooling: one calculator for every refrigerant, six pages with their own text ----------

def _a(path, label):
    return f'<a href="{REL}{path}">{label}</a>'


def _cell(b, rid, phase, t):
    return cell_text(printed(b.PT[rid], phase, t))


def _sat(b, rid, phase, psig):
    return t1(sat_temp(b.PT[rid], phase, psig))


def _gwp(rid):
    v, k, _ = refdata.GWP[rid]
    return v, src(k)


def examples_json(b, rids):
    """Example readings the page puts in the fields: {refrigerant: {"sh": [psig, °F], "sc": [psig, °F]}}."""
    out = {}
    for rid in rids:
        ex = example(b.PT[rid])
        out[rid] = {"sh": [ex["p_s"], ex["line_s"]], "sc": [ex["p_l"], ex["line_l"]]}
    return json.dumps(out, separators=(",", ":"))


def calc_widget(ref_field, ex, lookup_title):
    """The fields calc.js (initHvac) works with. ref_field is the refrigerant: a select on the shared calculator,
    a hidden input on a refrigerant's own page."""
    return f"""
<div class="calc card">
<div class="fields">
<div class="full"><div class="seg" id="mode" role="group" aria-label="Measurement">
<button data-v="sh" aria-pressed="true">Superheat</button><button data-v="sc" aria-pressed="false">Subcooling</button></div></div>
{ref_field}
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
<div class="full"><h2 style="margin:0">{lookup_title}</h2></div>
<div class="full"><div class="seg" id="ptmode" role="group" aria-label="Lookup direction">
<button data-v="p2t" aria-pressed="true">Pressure → temp</button><button data-v="t2p" aria-pressed="false">Temp → pressure</button></div></div>
<div class="full"><label for="pt-in" id="pt-in-label">Pressure <small>(psig)</small></label><input id="pt-in" inputmode="decimal" value="{ex['p_s']}"></div>
</div>
<div class="result"><div class="eyebrow">Saturation</div><div class="rows" id="pt-out"></div></div>
</section>
"""


def columns_text(r):
    g = glide(r)
    if g is None:
        return "One (single substance)" if r["id"] in PURE else "One (as the source chart prints it)"
    apart = next(x for x in g if x is not None)
    return f"Dew and bubble, {apart:.1f} °F apart" if apart >= 0.05 else "Dew and bubble, equal on this chart"


def calc_page(b):
    """The shared calculator (called from build.build_hvac). Every refrigerant is in the select; #r-454b in the
    address opens it with that refrigerant picked, which is how the PT chart pages link here."""
    path = MAIN_CALC
    n = len(b.PT)
    first = next(iter(b.PT))
    ex = example(b.PT[first])
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Superheat & subcooling calculator", path)])
    options = "".join(f'<option value="{rid}">{rid}{" (glide)" if r["dew"] else ""}</option>' for rid, r in b.PT.items())
    ref_field = (f'<div class="full"><label for="ref">Refrigerant</label><select id="ref">{options}</select>'
                 f'<p class="note" id="ref-info" data-charts="pt-chart/"></p></div>')

    rows = []
    for rid, r in b.PT.items():
        x = example(r)
        two = bool(r["dew"])
        more = _a(pt_path(rid), "PT chart") + (" · " + _a(sh_path(rid), "worked examples") if rid in OWN_PAGES else "")
        rows.append([f'<a href="#{slug(rid)}">{rid}</a>', columns_text(r), r["safety"],
                     f"{x['p_s']} psig → {t1(x['sat_s'])} °F{' dew' if two else ''}",
                     f"{x['p_l']} psig → {t1(x['sat_l'])} °F{' bubble' if two else ''}", more])
    by_source = {}
    for rid, r in b.PT.items():
        by_source.setdefault(r["source"], []).append(rid)
    sources = "; ".join(f"{e(s)} ({', '.join(ids)})" for s, ids in by_source.items())
    names = ", ".join(b.PT)

    faq_html, faq_ld = b.faq([
        ("How do you calculate superheat?",
         "Read the suction (low-side) pressure and convert it to the saturation temperature with the refrigerant's PT chart. "
         "Measure the suction line temperature near the service valve. Superheat = suction line temperature − saturation temperature. "
         "For blends with glide such as R-454B or R-407C, use the <b>dew point</b> (vapor) column."),
        ("How do you calculate subcooling?",
         "Read the liquid (high-side) pressure and convert it to the saturation temperature. Measure the liquid line temperature near the "
         "service valve. Subcooling = saturation temperature − liquid line temperature. For blends with glide, use the <b>bubble point</b> (liquid) column."),
        ("Should I charge by superheat or subcooling?",
         "Fixed-orifice (piston) systems are charged by superheat against a target from the outdoor and indoor conditions "
         f'(<a href="{REL}{TSH}">target superheat calculator</a>). TXV and EEV systems are charged by subcooling against the target on the '
         "outdoor unit's nameplate or the manufacturer's charging chart. Always follow the manufacturer's instructions for the specific unit."),
        ("Which refrigerants does the calculator cover?",
         f"{n} refrigerants: {names}. All of them are free to use here."),
        ("Can I open the calculator with a refrigerant already selected?",
         f"Yes. Add the refrigerant after a # sign at the end of the address, for example <code>{b.BASE}/{path}#r-454b</code>. "
         "The links on the PT chart pages open it that way."),
        ("Is R-454B a drop-in for R-410A?",
         "No. R-454B is an A2L (mildly flammable) refrigerant for equipment designed for it, with its own pressures, glide and safety requirements. "
         "Use the R-454B chart, not the R-410A one, and follow the A2L handling rules."),
        ("Where does this PT data come from?",
         f"From published pressure–temperature tables, one row every 5 °F: {sources}. Between the printed points the calculator "
         "interpolates along the vapor-pressure curve. It is a reference tool: verify against the equipment manufacturer's data."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Free HVAC tool</div>
<h1>Superheat &amp; Subcooling Calculator</h1>
<p class="lead">Pick one of {n} refrigerants, enter gauge pressure and line temperature, and get saturation, superheat or subcooling from the published PT chart.</p>
<p class="answer"><strong>Quick answer:</strong> superheat = suction line temperature − saturation temperature at the suction pressure;
subcooling = saturation temperature at the liquid pressure − liquid line temperature. With {first}, {ex['p_s']} psig is {t1(ex['sat_s'])} °F saturated,
so a {ex['line_s']} °F suction line has {t1(ex['sh'])} °F of superheat.</p></div>
{calc_widget(ref_field, ex, "PT lookup")}
<section class="guide"><h2>Refrigerants in this calculator</h2>
<p class="muted">Click a refrigerant to load it into the calculator above. The example readings are the ones the calculator starts with for
that refrigerant: they show the arithmetic and are not charging targets.</p>
{table(["Refrigerant", "Chart columns", "Safety class", "Example suction reading", "Example liquid reading", "More"], rows, "wide")}
<p class="note">Suction readings use the vapor (dew) column and liquid readings the liquid (bubble) column where the chart has two.</p></section>
<section><h2>Refrigerants with worked examples of their own</h2><div class="chips">{"".join(_a(sh_path(rid), rid) for rid in OWN_PAGES)}</div></section>
{b.promo("hvac-charge", "hvac-calc", "Same numbers on your phone, offline on the roof, with saved readings, piston target superheat and an add/recover call.")}
<section><h2>PT charts</h2><p class="muted">Full pressure–temperature tables, every 5 °F.</p>{b.chips()}</section>
{faq_html}
{hvac_links(b, MAIN_CALC)}
<p class="note">{HVAC_NOTE}</p>
"""
    desc = (f"Free superheat and subcooling calculator with PT lookup for {n} refrigerants, including R-454B, R-32, R-410A, R-22, "
            "R-134a and R-404A. Dew and bubble points from published PT charts.")
    scripts = (f"<script>window.HVAC_EXAMPLES = {examples_json(b, b.PT)};"
               f"window.HVAC_PAGES = {json.dumps({rid: 'superheat-calculator/' + slug(rid) + '.html' for rid in OWN_PAGES}, separators=(',', ':'))};</script>"
               f'<script src="{REL}assets/pt-data.js"></script><script src="{REL}assets/calc.js"></script>' + JS)
    b.shell(path, f"Superheat & Subcooling Calculator: {n} Refrigerants, Free", desc, body, "t-hvac", "hvac",
            [b.webapp_ld("Superheat & Subcooling Calculator", path, f"Superheat, subcooling and PT lookup for {n} refrigerants."), faq_ld], scripts)


# What is particular about each refrigerant that has its own page. Every function returns the text written for that
# refrigerant: lead, quick answer, meta description, sections [(heading, html)] and questions [(q, a)]. The numbers
# are computed from the PT tables here, so they cannot drift from the charts; tests run them through calc.js too.

def _r410a(b, r, ex):
    val, cls_src = safety_cell(r)
    gwp, gwp_src = _gwp("R-410A")
    p_s, sat_s = ex["p_s"], t1(ex["sat_s"])
    on_r22 = _sat(b, "R-22", "dew", p_s)
    return {
        "lead": "For residential and light commercial air conditioners and heat pumps charged with R-410A. Enter the gauge pressure and "
                "the line temperature; the saturation temperature comes from Arkema's R-410A chart.",
        "answer": f"R-410A has one pressure column, so superheat and subcooling use the same chart reading. {p_s} psig on the suction side is "
                  f"{sat_s} °F saturated, so a {ex['line_s']} °F suction line is {t1(ex['sh'])} °F superheated. {ex['p_l']} psig on the liquid line is "
                  f"{t1(ex['sat_l'])} °F, so a {ex['line_l']} °F line is {t1(ex['sc'])} °F subcooled.",
        "desc": "Free R-410A superheat and subcooling calculator with worked examples, typical R-410A pressures and how its chart differs "
                "from R-22, R-454B and R-32. Saturation from the published PT chart.",
        "sections": [
            ("A blend that is printed with one column",
             f"<p>R-410A is a blend: EPA gives its GWP as calculated for the blend ({gwp_src}). Arkema's chart still prints a single pressure "
             "column for it, so there is no bubble or dew column to choose from. The calculator shows one saturation temperature and uses it "
             "for both superheat and subcooling.</p>"),
            ("Much higher pressure than R-22",
             f"<p>At 40 °F saturated, R-410A reads {_cell(b, 'R-410A', 'dew', 40)} where R-22 reads {_cell(b, 'R-22', 'dew', 40)}; as 105 °F liquid it is "
             f"{_cell(b, 'R-410A', 'bubble', 105)} against {_cell(b, 'R-22', 'bubble', 105)}. One chart cannot stand in for the other: a {p_s} psig suction "
             f"reading looked up on the R-22 chart comes out as {on_r22} °F instead of {sat_s} °F.</p>"),
            ("R-454B and R-32 are for new equipment",
             f"<p>Arkema lists R-454B and R-32 as replacements for R-410A in new equipment ({src('arkema_digest')}). Both are A2L refrigerants, and "
             f"Chemours states that A2L refrigerants are for new equipment only, not for retrofits ({src('chemours_pt')}), so an R-410A unit is not "
             f"topped off with either. Their charts sit close to this one and are still different: at {p_s} psig the dew point of R-454B is "
             f"{_sat(b, 'R-454B', 'dew', p_s)} °F and R-32 is at {_sat(b, 'R-32', 'dew', p_s)} °F, against {sat_s} °F here. "
             f"See {_a(cmp_path('R-454B', 'R-410A'), 'R-454B vs R-410A')} and {_a(cmp_path('R-32', 'R-410A'), 'R-32 vs R-410A')}.</p>"),
            ("Class, oil and GWP",
             f"<p>R-410A is in safety class {val} ({cls_src}). Arkema names POE as its lubricant ({src(refdata.OIL['R-410A'][1])}). "
             f"Its 100-year GWP is {gwp} per US EPA.</p>"),
        ],
        "faq": [
            ("Does R-410A need the bubble or the dew column?",
             "Neither. The source chart prints one pressure column for R-410A, and this calculator uses that one saturation temperature "
             "for superheat and for subcooling."),
            ("Can I read R-410A pressures on an R-22 chart?",
             f"No. R-410A is at {_cell(b, 'R-410A', 'dew', 40)} at 40 °F and R-22 at {_cell(b, 'R-22', 'dew', 40)}. "
             f"A {p_s} psig reading on the R-22 chart would show {on_r22} °F instead of {sat_s} °F."),
            ("Can I top off an R-410A system with R-454B or R-32?",
             "No. Arkema lists both as R-410A replacements for new equipment, and Chemours states that A2L refrigerants are for new "
             "equipment only, not for retrofits."),
        ],
    }


def _r454b(b, r, ex):
    val, cls_src = safety_cell(r)
    gwp, gwp_src = _gwp("R-454B")
    comp, comp_key = refdata.COMPOSITION["R-454B"]
    g = glide(r)
    p_s, sat_s = ex["p_s"], t1(ex["sat_s"])
    bub_s = _sat(b, "R-454B", "bubble", p_s)
    on_410 = sat_temp(b.PT["R-410A"], "dew", p_s)
    return {
        "lead": "For air conditioners and heat pumps built for R-454B. It is a blend with temperature glide, so the calculator reads the "
                "dew point for superheat and the bubble point for subcooling.",
        "answer": f"R-454B has two saturation temperatures at one pressure. Superheat uses the dew point: {p_s} psig is {sat_s} °F, so a "
                  f"{ex['line_s']} °F suction line has {t1(ex['sh'])} °F of superheat. Subcooling uses the bubble point: {ex['p_l']} psig is "
                  f"{t1(ex['sat_l'])} °F, so a {ex['line_l']} °F liquid line has {t1(ex['sc'])} °F of subcooling.",
        "desc": "Free R-454B superheat and subcooling calculator: dew point for superheat, bubble point for subcooling. Worked examples, "
                "typical R-454B pressures, glide, A2L handling and the difference from R-410A, with sources.",
        "sections": [
            (f"A blend with about {g[0]:.1f} °F of glide",
             f"<p>R-454B is {e(comp)} ({src(comp_key)}). Its components boil off at different rates, so at one pressure the liquid starts to boil "
             f"at the bubble point and the last of it is gone at the dew point. On this chart the two are {g[0]:.1f} °F apart at a 40 °F dew point and "
             f"{g[1]:.1f} °F apart at a 105 °F bubble point: at {p_s} psig the dew point is {sat_s} °F and the bubble point {bub_s} °F.</p>"
             f"<p>Chemours prints the rule in the key of its R-454B chart: saturated vapor pressure for superheat, saturated liquid pressure for "
             f"subcooling ({src('chemours_pt')}). The Superheat and Subcooling buttons above switch the column for you. "
             f"{_a(BUBBLE_DEW, 'More on bubble and dew points')}.</p>"),
            ("Lower pressure than R-410A",
             f"<p>Arkema lists R-454B as a replacement for R-410A in new equipment only ({src('arkema_digest')}). It runs somewhat lower: "
             f"{_cell(b, 'R-454B', 'dew', 40)} against {_cell(b, 'R-410A', 'dew', 40)} as 40 °F vapor, and {_cell(b, 'R-454B', 'bubble', 105)} against "
             f"{_cell(b, 'R-410A', 'bubble', 105)} as 105 °F liquid. An R-410A chart applied to a {p_s} psig suction reading gives {t1(on_410)} °F instead of "
             f"{sat_s} °F, which would overstate superheat by {t1(ex['sat_s'] - on_410)} °F. See {_a(cmp_path('R-454B', 'R-410A'), 'R-454B vs R-410A')}.</p>"),
            ("A2L: what the manufacturers ask for",
             f"<p>R-454B is in safety class {val} ({cls_src}). Carrier's instructions call for non-sparking tools, a refrigerant detector before and "
             f"during the work and no flame for leak checking ({src('carrier_ph5')}). York requires service equipment rated for R-454B ({src('york_yh9')}), "
             f"and Lennox notes that R-454B cylinders have a ¼″ left-hand flare connection ({src('lennox_ml13')}). It is charged as liquid only "
             f"({src('carrier_llg')}), and Chemours states that A2L refrigerants are for new equipment only, not for retrofits.</p>"),
            ("Charging and GWP",
             f"<p>R-454B units with a TXV or EEV are charged by subcooling to the value on the rating plate: "
             f"{_a(CHARGE_454B, 'how to charge an R-454B system by subcooling')} walks through the steps with the manufacturer documents. "
             f"EPA gives R-454B a 100-year GWP of {gwp} ({gwp_src}); Arkema names POE as the lubricant.</p>"),
        ],
        "faq": [
            ("Which column do I use for R-454B, bubble or dew?",
             f"Dew (vapor) for superheat and bubble (liquid) for subcooling. At {p_s} psig they are {sat_s} °F and {bub_s} °F."),
            ("How much temperature glide does R-454B have?",
             f"About {g[0]:.1f} °F on this chart: the dew point minus the bubble point at the same pressure, at a 40 °F dew point."),
            ("Can I use an R-410A PT chart for R-454B?",
             f"No. At {p_s} psig the R-410A chart reads {t1(on_410)} °F and the R-454B dew point is {sat_s} °F, so superheat would come out "
             f"{t1(ex['sat_s'] - on_410)} °F too high."),
            ("Is R-454B added as liquid or as vapor?",
             "As liquid. It is a blend, and the equipment and refrigerant makers require it to leave the cylinder as liquid."),
        ],
    }


def _r32(b, r, ex):
    val, cls_src = safety_cell(r)
    gwp, gwp_src = _gwp("R-32")
    comp, comp_key = refdata.COMPOSITION["R-454B"]
    p_s, p_l = ex["p_s"], ex["p_l"]
    on_410_l = sat_temp(b.PT["R-410A"], "bubble", p_l)
    return {
        "lead": "For air conditioners, heat pumps and mini-splits built for R-32. It is a single substance, so there is one saturation "
                "temperature at each pressure and no glide.",
        "answer": f"R-32 boils and condenses at one temperature for each pressure, so one chart reading serves both calculations. {p_s} psig is "
                  f"{t1(ex['sat_s'])} °F: a {ex['line_s']} °F suction line has {t1(ex['sh'])} °F of superheat. {p_l} psig is {t1(ex['sat_l'])} °F: "
                  f"a {ex['line_l']} °F liquid line has {t1(ex['sc'])} °F of subcooling.",
        "desc": "Free R-32 superheat and subcooling calculator. R-32 is a single-component A2L refrigerant with no glide: worked examples, "
                "typical pressures and how its chart differs from R-410A and R-454B.",
        "sections": [
            ("One substance, no glide",
             "<p>R-32 is not a blend. At a given pressure it boils and condenses at a single temperature, so its chart has one pressure column "
             "and there is no bubble or dew decision to make. Whatever the calculator shows as the saturation temperature is used for superheat "
             "and for subcooling alike.</p>"),
            ("Close to R-410A, but not the same chart",
             f"<p>R-32 runs slightly above R-410A: {_cell(b, 'R-32', 'dew', 40)} against {_cell(b, 'R-410A', 'dew', 40)} at 40 °F, and "
             f"{_cell(b, 'R-32', 'bubble', 105)} against {_cell(b, 'R-410A', 'bubble', 105)} as 105 °F liquid. The gap looks small on a gauge and still moves "
             f"the result: {p_l} psig on the liquid line is {t1(ex['sat_l'])} °F for R-32 and {t1(on_410_l)} °F on the R-410A chart, a "
             f"{t1(abs(on_410_l - ex['sat_l']))} °F error in subcooling. See {_a(cmp_path('R-32', 'R-410A'), 'R-32 vs R-410A')}.</p>"),
            ("R-32 and R-454B",
             f"<p>Arkema lists both R-32 and R-454B as R-410A replacements for new equipment ({src('arkema_digest')}). R-454B is itself mostly R-32: "
             f"{e(comp)} ({src(comp_key)}). They are still two refrigerants. R-454B has glide and lower pressures, {_cell(b, 'R-454B', 'dew', 40)} as "
             f"40 °F vapor against {_cell(b, 'R-32', 'dew', 40)}, and a unit is charged with the one named on its data plate. "
             f"See {_a(cmp_path('R-454B', 'R-32'), 'R-454B vs R-32')}.</p>"),
            ("A2L class and GWP",
             f"<p>R-32 is in safety class {val} ({cls_src}). Chemours states that A2L refrigerants are for new equipment only, not for retrofits "
             f"({src('chemours_pt')}), so R-32 does not go into an R-410A system. EPA gives it a 100-year GWP of {gwp} ({gwp_src}), against "
             f"{refdata.GWP['R-410A'][0]} for R-410A. Arkema names POE as the lubricant.</p>"),
        ],
        "faq": [
            ("Does R-32 have temperature glide?",
             "No. R-32 is a single substance: one saturation temperature at each pressure, one column on the chart."),
            ("Is the R-32 PT chart the same as the R-410A chart?",
             f"No, although they are close. At 40 °F R-32 is at {_cell(b, 'R-32', 'dew', 40)} and R-410A at {_cell(b, 'R-410A', 'dew', 40)}; "
             f"at {p_l} psig the two charts are {t1(abs(on_410_l - ex['sat_l']))} °F apart."),
            ("Can R-32 be used in an R-410A system?",
             "No. R-32 is an A2L refrigerant, and Chemours states that A2L refrigerants are for new equipment only, not for retrofits."),
            ("What is the GWP of R-32?",
             f"{gwp} per US EPA ({e(refdata.GWP['R-32'][2])}), against {refdata.GWP['R-410A'][0]} for R-410A."),
        ],
    }


def _r22(b, r, ex):
    val, cls_src = safety_cell(r)
    gwp, gwp_src = _gwp("R-22")
    odp, odp_key = refdata.ODP["R-22"]
    oil, oil_key = refdata.OIL["R-22"]
    p_s, sat_s = ex["p_s"], t1(ex["sat_s"])
    on_410 = _sat(b, "R-410A", "dew", p_s)
    retro = (f"R-407C has a dew point of {_sat(b, 'R-407C', 'dew', p_s)} °F and a bubble point of {_sat(b, 'R-407C', 'bubble', p_s)} °F, and R-427A "
             f"{_sat(b, 'R-427A', 'dew', p_s)} °F and {_sat(b, 'R-427A', 'bubble', p_s)} °F")
    return {
        "lead": "For older air conditioners and heat pumps that still run on R-22. One substance, one pressure column, and pressures well "
                "below those of R-410A.",
        "answer": f"R-22 has one saturation temperature at each pressure. {p_s} psig on the suction side is {sat_s} °F, so a {ex['line_s']} °F suction "
                  f"line has {t1(ex['sh'])} °F of superheat. {ex['p_l']} psig on the liquid line is {t1(ex['sat_l'])} °F, so a {ex['line_l']} °F line has "
                  f"{t1(ex['sc'])} °F of subcooling.",
        "desc": "Free R-22 superheat and subcooling calculator for older systems: worked examples, typical R-22 pressures, what changes "
                "after a retrofit to R-407C or R-427A, and what EPA says about R-22 supply.",
        "sections": [
            ("No longer made, still in service",
             f"<p>R-22 is an HCFC with an ozone depletion potential of {odp} ({src(odp_key)}). EPA's guidance for homeowners says that no new R-22 "
             f"has been made or imported in the United States since 1 January 2020, and that existing R-22 systems can still be used and serviced, "
             f"with reclaimed R-22 and R-22 made before 2020 ({src('epa_hcfc22')}).</p>"),
            ("Low pressures next to R-410A",
             f"<p>R-22 reads {_cell(b, 'R-22', 'dew', 40)} at 40 °F and {_cell(b, 'R-22', 'bubble', 105)} as 105 °F liquid, where R-410A reads "
             f"{_cell(b, 'R-410A', 'dew', 40)} and {_cell(b, 'R-410A', 'bubble', 105)}. Put a {p_s} psig R-22 suction reading on an R-410A chart and it shows "
             f"{on_410} °F instead of {sat_s} °F.</p>"),
            ("After a retrofit the chart changes",
             f"<p>Arkema lists R-407C as a replacement and retrofit refrigerant for R-22, and R-427A as an R-22 retrofit ({src('arkema_digest')}). "
             f"Both are blends with two columns. At {p_s} psig, where R-22 has a single {sat_s} °F, {retro}. Once a system has been converted, "
             f"R-22 numbers no longer describe it: open the calculator with {_a(calc_href('R-407C'), 'R-407C')} or {_a(calc_href('R-427A'), 'R-427A')}, "
             f"whichever is on the retrofit label. See also {_a(cmp_path('R-407C', 'R-22'), 'R-407C vs R-22')}.</p>"),
            ("Oil, class and metering device",
             f"<p>Arkema lists {oil[0].lower() + oil[1:]} as lubricants for R-22 and says POE must be used with R-407C ({src(oil_key)}). R-22 is in "
             f"safety class {val} ({cls_src}), with a 100-year GWP of {gwp} per US EPA ({gwp_src}). An R-22 unit with a fixed orifice (piston) is charged "
             f"to a target superheat: see the {_a(TSH, 'target superheat calculator')}.</p>"),
        ],
        "faq": [
            ("Is R-22 still available?",
             "EPA's guidance for homeowners says no new R-22 has been made or imported in the United States since 1 January 2020. "
             "Existing systems can still be serviced with reclaimed R-22 and R-22 made before 2020."),
            ("Is R-22 a blend?",
             "No. R-22 is a single substance, so its chart has one pressure column and one saturation temperature at each pressure."),
            ("Can I use R-22 pressures after converting to R-407C or R-427A?",
             f"No. At {p_s} psig R-22 is at {sat_s} °F, while {retro}. Use the chart of the refrigerant that is in the system."),
            ("What is the ozone depletion potential of R-22?",
             f"{odp}, per US EPA."),
        ],
    }


def _r134a(b, r, ex):
    val, cls_src = safety_cell(r)
    gwp, gwp_src = _gwp("R-134a")
    lo, hi = trange(r)
    t_zero = next(t for t in range(lo, hi + 1, STEP) if printed(r, "bubble", t) >= 0)
    vac_psig = round(-10 * INHG, 1)
    vac_sat = sat_temp(r, "dew", vac_psig)
    p_s, sat_s = ex["p_s"], t1(ex["sat_s"])
    on_513 = sat_temp(b.PT["R-513A"], "dew", p_s)
    lowest = ("R-134a works at the lowest pressures of the refrigerants with their own page here. "
              if min(OWN_PAGES, key=lambda x: printed(b.PT[x], "dew", 40)) == "R-134a" else "")
    return {
        "lead": "For medium-temperature refrigeration, chillers and vehicle air conditioning on R-134a. A single substance with low "
                "pressures: on a cold evaporator the suction side can be in a vacuum.",
        "answer": f"R-134a has one saturation temperature at each pressure. In a medium-temperature case, {p_s} psig on the suction side is {sat_s} °F, "
                  f"so a {ex['line_s']} °F suction line has {t1(ex['sh'])} °F of superheat. {ex['p_l']} psig on the liquid line is {t1(ex['sat_l'])} °F, so a "
                  f"{ex['line_l']} °F line has {t1(ex['sc'])} °F of subcooling.",
        "desc": "Free R-134a superheat and subcooling calculator: worked medium-temperature examples, typical R-134a pressures, how to "
                "enter a vacuum reading and how the chart differs from R-513A.",
        "sections": [
            (f"Low pressures, and a vacuum below {t_zero} °F",
             f"<p>{lowest}Its chart reaches {_cell(b, 'R-134a', 'bubble', t_zero)} at "
             f"{t_zero} °F; colder than that the cells are printed in inches of mercury below atmospheric pressure: "
             f"{_cell(b, 'R-134a', 'bubble', t_zero - 5)} at {t_zero - 5} °F and {_cell(b, 'R-134a', 'bubble', -40)} at -40 °F.</p>"
             f"<p>The calculator takes gauge pressure in psig. To enter a vacuum reading, multiply the inches of mercury by 0.491 and type the result "
             f"with a minus sign: 10″ Hg is {abs(vac_psig)} psi below atmospheric, typed as {vac_psig}, which is {t1(vac_sat)} °F for R-134a.</p>"),
            ("One substance, one column",
             "<p>R-134a is not a blend, so it has a single saturation temperature at each pressure and no glide. The same chart reading is "
             "used for superheat and for subcooling.</p>"),
            ("R-513A is close, with a chart of its own",
             f"<p>Arkema lists R-513A as a replacement for R-134a, except in automotive AC ({src('arkema_digest')}). It runs a little higher: "
             f"{_cell(b, 'R-513A', 'dew', 40)} against {_cell(b, 'R-134a', 'dew', 40)} at 40 °F, and {_cell(b, 'R-513A', 'bubble', 105)} against "
             f"{_cell(b, 'R-134a', 'bubble', 105)} as 105 °F liquid. At {p_s} psig R-134a is at {sat_s} °F and the dew point of R-513A is {t1(on_513)} °F, "
             f"{t1(abs(ex['sat_s'] - on_513))} °F apart. See {_a(cmp_path('R-513A', 'R-134a'), 'R-513A vs R-134a')}.</p>"),
            ("Oil, class and what it replaced",
             f"<p>Arkema names POE as the lubricant for R-134a, with PAG in automotive AC only, and lists R-134a as the replacement for R-12 "
             f"({src('arkema_digest')}). R-134a is in safety class {val} ({cls_src}); EPA gives it a 100-year GWP of {gwp} ({gwp_src}).</p>"),
        ],
        "faq": [
            ("How do I enter a vacuum reading for R-134a?",
             f"As negative psig: inches of mercury × 0.491, with a minus sign. 10″ Hg of vacuum is typed as {vac_psig} and gives {t1(vac_sat)} °F."),
            ("At what temperature is R-134a at 0 psig?",
             f"At {t_zero} °F on Arkema's chart ({_cell(b, 'R-134a', 'bubble', t_zero)}). Below that the suction side is in a vacuum."),
            ("Can I use the R-134a chart for R-513A?",
             f"No. At {p_s} psig R-134a is at {sat_s} °F and the dew point of R-513A is {t1(on_513)} °F."),
            ("Which oil goes with R-134a?",
             "Arkema names POE, with PAG in automotive AC only."),
        ],
    }


def _r404a(b, r, ex):
    val, cls_src = safety_cell(r)
    gwp, gwp_src = _gwp("R-404A")
    lo, hi = trange(r)
    r134 = b.PT["R-134a"]
    t_zero_134 = next(t for t in range(*trange(r134), STEP) if printed(r134, "bubble", t) >= 0)
    p_s, sat_s = ex["p_s"], t1(ex["sat_s"])
    dew_448 = sat_temp(b.PT["R-448A"], "dew", p_s)
    after = (f"R-448A has a dew point of {t1(dew_448)} °F and a bubble point of {_sat(b, 'R-448A', 'bubble', p_s)} °F, and R-449A "
             f"{_sat(b, 'R-449A', 'dew', p_s)} °F and {_sat(b, 'R-449A', 'bubble', p_s)} °F")
    highest = max(OWN_PAGES, key=lambda x: float(refdata.GWP[x][0].replace(",", ""))) == "R-404A"
    return {
        "lead": "For low- and medium-temperature commercial refrigeration on R-404A. The worked example is a freezer case with a "
                f"{PROFILES['lt'][0]} °F evaporator.",
        "answer": f"Arkema's chart prints one pressure column for R-404A. In a low-temperature case, {p_s} psig on the suction side is {sat_s} °F, "
                  f"so a {ex['line_s']} °F suction line has {t1(ex['sh'])} °F of superheat. {ex['p_l']} psig on the liquid line is {t1(ex['sat_l'])} °F, so a "
                  f"{ex['line_l']} °F line has {t1(ex['sc'])} °F of subcooling.",
        "desc": "Free R-404A superheat and subcooling calculator with a low-temperature worked example, typical R-404A pressures and "
                "what changes after a conversion to R-448A or R-449A.",
        "sections": [
            ("Positive pressure on cold evaporators",
             f"<p>R-404A keeps the suction side above atmospheric pressure down to the bottom of the chart: {_cell(b, 'R-404A', 'dew', lo)} at {lo} °F, "
             f"{_cell(b, 'R-404A', 'dew', -10)} at -10 °F and {_cell(b, 'R-404A', 'dew', 20)} at 20 °F. {_a(sh_path('R-134a'), 'R-134a')}, by comparison, "
             f"is in a vacuum below {t_zero_134} °F.</p>"),
            ("A blend that is printed with one column",
             f"<p>R-404A is a blend: EPA gives its GWP as calculated for the blend ({gwp_src}). Arkema's chart prints one pressure column for it, "
             "so the calculator uses a single saturation temperature for superheat and for subcooling.</p>"),
            ("Its replacements have glide",
             f"<p>Arkema describes R-448A and R-449A as designed to replace R-404A, and lists R-452A as a replacement for R-404A and R-507A "
             f"({src('arkema_digest')}). Those charts have two columns. At {p_s} psig R-404A is at {sat_s} °F, while {after}. After a conversion to "
             f"R-448A, superheat taken from the R-404A chart would be {t1(dew_448 - ex['sat_s'])} °F too high. Open the calculator with "
             f"{_a(calc_href('R-448A'), 'R-448A')}, {_a(calc_href('R-449A'), 'R-449A')} or {_a(calc_href('R-452A'), 'R-452A')}, and see "
             f"{_a(cmp_path('R-448A', 'R-404A'), 'R-448A vs R-404A')} and {_a(cmp_path('R-449A', 'R-404A'), 'R-449A vs R-404A')}.</p>"),
            ("GWP, oil and neighbours",
             f"<p>EPA gives R-404A a 100-year GWP of {gwp}{', the highest of the refrigerants with their own page here' if highest else ''}. "
             f"Arkema lists it as the replacement for R-502 and names POE as its lubricant ({src('arkema_digest')}). It is in safety class {val} "
             f"({cls_src}). R-507A is a separate refrigerant with a chart of its own: at {p_s} psig it is at {_sat(b, 'R-507A', 'dew', p_s)} °F.</p>"),
        ],
        "faq": [
            ("Does R-404A have temperature glide on this chart?",
             "The source chart prints one pressure column for R-404A, so the calculator uses one saturation temperature for superheat and for subcooling."),
            ("What replaces R-404A?",
             "Arkema describes R-448A and R-449A as designed to replace R-404A, and lists R-452A and R-407A as replacements for R-404A and R-507A. "
             "A conversion follows the refrigerant maker's and the equipment maker's instructions."),
            ("Can I keep using the R-404A chart after converting to R-448A or R-449A?",
             f"No. At {p_s} psig R-404A is at {sat_s} °F, while {after}."),
            ("Does R-404A suction pressure go into a vacuum?",
             f"Not within this chart: it reads {_cell(b, 'R-404A', 'dew', lo)} at {lo} °F."),
        ],
    }


# The six refrigerants with a page of their own, each with text written for it. The other refrigerants are served
# by the shared calculator, opened with the refrigerant already picked (calc_href).
SPECIFICS = {"R-410A": _r410a, "R-454B": _r454b, "R-32": _r32, "R-22": _r22, "R-134a": _r134a, "R-404A": _r404a}
OWN_PAGES = list(SPECIFICS)

# Saturation temperatures for the "typical pressures" tables: (evaporator side, condenser side) per example profile.
TYPICAL = {
    "ac": ([30, 35, 40, 45, 50], [90, 100, 110, 120, 130]),
    "mt": ([0, 10, 20, 30, 40], [80, 90, 100, 110, 120]),
    "lt": ([-30, -20, -10, 0, 10], [80, 90, 100, 110, 120]),
}


def calc_href(rid):
    """Where "the superheat calculator for this refrigerant" is: its own page, or the shared calculator opened on it."""
    return sh_path(rid) if rid in OWN_PAGES else f"{MAIN_CALC}#{slug(rid)}"


def sh_page(b, rid):
    r = b.PT[rid]
    path = sh_path(rid)
    two = bool(r["dew"])
    ex = example(r)
    own = SPECIFICS[rid](b, r, ex)
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Superheat & subcooling", MAIN_CALC), (rid, path)])

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
    evap, cond = TYPICAL[PROFILE_OF[rid]]
    typ_rows = ([[f"Evaporator at {t} °F", b.fmt_cell(printed(r, "dew", t))] for t in evap]
                + [[f"Condenser at {t} °F", b.fmt_cell(printed(r, "bubble", t))] for t in cond])
    typ = table(["Saturation temperature", "Vapor (dew), psig" if two else "Pressure, psig"], typ_rows[:len(evap)]) + \
        table(["Saturation temperature", "Liquid (bubble), psig" if two else "Pressure, psig"], typ_rows[len(evap):])
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
    guide = guides.guide(f"{rid} worked examples and pressures", [
        f"<p>The readings below are {ex['label']}. They show the arithmetic; they are not charging targets.</p>",
        guides.example(f"{rid} superheat", sh_steps, f"Result: {t1(ex['sh'])} °F of superheat."),
        guides.example(f"{rid} subcooling", sc_steps, f"Result: {t1(ex['sc'])} °F of subcooling."),
        f"<h3>Typical {rid} pressures</h3>"
        f'<p class="muted">Cells of the {e(r["source"])} at evaporator and condenser saturation temperatures.</p>{typ}',
        guides.table(f"{rid} saturation temperature by gauge pressure", head, rows,
                     f"Interpolated between the 5 °F points of the chart, the same way the calculator does it. "
                     f'The full table by temperature is on the <a href="{REL}{pt_path(rid)}">{rid} PT chart</a>.'),
    ])
    about = "".join(f"<h3>{h}</h3>{text_}" for h, text_ in own["sections"])
    target = f"""<section class="prose"><h2>What should {rid} superheat and subcooling be?</h2>
<p>There is no single correct number for a refrigerant. The target belongs to the equipment: a fixed-orifice (piston) system is charged to a
target superheat from the manufacturer's charging table (<a href="{REL}{TSH}">target superheat calculator</a>), and a TXV or EEV system to the
target subcooling on the unit's data plate. Always use the manufacturer's numbers for the unit in front of you.</p></section>"""
    faq_html, faq_ld = b.faq(own["faq"] + [
        ("Where does the data come from?",
         f"{e(r['source'])}. Between the printed 5 °F points the calculator interpolates along the vapor-pressure curve."),
    ])
    others = "".join(f'<a href="{REL}{sh_path(x)}"{" aria-current=page" if x == rid else ""}>{x}</a>' for x in OWN_PAGES)
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Free HVAC tool · ASHRAE {r["safety"]}</div>
<h1>{rid} Superheat &amp; Subcooling Calculator</h1>
<p class="lead">{own["lead"]}</p>
<p class="answer"><strong>Quick answer:</strong> {own["answer"]}</p></div>
{calc_widget(f'<input type="hidden" id="ref" value="{rid}">', ex, f"{rid} PT lookup")}
<section class="prose"><h2>What is particular about {rid}</h2>{about}</section>
{guide}
{target}
{b.promo("hvac-charge", "sh-" + slug(rid), f"{rid} on your phone, offline on the roof: superheat, subcooling, piston target superheat and an add/recover call.")}
<section><h2>Other refrigerants</h2><div class="chips">{others}<a href="{REL}{MAIN_CALC}">All {len(b.PT)} refrigerants</a></div></section>
{hvac_links(b)}
{faq_html}
<p class="note">{HVAC_NOTE}</p>
"""
    data = json.dumps({rid: r}, separators=(",", ":"))
    scripts = (f"<script>window.PT_DATA = {data};window.HVAC_EXAMPLES = {examples_json(b, [rid])};</script>"
               f'<script src="{REL}assets/calc.js"></script>' + JS)
    b.shell(path, f"{rid} Superheat & Subcooling Calculator | Free, with PT Lookup", own["desc"], body, "t-hvac", "hvac",
            [b.webapp_ld(f"{rid} Superheat & Subcooling Calculator", path, own["desc"]), faq_ld], scripts)


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
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Comparisons", CMP_INDEX), (f"{a} vs {c}", path)])

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
<a href="{REL}{calc_href(a)}">{a} superheat &amp; subcooling</a><a href="{REL}{calc_href(c)}">{c} superheat &amp; subcooling</a>
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
    b.shell(path, f"{a} vs {c}: Pressure Difference, Glide and Safety Class", desc, body, "t-hvac", None, [ld, faq_ld], JS)


def cmp_index(b):
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Comparisons", CMP_INDEX)])
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
            body, "t-hvac", None)


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
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Target superheat", path)])
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
                   [("Outdoor dry bulb temperature", "°F"), ("Indoor wet bulb temperature", "°F"), ("Target superheat", "°F")]), faq_ld]
    b.shell(path, "Target Superheat Calculator and Chart (Fixed Orifice / Piston)", desc, body, "t-hvac", "tsh", lds, scripts)


# ---------- guide: bubble and dew points ----------

def bubble_dew_page(b):
    path = BUBBLE_DEW
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Bubble point vs dew point", path)])
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
            [article_ld(b, path, "Bubble point vs dew point: how to read a PT chart for a blend", desc), faq_ld], JS)


# ---------- article: charging R-454B by subcooling ----------

def charge_454b_page(b):
    path = CHARGE_454B
    r = b.PT["R-454B"]
    ex = example(r)
    wrong = sat_temp(r, "dew", ex["p_l"])
    target = 12  # the rating-plate value assumed in the worked example
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB), ("Charging R-454B by subcooling", path)])
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
            [article_ld(b, path, "How to charge an R-454B system by subcooling", desc), faq_ld], JS)


# ---------- hub ----------

def hub_page(b):
    crumb_html = crumbs([("Tools", "index.html"), ("HVAC", HUB)])
    cards = [
        (MAIN_CALC, "Calculator", "Superheat & subcooling calculator", f"All {len(b.PT)} refrigerants in one tool, with PT lookup."),
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
<section><h2>Superheat &amp; subcooling by refrigerant</h2>
<p class="muted">Each link opens the calculator on that refrigerant. {", ".join(OWN_PAGES[:-1])} and {OWN_PAGES[-1]} have a page of their own with worked examples.</p>
{chips(b, calc_href)}</section>
<section><h2>PT chart by refrigerant</h2>{b.chips()}</section>
<section><h2>Comparisons</h2><div class="chips">{"".join(f'<a href="{REL}{cmp_path(a, c)}">{a} vs {c}</a>' for a, c in PAIRS)}</div></section>
{b.promo("hvac-charge", "hvac-hub", f"All {len(b.PT)} refrigerants, piston target superheat and an add/recover call on your phone, offline.")}
<p class="note">{HVAC_NOTE}</p>
"""
    b.shell(HUB, "HVAC Calculators and Refrigerant PT Charts | Free",
            f"Free HVAC tools: a superheat and subcooling calculator for {len(b.PT)} refrigerants, target superheat for fixed-orifice systems, PT charts and refrigerant comparisons.",
            body, "t-hvac", None)


# Cards in the same shape as build.CALCS (path, tag, title, text, theme), for the home page and llms.txt.
CARDS = [
    (HUB, "HVAC", "All HVAC tools", "Calculators, PT charts, comparisons and guides in one place.", "t-hvac"),
    (TSH, "HVAC", "Target superheat calculator", "Fixed-orifice target from outdoor temperature and indoor wet bulb.", "t-hvac"),
    (CMP_INDEX, "HVAC", "Refrigerant comparisons", "R-454B vs R-410A, R-32 vs R-410A and more.", "t-hvac"),
    (BUBBLE_DEW, "HVAC", "Bubble point vs dew point", "Which PT column to use for a blend.", "t-hvac"),
    (CHARGE_454B, "HVAC", "Charging R-454B by subcooling", "Step by step, with manufacturer sources.", "t-hvac"),
]


def build(b):
    """Everything except the shared calculator and the PT chart pages, which build.build_hvac() makes through
    calc_page() and pt_page()."""
    hub_page(b)
    for rid in OWN_PAGES:
        sh_page(b, rid)
    for a, c in PAIRS:
        cmp_page(b, a, c)
    cmp_index(b)
    tsh_page(b)
    bubble_dew_page(b)
    charge_454b_page(b)
