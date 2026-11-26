"""Aquarium pages (TankLog): the free (un-ionized) ammonia chart and calculator, and seawater salinity to specific
gravity. Each page is the visible face of an open dataset in experimental/open-data (aquarium-ammonia-fraction,
seawater-salinity-specific-gravity): the same equations, the same rounding, and a Dataset block with "#dataset".
The maths below is repeated in assets/aquarium.js for the live calculators; tests/test_aquarium.py holds the two
together and against the published check values.
"""
import copy
import math

import calcs_common as c
import guides
import opendata
from calcs_common import src, table
from pages_hobby import inp, rows, seg

NH3_PAGE = "aquarium/ammonia-toxicity-chart.html"
SALT_PAGE = "aquarium/salinity-to-specific-gravity.html"
HOME_CARDS = [
    (NH3_PAGE, "Aquarium", "Ammonia toxicity chart", "Free NH₃ from your test kit's total ammonia, pH and temperature.", "t-water"),
    (SALT_PAGE, "Aquarium", "Salinity to specific gravity", "ppt to SG and back on the 77, 68 and 60 °F scales.", "t-water"),
]
CHECKED = "26 November 2026"
TANK_PITCH = ("Log your aquarium's water tests by tapping the numbers on your kit's color chart, see what is off, "
              "and how big a water change brings it back. The free-ammonia and salinity tools use these same formulas.")

# ---------- maths (the same as assets/aquarium.js and the open datasets) ----------


def pka(t_c):
    """Emerson et al. (1975) as US EPA prints it: pKa = 0.09018 + 2729.92 / (273.2 + t)."""
    return 0.09018 + 2729.92 / (273.2 + t_c)


def nh3_fraction(ph, t_c):
    return 1 / (1 + 10 ** (pka(t_c) - ph))


def f_to_c(f):
    return (f - 32) * 5 / 9


def pure_water(t):
    """Density of pure water (SMOW), kg/m³, as adopted in EOS-80."""
    return 999.842594 + 6.793952e-2 * t - 9.095290e-3 * t ** 2 + 1.001685e-4 * t ** 3 - 1.120083e-6 * t ** 4 + 6.536332e-9 * t ** 5


def density(s, t):
    """EOS-80 one-atmosphere density of seawater, kg/m³ (Millero & Poisson 1981)."""
    a = 8.24493e-1 - 4.0899e-3 * t + 7.6438e-5 * t ** 2 - 8.2467e-7 * t ** 3 + 5.3875e-9 * t ** 4
    b = -5.72466e-3 + 1.0227e-4 * t - 1.6546e-6 * t ** 2
    return pure_water(t) + a * s + b * s * math.sqrt(s) + 4.8314e-4 * s * s


SCALES = {"s25": (25.0, "25/25 °C (77 °F)"), "s20": (20.0, "20/20 °C (68 °F)"), "s60f": (f_to_c(60), "60/60 °F (15.6 °C)")}


def sg(s, t=25.0):
    return density(s, t) / pure_water(t)


def salinity_from_sg(value, t=25.0):
    lo, hi = 0.0, 50.0
    if value <= sg(lo, t):
        return 0.0
    if value >= sg(hi, t):
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if sg(mid, t) < value else (lo, mid)
    return (lo + hi) / 2


def salt_g_per_l(s):
    return s * density(s, 25) / 1000


def sig(x, n=3):
    """3 significant figures, trailing zeros kept: 1.20, 0.0569, 44.6."""
    return f"{x:#.{n}g}".rstrip(".")


# ---------- Dataset markup ----------

def dataset_ld(key, ld):
    """The open dataset's schema.org block (copied from open-data), with the Zenodo DOI and its downloads once
    opendata.DOI has one."""
    d = copy.deepcopy(ld)
    d.update(opendata.doi_props(key))
    doi = opendata.DOI.get(key, "")
    if doi:
        rec = doi.rsplit(".", 1)[1]
        d["distribution"] = [{"@type": "DataDownload", "encodingFormat": t, "contentUrl": f"https://zenodo.org/records/{rec}/files/{key}.{x}?download=1"}
                             for x, t in (("csv", "text/csv"), ("json", "application/json"))]
    return d


