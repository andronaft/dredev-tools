"""Control values for calc_math.py and assets/calc-more.js.

The expected numbers are the ones the apps' own unit tests pin (ferment-app, growlab-app, wickcalc-app, roofcalc-app,
slabcalc-app, pool-chem-app, coatcalc-app, Calculator_for_electrical test/*.dart), so a page can only drift from an
app by failing here.
Run: python3 -m unittest discover -s tests
"""
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import calc_math as m  # noqa: E402
import guides  # noqa: E402


def js(expr):
    """Evaluates an expression against the maths exported by calc-more.js (node)."""
    code = f"const m = require({json.dumps(str(ROOT / 'assets/calc-more.js'))}); console.log(JSON.stringify({expr}));"
    return json.loads(subprocess.run(["node", "-e", code], check=True, capture_output=True, text=True).stdout)


class Ferment(unittest.TestCase):
    def test_gravity_scales(self):  # ferment-app/test/calc_test.dart
        self.assertEqual(m.degrees_to_sg(0), 1.0)
        self.assertAlmostEqual(m.degrees_to_sg(12), 1.0484, delta=0.0001)
        self.assertAlmostEqual(m.degrees_to_sg(24), 1.1014, delta=0.0005)
        self.assertAlmostEqual(m.sg_to_degrees(1.050), 12.39, delta=0.02)
        self.assertAlmostEqual(m.sg_to_degrees(1.100), 23.8, delta=0.1)

    def test_abv(self):
        self.assertAlmostEqual(m.abv_standard(1.050, 1.010), 5.25, places=9)
        self.assertAlmostEqual(m.abv_standard(1.110, 1.000), 14.44, delta=0.01)
        self.assertAlmostEqual(m.abv_alternate(1.050, 1.010), 5.34, delta=0.01)
        self.assertAlmostEqual(m.abv_alternate(1.110, 1.000), 15.85, delta=0.02)
        self.assertAlmostEqual(m.attenuation(1.100, 1.010), 90, places=6)

    def test_honey(self):  # 35 points per pound per gallon (Sugar.honey.ppg)
        self.assertAlmostEqual(m.honey_points(1, 1), 35, places=9)
        self.assertAlmostEqual(m.honey_lb_for(100, 5), 14.2857, delta=0.0001)
        self.assertAlmostEqual(m.honey_points(m.honey_lb_for(80, 3), 3), 80, places=9)

    def test_js(self):
        got = js("[m.degreesToSg(12), m.sgToDegrees(1.1), m.abvStandard(1.11, 1), m.abvAlternate(1.11, 1), m.attenuation(1.1, 1.01), m.honeyLbFor(100, 5), m.honeyPoints(15, 5)]")
        want = [m.degrees_to_sg(12), m.sg_to_degrees(1.1), m.abv_standard(1.11, 1), m.abv_alternate(1.11, 1), m.attenuation(1.1, 1.01),
                m.honey_lb_for(100, 5), m.honey_points(15, 5)]
        for a, b in zip(got, want):
            self.assertAlmostEqual(a, b, places=9)


class GrowLab(unittest.TestCase):
    def test_scales(self):  # growlab-app/test/calc_test.dart
        self.assertAlmostEqual(m.ec_to_ppm(1.4, "500"), 700, places=9)
        self.assertAlmostEqual(m.ec_to_ppm(1.4, "700"), 980, places=9)
        self.assertAlmostEqual(m.ppm_to_ec(840, "700"), 1.2, places=9)
        self.assertAlmostEqual(m.ec_to_ppm(1.413, "500"), 706.5, delta=0.1)
        self.assertAlmostEqual(m.ec_to_ppm(1.413, "700"), 989.1, delta=0.1)
        self.assertAlmostEqual(m.ec_to_ppm(1.0, "640"), 640, places=9)

    def test_js(self):
        got = js("[m.fromEc(1.4, 'ppm500'), m.fromEc(1.4, 'ppm700'), m.toEc(840, 'ppm700'), m.fromEc(1.4, 'us'), m.fromEc(1, 'ppm640')]")
        for a, b in zip(got, [700, 980, 1.2, 1400, 640]):
            self.assertAlmostEqual(a, b, places=9)


