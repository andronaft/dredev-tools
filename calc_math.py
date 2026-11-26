"""Pure maths for the hobby and trade calculator pages (pages_hobby.py, pages_trades.py).

Every function mirrors the Dart engine of the matching app, named in the comment above it, so the static tables
on the pages, the live calculators (assets/calc-more.js) and the apps agree. tests/test_calc_math.py pins control
values taken from the apps' own unit tests; keep all three in step when an app changes.
"""
import math
from datetime import date, timedelta


def ceil_count(v):
    """Rounding up that ignores floating-point dust (slabcalc-app calc.dart ceilCount, roofcalc-app packs)."""
    return math.ceil(v - 1e-9) if math.isfinite(v) and v > 0 else 0


# ---------- Ferment: ferment-app/lib/calc/gravity.dart, sugar.dart ----------

L_PER_GAL = 3.785411784
KG_PER_LB = 0.45359237
HONEY_PPG = 35.0  # gravity points one pound adds to one US gallon (Sugar.honey)


def degrees_to_sg(deg):
    """Brix or Plato to SG (Gravity.degreesToSg)."""
    return 1 + deg / (258.6 - (deg / 258.2) * 227.1)


def sg_to_degrees(sg):
    """SG to Plato, also used for Brix (Gravity.sgToDegrees)."""
    return -616.868 + 1111.14 * sg - 630.272 * sg * sg + 135.997 * sg ** 3


def abv_standard(og, fg):
    return (og - fg) * 131.25


def abv_alternate(og, fg):
    """Michael Hall's formula (Gravity.abvAlternate)."""
    return (76.08 * (og - fg) / (1.775 - og)) * (fg / 0.794)


def attenuation(og, fg):
    return 0.0 if og <= 1 else (og - fg) / (og - 1) * 100


def honey_points(lb, gallons, ppg=HONEY_PPG):
    """Gravity points [lb] of honey add to a batch of [gallons], its final volume (SugarMath.pointsAdded)."""
    return 0.0 if gallons <= 0 else ppg * lb / gallons


def honey_lb_for(points, gallons, ppg=HONEY_PPG):
    """Pounds of honey that raise [gallons] by [points] (SugarMath.massForPoints)."""
    return 0.0 if points <= 0 else points * gallons / ppg


# ---------- GrowLab: growlab-app/lib/feature/calc.dart EcScale ----------

EC_SCALES = {"500": 500.0, "640": 640.0, "700": 700.0}  # ppm shown per 1 mS/cm; the app ships 500 and 700


def ec_to_ppm(ec_ms, scale):
    return ec_ms * EC_SCALES[scale]


def ppm_to_ec(ppm, scale):
    return ppm / EC_SCALES[scale]


# ---------- WickCalc: wickcalc-app/lib/feature/calc.dart ----------

WAX_FACTOR = 0.86  # defaultWaxFactor: wax weighs about 86 % of the same volume of water
G_PER_OZ = 28.349523125
G_PER_FLOZ_WATER = 29.5735  # 1 US fl oz of water weighs 29.57 g


def fill_from_water(water, factor=WAX_FACTOR):
    """Wax + fragrance a jar holds, from the weight of water to the fill line (fillFromWater)."""
    return max(0.0, water) * factor


def candle_split(fill, load_pct, of_wax=True):
    """(wax, fragrance) in one candle of [fill] weight (batch(): load as % of the wax, or of the total)."""
    f = min(max(load_pct, 0), 100) / 100
    if of_wax:
        wax = fill / (1 + f)
        return wax, fill - wax
    fo = fill * f
    return fill - fo, fo


def fragrance_for_wax(wax, load_pct):
    """Fragrance for a known wax weight, load as % of the wax (loadPct inverted)."""
    return wax * load_pct / 100


def convert_load(pct, from_wax=True):
    """The same load against the other basis: 10 % of wax = 9.09 % of the candle (convertLoad)."""
    f = pct / 100
    return 100 * (f / (1 + f) if from_wax else f / (1 - f))


# ---------- RoofCalc: roofcalc-app/lib/feature/roof.dart ----------

