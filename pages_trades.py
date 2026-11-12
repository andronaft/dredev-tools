"""Trade calculator pages: roofing (RoofCalc), shift patterns (ShiftWise), garage floor coating (CoatCalc),
concrete slabs by size (SlabCalc) and pool chlorine (PoolPro). Formulas are in calc_math.py; presets the apps own
(coating products, garage sizes) are read from their Dart sources at build time.
"""
import re
from datetime import date, timedelta

import calc_math as m
import calcs_common as c
import guides
from calcs_common import n, src, table, trim
from pages_hobby import inp, rows, seg

SLABS = [(10, 10), (10, 12), (10, 20), (12, 12), (12, 16), (12, 20), (12, 24), (14, 20), (16, 16), (16, 20), (16, 24), (18, 20),
         (20, 20), (20, 24), (20, 30), (20, 40), (24, 24), (24, 30), (24, 36), (24, 40), (30, 30), (30, 40), (30, 50), (30, 60),
         (40, 40), (40, 50), (40, 60), (40, 80), (50, 100), (60, 100)]
POOL_SIZES = [5000, 10000, 15000, 20000, 25000, 30000]

HOME_CARDS = [
    ("roofing/roof-pitch-multiplier-chart.html", "Roofing", "Roof pitch multiplier chart", "Slope factors for 1/12 to 12/12, with roof area and squares.", "t-roof"),
    ("roofing/shingle-bundles-calculator.html", "Roofing", "Shingle bundles calculator", "Squares and bundles from the footprint and pitch.", "t-roof"),
    ("concrete/concrete-slab-calculator.html", "Concrete", "Concrete slab calculator", f"Yards, bags and rebar, with {len(SLABS)} slab sizes worked out.", "t-slab"),
    ("coating/garage-floor-epoxy-calculator.html", "Coatings", "Garage floor epoxy calculator", "Gallons and kits for a 1, 2 or 3 car garage by system.", "t-coat"),
    ("pool/how-much-chlorine-to-add.html", "Pool", "How much chlorine to add", "Liquid chlorine, cal-hypo or trichlor for your pool's gallons.", "t-pool"),
    ("shifts/index.html", "Shifts", "Shift pattern calendars", "4 on 4 off, 2-2-3, DuPont and more: calendar, hours and days off.", "t-lid"),
]


def sel(i, label, options, small="", full=False):
    opts = "".join(f'<option value="{v}"{" selected" if d else ""}>{t}</option>' for v, t, d in options)
    sm = f" <small>{small}</small>" if small else ""
    return f'<div{" class=full" if full else ""}><label for="{i}">{label}{sm}</label><select id="{i}">{opts}</select></div>'


# ---------- RoofCalc ----------

ROOF_PITCH = "Measure from the ground, get the squares and every material, and send a PDF quote before you leave the driveway."
OC = ('<a href="https://www.owenscorning.com/roofing/tools/diy-roofing">Owens Corning, roofing basics for homeowners</a>: three bundles make one roofing square')
ROOF_NOTE = '<p class="note">Area of a roof whose planes share one pitch = footprint (with overhangs) × slope factor. Check the bundle wrapper: coverage per bundle differs between products.</p>'


def roof_form(length, width):
    pitches = [(r, f"{r}/12", r == 6) for r in range(1, 13)]
    return (inp("rlen", "Footprint length", "(ft, with overhangs)", str(length)) + inp("rwid", "Footprint width", "(ft, with overhangs)", str(width))
            + sel("rpitch", "Pitch", pitches) + sel("rwaste", "Waste", [(10, "10 % · simple gable", True), (15, "15 % · hip roof", False), (20, "20 % · cut-up roof", False)]))


ROOF_RESULT = rows("r-sq", "Roof size", [("r-area", "Roof area"), ("r-plan", "Footprint"), ("r-factor", "Slope factor"),
                                         ("r-bundles", "Shingles, 3 bundles per square, with waste")]) + '<div id="r-note" class="verdict"></div>'


def build_pitch():
    t1 = table("Roof pitch multiplier chart, 1/12 to 12/12", ["Pitch", "Angle", "Slope factor (area, rafter)", "Hip / valley factor", "Grade"],
               [[f"{r}/12", f"{m.pitch_degrees(r):.1f}°", f"{m.pitch_factor(r):.3f}", f"{m.hip_factor(r):.3f}", f"{r / 12 * 100:.0f} %"] for r in range(1, 13)],
               "Exact geometry: slope factor = √(12² + rise²) ÷ 12, hip and valley factor = √(2 × 12² + rise²) ÷ 12, angle = atan(rise ÷ 12). "
               "The same factors are in the RoofCalc app.")
    foot = [1000, 1500, 2000, 2500, 3000]
    t2 = table("Roof area by footprint and pitch", ["Pitch"] + [f"{n(f)} sq ft footprint" for f in foot],
               [[f"{r}/12"] + [f"{n(f * m.pitch_factor(r))} sq ft" for f in foot] for r in (3, 4, 5, 6, 7, 8, 9, 10, 12)],
               "Footprint is the area under the roof seen from above, overhangs included. Divide by 100 for squares.")
    area, sq, bundles = m.roof(2000, 6)
    ex = guides.example("a 50 × 40 ft footprint at 6/12", [
        "Footprint with overhangs: 50 × 40 = 2,000 sq ft.",
        f"Slope factor for 6/12: √(144 + 36) ÷ 12 = {m.pitch_factor(6):.3f}. Roof area: 2,000 × {m.pitch_factor(6):.3f} = {n(area)} sq ft.",
        f"Squares: {n(area)} ÷ 100 = {sq:.1f}. With 10 % waste at 3 bundles per square: {bundles} bundles.",
        f"A hip on the same roof runs {m.hip_factor(6):.1f} ft for every foot of run, so a hip over a 20 ft run is {20 * m.hip_factor(6):.0f} ft long.",
    ], f"Result: {n(area)} sq ft of roof, {sq:.1f} squares, {bundles} bundles of shingles.")
    answer = (f"multiply the footprint by the slope factor: {m.pitch_factor(4):.3f} for 4/12, {m.pitch_factor(6):.3f} for 6/12, {m.pitch_factor(8):.3f} for 8/12, "
              f"{m.pitch_factor(10):.3f} for 10/12 and {m.pitch_factor(12):.3f} for 12/12. A 2,000 sq ft footprint at 6/12 is {n(area)} sq ft of roof, or {sq:.1f} squares.")
    c.page(
        "roofing/roof-pitch-multiplier-chart.html", "Roof Pitch Multiplier Chart (1/12 to 12/12) and Calculator | Free",
        "Roof pitch multiplier chart for 1/12 to 12/12: slope factor, hip and valley factor, angle and grade, with a calculator for roof area, squares and bundles.",
        "Roofing", "Free roofing tool", "Roof pitch multiplier chart",
        "Slope factors for every pitch from 1/12 to 12/12, and a calculator that turns a footprint into roof area, squares and bundles.",
        answer, [t1, t2, ex], [
            ("What is the roof pitch multiplier for a 6/12 roof?",
             f"{m.pitch_factor(6):.3f}. Multiply the footprint area or the horizontal run by it to get the sloped area or the rafter length. The angle is {m.pitch_degrees(6):.1f}°."),
            ("How do I calculate a roof pitch multiplier?",
             "Slope factor = √(12² + rise²) ÷ 12. For 8/12: √(144 + 64) ÷ 12 = 1.202."),
            ("What is the hip and valley factor?",
             f"The length of a hip or valley per foot of common run when both planes have the same pitch: √(288 + rise²) ÷ 12. For 6/12 it is {m.hip_factor(6):.3f}, for 12/12 {m.hip_factor(12):.3f}."),
            ("Does the multiplier work for hip roofs?",
             "Yes, for the area. As long as every plane has the same pitch, roof area = footprint × slope factor, whether the roof is a gable or a hip. "
             "Hips and cut-up roofs need more waste for the cuts."),
            ("How do I measure the pitch?",
             "Hold a level horizontally against the roof or a rafter, mark 12 in along it and measure straight down to the roof. That drop in inches is the rise per 12."),
        ], "t-roof", ("roofcalc", "pitch-chart", ROOF_PITCH), "roof", roof_form(50, 40), ROOF_RESULT, "Pitch charts and worked example", ROOF_NOTE,
        extra=c.related("More roofing tools", [("roofing/shingle-bundles-calculator.html", "Shingle bundles calculator")]),
        embed=("roof-pitch", 560))