class GrowLabVpd(unittest.TestCase):
    def test_vpd(self):  # growlab-app/test/calc_test.dart
        self.assertAlmostEqual(m.svp(20), 2.338, delta=0.001)  # FAO-56 Annex 2 Table 2.3
        self.assertAlmostEqual(m.svp(25), 3.168, delta=0.001)
        self.assertAlmostEqual(m.svp(30), 4.243, delta=0.001)
        self.assertAlmostEqual(m.leaf_vpd(25, 25, 50), 1.584, delta=0.001)
        self.assertAlmostEqual(m.leaf_vpd(25, 23, 60), 0.908, delta=0.002)
        rh = m.rh_for_vpd(26, 24, 1.0)
        self.assertAlmostEqual(m.leaf_vpd(26, 24, rh), 1.0, places=9)
        dew = m.dew_point(25, 60)
        self.assertAlmostEqual(m.svp(dew), m.svp(25) * 0.6, places=9)
        self.assertAlmostEqual(m.leaf_vpd(25, dew, 60), 0, places=9)
        self.assertIsNone(m.dew_point(25, 0))

    def test_js(self):
        got = js("[m.svp(25), m.leafVpd(25, 23, 60), m.rhForVpd(26, 24, 1), m.dewPoint(25, 60)]")
        for a, b in zip(got, [m.svp(25), m.leaf_vpd(25, 23, 60), m.rh_for_vpd(26, 24, 1), m.dew_point(25, 60)]):
            self.assertAlmostEqual(a, b, places=9)


class WickCalc(unittest.TestCase):
    def test_jar(self):  # wickcalc-app/test/calc_test.dart
        self.assertAlmostEqual(m.fill_from_water(8), 6.88, delta=0.005)
        wax, fo = m.candle_split(m.fill_from_water(100), 10)  # Veda Oils example
        self.assertAlmostEqual(wax, 78.18, delta=0.01)
        self.assertAlmostEqual(fo, 7.82, delta=0.01)
        wax, fo = m.candle_split(m.fill_from_water(10, 0.85), 10, of_wax=False)
        self.assertAlmostEqual(wax, 7.65, places=9)
        self.assertAlmostEqual(fo, 0.85, places=9)

    def test_load(self):
        self.assertAlmostEqual(m.fragrance_for_wax(16, 6.25), 1.0, places=9)  # 1 oz per pound
        self.assertAlmostEqual(m.convert_load(10), 9.0909, delta=0.0001)
        self.assertAlmostEqual(m.convert_load(m.convert_load(10), from_wax=False), 10, places=9)

    def test_js(self):
        got = js("[m.fillFromWater(8, 0.86), ...m.candleSplit(86, 10, true), ...m.candleSplit(8.5, 10, false), m.convertLoad(10, true), m.convertLoad(10, false)]")
        want = [m.fill_from_water(8), *m.candle_split(86, 10), *m.candle_split(8.5, 10, False), m.convert_load(10), m.convert_load(10, False)]
        for a, b in zip(got, want):
            self.assertAlmostEqual(a, b, places=9)


class RoofCalc(unittest.TestCase):
    def test_pitch(self):  # roofcalc-app/test/roof_test.dart
        self.assertEqual(m.pitch_factor(0), 1)
        for rise, want in ((4, 1.0541), (6, 1.1180), (8, 1.2019), (12, 1.4142)):
            self.assertAlmostEqual(m.pitch_factor(rise), want, delta=1e-4)
        self.assertAlmostEqual(m.hip_factor(6), 1.5, places=9)
        self.assertAlmostEqual(m.hip_factor(12), 1.7321, delta=1e-4)
        self.assertAlmostEqual(m.pitch_degrees(12), 45, places=9)
        self.assertAlmostEqual(m.pitch_degrees(6), 26.565, delta=1e-3)

    def test_bundles(self):
        area, squares, bundles = m.roof(2000, 6, 0.10)
        self.assertAlmostEqual(area, 2236.07, delta=0.01)
        self.assertAlmostEqual(squares, 22.36, delta=0.01)
        self.assertEqual(bundles, 74)
        self.assertEqual(m.roof(2000, 0, 0)[2], 60)  # 20 squares, 3 bundles each, no float dust

    def test_js(self):
        got = js("[m.pitchFactor(6), m.hipFactor(6), m.pitchDegrees(6), m.roof(2000, 6, 0.1), m.roof(2000, 0, 0).bundles]")
        self.assertAlmostEqual(got[0], m.pitch_factor(6), places=12)
        self.assertAlmostEqual(got[1], 1.5, places=12)
        self.assertAlmostEqual(got[2], m.pitch_degrees(6), places=9)
        self.assertEqual(got[3]["bundles"], 74)
        self.assertEqual(got[4], 60)


