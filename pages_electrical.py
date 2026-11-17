"""Electrical reference pages: the NEC Table 310.16 ampacity chart, wire size by amps and distance, voltage drop
references for 12 AWG, three phase and 12 V DC, subpanel feeders, conduit fill, box fill and EV charger circuits, plus
the electrical hub.

Ampacities, wire sizes and voltage drops are computed with the functions and tables in guides.py, which mirror
assets/calc.js; tests/test_pages.py runs calc.js itself against the numbers on these pages. Correction factors and the
conduit, box and grounding tables are read from the Electrician Calc app (nec_tables.dart), so the site never drifts
from the app; the fill arithmetic is calc_math.py's mirror of the app's electrical.dart.
"""
import math
import re
import subprocess
from collections import Counter
from html import escape as e

import calc_math as cm
import guides
import refdata
from guides import AMPACITY, NEC_SIZES, awg, drop_volts, fmt, max_feet, mm2_of, wire_size
from pagekit import CSS, ELEC_NOTE, JS, REL, article_ld, byline, crumbs, dataset_ld, printbar, related, table

HUB = "electrical/index.html"
VD_CALC = "electrical/voltage-drop-calculator.html"
WIRE_CALC = "electrical/wire-size-calculator.html"
AWG_MM2 = "electrical/awg-to-mm2.html"
AMPACITY_PAGE = "electrical/ampacity-chart-nec-310-16.html"
BY_DISTANCE = "electrical/wire-size-by-amps-and-distance.html"
VD_12AWG = "electrical/12-awg-voltage-drop-per-foot.html"
VD_3PH = "electrical/three-phase-voltage-drop.html"
VD_12V = "electrical/12v-dc-voltage-drop.html"
SUBPANEL = "electrical/wire-size-50-amp-sub-panel.html"
FILL_CHART = "electrical/conduit-fill-chart.html"
FILL_12_EMT = "electrical/how-many-12-awg-wires-in-3-4-emt.html"
BOX_FILL = "electrical/box-fill-nec-314-16.html"
EV_WIRE = "electrical/ev-charger-wire-size.html"
NEC_BY_STATE = "electrical/nec-edition-by-state.html"

NEC_EDITION = "NFPA 70, National Electrical Code, 2023 edition"
# The K factor (Ω·cmil/ft) behind every number here: calc.js takes resistivity at 20 °C and adds 25 % for operating
# temperature. Handbooks round copper to 12.9, which gives about 0.5 % less.
K_CU = guides.RHO20["cu"] * 1.25 * 0.3048 / guides.MM2_PER_CMIL
K_AL = guides.RHO20["al"] * 1.25 * 0.3048 / guides.MM2_PER_CMIL
K_NOTE = (f"K = {K_CU:.2f} Ω·cmil/ft for copper: resistivity 0.017241 Ω·mm²/m at 20 °C plus 25 % for operating temperature, "
          "the resistance the voltage drop calculator on this site uses")
ALL_SIZES = [s for s, _ in guides.NEC]  # 18 AWG to 500 kcmil, for voltage drop only


def elec_links(skip=None):
    links = [(VD_CALC, "Voltage drop calculator"), (WIRE_CALC, "Wire size calculator"), (AMPACITY_PAGE, "Ampacity chart (NEC 310.16)"),
             (BY_DISTANCE, "Wire size by amps and distance"), (VD_12AWG, "12 AWG voltage drop per foot"),
             (VD_3PH, "Three-phase voltage drop"), (VD_12V, "12 V DC voltage drop"), (SUBPANEL, "Subpanel feeder wire size"),
             (EV_WIRE, "EV charger wire size"), (FILL_CHART, "Conduit fill chart"), (FILL_12_EMT, "12 AWG in 3/4 in. EMT"),
             (BOX_FILL, "Box fill (NEC 314.16)"), (NEC_BY_STATE, "NEC edition by state"), (AWG_MM2, "AWG to mm²"), (HUB, "All electrical tools")]
    return related("More electrical tools", [l for l in links if l[0] != skip])


def load_factors(b):
    """Ambient correction (NEC 310.15(B)) and adjustment (Table 310.15(C)(1)) factors as the app holds them."""
    text = (b.ROOT / "Calculator_for_electrical/lib/feature/engine/nec_tables.dart").read_text()
    block = text[text.index("const _ambient"):text.index("double necTempFactor")]
    ambient = {int(t): [float(x) for x in vals.split(",") if x.strip()]
               for t, vals in re.findall(r"NecTemp\.c(\d+): \[([^\]]+)\]", block)}
    adj = [(lbl, float(val)) for lbl, val in zip(
        re.findall(r"=> '([^']+)',", text[text.index("String necConductorLabel"):text.index("double necAdjustment")]),
        re.findall(r"=> ([\d.]+),", text[text.index("double necAdjustment"):text.index("/// 240.6(A)")]))]
    return ambient, adj


AMBIENT_ROWS = ["10 °C or less", "11–15 °C", "16–20 °C", "21–25 °C", "26–30 °C", "31–35 °C", "36–40 °C", "41–45 °C",
                "46–50 °C", "51–55 °C", "56–60 °C"]


def ampacity(cond, temp, size):
    return AMPACITY[cond][temp][NEC_SIZES.index(size)]


def size_for(amps, feet, volts, cond="cu", supply="single", limit=3.0, cont=False):
    """The calculator's pick: smallest size by ampacity (THHN, 75 °C terminations), then upsized until the drop is
    within `limit` percent. Returns (size or None, size by ampacity, drop %)."""
    pick, _, _, _ = wire_size(amps, "thhn", cond, cont)
    if not pick:
        return None, None, None
    for s in NEC_SIZES[NEC_SIZES.index(pick):]:
        pct = drop_volts(supply, cond, mm2_of(s), feet * 0.3048, amps) / volts * 100
        if pct <= limit:
            return s, pick, pct
    return None, pick, None


def vd_size(amps, feet, volts, limit, supply="dc", cond="cu"):
    """Smallest size from 18 AWG to 500 kcmil that keeps the drop within `limit` percent (voltage drop only)."""
    for s in ALL_SIZES:
        pct = drop_volts(supply, cond, mm2_of(s), feet * 0.3048, amps) / volts * 100
        if pct <= limit:
            return s, pct
    return None, None


def short(s):
    return f"{s} kcmil" if s.isdigit() and int(s) >= 250 else s


# ---------- ampacity chart ----------