BUNDLES_PER_SQUARE = 3
BUNDLE_SQFT = 100 / 3  # 3 bundles per square (GAF Timberline HDZ data sheet)


def pitch_factor(rise):
    return math.sqrt(144 + rise * rise) / 12


def hip_factor(rise):
    return math.sqrt(288 + rise * rise) / 12


def pitch_degrees(rise):
    return math.degrees(math.atan(rise / 12))


def roof(plan_sqft, rise, waste=0.10):
    """(sloped area, squares, bundles with waste): plan area × slope factor; packs(area × (1 + waste), bundleSqft)."""
    area = plan_sqft * pitch_factor(rise)
    return area, area / 100, ceil_count(area * (1 + max(0, waste)) / BUNDLE_SQFT)


# ---------- Dial In: dialin-coffee-app/lib/feature/models.dart, dial_in.dart ----------

def brew_ratio(dose, out):
    return 0.0 if dose <= 0 else out / dose


def shot_style(ratio):
    """Ristretto up to 1:1.5, normale to 1:2.5, lungo beyond (shotStyle)."""
    return "ristretto" if ratio <= 1.5 else "normale" if ratio <= 2.5 else "lungo"


# ---------- RowKeeper: rowcounter-app/lib/feature/yarn_math.dart ----------

M_PER_YD = 0.9144


def skeins_needed(length_needed, skein_length, extra_pct=0):
    """(length with the margin, whole skeins to buy) (skeinsNeeded)."""
    needed = length_needed * (1 + extra_pct / 100)
    exact = 0 if skein_length <= 0 else needed / skein_length
    return needed, (math.ceil(exact - 1e-9) if exact > 0 else 0)


def swatch_yarn(swatch_w, swatch_h, swatch_len, width, length):
    """Yarn for a width × length piece in the stitch of a swatch that took [swatch_len]: plain proportion by area."""
    a = swatch_w * swatch_h
    return 0.0 if a <= 0 else swatch_len * width * length / a


def length_from_weight(label_weight, label_length, weight):
    """Length of yarn in [weight], from the ball band (lengthLeft)."""
    return 0.0 if label_weight <= 0 else weight * label_length / label_weight


def gauge_count(per_4in, inches):
    """Stitches (or rows) for [inches] at a gauge counted over 4 in, to the nearest whole stitch."""
    return math.floor(per_4in / 4 * inches + 0.5)


# ---------- ShiftWise: shift-calendar-app/lib/feature/patterns.dart ----------

def rep(code, n):
    return [code] * n


_PITMAN = rep("D", 2) + rep("O", 2) + rep("D", 3) + rep("O", 2) + rep("D", 2) + rep("O", 3)
# D/N = 12-hour day and night, M/A/X = 8-hour morning, afternoon and night, T = 10-hour day, O = off.
PATTERNS = {
    "4on4off": rep("D", 4) + rep("O", 4),
    "pitman": _PITMAN,
    "dupont": rep("N", 4) + rep("O", 3) + rep("D", 3) + rep("O", 1) + rep("N", 3) + rep("O", 3) + rep("D", 4) + rep("O", 7),
    "3on3off": rep("D", 3) + rep("O", 3),
    "4on3off": rep("T", 4) + rep("O", 3),
    "continental": (rep("M", 2) + rep("A", 2) + rep("X", 3) + rep("O", 2) + rep("M", 2) + rep("A", 3) + rep("X", 2) + rep("O", 2)
                    + rep("M", 3) + rep("A", 2) + rep("X", 2) + rep("O", 3)),
}
SHIFT_HOURS = {"D": 12, "N": 12, "M": 8, "A": 8, "X": 8, "T": 10, "O": 0}


def cycle_stats(cycle):
    """(cycle days, work days, off days, hours per cycle, average hours per week, average days off per year)."""
    n = len(cycle)
    work = sum(1 for c in cycle if c != "O")
    hours = sum(SHIFT_HOURS[c] for c in cycle)
    return n, work, n - work, hours, hours / n * 7, (n - work) / n * 365.25