class DialIn(unittest.TestCase):
    def test_ratio(self):  # dialin-coffee-app dial_in.dart shotStyle
        self.assertEqual(m.brew_ratio(18, 36), 2)
        self.assertEqual([m.shot_style(r) for r in (1.0, 1.5, 1.51, 2.5, 2.51)], ["ristretto", "ristretto", "normale", "normale", "lungo"])
        self.assertEqual(js("[1, 1.5, 1.51, 2.5, 2.51].map(m.shotStyle)"), ["ristretto", "ristretto", "normale", "normale", "lungo"])


class RowKeeper(unittest.TestCase):
    def test_yarn(self):  # rowcounter-app yarn_math.dart
        needed, skeins = m.skeins_needed(1000, 220, 10)
        self.assertAlmostEqual(needed, 1100, places=9)
        self.assertEqual(skeins, 5)
        self.assertEqual(m.skeins_needed(440, 220)[1], 2)  # exactly two skeins stays two
        self.assertAlmostEqual(m.length_from_weight(100, 220, 3.2), 7.04, places=9)
        self.assertAlmostEqual(m.swatch_yarn(4, 4, 7.04, 8, 60), 211.2, places=9)
        self.assertEqual(m.gauge_count(18, 20), 90)
        self.assertEqual(m.gauge_count(24, 60), 360)

    def test_js(self):
        got = js("[m.skeinsNeeded(1000, 220, 10).skeins, m.skeinsNeeded(440, 220, 0).skeins, m.lengthFromWeight(100, 220, 3.2), m.swatchYarn(4, 4, 7.04, 8, 60), m.gaugeCount(18, 20), m.gaugeCount(22, 30)]")
        self.assertEqual(got[:2], [5, 2])
        self.assertAlmostEqual(got[2], 7.04, places=9)
        self.assertAlmostEqual(got[3], 211.2, places=9)
        self.assertEqual(got[4:], [90, m.gauge_count(22, 30)])


class ShiftWise(unittest.TestCase):
    def test_cycles(self):  # shift-calendar-app patterns.dart: cycle lengths and working days
        want = {"4on4off": (8, 4, 42.0), "pitman": (14, 7, 42.0), "dupont": (28, 14, 42.0), "3on3off": (6, 3, 42.0),
                "4on3off": (7, 4, 40.0), "continental": (28, 21, 42.0)}
        for key, (days, work, week) in want.items():
            n, w, off, hours, per_week, _ = m.cycle_stats(m.PATTERNS[key])
            self.assertEqual((n, w, off), (days, work, days - work), key)
            self.assertAlmostEqual(per_week, week, places=9, msg=key)
        self.assertEqual("".join(m.PATTERNS["dupont"]), "NNNNOOODDDONNNOOODDDDOOOOOOO")
        self.assertEqual("".join(m.PATTERNS["pitman"]), "DDOODDDOODDOOO")
        self.assertEqual("".join(m.PATTERNS["continental"]), "MMAAXXXOOMMAAAXXOOMMMAAXXOOO")

    def test_year(self):
        cycle = m.PATTERNS["4on4off"]
        shifts, off, hours, weekends = m.year_stats(cycle, 2027, date(2027, 1, 1))
        self.assertEqual(shifts + off, 365)
        self.assertEqual(shifts, 184)  # 45 full cycles (180 shifts) + 5 days, of which 4 are shifts
        self.assertEqual(hours, shifts * 12)
        # Monday to Thursday every week: every weekend of the year is free.
        self.assertEqual(m.year_stats(m.PATTERNS["4on3off"], 2027, date(2027, 1, 4))[3], 52)

    def test_js(self):
        for key, start in (("4on4off", date(2027, 1, 1)), ("dupont", date(2027, 1, 8)), ("continental", date(2026, 12, 20)), ("4on3off", date(2027, 1, 4))):
            cycle = m.PATTERNS[key]
            got = js(f"m.yearStats({json.dumps(cycle)}, 2027, m.dayNumber({start.year}, {start.month - 1}, {start.day}), {json.dumps(m.SHIFT_HOURS)})")
            self.assertEqual((got["shifts"], got["off"], got["hours"], got["weekends"]), m.year_stats(cycle, 2027, start), key)


