"""Hobby calculator pages: mead and cider (Ferment), hydroponics (GrowLab), candles (WickCalc), espresso (Dial In)
and knitting (RowKeeper). Formulas are in calc_math.py; data that the apps own (crop targets) is read from their
Dart sources at build time, so the pages never drift from the apps.
"""
import re

import calc_math as m
import calcs_common as c
import guides
import opendata
from calcs_common import n, src, table, trim

HOME_CARDS = [
    ("brewing/mead-abv-calculator.html", "Brewing", "Mead ABV calculator", "ABV for mead, cider and wine from SG, Brix or Plato.", "t-bread"),
    ("brewing/honey-per-gallon-calculator.html", "Brewing", "Honey per gallon calculator", "Honey for a target gravity, or the gravity from your honey.", "t-bread"),
    ("brewing/brix-plato-sg-chart.html", "Brewing", "Brix, Plato and SG chart", "Brix or Plato to specific gravity and back, with potential alcohol.", "t-bread"),
    ("hydroponics/ec-to-ppm-converter.html", "Hydroponics", "EC to ppm converter", "EC to ppm on the 500, 640 and 700 scales, and back.", "t-site"),
    ("hydroponics/ec-chart-by-crop.html", "Hydroponics", "EC and pH chart by crop", "Target EC, ppm and pH for 23 vegetables, herbs and flowers.", "t-site"),
    ("hydroponics/vpd-chart.html", "Hydroponics", "VPD chart and calculator", "Air and leaf VPD in kPa from temperature and humidity.", "t-site"),
    ("candles/fragrance-load-calculator.html", "Candles", "Fragrance load calculator", "Fragrance oil for your wax weight and load percentage.", "t-elec"),
    ("candles/candle-wax-calculator.html", "Candles", "Candle wax calculator", "Wax and fragrance for any jar, from the water it holds.", "t-elec"),
    ("coffee/espresso-ratio-calculator.html", "Coffee", "Espresso ratio calculator", "Dose, yield and brew ratio for espresso.", "t-roof"),
    ("knitting/yarn-yardage-calculator.html", "Knitting", "Yarn yardage calculator", "Yarn for a scarf, hat or blanket, from your own swatch.", "t-soap"),
    ("knitting/gauge-calculator.html", "Knitting", "Knitting gauge calculator", "Stitches to cast on and rows to work, from your gauge.", "t-soap"),
]

BREWERS_FRIEND = "formulas as published by Brewer's Friend (brewersfriend.com: Brix converter, Plato to SG chart, ABV calculator) and Michael L. Hall, Zymurgy, Summer 1995"
BJCP = '<a href="https://www.bjcp.org/beer-styles/introduction-to-mead-guidelines">BJCP Mead Guidelines, introduction</a>'


def inp(i, label, small, value, full=False, attrs='inputmode="decimal"'):
    sm = f' <small id="{i}-unit">{small}</small>' if small else ""
    return f'<div{" class=full" if full else ""} id="{i}-row"><label for="{i}">{label}{sm}</label><input id="{i}" {attrs} value="{value}"></div>'


def seg(i, label, options):
    btn = "".join(f'<button data-v="{v}" aria-pressed="{"true" if k == 0 else "false"}">{t}</button>' for k, (v, t) in enumerate(options))
    return f'<div class="full"><div class="seg" id="{i}" role="group" aria-label="{label}">{btn}</div></div>'


def rows(big_id, eyebrow, items):
    r = "".join(f'<div><span>{label}</span><span id="{i}">–</span></div>' for i, label in items)
    return f'<div class="eyebrow">{eyebrow}</div><div class="big" id="{big_id}">–</div><div class="rows">{r}</div>'


# ---------- Ferment ----------

FERMENT_PITCH = ("Log gravity readings for your cider, mead or kombucha and see when the batch is done, "
                 "with the ABV and the honey and sugar you step-feed counted.")


def build_abv():
    ogs = [1.040, 1.050, 1.060, 1.070, 1.080, 1.090, 1.100, 1.110, 1.120, 1.130]
    t1 = table("ABV by original gravity",
               ["Original gravity", "°Brix / °Plato", "ABV if it finishes at 1.000", "ABV if it finishes at 1.010", "Hall formula, finish 1.000"],
               [[f"{og:.3f}", f"{m.sg_to_degrees(og):.1f}", f"{m.abv_standard(og, 1.0):.1f} %", f"{m.abv_standard(og, 1.010):.1f} %",
                 f"{m.abv_alternate(og, 1.0):.1f} %"] for og in ogs],
               src(f"computed with the standard formula (OG − FG) × 131.25 and Hall's formula; {BREWERS_FRIEND}", "26 October 2026"))
    t2 = table("Mead by sweetness and strength (BJCP)", ["Class", "Final gravity", "Class", "ABV"],
               [["Dry", "0.990–1.010", "Hydromel", "3.5–7.5 %"], ["Semi-sweet", "1.010–1.025", "Standard", "7.5–14.0 %"],
                ["Sweet", "1.025–1.050", "Sack", "14.0–18.0 %"]],
               src(f"{BJCP}"))
    og, fg = 1.100, 1.010
    ex = guides.example("a mead from 1.100 down to 1.010", [
        f"Gravity drop: 1.100 − 1.010 = {og - fg:.3f}.",
        f"Standard formula: {og - fg:.3f} × 131.25 = {m.abv_standard(og, fg):.1f} % ABV.",
        f"Hall's formula, closer for strong meads and wines: 76.08 × {og - fg:.3f} ÷ (1.775 − 1.100) × (1.010 ÷ 0.794) = {m.abv_alternate(og, fg):.1f} %.",
        f"Apparent attenuation: {og - fg:.3f} ÷ 0.100 = {m.attenuation(og, fg):.0f} %. A final gravity of 1.010 sits on the line between dry and semi-sweet.",
    ], f"Result: about {m.abv_standard(og, fg):.0f} to {m.abv_alternate(og, fg):.0f} % ABV, a standard-strength mead.")
    answer = (f"ABV = (OG − FG) × 131.25. A mead that starts at 1.100 and finishes at 1.010 is about {m.abv_standard(og, fg):.1f} % ABV; "
              f"a cider from 1.050 to 1.000 is {m.abv_standard(1.050, 1.0):.1f} %. For Brix or Plato readings the calculator converts to specific gravity first.")
    form = (seg("gunit", "Gravity unit", [("sg", "SG"), ("brix", "Brix"), ("plato", "Plato")])
            + inp("og", "Original gravity", "(SG)", "1.100") + inp("fg", "Final gravity", "(SG)", "1.010"))
    result = rows("abv-std", "Alcohol by volume", [
        ("abv-alt", "Hall formula (strong meads, wines)"), ("abv-att", "Apparent attenuation"), ("abv-sg", "Specific gravity"),
        ("abv-deg", "In °Plato"), ("abv-sweet", "Mead sweetness (BJCP)"), ("abv-strength", "Mead strength (BJCP)"),
    ]) + '<div id="abv-note" class="verdict"></div><p class="note">An estimate from two gravity readings. Honey or sugar added during fermentation raises the real figure.</p>'
    c.page(
        "brewing/mead-abv-calculator.html", "Mead ABV Calculator (Cider & Wine): SG, Brix or Plato | Free",
        "Free ABV calculator for mead, cider and wine: enter original and final gravity as SG, Brix or Plato. Standard and Hall formulas, attenuation and BJCP sweetness.",
        "Brewing", "Free brewing tool", "Mead ABV calculator", "Alcohol by volume for mead, cider and wine from the original and final gravity, in SG, Brix or Plato.",
        answer, [t1, t2, ex], [
            ("How do you calculate the ABV of mead?",
             "Take a hydrometer reading before you pitch the yeast (original gravity, OG) and another when fermentation is over (final gravity, FG). "
             "ABV = (OG − FG) × 131.25. From 1.100 to 1.000 that is 13.1 %."),
            ("Which ABV formula is right for strong mead and wine?",
             "The standard × 131.25 formula reads low as the alcohol goes up. Michael Hall's formula, "
             "76.08 × (OG − FG) ÷ (1.775 − OG) × (FG ÷ 0.794), is closer above about 10 %. The calculator shows both."),
            ("Can I use a refractometer for the final gravity?",
             "Not directly. Alcohol bends light too, so a refractometer reads too high once fermentation has started. "
             "Use a hydrometer for the final reading, or a refractometer correction formula with both Brix readings (the Ferment app has one)."),
            ("Are Brix and Plato the same?",
             "For home brewing, close enough: both are percent sugar by weight and they agree to the first decimal at these gravities. "
             "This calculator uses SG = 1 + °P ÷ (258.6 − °P ÷ 258.2 × 227.1) for both."),
            ("Does it work for cider and wine?",
             "Yes. The formula only needs the gravity drop, whatever the sugar came from: apple juice, grape must or honey."),
            ("What if I added honey or sugar during fermentation?",
             "Step feeding raises the real original gravity. Add the gravity points of every addition to the OG before you calculate, "
             f'or use the <a href="{{rel}}brewing/honey-per-gallon-calculator.html">honey calculator</a> to find the points each addition gave.'),
        ], "t-bread", ("ferment", "abv", FERMENT_PITCH), "abv", form, result, "ABV charts and worked example",
        extra=c.related("More brewing tools", [("brewing/honey-per-gallon-calculator.html", "Honey per gallon calculator"),
                                               ("brewing/brix-plato-sg-chart.html", "Brix, Plato and SG chart")]),
        embed=("mead-abv", 760))