def cycle_day(start, day, n):
    """0-based cycle day of [day] for a rota whose cycle day 1 is [start] (Rota.cycleDay)."""
    return (day - start).days % n


def year_stats(cycle, year, start):
    """Counts for one calendar year: (shifts, days off, hours, full weekends off)."""
    n = len(cycle)
    d = date(year, 1, 1)
    shifts = off = hours = weekends = 0
    while d.year == year:
        c = cycle[cycle_day(start, d, n)]
        if c == "O":
            off += 1
            if d.weekday() == 5:
                nxt = d + timedelta(days=1)
                if nxt.year == year and cycle[cycle_day(start, nxt, n)] == "O":
                    weekends += 1
        else:
            shifts += 1
            hours += SHIFT_HOURS[c]
        d += timedelta(days=1)
    return shifts, off, hours, weekends


# ---------- Electrician Calc: Calculator_for_electrical/lib/feature/engine/electrical.dart ----------
# Only the arithmetic. The tables (NEC Chapter 9 Tables 1, 4 and 5, Tables 314.16(B)(1) and 250.122) are read from
# the app's nec_tables.dart by pages_electrical.py and passed in.

def fill_limit(n, limits):
    """Chapter 9 Table 1 as necFillLimit(): limits = (one conductor, two, more than two)."""
    return limits[0] if n == 1 else limits[1] if n == 2 else limits[2]


def conduit_max(cable_area, raceway_area, limits):
    """Most identical conductors that fit (conduitFill().maxConductors). It counts up while the limit for that
    many conductors holds, so it never rounds up."""
    n = 0
    while n <= 999 and fill_limit(n + 1, limits) * raceway_area >= (n + 1) * cable_area:
        n += 1
    return n


def conduit_fill(areas, raceway_area, limits):
    """(fill %, limit %, fits) for conductors of the given areas in one raceway (conduitFill() on their total)."""
    pct, limit = sum(areas) / raceway_area * 100, fill_limit(len(areas), limits) * 100
    return pct, limit, pct <= limit + 1e-9


def box_fill(conductors, clamps, fittings, devices, grounds, per_conductor, box_volume=0.0):
    """NEC 314.16(B) as boxFill(): (volume allowances, in³ required, fits, spare conductors). One allowance per
    conductor, one for any internal clamps, one per fixture stud or hickey, two per device, one for up to four
    grounds and a quarter for each one more."""
    ground = 0.0 if grounds <= 0 else 1 + (grounds - 4) * 0.25 if grounds > 4 else 1.0
    n = conductors + (1 if clamps else 0) + fittings + 2 * devices + ground
    need = n * per_conductor
    return n, need, need <= box_volume + 1e-9, math.floor((box_volume - need) / per_conductor + 1e-9)


def egc_for(ocpd, table, copper=True):
    """Table 250.122 ground for a breaker (necEgcFor): table = [(largest breaker, copper, aluminum)]."""
    return next(((cu if copper else al) for top, cu, al in table if ocpd <= top), None)


def egc_upsized(ocpd, table, cmil, sizes, minimum, installed, copper=True):
    """250.122(B) as necEgcUpsized(): the ground grows with the circular mils of the upsized conductors, never
    beyond them. cmil = {size: circular mils}, sizes = the app's necSizes in order."""
    base = egc_for(ocpd, table, copper)
    if base is None or minimum == installed:
        return base
    need = cmil[base] * cmil[installed] / cmil[minimum]
    size = next((s for s in sizes if cmil[s] >= need - 1e-6), installed)
    return installed if cmil[size] > cmil[installed] else size


# Battery & UPS Runtime: batteryRuntime() and batteryCapacityFor() in electrical.dart. The bank, the charge time and the
# battery count are the web page's own (electrical/uk/battery-runtime.html); the app has no charge time.

def battery_bank(volts, ah, series=1, parallel=1):
    """(bank volts, bank Ah, nominal Wh): series adds voltage, parallel adds Ah."""
    v, c = volts * series, ah * parallel
    return v, c, v * c