def dataset_note(key, what):
    """A line under the tables naming the open dataset; with its DOI once it is on Zenodo."""
    doi = opendata.DOI.get(key, "")
    where = f' Download it as CSV or JSON from <a href="https://doi.org/{doi}">Zenodo (doi:{doi})</a>.' if doi else ""
    return (f'<section><h2>Open data</h2><p>The full table, {what}, is an open dataset under the '
            f'<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> licence: use it anywhere, with credit.{where}</p></section>')


SCRIPT = '<script defer src="{rel}assets/aquarium.js"></script>'

# ---------- ammonia ----------

EMERSON = '<a href="https://doi.org/10.1139/f75-274">Emerson, Russo, Lund and Thurston (1975), J. Fish. Res. Board Can. 32: 2379–2383</a>'
EPA_2013 = ('<a href="https://19january2021snapshot.epa.gov/sites/static/files/2015-08/documents/aquatic-life-ambient-water-quality-criteria-for-ammonia-freshwater-2013.pdf">'
            'US EPA, Aquatic Life Ambient Water Quality Criteria for Ammonia – Freshwater 2013 (EPA-822-R-13-001), p. 7</a>')
EPA_1984 = ('<a href="https://19january2021snapshot.epa.gov/sites/static/files/2019-02/documents/ambient-wqc-ammonia-1984.pdf">'
            'US EPA, Ambient Water Quality Criteria for Ammonia – 1984, p. 3</a>')
NH3_TEMPS = [10, 15, 20, 22, 24, 26, 28, 30]
NH3_PHS = [round(6.0 + i / 5, 1) for i in range(16)]  # 6.0 … 9.0 in steps of 0.2
READINGS = [0.25, 0.5, 1, 2, 4, 8]  # the usual colour-chart steps (TankLog's quick-value chips)
KIT_PHS = [6.6, 7.0, 7.4, 7.8, 8.0, 8.2, 8.4]
KIT_T = 26