def build_honey():
    per_gal = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    t1 = table("Gravity from honey per US gallon of must",
               ["Honey per gallon", "Per litre", "Original gravity", "°Brix", "ABV if it ferments to 1.000"],
               [[f"{lb:g} lb", f"{lb * m.KG_PER_LB / m.L_PER_GAL * 1000:.0f} g", f"{1 + m.honey_points(lb, 1) / 1000:.3f}",
                 f"{m.sg_to_degrees(1 + m.honey_points(lb, 1) / 1000):.1f}", f"{m.abv_standard(1 + m.honey_points(lb, 1) / 1000, 1.0):.1f} %"]
                for lb in per_gal],
               src("35 gravity points per pound of honey per US gallon (Ken Schramm, The Compleat Meadmaker, 2003; the same average in "
                   "Mead Lover's Digest #949 on gotmead.com). Honey varies with its water content, so check the gravity after mixing"))
    targets = [1.060, 1.080, 1.100, 1.120]
    t2 = table("Honey for common batch sizes", ["Batch (final volume)"] + [f"OG {og:.3f}" for og in targets],
               [[f"{gal} gal ({gal * m.L_PER_GAL:.1f} L)"] + [f"{m.honey_lb_for((og - 1) * 1000, gal):.1f} lb" for og in targets] for gal in (1, 3, 5, 6)],
               "Same 35 points per pound per gallon. The gallon is the finished must, honey included: mix the honey with part of the water, then top up to the mark.")
    lb = m.honey_lb_for(100, 5)
    ex = guides.example("5 gallons of mead at 1.100", [
        "Target gravity 1.100 is 100 gravity points above water.",
        f"Honey: 100 points × 5 gal ÷ 35 points per lb per gal = {lb:.2f} lb ({lb * m.KG_PER_LB:.2f} kg).",
        f"That is {lb / 5:.2f} lb per gallon. Fermented dry to 1.000 it would reach {m.abv_standard(1.100, 1.0):.1f} % ABV.",
    ], f"Result: about {lb:.1f} lb of honey, topped up with water to 5 gallons.")
    answer = (f"one pound of honey in one US gallon of must adds about 35 gravity points. For a 1.100 mead use about {m.honey_lb_for(100, 1):.1f} lb per gallon "
              f"({lb:.1f} lb for 5 gallons); 3 lb per gallon gives about {1 + m.honey_points(3, 1) / 1000:.3f}. Honey varies, so measure after mixing.")
    form = (seg("hmode", "What to find", [("need", "Honey for a gravity"), ("get", "Gravity from honey")])
            + seg("hunit", "Units", [("us", "US: gal, lb"), ("metric", "Metric: L, kg")])
            + inp("hvol", "Batch size", "(US gallons)", "5") + inp("hstart", "Starting gravity", "(1.000 for water)", "1.000")
            + inp("hog", "Target original gravity", "", "1.100", True) + inp("hamt", "Honey", "(lb)", "15", True))
    result = rows("h-main", "Result", [("h-alt", "Other unit"), ("h-per", "Honey per volume"), ("h-og", "Original gravity"),
                                       ("h-abv", "ABV if it ferments to 1.000")]) + '<p class="note">Honey varies: stir well and check with a hydrometer before you pitch.</p>'
    c.page(
        "brewing/honey-per-gallon-calculator.html", "How Much Honey per Gallon of Mead? Honey Calculator | Free",
        "Free mead honey calculator: pounds or kilograms of honey for a target original gravity and batch size, or the gravity and potential ABV from your honey.",
        "Brewing", "Free brewing tool", "Honey per gallon calculator",
        "How much honey a mead needs for a target original gravity, or the gravity and potential alcohol your honey will give.",
        answer, [t1, t2, ex], [
            ("How much honey do I need for 1 gallon of mead?",
             f"About {m.honey_lb_for(80, 1):.1f} lb for a lighter mead at 1.080, {m.honey_lb_for(100, 1):.1f} lb for 1.100 and "
             f"{m.honey_lb_for(120, 1):.1f} lb for a strong one at 1.120, counting 35 gravity points per pound per gallon."),
            ("How much honey for 5 gallons of mead?",
             f"{m.honey_lb_for(80, 5):.1f} lb for 1.080, {m.honey_lb_for(100, 5):.1f} lb for 1.100 or {m.honey_lb_for(120, 5):.1f} lb for 1.120. "
             "Top up with water to the 5 gallon mark after the honey is in."),
            ("Is the gallon the water or the finished must?",
             "The finished must. Honey takes up room, so the formula uses the final volume: dissolve the honey in part of the water and top up to the mark."),
            ("Why is my gravity different from the calculator?",
             "Honey is not a standard product: its water content changes from jar to jar, and so do the points it gives. "
             "35 points per pound per gallon is an average. Stir until the honey is fully dissolved and trust the hydrometer."),
            ("Can I add honey later to raise the alcohol?",
             "Yes, that is step feeding. Set the starting gravity to your current reading and the calculator shows the honey for the points you want to add."),
        ], "t-bread", ("ferment", "honey", FERMENT_PITCH), "honey", form, result, "Honey charts and worked example",
        extra=c.related("More brewing tools", [("brewing/mead-abv-calculator.html", "Mead ABV calculator"),
                                               ("brewing/brix-plato-sg-chart.html", "Brix, Plato and SG chart")]))


NBS_C457 = ('<a href="https://nvlpubs.nist.gov/nistpubs/Legacy/circ/nbscircular457.pdf">National Bureau of Standards, Circular C457 '
            '(Snyder and Hammond, 1946), Table 1, apparent specific gravity 20°/20 °C</a>')
GRAVITY_FORMULAS = ('SG = 1 + °P ÷ (258.6 − (°P ÷ 258.2 × 227.1)), the equation <a href="https://www.brewersfriend.com/brix-converter/">'
                    'Brewer\'s Friend publishes as the Lyons equation</a>; SG to degrees by the ASBC polynomial '
                    '°P = −616.868 + 1111.14 SG − 630.272 SG² + 135.997 SG³ (<a href="https://www.brewersfriend.com/plato-to-sg-conversion-chart/">'
                    'Brewer\'s Friend, Plato to SG</a>)')