def build_bundles():
    areas = [1000, 1500, 2000, 2500, 3000, 3500]

    def b(area, waste):
        return str(m.ceil_count(area * (1 + waste) / m.BUNDLE_SQFT))

    t1 = table("Squares and bundles by roof area", ["Roof area", "Squares", "Bundles, no waste", "With 10 % waste", "With 15 %", "With 20 %"],
               [[f"{n(a)} sq ft", f"{a / 100:g}", b(a, 0), b(a, 0.10), b(a, 0.15), b(a, 0.20)] for a in areas],
               src(f"one square is 100 sq ft of roof and standard shingles come 3 bundles to the square ({OC}). "
                   "Some heavier shingles are packed differently, so read the wrapper"))
    t2 = table("A 2,000 sq ft footprint by pitch", ["Pitch", "Roof area", "Squares", "Bundles with 10 % waste"],
               [[f"{r}/12", f"{n(m.roof(2000, r)[0])} sq ft", f"{m.roof(2000, r)[1]:.1f}", str(m.roof(2000, r)[2])] for r in (3, 4, 5, 6, 7, 8, 9, 10, 12)],
               "A \"2,000 sq ft house\" is floor area, not roof area: the roof covers the footprint plus overhangs and is larger the steeper it is.")
    area, sq, bundles = m.roof(2000, 6)
    ex = guides.example("how many squares in a 2,000 sq ft roof", [
        "If 2,000 sq ft is the measured roof surface: 2,000 ÷ 100 = 20 squares, 60 bundles before waste, 66 with 10 %.",
        f"If 2,000 sq ft is the footprint under a 6/12 roof: 2,000 × {m.pitch_factor(6):.3f} = {n(area)} sq ft, or {sq:.1f} squares.",
        f"Bundles with 10 % waste: {n(area)} × 1.10 ÷ 33.3 sq ft per bundle = {bundles}.",
    ], f"Result: 20 squares for 2,000 sq ft of roof surface; {sq:.1f} squares and {bundles} bundles for a 2,000 sq ft footprint at 6/12.")
    answer = (f"one roofing square is 100 sq ft and takes 3 bundles of standard shingles. A 2,000 sq ft roof surface is 20 squares, 60 bundles plus waste. "
              f"A 2,000 sq ft footprint at 6/12 is {sq:.1f} squares, about {bundles} bundles with 10 % waste.")
    c.page(
        "roofing/shingle-bundles-calculator.html", "How Many Bundles of Shingles per Square? Roofing Squares Calculator | Free",
        "Free roofing calculator: squares and bundles of shingles from the footprint and pitch, with waste. How many squares in a 2,000 sq ft roof, by pitch.",
        "Roofing", "Free roofing tool", "Shingle bundles and squares calculator",
        "Roofing squares and bundles of shingles from the footprint and the pitch, with waste for gable, hip and cut-up roofs.",
        answer, [t1, t2, ex], [
            ("How many bundles of shingles are in a square?",
             "Three, for standard three-tab and laminated architectural shingles: each bundle covers about 33.3 sq ft. "
             "Coverage per bundle is printed on the wrapper, and some heavier products are packed differently."),
            ("How many squares is a 2,000 sq ft roof?",
             f"20 squares if 2,000 sq ft is the roof surface. If it is the footprint of the house, the roof is larger: {m.roof(2000, 4)[1]:.1f} squares at 4/12, "
             f"{m.roof(2000, 6)[1]:.1f} at 6/12 and {m.roof(2000, 8)[1]:.1f} at 8/12, before overhangs you have not counted."),
            ("How many bundles do I need for 1,500 sq ft?",
             f"45 bundles for 15 squares with no waste, {b(1500, 0.10)} with 10 % and {b(1500, 0.15)} with 15 %."),
            ("How much waste should I add?",
             "RoofCalc starts from 10 % for a simple gable, 15 % for a hip roof and 20 % for a cut-up roof with valleys and dormers. "
             "Manufacturers do not publish one figure, so adjust it to the roof and your own experience."),
            ("Does this include starter and ridge cap?",
             "No. Starter strip, hip and ridge cap, underlayment, drip edge and nails are counted separately from the field shingles. The RoofCalc app works them out from the same measurements."),
        ], "t-roof", ("roofcalc", "bundles", ROOF_PITCH), "roof", roof_form(50, 40), ROOF_RESULT, "Bundle charts and worked example", ROOF_NOTE,
        extra=c.related("More roofing tools", [("roofing/roof-pitch-multiplier-chart.html", "Roof pitch multiplier chart")]))


# ---------- ShiftWise ----------

SHIFT_PITCH = ("Pick your pattern, tap today's day, and every shift for years ahead falls into place, with a pay estimate, swaps, reminders and a widget. No ads.")
NAMES = {"D": "Day", "N": "Night", "M": "Morning", "A": "Afternoon", "X": "Night", "T": "Day", "O": "Off"}
WIKI = '<a href="https://en.wikipedia.org/wiki/Shift_plan">Wikipedia, "Shift plan"</a>'
SOON = "https://soon.works/shift-patterns"
YEAR = 2027
# key: (file, name, h1 lead-in, hours per shift, where the day-by-day sequence was read, one-line description)
SHIFTS = {
    "4on4off": ("4-on-4-off", "4 on 4 off", 12, f"{WIKI}: four 12-hour shifts, then four days off, a 42-hour average week",
                "Four 12-hour shifts, then four days off. Many rotas alternate a block of days with a block of nights, which makes the full cycle 16 days."),
    "pitman": ("2-2-3-pitman", "2-2-3 (Pitman)", 12, f'<a href="{SOON}/pitman">Soon, Pitman shift pattern</a>: work 2, off 2, work 3, off 2, work 2, off 3',
               "Two on, two off, three on, two off, two on, three off: 12-hour shifts over 14 days. When the cycle starts on a Monday, every other weekend is a three-day break."),
    "dupont": ("dupont", "DuPont", 12, f'{WIKI} and <a href="https://www.rosterelf.com/uk/guides/shift-patterns">RosterElf, shift patterns guide</a>: '
               "4 nights, 3 off, 3 days, 1 off, 3 nights, 3 off, 4 days, 7 off",
               "Four crews on 12-hour shifts over 28 days: four nights, three off, three days, one off, three nights, three off, four days, then seven days off."),
    "3on3off": ("3-on-3-off", "3 on 3 off", 12, "the pattern is defined by its name: three shifts, then three days off, repeating every 6 days",
                "Three 12-hour shifts, then three days off, repeating every six days."),
    "4on3off": ("4-on-3-off", "4 on 3 off (4×10)", 10, f'{WIKI} and <a href="{SOON}">Soon, shift patterns</a>: four 10-hour days and a three-day weekend, 40 hours a week',
                "Four 10-hour days and three days off every week, usually the same weekdays."),
    "continental": ("continental", "Continental", 8, f'<a href="{SOON}/continental">Soon, Continental shift pattern</a>: 2 mornings, 2 afternoons, 3 nights, 2 off; '
                    "2-3-2, 2 off; 3-2-2, 3 off",
                    "Four crews on 8-hour shifts over 28 days: mornings, afternoons and nights in runs of two and three, with two or three days off after each week of work."),
}


def shift_path(key):
    return f"shifts/{SHIFTS[key][0]}.html"


def strip(cycle):
    return '<div class="strip">' + "".join(f'<span class="s-{x}" title="Day {i + 1}: {NAMES[x]}">{x if x != "O" else "–"}</span>' for i, x in enumerate(cycle)) + "</div>"


def legend(cycle):
    used = [x for x in "DMTANX" if x in cycle]
    return '<p class="legend">' + "".join(f'<span><i class="s-{x}" style="background:{"#fde9c4" if x in "DMT" else "#fbd5d0" if x == "A" else "#d9d9f7"}"></i>{x} = {NAMES[x]} shift</span>'
                                          for x in used) + "<span>– = day off</span></p>"


def runs(cycle):
    """(longest run of shifts, longest break) in a repeating cycle."""
    def longest(pred):
        best = cur = 0
        for x in cycle * 2:
            cur = cur + 1 if pred(x) else 0
            best = max(best, cur)
        return min(best, len(cycle))
    return longest(lambda x: x != "O"), longest(lambda x: x == "O")