def build_nh3():
    t1 = table("Un-ionized ammonia (NH₃) as a percentage of total ammonia",
               ["pH"] + [f"{t} °C ({t * 9 / 5 + 32:.0f} °F)" for t in NH3_TEMPS],
               [[f"{ph:.1f}"] + [f"{sig(100 * nh3_fraction(ph, t))} %" for t in NH3_TEMPS] for ph in NH3_PHS],
               src(f"computed with the equation of {EMERSON}, as printed in {EPA_2013}: pKa = 0.09018 + 2729.92 ÷ (273.2 + t), "
                   "NH₃ % = 100 ÷ (1 + 10^(pKa − pH)). It reproduces the Emerson et al. table that " + EPA_1984 + " reprints", CHECKED)
               + " Fresh water only: in sea water the share is lower.")
    t2 = table(f"Free ammonia from a test-kit reading at {KIT_T} °C ({KIT_T * 9 / 5 + 32:.0f} °F)",
               ["pH"] + [f"Kit reads {r:g} ppm" for r in READINGS],
               [[f"{ph:.1f}"] + [f"{sig(r * nh3_fraction(ph, KIT_T), 2)} ppm" for r in READINGS] for ph in KIT_PHS],
               "The kit's number is total ammonia (NH₃ + NH₄⁺); each cell is the part of it that is free NH₃, in the same unit.")
    ph, t, total = 8.2, 26, 1.0
    p = pka(t)
    fr = nh3_fraction(ph, t)
    ex = guides.example(f"1 ppm on the kit, pH {ph}, {t} °C", [
        f"pKa at {t} °C: 0.09018 + 2729.92 ÷ (273.2 + {t}) = {p:.3f}.",
        f"Share as NH₃: 1 ÷ (1 + 10^({p:.3f} − {ph})) = {fr:.4f}, or {sig(100 * fr)} %.",
        f"Free ammonia: 1 ppm × {fr:.4f} = {sig(total * fr, 2)} ppm NH₃; the other {sig(total * (1 - fr))} ppm is ammonium.",
        f"The same reading at pH 7.0 is only {sig(total * nh3_fraction(7.0, t), 2)} ppm NH₃, "
        f"{nh3_fraction(ph, t) / nh3_fraction(7.0, t):.0f} times less.",
    ], f"Result: about {sig(total * fr, 2)} ppm of free ammonia. Any ammonia reading in an established tank is a reason to act.")
    answer = (f"free (un-ionized) ammonia = the kit reading × the NH₃ share for your pH and temperature. At 25 °C the share is "
              f"{sig(100 * nh3_fraction(7.0, 25))} % at pH 7.0, {sig(100 * nh3_fraction(8.0, 25))} % at pH 8.0 and "
              f"{sig(100 * nh3_fraction(8.4, 25))} % at pH 8.4, so the same 1 ppm reading is about ten times more toxic in a "
              "hard-water tank at pH 8 than in a soft one at pH 7.")
    form = (inp("nh3-total", "Total ammonia on the kit", "(ppm = mg/L)", "1") + inp("nh3-ph", "pH", "", "8.0")
            + seg("nh3-unit", "Temperature unit", [("c", "°C"), ("f", "°F")])
            + '<div id="nh3-temp-row"><label for="nh3-temp">Water temperature <small id="nh3-temp-unit">(°C)</small></label>'
              '<input id="nh3-temp" inputmode="decimal" value="25"></div>')
    result = rows("nh3-free", "Free ammonia (NH₃)", [("nh3-pct", "Share of total as NH₃"), ("nh3-nh4", "Ammonium (NH₄⁺)"),
                                                     ("nh3-pka", "pKa at this temperature"), ("nh3-other", "The same reading 0.2 pH lower · higher")]) + \
        ('<div id="nh3-note" class="verdict"></div><p class="note">Fresh water. Test pH and temperature at the same time as ammonia. '
         'No safe level is given: it depends on the fish and how long they are exposed.</p>')
    c.page(
        NH3_PAGE, "Ammonia Toxicity Chart: Free NH₃ by pH and Temperature (Aquarium) | Free",
        "Free ammonia chart and calculator for aquariums and ponds: how much of your test kit's total ammonia is toxic NH₃ at your pH and temperature (Emerson 1975, US EPA equation).",
        "Aquarium", "Free aquarium tool", "Ammonia toxicity chart",
        "How much of the ammonia your test kit reads is the toxic un-ionized form (NH₃), from your pH and water temperature, with the chart behind it.",
        answer, [t1, t2, ex], [
            ("What is the difference between ammonia and ammonium?",
             "In water, ammonia exists as un-ionized ammonia (NH₃), which passes through fish gills and is the toxic part, and as the ammonium ion "
             "(NH₄⁺), which is far less toxic. The balance between them depends on pH and temperature. Most aquarium test kits measure both together, "
             "as total ammonia."),
            ("How do I work out free ammonia from my test kit?",
             "Multiply the kit's reading by the NH₃ percentage for your pH and temperature, divided by 100. 1 ppm at pH 8.0 and 25 °C is "
             f"1 × {sig(100 * nh3_fraction(8.0, 25))} ÷ 100 = {sig(nh3_fraction(8.0, 25), 2)} ppm NH₃. The calculator above does it for any reading."),
            ("Why does pH matter so much?",
             f"Each 1.0 pH unit raises the NH₃ share about ten times, and even 0.2 pH changes it by more than half again: at 25 °C it is "
             f"{sig(100 * nh3_fraction(7.8, 25))} % at pH 7.8 and {sig(100 * nh3_fraction(8.0, 25))} % at pH 8.0. "
             "So measure pH with care and at the same time as ammonia."),
            ("Is ammonia safer in my soft-water tank?",
             "Less of it is in the toxic form at low pH, so the same reading does less harm: at pH 6.6 and 26 °C only "
             f"{sig(100 * nh3_fraction(6.6, 26))} % is NH₃. But a water change or a pH rise turns ammonium back into NH₃ at once, so "
             "a reading in an established tank still needs fixing."),
            ("What level of free ammonia is safe?",
             "This page gives no safe level, on purpose. Tolerance varies with species, size and exposure time, and published limits "
             "such as US EPA's water quality criteria are written for wild rivers and lakes, not for aquarium fish. In a cycled tank the "
             "target is zero total ammonia."),
            ("Does it work for saltwater or reef tanks?",
             "No. The equation is for fresh water. In sea water the NH₃ share at the same pH and temperature is lower, so this chart overstates it "
             "for a marine tank; use a seawater table for those."),
            ("My kit reads ammonia-nitrogen (NH₃-N). What do I do?",
             "The same percentages apply. To express the result as NH₃ rather than as nitrogen, multiply by 17.03 ÷ 14.007 = 1.216."),
        ], "t-water", ("tanklog", "ammonia", TANK_PITCH), "nh3", form, result, "Ammonia charts and worked example",
        extra=dataset_note("aquarium-ammonia-fraction", "every 0.1 pH from 6.0 to 9.0 at every degree from 0 to 30 °C (961 values)")
        + c.related("More aquarium tools", [(SALT_PAGE, "Salinity to specific gravity")]) + SCRIPT,
        extra_ld=[dataset_ld("aquarium-ammonia-fraction", NH3_LD)], checked=CHECKED)