def build_gravity():
    t1 = table("Brix or Plato to specific gravity, with potential alcohol",
               ["°Brix / °Plato", "Specific gravity", "Gravity points", "Potential ABV, to 1.000", "Hall formula, to 1.000"],
               [[f"{d}", f"{m.degrees_to_sg(d):.4f}", f"{(m.degrees_to_sg(d) - 1) * 1000:.1f}", f"{m.abv_standard(m.degrees_to_sg(d), 1):.1f} %",
                 f"{m.abv_alternate(m.degrees_to_sg(d), 1):.1f} %"] for d in range(0, 41)],
               src(f"computed with {GRAVITY_FORMULAS}; ABV = (OG − FG) × 131.25 and Michael Hall's formula (Zymurgy, Summer 1995), the formulas of the Ferment app",
                   "26 November 2026")
               + " " + open_dataset("brix-plato-specific-gravity", "The full table (every 0.5 °, with the ASBC back-conversion)"))
    sgs = [1.000 + i / 100 for i in range(0, 17)]
    t2 = table("Specific gravity to Brix or Plato", ["Specific gravity", "°Brix / °Plato (ASBC)", "Potential ABV, to 1.000"],
               [[f"{sg:.3f}", f"{m.sg_to_degrees(sg):.1f}", f"{m.abv_standard(sg, 1):.1f} %"] for sg in sgs],
               src("the ASBC polynomial as published by Brewer's Friend, as in the Ferment app", "26 November 2026"))
    t3 = table("Check against the US National Bureau of Standards sucrose table", ["°Brix", "NBS apparent SG 20/20 °C", "This chart"],
               [[f"{b}", f"{v:.5f}", f"{m.degrees_to_sg(b):.5f}"] for b, v in ((10, 1.04003), (20, 1.08297), (30, 1.12913), (40, 1.17874))],
               src(f"printed values from {NBS_C457}", "26 November 2026")
               + " The formula agrees to the fifth decimal up to 10 °Bx and within 0.0003 (0.3 gravity points) up to 40 °Bx.")
    d = 24
    sg = m.degrees_to_sg(d)
    ex = guides.example("a mead must that reads 24 °Brix", [
        f"Specific gravity: 1 + 24 ÷ (258.6 − 24 ÷ 258.2 × 227.1) = 1 + 24 ÷ {258.6 - d / 258.2 * 227.1:.2f} = {sg:.4f}.",
        f"Gravity points: ({sg:.4f} − 1) × 1000 = {(sg - 1) * 1000:.0f}.",
        f"Potential alcohol if it ferments dry to 1.000: ({sg:.4f} − 1.000) × 131.25 = {m.abv_standard(sg, 1):.1f} % ABV; Hall's formula gives {m.abv_alternate(sg, 1):.1f} %.",
        f"Back to degrees with the ASBC polynomial: {m.sg_to_degrees(sg):.2f} °P, the same within a few hundredths.",
    ], f"Result: 24 °Bx is about {sg:.3f} SG, enough sugar for roughly {m.abv_standard(sg, 1):.0f}–{m.abv_alternate(sg, 1):.0f} % ABV if the yeast takes it dry.")
    answer = (f"SG = 1 + °Bx ÷ (258.6 − °Bx ÷ 258.2 × 227.1). 10 °Bx is {m.degrees_to_sg(10):.3f}, 12 °Bx {m.degrees_to_sg(12):.3f}, "
              f"20 °Bx {m.degrees_to_sg(20):.3f} and 24 °Bx {m.degrees_to_sg(24):.3f}. Going back, 1.050 is {m.sg_to_degrees(1.05):.1f} °P and "
              f"1.100 is {m.sg_to_degrees(1.1):.1f} °P. Brix and Plato are the same within a tenth of a degree at brewing gravities.")
    form = (seg("bunit", "Scale of your reading", [("brix", "°Brix"), ("plato", "°Plato"), ("sg", "SG")]) + inp("bval", "Reading", "(°Bx)", "12"))
    result = rows("b-main", "Converted", [("b-sg", "Specific gravity"), ("b-deg", "Degrees Brix / Plato"), ("b-pts", "Gravity points"),
                                          ("b-abv", "Potential ABV, to 1.000"), ("b-hall", "Potential ABV, Hall formula")])
    c.page(
        "brewing/brix-plato-sg-chart.html", "Brix to SG Chart and Converter: Brix, Plato and Specific Gravity | Free",
        "Free Brix, Plato and specific gravity converter with a chart from 0 to 40 °Bx: SG, gravity points and potential alcohol, checked against the NBS sucrose table.",
        "Brewing", "Free brewing chart", "Brix, Plato and SG chart",
        "Convert degrees Brix or Plato to specific gravity and back, with gravity points and the alcohol a must can reach if it ferments dry.",
        answer, [t1, t2, t3, ex], [
            ("How do I convert Brix to specific gravity?",
             f"SG = 1 + °Bx ÷ (258.6 − °Bx ÷ 258.2 × 227.1). 12 °Bx is {m.degrees_to_sg(12):.4f}. For the other direction homebrewers use the ASBC "
             f"polynomial: °P = −616.868 + 1111.14 SG − 630.272 SG² + 135.997 SG³, so 1.050 is {m.sg_to_degrees(1.05):.2f} °P."),
            ("Are Brix and Plato the same?",
             "Both are sucrose percent by weight, measured to slightly different reference tables. At brewing and winemaking gravities they differ "
             "only in the third decimal of SG, so homebrew tools, the Ferment app included, use one formula for both."),
            ("Is there a simple rule of thumb?",
             f"SG ≈ 1 + °Bx × 4 ÷ 1000 is close at low gravities (10 °Bx → 1.040, the formula gives {m.degrees_to_sg(10):.3f}) but drifts higher up "
             f"(25 °Bx → 1.100, the formula gives {m.degrees_to_sg(25):.3f}). Use the chart for musts and strong worts."),
            ("Can I use a refractometer reading with this chart?",
             "Before fermentation, yes, after dividing the Brix reading by your wort correction factor (often about 1.04). Once there is alcohol a "
             "refractometer reads too high, and the reading needs a separate correction (Sean Terrill's formula, used in the Ferment app), not this chart."),
            ("How much alcohol will my must make?",
             f"The potential ABV column assumes every bit of sugar ferments down to 1.000. 20 °Bx gives about {m.abv_standard(m.degrees_to_sg(20), 1):.1f} %. "
             "Yeast stops early at high gravities, so above about 30 °Bx the number is a ceiling, not a forecast. Measure the final gravity and use the "
             f'<a href="{{rel}}brewing/mead-abv-calculator.html">ABV calculator</a>.'),
            ("At what temperature is SG measured?",
             "These are apparent specific gravities of sugar solutions at 20 °C, what a hydrometer calibrated at 20 °C reads in a pure sugar solution. "
             "Read your hydrometer at its calibration temperature or correct the reading."),
        ], "t-bread", ("ferment", "gravity-chart", FERMENT_PITCH), "grav", form, result, "Gravity charts and worked example",
        extra=c.related("More brewing tools", [("brewing/mead-abv-calculator.html", "Mead ABV calculator"),
                                               ("brewing/honey-per-gallon-calculator.html", "Honey per gallon calculator")]),
        extra_ld=[opendata.with_doi(opendata.BRIX_LD, "brix-plato-specific-gravity",
                                    ["brix-plato-specific-gravity.csv", "brix-plato-specific-gravity.json"])])


# ---------- GrowLab ----------

GROW_PITCH = ("A hydroponic nutrient calculator for vegetables, herbs and flowers: type the doses from your own labels, any brand, "
              "and see exactly how much of each part goes into your reservoir.")
HANNA = ('<a href="https://knowledge.hannainst.com/en/knowledge/ec-tds-what-is-the-relationship-between-tds-and-ec">Hanna Instruments, '
         '"What is the relationship between TDS and EC?"</a>')
OSU = ('<a href="https://extension.okstate.edu/fact-sheets/electrical-conductivity-and-ph-guide-for-hydroponics.html">Oklahoma State University '
       'Extension, HLA-6722 "Electrical Conductivity and pH Guide for Hydroponics"</a> (Singh and Dunn, 2016), Table 2')
SCALE_NOTE = ("The 640 column is plain arithmetic (EC × 640): sellers list a 0.64 factor for some European meters, "
              "but we found no meter maker's manual that confirms it, so check your own meter's manual before you rely on it.")


def load_crops():
    """Crop EC and pH ranges exactly as GrowLab ships them (OSU HLA-6722, Table 2), with the app's English names."""
    root = c.B.ROOT / "growlab-app/lib"
    names = dict(re.findall(r"String get crop(\w+) => '([^']+)';", (root / "l10n/app_localizations_en.dart").read_text()))
    out = []
    for cid, lo, hi, plo, phi in re.findall(r"Crop\('(\w+)', ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)", (root / "feature/models.dart").read_text()):
        out.append((names.get(cid[0].upper() + cid[1:], cid), float(lo), float(hi), float(plo), float(phi)))
    return sorted(out)


def ec_form(crop=True):
    opts = [("ms", "EC, mS/cm"), ("us", "EC, µS/cm"), ("ppm500", "ppm, 500 scale"), ("ppm640", "ppm, 640 scale"), ("ppm700", "ppm, 700 scale")]
    sel = "".join(f'<option value="{v}">{t}</option>' for v, t in opts)
    form = (inp("ecval", "Reading", "", "1.8") + f'<div><label for="ecfrom">Unit on your meter</label><select id="ecfrom">{sel}</select></div>'
            + '<div class="full"><label for="eccrop">Check against a crop <small>(optional)</small></label><select id="eccrop"></select></div>')
    result = rows("ec-ms", "Conductivity", [("ec-us", "In µS/cm"), ("ec-500", "500 scale (TDS, NaCl)"), ("ec-640", "640 scale"),
                                           ("ec-700", "700 scale (442)"), ("ec-crop", "Crop's range"), ("ec-ph", "Crop's pH")]) + '<div id="ec-verdict" class="verdict"></div>'
    return form, result


def build_ec(crops):
    ecs = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.5, 4.0]
    t1 = table("EC to ppm conversion chart", ["EC, mS/cm", "µS/cm", "ppm, 500 scale", "ppm, 640 scale", "ppm, 700 scale"],
               [[f"{ec:.1f}", n(ec * 1000)] + [n(m.ec_to_ppm(ec, s)) for s in ("500", "640", "700")] for ec in ecs],
               src(f"ppm = EC in µS/cm × 0.5 for NaCl-calibrated meters and × 0.7 for 442 (fertilizer-type) solutions: {HANNA}") + " " + SCALE_NOTE)
    t2 = table("Which scale is my meter? Reading in 1,413 µS/cm calibration solution", ["Scale", "Factor", "The meter shows"],
               [[f"{s} scale", f"× {m.EC_SCALES[s] / 1000:.2f}", f"{m.ec_to_ppm(1.413, s):.1f} ppm"] for s in ("500", "640", "700")],
               "Dip the meter in standard 1.413 mS/cm calibration solution: the ppm it shows tells you its factor.")
    ex = guides.example("a reservoir at 1.8 mS/cm", [
        "1.8 mS/cm is 1,800 µS/cm.",
        f"500 scale: 1,800 × 0.5 = {n(m.ec_to_ppm(1.8, '500'))} ppm. 700 scale: 1,800 × 0.7 = {n(m.ec_to_ppm(1.8, '700'))} ppm.",
        f"Going back: a feed chart that asks for 840 ppm on the 700 scale means 840 ÷ 700 = {m.ppm_to_ec(840, '700'):.1f} mS/cm, "
        f"which a 500-scale meter shows as {n(m.ec_to_ppm(m.ppm_to_ec(840, '700'), '500'))} ppm.",
    ], "Result: the same water reads 900 ppm on one meter and 1,260 ppm on another. Compare in EC.")
    answer = (f"ppm = EC (mS/cm) × 500, 640 or 700, depending on your meter's scale. 1.0 mS/cm is 500, 640 or 700 ppm; "
              f"1.8 mS/cm is {n(m.ec_to_ppm(1.8, '500'))}, {n(m.ec_to_ppm(1.8, '640'))} or {n(m.ec_to_ppm(1.8, '700'))} ppm. "
              "EC is the real measurement, so compare readings in EC.")
    form, result = ec_form()
    c.page(
        "hydroponics/ec-to-ppm-converter.html", "EC to PPM Converter (500, 640 and 700 Scale) with Chart | Free",
        "Free EC to ppm converter for hydroponics: mS/cm or µS/cm to ppm on the 500, 640 and 700 scales and back, with a conversion chart and a check against your crop's range.",
        "Hydroponics", "Free hydroponics tool", "EC to ppm converter",
        "Convert EC to ppm on the 500, 640 or 700 scale, or a ppm reading back to EC, and check it against a crop's published range.",
        answer, [t1, t2, ex], [
            ("How do I convert EC to ppm?",
             "Multiply the EC in mS/cm by your meter's scale: × 500, × 640 or × 700. To go back, divide the ppm by the same number. "
             "1.4 mS/cm is 700 ppm on the 500 scale and 980 ppm on the 700 scale."),
            ("Is my meter on the 500 or the 700 scale?",
             f"Check the manual, or dip the meter in 1.413 mS/cm calibration solution: about {m.ec_to_ppm(1.413, '500'):.1f} ppm means the 500 scale, "
             f"about {m.ec_to_ppm(1.413, '700'):.1f} ppm the 700 scale. "
             "Hanna's guide gives 0.5 for meters calibrated with sodium chloride and 0.7 for the 442 type solutions that behave like fertilizer."),
            ("Why do two meters show different ppm in the same water?",
             "Both measure the same conductivity and then multiply by a different factor. Nothing is wrong with either meter: they use different scales. "
             "That is why nutrient charts are easier to follow in EC."),
            ("Is ppm the real amount of nutrients in the water?",
             "No. A TDS meter does not weigh anything: it measures how well the water conducts electricity and converts that to an estimate. "
             "Different salts conduct differently, so treat ppm as a convenient label for EC."),
            ("What EC should my nutrient solution be?",
             f'It depends on the crop: see the <a href="{{rel}}hydroponics/ec-chart-by-crop.html">EC and pH chart by crop</a> '
             "with the ranges published by Oklahoma State University Extension."),
        ], "t-site", ("growlab", "ec-ppm", GROW_PITCH), "ec", form, result, "Conversion charts and worked example",
        data={"crops": crops}, extra=c.related("More hydroponics tools", [("hydroponics/ec-chart-by-crop.html", "EC and pH chart by crop"),
                                                                           ("hydroponics/vpd-chart.html", "VPD chart")]),
        embed=("ec-ppm", 740))