class ElectricianCalc(unittest.TestCase):
    LIMITS = (0.53, 0.31, 0.40)  # NEC Chapter 9 Table 1 (necFillLimit)
    HALF_EMT, W14, W12, W10 = 0.304, 0.0097, 0.0133, 0.0211  # Chapter 9 Tables 4 and 5, as in nec_tables.dart
    EGC = [(15, "14", "12"), (20, "12", "10"), (60, "10", "8"), (100, "8", "6"), (200, "6", "4")]  # Table 250.122

    def test_conduit_fill(self):  # Calculator_for_electrical/test/nec_test.dart 'conduit fill matches Annex C'
        self.assertEqual(m.conduit_max(self.W12, self.HALF_EMT, self.LIMITS), 9)
        self.assertEqual(m.conduit_max(self.W14, self.HALF_EMT, self.LIMITS), 12)
        self.assertFalse(m.conduit_fill([self.W12] * 10, self.HALF_EMT, self.LIMITS)[2])
        # test/conduit_fill_test.dart: three 10 AWG and a 12 AWG ground in 1/2 in. EMT, 0.0766 in², 25.2 %.
        pct, limit, ok = m.conduit_fill([self.W10] * 3 + [self.W12], self.HALF_EMT, self.LIMITS)
        self.assertEqual((f"{pct:.1f}", f"{limit:.0f}", ok), ("25.2", "40", True))
        # One conductor may fill 53 %, two 31 %: the count stops at one where two would pass 31 %.
        self.assertEqual([m.fill_limit(n, self.LIMITS) for n in (1, 2, 3, 9)], [0.53, 0.31, 0.40, 0.40])
        self.assertEqual(m.conduit_max(0.0507, self.HALF_EMT, self.LIMITS), 1)  # 6 AWG: two are 33 % of 1/2 in. EMT
        self.assertEqual(m.conduit_max(0.1855, self.HALF_EMT, self.LIMITS), 0)  # 1/0: one is 61 %

    def test_box_fill(self):  # test/customer_voice_test.dart 'box fill counts allowances as NEC 314.16(B) does'
        n, need, ok, spare = m.box_fill(4, True, 0, 1, 2, 2.25, 18)
        self.assertEqual((n, ok, spare), (8, True, 0))
        self.assertAlmostEqual(need, 18, places=9)
        self.assertEqual(m.box_fill(0, False, 0, 0, 6, 2, 10)[0], 1.5)
        self.assertEqual(m.box_fill(0, False, 0, 0, 0, 2.25, 21)[3], 9)

    def test_grounds(self):  # test/nec_test.dart 'equipment grounding conductor'
        cmil, sizes = dict(guides.NEC), guides.NEC_SIZES
        self.assertEqual([m.egc_for(20, self.EGC), m.egc_for(100, self.EGC), m.egc_for(150, self.EGC, False)], ["12", "8", "4"])
        self.assertIsNone(m.egc_for(250, self.EGC))
        self.assertEqual(m.egc_upsized(20, self.EGC, cmil, sizes, "12", "8"), "8")
        self.assertEqual(m.egc_upsized(60, self.EGC, cmil, sizes, "6", "3"), "6")
        self.assertEqual(m.egc_upsized(60, self.EGC, cmil, sizes, "6", "6"), "10")

    def test_adjusted_wire_size(self):  # test/nec_test.dart: THHN copper on 75 °C terminals
        self.assertEqual(guides.wire_size(16, "thhn", "cu", True)[::2], ("12", 20))  # continuous 16 A: 12 AWG on 20 A
        self.assertEqual(guides.wire_size(40, "thhn", "cu", adjust=0.91 * 0.80)[0], "8")  # 36–40 °C and 4–6 conductors
        self.assertEqual([guides.wire_size(a, "nmb")[0] for a in (20, 30)], ["12", "10"])  # NM-B at the 60 °C column
        self.assertEqual(guides.wire_size(40)[1], 50)  # without a factor the ampacity stays the table's whole number