# ---------- salinity ----------

MILLERO = '<a href="https://doi.org/10.1016/0198-0149(81)90122-9">Millero and Poisson (1981), Deep-Sea Research 28A: 625–629</a>'
UNESCO44 = ('<a href="https://repository.oceanbestpractices.org/handle/11329/109">Fofonoff and Millard (1983), '
            'Unesco Technical Papers in Marine Science 44</a>')
SAL_ROWS = [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37]
SG_ROWS = [1.018, 1.019, 1.020, 1.021, 1.022, 1.023, 1.024, 1.025, 1.026, 1.027, 1.028]


def build_salt():
    t25, t20, t60 = (SCALES[k][0] for k in ("s25", "s20", "s60f"))
    t1 = table("Salinity to specific gravity on each scale",
               ["Salinity, ppt", "SG 25/25 °C (77 °F)", "SG 20/20 °C (68 °F)", "SG 60/60 °F", "Density at 25 °C", "Dissolved salts"],
               [[f"{s}", f"{sg(s, t25):.4f}", f"{sg(s, t20):.4f}", f"{sg(s, t60):.4f}", f"{density(s, 25):.1f} kg/m³",
                 f"{salt_g_per_l(s):.1f} g/L"] for s in SAL_ROWS],
               src(f"computed with the one-atmosphere international equation of state of seawater, EOS-80 ({MILLERO}; {UNESCO44}). "
                   "SG t/t = density of the water at t ÷ density of pure water at t", CHECKED))
    t2 = table("Specific gravity to salinity", ["Refractometer or hydrometer reads", "Salinity if it is a 25/25 °C (77 °F) scale",
                                                "If 20/20 °C", "If 60/60 °F"],
               [[f"{v:.3f}", f"{salinity_from_sg(v, t25):.1f} ppt", f"{salinity_from_sg(v, t20):.1f} ppt", f"{salinity_from_sg(v, t60):.1f} ppt"]
                for v in SG_ROWS],
               "The same reading means more salt on a 25 °C scale than on a 60 °F one. Most hobby refractometers are 25/25 °C; check the manual.")
    s = 35
    ex = guides.example("natural seawater, 35 ppt", [
        f"Density at 25 °C from EOS-80: {density(s, 25):.2f} kg/m³; pure water at 25 °C: {pure_water(25):.2f} kg/m³.",
        f"Specific gravity 25/25 °C: {density(s, 25):.2f} ÷ {pure_water(25):.2f} = {sg(s, t25):.4f}.",
        f"On a 60/60 °F hydrometer scale the same water is {sg(s, t60):.4f}; on 20/20 °C it is {sg(s, t20):.4f}.",
        f"Dissolved salts: 35 g/kg × {density(s, 25) / 1000:.4f} kg/L = {salt_g_per_l(s):.2f} g per litre, "
        f"{salt_g_per_l(s) * 3.785411784:.0f} g per US gallon.",
    ], f"Result: 35 ppt reads {sg(s, t25):.4f} on a 77 °F refractometer. A reading of 1.025 is {salinity_from_sg(1.025):.1f} ppt.")
    answer = (f"35 ppt (natural seawater) is SG {sg(35, t25):.4f} on the 25/25 °C (77 °F) scale of hobby refractometers, "
              f"{sg(35, t60):.4f} on the 60/60 °F hydrometer scale. A reading of 1.025 at 77 °F is {salinity_from_sg(1.025):.1f} ppt "
              f"and 1.026 is {salinity_from_sg(1.026):.1f} ppt. Values from the UNESCO seawater equation of state, EOS-80.")
    opts = "".join(f'<option value="{k}">{label}</option>' for k, (_t, label) in SCALES.items())
    form = (seg("sal-mode", "Convert", [("ppt", "Salinity → SG"), ("sg", "SG → salinity")])
            + '<div id="sal-val-row"><label for="sal-val">Value <small id="sal-val-unit">(ppt)</small></label><input id="sal-val" inputmode="decimal" value="35"></div>'
            + f'<div><label for="sal-scale">Specific gravity scale</label><select id="sal-scale">{opts}</select></div>')
    result = rows("sal-main", "Result", [("sal-25", "SG 25/25 °C (77 °F)"), ("sal-20", "SG 20/20 °C (68 °F)"), ("sal-60", "SG 60/60 °F"),
                                         ("sal-rho", "Density at 25 °C"), ("sal-salt", "Dissolved salts")]) + \
        ('<div id="sal-note" class="verdict"></div><p class="note">Natural seawater composition. Salt mixes also hold water and differ '
         'by brand: follow the package and confirm with a calibrated refractometer.</p>')
    c.page(
        SALT_PAGE, "Salinity to Specific Gravity Converter (ppt ↔ SG) with Chart | Free",
        "Convert aquarium salinity in ppt to specific gravity and back on the 25/25 °C, 20/20 °C and 60/60 °F scales, with a chart, from the UNESCO EOS-80 equation of state.",
        "Aquarium", "Free aquarium tool", "Salinity to specific gravity",
        "Salinity in ppt to specific gravity and back, on the reference scale of your refractometer or hydrometer, with the density and the salt per litre.",
        answer, [t1, t2, ex], [
            ("What specific gravity is 35 ppt?",
             f"{sg(35, t25):.4f} on a 25/25 °C (77 °F) scale, the one most hobby refractometers use; {sg(35, t20):.4f} on 20/20 °C "
             f"and {sg(35, t60):.4f} on 60/60 °F."),
            ("What salinity is SG 1.025?",
             f"{salinity_from_sg(1.025):.1f} ppt if your instrument reads on the 25/25 °C scale, {salinity_from_sg(1.025, t60):.1f} ppt "
             "on a 60/60 °F scale. Find the scale in the refractometer's manual."),
            ("Why are there different specific gravity scales?",
             "Specific gravity compares the water with pure water at the same temperature, and both expand as they warm, by different amounts. "
             "So the number depends on the reference temperature: 60 °F for many older hydrometers, 77 °F (25 °C) for most refractometers sold for reef tanks."),
            ("Is ppt the same as PSU?",
             "Practically, yes. Oceanographers measure practical salinity (PSU, no unit) by conductivity; for natural seawater it equals grams of salts "
             "per kilogram of water, parts per thousand, to within about half a percent."),
            ("How much salt do I need per gallon?",
             f"Natural seawater at 35 ppt holds about {salt_g_per_l(35):.1f} g of dissolved salts per litre, {salt_g_per_l(35) * 3.785411784:.0f} g per US "
             "gallon. Commercial salt mixes need more, because they hold water, and differ by brand: start with the package's dose and check "
             "with a refractometer."),
            ("Can I use this to correct a hydrometer read at tank temperature?",
             "No. A hydrometer's own glass or plastic expands with temperature too, so the correction depends on the instrument. Use the maker's "
             "correction chart, or a refractometer with automatic temperature compensation."),
        ], "t-water", ("tanklog", "salinity", TANK_PITCH), "salt", form, result, "Salinity charts and worked example",
        extra=dataset_note("seawater-salinity-specific-gravity", "every 0.5 ppt from 0 to 45 on all three scales (91 rows)")
        + c.related("More aquarium tools", [(NH3_PAGE, "Ammonia toxicity chart")]) + SCRIPT,
        extra_ld=[dataset_ld("seawater-salinity-specific-gravity", SEAWATER_LD)], checked=CHECKED)