def build_crops(crops):
    def ph(lo, hi):
        return f"{lo:.1f}" if lo == hi else f"{lo:.1f}–{hi:.1f}"

    t1 = table("Target EC and pH for hydroponic vegetables, herbs and flowers",
               ["Crop", "EC, mS/cm", "ppm, 500 scale", "ppm, 700 scale", "pH"],
               [[name, f"{lo:.1f}–{hi:.1f}", f"{n(lo * 500)}–{n(hi * 500)}", f"{n(lo * 700)}–{n(hi * 700)}", ph(plo, phi)] for name, lo, hi, plo, phi in crops],
               src(f"EC and pH as printed in {OSU}; ppm columns computed from the EC range") + " These are the ranges the GrowLab app uses.")
    by = {name: (lo, hi, plo, phi) for name, lo, hi, plo, phi in crops}
    lo, hi, plo, phi = by["Lettuce"]
    ex = guides.example("checking a lettuce reservoir", [
        f"The published range for lettuce is {lo:.1f}–{hi:.1f} mS/cm at pH {ph(plo, phi)}.",
        f"Your meter shows 1,050 ppm and is on the 700 scale: 1,050 ÷ 700 = {m.ppm_to_ec(1050, '700'):.1f} mS/cm. Inside the range.",
        f"The same 1,050 ppm on a 500-scale meter would be {m.ppm_to_ec(1050, '500'):.1f} mS/cm: above the range, so you would add plain water.",
    ], "Result: know your meter's scale before you compare a ppm reading with a chart.")

    def crop_q(name):
        a, b, p1, p2 = by[name]
        return (f"What EC is best for hydroponic {name.lower()}?",
                f"{a:.1f}–{b:.1f} mS/cm, which is {n(a * 500)}–{n(b * 500)} ppm on the 500 scale or {n(a * 700)}–{n(b * 700)} ppm on the 700 scale, "
                f"at pH {ph(p1, p2)} (Oklahoma State University Extension, HLA-6722). Start young plants at the low end.")

    answer = (f"published target EC is {by['Lettuce'][0]:.1f}–{by['Lettuce'][1]:.1f} mS/cm for lettuce, {by['Basil'][0]:.1f}–{by['Basil'][1]:.1f} for basil, "
              f"{by['Tomato'][0]:.1f}–{by['Tomato'][1]:.1f} for tomato and {by['Strawberry'][0]:.1f}–{by['Strawberry'][1]:.1f} for strawberry "
              "(Oklahoma State University Extension). The chart below gives 23 crops with ppm on both scales and pH.")
    form, result = ec_form()
    c.page(
        "hydroponics/ec-chart-by-crop.html", "Hydroponic EC and pH Chart by Crop (EC, ppm 500 / 700) | Free",
        "Target EC, ppm and pH for 23 hydroponic vegetables, herbs and flowers, from Oklahoma State University Extension, with a checker for your own reading.",
        "Hydroponics", "Free hydroponics chart", "EC and pH chart by crop",
        "Published EC and pH ranges for hydroponic vegetables, herbs and flowers, with ppm on the 500 and 700 scales. Enter your reading to check it.",
        answer, [t1, ex], [crop_q("Lettuce"), crop_q("Tomato"), crop_q("Basil"), crop_q("Strawberry"), crop_q("Cucumber"), (
            "My EC is too high or too low. What do I do?",
            "Too high: add plain water. Too low: add nutrients at your label's ratio. Then stir, wait a few minutes and measure again. "
            "GrowLab works out the exact litres of water or millilitres of each part from your reservoir size."),
            ("Are these ranges right for every variety and system?",
             "They are starting points from one university fact sheet. Water quality, light, temperature and the variety all move the best value, "
             "so watch the plants and follow your nutrient maker's label.")],
        "t-site", ("growlab", "ec-chart", GROW_PITCH), "ec", form, result, "Crop chart and worked example",
        data={"crops": crops}, extra=c.related("More hydroponics tools", [("hydroponics/ec-to-ppm-converter.html", "EC to ppm converter"),
                                                                           ("hydroponics/vpd-chart.html", "VPD chart")]))


FAO56 = ('<a href="https://www.fao.org/4/x0490e/x0490e07.htm">FAO Irrigation and Drainage Paper 56 (Allen et al., 1998), '
         'Chapter 3, Eq. 11</a>')
FAO56_T23 = '<a href="https://www.fao.org/4/x0490e/x0490e0j.htm">FAO-56 Annex 2, Table 2.3</a>'
VPD_PITCH = ("A hydroponic nutrient calculator with a VPD screen: air temperature, humidity and your leaf offset give the leaf VPD "
             "and the humidity to aim for at each growth stage.")


def open_dataset(ds, what):
    """The line under a chart that names the open dataset; it links the Zenodo record once the DOI is in opendata.DOI."""
    doi = opendata.DOI.get(ds, "")
    name = f'<a href="https://doi.org/{doi}">open dataset (CC BY 4.0, DOI {doi})</a>' if doi else "open dataset under CC BY 4.0"
    return f"{what} is published as an {name}: CSV and JSON, with the formulas and checks."