def build_shift(key):
    slug, name, hours, source, about = SHIFTS[key]
    cycle = m.PATTERNS[key]
    days, work, off, _, _, off_year = m.cycle_stats(cycle)
    per_cycle = work * hours
    week = per_cycle / days * 7
    longest_on, longest_off = runs(cycle)
    offsets = [0, days // 4, days // 2, 3 * days // 4] if days % 4 == 0 else (list(range(7)) if days == 7 else [0, days // 2])
    jan1 = date(YEAR, 1, 1)
    yr_rows = []
    for o in offsets:
        start = jan1 + timedelta(days=o)
        s, f, h, we = m.year_stats(cycle, YEAR, start)
        yr_rows.append([f"{start:%A} {start.day} January {YEAR}", str(s), str(f), n(h), str(we)])
    t1 = table(f"The {name} cycle, day by day", ["Day of the cycle", "Shift", "Hours"],
               [[f"Day {i + 1}", NAMES[x] if x != "O" else "Off", str(hours) if x != "O" else "–"] for i, x in enumerate(cycle)],
               src(source) + " ShiftWise uses the same sequence where it has this pattern as a preset; shift times are yours to change.")
    t2 = table(f"{name} in {YEAR}, by the date your cycle starts", ["Day 1 of the cycle falls on", "Shifts in the year", "Days off", "Hours", "Full weekends off"],
               yr_rows, f"Counted day by day through {YEAR} from the cycle above with {hours}-hour shifts. A full weekend off is a Saturday and Sunday both off. "
               "Holidays, leave and overtime are not included.")
    ex = guides.example(f"average hours per week on {name}", [
        f"One cycle is {days} days with {work} shifts of {hours} hours: {work} × {hours} = {per_cycle} hours.",
        f"Per week: {per_cycle} ÷ {days} × 7 = {week:.1f} hours.",
        f"Days off: {off} of every {days} days, which is {off} ÷ {days} × 365.25 = {off_year:.0f} days off in an average year.",
        f"The longest stretch of work is {longest_on} shifts in a row; the longest break is {longest_off} days.",
    ], f"Result: {week:.1f} hours a week on average and about {off_year:.0f} days off a year.")
    answer = (f"{about} That is {work} shifts in a {days}-day cycle: {week:.1f} hours a week on average with {hours}-hour shifts, "
              f"and about {off_year:.0f} days off a year. Pick a date below to see your own calendar.")
    form = (inp("sdate", "A date you know", "", "", attrs='type="date"') + '<div><label for="sday">On that date you are on</label><select id="sday"></select></div>'
            + inp("slen", "Hours per shift", "", str(hours), True))
    result = rows("s-week", "Average week", [("s-year", "Year counted"), ("s-shifts", "Shifts in that year"), ("s-off", "Days off in that year"),
                                             ("s-hours", "Hours in that year"), ("s-weekends", "Full weekends off")]) \
        + '<p class="note">Scheduled hours. Unpaid breaks, leave and overtime change what you are paid for.</p>'
    others = [(shift_path(k), SHIFTS[k][1]) for k in SHIFTS if k != key]
    c.page(
        shift_path(key), f"{name} Shift Pattern: Calendar Generator, Hours and Days Off | Free",
        f"{name} shift pattern explained: a calendar generator for your own start date, average hours per week, days off per year and full weekends off in {YEAR}.",
        f'<a href="{{rel}}shifts/index.html">Shifts</a> › {name}', "Free shift calendar", f"{name} shift pattern",
        f"The {name} rota day by day, a calendar from your own start date, and the hours and days off it adds up to.",
        answer, [f"<h3>One cycle</h3>{strip(cycle)}{legend(cycle)}", t1, t2, ex], [
            (f"How many hours a week is a {name} shift pattern?",
             f"{week:.1f} hours on average with {hours}-hour shifts: {work} shifts × {hours} hours ÷ {days} days × 7. Single weeks are longer or shorter than the average."),
            (f"How many days off a year do you get on {name}?",
             f"About {off_year:.0f}: {off} days off in every {days}-day cycle. In {YEAR} the exact count is between "
             f"{min(int(r[2]) for r in yr_rows)} and {max(int(r[2]) for r in yr_rows)}, depending on the date your cycle starts. Annual leave comes on top."),
            (f"How many weekends off do you get on {name}?",
             f"In {YEAR}, between {min(int(r[4]) for r in yr_rows)} and {max(int(r[4]) for r in yr_rows)} full weekends (Saturday and Sunday both off), depending on where your cycle starts."
             if days != 7 else "With the same four weekdays every week, the weekend is free whenever your three days off include Saturday and Sunday. Set your own days in the generator."),
            ("How do I find where I am in the cycle?",
             "Pick any date you know, for example today, and choose which day of the cycle it is: \"Day 1\" is the first shift of the block. The calendar fills in from there."),
            ("Does the calendar show my pay?",
             "No, only the shifts and hours. The ShiftWise app adds your hourly rate, night and weekend rates and overtime, and estimates gross pay for each pay period."),
        ], "t-lid", ("shiftwise", f"shift-{slug}", SHIFT_PITCH), "shift", form, result, f"{name} by the numbers",
        note='<section class="card" style="margin-top:20px"><h2>Your next 12 weeks</h2><div class="tablewrap" style="border:0" id="s-cal"></div>'
             '<p class="legend"><span><i style="background:#fde9c4"></i>day shift</span><span><i style="background:#fbd5d0"></i>afternoon</span>'
             '<span><i style="background:#d9d9f7"></i>night</span><span>plain = day off</span></p></section>',
        data={"cycle": "".join(cycle), "names": NAMES}, extra=c.related("Other shift patterns", others))


def build_shift_hub():
    comp = []
    for key, (slug, name, hours, _, _) in SHIFTS.items():
        cycle = m.PATTERNS[key]
        days, work, off, _, _, off_year = m.cycle_stats(cycle)
        on, brk = runs(cycle)
        comp.append([f'<a href="{{rel}}{shift_path(key)}">{name}</a>', f"{days} days", f"{hours} h", str(work), f"{work * hours / days * 7:.1f} h",
                     f"{off_year:.0f}", str(on), f"{brk} days"])
    t1 = table("Shift patterns compared", ["Pattern", "Cycle", "Shift length", "Shifts per cycle", "Average week", "Days off a year", "Longest run of shifts", "Longest break"],
               comp, "Computed from each pattern's day-by-day cycle; the pattern pages name the source of each sequence. Days off a year = days off per cycle ÷ cycle length × 365.25.")
    ex = guides.example("why 12-hour patterns average 42 hours", [
        "A year has 8,766 hours on average (365.25 × 24). Four crews covering all of them work 8,766 ÷ 4 = 2,191.5 hours each.",
        "Per week: 2,191.5 ÷ 52.18 weeks = 42 hours.",
        "So every four-crew rota that covers 24 hours a day lands on 42 hours a week, whether the shifts are 8 or 12 hours long. Only the rhythm of work and rest differs.",
    ], "Result: 4 on 4 off, 2-2-3, DuPont and Continental all average 42 hours a week.")
    cards = "".join(f'<a class="card t-lid" href="{{rel}}{shift_path(k)}"><span class="tag">{v[2]} h shifts</span><h3>{v[1]}</h3><p>{v[4]}</p>{strip(m.PATTERNS[k])}</a>' for k, v in SHIFTS.items())
    answer = ("4 on 4 off, 2-2-3 (Pitman), DuPont and Continental are four-crew rotas that average 42 hours a week; 3 on 3 off also averages 42, "
              "and 4 on 3 off is a 40-hour week of four 10-hour days. Each page below has a calendar generator and the days off it adds up to.")
    c.page(
        "shifts/index.html", "Shift Pattern Calendars: 4 on 4 off, 2-2-3, DuPont, Continental | Free",
        "Free shift pattern calendars and calculators: 4 on 4 off, 2-2-3 Pitman, DuPont, 4 on 3 off, 3 on 3 off and Continental, with hours per week and days off per year.",
        "Shifts", "Free shift calendars", "Shift pattern calendars",
        "Six common rotas day by day, with a calendar generator for your own start date, the average week and the days off each one gives.",
        answer, [f'<div class="grid">{cards}</div>', t1, ex], [
            ("Which shift pattern gives the most days off?",
             "Counted in days, the 12-hour patterns: 4 on 4 off, 2-2-3, DuPont and 3 on 3 off all give about 183 days off a year, because you work half the days. "
             "The price is longer shifts."),
            ("Which pattern has the longest break?",
             "DuPont: seven days off in a row once every 28 days. It also has a 72-hour week in the cycle."),
            ("What is the difference between Pitman and 2-2-3?",
             "They are the same sequence: 2 on, 2 off, 3 on, 2 off, 2 on, 3 off over 14 days. \"Panama\" is another name used for it."),
            ("Can I put my rota on my phone?",
             "Yes. ShiftWise has 4 on 4 off, Pitman, DuPont and 3 on 3 off as presets and lets you build any other rota day by day. "
             "It shows your shifts in a calendar and a home screen widget and exports them to your phone's calendar."),
        ], "t-lid", ("shiftwise", "shift-hub", SHIFT_PITCH), guide_h2="Patterns and comparison")


# ---------- CoatCalc ----------

COAT_PITCH = "Flake, crack filler, cove base, dew point and pot life, then a PDF quote with your client price in one tap."
# Published ranges behind each preset: coatcalc-app/docs/PRESETS.md (manufacturer data sheets, checked October 2026).
COAT_RANGES = {
    "Water-based epoxy": "Water-based sealers and primers: about 50–60 % solids in 3–5 mil coats",
    "100% solids epoxy": "Ecocrete 160 sq ft/gal at 10 mils; Polytitan 150 at 10 mils; Benjamin Moore HP4300 100–150 at 10–15 mils",
    "Polyurea basecoat": "Floorguard 170–200 sq ft/gal at 8–9 mils; UDT Polyurea 1 230–320 at 5–7 mils; Simiron 200–267 at 6–8 mils",
    "Polyaspartic topcoat": "PE-XXX 150–200 sq ft/gal over chip; Poly 85 175–225 over flake; Deco-Crete Polyaspartic 90 150–260",
    "Moisture-vapor primer": "Moisture-vapor epoxy primers: 100 % solids at 12–16 mils",
}


def load_coat():
    src_text = (c.B.ROOT / "coatcalc-app/lib/feature/calc.dart").read_text()
    products = [{"name": name, "solids": float(s), "mils": float(mils), "kit": float(k)} for name, s, mils, k in
                re.findall(r"CoatProduct\(name: '([^']+)', solids: ([\d.]+), mils: ([\d.]+), kitGallons: ([\d.]+)", src_text)]
    garages = [(name, float(v)) for name, v in re.findall(r"'(\d-car)': ([\d.]+)", re.search(r"garages = \{([^}]+)\}", src_text).group(1))]
    for p in products:
        p["def"] = p["name"] == "100% solids epoxy"
    return products, garages


def build_garage():
    products, garages = load_coat()
    by = {p["name"]: p for p in products}
    epoxy, top = by["100% solids epoxy"], by["Polyaspartic topcoat"]

    def gal(sqft, p):
        return m.coat_gallons(sqft, p["mils"], p["solids"], 0.10)

    t1 = table("Gallons for one coat, with 10 % waste", ["Garage (example size)"] + [f'{p["name"]}, {p["mils"]:g} mils' for p in products],
               [[f"{name} · {n(sqft)} sq ft"] + [f"{gal(sqft, p):.1f} gal" for p in products] for name, sqft in garages],
               "Gallons = area × mils ÷ (1,604 × solids by volume) × 1.10. The garage sizes are the presets in CoatCalc, not a standard: measure your own floor.")
    t2 = table("Coverage per gallon by system type", ["System", "Solids by volume", "Typical thickness", "Coverage per gallon", "Published data behind it"],
               [[p["name"], f'{p["solids"] * 100:.0f} %', f'{p["mils"]:g} mils', f'{n(m.coat_rate(p["mils"], p["solids"]))} sq ft', COAT_RANGES.get(p["name"], "")] for p in products],
               src("coverage = 1,604 sq ft per gallon at 1 mil × solids ÷ mils "
                   '(<a href="https://www.neogard.com/news/id/theoretical-vs-actual-coverage-rates">Neogard, "Theoretical vs. actual coverage rates"</a>, checked 12 November 2026); '
                   "solids and thickness are mid-range values from the makers' data sheets named in the last column", "October 2026")
               + " Always use the numbers on your own product's technical data sheet.")
    two = dict(garages)["2-car"]
    g1, g2 = gal(two, epoxy), gal(two, top)
    ex = guides.example(f"a two-car garage, {n(two)} sq ft, flake system", [
        f"Base coat, 100 % solids epoxy at {epoxy['mils']:g} mils: {n(two)} × {epoxy['mils']:g} ÷ 1,604 = {two * epoxy['mils'] / 1604:.2f} gal, plus 10 % = {g1:.2f} gal. "
        f"In {epoxy['kit']:g}-gallon kits: {m.kits(g1, epoxy['kit'])} kit{'s' if m.kits(g1, epoxy['kit']) > 1 else ''}.",
        f"Topcoat, polyaspartic at {top['solids'] * 100:.0f} % solids and {top['mils']:g} mils: {n(two)} × {top['mils']:g} ÷ (1,604 × {top['solids']:.2f}) × 1.10 = {g2:.2f} gal. "
        f"In {top['kit']:g}-gallon kits: {m.kits(g2, top['kit'])}.",
        "Flake, primer and a second topcoat are sized the same way, each from its own data sheet.",
    ], f"Result: about {g1:.1f} gal of epoxy base and {g2:.1f} gal of polyaspartic topcoat.")
    sizes = {name: sqft for name, sqft in garages}
    answer = (f"with a 100 % solids epoxy at 10 mils and 10 % waste, a one-car garage ({n(sizes['1-car'])} sq ft) takes about {gal(sizes['1-car'], epoxy):.1f} gallons, "
              f"a two-car ({n(sizes['2-car'])} sq ft) about {gal(sizes['2-car'], epoxy):.1f} and a three-car ({n(sizes['3-car'])} sq ft) about {gal(sizes['3-car'], epoxy):.1f}. "
              "Thin water-based coats need far less per coat. Measure your floor: garages vary.")
    form = (sel("gsize", "Garage", [(f"{sqft:g}", f"{name} · {n(sqft)} sq ft", name == "2-car") for name, sqft in garages] + [("", "Your own size", False)])
            + inp("garea", "Floor area", "(sq ft)", f"{two:g}")
            + '<div class="full"><label for="gsys">System</label><select id="gsys"></select></div>'
            + inp("gmils", "Thickness", "(mils DFT)", "10") + inp("gsolids", "Solids by volume", "(%)", "100")
            + inp("gwaste", "Waste", "(%)", "10") + inp("gkit", "Kit size", "(gal)", "3"))
    result = rows("ga-gal", "Material for one coat", [("ga-l", "In litres"), ("ga-rate", "Spread rate"), ("ga-kits", "Kits to order")]) \
        + '<p class="note">One coat of one product. Size each layer of the system the same way, from its own data sheet.</p>'
    c.page(
        "coating/garage-floor-epoxy-calculator.html", "How Much Epoxy for a 1, 2 or 3 Car Garage? Calculator | Free",
        "Free garage floor epoxy calculator: gallons and kits for a 1, 2 or 3 car garage by system type, with coverage per gallon for water-based, 100 % solids, polyurea and polyaspartic coatings.",
        "Coatings", "Free coatings tool", "Garage floor epoxy calculator",
        "How many gallons and kits a one, two or three car garage needs, by coating system, thickness and solids.",
        answer, [t1, t2, ex], [
            ("How much epoxy do I need for a 2 car garage?",
             f"For {n(sizes['2-car'])} sq ft with a 100 % solids epoxy at 10 mils and 10 % waste: {gal(sizes['2-car'], epoxy):.1f} gallons for the base coat. "
             f"A 500 sq ft floor takes {m.coat_gallons(500, 10, 1, 0.10):.1f} gallons the same way."),
            ("How much epoxy for a 1 car garage?",
             f"About {gal(sizes['1-car'], epoxy):.1f} gallons of 100 % solids epoxy at 10 mils for {n(sizes['1-car'])} sq ft, with 10 % waste."),
            ("How much epoxy for a 3 car garage?",
             f"About {gal(sizes['3-car'], epoxy):.1f} gallons of 100 % solids epoxy at 10 mils for {n(sizes['3-car'])} sq ft, with 10 % waste. "
             f"In {epoxy['kit']:g}-gallon kits that is {m.kits(gal(sizes['3-car'], epoxy), epoxy['kit'])} kits."),
            ("How many square feet does a gallon of epoxy cover?",
             "1,604 sq ft at 1 mil, times the solids by volume, divided by the dry thickness in mils. A 100 % solids epoxy at 10 mils covers about 160 sq ft; "
             "a 50 % solids water-based epoxy at 3 mils covers about 267 sq ft, but leaves a much thinner film."),
            ("Why does a water-based kit cover more than a 100 % solids kit?",
             "Because it goes on thinner and half of it evaporates. Coverage alone does not compare products: compare the dry film thickness you end up with."),
        ], "t-coat", ("coatcalc", "garage-epoxy", COAT_PITCH), "garage", form, result, "Garage charts and worked example",
        data={"products": products}, extra=c.related("More coating tools", [("coating/epoxy-coverage-calculator.html", "Epoxy coverage calculator")]),
        embed=("garage-epoxy", 620))


# ---------- SlabCalc ----------

SLAB_PITCH = "Slabs, footings, columns and stairs on a feet-inch keypad, with rebar, mesh and forms. Pay once, no ads."
QUIKRETE = ('<a href="https://www.quikrete.com/PDFs/DATA_SHEET-Concrete%20Mix%201101.pdf">QUIKRETE Concrete Mix No. 1101 data sheet</a>: '
            "an 80 lb bag yields about 0.60 cu ft, 60 lb 0.45 cu ft, 40 lb 0.30 cu ft")
THICK = [4, 5, 6, 8]


def slab_path(l, w):
    return f"concrete/{l}x{w}-concrete-slab.html"


def slab_form(l, w):
    return (inp("sl", "Length", "(ft)", str(l)) + inp("sw", "Width", "(ft)", str(w)) + inp("st", "Thickness", "(in)", "4") + inp("sextra", "Extra for waste", "(%)", "10")
            + sel("sspace", "Rebar spacing", [(12, '12 in on centre', False), (16, '16 in on centre', True), (18, '18 in on centre', False), (24, '24 in on centre', False)],
                  "(#4 bar, 20 ft sticks)", True))


SLAB_RESULT = rows("sb-yd", "Concrete, with the extra", [("sb-ft3", "In cubic feet"), ("sb-order", "Ready-mix order (next ¼ yd)"), ("sb-80", "80 lb bags"),
                                                         ("sb-60", "60 lb bags"), ("sb-40", "40 lb bags"), ("sb-rebar", "Rebar grid")]) \
    + '<p class="note">Thickness, reinforcement and bar spacing come from your plans, engineer or building department. This sizes the order.</p>'


def slab_tables(l, w):
    t1 = table(f"Concrete for a {l} × {w} ft slab by thickness",
               ["Thickness", "Exact volume", "With 10 % extra", "Ready-mix order", "80 lb bags", "60 lb bags", "40 lb bags"],
               [[f"{t} in", f"{m.slab_ft3(l, w, t) / 27:.2f} cu yd", f"{m.slab_ft3(l, w, t, 10) / 27:.2f} cu yd", f"{trim(m.order_rounded(m.slab_ft3(l, w, t, 10)))} cu yd"]
                + [n(m.bags_for(m.slab_ft3(l, w, t, 10), y)) for _, y in m.BAGS] for t in THICK],
               src(f"volume is length × width × thickness; bag counts use {QUIKRETE}") + " Bags and the order include the 10 % extra; ready-mix rounds up to the next quarter yard.")
    grid_rows = []
    for sp in (12, 16, 18, 24):
        g = m.rebar_grid(l, w, sp)
        grid_rows.append([f"{sp} in on centre", f"{g['bars_long']} × {g['long_bar']:.1f} ft", f"{g['bars_short']} × {g['short_bar']:.1f} ft", str(g["pieces"]),
                          f"{n(g['total_ft'])} ft", f"{n(g['weight_lb'])} lb"])
    t2 = table(f"#4 rebar grid for a {l} × {w} ft slab", ["Spacing", "Bars along the length", "Bars across", "20 ft sticks to buy", "Total bar", "Weight"],
               grid_rows, "Bars each way = spaces rounded up + 1, 3 in clear of every edge, laps of 40 bar diameters (20 in) where a run is longer than a stick. "
               "#4 bar weighs 0.668 lb per foot (ASTM A615). Spacing and laps are examples: the engineer or your plans set them.")
    return t1, t2


def build_slab(i):
    l, w = SLABS[i]
    area, perim = l * w, 2 * (l + w)
    v4, v4x = m.slab_ft3(l, w, 4), m.slab_ft3(l, w, 4, 10)
    v6x = m.slab_ft3(l, w, 6, 10)
    g = m.rebar_grid(l, w, 16)
    b80, b60 = m.bags_for(v4x, 0.60), m.bags_for(v4x, 0.45)
    small = v4x < m.FT3_PER_YD3
    t1, t2 = slab_tables(l, w)
    how = ("Under a cubic yard, so it is usually mixed from bags." if small else
           f"Over a cubic yard, so ready-mix is usually less work than {n(b80)} bags.")
    ex = guides.example(f"a {l} × {w} ft slab, 4 in thick", [
        f"Area: {l} × {w} = {n(area)} sq ft. Perimeter for the forms: 2 × ({l} + {w}) = {perim} ft.",
        f"Volume: {n(area)} sq ft × 4 in ÷ 12 = {v4:.1f} cu ft, ÷ 27 = {v4 / 27:.2f} cu yd.",
        f"With 10 % extra for uneven ground and spillage: {v4x / 27:.2f} cu yd. Ready-mix is ordered by the quarter yard: {trim(m.order_rounded(v4x))} cu yd.",
        f"In bags: {v4x:.1f} cu ft ÷ 0.60 = {n(b80)} bags of 80 lb, or ÷ 0.45 = {n(b60)} bags of 60 lb. {how}",
        f"Rebar at 16 in on centre: {g['bars_long']} bars of {g['long_bar']:.1f} ft and {g['bars_short']} bars of {g['short_bar']:.1f} ft, "
        f"cut from {g['pieces']} sticks of 20 ft #4, {n(g['weight_lb'])} lb of steel.",
    ], f"Result: order {trim(m.order_rounded(v4x))} cu yd of ready-mix or {n(b80)} bags of 80 lb, and {g['pieces']} sticks of #4 rebar.")
    answer = (f"a {l} × {w} ft slab is {n(area)} sq ft. At 4 in thick it takes {v4 / 27:.2f} cubic yards of concrete, {v4x / 27:.2f} with 10 % extra: "
              f"order {trim(m.order_rounded(v4x))} yards of ready-mix or {n(b80)} bags of 80 lb. At 6 in thick it takes {v6x / 27:.2f} yards with the extra.")
    near = [SLABS[j] for j in range(max(0, i - 3), min(len(SLABS), i + 4)) if j != i]
    c.page(
        slab_path(l, w), f"{l}x{w} Concrete Slab: Yards, Bags and Rebar | Calculator",
        f"How much concrete for a {l}x{w} slab: {v4x / 27:.2f} cubic yards at 4 in with 10 % extra, {n(b80)} bags of 80 lb, plus yards at 5, 6 and 8 in and a #4 rebar grid.",
        f'<a href="{{rel}}concrete/concrete-slab-calculator.html">Concrete</a> › {l} × {w} slab', "Free concrete tool", f"{l} × {w} concrete slab",
        f"Cubic yards, 40, 60 and 80 lb bags and rebar for a {l} by {w} foot slab, at 4, 5, 6 and 8 inches thick. Change any number in the calculator.",
        answer, [t1, t2, ex], [
            (f"How many yards of concrete do I need for a {l}x{w} slab?",
             f"{v4 / 27:.2f} cubic yards at 4 in thick, {m.slab_ft3(l, w, 5) / 27:.2f} at 5 in and {m.slab_ft3(l, w, 6) / 27:.2f} at 6 in, before waste. "
             f"With 10 % extra, order {trim(m.order_rounded(v4x))} yards for a 4 in slab and {trim(m.order_rounded(v6x))} for a 6 in slab."),
            (f"How many bags of concrete for a {l}x{w} slab?",
             f"At 4 in thick with 10 % extra: {n(b80)} bags of 80 lb, {n(b60)} bags of 60 lb or {n(m.bags_for(v4x, 0.30))} bags of 40 lb. {how}"),
            (f"How much rebar do I need for a {l}x{w} slab?",
             f"A #4 grid at 16 in on centre takes {g['pieces']} sticks of 20 ft ({n(g['total_ft'])} ft of bar, {n(g['weight_lb'])} lb). "
             f"At 12 in on centre it is {m.rebar_grid(l, w, 12)['pieces']} sticks, at 24 in {m.rebar_grid(l, w, 24)['pieces']}. Use the spacing on your plans."),
            (f"How thick should a {l}x{w} slab be?",
             "That depends on what it carries and on the ground under it, so take it from your plans, your engineer or the local building department. "
             "The table shows the concrete for 4, 5, 6 and 8 in so you can price each."),
            ("How much extra concrete should I order?",
             "Estimating guides commonly add 5–10 % for spillage and an uneven subgrade, more for complicated forms or pumping. Running short in the middle of a pour costs far more than a little left over."),
        ], "t-slab", ("slabcalc", f"slab-{l}x{w}", SLAB_PITCH), "slab", slab_form(l, w), SLAB_RESULT, f"{l} × {w} slab charts and worked example",
        data={"slab": [l, w]},
        extra=c.related("Other slab sizes", [(slab_path(a, b), f"{a} × {b}") for a, b in near] + [("concrete/concrete-slab-calculator.html", "All sizes")]))


def build_slab_hub():
    size_rows = []
    for l, w in SLABS:
        v = m.slab_ft3(l, w, 4, 10)
        size_rows.append([f'<a href="{{rel}}{slab_path(l, w)}">{l} × {w} ft</a>', f"{n(l * w)} sq ft", f"{v / 27:.2f} cu yd", f"{trim(m.order_rounded(v))} cu yd",
                          n(m.bags_for(v, 0.60)), f"{m.slab_ft3(l, w, 6, 10) / 27:.2f} cu yd"])
    t1 = table("Concrete by slab size", ["Slab", "Area", "4 in thick, with 10 % extra", "Ready-mix order", "80 lb bags", "6 in thick, with 10 % extra"], size_rows,
               src(f"volume is length × width × thickness plus 10 %; bag counts use {QUIKRETE}") + " Each size has its own page with 5 and 8 in slabs and a rebar grid.")
    t2 = table("Bags per cubic yard", ["Bag", "Yield", "Bags per cubic yard"], [[label, f"{y:.2f} cu ft", str(m.bags_for(27, y))] for label, y in m.BAGS],
               src(QUIKRETE))
    v = m.slab_ft3(12, 12, 4, 10)
    ex = guides.example("a 12 × 12 ft patio slab, 4 in thick", [
        "Volume: 12 × 12 × (4 ÷ 12) = 48 cu ft, or 48 ÷ 27 = 1.78 cu yd.",
        f"With 10 % extra: {v:.1f} cu ft = {v / 27:.2f} cu yd. Ready-mix order: {trim(m.order_rounded(v))} cu yd.",
        f"In bags: {v:.1f} ÷ 0.60 = {m.bags_for(v, 0.60)} bags of 80 lb.",
    ], f"Result: {trim(m.order_rounded(v))} cu yd of ready-mix, or {m.bags_for(v, 0.60)} bags of 80 lb.")
    answer = ("cubic yards = length × width × thickness in feet ÷ 27. A 10 × 10 ft slab 4 in thick is 1.23 yards, a 20 × 20 is 4.94 and a 30 × 40 is 14.81, before waste. "
              "One cubic yard is 45 bags of 80 lb, 60 bags of 60 lb or 90 bags of 40 lb.")
    c.page(
        "concrete/concrete-slab-calculator.html", "Concrete Slab Calculator: Yards, Bags and Rebar by Size | Free",
        f"Free concrete slab calculator: cubic yards, 40, 60 and 80 lb bags and a #4 rebar grid for any slab, with {len(SLABS)} common sizes from 10x10 to 60x100 worked out.",
        "Concrete", "Free concrete tool", "Concrete slab calculator",
        "Cubic yards, bags and rebar for a slab of any size, with waste and the ready-mix order rounded to the quarter yard.",
        answer, [t1, t2, ex], [
            ("How do I calculate concrete for a slab?",
             "Multiply length × width × thickness, all in feet (4 in is 0.333 ft), to get cubic feet, then divide by 27 for cubic yards. Add 5–10 % for waste."),
            ("How many 80 lb bags of concrete make a yard?",
             "45. An 80 lb bag yields about 0.60 cu ft and a cubic yard is 27 cu ft. It takes 60 bags of 60 lb or 90 bags of 40 lb."),
            ("How many square feet does a yard of concrete cover?",
             "81 sq ft at 4 in thick, 65 sq ft at 5 in and 54 sq ft at 6 in: 27 cu ft divided by the thickness in feet."),
            ("When should I order ready-mix instead of bags?",
             "Around one cubic yard. Below that a truck is a short load with an extra fee; above it you would be mixing 45 or more 80 lb bags, and ready-mix is usually less work."),
            ("Does the calculator handle footings, columns and stairs?",
             "This page is for rectangular slabs. The SlabCalc app does footings, pads, columns, sonotubes, post holes, walls and stairs, and adds mesh and forms."),
        ], "t-slab", ("slabcalc", "slab-calc", SLAB_PITCH), "slab", slab_form(20, 20), SLAB_RESULT, "Slab sizes and worked example",
        embed=("concrete-slab", 640))


# ---------- PoolPro ----------

POOL_PITCH = "Turn a pool test into exact doses for the chemicals already on your shelf, in the order to add them. Offline, no account, no ads."
TFP = ('<a href="https://www.troublefreepool.com/blog/2019/01/18/free-chlorine-and-cyanuric-acid-relationship-explained/">Trouble Free Pool, '
       '"The Free Chlorine and Cyanuric Acid Relationship"</a>')
CDC = '<a href="https://www.cdc.gov/healthy-swimming/toolkit/pool-chemical-safety.html">CDC, pool chemical safety</a>'
SAFETY = f"""<section class="safety"><h2>Before you add chlorine</h2><ul>
<li><b>The product label comes first.</b> Read it and follow its directions and dose limits, even where this page says something different.</li>
<li><b>Never mix pool chemicals</b> with each other, and never mix different kinds of chlorine. Mixing can release toxic gas or start a fire. Use a clean, dry scoop for each product.</li>
<li>Wear goggles and gloves, work outdoors or with good ventilation, and keep children and pets away.</li>
<li>Add one chemical at a time to the pool water with the pump running. Never add water to a chemical.</li>
<li>Store chemicals in their original labelled containers, dry, closed and apart from each other.</li>
<li>Add in portions, let the water circulate, test again, and wait until the chlorine is back in its normal range before anyone swims.</li>
</ul><p class="note">More on storing and handling pool chemicals: {CDC} (read {c.CHECKED}). If someone breathes fumes or gets chemical in the eyes, call emergency services or poison control.</p></section>"""
POOL_NOTE = SAFETY


def dose_text(product, ppm, gallons):
    amt, unit = m.chlorine_dose(product, ppm, gallons)
    if unit == "fl oz":
        return f"{amt:.0f} fl oz ({amt / 128:.2f} gal)" if amt >= 64 else f"{amt:.1f} fl oz"
    return f"{amt / 16:.2f} lb" if amt >= 16 else f"{amt:.1f} oz"


def pool_form(gallons):
    return (seg("cunit", "Volume unit", [("gal", "US gallons"), ("l", "Litres")]) + inp("cvol", "Pool volume", "", str(gallons), True)
            + '<div class="full"><label for="cprod">Chlorine product <small>(use the strength on your label)</small></label><select id="cprod"></select></div>'
            + inp("cfrom", "Free chlorine now", "(ppm)", "2") + inp("cto", "Target", "(ppm)", "5"))


POOL_RESULT = rows("cl-amt", "Add", [("cl-alt", "Also"), ("cl-rise", "Raises"), ("cl-side", "Also adds")]) \
    + '<p class="note">An estimate from the label strength. Add in portions and retest. Never mix chlorine products with each other or with acid.</p>'
POOL_KEYS = ["liquid10", "liquid125", "bleach6", "bleach825", "calhypo65", "calhypo73", "dichlor", "trichlor"]


def side_text(key, ppm=1.0):
    cya, ch = m.chlorine_side(key, ppm)
    return f"+{cya:.1f} ppm stabilizer (CYA)" if cya else f"+{ch:.1f} ppm calcium hardness" if ch else "salt only"


def tfp_table():
    return table("Free chlorine to keep, by stabilizer level (pools without a salt cell)", ["CYA (stabilizer)", "Minimum FC", "Target FC"],
                 [["30 ppm", "2 ppm", "4–6 ppm"], ["40 ppm", "3 ppm", "5–7 ppm"], ["50 ppm", "4 ppm", "6–8 ppm"]],
                 src(f"{TFP}, liquid chlorine table") + " More stabilizer means more free chlorine is needed. Your local health rules and the product label still apply.")


def build_pool():
    t1 = table("Chlorine to raise free chlorine by 1 ppm in 10,000 US gallons", ["Product (label strength)", "Amount", "Each 1 ppm also adds"],
               [[m.CHLORINE[k][0], dose_text(k, 1, 10000), side_text(k)] for k in POOL_KEYS],
               src("stoichiometry: ppm × litres = milligrams of chlorine, divided by the product's label strength; the same maths as PoolPro, which agrees with "
                   "Trouble Free Pool's Pool Math within about 1 % (10 % liquid chlorine: 12.8 fl oz)", "25 October 2026")
               + " Strengths are common label values: use the one printed on your product.")
    t2 = table("Chlorine for a 1 ppm rise by pool size", ["Pool volume", "Liquid chlorine 10 %", "Liquid chlorine 12.5 %", "Cal-hypo 65 %", "Trichlor 90 %"],
               [[f'<a href="{{rel}}{pool_path(g)}">{n(g)} gal</a>' if g in POOL_SIZES else f"{n(g)} gal"] + [dose_text(k, 1, g) for k in ("liquid10", "liquid125", "calhypo65", "trichlor")]
                for g in (5000, 7500, 10000, 15000, 20000, 25000, 30000, 40000)],
               "Scale by the rise you need: 3 ppm takes three times as much. Trichlor dissolves slowly (tablets in a feeder or floater), so it is not a way to raise chlorine quickly.")
    amt, _ = m.chlorine_dose("liquid10", 3, 15000)
    ex = guides.example("15,000 gallons, free chlorine from 2 to 5 ppm", [
        "Rise needed: 5 − 2 = 3 ppm.",
        f"10 % liquid chlorine: {m.chlorine_dose('liquid10', 1, 10000)[0]:.1f} fl oz raises 10,000 gallons by 1 ppm.",
        f"For 15,000 gallons and 3 ppm: {m.chlorine_dose('liquid10', 1, 10000)[0]:.1f} × 1.5 × 3 = {amt:.0f} fl oz, about {amt / 128:.2f} gallon.",
        f"The same rise with 65 % cal-hypo: {dose_text('calhypo65', 3, 15000)}, which also adds {m.chlorine_side('calhypo65', 3)[1]:.1f} ppm of calcium hardness.",
    ], f"Result: about {amt:.0f} fl oz of 10 % liquid chlorine, added in portions with the pump running.")
    answer = (f"to raise free chlorine by 1 ppm in 10,000 US gallons, add about {m.chlorine_dose('liquid10', 1, 10000)[0]:.1f} fl oz of 10 % liquid chlorine, "
              f"{m.chlorine_dose('calhypo65', 1, 10000)[0]:.1f} oz of 65 % cal-hypo or {m.chlorine_dose('trichlor', 1, 10000)[0]:.1f} oz of 90 % trichlor. "
              "Scale by your pool's gallons and the ppm you need, and follow the product label.")
    c.page(
        "pool/how-much-chlorine-to-add.html", "How Much Chlorine to Add to a Pool: Calculator by Gallons and Product | Free",
        "Free pool chlorine calculator: how much liquid chlorine, bleach, cal-hypo, dichlor or trichlor to add for your pool's gallons and the ppm you need, with safety notes.",
        "Pool", "Free pool tool", "How much chlorine to add to a pool",
        "The amount of liquid chlorine, bleach, cal-hypo, dichlor or trichlor that raises free chlorine by the ppm you need, for your pool's volume.",
        answer, [t1, t2, tfp_table(), ex], [
            ("How much liquid chlorine do I add per 10,000 gallons?",
             f"About {m.chlorine_dose('liquid10', 1, 10000)[0]:.1f} fl oz of 10 % liquid chlorine, or {m.chlorine_dose('liquid125', 1, 10000)[0]:.1f} fl oz of 12.5 %, for each 1 ppm of free chlorine. "
             f"A 3 ppm rise takes {m.chlorine_dose('liquid10', 3, 10000)[0]:.0f} fl oz of 10 %."),
            ("How much chlorine per gallon of pool water?",
             f"Per 1,000 gallons, 1 ppm takes about {m.chlorine_dose('liquid10', 1, 1000)[0]:.2f} fl oz of 10 % liquid chlorine or {m.chlorine_dose('calhypo65', 1, 1000)[0]:.2f} oz of 65 % cal-hypo. "
             "Work from the ppm you need, not from a fixed amount per gallon."),
            ("What is the difference between liquid chlorine, cal-hypo and trichlor?",
             f"All add free chlorine. Liquid chlorine and bleach add only salt. Cal-hypo also adds calcium: about {m.chlorine_side('calhypo65', 10)[1]:.0f} ppm of hardness for every 10 ppm of chlorine. "
             f"Trichlor and dichlor also add stabilizer: about {m.chlorine_side('trichlor', 10)[0]:.0f} and {m.chlorine_side('dichlor', 10)[0]:.0f} ppm of CYA per 10 ppm of chlorine, which builds up over a season."),
            ("How much free chlorine should my pool have?",
             "It depends on the stabilizer (CYA) level: Trouble Free Pool's chart gives a target of 4–6 ppm at 30 ppm CYA and 5–7 ppm at 40 ppm for pools without a salt cell. "
             "Test first, then dose the difference."),
            ("Can I mix two kinds of chlorine to save time?",
             "No. Never mix pool chemicals, and never put one kind of chlorine into a feeder, bucket or scoop that held another: some combinations react violently. "
             "Add each product to the pool water separately."),
            ("How long after adding chlorine can you swim?",
             "Follow the product label. As a rule, let the pump circulate the water, test again, and swim only when the free chlorine is back within the range for your pool."),
        ], "t-pool", ("poolpro", "chlorine", POOL_PITCH), "chlor", pool_form(15000), POOL_RESULT, "Chlorine charts and worked example", POOL_NOTE,
        extra=c.related("Chlorine by pool size", [(pool_path(g), f"{n(g)} gallons") for g in POOL_SIZES] + [("pool/pool-chemical-calculator.html", "Pool chemical calculator")]),
        embed=("pool-chlorine", 600))


def pool_path(gallons):
    return f"pool/chlorine-for-{gallons}-gallon-pool.html"


def build_pool_size(gallons):
    litres = gallons * 3.78541
    rises = [1, 2, 3, 5, 10]
    t1 = table(f"Chlorine for a {n(gallons)} gallon pool", ["Product (label strength)"] + [f"+{r} ppm" for r in rises],
               [[m.CHLORINE[k][0]] + [dose_text(k, r, gallons) for r in rises] for k in POOL_KEYS],
               src("ppm × litres = milligrams of chlorine, divided by the label strength; the same maths as PoolPro, cross-checked with Trouble Free Pool's Pool Math",
                   "25 October 2026") + " Use the strength printed on your own product.")

    def adds(key, grams_or_ml):
        _, kind, v = m.CHLORINE[key]
        mg = grams_or_ml / 1000 * v * 1000 if kind == "liquid" else grams_or_ml * v * 1000
        fc = mg / litres
        cya, ch = m.chlorine_side(key, fc)
        return [f"+{fc:.1f} ppm", f"+{cya:.1f} ppm" if cya else "–", f"+{ch:.1f} ppm" if ch else "–"]

    t2 = table(f"What one container adds to {n(gallons)} gallons", ["You add", "Free chlorine", "Stabilizer (CYA)", "Calcium hardness"],
               [["1 gallon of liquid chlorine 10 %"] + adds("liquid10", 3785.41), ["1 gallon of liquid chlorine 12.5 %"] + adds("liquid125", 3785.41),
                ["1 gallon of bleach 8.25 %"] + adds("bleach825", 3785.41), ["1 lb of cal-hypo 65 %"] + adds("calhypo65", 453.592),
                ["1 lb of dichlor 56 %"] + adds("dichlor", 453.592), ["1 lb of trichlor 90 %"] + adds("trichlor", 453.592)],
               "The same maths run backwards. Stabilizer and calcium stay in the water after the chlorine is used up; only replacing water lowers them.")
    a10 = m.chlorine_dose("liquid10", 3, gallons)[0]
    ex = guides.example(f"{n(gallons)} gallons, free chlorine from 2 to 5 ppm", [
        "Rise needed: 5 − 2 = 3 ppm.",
        f"{n(gallons)} gallons is {n(litres)} litres, so 3 ppm is 3 × {n(litres)} ÷ 1,000 = {3 * litres / 1000:.0f} g of chlorine.",
        f"10 % liquid chlorine holds 100 g per litre: {3 * litres / 1000:.0f} ÷ 100 = {3 * litres / 100000:.2f} L, which is {a10:.0f} fl oz.",
        f"With 65 % cal-hypo instead: {dose_text('calhypo65', 3, gallons)}.",
    ], f"Result: about {a10:.0f} fl oz ({a10 / 128:.2f} gal) of 10 % liquid chlorine.")
    answer = (f"each 1 ppm of free chlorine in a {n(gallons)} gallon pool takes about {dose_text('liquid10', 1, gallons)} of 10 % liquid chlorine, "
              f"{dose_text('calhypo65', 1, gallons)} of 65 % cal-hypo or {dose_text('trichlor', 1, gallons)} of 90 % trichlor. "
              f"Raising it from 2 to 5 ppm takes {dose_text('liquid10', 3, gallons)} of 10 % liquid chlorine. Follow the product label.")
    c.page(
        pool_path(gallons), f"How Much Chlorine for a {n(gallons)} Gallon Pool? Chart by Product",
        f"How much chlorine to add to a {n(gallons)} gallon pool: liquid chlorine, bleach, cal-hypo, dichlor and trichlor for a 1 to 10 ppm rise, with a calculator and safety notes.",
        f'<a href="{{rel}}pool/how-much-chlorine-to-add.html">Pool</a> › {n(gallons)} gallons', "Free pool tool", f"How much chlorine for a {n(gallons)} gallon pool",
        f"Liquid chlorine, bleach, cal-hypo, dichlor and trichlor for a {n(gallons)} gallon pool, by the ppm of free chlorine you need to add.",
        answer, [t1, t2, tfp_table(), ex], [
            (f"How much liquid chlorine for a {n(gallons)} gallon pool?",
             f"{dose_text('liquid10', 1, gallons)} of 10 % liquid chlorine for each 1 ppm, so {dose_text('liquid10', 3, gallons)} for a 3 ppm rise. With 12.5 % it is {dose_text('liquid125', 1, gallons)} per ppm."),
            (f"How much does a gallon of liquid chlorine raise a {n(gallons)} gallon pool?",
             f"One gallon of 10 % liquid chlorine adds about {adds('liquid10', 3785.41)[0][1:]} of free chlorine; one gallon of 12.5 % adds {adds('liquid125', 3785.41)[0][1:]}."),
            (f"How much cal-hypo for a {n(gallons)} gallon pool?",
             f"{dose_text('calhypo65', 1, gallons)} of 65 % cal-hypo per 1 ppm of free chlorine, {dose_text('calhypo65', 5, gallons)} for 5 ppm. It adds calcium hardness too, so watch that level in hard-water areas."),
            (f"How many pounds of trichlor does a {n(gallons)} gallon pool use?",
             f"One pound of 90 % trichlor adds {adds('trichlor', 453.592)[0][1:]} of free chlorine and {adds('trichlor', 453.592)[1][1:]} of stabilizer here. "
             "How much the pool uses per week depends on sun, heat and swimmers, so test and adjust."),
            ("Is it safe to add this much at once?",
             "Read the label for the largest single dose, add in portions with the pump running and test again before adding more. Never mix products."),
        ], "t-pool", ("poolpro", f"chlorine-{gallons}", POOL_PITCH), "chlor", pool_form(gallons), POOL_RESULT, f"{n(gallons)} gallon charts and worked example", POOL_NOTE,
        data={"gallons": gallons},
        extra=c.related("Other pool sizes", [(pool_path(g), f"{n(g)} gallons") for g in POOL_SIZES if g != gallons] + [("pool/how-much-chlorine-to-add.html", "Any size")]))


def build():
    build_pitch()
    build_bundles()
    build_shift_hub()
    for key in SHIFTS:
        build_shift(key)
    build_garage()
    build_slab_hub()
    for i in range(len(SLABS)):
        build_slab(i)
    build_pool()
    for g in POOL_SIZES:
        build_pool_size(g)


# Rows for the methodology page (trust.METHODS): (calculator, page, tables and formulas, assumptions, limits).
METHODS = [
    ("Roof pitch chart and shingle bundles calculator", "roofing/roof-pitch-multiplier-chart.html",
     ["Slope factor = &radic;(12&sup2; + rise&sup2;) &divide; 12; hip and valley factor = &radic;(2 &times; 12&sup2; + rise&sup2;) &divide; 12. Exact geometry, the same as in the RoofCalc app.",
      "One square is 100 sq ft; three bundles to the square (Owens Corning, read 12 November 2026), 33.3 sq ft per bundle."],
     ["Every plane of the roof has the same pitch.", "The footprint includes the overhangs."],
     ["Field shingles only: starter, ridge cap, underlayment, drip edge and nails are not counted.",
      "Coverage per bundle differs between products: read the wrapper.", "Code limits for low slopes follow the IRC; your local code may differ."]),
    ("Concrete slab calculator and slab sizes", "concrete/concrete-slab-calculator.html",
     ["Volume = length &times; width &times; thickness; 27 cu ft to the cubic yard; ready-mix rounded up to the next quarter yard.",
      "Bag yields from the QUIKRETE Concrete Mix No. 1101 data sheet: 0.60, 0.45 and 0.30 cu ft for 80, 60 and 40 lb bags (read 12 November 2026).",
      "Rebar: bars each way = spaces rounded up + 1, #4 bar at 0.668 lb per foot (ASTM A615), 20 ft sticks, laps of 40 bar diameters."],
     ["A flat rectangular slab of even thickness.", "10 % extra unless you change it; bars 3 in clear of the edges."],
     ["It sizes an order. Thickness, reinforcement, joints and base come from your plans, engineer or building department.",
      "Lap length depends on the concrete, the bar and the spacing: the engineer gives it."]),
    ("Garage floor epoxy calculator", "coating/garage-floor-epoxy-calculator.html",
     ["Gallons = area &times; mils &divide; (1,604 &times; solids by volume) &times; (1 + waste), as on the epoxy coverage calculator.",
      "System presets (solids and thickness) are the CoatCalc app's mid-range values from makers' data sheets (read October 2026)."],
     ["One coat of one product at the dry film thickness you enter."],
     ["The garage sizes are examples, not a standard: measure the floor.", "Use the solids and coverage on your own product's data sheet."]),
    ("Pool chlorine calculator", "pool/how-much-chlorine-to-add.html",
     ["ppm &times; litres = milligrams of chlorine, divided by the product's label strength: the same maths as the pool chemical calculator and the PoolPro app.",
      "Stabilizer from dichlor and trichlor and calcium from cal-hypo follow from the molar masses.",
      "Free chlorine by stabilizer level: Trouble Free Pool's FC/CYA chart (read 12 November 2026)."],
     ["The pool volume and the strength on the label are right."],
     ["The product label comes first, including its largest single dose.", "Never mix pool chemicals. Add in portions and test again.",
      "It does not handle pH, alkalinity or water balance."]),
    ("Shift pattern calendars", "shifts/",
     ["Each rota is written out day by day and counted: hours per week = hours per cycle &divide; cycle days &times; 7; days off a year = days off per cycle &divide; cycle days &times; 365.25.",
      "The sequences are those of the ShiftWise app where it has the pattern, and of the sources named on each page (read 12 November 2026)."],
     ["Every shift has the same length; the calendar year is counted day by day."],
     ["Scheduled hours only: unpaid breaks, leave, overtime and public holidays are not counted.", "Employers run variants of every pattern: go by your own rota."]),
]
