"""Static answer blocks for the calculator pages: a quick answer, a table of common cases and a worked example.

The numbers are computed here with the same formulas as assets/calc.js, so the page text, the tables and the
live calculator agree. Crawlers and AI search read this HTML; the live result needs JavaScript.
"""
import json
import math
from datetime import date
from html import escape as e
from pathlib import Path

AUTHOR = "Andrii Zhukovskyi"
ABOUT = "https://zhukovskyi.space/about/"  # who makes these tools
# The day the sources were last read against the checked examples (verification.json).
CHECKED = date.fromisoformat(json.loads((Path(__file__).resolve().parent / "verification.json").read_text())["checked"])
CHECKED_TEXT = f"{CHECKED.day} {CHECKED:%B %Y}"

# ---------- shared ----------


def fmt(x, d=0):
    return f"{x:,.{d}f}"


def table(caption, head, rows, note=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    n = f'<p class="note">{note}</p>' if note else ""
    return f'<h3>{caption}</h3><div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>{n}'


def example(title, steps, result):
    li = "".join(f"<li>{s}</li>" for s in steps)
    return f'<h3>Worked example: {title}</h3><ol class="steps">{li}</ol><p><strong>{result}</strong></p>'


def guide(h2, parts):
    by = (f'<p class="note byline">Made and checked by <a href="{ABOUT}">{AUTHOR}</a>. Formulas and sources are in the questions below '
          f'and in the <a href="{{rel}}methodology.html">methodology</a>. Checked against the sources on {CHECKED_TEXT}: '
          f'<a href="{{rel}}verification.html">see the examples</a>.</p>')
    return f'<section class="guide"><h2>{h2}</h2>{"".join(parts)}{by}</section>'


def answer(text):
    return f'<p class="answer"><strong>Quick answer:</strong> {text}</p>'


# ---------- electrical (same as calc.js) ----------

RHO20 = {"cu": 0.017241, "al": 0.028264}
RHO_IEC = {"cu": 0.0225, "al": 0.036}
MM2_PER_CMIL = 0.000506707
NEC = [("18", 1620), ("16", 2580), ("14", 4110), ("12", 6530), ("10", 10380), ("8", 16510), ("6", 26240), ("4", 41740),
       ("3", 52620), ("2", 66360), ("1", 83690), ("1/0", 105600), ("2/0", 133100), ("3/0", 167800), ("4/0", 211600),
       ("250", 250000), ("300", 300000), ("350", 350000), ("400", 400000), ("500", 500000)]
IEC = [0.5, 0.75, 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
NEC_SIZES = ["14", "12", "10", "8", "6", "4", "3", "2", "1", "1/0", "2/0", "3/0", "4/0", "250", "300", "350", "400", "500"]
AMPACITY = {
    "cu": {60: [15, 20, 30, 40, 55, 70, 85, 95, 110, 125, 145, 165, 195, 215, 240, 260, 280, 320],
           75: [20, 25, 35, 50, 65, 85, 100, 115, 130, 150, 175, 200, 230, 255, 285, 310, 335, 380],
           90: [25, 30, 40, 55, 75, 95, 115, 130, 145, 170, 195, 225, 260, 290, 320, 350, 380, 430]},
    "al": {60: [0, 15, 25, 35, 40, 55, 65, 75, 85, 100, 115, 130, 150, 170, 195, 210, 225, 260],
           75: [0, 20, 30, 40, 50, 65, 75, 90, 100, 120, 135, 155, 180, 205, 230, 250, 270, 310],
           90: [0, 25, 35, 45, 55, 75, 85, 100, 115, 135, 150, 175, 205, 230, 260, 280, 305, 350]},
}
BREAKERS = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450, 500, 600]
WIRES = {"nmb": (90, 60), "uf": (60, 60), "thwn": (75, 75), "thhn": (90, 75)}
SMALL = {"cu": {"14": 15, "12": 20, "10": 30}, "al": {"12": 15, "10": 25}}


def awg(s):
    return f"{s} kcmil" if s.isdigit() and int(s) >= 250 else f"{s} AWG"


def mm2_of(size):
    return dict(NEC)[size] * MM2_PER_CMIL


def drop_volts(supply, cond, mm2, metres, amps, iec=False, pf=1.0):
    ac = supply != "dc"
    rho = RHO_IEC[cond] if iec else RHO20[cond] * 1.25
    z = (rho / mm2) * (pf if ac else 1) + (0.00008 * math.sqrt(max(0, 1 - pf * pf)) if ac else 0)
    return (math.sqrt(3) if supply == "three" else 2) * amps * metres * z


def wire_size(amps, wire="thhn", cond="cu", cont=False, term=75):
    """Ampacity pick exactly as initWireSize() in calc.js: (size, ampacity, breaker, column)."""
    insul_t, limit_t = WIRES[wire]
    design = amps * 1.25 if cont else amps
    ocpd = next((b for b in BREAKERS if b >= design - 1e-9), None)
    cap = min(limit_t, term)
    for i, s in enumerate(NEC_SIZES):
        insul = AMPACITY[cond][insul_t][i]
        term_a = AMPACITY[cond][cap][i]
        if not insul or not ocpd:
            continue
        a = min(insul, term_a)
        small = SMALL[cond].get(s)
        if small and ocpd > small:
            continue
        if term_a < design or a < amps:
            continue
        nxt = next((b for b in BREAKERS if b >= a - 1e-9), None)
        if not (a >= ocpd or (ocpd <= 800 and nxt and nxt >= ocpd)):
            continue
        return s, a, ocpd, cap
    return None, None, ocpd, cap


def max_feet(size, amps, volts, cond="cu", supply="single", limit=3.0):
    """One-way length in feet at which the drop reaches `limit` percent (NEC resistivity, unity power factor)."""
    per_metre = drop_volts(supply, cond, mm2_of(size), 1.0, amps)
    return limit / 100 * volts / per_metre / 0.3048


def max_metres_iec(mm2, amps, volts, supply="single", limit=3.0):
    return limit / 100 * volts / drop_volts(supply, "cu", mm2, 1.0, amps, iec=True)


NMB_LARGEST = NEC_SIZES.index("2")  # NM-B is not made above 2 AWG
NMB_MADE = ["14", "12", "10", "8", "6", "4", "2"]  # copper NM-B sizes on sale; 3 AWG is not made


def nmb_size(amps):
    """NM-B pick: the calculator's size, moved up to the next size NM-B is actually made in."""
    s, _, _, _ = wire_size(amps, "nmb", "cu")
    if not s:
        return None
    i = NEC_SIZES.index(s)
    return next((m for m in NMB_MADE if NEC_SIZES.index(m) >= i), None)


def wire_guide():
    loads = [15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 200]
    rows, picks = [], {}
    for amps in loads:
        cu, _, ocpd, _ = wire_size(amps, "thhn", "cu")
        nm = nmb_size(amps)
        al, _, _, _ = wire_size(amps, "thhn", "al")
        picks[amps] = (cu, nm, al)
        nm_txt = awg(nm) if nm else "not made: SER or THHN in conduit"
        run = max_feet(cu, amps, 240)
        rows.append([f"{amps} A", f"{ocpd} A", awg(cu), nm_txt, awg(al), f"{fmt(run)} ft"])
    tbl = table(
        "Wire size by load (non-continuous, 30 °C, up to 3 current-carrying conductors)",
        ["Load", "Breaker", "Copper THHN / THWN-2 (75 °C)", "Copper NM-B (60 °C)", "Aluminum (75 °C)", "Copper run at 3 % drop, 240 V"],
        rows,
        "For continuous loads (3 hours or more, such as EV chargers and water heaters) size for 125 % of the load first. "
        "The last column is the one-way length at which the copper THHN size reaches a 3 % voltage drop at full load on 240 V single phase; "
        "on 120 V it is half that. Dwelling services and main feeders can use the smaller sizes of NEC 310.12.")

    # Worked example: 40 A range, 240 V, NM-B, 60 ft.
    size, amp, ocpd, cap = wire_size(40, "nmb", "cu")
    pct = drop_volts("single", "cu", mm2_of(size), 60 * 0.3048, 40) / 240 * 100
    ten = AMPACITY["cu"][60][NEC_SIZES.index("10")]
    ex = example("40 A range on NM-B, 240 V, 60 ft", [
        "A range is not a continuous load, so the design current is 40 A and the breaker is 40 A (no 125 % factor).",
        f"NM-B is limited to the 60 °C column by NEC 334.80. 10 AWG copper is {ten} A there, too small. "
        f"{awg(size)} copper is {amp} A, enough for 40 A.",
        f"Voltage drop at 60 ft one way: 2 × 40 A × 18.3 m × (0.0216 Ω·mm²/m ÷ {mm2_of(size):.2f} mm²) = "
        f"{drop_volts('single', 'cu', mm2_of(size), 60 * 0.3048, 40):.2f} V, or {pct:.2f} % of 240 V. Under 3 %, so no upsizing.",
        "The equipment grounding conductor for a 40 A breaker is 10 AWG copper (NEC Table 250.122); 8/3 NM-B already has one.",
    ], f"Result: {awg(size)} copper NM-B on a {ocpd} A breaker.")

    cu = {a: awg(picks[a][0]) for a in loads}
    ans = answer(f"with copper THHN and 75 °C terminations, a 20 A circuit needs {cu[20]}, 30 A needs {cu[30]}, 40 A needs {cu[40]}, "
                 f"50 A needs {cu[50]} and 60 A needs {cu[60]} (NEC Table 310.16). NM-B (Romex) uses the 60 °C column, so it is often one size larger. "
                 "Long runs may need a bigger wire to keep voltage drop under 3 %.")
    faqs = []
    for amps in (20, 40, 50, 60, 100, 200):
        c, n, a = picks[amps]
        nm = f" In NM-B (Romex), {awg(n)}." if n else " NM-B is not made that large: use SER or THHN in conduit."
        faqs.append((f"What size wire for a {amps} amp breaker?",
                     f"{awg(c)} copper or {awg(a)} aluminum with 75 °C terminations (NEC Table 310.16, 30 °C ambient, "
                     f"up to 3 current-carrying conductors).{nm} At full load on 240 V, {awg(c)} copper reaches a 3 % voltage drop "
                     f"at about {fmt(max_feet(c, amps, 240))} ft one way; longer runs need a larger size."))
    return ans, guide("Wire size chart and worked example", [tbl, ex]), faqs


def vd_guide():
    nec_rows = []
    for size, amps in (("14", 15), ("12", 20), ("10", 30), ("8", 40), ("6", 50), ("4", 70), ("2", 95), ("1/0", 125)):
        nec_rows.append([awg(size), f"{amps} A", f"{fmt(max_feet(size, amps, 120))} ft", f"{fmt(max_feet(size, amps, 240))} ft",
                         f"{fmt(max_feet(size, amps, 480, supply='three'))} ft"])
    t1 = table("Longest copper run at 3 % voltage drop (NEC, full load, one way)",
               ["Wire", "Load", "120 V 1-phase", "240 V 1-phase", "480 V 3-phase"], nec_rows,
               "At half the load the length doubles. 208 V three phase gives almost the same lengths as 240 V single phase. Aluminum reaches 3 % at about 61 % of these lengths.")
    iec_rows = []
    for mm2, amps in ((1.5, 10), (2.5, 16), (4, 25), (6, 32), (10, 40), (16, 63), (25, 80)):
        iec_rows.append([f"{fmt(mm2, 1).rstrip('0').rstrip('.')} mm²", f"{amps} A", f"{fmt(max_metres_iec(mm2, amps, 230))} m",
                         f"{fmt(max_metres_iec(mm2, amps, 400, 'three'))} m"])
    t2 = table("Longest copper run at 3 % voltage drop (IEC 60364, full load, one way)",
               ["Cable", "Load", "230 V 1-phase", "400 V 3-phase"], iec_rows,
               "IEC 60364-5-52 Annex G resistivity for copper at operating temperature (0.0225 Ω·mm²/m).")

    vd = drop_volts("single", "cu", mm2_of("12"), 100 * 0.3048, 20)
    k = 2 * 12.9 * 20 * 100 / 6530
    fit = next(s for s in NEC_SIZES if drop_volts("single", "cu", mm2_of(s), 100 * 0.3048, 20) / 120 * 100 <= 3)
    fit_pct = drop_volts("single", "cu", mm2_of(fit), 100 * 0.3048, 20) / 120 * 100
    ex = example("20 A on 12 AWG copper, 120 V, 100 ft", [
        "K-factor method: VD = 2 × K × I × L ÷ CM = 2 × 12.9 × 20 A × 100 ft ÷ 6,530 cmil = "
        f"{k:.2f} V.",
        f"The calculator's resistance method gives {vd:.2f} V, which is {vd / 120 * 100:.1f} % of 120 V. Over the 3 % recommendation.",
        f"Going up in size: {awg(fit)} gives {fit_pct:.2f} %, the first size under 3 %.",
    ], f"Result: use {awg(fit)} copper for a 20 A load at 100 ft on 120 V, or move the load closer.")
    ans = answer(f"voltage drop is 2 × K × I × L ÷ CM for single phase (K = 12.9 for copper). The NEC recommends at most 3 % on a branch circuit "
                 f"and 5 % feeder plus branch. Example: 20 A on 12 AWG copper over 100 ft at 120 V drops about {vd:.1f} V ({vd / 120 * 100:.1f} %), "
                 f"so a long run like that needs {awg(fit)}.")
    faqs = [("How far can I run 12 AWG wire on 20 amps?",
             f"About {fmt(max_feet('12', 20, 120))} ft one way at 120 V and {fmt(max_feet('12', 20, 240))} ft at 240 V before the drop "
             "passes 3 % at full load. At a 10 A load the distance doubles."),
            ("How much voltage drop on 100 ft of 10 AWG at 30 amps?",
             f"About {drop_volts('single', 'cu', mm2_of('10'), 30.48, 30):.1f} V: "
             f"{drop_volts('single', 'cu', mm2_of('10'), 30.48, 30) / 120 * 100:.1f} % at 120 V or "
             f"{drop_volts('single', 'cu', mm2_of('10'), 30.48, 30) / 240 * 100:.1f} % at 240 V (copper, one-way length).")]
    return ans, guide("Voltage drop tables and worked example", [t1, t2, ex]), faqs


def awg_guide():
    rows = []
    for s, cmil in NEC:
        mm2 = cmil * MM2_PER_CMIL
        nxt = next((a for a in IEC if a >= mm2 - 1e-9), None)
        rows.append([awg(s), f"{mm2:.2f} mm²", f"{fmt(cmil)}", f"{nxt:g} mm²" if nxt else "–"])
    t = table("AWG and kcmil to mm² (NEC Chapter 9, Table 8)", ["Size", "mm²", "Circular mils", "Next IEC size up"], rows)
    ans = answer("14 AWG = 2.08 mm², 12 AWG = 3.31 mm², 10 AWG = 5.26 mm², 8 AWG = 8.37 mm² and 6 AWG = 13.3 mm². "
                 "1 circular mil = 0.000507 mm². When you swap metric cable for AWG wire, pick the size that is not smaller.")
    faqs = [("What is 6 mm² in AWG?", "6 mm² sits between 10 AWG (5.26 mm²) and 8 AWG (8.37 mm²). The closest AWG that is not smaller is 8 AWG."),
            ("What is 4 AWG in mm²?", "4 AWG is 41,740 circular mils, which is 21.2 mm². The next IEC size up is 25 mm².")]
    return ans, guide("AWG to mm² chart", [t]), faqs


# ---------- coatings ----------

SQFT_PER_GAL_1MIL = 1604


def coat_guide():
    solids = [100, 80, 70, 50]
    rows = [[f"{m} mils"] + [f"{fmt(SQFT_PER_GAL_1MIL * s / 100 / m)} sq ft" for s in solids] for m in (3, 5, 8, 10, 15, 20, 30)]
    t = table("Coverage per US gallon by dry film thickness and solids by volume",
              ["Thickness (DFT)", "100 % solids", "80 % solids", "70 % solids", "50 % solids"], rows,
              "Before waste. Porous or profiled concrete takes more on the first coat. Source: one US gallon spread 1 mil thick covers "
              '1,604 sq ft (<a href="https://www.neogard.com/news/id/theoretical-vs-actual-coverage-rates">Neogard, "Theoretical vs. actual coverage rates"</a>); '
              "coverage = 1,604 × solids ÷ mils. Checked 12 November 2026.")
    gal = 480 * 10 / SQFT_PER_GAL_1MIL * 1.10
    kits = math.ceil(gal / 1.5 - 1e-9)
    ex = example("two-car garage, 480 sq ft at 10 mils", [
        "Spread rate of a 100 % solids epoxy at 10 mils: 1,604 ÷ 10 = 160 sq ft per gallon.",
        f"Material: 480 sq ft ÷ 160 = {480 * 10 / SQFT_PER_GAL_1MIL:.2f} gal, plus 10 % waste = {gal:.2f} gal.",
        f"Kits of 1.5 gal: {gal:.2f} ÷ 1.5 = {gal / 1.5:.2f}, round up to {kits}.",
    ], f"Result: {gal:.1f} gallons, order {kits} kits of 1.5 gal.")
    ans = answer("one US gallon at 1 mil covers 1,604 sq ft. A 100 % solids epoxy at 10 mils covers about 160 sq ft per gallon; "
                 "a 50 % solids product at the same dry thickness covers 80 sq ft. A 480 sq ft two-car garage at 10 mils needs about "
                 f"{gal:.1f} gallons with 10 % waste.")
    faqs = [("How much epoxy for a 2 car garage?",
             f"Measure the floor first: garages vary. At 10 mils with a 100 % solids epoxy and 10 % waste, 480 sq ft takes {gal:.1f} gallons. "
             "A flake system adds a primer coat and a clear topcoat, each sized the same way. The "
             '<a href="{rel}coating/garage-floor-epoxy-calculator.html">garage floor epoxy calculator</a> has one, two and three car examples by system.')]
    return ans, guide("Coverage chart and worked example", [t, ex]), faqs


# ---------- pool (same as calc.js / PoolPro) ----------

MW = {"cl2": 70.906, "naocl": 74.44, "caco3": 50.04, "nahco3": 84.007}
L_PER_GAL = 3.78541
PRODUCTS = {
    "Liquid chlorine 10 %": ("liquid", 100),
    "Liquid chlorine 12.5 %": ("liquid", 125),
    "Bleach 6 %": ("liquid", 6 * 10 * (1.0174 + 0.01003 * 6) * MW["cl2"] / MW["naocl"]),
    "Bleach 8.25 %": ("liquid", 8.25 * 10 * (1.0174 + 0.01003 * 8.25) * MW["cl2"] / MW["naocl"]),
    "Cal-hypo 65 %": ("solid", 0.65),
    "Dichlor 56 %": ("solid", 0.56),
}


def fc_dose(product, ppm, gallons):
    kind, v = PRODUCTS[product]
    grams = ppm * gallons * L_PER_GAL / 1000
    return (grams / v * 1000 / 29.5735, "fl oz") if kind == "liquid" else (grams / v / 28.3495, "oz")


def pool_guide():
    rows = []
    for p in PRODUCTS:
        amt, unit = fc_dose(p, 1, 10000)
        rows.append([f"Free chlorine +1 ppm", p, f"{amt:.1f} {unit}"])
    soda = 10 / MW["caco3"] * MW["nahco3"] * 10000 * L_PER_GAL / 1000 / 453.592
    cya = 10 * 10000 * L_PER_GAL / 1000 / 0.99 / 453.592
    salt = 500 * 10000 * L_PER_GAL / 1000 / 0.99 / 453.592
    rows += [["Total alkalinity +10 ppm", "Baking soda", f"{soda:.2f} lb"],
             ["Stabilizer (CYA) +10 ppm", "Cyanuric acid", f"{cya:.2f} lb"],
             ["Salt +500 ppm", "Pool salt", f"{salt:.0f} lb"]]
    t = table("Doses per 10,000 US gallons", ["To raise", "Product", "Amount"], rows,
              "Scale linearly: 20,000 gallons needs twice as much, a 2 ppm rise twice as much. Add in portions and retest. "
              "Source: stoichiometry (ppm × litres = milligrams, by molar mass and label strength), the same maths as PoolPro, "
              "cross-checked with Trouble Free Pool's Pool Math (10 % liquid chlorine: 12.79 fl oz). Checked 25 October 2026.")
    amt, _ = fc_dose("Liquid chlorine 10 %", 3, 15000)
    ex = example("15,000 gallons, free chlorine from 2 to 5 ppm", [
        "Rise needed: 5 − 2 = 3 ppm.",
        f"10 % liquid chlorine raises 10,000 gallons by 1 ppm with {fc_dose('Liquid chlorine 10 %', 1, 10000)[0]:.1f} fl oz.",
        f"For 15,000 gallons and 3 ppm: {fc_dose('Liquid chlorine 10 %', 1, 10000)[0]:.1f} × 1.5 × 3 = {amt:.0f} fl oz.",
    ], f"Result: about {amt:.0f} fl oz ({amt * 29.5735 / 1000:.2f} L) of 10 % liquid chlorine.")
    ans = answer(f"to raise free chlorine by 1 ppm in 10,000 US gallons add about {fc_dose('Liquid chlorine 10 %', 1, 10000)[0]:.1f} fl oz of 10 % liquid chlorine, "
                 f"{fc_dose('Bleach 6 %', 1, 10000)[0]:.0f} fl oz of 6 % bleach or {fc_dose('Cal-hypo 65 %', 1, 10000)[0]:.1f} oz of 65 % cal-hypo. "
                 f"{soda:.1f} lb of baking soda raises total alkalinity by 10 ppm.")
    faqs = [("How much baking soda to raise alkalinity 10 ppm?",
             f"{soda:.2f} lb (about {soda * 453.592 / 1000:.2f} kg) of baking soda per 10,000 US gallons. For 20,000 gallons, twice that."),
            ("How much chlorine do I add for my pool's size?",
             'See <a href="{rel}pool/how-much-chlorine-to-add.html">how much chlorine to add to a pool</a>: liquid chlorine, cal-hypo, dichlor and trichlor '
             "by gallons, with what each one leaves behind in the water and the safety rules.")]
    return ans, guide("Dose chart and worked example", [t, ex]), faqs


# ---------- bread (same as calc.js / Levain) ----------


def bread(flour, hyd, starter=0.20, st_hyd=1.0, salt=0.02):
    s = starter * flour
    s_flour = s / (1 + st_hyd)
    s_water = s - s_flour
    water = hyd * flour
    return water, s, salt * flour, (water + s_water) / (flour + s_flour) * 100


def bread_guide():
    rows = []
    for h in (65, 70, 75, 80, 85):
        w, s, sa, true = bread(500, h / 100)
        rows.append([f"{h} %", f"{fmt(w)} g", f"{fmt(s)} g", f"{sa:.0f} g", f"{fmt(500 + w + s + sa)} g", f"{true:.1f} %"])
    t = table("500 g flour, 20 % starter at 100 % hydration, 2 % salt",
              ["Hydration", "Water", "Starter", "Salt", "Dough", "True hydration"], rows,
              "True hydration counts the flour and water inside the starter. With a 100 % starter it stays close to the nominal figure. "
              "Plain arithmetic from baker's percentages (every ingredient as a share of the flour weight), the same as in the Levain app; no outside data.")
    w, s, sa, true = bread(500, 0.75)
    ex = example("one loaf at 75 % hydration", [
        "Flour is 100 %: 500 g.",
        f"Water 75 % of 500 g = {fmt(w)} g; starter 20 % = {fmt(s)} g; salt 2 % = {sa:.0f} g.",
        f"The starter holds 50 g flour and 50 g water, so true hydration = ({fmt(w)} + 50) ÷ (500 + 50) = {true:.1f} %.",
    ], f"Result: 500 g flour, {fmt(w)} g water, {fmt(s)} g starter, {sa:.0f} g salt; {fmt(500 + w + s + sa)} g of dough.")
    ans = answer(f"every ingredient is a percentage of the flour weight. For 500 g flour at 75 % hydration with 20 % starter and 2 % salt: "
                 f"{fmt(w)} g water, {fmt(s)} g starter and {sa:.0f} g salt, {fmt(500 + w + s + sa)} g of dough.")
    return ans, guide("Hydration chart and worked example", [t, ex]), []


# ---------- lye (same as calc.js / Lye Calc) ----------

KOH_TO_NAOH = 39.997 / 56.106


def lye_guide(oils):
    rows = [[o["name"], f"{o['sap']:.3f}", f"{o['sap'] * KOH_TO_NAOH * 100:.2f} g", f"{o['sap'] * KOH_TO_NAOH * 95:.2f} g"]
            for o in sorted(oils, key=lambda o: o["name"])]
    t = table("Sodium hydroxide per 100 g of oil", ["Oil", "SAP (KOH)", "NaOH at 0 % superfat", "NaOH at 5 % superfat"], rows,
              'Source: SAP values from the <a href="https://soapcalc.net/oil-list">SoapCalc oil list</a> as shipped in the Lye Calc app, converted to NaOH by '
              "molar mass (39.997 ÷ 56.106). Snapshot of 25 October 2026. Suppliers' oils vary, so run your full recipe through the calculator.")
    by = {o["id"]: o for o in oils}
    olive, coco = by.get("olive"), by.get("coconut76")
    parts = [t]
    ans_txt = "lye = Σ (oil grams × SAP) × (1 − superfat), with SAP converted from KOH to NaOH by 39.997 ÷ 56.106."
    if olive and coco:
        koh = 700 * olive["sap"] + 300 * coco["sap"]
        naoh = koh * KOH_TO_NAOH * 0.95
        water = naoh * 67 / 33
        parts.append(example("1,000 g of oils, 70 % olive and 30 % coconut", [
            f"KOH equivalent: 700 g × {olive['sap']:.3f} + 300 g × {coco['sap']:.3f} = {koh:.1f} g.",
            f"Convert to NaOH: × 0.7129 = {koh * KOH_TO_NAOH:.1f} g. With 5 % superfat: × 0.95 = {naoh:.1f} g.",
            f"Water at 33 % lye concentration: {naoh:.1f} × 67 ÷ 33 = {water:.0f} g.",
        ], f"Result: {naoh:.0f} g NaOH and {water:.0f} g water for 1,000 g of oils."))
        ans_txt += f" For 700 g olive and 300 g coconut oil at 5 % superfat: {naoh:.0f} g NaOH and {water:.0f} g water at 33 % concentration."
    return answer(ans_txt), guide("Lye chart and worked example", parts), []