def battery_runtime(volts, ah, count, load_w, dod=0.8, eff=0.9):
    """Hours: U × Ah × n × DoD × η / P (batteryRuntime). n counts every battery, in series or in parallel."""
    return volts * ah * count * dod * eff / load_w if load_w > 0 else 0.0


def battery_capacity_for(volts, load_w, hours, dod=0.8, eff=0.9):
    """Ah at [volts] for [hours]: P × t / (U × DoD × η) (batteryCapacityFor)."""
    return load_w * hours / (volts * dod * eff)


def charge_hours(ah, amps, charge_eff):
    """Hours to put back [ah] at a steady [amps] with the coulombic efficiency [charge_eff]. The bulk stage only:
    a lead-acid battery then needs a slower absorption stage on top."""
    return ah / (amps * charge_eff) if amps > 0 and charge_eff > 0 else 0.0


def batteries_for(need_ah, ah_one, series=1):
    """(strings in parallel, batteries in all) so the bank holds at least [need_ah] at its voltage."""
    strings = ceil_count(need_ah / ah_one) if ah_one > 0 else 0
    return strings, strings * series


# ---------- CoatCalc: coatcalc-app/lib/feature/calc.dart ----------

SQFT_PER_GAL_1MIL = 1604.0


def coat_gallons(sqft, mils, solids, waste=0.0):
    return sqft * mils / (SQFT_PER_GAL_1MIL * solids) * (1 + waste)


def coat_rate(mils, solids):
    return SQFT_PER_GAL_1MIL * solids / mils


def kits(gallons, kit_gallons):
    return ceil_count(gallons / kit_gallons) if kit_gallons > 0 else 0


# ---------- SlabCalc: slabcalc-app/lib/feature/calc.dart ----------

FT3_PER_YD3 = 27.0
BAGS = [("80 lb", 0.60), ("60 lb", 0.45), ("40 lb", 0.30)]  # Quikrete Concrete Mix 1101 yields, ft³
REBAR = {"#3": (0.375, 0.376), "#4": (0.500, 0.668), "#5": (0.625, 1.043)}  # diameter in, lb/ft (ASTM A615)


def slab_ft3(length_ft, width_ft, thick_in, extra_pct=0.0):
    return length_ft * width_ft * thick_in / 12 * (1 + extra_pct / 100)


def bags_for(ft3, yield_ft3):
    return ceil_count(ft3 / yield_ft3)


def order_rounded(ft3):
    """Ready-mix order in yd³, rounded up to the next ¼ yard (orderRounded)."""
    return ceil_count(ft3 / FT3_PER_YD3 * 4) / 4


def pieces_for(runs, run, stock, lap=0.0):
    """(stock pieces, laps per run) for [runs] bars of [run] ft cut from [stock] ft sticks (piecesFor)."""
    if runs <= 0 or run <= 0 or stock <= 0:
        return 0, 0
    if run <= stock + 1e-9:
        return ceil_count(runs / math.floor(stock / run + 1e-9)), 0
    if stock <= lap:
        return 0, 0
    per_run = ceil_count((run - lap) / (stock - lap))
    last = run - (per_run - 1) * (stock - lap)
    last_per_stock = math.floor(stock / last + 1e-9)
    return runs * (per_run - 1) + ceil_count(runs / last_per_stock), per_run - 1


def rebar_grid(length, width, spacing_in=16.0, edge_in=3.0, stock=20.0, bar="#4", lap_diameters=40.0):
    """A grid both ways (RebarGrid.calc with the app's defaults): dict of bars, pieces, total feet and weight."""
    dia_in, lb_ft = REBAR[bar]
    spacing, edge, lap = spacing_in / 12, edge_in / 12, lap_diameters * dia_in / 12
    long_side, short_side = max(length, width), min(length, width)
    long_bar, short_bar = long_side - 2 * edge, short_side - 2 * edge
    if long_bar <= 0 or short_bar <= 0 or spacing <= 0:
        return None
    bars_long = ceil_count(short_bar / spacing) + 1
    bars_short = ceil_count(long_bar / spacing) + 1
    a, a_laps = pieces_for(bars_long, long_bar, stock, lap)
    b, b_laps = pieces_for(bars_short, short_bar, stock, lap)
    total = bars_long * (long_bar + a_laps * lap) + bars_short * (short_bar + b_laps * lap)
    return {"bars_long": bars_long, "long_bar": long_bar, "bars_short": bars_short, "short_bar": short_bar,
            "pieces": a + b, "total_ft": total, "weight_lb": total * lb_ft}