def build():
    build_nh3()
    build_salt()


# Rows for the methodology page (trust.METHODS): (calculator, page, tables and formulas, assumptions, limits).
METHODS = [
    ("Ammonia toxicity chart", NH3_PAGE,
     ["pKa = 0.09018 + 2729.92 &divide; (273.2 + t) and NH<sub>3</sub> share = 1 &divide; (1 + 10<sup>pKa &minus; pH</sup>), "
      "Emerson et al. (1975) as printed by US EPA (1999 Update, EPA-822-R-99-014; 2013 freshwater criteria, EPA-822-R-13-001).",
      "Checked against 38 cells of the Emerson et al. table reprinted in EPA's 1984 ammonia criteria (within the table's rounding) "
      "and the TankLog app's unit tests (read 26 November 2026). TankLog writes the temperature as t + 273.15 K; the difference is under 0.5 % of the result."],
     ["Fresh water of low ionic strength.", "The kit reading is total ammonia (NH<sub>3</sub> + NH<sub>4</sub><sup>+</sup>)."],
     ["Not for sea water: the NH<sub>3</sub> share there is lower.", "No toxicity threshold is given.",
      "A 0.1 pH error moves the result by about 25 %."]),
    ("Salinity to specific gravity", SALT_PAGE,
     ["Density from the one-atmosphere international equation of state of seawater, EOS-80 (Millero and Poisson 1981; UNESCO 1981).",
      "Specific gravity t/t = &rho;(S, t) &divide; &rho;(0, t), for 25/25 &deg;C, 20/20 &deg;C and 60/60 &deg;F.",
      "Checked against the UNESCO check values (for example 1023.34306 kg/m&sup3; at S = 35, 25 &deg;C) and the TankLog app's unit tests."],
     ["Natural seawater composition at one atmosphere.", "The instrument reads on the scale you choose."],
     ["Not a temperature correction for a hydrometer read at tank temperature.",
      "Dissolved salts are not the weight of a commercial mix, which also holds water."]),
]