class BatteryRuntime(unittest.TestCase):
    """Battery & UPS Runtime (electrical.dart) and the Ukrainian battery page (assets/battery-uk.js)."""

    def test_app_control_values(self):  # Calculator_for_electrical/test/electrical_test.dart
        self.assertAlmostEqual(m.battery_runtime(12, 100, 2, 432), 4, places=9)
        self.assertAlmostEqual(m.battery_capacity_for(24, 432, 4), 100, places=9)

    def test_bank_series_and_parallel(self):
        self.assertEqual(m.battery_bank(12, 100, 1, 2), (12, 200, 2400))  # parallel adds Ah
        self.assertEqual(m.battery_bank(12, 100, 2, 1), (24, 100, 2400))  # series adds volts, same energy
        self.assertEqual(m.battery_bank(12, 100, 4, 2), (48, 200, 9600))

    def test_chat_example(self):  # 2 × AGM 100 Ah on 12 V, router, fridge and boiler (223 W), charged at 20 A
        self.assertAlmostEqual(m.battery_runtime(12, 100, 2, 223, 0.5, 0.85), 1020 / 223, places=9)
        self.assertAlmostEqual(m.charge_hours(100, 20, 0.9), 5.5556, delta=1e-4)
        need = m.battery_capacity_for(12, 223, 8, 0.5, 0.85)
        self.assertAlmostEqual(need, 349.8, delta=0.05)
        self.assertEqual(m.batteries_for(need, 100, 1), (4, 4))
        self.assertEqual(m.batteries_for(need / 2, 100, 2), (2, 4))  # the same energy at 24 V: two strings of two

    def test_edges(self):
        self.assertEqual(m.battery_runtime(12, 100, 1, 0), 0)
        self.assertEqual(m.charge_hours(100, 0, 0.9), 0)
        self.assertEqual(m.batteries_for(200, 100), (2, 2))  # exactly full: no extra battery for rounding dust
        self.assertEqual(m.batteries_for(200.0000000001, 100), (2, 2))
        self.assertEqual(m.batteries_for(201, 100), (3, 3))

    def test_js(self):
        code = (f"const m = require({json.dumps(str(ROOT / 'assets/battery-uk.js'))}); console.log(JSON.stringify(["
                "m.batteryRuntime(12, 100, 2, 432, 0.8, 0.9), m.batteryCapacityFor(24, 432, 4, 0.8, 0.9), m.batteryBank(12, 100, 4, 2), "
                "m.batteryRuntime(12.8, 100, 2, 223, 0.8, 0.85), m.chargeHours(100, 20, 0.9), m.batteriesFor(349.8, 100, 2)]));")
        got = json.loads(subprocess.run(["node", "-e", code], check=True, capture_output=True, text=True).stdout)
        self.assertAlmostEqual(got[0], m.battery_runtime(12, 100, 2, 432), places=9)
        self.assertAlmostEqual(got[1], m.battery_capacity_for(24, 432, 4), places=9)
        self.assertEqual((got[2]["volts"], got[2]["ah"], got[2]["wh"]), m.battery_bank(12, 100, 4, 2))
        self.assertAlmostEqual(got[3], m.battery_runtime(12.8, 100, 2, 223, 0.8, 0.85), places=9)
        self.assertAlmostEqual(got[4], m.charge_hours(100, 20, 0.9), places=9)
        self.assertEqual((got[5]["strings"], got[5]["total"]), m.batteries_for(349.8, 100, 2))


class CoatCalc(unittest.TestCase):
    def test_coverage(self):  # coatcalc-app/test/calc_test.dart
        self.assertAlmostEqual(m.coat_rate(10, 1), 160.4, delta=0.01)
        self.assertAlmostEqual(m.coat_gallons(1604, 10, 1), 10, places=9)
        self.assertAlmostEqual(m.coat_gallons(1604, 1, 1, 0.1), 1.1, places=9)
        self.assertEqual([m.kits(6, 3), m.kits(6.01, 3), m.kits(0, 3)], [2, 3, 0])
        self.assertEqual(js("[m.kits(6, 3), m.kits(6.01, 3), m.kits(0, 3), m.coatGallons(1604, 10, 1, 0), m.coatRate(10, 1)]"), [2, 3, 0, 10, 160.4])