def build_vpd():
    temps = list(range(15, 36))
    rhs = [30, 40, 50, 60, 70, 80, 90]
    off = m.LEAF_OFFSET_C
    t1 = table("Air VPD (kPa) by air temperature and relative humidity", ["Air"] + [f"{h} % RH" for h in rhs],
               [[f"{t} °C ({t * 9 / 5 + 32:.0f} °F)"] + [f"{m.leaf_vpd(t, t, h):.2f}" for h in rhs] for t in temps],
               src(f"computed with e°(T) = 0.6108 × exp(17.27 T ÷ (T + 237.3)) kPa from {FAO56}; air VPD = e°(air) × (1 − RH ÷ 100), "
                   "the leaf taken at air temperature", "26 November 2026"))
    t2 = table(f"Leaf VPD (kPa) for a leaf {abs(off):g} °C cooler than the air", ["Air / leaf"] + [f"{h} % RH" for h in rhs],
               [[f"{t} / {t + off:g} °C"] + [f"{m.leaf_vpd(t, t + off, h):.2f}" for h in rhs] for t in temps],
               src(f"leaf VPD = e°(leaf) − e°(air) × RH ÷ 100, the GrowLab app's formula and its default offset of {off:g} °C, with {FAO56}. "
                   "A negative value means the leaf is at or below the dew point", "26 November 2026")
               + " " + open_dataset("vpd-table", "The full table (every 5 % RH, with vapour pressures and dew point)"))
    t3 = table("Saturation vapour pressure: the formula against FAO's printed table", ["Temperature", "e°(T), Eq. 11", "FAO-56 Table 2.3"],
               [[f"{t} °C", f"{m.svp(t):.3f} kPa", f"{v:.3f} kPa"] for t, v in ((15, 1.705), (20, 2.338), (25, 3.168), (30, 4.243), (35, 5.623))],
               src(f"printed values from {FAO56_T23}", "26 November 2026") + " All 21 values from 15 to 35 °C match to the third decimal.")
    air, rh, leaf = 25, 60, 23
    ex = guides.example("a grow tent at 25 °C and 60 % RH", [
        f"Saturation vapour pressure at the air temperature: e°(25) = 0.6108 × exp(17.27 × 25 ÷ 262.3) = {m.svp(air):.3f} kPa.",
        f"The air holds 60 % of that: {m.svp(air):.3f} × 0.60 = {m.svp(air) * rh / 100:.3f} kPa.",
        f"Air VPD: {m.svp(air):.3f} − {m.svp(air) * rh / 100:.3f} = {m.leaf_vpd(air, air, rh):.2f} kPa.",
        f"The leaves read 23 °C on an infrared thermometer: e°(23) = {m.svp(leaf):.3f} kPa, so leaf VPD = {m.svp(leaf):.3f} − {m.svp(air) * rh / 100:.3f} = {m.leaf_vpd(air, leaf, rh):.2f} kPa.",
        f"For a leaf VPD of 1.2 kPa at the same temperatures the humidity would be ({m.svp(leaf):.3f} − 1.2) ÷ {m.svp(air):.3f} × 100 = {m.rh_for_vpd(air, leaf, 1.2):.0f} %.",
    ], f"Result: {m.leaf_vpd(air, air, rh):.2f} kPa in the air, {m.leaf_vpd(air, leaf, rh):.2f} kPa at the leaf. A cooler leaf means a lower VPD.")
    answer = (f"VPD = e°(T) × (1 − RH ÷ 100), with e°(T) = 0.6108 × exp(17.27 T ÷ (T + 237.3)) kPa (FAO-56). "
              f"At 25 °C and 60 % RH the air VPD is {m.leaf_vpd(25, 25, 60):.2f} kPa; with leaves 2 °C cooler it is {m.leaf_vpd(25, 23, 60):.2f} kPa. "
              f"At 20 °C and 70 % it is {m.leaf_vpd(20, 20, 70):.2f} kPa, at 30 °C and 50 % {m.leaf_vpd(30, 30, 50):.2f} kPa.")
    form = (seg("vunit", "Temperature unit", [("c", "°C"), ("f", "°F")]) + inp("vair", "Air temperature", "(°C)", "25")
            + inp("vrh", "Relative humidity", "(%)", "60") + inp("voff", "Leaf offset", "(°C, leaf minus air)", "-2")
            + inp("vtarget", "Target leaf VPD", "(kPa, optional)", "1.0"))
    result = rows("v-leaf", "Leaf VPD", [("v-air", "Air VPD (leaf at air temperature)"), ("v-es", "Saturation vapour pressure"),
                                         ("v-ea", "Actual vapour pressure"), ("v-dew", "Dew point"), ("v-rh", "Humidity for the target VPD")]) \
        + '<div id="v-note" class="verdict"></div>'
    c.page(
        "hydroponics/vpd-chart.html", "VPD Chart and Calculator (kPa): Air and Leaf VPD by Temperature and Humidity | Free",
        "Free VPD chart and calculator: vapour pressure deficit in kPa for 15–35 °C and 30–90 % humidity, for the air and for a leaf 2 °C cooler, from the FAO-56 formula.",
        "Hydroponics", "Free grow room chart", "VPD chart and calculator",
        "Vapour pressure deficit for your grow room or greenhouse from air temperature and humidity, for the air and at the leaf, with the humidity that gives a target VPD.",
        answer, [t1, t2, t3, ex], [
            ("What is VPD?",
             "Vapour pressure deficit is how much more water vapour the air could hold before it is saturated, in kilopascals. "
             "It drives transpiration: the higher the VPD, the faster leaves lose water. Unlike relative humidity it accounts for temperature, "
             "so 60 % RH is a different climate at 20 °C than at 30 °C."),
            ("How do I calculate VPD?",
             "Work out the saturation vapour pressure e°(T) = 0.6108 × exp(17.27 T ÷ (T + 237.3)) kPa (FAO-56, Eq. 11). "
             f"Air VPD = e°(air) × (1 − RH ÷ 100). Leaf VPD = e°(leaf) − e°(air) × RH ÷ 100. At 25 °C and 60 % the air VPD is {m.leaf_vpd(25, 25, 60):.2f} kPa."),
            ("Why use leaf temperature?",
             "The air spaces inside a leaf are saturated at the leaf's own temperature, which is usually a little below the air under lights. "
             f"A leaf 2 °C cooler than 25 °C air at 60 % has a VPD of {m.leaf_vpd(25, 23, 60):.2f} kPa instead of {m.leaf_vpd(25, 25, 60):.2f}. "
             "Measure your leaves with an infrared thermometer and enter the difference."),
            ("What VPD should I aim for?",
             "It depends on the crop and the stage, and the published advice is guidance rather than a rule. "
             '<a href="https://www.canr.msu.edu/floriculture/uploads/files/Water%20VPD.pdf">Michigan State University\'s floriculture team</a> '
             "suggests keeping VPD above about 0.5 kPa so plants transpire and foliar disease is held back, and notes that above about 1.5 kPa "
             "water loss is high. GrowLab starts from 0.4–0.8 kPa for seedlings and cuttings, 0.8–1.2 for vegetative growth and 1.0–1.5 for "
             "flowering and fruiting, as editable defaults."),
            ("What does a negative leaf VPD mean?",
             "The leaf is at or below the dew point of the air, so water condenses on it. That happens with cool leaves in very humid air "
             f"(at 25 °C and 90 % RH the dew point is {m.dew_point(25, 90):.1f} °C) and invites mould: raise the temperature or lower the humidity."),
            ("Does altitude change VPD?",
             "No. VPD depends on temperature and humidity only; air pressure does not enter the formula."),
        ], "t-site", ("growlab", "vpd-chart", VPD_PITCH), "vpd", form, result, "VPD charts and worked example",
        extra=c.related("More hydroponics tools", [("hydroponics/ec-to-ppm-converter.html", "EC to ppm converter"),
                                                   ("hydroponics/ec-chart-by-crop.html", "EC and pH chart by crop")]),
        extra_ld=[opendata.with_doi(opendata.VPD_LD, "vpd-table", ["vpd-table.csv", "vpd-table.json"])])


# ---------- WickCalc ----------

WICK_PITCH = "Wax and fragrance for any jar, your real cost per candle and the Etsy price that keeps a profit after fees."
# (wax, the supplier's listed fragrance load for container candles in %), from CandleScience product pages.
WAXES = [("Golden Brands 464 soy wax", 10), ("Golden Brands 444 soy wax", 10), ("IGI 6006 paraffin-soy blend", 10),
         ("IGI 4630 paraffin", 10), ("IGI 4627 paraffin", 12)]
CRAFTYBASE = '<a href="https://craftybase.com/candle-fragrance-load-calculator">Craftybase, candle fragrance load calculator</a>'


def oz(v):
    return f"{v:.2f} oz"


def build_fragrance():
    loads = [6, 8, 10, 12]
    t1 = table("Fragrance oil by wax weight and load (load as % of the wax)", ["Wax"] + [f"{p} %" for p in loads],
               [[label] + [f"{w * p / 100:.2f} oz" if unit == "oz" else f"{w * p / 100:.0f} g" for p in loads]
                for label, w, unit in (("8 oz", 8, "oz"), ("1 lb (16 oz)", 16, "oz"), ("2 lb", 32, "oz"), ("5 lb", 80, "oz"),
                                       ("10 lb", 160, "oz"), ("500 g", 500, "g"), ("1 kg", 1000, "g"), ("5 kg", 5000, "g"))],
               "Fragrance = wax weight × load ÷ 100. Weigh fragrance oil, do not measure it by volume: oils differ in density.")
    t2 = table("Fragrance load the supplier lists for common container waxes", ["Wax", "Listed load", "Per pound of wax"],
               [[w, f"{p} %", f"{p / 100 * 16:.1f} oz"] for w, p in WAXES],
               src("the container-candle fragrance load printed on each wax's product page at CandleScience (candlescience.com). "
                   f"{CRAFTYBASE}: most waxes support a maximum of 6–12 %, depending on the wax") + " Your wax maker's data sheet has the last word.")
    fo = m.fragrance_for_wax(16, 8)
    ex = guides.example("1 lb of soy wax at 8 %", [
        f"Fragrance: 16 oz × 8 ÷ 100 = {fo:.2f} oz.",
        f"Wax plus fragrance: 16 + {fo:.2f} = {16 + fo:.2f} oz to pour.",
        f"The same recipe counted against the whole candle is {m.convert_load(8):.2f} %: 8 % of the wax is not 8 % of the candle.",
    ], f"Result: weigh out {fo:.2f} oz ({fo * m.G_PER_OZ:.0f} g) of fragrance oil for 1 lb of wax.")
    answer = (f"fragrance = wax weight × load %. At 8 % one pound of wax takes {fo:.2f} oz of fragrance oil, at 10 % it takes "
              f"{m.fragrance_for_wax(16, 10):.1f} oz. \"1 oz per pound\" is 6.25 %. Most waxes hold 6–12 %; check your wax's data sheet.")
    form = (seg("funit", "Weight unit", [("oz", "Ounces"), ("g", "Grams")]) + inp("fwax", "Wax weight", "(oz)", "16") + inp("fload", "Fragrance load", "(% of the wax)", "8")
            + '<div class="full"><label for="fwaxtype">Wax <small>(optional, checks the supplier\'s listed load)</small></label><select id="fwaxtype"></select></div>')
    result = rows("f-fo", "Fragrance oil", [("f-total", "Wax + fragrance"), ("f-total-pct", "Same load, other basis"), ("f-perlb", "Rate")]) + '<div id="f-warn" class="verdict"></div>'
    c.page(
        "candles/fragrance-load-calculator.html", "Candle Fragrance Load Calculator: Oil by Wax Weight | Free",
        "Free fragrance load calculator for candles and wax melts: ounces or grams of fragrance oil for your wax weight and load %, with the load suppliers list for common waxes.",
        "Candles", "Free candle making tool", "Fragrance load calculator",
        "How much fragrance oil to weigh for your wax, in ounces or grams, and whether the load fits what the supplier lists for that wax.",
        answer, [t1, t2, ex], [
            ("How do I calculate fragrance load?",
             "Fragrance weight = wax weight × load ÷ 100, when the load is a percentage of the wax (the usual way in the US). "
             "16 oz of wax at 8 % needs 1.28 oz of fragrance oil."),
            ("Is the load a percentage of the wax or of the whole candle?",
             f"Most suppliers mean the wax. Some recipes mean the finished candle, which is a little more oil: "
             f"10 % of the wax is {m.convert_load(10):.2f} % of the candle, and 10 % of the candle is {m.convert_load(10, False):.2f} % of the wax. Check which one your recipe uses."),
            ("How much fragrance oil per pound of wax?",
             "1 oz per pound is 6.25 %, 1.3 oz is about 8 %, 1.6 oz is 10 % and 1.9 oz is about 12 %."),
            ("What is the maximum fragrance load?",
             "It depends on the wax. CandleScience lists 10 % for Golden Brands 464 and 444, IGI 6006 and IGI 4630, and 12 % for IGI 4627 in container candles. "
             "More oil than the wax can hold seeps out and can burn badly, so stay within your wax maker's data sheet."),
            ("Does this work for wax melts?",
             "The arithmetic is the same: wax weight × load. Melt waxes have their own limits, so use the figure from that wax's data sheet."),
        ], "t-elec", ("wickcalc", "fragrance", WICK_PITCH), "frag", form, result, "Fragrance charts and worked example",
        data={"waxes": WAXES}, extra=c.related("More candle tools", [("candles/candle-wax-calculator.html", "Candle wax calculator")]),
        embed=("fragrance-load", 680))


