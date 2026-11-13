"""Electrical reference pages: the NEC Table 310.16 ampacity chart, wire size by amps and distance, and voltage drop
references for 12 AWG, three phase and 12 V DC, plus the electrical hub.

Ampacities, wire sizes and voltage drops are computed with the functions and tables in guides.py, which mirror
assets/calc.js; tests/test_pages.py runs calc.js itself against the numbers on these pages. Correction factors are
read from the Electrician Calc app (nec_tables.dart), so the site never drifts from the app.
"""
import re
from html import escape as e

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
             (VD_3PH, "Three-phase voltage drop"), (VD_12V, "12 V DC voltage drop"), (AWG_MM2, "AWG to mm²"), (HUB, "All electrical tools")]
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


def size_for(amps, feet, volts, cond="cu", supply="single", limit=3.0):
    """The calculator's pick: smallest size by ampacity (THHN, 75 °C terminations), then upsized until the drop is
    within `limit` percent. Returns (size or None, size by ampacity, drop %)."""
    pick, _, _, _ = wire_size(amps, "thhn", cond)
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


# ---------- hub ----------

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
]


def build(b):
    hub_page(b)
    ampacity_page(b)
    by_distance_page(b)
    vd_12awg_page(b)
    vd_3ph_page(b)
    vd_12v_page(b)