# ---------- the open datasets' schema.org blocks ----------
# Copied from experimental/open-data/<dataset>/schema-org-dataset.jsonld (built 26 November 2026) without sameAs and
# distribution: neither dataset is on Zenodo yet. dataset_ld() adds the DOI and the downloads once opendata.DOI has them.

NH3_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/aquarium/ammonia-toxicity-chart.html#dataset",
    "name": "Un-ionized ammonia (NH3) as a percentage of total ammonia by pH (6.0–9.0) and temperature (0–30 °C), Emerson et al. (1975) equation as used by US EPA",
    "alternateName": "Un-ionized ammonia (NH3) % by pH and temperature",
    "description": "The share of total ammonia (NH3 + NH4+) present as toxic un-ionized ammonia (NH3) in fresh water, for every 0.1 pH unit from 6.0 to 9.0 and every whole degree from 0 to 30 °C (961 rows), with the temperature in °F and the pKa of the ammonium ion. Computed with the equation of Emerson, Russo, Lund and Thurston (1975), pKa = 0.09018 + 2729.92 / (273.2 + t) (t in °C) and NH3 % = 100 / (1 + 10^(pKa − pH)), written exactly as US EPA prints it in its ammonia criteria documents (1999 Update, EPA-822-R-99-014; 2013 freshwater criteria, EPA-822-R-13-001). Every value is computed; it reproduces all 38 cells checked against the Emerson et al. table reproduced in EPA's 1984 ammonia criteria document. Aquarium and pond test kits report total ammonia: multiply a reading by the percentage here to get free NH3. The table behind the ammonia chart on zhukovskyi.space and the TankLog aquarium app. Fresh water only (zero salinity); no toxicity thresholds are included.",
    "url": "https://zhukovskyi.space/calculators/aquarium/ammonia-toxicity-chart.html",
    "version": "1.0.0",
    "datePublished": "2026-11-26",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "ammonia",
        "un-ionized ammonia",
        "free ammonia",
        "NH3",
        "ammonium",
        "pKa",
        "aquarium",
        "aquaculture",
        "water quality",
        "Emerson 1975"
    ],
    "citation": "Zhukovskyi, A. (2026). Un-ionized ammonia (NH3) as a percentage of total ammonia by pH (6.0–9.0) and temperature (0–30 °C), Emerson et al. (1975) equation as used by US EPA (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/aquarium/ammonia-toxicity-chart.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "temp_c",
            "description": "Water temperature, 0 to 30 in steps of 1.",
            "unitText": "°C"
        },
        {
            "@type": "PropertyValue",
            "name": "temp_f",
            "description": "The same temperature in Fahrenheit: temp_c × 9/5 + 32.",
            "unitText": "°F"
        },
        {
            "@type": "PropertyValue",
            "name": "ph",
            "description": "pH, 6.0 to 9.0 in steps of 0.1."
        },
        {
            "@type": "PropertyValue",
            "name": "pka",
            "description": "pKa of NH4+ at this temperature: 0.09018 + 2729.92 / (273.2 + temp_c) (Emerson et al. 1975, as printed by US EPA)."
        },
        {
            "@type": "PropertyValue",
            "name": "nh3_pct",
            "description": "Un-ionized ammonia as a percentage of total ammonia: 100 / (1 + 10^(pka − ph)), 4 significant figures.",
            "unitText": "%"
        }
    ],
    "isBasedOn": [
        "https://doi.org/10.1139/f75-274",
        "https://19january2021snapshot.epa.gov/sites/static/files/2015-08/documents/aquatic-life-ambient-water-quality-criteria-for-ammonia-freshwater-2013.pdf",
        "https://www.waterboards.ca.gov/waterrights/water_issues/programs/bay_delta/docs/cmnt081712/srcsd/usepa99update.pdf",
        "https://19january2021snapshot.epa.gov/sites/static/files/2019-02/documents/ambient-wqc-ammonia-1984.pdf"
    ]
}