# ---------- PoolPro: pool-chem-app/lib/feature/chem/products.dart, dosing.dart ----------

MW_CL2, MW_NAOCL, MW_CYA, MW_CACO3 = 70.906, 74.44, 129.07, 100.09
ML_PER_FLOZ = 29.5735


# Specific gravity (60 °F) against weight % NaOCl: OxyChem, Sodium Hypochlorite Handbook, Table 2 "Materials for
# Making 1000 Gallons of Bleach Solution", the rows 5.0–8.0 wt % available chlorine (read 26 November 2026,
# https://www.forceflowscales.com/downloads/chemical-safety/hypochlorite/Hypo_Handbook_Oxy_Chem.pdf).
# Replaces the unsourced fit 1.0174 + 0.01003·%, which was 0.9 % (6 %) and 2.1 % (8.25 %) too light.
BLEACH_SG = [(5.25, 1.075), (5.51, 1.079), (5.78, 1.083), (6.04, 1.088), (6.30, 1.092), (7.35, 1.109), (8.40, 1.126)]


def bleach_sg(pct):
    """Specific gravity of bleach labelled [pct] wt % NaOCl: straight line between the two BLEACH_SG rows around it."""
    for (x0, y0), (x1, y1) in zip(BLEACH_SG, BLEACH_SG[1:]):
        if x0 <= pct <= x1:
            return y0 + (y1 - y0) * (pct - x0) / (x1 - x0)
    raise ValueError(f"{pct} % NaOCl is outside the OxyChem rows used (5.25–8.40 %)")


def bleach_gpl(pct):
    """Grams of available chlorine per litre of bleach labelled % NaOCl by weight (chlorineGramsPerLitre)."""
    return pct * 10 * bleach_sg(pct) * MW_CL2 / MW_NAOCL


# id: (name, kind, strength). Liquids: g of available chlorine per litre; dry: share of available chlorine.
CHLORINE = {
    "liquid10": ("Liquid chlorine 10 %", "liquid", 100.0),
    "liquid125": ("Liquid chlorine 12.5 %", "liquid", 125.0),
    "bleach6": ("Bleach 6 %", "liquid", bleach_gpl(6)),
    "bleach825": ("Bleach 8.25 %", "liquid", bleach_gpl(8.25)),
    "calhypo65": ("Cal-hypo 65 %", "calhypo", 0.65),
    "calhypo73": ("Cal-hypo 73 %", "calhypo", 0.73),
    "dichlor": ("Dichlor 56 %", "dichlor", 0.56),
    "trichlor": ("Trichlor 90 %", "trichlor", 0.90),
}
CYA_PER_FC = {"dichlor": MW_CYA / (2 * MW_CL2), "trichlor": MW_CYA / (3 * MW_CL2)}
CH_PER_FC = {"calhypo": MW_CACO3 / (2 * MW_CL2)}


def chlorine_dose(product, ppm, gallons):
    """(amount, unit): US fl oz of a liquid or oz by weight of a dry product that raise FC by [ppm]."""
    _, kind, strength = CHLORINE[product]
    grams = ppm * gallons * 3.78541 / 1000  # ppm × litres = mg of chlorine
    if kind == "liquid":
        return grams / strength * 1000 / ML_PER_FLOZ, "fl oz"
    return grams / strength / 28.3495, "oz"


def chlorine_side(product, ppm):
    """What a dry product adds besides chlorine: (ppm CYA, ppm calcium hardness)."""
    kind = CHLORINE[product][1]
    return CYA_PER_FC.get(kind, 0) * ppm, CH_PER_FC.get(kind, 0) * ppm