class SlabCalc(unittest.TestCase):
    def test_bags(self):  # slabcalc-app/test/calc_test.dart
        self.assertEqual([m.bags_for(27, y) for _, y in m.BAGS], [45, 60, 90])
        self.assertEqual(m.order_rounded(27 * 2.26), 2.5)
        self.assertEqual(m.order_rounded(27 * 2.0), 2.0)
        self.assertEqual(m.order_rounded(1.7525 * 27), 2)
        self.assertAlmostEqual(m.slab_ft3(20, 20, 4) / 27, 4.938, delta=0.001)

    def test_rebar(self):  # 20 × 12 ft, #4 at 16 in, 3 in edge, 20 ft sticks, 40-diameter laps
        g = m.rebar_grid(20, 12, 16, 3, 20, "#4", 40)
        self.assertEqual(g["pieces"], 26)
        self.assertAlmostEqual(g["total_ft"], 10 * 19.5 + 16 * 11.5, places=9)
        self.assertAlmostEqual(g["weight_lb"], g["total_ft"] * 0.668, places=9)

    def test_js(self):
        got = js("[m.bagsFor(27, 0.6), m.bagsFor(27, 0.45), m.bagsFor(27, 0.3), m.orderRounded(27 * 2.26), m.orderRounded(1.7525 * 27), m.rebarGrid(20, 12, 16, 3, 20, '#4', 40)]")
        self.assertEqual(got[:5], [45, 60, 90, 2.5, 2])
        self.assertEqual(got[5]["pieces"], 26)
        self.assertAlmostEqual(got[5]["totalFt"], 379, places=9)
        for l, w in ((10, 10), (30, 40), (24, 36), (60, 100), (14, 20)):  # same grid in Python and JS for every spacing
            for sp in (12, 16, 18, 24):
                a, b = m.rebar_grid(l, w, sp), js(f"m.rebarGrid({l}, {w}, {sp}, 3, 20, '#4', 40)")
                self.assertEqual(a["pieces"], b["pieces"], (l, w, sp))
                self.assertAlmostEqual(a["weight_lb"], b["weightLb"], places=6)


class PoolPro(unittest.TestCase):
    def test_doses(self):  # pool-chem-app/test/chem_test.dart: per 1 ppm in 10,000 US gal
        self.assertAlmostEqual(m.chlorine_dose("liquid10", 1, 10000)[0], 12.8, delta=0.05)
        self.assertAlmostEqual(m.chlorine_dose("liquid125", 1, 10000)[0], 10.24, delta=0.05)
        self.assertAlmostEqual(m.chlorine_dose("bleach6", 1, 10000)[0], 20.79, delta=0.05)
        self.assertAlmostEqual(m.chlorine_dose("calhypo65", 1, 10000)[0], 2.05, delta=0.02)

    def test_side_effects(self):
        self.assertAlmostEqual(m.chlorine_side("dichlor", 1)[0], 0.9, delta=0.02)
        self.assertAlmostEqual(m.chlorine_side("trichlor", 1)[0], 0.6, delta=0.02)
        self.assertAlmostEqual(m.chlorine_side("calhypo65", 1)[1], 0.7, delta=0.01)
        self.assertEqual(m.chlorine_side("liquid10", 5), (0, 0))

    def test_js(self):
        litres = 10000 * 3.78541
        for key in m.CHLORINE:
            got = js(f"[m.chlorineDose('{key}', 3, {litres}), m.chlorineSide('{key}', 3)]")
            amt, unit = m.chlorine_dose(key, 3, 10000)
            if unit == "fl oz":
                self.assertAlmostEqual(got[0]["ml"] / 29.5735, amt, places=6, msg=key)
            else:
                self.assertAlmostEqual(got[0]["grams"] / 28.3495, amt, places=6, msg=key)
            self.assertAlmostEqual(got[1]["cya"], m.chlorine_side(key, 3)[0], places=9)
            self.assertAlmostEqual(got[1]["ch"], m.chlorine_side(key, 3)[1], places=9)


class Address(unittest.TestCase):
    """A slab size or a pool volume passed in the page address (calc-more.js): one page serves every size."""

    def test_slab(self):
        self.assertEqual(js("m.slabFromUrl('#20x20', '')"), [20, 20])
        self.assertEqual(js("m.slabFromUrl('', '?size=60x100')"), [60, 100])
        self.assertEqual(js("m.slabFromUrl('', '?utm=x&size=12x16&y=1')"), [12, 16])
        for bad in ("#20x", "#0x20", "#abc", "#20x20x4", "#15000-gallons", ""):
            self.assertIsNone(js(f"m.slabFromUrl({bad!r}, '')"), bad)

    def test_gallons(self):
        self.assertEqual(js("m.gallonsFromUrl('#15000-gallons', '')"), 15000)
        self.assertEqual(js("m.gallonsFromUrl('', '?gallons=7500')"), 7500)
        for bad in ("#15000", "#20x20", "#-gallons", ""):
            self.assertIsNone(js(f"m.gallonsFromUrl({bad!r}, '')"), bad)


if __name__ == "__main__":
    unittest.main()