def ampacity_page(b):
    path = AMPACITY_PAGE
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("Ampacity chart", path)])
    ambient, adj = load_factors(b)
    rows = []
    for i, s in enumerate(NEC_SIZES):
        cells = [awg(s)]
        for cond in ("cu", "al"):
            for t in (60, 75, 90):
                v = AMPACITY[cond][t][i]
                cells.append(f"{v}" if v else "–")
        rows.append(cells)
    chart = table(["Size", "Copper 60 °C", "Copper 75 °C", "Copper 90 °C", "Aluminum 60 °C", "Aluminum 75 °C", "Aluminum 90 °C"], rows, "wide")
    amb = table(["Ambient temperature", "60 °C conductor", "75 °C conductor", "90 °C conductor"],
                [[AMBIENT_ROWS[i]] + [(f"{ambient[t][i]:.2f}" if i < len(ambient[t]) and ambient[t][i] else "–") for t in (60, 75, 90)]
                 for i in range(len(AMBIENT_ROWS))])
    adj_t = table(["Current-carrying conductors", "Multiply ampacity by"], [[lbl, f"{v:.2f}"] for lbl, v in adj if lbl != "1–3"])

    # Worked example 1: 60 A load, copper THHN, 75 °C terminations.
    s1, a1, ocpd1, _ = wire_size(60, "thhn", "cu")
    s1a, a1a, _, _ = wire_size(60, "thhn", "al")
    ex1 = guides.example("60 A feeder, copper THHN, 75 °C terminations", [
        "The load is 60 A, not continuous, so the breaker is 60 A.",
        f"Terminations are rated 75 °C, so read the 75 °C copper column: 8 AWG is {ampacity('cu', 75, '8')} A, too small; {awg(s1)} is {a1} A.",
        f"In aluminum the same column gives {awg(s1a)} at {a1a} A.",
    ], f"Result: {awg(s1)} copper or {awg(s1a)} aluminum on a {ocpd1} A breaker.")

    # Worked example 2: derating in a hot attic with 6 current-carrying conductors.
    f_amb = ambient[90][AMBIENT_ROWS.index("36–40 °C")]
    f_adj = dict(adj)["4–6"]
    base = ampacity("cu", 90, "12")
    derated = base * f_amb * f_adj
    ex2 = guides.example("12 AWG THHN copper, six current-carrying conductors in one conduit at 40 °C", [
        f"THHN is a 90 °C conductor, so the correction starts from the 90 °C column: 12 AWG copper is {base} A.",
        f"Ambient 36–40 °C, 90 °C conductor: multiply by {f_amb:.2f}.",
        f"Four to six current-carrying conductors: multiply by {f_adj:.2f}.",
        f"{base} × {f_amb:.2f} × {f_adj:.2f} = {derated:.1f} A.",
        f"The result may not exceed the 75 °C termination value ({ampacity('cu', 75, '12')} A), and 240.4(D) still limits 12 AWG copper to a 20 A breaker.",
    ], f"Result: {derated:.1f} A after correction, enough for a 20 A circuit.")

    faq_html, faq_ld = b.faq([
        ("What is the ampacity of 12 AWG copper wire?",
         f"{ampacity('cu', 60, '12')} A at 60 °C, {ampacity('cu', 75, '12')} A at 75 °C and {ampacity('cu', 90, '12')} A at 90 °C in NEC Table 310.16. "
         "NEC 240.4(D) limits the breaker on 12 AWG copper to 20 A in most circuits."),
        ("What is the ampacity of 6 AWG wire?",
         f"Copper: {ampacity('cu', 60, '6')} A at 60 °C, {ampacity('cu', 75, '6')} A at 75 °C and {ampacity('cu', 90, '6')} A at 90 °C. "
         f"Aluminum: {ampacity('al', 60, '6')}, {ampacity('al', 75, '6')} and {ampacity('al', 90, '6')} A."),
        ("Which temperature column do I use?",
         "The lowest rating in the circuit: the conductor insulation and the terminals at both ends. NEC 110.14(C) sets the termination rules; "
         "many breakers and lugs are marked 75 °C. NM-B cable is held to the 60 °C column by NEC 334.80. The 90 °C column is mainly a starting point for correction factors."),
        ("What size wire for 100 amps?",
         f"{awg(wire_size(100, 'thhn', 'cu')[0])} copper or {awg(wire_size(100, 'thhn', 'al')[0])} aluminum at 75 °C. "
         "Dwelling services and main feeders may use the smaller sizes of NEC 310.12."),
        ("When do I have to derate?",
         "When the ambient temperature is not 30 °C (86 °F), or when more than three current-carrying conductors share a raceway or cable. "
         "Multiply the table ampacity by the correction and adjustment factors below."),
        ("Where do these numbers come from?",
         f"{NEC_EDITION}: Table 310.16, with the ambient correction factors of 310.15(B) and the adjustment factors of Table 310.15(C)(1). They are the values the Electrician Calc app uses. "
         "The code text is not reproduced here: read the full table, its notes and your local amendments in the code itself."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>Ampacity Chart: NEC Table 310.16</h1>
<p class="lead">Allowable ampacity of copper and aluminum conductors, 14 AWG to 500 kcmil, in the 60 °C, 75 °C and 90 °C columns, with correction factors and worked examples.</p>
<p class="answer"><strong>Quick answer:</strong> at 75 °C, copper carries {ampacity('cu', 75, '14')} A on 14 AWG, {ampacity('cu', 75, '12')} A on 12 AWG, {ampacity('cu', 75, '10')} A on 10 AWG,
{ampacity('cu', 75, '8')} A on 8 AWG, {ampacity('cu', 75, '6')} A on 6 AWG and {ampacity('cu', 75, '4')} A on 4 AWG (NEC Table 310.16, 2023). Breakers on 14, 12 and 10 AWG copper are limited to 15, 20 and 30 A by NEC 240.4(D).</p></div>
{byline(f"Values from {NEC_EDITION}, Table 310.16, as used in the Electrician Calc app.")}
{printbar()}
<section><h2>Allowable ampacity, amperes</h2>
<p class="muted">Not more than three current-carrying conductors in a raceway, cable or earth, ambient 30 °C (86 °F). Insulated conductors rated up to 2000 V.</p>
{chart}
<p class="note">Common wire types by column: UF at 60 °C; THW and THWN at 75 °C; THHN, THWN-2 and XHHW-2 at 90 °C. The aluminum columns also cover copper-clad aluminum. 14 AWG aluminum is not listed.</p>
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p></section>
<section class="guide"><h2>Correction factors and worked examples</h2>
<h3>Ambient temperature correction (based on 30 °C)</h3>{amb}
<h3>More than three current-carrying conductors</h3>{adj_t}
{ex1}{ex2}</section>
<p><a class="btn" href="{REL}{WIRE_CALC}">Wire size calculator</a> <a class="btn ghost" href="{REL}{BY_DISTANCE}">Wire size by amps and distance</a></p>
{b.promo("electrician-calc", "ampacity", "Cable sizing with ambient and grouping derating, NEC and IEC, every step shown, plus PDF reports.")}
{faq_html}
{elec_links(AMPACITY_PAGE)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("Ampacity chart from NEC Table 310.16 (2023): copper and aluminum, 14 AWG to 500 kcmil, 60/75/90 °C columns, "
            "with ambient and conductor-count correction factors and worked examples. Printable.")
    ld = dataset_ld(b, path, "Conductor ampacity chart (NEC Table 310.16)", desc, f"{NEC_EDITION}, Table 310.16",
                    [("Conductor size", "AWG or kcmil"), ("Allowable ampacity, copper", "A"), ("Allowable ampacity, aluminum", "A")])
    b.shell(path, "Ampacity Chart: NEC Table 310.16 (Copper & Aluminum, 60/75/90 °C)", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- wire size by amps and distance ----------

DIST_LOADS = [15, 20, 30, 40, 50, 60, 80, 100]
DIST_FEET = [25, 50, 75, 100, 150, 200, 250, 300]


def dist_table(volts, cond="cu"):
    rows = []
    for amps in DIST_LOADS:
        cells = [f"{amps} A"]
        for ft in DIST_FEET:
            s, _, _ = size_for(amps, ft, volts, cond)
            cells.append(short(s) if s else "&gt; 500")
        rows.append(cells)
    return table(["Load \\ one-way length"] + [f"{ft} ft" for ft in DIST_FEET], rows)


def reach(amps, volts, cond="cu", groups=3):
    """'12 AWG up to 25 ft, 10 AWG up to 50 ft, ...': how far each size goes, from the chart's own cells."""
    out = []
    for ft in DIST_FEET:
        s = size_for(amps, ft, volts, cond)[0]
        if out and out[-1][0] == s:
            out[-1][1] = ft
        else:
            out.append([s, ft])
    return ", ".join(f"{awg(s)} up to {ft} ft" for s, ft in out[:groups])


def by_distance_page(b):
    path = BY_DISTANCE
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("Wire size by amps and distance", path)])
    s, pick, pct = size_for(30, 150, 240)
    pct_pick = drop_volts("single", "cu", mm2_of(pick), 150 * 0.3048, 30) / 240 * 100
    ex = guides.example("30 A at 240 V, 150 ft one way, copper", [
        f"By ampacity (75 °C column, NEC Table 310.16): {awg(pick)} copper, {ampacity('cu', 75, pick)} A, on a 30 A breaker.",
        f"Voltage drop of {awg(pick)} at 150 ft and 30 A: {drop_volts('single', 'cu', mm2_of(pick), 150 * 0.3048, 30):.2f} V, which is {pct_pick:.2f} % of 240 V. Over 3 %.",
        f"Next size up, {awg(s)}: {drop_volts('single', 'cu', mm2_of(s), 150 * 0.3048, 30):.2f} V, or {pct:.2f} %. Under 3 %.",
    ], f"Result: {awg(s)} copper for 30 A at 150 ft on 240 V.")

    def q(amps, ft, volts):
        sz, pk, p = size_for(amps, ft, volts)
        extra = "" if sz == pk else f" By ampacity alone it would be {awg(pk)}; the length is what pushes it up."
        return (f"What size wire for {amps} amps at {ft} feet?",
                f"{awg(sz)} copper on {volts} V single phase: the drop at full load is {p:.2f} %, within 3 %.{extra}")

    faq_html, faq_ld = b.faq([
        q(20, 100, 120), q(30, 100, 240), q(50, 100, 240), q(100, 200, 240),
        ("Is the distance one way or the total wire length?",
         "One way: the distance from the panel to the load. The voltage drop formula already counts the current going out and coming back."),
        ("Does a longer run change the breaker size?",
         "No. The breaker follows the load. A longer run only makes the wire larger to keep the voltage drop down. "
         "When you upsize the ungrounded conductors, NEC 250.122(B) has the equipment grounding conductor upsized in proportion."),
        ("How are these sizes worked out?",
         "First the smallest conductor whose ampacity in the 75 °C column of NEC Table 310.16 covers the load and its breaker, with the 240.4(D) limits for small conductors. "
         f"Then the size goes up until the voltage drop at full load is 3 % or less, using copper or aluminum resistance at operating temperature (K = {K_CU:.2f} Ω·cmil/ft for copper, {K_AL:.1f} for aluminum)."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>Wire size by amps and distance</h1>
<p class="lead">The smallest conductor that carries the load and keeps voltage drop within 3 %, for 15 to 100 A over 25 to 300 ft, at 120 V and 240 V.</p>
<p class="answer"><strong>Quick answer:</strong> copper, 3 % voltage drop or less. On 120 V, 20 A needs {reach(20, 120)}.
On 240 V, 30 A needs {reach(30, 240)}, and 50 A needs {reach(50, 240)}.</p></div>
{byline(f"Ampacities from {NEC_EDITION}, Table 310.16; sizes computed with the same formulas as the wire size calculator.")}
{printbar()}
<section class="guide"><h2>Wire size charts</h2>
<p class="muted">Sizes are AWG unless marked kcmil. Non-continuous load, THHN/THWN-2 conductors with 75 °C terminations, 30 °C ambient, up to three current-carrying conductors, power factor 1, voltage drop 3 % or less at full load.</p>
<h3>Copper, 120 V single phase</h3>{dist_table(120)}
<h3>Copper, 240 V single phase</h3>{dist_table(240)}
<h3>Aluminum, 240 V single phase</h3>{dist_table(240, "al")}
<p class="note">For continuous loads (3 hours or more, such as EV chargers) size for 125 % of the load first. NM-B cable uses the 60 °C column and is often one size larger at short lengths.
“&gt; 500” means even 500 kcmil is over 3 %: use parallel runs or a higher voltage.</p>
{ex}
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p></section>
<p><a class="btn" href="{REL}{WIRE_CALC}">Wire size calculator</a> <a class="btn ghost" href="{REL}{AMPACITY_PAGE}">Ampacity chart</a></p>
{b.promo("electrician-calc", "wire-distance", "Any load, length, voltage and wire type, with derating and the working shown step by step.")}
{faq_html}
{elec_links(BY_DISTANCE)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("Wire size chart by amps and distance: copper and aluminum for 15 to 100 A over 25 to 300 ft at 120 V and 240 V, "
            "sized for NEC Table 310.16 ampacity and 3 % voltage drop, with a worked example.")
    ld = dataset_ld(b, path, "Wire size by amps and distance", desc, f"{NEC_EDITION}, Table 310.16",
                    [("Load", "A"), ("One-way length", "ft"), ("Conductor size", "AWG or kcmil")])
    b.shell(path, "Wire Size Chart by Amps and Distance (120 V and 240 V)", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- 12 AWG voltage drop per foot ----------

def per_amp_foot(size, cond="cu", supply="single"):
    """Volts dropped per ampere per foot of one-way length."""
    return drop_volts(supply, cond, mm2_of(size), 0.3048, 1)


def vd_12awg_page(b):
    path = VD_12AWG
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("12 AWG voltage drop per foot", path)])
    k = per_amp_foot("12")
    loads, feet = [5, 10, 15, 20], [25, 50, 75, 100, 150, 200]

    def drop(a, ft):
        return drop_volts("single", "cu", mm2_of("12"), ft * 0.3048, a)

    t120 = table(["Load \\ one-way length"] + [f"{ft} ft" for ft in feet],
                 [[f"{a} A"] + [f"{drop(a, ft):.2f} V ({drop(a, ft) / 120 * 100:.1f} %)" for ft in feet] for a in loads])
    sizes = ["14", "12", "10", "8", "6", "4", "2"]
    per = table(["Wire", "Copper, mV per amp per foot", "Aluminum, mV per amp per foot", "Copper: longest run at 3 %, 120 V, full load"],
                [[awg(s), f"{per_amp_foot(s) * 1000:.3f}", f"{per_amp_foot(s, 'al') * 1000:.3f}" if ampacity("al", 75, s) else "–",
                  f"{fmt(max_feet(s, min(ampacity('cu', 75, s), guides.SMALL['cu'].get(s, 999)), 120))} ft at {min(ampacity('cu', 75, s), guides.SMALL['cu'].get(s, 999))} A"]
                 for s in sizes], "wide")
    ex = guides.example("15 A on 12 AWG copper, 120 V, 80 ft", [
        f"Drop per amp per foot of one-way length: {k * 1000:.3f} mV.",
        f"{k * 1000:.3f} mV × 15 A × 80 ft = {drop(15, 80):.2f} V.",
        f"As a share of 120 V: {drop(15, 80) / 120 * 100:.2f} %.",
    ], f"Result: {drop(15, 80):.2f} V, {'within' if drop(15, 80) / 120 * 100 <= 3 else 'over'} the 3 % recommendation.")
    faq_html, faq_ld = b.faq([
        ("What is the voltage drop of 12 AWG wire per foot?",
         f"About {k * 1000:.2f} millivolts per amp for each foot of one-way length on a single-phase or DC circuit (copper, both conductors counted). "
         f"At 20 A that is {k * 20:.4f} V per foot, or {k * 20 * 100:.2f} V per 100 ft."),
        ("How far can I run 12 AWG on a 20 amp circuit?",
         f"About {fmt(max_feet('12', 20, 120))} ft one way at 120 V and {fmt(max_feet('12', 20, 240))} ft at 240 V before the drop passes 3 % at a full 20 A. "
         f"At 15 A the 120 V distance is about {fmt(max_feet('12', 15, 120))} ft."),
        ("What is the voltage drop on 100 ft of 12 AWG at 20 amps?",
         f"{drop(20, 100):.2f} V: {drop(20, 100) / 120 * 100:.1f} % at 120 V or {drop(20, 100) / 240 * 100:.1f} % at 240 V."),
        ("Is 3 % a code requirement?",
         "For most circuits it is a recommendation in the NEC's informational notes (3 % on a branch circuit, 5 % for feeder and branch together), not a rule. "
         "Some equipment and some local codes do require it."),
        ("How is this calculated?",
         f"VD = 2 × K × I × L ÷ CM, with 6,530 circular mils for 12 AWG (NEC Chapter 9, Table 8) and {K_NOTE}. "
         f"That is 2 × {K_CU:.3f} ÷ 6,530 = {k * 1000:.3f} mV per amp per foot. Handbooks often round K to 12.9, which gives "
         f"{2 * 12.9 / 6530 * 1000:.3f} mV, about 0.5 % less."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>12 AWG voltage drop per foot</h1>
<p class="lead">How many volts 12 AWG copper loses per foot at 5 to 20 A, how far you can run it, and the same figure for 14 to 2 AWG.</p>
<p class="answer"><strong>Quick answer:</strong> 12 AWG copper drops about {k * 1000:.2f} mV per amp per foot of one-way length (single phase or DC).
At 20 A that is {k * 20 * 100:.2f} V per 100 ft, so a 120 V circuit reaches 3 % at about {fmt(max_feet('12', 20, 120))} ft.</p></div>
{byline(f"Computed with {K_NOTE}.")}
{printbar()}
<section class="guide"><h2>12 AWG copper: voltage drop at 120 V</h2>
<p class="muted">Volts lost and percent of 120 V. Length is one way; the formula counts both conductors. On 240 V the volts are the same and the percent is half.</p>
{t120}
<h3>Voltage drop per amp per foot, 14 to 2 AWG</h3>{per}
<p class="note">Multiply by the amps and the one-way feet to get volts. Three phase: multiply the result by 0.866. The last column uses each size's usual breaker limit.</p>
{ex}
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p></section>
<p><a class="btn" href="{REL}{VD_CALC}">Voltage drop calculator</a> <a class="btn ghost" href="{REL}{BY_DISTANCE}">Wire size by amps and distance</a></p>
{b.promo("electrician-calc", "vd-12awg", "Voltage drop, wire size and 21 calculators for NEC and IEC, with every step shown.")}
{faq_html}
{elec_links(VD_12AWG)}
<p class="note">Voltage drop only: the wire must also be large enough for the load and its breaker. {ELEC_NOTE}</p>
"""
    desc = ("12 AWG voltage drop per foot: millivolts per amp per foot for copper and aluminum, drop at 5 to 20 A over 25 to 200 ft at 120 V, "
            "maximum run length and a worked example.")
    ld = dataset_ld(b, path, "12 AWG voltage drop per foot", desc, f"NEC Chapter 9, Table 8 conductor areas; copper resistance K = {K_CU:.2f} Ω·cmil/ft",
                    [("Load", "A"), ("One-way length", "ft"), ("Voltage drop", "V")])
    b.shell(path, "12 AWG Voltage Drop per Foot: Chart and Maximum Distance", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- three-phase voltage drop ----------

THREE_PH = [("12", 20), ("10", 30), ("8", 50), ("6", 65), ("4", 85), ("2", 115), ("1/0", 150), ("3/0", 200), ("250", 255), ("500", 380)]


def vd_3ph_page(b):
    path = VD_3PH
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("Three-phase voltage drop", path)])
    rows = [[awg(s), f"{a} A"] + [f"{fmt(max_feet(s, a, v, supply='three'))} ft" for v in (208, 240, 480)]
            + [f"{fmt(max_feet(s, a, 480, 'al', 'three'))} ft" if ampacity("al", 75, s) else "–"] for s, a in THREE_PH]
    t = table(["Wire", "Load", "208 V copper", "240 V copper", "480 V copper", "480 V aluminum"], rows, "wide")
    amps, ft, size, volts = 40, 250, "8", 480
    vd = drop_volts("three", "cu", mm2_of(size), ft * 0.3048, amps)
    k = 1.732 * 12.9 * amps * ft / dict(guides.NEC)[size]
    single = drop_volts("single", "cu", mm2_of(size), ft * 0.3048, amps)
    ex = guides.example(f"{amps} A on {awg(size)} copper, {volts} V three phase, {ft} ft", [
        f"Handbook K-factor (K = 12.9): VD = 1.732 × K × I × L ÷ CM = 1.732 × 12.9 × {amps} A × {ft} ft ÷ {fmt(dict(guides.NEC)[size])} cmil = {k:.2f} V.",
        f"The calculator on this site uses K = {K_CU:.2f} and gives {vd:.2f} V line to line, which is {vd / volts * 100:.2f} % of {volts} V.",
        f"The same wire, current and length on a single-phase circuit would drop {single:.2f} V: three phase is 0.866 of that.",
    ], f"Result: {vd:.2f} V, {vd / volts * 100:.2f} %, within 3 %.")
    faq_html, faq_ld = b.faq([
        ("What is the three-phase voltage drop formula?",
         f"VD = 1.732 × K × I × L ÷ CM, with K ≈ 12.9 Ω·cmil/ft for copper in handbooks (this site's calculator uses {K_CU:.2f} for copper and {K_AL:.1f} for aluminum), I the line current, L the one-way length in feet and CM the conductor area in circular mils. "
         "The result is the drop between lines; divide by the line-to-line voltage for percent."),
        ("Why 1.732 instead of 2?",
         "In a balanced three-phase circuit the currents in the three conductors cancel in the return path, so the line-to-line drop is √3 times the drop of one conductor, "
         "not twice as in a single-phase circuit."),
        ("Do I use line-to-line or line-to-neutral voltage?",
         "Line-to-line with the 1.732 formula: 208, 240 or 480 V. For a single-phase load connected line to neutral on a three-phase system, use the single-phase formula with the line-to-neutral voltage."),
        (f"How far can I run {awg('6')} on a 480 V three-phase circuit?",
         f"About {fmt(max_feet('6', 65, 480, supply='three'))} ft one way at a full 65 A before the drop passes 3 %. At half the load the distance doubles."),
        ("Does power factor matter?",
         "Yes, on large conductors and motor loads. The table assumes power factor 1; the voltage drop calculator on this site lets you enter the power factor and adds conductor reactance."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>Three-phase voltage drop: formula and chart</h1>
<p class="lead">The 1.732 formula, the longest run at 3 % for 208, 240 and 480 V, and a worked example.</p>
<p class="answer"><strong>Quick answer:</strong> three-phase voltage drop is 1.732 × K × I × L ÷ CM, with K ≈ 12.9 for copper. It is 0.866 of the single-phase drop for the same wire, current and length.
Example: {amps} A on {awg(size)} copper over {ft} ft at {volts} V drops {vd:.1f} V ({vd / volts * 100:.1f} %).</p></div>
{byline(f"Computed with {K_NOTE}.")}
{printbar()}
<section class="guide"><h2>Longest three-phase run at 3 % voltage drop</h2>
<p class="muted">One-way length at the load shown (the 75 °C ampacity of each size from NEC Table 310.16), power factor 1.</p>
{t}
<p class="note">At half the load the length doubles. For 5 % multiply the length by 1.67.</p>
{ex}
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p></section>
<p><a class="btn" href="{REL}{VD_CALC}">Voltage drop calculator (choose 3-phase)</a></p>
{b.promo("electrician-calc", "vd-3ph", "Three-phase cable sizing, motor circuits and fault level, NEC and IEC, with the working shown.")}
{faq_html}
{elec_links(VD_3PH)}
<p class="note">Voltage drop only: the wire must also be large enough for the load and its overcurrent protection. {ELEC_NOTE}</p>
"""
    desc = ("Three-phase voltage drop formula (1.732 × K × I × L ÷ CM) with a chart of the longest run at 3 % for 208, 240 and 480 V, "
            "copper and aluminum, and a worked example.")
    b.shell(path, "Three-Phase Voltage Drop: Formula, Chart and Example", desc, body, "t-elec", None,
            [article_ld(b, path, "Three-phase voltage drop: formula and chart", desc), faq_ld], JS)


# ---------- 12 V DC voltage drop ----------

DC_AMPS = [5, 10, 15, 20, 30, 40, 50]
DC_FEET = [5, 10, 15, 20, 25, 30, 40, 50]


def dc_table(limit):
    rows = []
    for a in DC_AMPS:
        cells = [f"{a} A"]
        for ft in DC_FEET:
            s, _ = vd_size(a, ft, 12, limit)
            cells.append(short(s) if s else "&gt; 500")
        rows.append(cells)
    return table(["Current \\ one-way length"] + [f"{ft} ft" for ft in DC_FEET], rows)


def vd_12v_page(b):
    path = VD_12V
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("12 V DC voltage drop", path)])
    a, ft = 20, 15
    s3, p3 = vd_size(a, ft, 12, 3)
    s10, p10 = vd_size(a, ft, 12, 10)
    v14 = drop_volts("dc", "cu", mm2_of("14"), ft * 0.3048, a)
    ex = guides.example(f"{a} A load, {ft} ft from the battery, 12 V", [
        f"On 14 AWG: 2 × {ft} ft of wire carry {a} A and drop {v14:.2f} V, which is {v14 / 12 * 100:.1f} % of 12 V.",
        f"To stay within 3 % (0.36 V) the wire has to be {awg(s3)}: {p3:.2f} %.",
        f"If 10 % (1.2 V) is acceptable for the load, {awg(s10)} is enough: {p10:.2f} %.",
    ], f"Result: {awg(s3)} for 3 %, {awg(s10)} for 10 %.")
    faq_html, faq_ld = b.faq([
        ("Why does voltage drop matter more at 12 V?",
         "The volts lost depend on current and wire, not on the system voltage. Losing 0.5 V is 0.4 % of 120 V but over 4 % of 12 V, "
         "so low-voltage DC runs need much heavier wire for the same percent."),
        ("What voltage drop is acceptable on 12 V?",
         "It depends on the load, so this page gives two limits: 3 % (0.36 V) and 10 % (1.2 V). "
         "Use the limit the maker of the equipment specifies."),
        ("Is the length one way or round trip?",
         "The tables use the one-way distance from the source to the load and already count both the positive and the negative conductor."),
        (f"What size wire for {a} amps at 12 volts?",
         f"For a {ft} ft run, {awg(s3)} keeps the drop within 3 % and {awg(s10)} within 10 %. Longer runs need larger wire: see the tables."),
        ("Does this cover fuse and ampacity?",
         "No. These tables check voltage drop only. The wire must also be rated for the current, and the fuse or breaker must protect the wire. "
         "Vehicles and boats have their own wiring standards; follow the one that applies."),
        ("How is this calculated?",
         f"VD = 2 × K × I × L ÷ CM with {K_NOTE}, set to DC. "
         "Cooler wire has slightly less resistance, so real drops are a little lower."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>12 V DC voltage drop and wire size chart</h1>
<p class="lead">The smallest copper wire that keeps a 12 V DC run within 3 % or 10 % voltage drop, for 5 to 50 A over 5 to 50 ft.</p>
<p class="answer"><strong>Quick answer:</strong> at 12 V, 3 % is only 0.36 V. A {a} A load {ft} ft from the battery needs {awg(s3)} copper to stay within 3 %, or {awg(s10)} if a 10 % drop is acceptable.</p></div>
{byline("Computed with the same formula as the voltage drop calculator on this site, set to DC.")}
{printbar()}
<section class="guide"><h2>12 V DC wire size charts</h2>
<p class="muted">Copper, AWG unless marked kcmil. Length is one way from the source to the load; both conductors are counted.</p>
<h3>3 % voltage drop or less (0.36 V)</h3>{dc_table(3)}
<h3>10 % voltage drop or less (1.2 V)</h3>{dc_table(10)}
<p class="note">Voltage drop only. Check the wire's ampacity and the fuse rating separately. For 24 V the same wire allows twice the length.</p>
{ex}
<p class="note print-only">{b.BASE}/{path} · checked {refdata.CHECKED}</p></section>
<p><a class="btn" href="{REL}{VD_CALC}">Voltage drop calculator (choose DC)</a></p>
{b.promo("electrician-calc", "vd-12v", "DC, single and three-phase voltage drop, solar PV strings and battery sizing in one app.")}
{faq_html}
{elec_links(VD_12V)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("12 V DC wire size chart by amps and length for 3 % and 10 % voltage drop, 5 to 50 A over 5 to 50 ft, copper, "
            "with a worked example. Voltage drop only: check ampacity and fusing separately.")
    ld = dataset_ld(b, path, "12 V DC wire size by current and length", desc, f"NEC Chapter 9, Table 8 conductor areas; copper resistance K = {K_CU:.2f} Ω·cmil/ft",
                    [("Current", "A"), ("One-way length", "ft"), ("Conductor size", "AWG")])
    b.shell(path, "12 V DC Voltage Drop and Wire Size Chart (3 % and 10 %)", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- pages on the app's tables: subpanel feeders, conduit fill, box fill, EV chargers ----------

# The day these five pages were compared with the app's engine (main of Calculator_for_electrical).
ENGINE_CHECKED = ("16 November 2026", "2026-11-16")
FILL_SIZES = ["14", "12", "10", "8", "6", "4", "3", "2", "1", "1/0"]
FILL_TRADES = ["1/2", "3/4", "1", "1-1/4", "1-1/2", "2"]
TRADE_LABEL = {"1/2": "½", "3/4": "¾", "1": "1", "1-1/4": "1¼", "1-1/2": "1½", "2": "2"}
SUB_FEEDERS = [50, 60, 100]
SUB_FEET = [25, 50, 75, 100, 150, 200, 250]
EV_AMPS = [32, 40, 48, 80]
EV_FEET = [25, 50, 75, 100, 150, 200]
_APP = {}


def app_tables(b):
    """NEC Chapter 9 Tables 1, 4 and 5 (THHN in EMT and PVC Schedule 40), Table 314.16(B)(1), the common metal boxes
    of Table 314.16(A) and Table 250.122, as the Electrician Calc app holds them in nec_tables.dart."""
    if _APP:
        return _APP
    text = (b.ROOT / "Calculator_for_electrical/lib/feature/engine/nec_tables.dart").read_text()

    def body(start, end="};"):
        return text.split(start, 1)[1].split(end, 1)[0]

    def pairs(src):
        return {k: float(v) for k, v in re.findall(r"'([^']+)': ([\d.]+)", src)}

    lim = body("double necFillLimit(int conductors) => switch (conductors) {")
    _APP.update(
        thhn=pairs(body("const thhnArea = <String, double>{")),
        trade=re.findall(r"'([^']+)'", body("const tradeSizes = <String>[", "];")),
        raceway={k: [float(x) for x in v.split(",") if x.strip()]
                 for k, v in re.findall(r"Raceway\.(\w+): \[([^\]]+)\]", body("const racewayArea = <Raceway, List<double>>{"))},
        raceway_name=dict(re.findall(r"(\w+)\('([^']+)'\)", body("enum Raceway {", ";"))),
        limits=tuple(float(re.search(k + r" => ([\d.]+)", lim).group(1)) for k in ("1", "2", "_")),
        box=pairs(body("const boxVolumePerConductor = <String, double>{")),
        boxes=[(n, float(v)) for n, v in re.findall(r"\('([^']+)', ([\d.]+)\)", body("const metalBoxes = <(String, double)>[", "];"))],
        egc=[(int(a), cu, al) for a, cu, al in re.findall(r"(\d+): \('([^']+)', '([^']+)'\)", body("const necEgc = <int, (String, String)>{"))],
    )
    return _APP


def raceway_area(t, raceway, trade):
    return t["raceway"][raceway][t["trade"].index(trade)]


def fill_count(t, raceway, trade, size):
    """(the app's count, mark). '*': the 40 % calculation ends in .8 or more, where Note 7 to the Chapter 9 tables
    permits the next whole number and the app still rounds down. '†': 40 % of the raceway would hold two, but two
    conductors are limited to 31 %, so one fits."""
    area, wire = raceway_area(t, raceway, trade), t["thhn"][size]
    n = cm.conduit_max(wire, area, t["limits"])
    x = t["limits"][2] * area / wire
    return n, "*" if n >= 2 and x - n >= 0.8 - 1e-9 else "†" if n == 1 and x >= 2 else ""


def ground(b, ocpd, copper=True):
    return cm.egc_for(ocpd, app_tables(b)["egc"], copper)


def ground_upsized(b, ocpd, minimum, installed, copper=True):
    return cm.egc_upsized(ocpd, app_tables(b)["egc"], dict(guides.NEC), NEC_SIZES, minimum, installed, copper)


def nmb_for(amps, cont=False):
    """Copper NM-B for a load: the 60 °C pick, moved up to a size NM-B is made in; None above 2 AWG."""
    s = wire_size(amps, "nmb", "cu", cont)[0]
    return next((m for m in guides.NMB_MADE if s and NEC_SIZES.index(m) >= NEC_SIZES.index(s)), None)


def pct_at(size, amps, feet, cond="cu", volts=240):
    return drop_volts("single", cond, mm2_of(size), feet * 0.3048, amps) / volts * 100


def run_table(loads, feet, cond="cu", cont=False):
    """Rows of lengths, a column per load: the size the wire size calculator picks and the drop at that size."""
    rows = []
    for ft in feet:
        cells = [f"{ft} ft"]
        for amps in loads:
            s, _, pct = size_for(amps, ft, 240, cond, cont=cont)
            cells.append(f"{awg(s)} <small>{pct:.2f} %</small>" if s else "&gt; 500 kcmil")
        rows.append(cells)
    return table(["One-way length"] + [f"{a} A" for a in loads], rows, "stack tight")


def holds(amps, feet, cond="cu", cont=False):
    """(size by ampacity, the longest length of the chart it serves, the next length, the size there)."""
    pick = wire_size(amps, "thhn", cond, cont)[0]
    far = [ft for ft in feet if size_for(amps, ft, 240, cond, cont=cont)[0] == pick]
    nxt = feet[len(far)] if len(far) < len(feet) else None
    return pick, far[-1], nxt, size_for(amps, nxt, 240, cond, cont=cont)[0] if nxt else None


def app_line(b, source, text):
    """One factual line under the answer on what the app adds for this job, with the store buttons."""
    name = e(b.CFG["apps"]["electrician-calc"]["short"])
    return (f'<!-- app:electrician-calc --><div class="appline"><p><strong>In the <a href="{b.app_href("electrician-calc")}">{name}</a> app:</strong> '
            f'{text}</p>{b.store_buttons("electrician-calc", source)}</div>')


def checked_note(b, path):
    return f'<p class="note print-only">{b.BASE}/{path} · checked {ENGINE_CHECKED[0]}</p>'


# ---------- what size wire for a 50 amp sub panel ----------

def subpanel_page(b):
    path = SUBPANEL
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("Wire size for a 50 amp sub panel", path)])

    def both(amps):
        cu, al = holds(amps, SUB_FEET), holds(amps, SUB_FEET, "al")
        far = f"up to {cu[1]} ft one way" if cu[1] == al[1] else f"up to {cu[1]} ft one way in copper and {al[1]} ft in aluminum"
        return cu, al, far

    cu, al, far = both(50)
    answer = (f"a 50 amp subpanel needs {awg(cu[0])} copper or {awg(al[0])} aluminum feeder conductors (THHN, XHHW-2 or SER cable on 75 °C terminals; "
              f"NEC Table 310.16, 2023 edition). On 240 V that keeps voltage drop within 3 % at a full 50 A {far}; "
              f"at {cu[2]} ft use {awg(cu[3])} copper or {awg(size_for(50, cu[2], 240, 'al')[0])} aluminum. "
              "The feeder has four conductors: two hots, a neutral and a ground.")

    def q(amps):
        c, a, reach_ = both(amps)
        return (f"What size wire for a {amps} amp sub panel?",
                f"{awg(c[0])} copper or {awg(a[0])} aluminum, on a {amps} A breaker, {reach_}. "
                f"At {c[2]} ft the chart moves to {awg(c[3])} copper to keep the drop within 3 % at a full {amps} A on 240 V.")

    grounds = table(["Feeder breaker", "Copper ground", "Aluminum ground"],
                    [[f"{a} A", awg(ground(b, a)), awg(ground(b, a, False))] for a in SUB_FEEDERS])
    s, pick, pct = size_for(60, 150, 240)
    egc, up = ground(b, 60), ground_upsized(b, 60, pick, s)
    ex = guides.example("60 A subpanel in a detached garage, 150 ft from the main panel, copper", [
        f"By ampacity (75 °C column, NEC Table 310.16): {awg(pick)} copper, {ampacity('cu', 75, pick)} A, on a 60 A breaker.",
        f"Voltage drop of {awg(pick)} at 150 ft and a full 60 A: {pct_at(pick, 60, 150) * 2.4:.2f} V, which is {pct_at(pick, 60, 150):.2f} % of 240 V. Over 3 %.",
        f"Next size up, {awg(s)}: {pct * 2.4:.2f} V, or {pct:.2f} %. Under 3 %.",
        f"Ground: Table 250.122 gives {awg(egc)} copper for a 60 A breaker. Because the hots went up from {awg(pick)} to {awg(s)}, "
        f"250.122(B) increases the ground in the same proportion: {awg(up)}.",
    ], f"Result: two {awg(s)} hots, a neutral of the same size and a {awg(up)} ground, all copper, on a 60 A breaker.")
    n50, n60 = nmb_for(50), nmb_for(60)
    nmb_why = (f"NM-B (Romex) cable is held to the 60 °C column by NEC 334.80, where {awg(cu[0])} copper is only {ampacity('cu', 60, cu[0])} A. "
               f"On NM-B a 50 A feeder needs {awg(n50)} copper and a 60 A feeder {awg(n60)}.")
    faq_html, faq_ld = b.faq([
        q(50), q(60), q(100),
        (f"Why do other sites say {awg(n50)} for a 50 amp sub panel?",
         f"They size NM-B cable. {nmb_why} The {awg(cu[0])} answer is for THHN or XHHW-2 conductors in conduit on 75 °C terminals, where {awg(cu[0])} copper is {ampacity('cu', 75, cu[0])} A."),
        ("Why do some charts show a smaller wire for 100 amps?",
         "They use NEC 310.12, which allows smaller conductors for a dwelling's service and for the one feeder that carries the dwelling's whole load. "
         "A feeder to a subpanel that carries only part of the load is sized from Table 310.16, as on this page."),
        ("Does a sub panel need 3 wires or 4?",
         "Four: two hots, a neutral and an equipment ground. The neutral and the ground are kept on separate bars in the subpanel, "
         "and the neutral is bonded to ground only at the service (NEC 250.24(B)). A subpanel in a detached building also gets its own grounding electrode (NEC 250.32)."),
        ("Is the distance one way or the total wire length?",
         "One way: from the main panel to the subpanel. The voltage drop formula already counts the current going out and coming back."),
        ("How are these sizes worked out?",
         "First the smallest conductor whose ampacity in the 75 °C column of NEC Table 310.16 covers the feeder breaker. "
         f"Then the size goes up until the voltage drop at the feeder's full rating is 3 % or less on 240 V, using copper or aluminum resistance at operating temperature "
         f"(K = {K_CU:.2f} Ω·cmil/ft for copper, {K_AL:.1f} for aluminum). These are the formulas of the wire size calculator on this site and of the Electrician Calc app."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>What size wire for a 50 amp sub panel?</h1>
<p class="lead">Feeder wire for 50, 60 and 100 amp subpanels from 25 to 250 ft, copper and aluminum, with the voltage drop at each length.</p>
<p class="answer"><strong>Quick answer:</strong> {answer}</p></div>
{app_line(b, "subpanel", "the free Wire Size calculator sizes a feeder for any load, length, voltage and wire type, shows the working and gives the ground wire, "
          "increased under 250.122(B) when the run is upsized for voltage drop. The Panel Planner, which assigns a panel's circuits to breakers and wire sizes, is in Pro.")}
{byline(f"Ampacities from {NEC_EDITION}, Table 310.16; sizes and voltage drop computed with the formulas of the Electrician Calc app.", ENGINE_CHECKED)}
{printbar()}
<section class="guide"><h2>Feeder wire size for 50, 60 and 100 amp subpanels</h2>
<p class="muted">Each cell is the smallest wire that carries the feeder and keeps voltage drop at or under 3 %, with the drop at that size. 240 V single phase, the feeder loaded to its full rating,
non-continuous load, THHN/THWN-2 or XHHW-2 conductors (SER cable for aluminum) on 75 °C terminals, 30 °C ambient, power factor 1. Length is one way.</p>
<h3>Copper</h3>{run_table(SUB_FEEDERS, SUB_FEET)}
<h3>Aluminum</h3>{run_table(SUB_FEEDERS, SUB_FEET, "al")}
<p class="note">The breaker in the main panel is the feeder rating: 50, 60 or 100 A. A longer run does not change it; it only makes the wire larger.
If the subpanel's real load is lower than the breaker, the drop is lower in the same proportion. <strong>Why other sites show a different number:</strong> {nmb_why}</p>
<h3>Four conductors, and the size of the ground</h3>
<p>A feeder to a subpanel has four conductors: two ungrounded (hot) conductors, a neutral and an equipment grounding conductor.
In the subpanel the neutral bar is isolated from the enclosure and from the ground bar, because the neutral is bonded to ground only at the service (NEC 250.24(B)).
A subpanel in a detached building also needs its own grounding electrode, connected to the ground bar (NEC 250.32).
The charts above size the two hots; run the neutral the same size unless a load calculation allows a smaller one (NEC 220.61).</p>
{grounds}
<p class="note">Minimum equipment grounding conductor from NEC Table 250.122, by the feeder breaker. When the hots are upsized for voltage drop, 250.122(B) increases the ground in proportion.</p>
{ex}
{checked_note(b, path)}</section>
<p><a class="btn" href="{REL}{WIRE_CALC}">Wire size calculator</a> <a class="btn ghost" href="{REL}{BY_DISTANCE}">Wire size by amps and distance</a></p>
{faq_html}
{elec_links(SUBPANEL)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("What size wire for a 50 amp sub panel: copper and aluminum feeder sizes for 50, 60 and 100 A subpanels from 25 to 250 ft, "
            "with voltage drop at each length, the ground wire size and the four-wire rule. NEC 2023.")
    ld = dataset_ld(b, path, "Subpanel feeder wire size by distance", desc, f"{NEC_EDITION}, Tables 310.16 and 250.122",
                    [("Feeder rating", "A"), ("One-way length", "ft"), ("Conductor size", "AWG or kcmil"), ("Voltage drop", "%")], ENGINE_CHECKED[1])
    b.shell(path, "What Size Wire for a 50 Amp Sub Panel? 60 A and 100 A Chart", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- conduit fill chart ----------

def fill_table(t, raceway):
    rows = [[awg(s)] + ["{}{}".format(*fill_count(t, raceway, tr, s)) for tr in FILL_TRADES] for s in FILL_SIZES]
    return table(["Wire \\ trade size, in."] + [TRADE_LABEL[x] for x in FILL_TRADES], rows, "tight")


def fill_marks(t):
    """The footnotes the two charts need, as HTML."""
    marks = {fill_count(t, r, tr, s)[1] for r in t["raceway"] for tr in FILL_TRADES for s in FILL_SIZES}
    one, two, more = (f"{v * 100:.0f} %" for v in t["limits"])
    out = []
    if "*" in marks:
        out.append(f"* The {more} calculation ends in .8 or more. Note 7 to the Chapter 9 tables permits the next whole number in that case, "
                   "so charts that round up, NEC Annex C among them, list one more conductor in these cells. This chart rounds down, as the Electrician Calc app does.")
    if "†" in marks:
        out.append(f"† Two of these conductors are under {more} of the raceway but over the {two} limit for two conductors, so only one fits.")
    return " ".join(out)


def fill_chart_page(b):
    path = FILL_CHART
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("Conduit fill chart", path)])
    t = app_tables(b)
    one, two, more = t["limits"]
    names = t["raceway_name"]

    def n(raceway, trade, size):
        return fill_count(t, raceway, trade, size)[0]

    areas = table(["Trade size", "EMT area, in²", f"EMT at {more * 100:.0f} %, in²", "PVC Sch 40 area, in²", f"PVC Sch 40 at {more * 100:.0f} %, in²"],
                  [[f"{TRADE_LABEL[tr]} in.", f"{raceway_area(t, 'emt', tr):.3f}", f"{raceway_area(t, 'emt', tr) * more:.4f}",
                    f"{raceway_area(t, 'pvc40', tr):.3f}", f"{raceway_area(t, 'pvc40', tr) * more:.4f}"] for tr in FILL_TRADES], "wide tight")
    wires = table(["THHN / THWN-2 wire", "Area with insulation, in²"], [[awg(s), f"{t['thhn'][s]:.4f}"] for s in FILL_SIZES])
    a34, w12, w10 = raceway_area(t, "emt", "3/4"), t["thhn"]["12"], t["thhn"]["10"]
    ex1 = guides.example("12 AWG THHN in ¾ in. EMT", [
        f"Total area of ¾ in. EMT (Chapter 9, Table 4): {a34:.3f} in².",
        f"More than two conductors may fill {more * 100:.0f} % (Table 1): {a34:.3f} × {more:.2f} = {a34 * more:.4f} in².",
        f"One 12 AWG THHN is {w12:.4f} in² with its insulation (Table 5): {a34 * more:.4f} ÷ {w12:.4f} = {a34 * more / w12:.2f}.",
    ], f"Result: {n('emt', '3/4', '12')} conductors.")
    a12 = raceway_area(t, "emt", "1/2")
    mixed = [w10] * 3 + [w12]
    pct, limit, ok = cm.conduit_fill(mixed, a12, t["limits"])
    ex2 = guides.example("three 10 AWG and a 12 AWG ground in ½ in. EMT (mixed sizes)", [
        f"Add the areas: 3 × {w10:.4f} + {w12:.4f} = {sum(mixed):.4f} in².",
        f"Divide by the area of ½ in. EMT: {sum(mixed):.4f} ÷ {a12:.3f} = {pct:.1f} %.",
        f"Four conductors, so the limit is {limit:.0f} %. The ground counts like any other conductor.",
    ], f"Result: {pct:.1f} % fill, {'within' if ok else 'over'} the {limit:.0f} % limit.")
    marks = fill_marks(t)
    faq_html, faq_ld = b.faq([
        ("How many 12 AWG wires fit in 1/2 inch EMT?",
         f"{n('emt', '1/2', '12')} THHN conductors at the {more * 100:.0f} % limit. PVC Schedule 40 of the same trade size is slightly smaller inside and holds {n('pvc40', '1/2', '12')}."),
        ("How many 12 AWG wires fit in 3/4 inch conduit?",
         f"{n('emt', '3/4', '12')} THHN conductors in EMT and {n('pvc40', '3/4', '12')} in PVC Schedule 40. "
         f'With more than three of them carrying current the ampacity has to be reduced: see <a href="{REL}{FILL_12_EMT}">how many 12 AWG wires in 3/4 EMT</a>.'),
        ("What is the 40 % rule?",
         f"NEC Chapter 9, Table 1: conductors may fill {one * 100:.0f} % of a raceway's cross-section when there is one, {two * 100:.0f} % when there are two "
         f"and {more * 100:.0f} % when there are more than two. Fill is the total area of the conductors with their insulation (Table 5) divided by the internal area of the raceway (Table 4)."),
        ("Do ground wires count toward conduit fill?",
         "Yes. Every conductor in the raceway counts, equipment grounding conductors included (Note 3 to the Chapter 9 tables)."),
        ("Why does this chart show one less than my code book in some cells?",
         "Annex C of the NEC rounds up when the calculation ends in .8 or more, as Note 7 to the Chapter 9 tables permits for conductors of one size. "
         "This chart always rounds down, as the Electrician Calc app does, so the marked cells are one lower. Rounding down never overfills the raceway."),
        ("Does fill decide how many circuits I can run in one conduit?",
         "Only partly. With more than three current-carrying conductors in a raceway, NEC 310.15(C)(1) reduces their ampacity, and that limit is often reached before the fill limit."),
        ("Where do these numbers come from?",
         f"{NEC_EDITION}: Chapter 9, Table 1 (fill limits), Table 4 (raceway areas) and Table 5 (THHN and THWN-2 areas), as held in the Electrician Calc app. "
         f"Each count is the largest number of conductors whose total area stays within the limit. The code text is not reproduced here."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>Conduit fill chart: THHN in EMT and PVC Schedule 40</h1>
<p class="lead">How many THHN or THWN-2 conductors, 14 AWG to 1/0, fit in ½ to 2 in. EMT and PVC Schedule 40 conduit, with the 40 % rule and the areas behind every count.</p>
<p class="answer"><strong>Quick answer:</strong> at {more * 100:.0f} % fill, ½ in. EMT holds {n('emt', '1/2', '14')} conductors of 14 AWG THHN, {n('emt', '1/2', '12')} of 12 AWG or {n('emt', '1/2', '10')} of 10 AWG.
¾ in. EMT holds {n('emt', '3/4', '14')}, {n('emt', '3/4', '12')} or {n('emt', '3/4', '10')}, and 1 in. EMT {n('emt', '1', '14')}, {n('emt', '1', '12')} or {n('emt', '1', '10')}
(NEC Chapter 9, Tables 1, 4 and 5, 2023 edition). Counts are rounded down, so some are one lower than Annex C.</p></div>
{app_line(b, "conduit-fill", "Conduit Fill is free. It mixes two wire sizes in one run, such as the circuit conductors and a smaller ground, shows the fill percent against the limit "
          "and names the smallest EMT or PVC Schedule 40 that fits.")}
{byline(f"Areas and limits from {NEC_EDITION}, Chapter 9, Tables 1, 4 and 5, as held in the Electrician Calc app; counts computed with the app's formula.", ENGINE_CHECKED)}
{printbar()}
<section class="guide"><h2>Maximum number of THHN conductors</h2>
<p class="muted">All conductors the same size, THHN or THWN-2, counted by NEC Chapter 9, Table 1: {one * 100:.0f} % fill for one conductor, {two * 100:.0f} % for two, {more * 100:.0f} % for more than two. Grounds count.</p>
<h3>{e(names['emt'])} (electrical metallic tubing)</h3>{fill_table(t, 'emt')}
<h3>{e(names['pvc40'])}</h3>{fill_table(t, 'pvc40')}
<p class="note">{marks}</p>
<p class="note">Fill is only the space. More than three current-carrying conductors in one raceway also lowers their ampacity (NEC 310.15(C)(1)).
Other raceway types have their own areas in Table 4 and are not covered here.</p>
<h3>The 40 % rule: raceway areas</h3>{areas}
<h3>Conductor areas</h3>{wires}
{ex1}{ex2}
{checked_note(b, path)}</section>
<p><a class="btn" href="{REL}{FILL_12_EMT}">How many 12 AWG wires in ¾ in. EMT</a> <a class="btn ghost" href="{REL}{BOX_FILL}">Box fill</a></p>
{faq_html}
{elec_links(FILL_CHART)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("Conduit fill chart: how many THHN conductors from 14 AWG to 1/0 fit in 1/2 to 2 in. EMT and PVC Schedule 40 at 40 % fill, "
            "with raceway and wire areas from NEC Chapter 9, Tables 1, 4 and 5 (2023) and worked examples.")
    ld = dataset_ld(b, path, "Conduit fill chart for THHN conductors", desc, f"{NEC_EDITION}, Chapter 9, Tables 1, 4 and 5",
                    [("Conductor size", "AWG"), ("Trade size", "in"), ("Maximum number of conductors", "")], ENGINE_CHECKED[1])
    b.shell(path, "Conduit Fill Chart: THHN in EMT and PVC Schedule 40 (NEC 2023)", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- how many 12 AWG wires in 3/4 EMT ----------

def fill_12_emt_page(b):
    path = FILL_12_EMT
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("12 AWG wires in ¾ in. EMT", path)])
    t = app_tables(b)
    more = t["limits"][2]
    _, adj = load_factors(b)
    adj = adj[:4]  # 1–3, 4–6, 7–9, 10–20: more than 20 conductors of these sizes do not fit the two conduits

    def n(trade, size):
        return fill_count(t, "emt", trade, size)[0]

    def capped(size, factor):
        return min(ampacity("cu", 90, size) * factor, ampacity("cu", 75, size))

    counts = table(["THHN wire", "½ in. EMT", "¾ in. EMT"], [[awg(s), str(n("1/2", s)), str(n("3/4", s))] for s in ("12", "10")])
    rows = [[f"{lbl} <small>× {f:.2f}</small>", f"{capped('12', f):g} A", awg(wire_size(20, "thhn", "cu", adjust=f)[0]),
             f"{capped('10', f):g} A", awg(wire_size(30, "thhn", "cu", adjust=f)[0])] for lbl, f in adj]
    derate = table(["Current-carrying wires, and the factor", "12 AWG THHN carries", "A 20 A load needs", "10 AWG THHN carries", "A 30 A load needs"], rows, "wide tight stack")
    last12 = [lbl for lbl, f in adj if wire_size(20, "thhn", "cu", adjust=f)[0] == "12"][-1]  # "7–9"
    first10 = next(lbl for lbl, f in adj if wire_size(20, "thhn", "cu", adjust=f)[0] != "12")  # "10–20"
    most12, least10 = last12.split("–")[-1], first10.split("–")[0]
    up20 = awg(wire_size(20, "thhn", "cu", adjust=dict(adj)[first10])[0])
    a34, a1, w12, w10 = raceway_area(t, "emt", "3/4"), raceway_area(t, "emt", "1"), t["thhn"]["12"], t["thhn"]["10"]
    egc20 = ground(b, 20)
    four = cm.conduit_fill([w12] * 8 + [t["thhn"][egc20]], a34, t["limits"])
    five = [w10] * 10 + [t["thhn"][egc20]]
    five34, five1 = cm.conduit_fill(five, a34, t["limits"]), cm.conduit_fill(five, a1, t["limits"])
    ex = guides.example("Five 20 A, 120 V circuits in one conduit", [
        "Each two-wire circuit has a hot and a neutral, and both carry current: five circuits are 10 current-carrying conductors. The ground is not counted for ampacity.",
        f"Table 310.15(C)(1), {first10} conductors: multiply the ampacity by {dict(adj)[first10]:.2f}. 12 AWG THHN starts at {ampacity('cu', 90, '12')} A in the 90 °C column, "
        f"so it carries {capped('12', dict(adj)[first10]):g} A. Not enough for a 20 A circuit: the circuits need {up20}.",
        f"Fill of ten {up20} and one {awg(egc20)} ground: 10 × {w10:.4f} + {t['thhn'][egc20]:.4f} = {sum(five):.4f} in². "
        f"In ¾ in. EMT ({a34:.3f} in²) that is {five34[0]:.1f} %, {'within' if five34[2] else 'over'} the {five34[1]:.0f} % limit; in 1 in. EMT ({a1:.3f} in²) it is {five1[0]:.1f} %.",
        f"Four circuits stay at eight current-carrying conductors, factor {dict(adj)[last12]:.2f}: 12 AWG still carries {capped('12', dict(adj)[last12]):g} A, "
        f"and eight 12 AWG with a {awg(egc20)} ground fill ¾ in. EMT to {four[0]:.1f} %.",
    ], f"Result: four 20 A circuits fit ¾ in. EMT on 12 AWG. A fifth circuit means {up20} and 1 in. EMT.")
    why = (f"<strong>Why other sites give a smaller number:</strong> {n('3/4', '12')} is how many wires physically fit. "
           f"Once more than three of them carry current, NEC 310.15(C)(1) reduces the ampacity of every one, and from {least10} current-carrying conductors up "
           f"12 AWG THHN no longer carries 20 A. That is why {most12} is often given as the practical limit for 20 A circuits.")
    faq_html, faq_ld = b.faq([
        ("How many 12 AWG wires can I put in 3/4 EMT?",
         f"{n('3/4', '12')} THHN or THWN-2 conductors by conduit fill. If they are 20 A circuits, no more than {most12} of them may be current-carrying before the wire has to go up to {up20}."),
        ("How many 12 AWG wires fit in 1/2 EMT?",
         f"{n('1/2', '12')} THHN conductors by fill. All {n('1/2', '12')} can carry current on 20 A circuits: with {last12} current-carrying conductors 12 AWG THHN still carries {capped('12', dict(adj)[last12]):g} A."),
        ("How many 10 AWG wires fit in 3/4 EMT?",
         f"{n('3/4', '10')} THHN conductors by fill, and {n('1/2', '10')} in ½ in. EMT. For 30 A circuits the ampacity limit comes first: "
         f"with more than six current-carrying conductors a full 30 A load needs {awg(wire_size(30, 'thhn', 'cu', adjust=dict(adj)['7–9'])[0])}."),
        ("How many 20 amp circuits can I run in 3/4 conduit?",
         "Four two-wire 120 V circuits on 12 AWG THHN: eight current-carrying conductors and a ground. A fifth circuit takes the count to ten, "
         f"which needs {up20} and, with it, a larger conduit."),
        ("Do neutrals and grounds count?",
         "For fill, every conductor counts, grounds included. For the ampacity adjustment, count the hots and the neutral of each two-wire circuit. "
         "A neutral that carries only the unbalanced current of a multiwire circuit is not counted (NEC 310.15(E)), and grounds are never counted (310.15(F))."),
        ("Where do these numbers come from?",
         f"{NEC_EDITION}: Chapter 9, Tables 1, 4 and 5 for fill, Table 310.16 and Table 310.15(C)(1) for ampacity and its adjustment, 240.4(D) for the breaker limits on small conductors. "
         "They are the tables and formulas of the Electrician Calc app."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>How many 12 AWG wires in ¾ in. EMT?</h1>
<p class="lead">The conduit fill count for 12 AWG and 10 AWG THHN in ½ and ¾ in. EMT, and the ampacity rule that usually stops you before the conduit is full.</p>
<p class="answer"><strong>Quick answer:</strong> {n('3/4', '12')} THHN conductors of 12 AWG fit in ¾ in. EMT at the {more * 100:.0f} % fill limit, and {n('1/2', '12')} fit in ½ in. EMT.
For 10 AWG THHN it is {n('3/4', '10')} and {n('1/2', '10')} (NEC Chapter 9, Tables 1, 4 and 5, 2023 edition).</p>
<p class="answer">That is fill only. With more than three current-carrying conductors in the conduit, NEC 310.15(C)(1) lowers the ampacity of each one:
12 AWG THHN stays good for 20 A circuits up to {most12} current-carrying conductors, and from {least10} up the circuits need {up20}.</p></div>
{app_line(b, "fill-12-emt", "Conduit Fill is free and checks any mix of two wire sizes against the limit. Wire Size, also free, applies the 310.15(C)(1) factor together with the ambient temperature and shows each step.")}
{byline(f"Areas, limits and ampacities from {NEC_EDITION}, as held in the Electrician Calc app; counts and sizes computed with the app's formulas.", ENGINE_CHECKED)}
{printbar()}
<section class="guide"><h2>Conduit fill: how many fit</h2>
<p class="muted">THHN or THWN-2, all one size, {more * 100:.0f} % fill for more than two conductors (NEC Chapter 9, Table 1). Grounds count toward fill.</p>
{counts}
<p class="note">¾ in. EMT has {a34:.3f} in² inside (Table 4); {more * 100:.0f} % of it is {a34 * more:.4f} in². One 12 AWG THHN is {w12:.4f} in² (Table 5), and {a34 * more:.4f} ÷ {w12:.4f} = {a34 * more / w12:.2f}, so {n('3/4', '12')} fit.</p>
<h2>Ampacity: how many may carry current</h2>
<p>{why}</p>
{derate}
<p class="note">THHN is a 90 °C conductor, so the adjustment starts from the 90 °C column of Table 310.16 ({ampacity('cu', 90, '12')} A for 12 AWG, {ampacity('cu', 90, '10')} A for 10 AWG) and the result may not exceed the 75 °C termination value
({ampacity('cu', 75, '12')} A and {ampacity('cu', 75, '10')} A). 30 °C ambient; a hot attic or roof lowers these further. Breakers on 12 and 10 AWG copper stay at 20 and 30 A (240.4(D)).</p>
{ex}
{checked_note(b, path)}</section>
<p><a class="btn" href="{REL}{FILL_CHART}">Conduit fill chart, 14 AWG to 1/0</a> <a class="btn ghost" href="{REL}{AMPACITY_PAGE}">Ampacity chart</a></p>
{faq_html}
{elec_links(FILL_12_EMT)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = (f"How many 12 AWG wires fit in 3/4 EMT: {n('3/4', '12')} THHN conductors by NEC conduit fill ({n('1/2', '12')} in 1/2 in. EMT; 10 AWG: {n('3/4', '10')} and {n('1/2', '10')}), "
            "and how the ampacity adjustment of 310.15(C)(1) limits the number of 20 A circuits.")
    ld = dataset_ld(b, path, "12 AWG and 10 AWG THHN in 1/2 and 3/4 in. EMT", desc, f"{NEC_EDITION}, Chapter 9, Tables 1, 4 and 5; Tables 310.16 and 310.15(C)(1)",
                    [("Conductor size", "AWG"), ("Trade size", "in"), ("Maximum number of conductors", ""), ("Adjusted ampacity", "A")], ENGINE_CHECKED[1])
    b.shell(path, "How Many 12 AWG Wires in 3/4 EMT? Fill Count and Derating", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- box fill ----------

def box_fill_page(b):
    path = BOX_FILL
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("Box fill", path)])
    t = app_tables(b)
    vol, boxes = t["box"], t["boxes"]

    def smallest(need):
        return next(((name, v) for name, v in boxes if v >= need - 1e-9), None)

    def holds_n(volume, size):
        return cm.box_fill(0, False, 0, 0, 0, vol[size], volume)[3]

    per = table(["Conductor size", "Volume for each conductor"], [[awg(s), f"{v:.2f} in³"] for s, v in vol.items()])
    counts = table(["What is in the box", "Volume allowances", "NEC"], [
        ["Each insulated conductor that enters the box and is spliced or ends there", "1", "314.16(B)(1)"],
        ["A conductor that passes through without a splice", "1", "314.16(B)(1)"],
        ["Pigtails that start and end inside the box", "0", "314.16(B)(1)"],
        ["Internal cable clamps, however many", "1", "314.16(B)(2)"],
        ["Fixture studs or hickeys: once for each type present", "1", "314.16(B)(3)"],
        ["Each switch or receptacle (one yoke)", "2", "314.16(B)(4)"],
        ["Ground wires: up to four", "1", "314.16(B)(5)"],
        ["Each ground wire over four", "¼", "314.16(B)(5)"],
    ], "wide tight wrap1")
    cap = table(["Metal box", "Volume", "14 AWG", "12 AWG", "10 AWG"],
                [[e(name), f"{v:g} in³"] + [str(holds_n(v, s)) for s in ("14", "12", "10")] for name, v in boxes], "wide tight wrap1")
    # Example 1: two 12/2 cables to a receptacle in a metal box with clamps.
    a1, need1, _, _ = cm.box_fill(4, True, 0, 1, 2, vol["12"])
    box1 = smallest(need1)
    ex1 = guides.example("a receptacle fed by two 12/2 cables, metal box with internal clamps", [
        "Insulated conductors: two cables with a hot and a neutral each, 4 allowances.",
        "Internal clamps: 1. Receptacle: 2. Two ground wires: 1.",
        f"Total: 4 + 1 + 2 + 1 = {a1:g} allowances.",
        f"All wires are 12 AWG at {vol['12']:.2f} in³ each: {a1:g} × {vol['12']:.2f} = {need1:g} in³.",
    ], f"Result: {need1:g} in³. The smallest standard metal box is a {box1[0]} box ({box1[1]:g} in³).")
    # Example 2: five 12/2 cables spliced in a junction box, to show the quarter allowance for grounds over four.
    a2, need2, _, _ = cm.box_fill(10, True, 0, 0, 5, vol["12"])
    old2 = cm.box_fill(10, True, 0, 0, 4, vol["12"])
    box2 = smallest(need2)
    ex2 = guides.example("a junction box with five 12/2 cables spliced, internal clamps, no device", [
        "Insulated conductors: five cables with a hot and a neutral each, 10 allowances.",
        "Internal clamps: 1.",
        "Five ground wires: 1 for the first four and ¼ for the fifth, 1¼ allowances.",
        f"Total: 10 + 1 + 1¼ = {a2:g} allowances. {a2:g} × {vol['12']:.2f} = {need2:.2f} in³.",
    ], f"Result: {need2:.2f} in³. The smallest standard metal box is a {box2[0]} box ({box2[1]:g} in³).")
    sq15, sq21 = dict(boxes)["4 in square × 1½ in"], dict(boxes)["4 in square × 2⅛ in"]
    dev = dict(boxes)["3 × 2 × 3½ in device"]
    faq_html, faq_ld = b.faq([
        ("How many 12 AWG wires can be in a 4 inch square box?",
         f"A 4 in square × 1½ in box is {sq15:g} in³ and takes {holds_n(sq15, '12')} conductors of 12 AWG; the 2⅛ in deep one is {sq21:g} in³ and takes {holds_n(sq21, '12')}. "
         "That is with nothing else in the box: a device counts as two conductors, clamps as one and the grounds as one."),
        ("How many 14 AWG wires fit in a single-gang box?",
         f"A 3 × 2 × 3½ in metal device box is {dev:g} in³: {holds_n(dev, '14')} conductors of 14 AWG, or {holds_n(dev, '12')} of 12 AWG, before devices, clamps and grounds are counted. "
         "For a plastic box use the volume stamped inside it."),
        ("Do ground wires count in box fill?",
         "Yes, but together: up to four ground wires count as one conductor, and each one over four adds a quarter (NEC 314.16(B)(5))."),
        ("Why do older guides count all the grounds as one?",
         f"Before the 2020 edition every ground in the box shared a single allowance. Since NEC 2020 each ground over four adds a quarter, so the junction box in the second example "
         f"needs {a2:g} allowances ({need2:.2f} in³) where an older guide says {old2[0]:g} ({old2[1]:g} in³)."),
        ("Do pigtails and wire nuts count?",
         "No. A pigtail that starts and ends inside the box is not counted, and neither are wire connectors."),
        ("Does a switch or receptacle count?",
         "Yes: each device on one yoke counts as two conductors of the largest size connected to it."),
        ("What if the wires are different sizes?",
         "The code takes each item at the size of the conductor it belongs to: a device at the largest wire connected to it, clamps at the largest wire in the box. "
         "This page and the app use one size for everything, the largest wire in the box, which never gives a smaller box than the code."),
        ("Where do these numbers come from?",
         f"{NEC_EDITION}: 314.16(B) and Table 314.16(B)(1) for the volume allowances, Table 314.16(A) for the metal box volumes, as held in the Electrician Calc app. The code text is not reproduced here."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>Box fill: NEC 314.16 chart and examples</h1>
<p class="lead">The volume each conductor needs, what counts as a conductor, how many wires common metal boxes take, and two worked examples.</p>
<p class="answer"><strong>Quick answer:</strong> each conductor needs {vol['14']:.2f} in³ of box for 14 AWG, {vol['12']:.2f} in³ for 12 AWG and {vol['10']:.2f} in³ for 10 AWG (NEC Table 314.16(B)(1), 2023 edition).
Count one for each insulated conductor, one for all internal clamps, one for a fixture stud or hickey, two for each switch or receptacle and one for up to four ground wires, then multiply by the volume for the wire size.
Two 12/2 cables and a receptacle in a box with clamps come to {a1:g} × {vol['12']:.2f} = {need1:g} in³.</p></div>
{app_line(b, "box-fill", "box fill is part of the free Conduit Fill calculator. Enter what is in the box and it shows the volume needed, the working, the smallest standard metal box and how many more conductors still fit.")}
{byline(f"Volumes from {NEC_EDITION}, Tables 314.16(A) and 314.16(B)(1), as held in the Electrician Calc app; examples computed with the app's formula.", ENGINE_CHECKED)}
{printbar()}
<section class="guide"><h2>Volume allowance per conductor</h2>
<p class="muted">NEC Table 314.16(B)(1): the free space in the box required for each conductor.</p>
{per}
<h3>What counts</h3>{counts}
<p class="note">Add the allowances and multiply by the volume for the wire size. The box volume must be at least that: Table 314.16(A) for standard metal boxes, the marked volume for plastic boxes, plus the marked volume of any extension or plaster ring.</p>
<h3>Common metal boxes: how many conductors they take</h3>
<p class="muted">Box volume from Table 314.16(A), divided by the volume per conductor and rounded down. Nothing else in the box: subtract two for each device, one for clamps and one for the grounds.</p>
{cap}
{ex1}{ex2}
{checked_note(b, path)}</section>
<p><a class="btn" href="{REL}{FILL_CHART}">Conduit fill chart</a> <a class="btn ghost" href="{REL}{WIRE_CALC}">Wire size calculator</a></p>
{faq_html}
{elec_links(BOX_FILL)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("Box fill by NEC 314.16 (2023): volume per conductor from Table 314.16(B)(1), what counts (devices, clamps, grounds, fixture studs), "
            "how many 14, 12 and 10 AWG conductors common metal boxes take, and two worked examples.")
    b.shell(path, "Box Fill Chart and Examples: NEC 314.16 (2023)", desc, body, "t-elec", None,
            [article_ld(b, path, "Box fill: NEC 314.16 chart and examples", desc, ENGINE_CHECKED[1]), faq_ld], JS)


# ---------- EV charger wire size ----------

def ev_wire_page(b):
    path = EV_WIRE
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("EV charger wire size", path)])

    def circuit(amps):
        """(breaker, copper THHN, copper NM-B or None, copper ground) for a charger drawing `amps` continuously."""
        cu, _, ocpd, _ = wire_size(amps, "thhn", "cu", True)
        return ocpd, cu, nmb_for(amps, True), ground(b, ocpd)

    rows = []
    for a in EV_AMPS:
        ocpd, cu, nm, egc = circuit(a)
        rows.append([f"{a} A <small>{a * 240 / 1000:.1f} kW</small>", f"{ocpd} A", awg(cu), awg(nm) if nm else "–", awg(egc)])
    summary = table(["Charger current, power at 240 V", "Breaker (125&nbsp;%)", "Copper THHN in conduit", "Copper NM-B cable", "Copper ground"], rows, "wide tight stack")

    def line(a):
        ocpd, cu, _, _ = circuit(a)
        return f"{a} A charger: {ocpd} A breaker and {awg(cu)} copper for runs up to {holds(a, EV_FEET, cont=True)[1]} ft"

    o48, cu48, nm48, _ = circuit(48)
    why = (f"<strong>Why other sites show a different number:</strong> the wiring method. THHN in conduit on 75 °C terminals is read from the 75 °C column, where {awg(cu48)} copper is {ampacity('cu', 75, cu48)} A. "
           f"NM-B cable is held to the 60 °C column (NEC 334.80), where {awg(cu48)} is {ampacity('cu', 60, cu48)} A: less than the {o48} A a 48 A charger needs, so NM-B has to be {awg(nm48)}.")
    s, pick, pct = size_for(48, 200, 240, cont=True)
    egc, up = ground(b, o48), ground_upsized(b, o48, pick, s)
    ex = guides.example("48 A charger, 200 ft from the panel, copper THHN in conduit", [
        f"Charging is a continuous load: 48 A × 125 % = {48 * 1.25:g} A, so the breaker is {o48} A.",
        f"By ampacity (75 °C column, NEC Table 310.16): {awg(pick)} copper, {ampacity('cu', 75, pick)} A.",
        f"Voltage drop of {awg(pick)} at 200 ft and 48 A: {pct_at(pick, 48, 200):.2f} % of 240 V. Over 3 %.",
        f"Next size up, {awg(s)}: {pct:.2f} %. Under 3 %.",
        f"Ground: Table 250.122 gives {awg(egc)} copper for a {o48} A breaker; with the wire upsized from {awg(pick)} to {awg(s)}, 250.122(B) increases it to {awg(up)}.",
    ], f"Result: {awg(s)} copper with a {awg(up)} ground on a {o48} A breaker.")
    o40, cu40, nm40, _ = circuit(40)
    faq_html, faq_ld = b.faq([
        ("What size wire for a 48 amp EV charger?",
         f"{awg(cu48)} copper THHN in conduit on a {o48} A breaker, for runs up to {holds(48, EV_FEET, cont=True)[1]} ft. In NM-B cable it has to be {awg(nm48)} copper."),
        ("What size breaker for a 40 amp EV charger?",
         f"{o40} A: the charger is a continuous load, so the breaker is at least 125 % of 40 A. The wire is {awg(cu40)} copper THHN in conduit, or {awg(nm40)} copper NM-B."),
        ("What size wire for a 50 amp EV charger circuit?",
         f"A {o40} A circuit carries a charger set to 40 A. It needs {awg(cu40)} copper THHN in conduit or {awg(nm40)} copper NM-B cable, larger on long runs: see the chart."),
        (f"Can I use {awg(cu48)} NM-B (Romex) for a 48 amp charger?",
         f"No. NM-B is limited to the 60 °C column, where {awg(cu48)} copper is {ampacity('cu', 60, cu48)} A, and a 48 A charger needs a {o48} A circuit. "
         f"Use {awg(nm48)} NM-B, or {awg(cu48)} THHN in conduit, or set the charger to 40 A on a {o40} A breaker."),
        ("Why 125 %?",
         "An EV charger can run at full current for hours, so the NEC treats it as a continuous load: the breaker is rated at least 125 % of the charger's maximum current (NEC 625.41), "
         "and the conductors are sized for the same 125 % (210.19(A)(1))."),
        ("Does a longer run change the breaker?",
         "No. The breaker follows the charger. A longer run only makes the wire larger to keep the voltage drop within 3 %."),
        ("Can my panel take the charger?",
         "That is a separate question from the wire size: the existing service has to carry the new load. NEC 220.83 and 220.87 are the two ways to check an existing house. "
         "The EV Charger &amp; Heat Pump Check in the Electrician Calc app (Pro) does both."),
        ("How are these sizes worked out?",
         "The breaker is the next standard size at or above 125 % of the charger current. The wire is the smallest copper conductor whose ampacity in the 75 °C column of NEC Table 310.16 covers that, "
         f"then upsized until the voltage drop at the charger current is 3 % or less on 240 V (K = {K_CU:.2f} Ω·cmil/ft). These are the formulas of the wire size calculator on this site and of the Electrician Calc app."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>EV charger wire size by amps and distance</h1>
<p class="lead">Breaker and copper wire for 32, 40, 48 and 80 amp Level 2 chargers on 240 V, with the 125 % continuous-load rule and the voltage drop from 25 to 200 ft.</p>
<p class="answer"><strong>Quick answer:</strong> {line(48)}. {line(40)}. {line(32)}. {line(80)}.
That is copper THHN in conduit on 75 °C terminals (NEC Table 310.16, 2023 edition), with voltage drop within 3 % on 240 V. The breaker is 125 % of the charger current, because the NEC treats charging as a continuous load (625.41).</p></div>
{app_line(b, "ev-wire", "Wire Size is free and sizes the charger circuit for any current, length and wire type, with a switch for continuous loads. "
          "The EV Charger &amp; Heat Pump Check (Pro) answers whether the existing service can take the charger, by NEC 220.83 or 220.87.")}
{byline(f"Ampacities from {NEC_EDITION}, Table 310.16; sizes and voltage drop computed with the formulas of the Electrician Calc app.", ENGINE_CHECKED)}
{printbar()}
<section class="guide"><h2>Breaker and wire for each charger</h2>
<p class="muted">Charger current is what the charger draws, not the breaker. 240 V single phase, copper, 75 °C terminals, 30 °C ambient, no more than three current-carrying conductors. Short runs; see the next chart for length.</p>
{summary}
<p class="note">{why} NM-B is not made above 2 AWG (the dash in the chart), so an 80 A charger is wired with THHN in conduit. The ground is the minimum of NEC Table 250.122 for the breaker.</p>
<h3>Copper THHN by run length</h3>
<p class="muted">The smallest wire that carries the charger and keeps voltage drop at or under 3 % at the charger current, with the drop at that size. Length is one way.</p>
{run_table(EV_AMPS, EV_FEET, cont=True)}
{ex}
{checked_note(b, path)}</section>
<p><a class="btn" href="{REL}{WIRE_CALC}">Wire size calculator</a> <a class="btn ghost" href="{REL}{BY_DISTANCE}">Wire size by amps and distance</a></p>
{faq_html}
{elec_links(EV_WIRE)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = ("EV charger wire size chart: breaker and copper wire for 32, 40, 48 and 80 A Level 2 chargers with the 125 % continuous-load rule, "
            "THHN and NM-B, by run length from 25 to 200 ft with voltage drop. NEC 2023.")
    ld = dataset_ld(b, path, "EV charger wire size by amps and distance", desc, f"{NEC_EDITION}, Tables 310.16 and 250.122",
                    [("Charger current", "A"), ("Breaker", "A"), ("One-way length", "ft"), ("Conductor size", "AWG"), ("Voltage drop", "%")], ENGINE_CHECKED[1])
    b.shell(path, "EV Charger Wire Size Chart: 32, 40, 48 and 80 Amp by Distance", desc, body, "t-elec", None, [ld, faq_ld], JS)


# ---------- hub ----------

# ---------- NEC edition by state ----------

NFPA_MAP = "https://www.nfpa.org/education-and-research/electrical/nec-enforcement-maps"
NFPA_AS_OF = "3 August 2026"  # the date NFPA's page gives for its own table
STATES_CHECKED = ("17 November 2026", "2026-11-17")  # the day the table below was read against NFPA's page again
OWNER_CHECKED = "16 November 2026"
# What NFPA's row says beyond the app's note.
STATE_EXTRA = {
    "NC": "NFPA lists this edition for other than one- and two-family dwellings.",
    "IA": "NEC 2026 is being adopted.",
    "KY": "NEC 2026 is being adopted.",
    "NE": "NEC 2026 is being adopted.",
    "MI": "NEC 2026 is being adopted for commercial work.",
}
OWNER_TEXT = {"allowed": "Yes", "notAllowed": "No", "local": "Decided by the city or county"}


def state_codes(b):
    """The rows of the Electrician Calc app's state_code.dart, so the page and the app give the same answer. Read
    from origin/main, because the app's checkout is often on a work branch that does not have the file."""
    repo, rel = b.ROOT / "Calculator_for_electrical", "lib/feature/engine/state_code.dart"
    got = subprocess.run(["git", "-C", str(repo), "show", f"origin/main:{rel}"], capture_output=True, text=True)
    text = got.stdout if got.returncode == 0 else (repo / rel).read_text()
    rows = []
    for block in text[text.index("const stateCodes"):].split("StateCode(")[1:]:
        code, name = re.match(r"\s*'([A-Z]{2})',\s*'([^']+)'", block).groups()

        def s(field):
            m = re.search(rf"\b{field}:\s*'([^']*)'", block)
            return m.group(1) if m else ""

        ed, own = re.search(r"\bedition:\s*(\d{4})", block), re.search(r"Homeowner\.(\w+)", block)
        rows.append({"code": code, "name": name, "edition": int(ed.group(1)) if ed else None, "effective": s("effective"),
                     "note": s("note"), "source": s("source") or (NFPA_MAP if "_nfpa" in block else ""),
                     "unconfirmed": "unconfirmed: true" in block, "owner": own.group(1) if own else "unknown",
                     "owner_source": s("homeownerSource"), "owner_condition": s("ownerCondition"), "board": s("board")})
    return rows


def names(rows):
    n = [r["name"] for r in rows]
    return n[0] if len(n) == 1 else ", ".join(n[:-1]) + " and " + n[-1]


def nec_by_state_page(b):
    path = NEC_BY_STATE
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB), ("NEC edition by state", path)])
    rows = state_codes(b)
    by_ed = Counter(r["edition"] for r in rows if r["edition"])
    of = lambda year: [r for r in rows if r["edition"] == year]  # noqa: E731
    local = [r for r in rows if not r["edition"] and not r["unconfirmed"]]
    top = by_ed.most_common(1)[0][0]
    rest = ", ".join(f"NEC {y} in {by_ed[y]}" for y in sorted(by_ed, reverse=True) if y != top)
    answer = (f"NEC {top} is the most common statewide edition, in force in {by_ed[top]} states. The others: {rest}. "
              f"NEC 2026 is in force in {names(of(2026))}. {names(local)} have no statewide edition that covers houses: "
              "there the city or county decides. Counts include the District of Columbia.")

    def edition(r):
        if r["edition"]:
            return f"<strong>NEC {r['edition']}</strong>"
        return "Not confirmed" if r["unconfirmed"] else "No statewide edition"

    def note(r):
        return " ".join(x for x in (e(r["note"]), STATE_EXTRA.get(r["code"], "")) if x) or "—"

    def link(u):
        return f'<a href="{e(u)}" rel="noopener">{e(re.sub(r"^https?://(www\.)?", "", u).split("/")[0])}</a>' if u else "—"

    main = table(["State", "NEC edition in force", "In force since", "Notes"],
                 [[f'<td id="{r["code"].lower()}">{e(r["name"])}</td>', edition(r), r["effective"] or "—", note(r)] for r in rows], "states")
    owners = [r for r in rows if r["owner"] != "unknown"]
    owner = table(["State", "May the owner wire their own house?", "The state's conditions", "Source"],
                  [[e(r["name"]), OWNER_TEXT[r["owner"]], e(r["owner_condition"]) or "Ask the local building department.",
                    link(r["owner_source"])] for r in owners], "states owners")
    pending = [r for r in rows if re.search(r"being adopted|expected|from 1 Jan", note(r))]
    faq_html, faq_ld = b.faq([
        ("Which states use the 2026 NEC?",
         f"{names(of(2026))}, as of {STATES_CHECKED[0]}. NFPA's own table is dated {NFPA_AS_OF}, so a state that switched after that day may still show its older edition here."),
        ("Which states have no statewide electrical code?",
         f"{names(local)}. In Arizona, Mississippi and Missouri the NEC is adopted city by city or county by county. Illinois and Kansas have a state rule based on NEC 2008, "
         "but it does not cover houses in places with their own code, so the local edition is the one that counts."),
        ("Which NEC edition do most states use?",
         f"NEC {top}: {by_ed[top]} states enforce it statewide. " + " ".join(f"NEC {y}: {by_ed[y]}." for y in sorted(by_ed, reverse=True) if y != top)),
        ("Is the NEC a federal law?",
         "No. The National Electrical Code is a model code published by NFPA as NFPA 70. It becomes law only where a state, county or city adopts an edition, often with its own amendments."),
        ("How often is the NEC updated?",
         "Every three years: 2017, 2020, 2023, 2026. States adopt each edition on their own schedule, which is why several editions are in force at the same time."),
        ("How do I find the edition my city enforces?",
         "Ask the building department that issues the electrical permit, or read its permit page. A city may amend the state's edition or enforce a newer one, and the inspector's edition is the one your work is checked against."),
        ("Which edition do the calculators on this site use?",
         f"{NEC_EDITION}: Table 310.16 for ampacity, Table 250.122 for grounding and Chapter 9 for conduit fill. If your state is on another edition, check the article numbers against that edition."),
    ])
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Electrical reference</div>
<h1>NEC edition by state: which electrical code each state uses</h1>
<p class="lead">The National Electrical Code edition in force in each of the 50 states and the District of Columbia, the day it took effect and what is being adopted next.</p>
<p class="answer"><strong>Quick answer:</strong> {answer}</p></div>
{byline(f'Editions and dates from <a href="{NFPA_MAP}" rel="noopener">NFPA\'s NEC enforcement table</a>, which NFPA dates {NFPA_AS_OF}; the District of Columbia from its own code page. '
        "It is the same list the Electrician Calc app uses.", STATES_CHECKED)}
{printbar("Print this table")}
<section class="guide"><h2>NEC edition in force, state by state</h2>
<p class="muted">The statewide edition is the starting point. Cities and counties may amend it or enforce a newer one, and the inspector has the final word.</p>
{main}
<p class="note">A link to one state ends with its two-letter code, for example <a href="#tx">#tx</a> for Texas.
“No statewide edition” means the state leaves the choice to cities and counties, or its own rule does not cover houses.</p>
<h3>States where a newer edition is on the way</h3>
<p>{names(pending)}. The note in each row says which edition and, where the state has set one, the date.</p>
<h3>Why the edition matters</h3>
<p>An inspector checks the work against the edition the jurisdiction adopted, not the newest one. Article numbers and requirements move between editions,
so a rule quoted from NEC 2023 may read differently, or sit in another section, where NEC 2017 or 2020 is still in force. Before a job in another state, look up its edition first.</p>
{checked_note(b, path)}</section>
<section class="guide"><h2>May a homeowner do their own electrical work?</h2>
<p class="muted">Read from each state's statute or licensing board on {OWNER_CHECKED}, for the {len(owners)} states we have checked so far. A permit and an inspection are still required almost everywhere.
States not listed here have not been checked: ask the local building department.</p>
{owner}</section>
{b.promo("electrician-calc", "nec-by-state", "Wire size with derating, panel planner, motors, solar and 21 calculators with step-by-step working and PDF reports.")}
{faq_html}
{elec_links(NEC_BY_STATE)}
<p class="note">{ELEC_NOTE}</p>
"""
    desc = (f"Which NEC edition each state enforces in 2026: all 50 states and DC with the effective date, pending adoptions and local-adoption states. "
            f"NEC {top} leads with {by_ed[top]} states. Checked {STATES_CHECKED[0]}.")
    ld = dataset_ld(b, path, "NEC edition in force by US state", desc, "NFPA, NEC enforcement table",
                    [("NEC edition", "year"), ("Effective date", "date")], STATES_CHECKED[1])
    b.shell(path, "NEC Edition by State (2026): Which Electrical Code Each State Uses", desc, body, "t-elec", None, [ld, faq_ld], JS)


def hub_page(b):
    crumb_html = crumbs([("Tools", "index.html"), ("Electrical", HUB)])
    cards = [
        (VD_CALC, "Calculator", "Voltage drop calculator", "AWG or mm², copper or aluminum, single phase, three phase and DC."),
        (WIRE_CALC, "Calculator", "Wire size calculator", "Conductor and breaker by NEC Table 310.16, with a voltage drop check."),
        (AWG_MM2, "Calculator", "AWG to mm² converter", "AWG and kcmil to mm² and back."),
        (AMPACITY_PAGE, "Chart", "Ampacity chart (NEC 310.16)", "Copper and aluminum, 60/75/90 °C, with correction factors."),
        (BY_DISTANCE, "Chart", "Wire size by amps and distance", "15 to 100 A over 25 to 300 ft at 120 V and 240 V."),
        (VD_12AWG, "Chart", "12 AWG voltage drop per foot", "Millivolts per amp per foot and maximum run length."),
        (VD_3PH, "Guide", "Three-phase voltage drop", "The 1.732 formula with a chart for 208, 240 and 480 V."),
        (VD_12V, "Chart", "12 V DC voltage drop", "Wire size for 3 % and 10 % drop on low-voltage DC runs."),
        (SUBPANEL, "Chart", "Wire size for a 50 amp sub panel", "50, 60 and 100 A feeders, copper and aluminum, 25 to 250 ft."),
        (EV_WIRE, "Chart", "EV charger wire size", "32 to 80 A chargers: breaker and copper wire by run length."),
        (FILL_CHART, "Chart", "Conduit fill chart", "THHN in EMT and PVC Schedule 40, 1/2 to 2 in., at 40 % fill."),
        (FILL_12_EMT, "Guide", "How many 12 AWG wires in 3/4 EMT", "The fill count, and what derating leaves of it."),
        (BOX_FILL, "Guide", "Box fill (NEC 314.16)", "Volume per conductor, what counts and two worked examples."),
        (NEC_BY_STATE, "Reference", "NEC edition by state", "The edition each state enforces, its effective date and what is pending."),
    ]
    grid = "".join(f'<a class="card" href="{REL}{p}"><span class="tag">{tag}</span><h3>{e(h)}</h3><p>{e(d)}</p></a>' for p, tag, h, d in cards)
    body = f"""{CSS}
{crumb_html}
<div class="hero"><div class="eyebrow">Free electrical tools</div><h1>Electrical calculators and charts</h1>
<p class="lead">Voltage drop, wire size and ampacity for NEC work, with the formulas, tables and worked examples behind every number.</p></div>
<div class="grid">{grid}</div>
{b.promo("electrician-calc", "elec-hub", "Wire size with derating, panel planner, motors, solar and 21 calculators with step-by-step working and PDF reports.")}
<p class="note">{ELEC_NOTE}</p>
"""
    b.shell(HUB, "Electrical Calculators and Charts: Voltage Drop, Wire Size, Ampacity | Free",
            "Free electrical tools: voltage drop and wire size calculators, the NEC 310.16 ampacity chart, wire size by amps and distance, and voltage drop references.",
            body, "t-elec", None)


# Cards in the same shape as build.CALCS (path, tag, title, text, theme), for the home page and llms.txt.
CARDS = [
    (HUB, "Electrical", "All electrical tools", "Calculators, charts and guides in one place.", "t-elec"),
    (AMPACITY_PAGE, "Electrical", "Ampacity chart (NEC 310.16)", "Copper and aluminum, 60/75/90 °C columns.", "t-elec"),
    (BY_DISTANCE, "Electrical", "Wire size by amps and distance", "15 to 100 A over 25 to 300 ft.", "t-elec"),
    (VD_12AWG, "Electrical", "12 AWG voltage drop per foot", "Per amp per foot, with maximum run length.", "t-elec"),
    (VD_3PH, "Electrical", "Three-phase voltage drop", "Formula, chart and example.", "t-elec"),
    (VD_12V, "Electrical", "12 V DC voltage drop", "Wire size for 3 % and 10 % drop.", "t-elec"),
    (SUBPANEL, "Electrical", "Wire size for a 50 amp sub panel", "50, 60 and 100 A feeders by distance, copper and aluminum.", "t-elec"),
    (EV_WIRE, "Electrical", "EV charger wire size", "32 to 80 A chargers: breaker and wire by run length.", "t-elec"),
    (FILL_CHART, "Electrical", "Conduit fill chart", "THHN in EMT and PVC Schedule 40 at 40 % fill.", "t-elec"),
    (FILL_12_EMT, "Electrical", "How many 12 AWG wires in 3/4 EMT", "Fill count and the derating that limits it.", "t-elec"),
    (BOX_FILL, "Electrical", "Box fill (NEC 314.16)", "Volume per conductor, what counts, worked examples.", "t-elec"),
    (NEC_BY_STATE, "Electrical", "NEC edition by state", "Which NEC edition each state enforces, with dates and sources.", "t-elec"),
]


def build(b):
    hub_page(b)
    ampacity_page(b)
    by_distance_page(b)
    vd_12awg_page(b)
    vd_3ph_page(b)
    vd_12v_page(b)
    subpanel_page(b)
    fill_chart_page(b)
    fill_12_emt_page(b)
    box_fill_page(b)
    ev_wire_page(b)
    nec_by_state_page(b)