def build_jar():
    def line(water):
        fill = m.fill_from_water(water)
        w8, f8 = m.candle_split(fill, 8)
        w10, f10 = m.candle_split(fill, 10)
        return [f"{water} oz", oz(fill), oz(w8), oz(f8), oz(w10), oz(f10)]

    t1 = table("Wax and fragrance by the water a jar holds (wax factor 0.86)",
               ["Water to the fill line", "Wax + fragrance", "Wax at 8 %", "Fragrance at 8 %", "Wax at 10 %", "Fragrance at 10 %"],
               [line(w) for w in (4, 6, 8, 10, 12, 16)],
               src('water weight × 0.86 for the fill, then wax = fill ÷ (1 + load): the method in <a href="https://armatagecandlecompany.com/blog/wax-per-candle/">'
                   'Armatage Candle Company, "How To Calculate Your Wax Per Candle"</a>, which notes that common candle waxes are 82–95 % as dense as water',
                   "26 October 2026") + " Weights in ounces by weight, load as % of the wax.")
    fill = m.fill_from_water(8)
    wax, fo = m.candle_split(fill, 8)
    k = 12 * 1.05
    per_10lb = int(160 // wax)
    ex = guides.example("twelve candles in jars that hold 8 oz of water", [
        f"Fill per candle: 8 oz of water × 0.86 = {fill:.2f} oz of wax and fragrance.",
        f"At 8 % of the wax: wax = {fill:.2f} ÷ 1.08 = {wax:.2f} oz, fragrance = {fo:.2f} oz.",
        f"Twelve candles with 5 % extra for the pot and spills: {wax * k:.1f} oz of wax ({wax * k / 16:.2f} lb) and {fo * k:.2f} oz of fragrance.",
    ], f"Result: melt about {wax * k / 16:.1f} lb of wax and weigh {fo * k:.1f} oz of fragrance oil.")
    answer = (f"weigh the water your jar holds to the fill line and multiply by 0.86. A jar that holds 8 oz of water takes {fill:.2f} oz of wax and fragrance: "
              f"at 8 % that is {wax:.2f} oz of wax and {fo:.2f} oz of oil. Ten pounds of wax fills about {per_10lb} of those jars.")
    form = (seg("junit", "Weight unit", [("oz", "Ounces"), ("g", "Grams")]) + inp("jwater", "Jar holds", "(oz of water)", "8") + inp("jfactor", "Wax factor", "(0.86 is typical)", "0.86")
            + inp("jload", "Fragrance load", "(% of the wax)", "8") + inp("jcount", "Candles", "", "12", attrs='inputmode="numeric"')
            + inp("jextra", "Extra for spills", "(%)", "5", True))
    result = rows("j-wax", "Per candle", [("j-fo", "Fragrance per candle"), ("j-fill", "Wax + fragrance per candle"), ("j-twax", "Wax for the batch"),
                                          ("j-tfo", "Fragrance for the batch")]) + '<p class="note">Pour one test candle, weigh it and adjust the wax factor for your wax and jar.</p>'
    c.page(
        "candles/candle-wax-calculator.html", "Candle Wax Calculator: How Much Wax per Jar? | Free",
        "Free candle wax calculator: how much wax and fragrance oil for a 4, 8, 12 or 16 oz jar and for a whole batch, from the water the jar holds.",
        "Candles", "Free candle making tool", "Candle wax calculator",
        "How much wax and fragrance oil one jar takes, and the totals for a batch, from the weight of water the jar holds to the fill line.",
        answer, [t1, ex], [
            ("How much wax do I need for an 8 oz jar?",
             f"If the jar holds 8 oz of water to your fill line, it takes {fill:.2f} oz of wax and fragrance together. "
             f"With an 8 % fragrance load that is {wax:.2f} oz of wax and {fo:.2f} oz of oil."),
            ("Why multiply by 0.86?",
             "Wax is lighter than water: common candle waxes weigh 82–95 % as much as the same volume of water, and 0.86 is the usual starting value. "
             "Weigh a finished test candle to find the real factor for your wax."),
            ("How do I measure what my jar holds?",
             "Put the empty jar on a scale, zero it and fill with water to the line where the wax will stop. The reading is the number to enter. "
             "Without a scale: 1 US fluid ounce of water weighs about 1.04 oz (29.6 g)."),
            ("How many candles does 10 lb of wax make?",
             f"For jars that hold 8 oz of water at an 8 % load, each candle takes {wax:.2f} oz of wax, so 10 lb (160 oz) fills about {per_10lb} candles before spills."),
            ("Is an 8 oz jar 8 oz of wax?",
             "No. Jars are named by the volume they hold, not by the weight of wax. An 8 fl oz jar filled to the brim holds about 8.3 oz of water by weight, "
             "and you normally stop below the brim, so measure to your own fill line."),
        ], "t-elec", ("wickcalc", "wax", WICK_PITCH), "jar", form, result, "Jar chart and worked example",
        extra=c.related("More candle tools", [("candles/fragrance-load-calculator.html", "Fragrance load calculator")]),
        embed=("candle-wax", 820))


# ---------- Dial In ----------

DIAL_PITCH = "Sour or bitter shot? Log it and Dial In tells you the one change for the next shot, with the number: \"Grind finer: 13 → 12\"."
LM = ('<a href="https://home.lamarzoccousa.com/brew-ratios-around-world/">La Marzocco Home, "Brew Ratios Around the World"</a>')
SCA = ('<a href="https://sca.coffee/sca-news/25-magazine/issue-3/defining-ever-changing-espresso-25-magazine-issue-3">SCA 25 Magazine, '
       '"Defining the Ever-Changing Espresso"</a>')


def build_espresso():
    ratios = [1.5, 2.0, 2.5, 3.0]
    t1 = table("Espresso yield by dose and brew ratio", ["Dose in"] + [f"1:{r:g}" for r in ratios],
               [[f"{d} g"] + [f"{d * r:g} g" for r in ratios] for d in (14, 15, 16, 17, 18, 19, 20, 21, 22)],
               "Yield = dose × ratio, both weighed in grams: the dry coffee in the basket and the liquid espresso in the cup.")
    t2 = table("What the ratio is called", ["Style", "Dial In and this calculator", "La Marzocco Home's guide"],
               [["Ristretto", "up to 1:1.5", "1:1 to 1:2"], ["Normale (espresso)", "1:1.5 to 1:2.5", "1:2 to 1:3"], ["Lungo", "above 1:2.5", "1:3 to 1:4"]],
               src(f"{LM}. There is no single standard for these names: sources draw the lines in different places, so go by the number"))
    ex = guides.example("18 g in, 36 g out", [
        f"Ratio = yield ÷ dose = 36 ÷ 18 = {m.brew_ratio(18, 36):.1f}, written 1:2.",
        f"That is a {m.shot_style(2.0)} shot in this calculator, the usual place to start dialling in.",
        "Sour and thin? Keep the dose and grind finer, or run it longer to 1:2.2 (about 40 g). Bitter and harsh? Grind coarser or stop at 1:1.8 (about 32 g).",
    ], "Result: 18 g of coffee and 36 g of espresso is a 1:2 ratio.")
    answer = ("brew ratio = espresso out ÷ coffee in, by weight. 18 g in and 36 g out is 1:2, a common starting point; "
              "1:1.5 from the same dose is 27 g out and 1:2.5 is 45 g. Weigh the shot, do not go by volume.")
    form = (seg("emode", "What to find", [("ratio", "Ratio"), ("yield", "Yield"), ("dose", "Dose")])
            + inp("edose", "Dose in", "(g of ground coffee)", "18", True) + inp("eyield", "Yield out", "(g of espresso)", "36", True)
            + inp("eratio", "Ratio 1 :", "(for example 2)", "2", True))
    result = rows("e-main", "Result", [("e-dose", "Dose in"), ("e-yield", "Yield out"), ("e-ratio", "Brew ratio"), ("e-style", "Style")]) + '<p class="note">A starting point. Your taste decides.</p>'
    c.page(
        "coffee/espresso-ratio-calculator.html", "Espresso Ratio Calculator: Dose, Yield and Brew Ratio | Free",
        "Free espresso brew ratio calculator: enter dose and yield to get the ratio, or dose and ratio to get the yield. With a yield chart for 14 to 22 g doses.",
        "Coffee", "Free coffee tool", "Espresso ratio calculator",
        "The brew ratio from your dose and yield, or the yield to aim for from your dose and a target ratio.",
        answer, [t1, t2, ex], [
            ("What is a 1:2 espresso ratio?",
             "Two grams of liquid espresso for every gram of ground coffee: 18 g in the basket and 36 g in the cup. It is the common starting point for a modern espresso."),
            ("How much espresso should I get from 18 g of coffee?",
             "27 g at 1:1.5, 36 g at 1:2, 45 g at 1:2.5 and 54 g at 1:3. Start at 36 g and adjust by taste."),
            ("How long should an espresso shot take?",
             "There is no rule, but 25 to 30 seconds is typical: in a barista survey reported by the Specialty Coffee Association's 25 Magazine, "
             "about half the baristas pulled shots in that window. Use time as a clue and taste as the judge."),
            ("What is the difference between ristretto, espresso and lungo?",
             "The same dose with less or more water through it. A ristretto is shorter and more concentrated, a lungo longer and lighter. "
             "Where one ends and the next begins depends on who you ask, so the table above shows two sets of ranges."),
            ("Why weigh the shot instead of measuring millilitres?",
             "Crema is mostly gas, so the volume in the cup changes with the freshness of the beans while the weight does not. A small scale under the cup gives repeatable shots."),
        ], "t-roof", ("dial-in", "espresso-ratio", DIAL_PITCH), "ratio", form, result, "Yield chart and worked example",
        embed=("espresso-ratio", 740))


# ---------- RowKeeper ----------

ROW_PITCH = "A knitting and crochet row counter that shows your next row in words from your pattern, with a yarn calculator and backups. No ads."
CYC = '<a href="https://www.craftyarncouncil.com/standards/yarn-weight-system">Craft Yarn Council, Standard Yarn Weight System</a>'
# Example sizes in inches (width, length); the user's own measurements always win.
SIZES = [("Scarf, 8 × 60 in", 8, 60), ("Hat body, 21 × 8 in", 21, 8), ("Baby blanket, 30 × 36 in", 30, 36), ("Throw blanket, 50 × 60 in", 50, 60)]
CYC_GAUGE = [("1 Super Fine", "27–32", "2.25–3.25 mm (US 1–3)"), ("2 Fine", "23–26", "3.25–3.75 mm (US 3–5)"), ("3 Light", "21–24", "3.75–4.5 mm (US 5–7)"),
             ("4 Medium", "16–20", "4.5–5.5 mm (US 7–9)"), ("5 Bulky", "12–15", "5.5–8 mm (US 9–11)"), ("6 Super Bulky", "7–11", "8–12.75 mm (US 11–17)")]


def build_yarn():
    per_swatch = [5, 7, 9, 12, 15]
    t1 = table("Yarn by project size and how much yarn a 4 × 4 in swatch takes", ["Project (example size)"] + [f"{y} yd per swatch" for y in per_swatch],
               [[name] + [f"{n(m.swatch_yarn(4, 4, y, w, l))} yd" for y in per_swatch] for name, w, l in SIZES],
               "Yarn = swatch yarn × project area ÷ swatch area, before any extra. Sizes are examples: enter your own. "
               "The hat is counted as a tube, head circumference × height, so it comes out a little generous.")
    swatch = m.length_from_weight(100, 220, 3.2)
    need = m.swatch_yarn(4, 4, swatch, 8, 60)
    total, balls = m.skeins_needed(need, 220, 10)
    ex = guides.example("a scarf from a swatch", [
        f"Your 4 × 4 in swatch weighs 3.2 g. The ball band says 100 g is 220 yd, so the swatch holds 3.2 × 220 ÷ 100 = {swatch:.2f} yd.",
        f"The scarf is 8 × 60 in = 480 sq in, which is 480 ÷ 16 = 30 swatches: 30 × {swatch:.2f} = {need:.0f} yd.",
        f"Add 10 % for the cast-on, ends and tension: {total:.0f} yd. One ball is 220 yd, so {total:.0f} ÷ 220 = {total / 220:.2f}, round up.",
    ], f"Result: about {total:.0f} yd ({total * m.M_PER_YD:.0f} m), buy {balls} balls from one dye lot.")
    answer = (f"knit a swatch in your stitch, weigh it, and scale by area. If a 4 × 4 in swatch takes {swatch:.0f} yd, an 8 × 60 in scarf needs about {need:.0f} yd "
              f"and a 50 × 60 in throw about {n(m.swatch_yarn(4, 4, swatch, 50, 60))} yd, plus about 10 % extra. No yardage table knows your yarn, needles and stitch.")
    form = (seg("yunit", "Units", [("in", "Inches, yards"), ("cm", "Centimetres, metres")])
            + '<div><label for="yw">Swatch width <small class="y-dim">(in)</small></label><input id="yw" inputmode="decimal" value="4"></div>'
            + '<div><label for="yh">Swatch height <small class="y-dim">(in)</small></label><input id="yh" inputmode="decimal" value="4"></div>'
            + inp("ysw", "Swatch weight", "(g)", "3.2", True)
            + inp("ybw", "Ball weight on the band", "(g)", "100") + inp("ybl", "Ball length on the band", "(yd)", "220")
            + '<div class="full"><label for="yproj">Project</label><select id="yproj"></select></div>'
            + '<div><label for="ypw">Width <small class="y-dim">(in)</small></label><input id="ypw" inputmode="decimal" value="8"></div>'
            + '<div><label for="ypl">Length <small class="y-dim">(in)</small></label><input id="ypl" inputmode="decimal" value="60"></div>'
            + inp("yextra", "Extra", "(%)", "10", True))
    result = rows("y-len", "Yarn needed", [("y-alt", "Other unit"), ("y-wt", "By weight"), ("y-sk", "Balls to buy"), ("y-swatch", "Yarn in your swatch")]) \
        + '<p class="note">An estimate: ribbing, cables and lace use yarn differently from plain rows, so swatch in the stitch you will use. Buy one dye lot.</p>'
    c.page(
        "knitting/yarn-yardage-calculator.html", "Yarn Yardage Calculator: Scarf, Hat or Blanket from a Swatch | Free",
        "Free yarn calculator for knitting and crochet: how much yarn a scarf, hat or blanket needs, worked out from your own swatch, in yards, metres, grams and balls.",
        "Knitting", "Free knitting and crochet tool", "Yarn yardage calculator",
        "How much yarn a scarf, hat or blanket needs, from a swatch in your own yarn, needles and stitch. Works for knitting and crochet.",
        answer, [t1, ex], [
            ("How much yarn do I need for a scarf?",
             f"It depends on the yarn and the stitch, which is why a swatch beats a table. As an example, if your 4 × 4 in swatch takes {swatch:.0f} yd, "
             f"a plain 8 × 60 in scarf needs about {need:.0f} yd, or {total:.0f} yd with 10 % extra."),
            ("How much yarn do I need for a blanket?",
             f"With the same {swatch:.0f} yd swatch, a 30 × 36 in baby blanket needs about {n(m.swatch_yarn(4, 4, swatch, 30, 36))} yd and a 50 × 60 in throw about "
             f"{n(m.swatch_yarn(4, 4, swatch, 50, 60))} yd before the extra. Thicker yarn covers the same area with fewer yards."),
            ("How do I find the yards in my swatch?",
             "Weigh the swatch on a kitchen scale. Yards in the swatch = swatch weight × yards on the ball band ÷ grams on the ball band. "
             "A 3.2 g swatch from a 100 g, 220 yd ball holds about 7 yd."),
            ("Does this work for crochet?",
             "Yes. Crochet a swatch in the stitch you will use and weigh it. The calculator only scales your own swatch, so the stitch is already counted."),
            ("How much extra yarn should I buy?",
             "About 10 % covers the cast-on, bind-off, ends and small tension changes. Add more for fringe, pompoms or a border, and buy it all from one dye lot."),
        ], "t-soap", ("rowkeeper", "yarn", ROW_PITCH), "yarn", form, result, "Yarn chart and worked example",
        data={"sizes": SIZES}, extra=c.related("More knitting tools", [("knitting/gauge-calculator.html", "Knitting gauge calculator")]))


def build_gauge():
    gauges = [12, 14, 16, 18, 20, 22, 24, 28]
    widths = [8, 20, 30, 40, 50]
    t1 = table("Stitches to cast on by gauge and width", ["Gauge, stitches per 4 in"] + [f"{w} in wide" for w in widths],
               [[f"{g} sts"] + [str(m.gauge_count(g, w)) for w in widths] for g in gauges],
               "Stitches = gauge ÷ 4 × width, rounded to a whole stitch. Round to your pattern repeat and add edge stitches if the pattern has them.")
    t2 = table("Usual knit gauge by yarn weight", ["Yarn weight", "Stitches per 4 in, stockinette", "Recommended needle"],
               [list(r) for r in CYC_GAUGE], src(f"{CYC}. Ranges are guidelines: your own swatch is the gauge that counts"))
    ex = guides.example("a 20 in wide blanket panel", [
        "You count 18 stitches and 24 rows over a 4 in square of your swatch.",
        f"Per inch: 18 ÷ 4 = 4.5 stitches. Cast on 4.5 × 20 = {m.gauge_count(18, 20)} stitches.",
        f"Rows: 24 ÷ 4 = 6 per inch. For 60 in of length, 6 × 60 = {m.gauge_count(24, 60)} rows.",
    ], f"Result: cast on {m.gauge_count(18, 20)} stitches and work {m.gauge_count(24, 60)} rows.")
    answer = (f"stitches to cast on = stitches per 4 in ÷ 4 × the width in inches. At 18 stitches per 4 in, a 20 in piece needs {m.gauge_count(18, 20)} stitches; "
              f"at 14 it needs {m.gauge_count(14, 20)}. Measure the gauge on a washed swatch, away from the edges.")
    form = (seg("gunit2", "Units", [("in", "Inches"), ("cm", "Centimetres")])
            + inp("gsts", "Stitches counted", "", "18", attrs='inputmode="decimal"')
            + '<div><label for="gsw">Over a width of <small class="g-dim">(in)</small></label><input id="gsw" inputmode="decimal" value="4"></div>'
            + inp("grows", "Rows counted", "", "24")
            + '<div><label for="gsh">Over a height of <small class="g-dim">(in)</small></label><input id="gsh" inputmode="decimal" value="4"></div>'
            + '<div><label for="gw">Finished width <small class="g-dim">(in)</small></label><input id="gw" inputmode="decimal" value="20"></div>'
            + '<div><label for="gl">Finished length <small class="g-dim">(in)</small></label><input id="gl" inputmode="decimal" value="60"></div>')
    result = rows("g-cast", "Cast on", [("g-rows", "Rows to work"), ("g-gauge", "Your gauge"), ("g-per1", "Per unit")])
    c.page(
        "knitting/gauge-calculator.html", "Knitting Gauge Calculator: Stitches to Cast On and Rows | Free",
        "Free knitting gauge calculator: count the stitches and rows in your swatch and get the stitches to cast on and the rows to work for any width and length.",
        "Knitting", "Free knitting and crochet tool", "Knitting gauge calculator",
        "From the stitches and rows you count in a swatch to the stitches to cast on and the rows to work, for any finished size.",
        answer, [t1, t2, ex], [
            ("How do I measure knitting gauge?",
             "Knit a swatch at least 5 in square in the pattern stitch, wash and dry it the way you will treat the finished piece, lay it flat and count the stitches "
             "and rows over 4 in in the middle, away from the edges."),
            ("How many stitches do I cast on for a 20 inch width?",
             f"{m.gauge_count(16, 20)} stitches at 16 per 4 in, {m.gauge_count(18, 20)} at 18 and {m.gauge_count(20, 20)} at 20. "
             "Divide your gauge by 4 and multiply by the width."),
            ("My gauge does not match the pattern. What now?",
             "Change the needle size and swatch again: a larger needle gives fewer stitches per inch. If you like the fabric as it is, "
             "recalculate the cast-on from your own gauge with this calculator and expect to use a different amount of yarn."),
            ("Does row gauge matter?",
             "For pieces worked to a length (\"knit until 10 in\"), hardly. For shaping counted in rows, such as sleeve caps, raglans and colourwork charts, it does."),
            ("Does it work for crochet?",
             "Yes. Count stitches and rows in a crochet swatch the same way: the arithmetic is identical. The yarn weight table above is for knitting gauge."),
        ], "t-soap", ("rowkeeper", "gauge", ROW_PITCH), "gauge", form, result, "Gauge charts and worked example",
        extra=c.related("More knitting tools", [("knitting/yarn-yardage-calculator.html", "Yarn yardage calculator")]))


def build():
    crops = load_crops()
    build_abv()
    build_honey()
    build_ec(crops)
    build_crops(crops)
    build_gravity()
    build_vpd()
    build_fragrance()
    build_jar()
    build_espresso()
    build_yarn()
    build_gauge()


# Rows for the methodology page (trust.METHODS): (calculator, page, tables and formulas, assumptions, limits).
METHODS = [
    ("Mead ABV and honey calculators", "brewing/mead-abv-calculator.html",
     ["ABV = (OG &minus; FG) &times; 131.25, and Michael Hall's formula (Zymurgy, Summer 1995) for strong meads and wines, as published by Brewer's Friend.",
      "Brix or Plato to SG: 1 + &deg;P &divide; (258.6 &minus; &deg;P &divide; 258.2 &times; 227.1); SG to Plato by the ASBC polynomial.",
      "Honey: 35 gravity points per pound per US gallon (Ken Schramm, The Compleat Meadmaker, 2003).",
      "Mead sweetness and strength classes from the BJCP Mead Guidelines (read 12 November 2026)."],
     ["Readings are taken with a hydrometer at its calibration temperature.", "The batch volume is the finished must, honey included."],
     ["Honey varies with its water content: measure the gravity after mixing.",
      "A refractometer reads too high once alcohol is present; the page does not correct for it.",
      "Honey or sugar added during fermentation is not counted unless you add its points to the original gravity."]),
    ("EC to ppm converter and crop chart", "hydroponics/ec-to-ppm-converter.html",
     ["ppm = EC in &micro;S/cm &times; 0.5 for NaCl-calibrated meters and &times; 0.7 for 442-type solutions (Hanna Instruments, read 12 November 2026).",
      "Crop EC and pH ranges: Oklahoma State University Extension, HLA-6722, Table 2, for 23 vegetables, herbs and flowers, as the GrowLab app ships them."],
     ["Your meter is calibrated and temperature-compensated."],
     ["The 640 scale is arithmetic only: no meter maker's manual was found that confirms a 0.64 factor.",
      "Crop ranges are starting points from one fact sheet; variety, water and climate move them. Follow your nutrient maker's label."]),
    ("Brix, Plato and SG chart", "brewing/brix-plato-sg-chart.html",
     ["Brix or Plato to SG: 1 + &deg;P &divide; (258.6 &minus; &deg;P &divide; 258.2 &times; 227.1), the Lyons equation as published by Brewer's Friend; SG to degrees by the ASBC polynomial.",
      "Potential ABV = (SG &minus; 1.000) &times; 131.25, and Michael Hall's formula (Zymurgy, Summer 1995).",
      "Checked against the NBS Circular C457 sucrose table (apparent SG 20/20 &deg;C): within 0.0003 up to 40 &deg;Bx (read 26 November 2026)."],
     ["Brix and Plato are treated as one scale, as in the Ferment app.", "The must ferments to 1.000 for the potential ABV."],
     ["Apparent SG of pure sugar solutions at 20 &deg;C: wort and juice contain other solids.",
      "A refractometer reading needs the wort correction factor, and a separate correction once alcohol is present.",
      "Above about 30 &deg;Bx yeast stops before 1.000, so the potential ABV is a ceiling."]),
    ("VPD chart and calculator", "hydroponics/vpd-chart.html",
     ["Saturation vapour pressure e&deg;(T) = 0.6108 &times; exp(17.27 T &divide; (T + 237.3)) kPa, FAO-56 Eq. 11; it reproduces FAO's Annex 2 Table 2.3 to the third decimal from 15 to 35 &deg;C.",
      "Leaf VPD = e&deg;(leaf) &minus; e&deg;(air) &times; RH &divide; 100, and the humidity for a target VPD by the inverse, as in the GrowLab app."],
     ["The leaf is 2 &deg;C cooler than the air (GrowLab's default) unless you enter your own offset."],
     ["Target VPD ranges are guidance from extension and trade sources, not data; the page does not judge a reading.",
      "Leaf temperature varies across the canopy: measure it with an infrared thermometer."]),
    ("Candle fragrance and wax calculators", "candles/fragrance-load-calculator.html",
     ["Fragrance = wax weight &times; load, with the load as a percentage of the wax.",
      "Wax and fragrance in a jar = weight of water to the fill line &times; 0.86 (Armatage Candle Company; common waxes are 82&ndash;95 % as dense as water), then wax = fill &divide; (1 + load).",
      "Listed fragrance loads for five container waxes from their CandleScience product pages (read 12 November 2026)."],
     ["The wax factor 0.86 until you measure your own from a test candle."],
     ["A listed load is the supplier's figure for container candles, not a promise for your wick, jar and oil: test burn.",
      "It does not pick a wick."]),
    ("Espresso ratio calculator", "coffee/espresso-ratio-calculator.html",
     ["Brew ratio = espresso out &divide; coffee in, by weight.",
      "Style names use the Dial In app's lines (ristretto up to 1:1.5, normale to 1:2.5, lungo beyond); La Marzocco Home's ranges are shown next to them."],
     ["Both weights are in grams."],
     ["There is no single standard for ristretto, normale and lungo. Taste decides, not the ratio."]),
    ("Yarn yardage and gauge calculators", "knitting/yarn-yardage-calculator.html",
     ["Yarn = yarn in your swatch &times; project area &divide; swatch area; yarn in the swatch = swatch weight &times; length on the ball band &divide; weight on the ball band.",
      "Balls to buy are rounded up, as in the RowKeeper app. Stitches to cast on = gauge &divide; 4 &times; width.",
      "Usual gauge by yarn weight: Craft Yarn Council, Standard Yarn Weight System (read 12 November 2026)."],
     ["The project is worked in the same yarn, needles and stitch as the swatch.", "A hat is counted as a tube, so it comes out a little generous."],
     ["No yardage tables: the result is only as good as your swatch.", "Shaping, cables, lace and borders change the amount."]),
]