SEAWATER_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/aquarium/salinity-to-specific-gravity.html#dataset",
    "name": "Seawater salinity (0–45 ppt) to density and specific gravity at 25/25 °C, 20/20 °C and 60/60 °F, from the UNESCO one-atmosphere equation of state EOS-80",
    "alternateName": "Seawater salinity to specific gravity (EOS-80)",
    "description": "Density and specific gravity of seawater for every 0.5 ppt of salinity from 0 to 45 (91 rows), computed with the international one-atmosphere equation of state of seawater (EOS-80; Millero and Poisson 1981, UNESCO 1981): the density at 25 °C, the specific gravity on the three usual reference scales (25/25 °C, the scale of hobby refractometers; 20/20 °C; 60/60 °F, the classic hydrometer scale), and the grams of dissolved salts per litre at 25 °C. Specific gravity t/t is the density of the sample divided by that of pure water at the same temperature. Every value is computed; the equation reproduces the UNESCO check values (for example 1023.34306 kg/m³ at S = 35, 25 °C). Natural seawater of 35 ppt reads 1.0264 at 25/25 °C. The table behind the salinity and specific gravity converter on zhukovskyi.space and the TankLog aquarium app. No target ranges are included.",
    "url": "https://zhukovskyi.space/calculators/aquarium/salinity-to-specific-gravity.html",
    "version": "1.0.0",
    "datePublished": "2026-11-26",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "seawater",
        "salinity",
        "specific gravity",
        "density",
        "EOS-80",
        "UNESCO",
        "refractometer",
        "hydrometer",
        "reef aquarium",
        "marine aquarium"
    ],
    "citation": "Zhukovskyi, A. (2026). Seawater salinity (0–45 ppt) to density and specific gravity at 25/25 °C, 20/20 °C and 60/60 °F, from the UNESCO one-atmosphere equation of state EOS-80 (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/aquarium/salinity-to-specific-gravity.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "salinity_ppt",
            "description": "Practical salinity, 0 to 45 in steps of 0.5; numerically the same as parts per thousand by mass.",
            "unitText": "ppt (g/kg)"
        },
        {
            "@type": "PropertyValue",
            "name": "density_25c_kg_m3",
            "description": "Density at 25 °C and one atmosphere, EOS-80 one-atmosphere equation.",
            "unitText": "kg/m³"
        },
        {
            "@type": "PropertyValue",
            "name": "sg_25_25",
            "description": "Specific gravity 25/25 °C (77/77 °F): density at 25 °C ÷ density of pure water at 25 °C. The scale of hobby refractometers."
        },
        {
            "@type": "PropertyValue",
            "name": "sg_20_20",
            "description": "Specific gravity 20/20 °C (68/68 °F)."
        },
        {
            "@type": "PropertyValue",
            "name": "sg_60_60f",
            "description": "Specific gravity 60/60 °F (15.556/15.556 °C), the classic hydrometer scale."
        },
        {
            "@type": "PropertyValue",
            "name": "salt_g_per_l",
            "description": "Dissolved salts per litre of this water at 25 °C: salinity_ppt × density_25c_kg_m3 / 1000.",
            "unitText": "g/L"
        }
    ],
    "isBasedOn": [
        "https://doi.org/10.1016/0198-0149(81)90122-9",
        "https://repository.oceanbestpractices.org/handle/11329/109"
    ]
}

