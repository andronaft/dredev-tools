"""Checks that the numbers on the HVAC and electrical reference pages are the ones the live calculator gives
(assets/calc.js and assets/ref-pages.js, run in Node by calc_harness.js) and the ones in the source data
(hvac-charge-app pt_data.dart and charge.dart, Calculator_for_electrical nec_tables.dart, refdata.py). The subpanel,
conduit fill, box fill and EV charger pages are also held to the answers of the app's own Dart engine (ENGINE_* below).
Also: every new page is in the sitemap and reachable from its section hub, no internal link is broken, JSON-LD parses.

    python3 -m unittest discover -s tests

The run rebuilds site/ and docs/ first (the same as python3 build.py).
"""
import contextlib
import html
import io
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import build  # noqa: E402
import guides  # noqa: E402
import calc_math as cm  # noqa: E402
import pages_electrical as pe  # noqa: E402
import pages_hvac as ph  # noqa: E402
import refdata  # noqa: E402

SITE = build.OUT
ATM, INHG = 14.695949, 0.4911541


def setUpModule():
    build.pages.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        build.main()


def js(ops):
    """What the site's JavaScript returns for these operations (see calc_harness.js)."""
    res = subprocess.run(["node", str(REPO / "tests/calc_harness.js")], input=json.dumps({"ops": ops}),
                         capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def page(path):
    return (SITE / path).read_text()


def text(h):
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


def tables(h):
    """Every table on a page as rows of cell texts."""
    return [[[text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)] for row in re.findall(r"<tr>(.*?)</tr>", t, re.S)]
            for t in re.findall(r"<table>(.*?)</table>", h, re.S)]


def jsonld(h, graph=False):
    """The page's own JSON-LD blocks; with graph=True, the nodes of the @graph block build.shell() adds to every page."""
    blocks = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)]
    if graph:
        return [n for blk in blocks for n in blk.get("@graph", [])]
    return [blk for blk in blocks if "@graph" not in blk]


def crumb_names(h):
    crumbs = next(n for n in jsonld(h, graph=True) if n["@type"] == "BreadcrumbList")
    return [i["name"] for i in crumbs["itemListElement"]]


def num(s):
    return float(s.replace(",", "").split()[0])


# ---------- source data, parsed here independently of build.py ----------

def dart_pt():
    """pt_data.dart cells as printed on the site: psig, or negative inches of mercury for vacuum."""
    text_ = (build.ROOT / "hvac-charge-app/lib/feature/engine/pt_data.dart").read_text()
    out = {}
    for block in text_.split("= Refrigerant(")[1:]:
        rid = re.search(r"id: '([^']+)'", block).group(1)
        out[rid] = {}
        for name in ("bubble", "dew"):
            m = re.search(name + r": PtCurve\((.*?)\]", block, re.S)
            if not m:
                continue
            head, cells = m.group(1).split("[", 1)
            vals = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", cells)]
            if "absolute: true" in head:
                vals = [round(p - ATM, 1) if p >= ATM else round(-(ATM - p) / INHG, 1) for p in vals]
            out[rid][name] = (int(re.search(r"startF: (-?\d+)", head).group(1)), vals)
    return out


def shown(p):
    return f"{abs(p):.1f}″ Hg" if p < 0 else f"{p:.1f}"


def source_cell(src, rid, phase, t):
    start, vals = src[rid].get(phase) or src[rid]["bubble"]
    return vals[(t - start) // 5]


def dart_tsh():
    text_ = (build.ROOT / "hvac-charge-app/lib/feature/engine/charge.dart").read_text()

    def axis(name):
        return [int(x) for x in re.search(name + r" = \[([\d, ]+)\]", text_).group(1).split(",")]

    grid = text_.split("superheatF = [", 1)[1].split("];", 1)[0]
    rows = [[None if x == "null" else int(x) for x in re.findall(r"null|\d+", row)] for row in re.findall(r"\[([^\[\]]+)\]", grid)]
    return axis("outdoorF"), axis("wetBulbF"), rows


def dart_nec():
    text_ = (build.ROOT / "Calculator_for_electrical/lib/feature/engine/nec_tables.dart").read_text()

    def block(name):
        body = text_.split(f"const {name} = ", 1)[1].split("};", 1)[0]
        return {int(t): [float(x) for x in vals.split(",") if x.strip()] for t, vals in re.findall(r"NecTemp\.c(\d+): \[([^\]]+)\]", body)}

    return block("_cu"), block("_al"), block("_ambient")


def dart_const(name):
    """The body of one constant of the app's nec_tables.dart."""
    text_ = (build.ROOT / "Calculator_for_electrical/lib/feature/engine/nec_tables.dart").read_text()
    return text_.split(f"const {name} = ", 1)[1].split(";", 1)[0]


def dart_fill():
    """Chapter 9 Tables 4 and 5, Table 314.16(B)(1), the metal boxes and Table 250.122 as the app holds them."""
    def num_map(name):
        return {k: float(v) for k, v in re.findall(r"'([^']+)': ([\d.]+)", dart_const(name))}

    raceway = {k: [float(x) for x in v.split(",") if x.strip()] for k, v in re.findall(r"Raceway\.(\w+): \[([^\]]+)\]", dart_const("racewayArea"))}
    boxes = [(n, float(v)) for n, v in re.findall(r"\('([^']+)', ([\d.]+)\)", dart_const("metalBoxes"))]
    egc = {int(a): (cu, al) for a, cu, al in re.findall(r"(\d+): \('([^']+)', '([^']+)'\)", dart_const("necEgc"))}
    return num_map("thhnArea"), raceway, num_map("boxVolumePerConductor"), boxes, egc


# What the app's own engine answers: cableSizeNec, necEgcFor, conduitFill and boxFill of Calculator_for_electrical
# (lib/feature/engine/sizing.dart and electrical.dart, main at 12f1339), run with dart on 16 November 2026.
# Size and voltage drop in percent at 25, 50, 75, 100, 150, 200 and 250 ft, 240 V, THHN on 75 °C terminals.
ENGINE_SUB = {
    ("cu", 50): "8 0.82, 8 1.64, 8 2.45, 6 2.06, 4 1.94, 4 2.59, 3 2.57",
    ("cu", 60): "6 0.62, 6 1.24, 6 1.85, 6 2.47, 4 2.33, 3 2.46, 2 2.44",
    ("cu", 100): "3 0.51, 3 1.03, 3 1.54, 3 2.05, 2 2.44, 1 2.58, 1/0 2.56",
    ("al", 50): "6 0.84, 6 1.69, 6 2.53, 4 2.12, 3 2.52, 2 2.67, 1 2.65",
    ("al", 60): "4 0.64, 4 1.27, 4 1.91, 4 2.55, 2 2.40, 1 2.54, 1/0 2.52",
    ("al", 100): "1 0.53, 1 1.06, 1 1.59, 1 2.12, 1/0 2.52, 2/0 2.66, 3/0 2.64",
}
ENGINE_SUB_GROUND = {50: ("10", "8"), 60: ("10", "8"), 100: ("8", "6")}  # Table 250.122: copper, aluminum
# Continuous load, copper: breaker, ground, the engine's NM-B size (60 °C column), THHN size and drop at 25 to 200 ft.
ENGINE_EV = {
    32: (40, "10", "8", "8 0.52, 8 1.05, 8 1.57, 8 2.09, 6 1.98, 6 2.63"),
    40: (50, "10", "6", "8 0.65, 8 1.31, 8 1.96, 8 2.62, 6 2.47, 4 2.07"),
    48: (60, "10", "4", "6 0.49, 6 0.99, 6 1.48, 6 1.98, 6 2.96, 4 2.48"),
    80: (100, "8", "1", "3 0.41, 3 0.82, 3 1.23, 3 1.64, 3 2.46, 2 2.60"),
}
# conduitFill().maxConductors of THHN in 1/2, 3/4, 1, 1-1/4, 1-1/2 and 2 in.
ENGINE_FILL = {
    "emt": {"14": [12, 21, 35, 61, 83, 138], "12": [9, 16, 25, 44, 61, 100], "10": [5, 10, 16, 28, 38, 63], "8": [3, 5, 9, 16, 22, 36],
            "6": [1, 4, 6, 11, 16, 26], "4": [1, 2, 4, 7, 9, 16], "3": [1, 1, 3, 6, 8, 13], "2": [1, 1, 2, 5, 7, 11],
            "1": [1, 1, 1, 3, 5, 8], "1/0": [0, 1, 1, 3, 4, 7]},
    "pvc40": {"14": [11, 20, 34, 59, 81, 135], "12": [8, 15, 25, 43, 59, 98], "10": [5, 9, 15, 27, 37, 62], "8": [3, 5, 9, 15, 21, 35],
              "6": [1, 4, 6, 11, 15, 25], "4": [1, 1, 4, 7, 9, 15], "3": [1, 1, 3, 5, 8, 13], "2": [1, 1, 2, 5, 6, 11],
              "1": [0, 1, 1, 3, 5, 8], "1/0": [0, 1, 1, 3, 4, 7]},
}
# boxFill().spare of an empty box: 14, 12 and 10 AWG conductors in each metal box of nec_tables.dart.
ENGINE_BOXES = {"3 × 2 × 2 in device": [5, 4, 4], "3 × 2 × 2½ in device": [6, 5, 5], "4 in square × 1¼ in": [9, 8, 7],
                "3 × 2 × 3½ in device": [9, 8, 7], "4 in square × 1½ in": [10, 9, 8], "4 in round/octagon × 2⅛ in": [10, 9, 8],
                "4 11/16 in square × 1¼ in": [12, 11, 10], "4 11/16 in square × 1½ in": [14, 13, 11], "4 in square × 2⅛ in": [15, 13, 12],
                "4 11/16 in square × 2⅛ in": [21, 18, 16]}
# cableSizeNec for a full 20 A and 30 A load with 1–3, 4–6, 7–9 and 10–20 current-carrying conductors, and the
# adjusted ampacity of 12 and 10 AWG THHN (90 °C column × Table 310.15(C)(1), capped at the 75 °C column).
ENGINE_DERATE = [["1–3 × 1.00", "25 A", "12 AWG", "35 A", "10 AWG"], ["4–6 × 0.80", "24 A", "12 AWG", "32 A", "10 AWG"],
                 ["7–9 × 0.70", "21 A", "12 AWG", "28 A", "8 AWG"], ["10–20 × 0.50", "15 A", "10 AWG", "20 A", "6 AWG"]]


class PtMath(unittest.TestCase):
    """pages_hvac.py's saturation maths is the same as calc.js for every refrigerant."""

    def test_python_port_matches_calc_js(self):
        ops, want = [], []
        for rid, r in build.PT.items():
            for phase in ("bubble", "dew"):
                c = ph.curve(r, phase)
                lo, hi = c["startF"], c["startF"] + 5 * (len(c["psig"]) - 1)
                for k in range(12):
                    t = lo + (hi - lo) * (k + 0.37) / 12
                    p = ph.psia_at(c, t)
                    ops.append({"op": "eval", "code": f"[psiaAt({json.dumps(c)}, {t!r}), tempAtPsia({json.dumps(c)}, {p!r})]"})
                    want.append((p, ph.temp_at_psia(c, p)))
        for (p, t), (jp, jt) in zip(want, js(ops)):
            self.assertAlmostEqual(p, jp, places=9)
            self.assertAlmostEqual(t, jt, places=9)


class PtChartPages(unittest.TestCase):
    def setUp(self):
        self.src = dart_pt()

    def test_pinned_source_cells(self):
        # Read by eye in pt_data.dart (Arkema chart rows): a guard on the parser above.
        self.assertEqual(len(self.src), 22)
        for t, want in ((-50, 5.0), (40, 118.8), (95, 296.4), (150, 613.9)):
            self.assertEqual(source_cell(self.src, "R-410A", "bubble", t), want)
        self.assertEqual(source_cell(self.src, "R-454B", "bubble", -45), 6.6)

    def test_every_table_cell_is_the_source_cell(self):
        for rid in build.PT:
            h = page(ph.pt_path(rid))
            two = "dew" in self.src[rid]
            checked = 0
            for tbl in tables(h):
                head = tbl[0]
                if head[0] not in ("°F", "Temperature"):
                    continue
                for row in tbl[1:]:
                    t = int(num(row[0]))
                    want = [shown(source_cell(self.src, rid, "bubble", t))] + ([shown(source_cell(self.src, rid, "dew", t))] if two else [])
                    self.assertEqual(row[2:], want, f"{rid} at {t} °F")
                    checked += 1
            self.assertGreater(checked, 20, rid)

    def test_typical_temperatures(self):
        for rid, r in build.PT.items():
            lo, hi = ph.trange(r)
            typ = next(t for t in tables(page(ph.pt_path(rid))) if t[0][0] == "Temperature")
            self.assertEqual([int(num(row[0])) for row in typ[1:]], [t for t in (70, 80, 90, 95, 105) if lo <= t <= hi], rid)

    def test_quick_answer_uses_source_cells(self):
        h = page(ph.pt_path("R-454B"))
        ans = text(re.search(r'<p class="answer">(.*?)</p>', h, re.S).group(1))
        for phase, t in (("bubble", 95), ("dew", 95), ("bubble", 40), ("dew", 40)):
            self.assertIn(f"{source_cell(self.src, 'R-454B', phase, t):.1f} psig", ans)

    def test_page_furniture(self):
        for rid in build.PT:
            h = page(ph.pt_path(rid))
            types = [d["@type"] for d in jsonld(h)]
            self.assertEqual(sorted(types), ["Dataset", "FAQPage"], rid)
            self.assertEqual(crumb_names(h)[2:], ["HVAC", "PT charts", f"{rid} PT Chart"], rid)
            self.assertIn(f'<time datetime="{refdata.CHECKED_ISO}">{refdata.CHECKED}</time> by {guides.AUTHOR}', h)
            self.assertIn("data-print", h)
            self.assertIn("ref-pages.css", h)
            self.assertIn("ref-pages.js", h)
            self.assertIn("equipment manufacturer", h)
            self.assertIn("local codes", h)
            # Six refrigerants have a calculator page of their own; the rest open the shared calculator on themselves.
            want = ph.sh_path(rid) if rid in ph.OWN_PAGES else f"hvac/superheat-subcooling-calculator.html#{ph.slug(rid)}"
            self.assertEqual(ph.calc_href(rid), want)
            self.assertTrue(f'href="../../{want}"' in h, rid)

    def test_facts_are_sourced(self):
        for rid in build.PT:
            rows = {r[0]: r[1] for t in tables(page(ph.pt_path(rid))) for r in t if len(r) == 2}
            h = page(ph.pt_path(rid))
            gwp, key, _ = refdata.GWP[rid]
            self.assertTrue(rows["GWP (100-year)"].startswith(gwp + " "), rid)
            self.assertIn(html.escape(refdata.SOURCES[key][1]), h)
            for label, data in (("Compressor lubricant", refdata.OIL), ("Sold as a replacement for", refdata.REPLACES),
                                ("Composition", refdata.COMPOSITION), ("Ozone depletion potential", refdata.ODP)):
                if rid in data:
                    self.assertTrue(rows[label].startswith(data[rid][0]), (rid, label))
                    self.assertIn(html.escape(refdata.SOURCES[data[rid][1]][1]), h)
                else:
                    self.assertNotIn(label, rows, f"{rid}: {label} shown without a source")
            self.assertTrue(rows["Safety class"].startswith(build.PT[rid]["safety"]), rid)

    def test_gwp_names_one_publisher_next_to_the_number(self):
        for rid in build.PT:
            rows = {r[0]: r[1] for t in tables(page(ph.pt_path(rid))) for r in t if len(r) == 2}
            self.assertRegex(rows["GWP (100-year)"], r"^[\d,.]+ per US EPA \(", rid)
            self.assertTrue(refdata.SOURCES[refdata.GWP[rid][1]][0].startswith("US EPA"), rid)

    def test_r427a_explains_the_150_f_row(self):
        # The 2025 chart prints the R-404A and R-507A cells in the R-427A row at 150 °F; the page uses the 2019 edition.
        self.assertEqual(source_cell(self.src, "R-427A", "bubble", 150), 418.9)
        self.assertEqual(source_cell(self.src, "R-427A", "dew", 150), 388.8)
        self.assertEqual(source_cell(self.src, "R-404A", "bubble", 150), 456.8)
        self.assertEqual(source_cell(self.src, "R-507A", "bubble", 150), 467.4)
        h = page(ph.pt_path("R-427A"))
        note = text(re.search(r"<p class=\"note\"><strong>Why this differs.*?</p>", h, re.S).group(0))
        for value in ("456.8", "467.4", "418.9", "388.8", "2019 edition"):
            self.assertIn(value, note)
        for key in ("arkema_pt_2019", "arkema_pt_2025"):
            self.assertIn(html.escape(refdata.SOURCES[key][1]), h)
        self.assertNotIn("Why this differs", page(ph.pt_path("R-410A")))

    def test_every_source_is_https_and_has_a_title(self):
        for key, (title, link) in refdata.SOURCES.items():
            self.assertTrue(link.startswith("https://") and len(title) > 10, key)
        used = {v[1] for d in (refdata.GWP, refdata.ODP, refdata.OIL, refdata.REPLACES, refdata.COMPOSITION) for v in d.values()}
        self.assertLessEqual(used | set(refdata.SAFETY_SOURCE.values()), set(refdata.SOURCES))


def shared_text(a, b, n=5):
    """Share of page a's words that sit in runs of n words also found on page b (main content only)."""
    def words(h):
        h = re.search(r"<main[^>]*>(.*?)</main>", h, re.S).group(1)
        h = re.sub(r"<script.*?</script>", " ", h, flags=re.S)
        return re.findall(r"[A-Za-z0-9°.\-]+", text(re.sub(r"<[^>]+>", " ", h)))

    wa, wb = words(a), words(b)
    runs = {tuple(wb[i:i + n]) for i in range(len(wb) - n + 1)}
    hit = set()
    for i in range(len(wa) - n + 1):
        if tuple(wa[i:i + n]) in runs:
            hit.update(range(i, i + n))
    return len(hit) / len(wa)


class SharedCalculator(unittest.TestCase):
    """hvac/superheat-subcooling-calculator.html: one calculator for every refrigerant."""

    def setUp(self):
        self.h = page(ph.MAIN_CALC)

    def test_every_refrigerant_is_in_the_select_and_in_the_data(self):
        select = re.search(r'<select id="ref">(.*?)</select>', self.h, re.S).group(1)
        self.assertEqual(re.findall(r'<option value="([^"]+)"', select), list(build.PT))
        data = (SITE / "assets/pt-data.js").read_text()
        self.assertEqual(json.loads(data[len("window.PT_DATA = "):].rstrip().rstrip(";")), build.PT)
        self.assertIn("assets/pt-data.js", self.h)
        self.assertIn('data-calc="hvac"', self.h)
        self.assertEqual(sorted(d["@type"] for d in jsonld(self.h)), ["FAQPage", "WebApplication"])
        self.assertEqual(crumb_names(self.h)[2:], ["HVAC", "Superheat & Subcooling Calculator"])
        self.assertIn("equipment manufacturer", self.h)

    def test_example_readings_match_the_live_calculator(self):
        shown_ = json.loads(re.search(r"window\.HVAC_EXAMPLES = (\{.*?\});", self.h).group(1))
        self.assertEqual(list(shown_), list(build.PT))
        ops = []
        for rid, r in build.PT.items():
            ex = ph.example(r)
            self.assertEqual(shown_[rid], {"sh": [ex["p_s"], ex["line_s"]], "sc": [ex["p_l"], ex["line_l"]]})
            ops.append({"op": "hvac", "rid": rid, "data": r, "mode": "sh", "p": ex["p_s"], "t": ex["line_s"]})
            ops.append({"op": "hvac", "rid": rid, "data": r, "mode": "sc", "p": ex["p_l"], "t": ex["line_l"]})
        res = js(ops)
        tbl = next(x for x in tables(self.h) if x[0][0] == "Refrigerant")
        self.assertEqual([row[0] for row in tbl[1:]], list(build.PT))
        for i, (rid, r) in enumerate(build.PT.items()):
            ex, row = ph.example(r), tbl[1 + i]
            sat_s, sat_l = (res[2 * i + k]["sat"].split(" °F")[0] for k in (0, 1))
            self.assertEqual(row[3], f"{ex['p_s']} psig → {sat_s} °F" + (" dew" if r["dew"] else ""), rid)
            self.assertEqual(row[4], f"{ex['p_l']} psig → {sat_l} °F" + (" bubble" if r["dew"] else ""), rid)
            self.assertEqual(row[2], r["safety"], rid)
            self.assertIn(f'href="#{ph.slug(rid)}"', self.h)
        # The fields start with the first refrigerant's example.
        first = ph.example(next(iter(build.PT.values())))
        self.assertIn(f'id="p" inputmode="decimal" value="{first["p_s"]}"', self.h)
        self.assertIn(f'id="t" inputmode="decimal" value="{first["line_s"]}"', self.h)

    def test_refrigerant_from_the_address(self):
        ids = json.dumps(list(build.PT))
        cases = [("#r-454b", "", "R-454B"), ("#R-1234YF", "", "R-1234yf"), ("", "?ref=R-134a", "R-134a"),
                 ("", "?x=1&ref=r-744", "R-744"), ("#r-32", "?ref=R-22", "R-32"), ("#nothing", "?ref=R-22", "R-22"),
                 ("#nothing", "", None), ("", "", None), ("#%zz", "", None)]
        res = js([{"op": "eval", "code": f"RefPages.refFromAddress({json.dumps(h)}, {json.dumps(q)}, {ids})"} for h, q, _ in cases])
        self.assertEqual(res, [want for _, _, want in cases])


class SuperheatPages(unittest.TestCase):
    """The six refrigerants with a calculator page of their own."""

    def test_only_six_refrigerants_have_a_page(self):
        self.assertEqual(ph.OWN_PAGES, ["R-410A", "R-454B", "R-32", "R-22", "R-134a", "R-404A"])
        made = sorted(f.name for f in (SITE / "hvac/superheat-calculator").iterdir())
        self.assertEqual(made, sorted(f"{ph.slug(rid)}.html" for rid in ph.OWN_PAGES))
        self.assertEqual((SITE / "sitemap.xml").read_text().count("/hvac/superheat-calculator/"), len(ph.OWN_PAGES))

    def test_examples_and_tables_match_the_live_calculator(self):
        ops, plan = [], []
        for rid in ph.OWN_PAGES:
            r = build.PT[rid]
            ex = ph.example(r)
            ops.append({"op": "hvac", "rid": rid, "data": r, "mode": "sh", "p": ex["p_s"], "t": ex["line_s"]})
            ops.append({"op": "hvac", "rid": rid, "data": r, "mode": "sc", "p": ex["p_l"], "t": ex["line_l"]})
            plan += [(rid, "sh", ex), (rid, "sc", ex)]
            for p in ph.pressure_rows(r):
                ops.append({"op": "hvac", "rid": rid, "data": r, "mode": "sh", "p": p, "t": 0})
                plan.append((rid, "row", p))
        res = js(ops)
        lookups = {}
        for (rid, kind, x), out in zip(plan, res):
            h = page(ph.sh_path(rid))
            if kind == "row":
                spans = [text(s) for s in re.findall(r"<span>(.*?)</span>", out["pt"])]
                lookups.setdefault(rid, {})[x] = dict(zip(spans[0::2], spans[1::2]))
                continue
            value = text(out["out"]).replace(" °F", "")
            sat = out["sat"].split(" °F")[0]
            answer = text(re.search(r'<p class="answer">(.*?)</p>', h, re.S).group(1))
            if kind == "sh":
                self.assertEqual(value, ph.t1(x["sh"]), rid)
                self.assertIn(f"Saturation temperature at {x['p_s']} psig in the", h)
                self.assertIn(f": {sat} °F.</li>", h)
                self.assertIn(f"= {value} °F.</li>", h)
                self.assertIn(f"Result: {value} °F of superheat.", h)
                self.assertIn(f'id="p" inputmode="decimal" value="{x["p_s"]}"', h)
                self.assertIn(f'id="t" inputmode="decimal" value="{x["line_s"]}"', h)
                self.assertIn(f"{x['p_s']} psig", answer)
                self.assertIn(f"{sat} °F", answer)
                self.assertIn(f"{value} °F", answer)
            else:
                self.assertEqual(value, ph.t1(x["sc"]), rid)
                self.assertIn(f"Subcooling = {sat} − {x['line_l']} = {value} °F.", h)
                self.assertIn(f"Result: {value} °F of subcooling.", h)
                self.assertIn(f"{x['p_l']} psig", answer)
                self.assertIn(f"{sat} °F", answer)
                self.assertIn(f"{value} °F", answer)
            self.assertGreater(float(value), 0, rid)
        for rid in ph.OWN_PAGES:
            r = build.PT[rid]
            tbl = next(t for t in tables(page(ph.sh_path(rid))) if t[0][0] == "Pressure, psig")
            self.assertGreaterEqual(len(tbl), 6, rid)
            for row in tbl[1:]:
                got = lookups[rid][int(row[0])]

                def f(name):
                    v = got[name]
                    return "–" if v == "outside the chart" else v.split(" °F")[0]

                if r["dew"]:
                    self.assertEqual(row[1:3], [f("Dew (vapour)"), f("Bubble (liquid)")], f"{rid} at {row[0]} psig")
                    if "–" not in row[1:4]:
                        self.assertAlmostEqual(float(row[3]), float(row[1]) - float(row[2]), delta=0.11)
                else:
                    self.assertEqual(row[1], f("Saturation"), f"{rid} at {row[0]} psig")
                    self.assertEqual(row[2], got["Saturation"].split("(")[1].split(" °C")[0])

    def test_typical_pressures_are_source_cells(self):
        src = dart_pt()
        for rid in ph.OWN_PAGES:
            evap, cond = ph.TYPICAL[ph.PROFILE_OF[rid]]
            typ = [t for t in tables(page(ph.sh_path(rid))) if t[0][0] == "Saturation temperature"]
            self.assertEqual(len(typ), 2, rid)
            for tbl, temps, phase, where in ((typ[0], evap, "dew", "Evaporator"), (typ[1], cond, "bubble", "Condenser")):
                self.assertEqual([row[0] for row in tbl[1:]], [f"{where} at {t} °F" for t in temps], rid)
                self.assertEqual([row[1] for row in tbl[1:]], [shown(source_cell(src, rid, phase, t)) for t in temps], rid)

    def test_text_about_the_refrigerant_matches_the_live_calculator(self):
        """Readings on another refrigerant's chart, quoted in the text written for each page."""
        quoted = {  # page: [(chart, mode, which example pressure, or a literal psig)]
            "R-410A": [("R-22", "sh", "p_s"), ("R-454B", "sh", "p_s"), ("R-32", "sh", "p_s")],
            "R-454B": [("R-454B", "sc", "p_s"), ("R-410A", "sh", "p_s")],
            "R-32": [("R-410A", "sc", "p_l")],
            "R-22": [("R-410A", "sh", "p_s"), ("R-407C", "sh", "p_s"), ("R-407C", "sc", "p_s"), ("R-427A", "sh", "p_s"), ("R-427A", "sc", "p_s")],
            "R-134a": [("R-513A", "sh", "p_s"), ("R-134a", "sh", round(-10 * INHG, 1))],
            "R-404A": [("R-448A", "sh", "p_s"), ("R-448A", "sc", "p_s"), ("R-449A", "sh", "p_s"), ("R-449A", "sc", "p_s"), ("R-507A", "sh", "p_s")],
        }
        self.assertEqual(list(quoted), ph.OWN_PAGES)
        ops, plan = [], []
        for rid, cases in quoted.items():
            ex = ph.example(build.PT[rid])
            for chart, mode, p in cases:
                p = ex[p] if isinstance(p, str) else p
                ops.append({"op": "hvac", "rid": chart, "data": build.PT[chart], "mode": mode, "p": p, "t": 0})
                plan.append((rid, chart, p))
        for (rid, chart, p), out in zip(plan, js(ops)):
            about = text(re.search(r"<h2>What is particular about.*?</section>", page(ph.sh_path(rid)), re.S).group(0))
            self.assertIn(f"{out['sat'].split(' °F')[0]} °F", about, f"{rid}: {chart} at {p} psig")
            self.assertIn(f"{p} psig" if p > 0 else f"typed as {p}", about, rid)

    def test_cells_quoted_in_the_text_are_source_cells(self):
        src = dart_pt()
        quoted = {
            "R-410A": [("R-410A", "dew", 40), ("R-22", "dew", 40), ("R-410A", "bubble", 105), ("R-22", "bubble", 105)],
            "R-454B": [("R-454B", "dew", 40), ("R-410A", "dew", 40), ("R-454B", "bubble", 105), ("R-410A", "bubble", 105)],
            "R-32": [("R-32", "dew", 40), ("R-410A", "dew", 40), ("R-32", "bubble", 105), ("R-410A", "bubble", 105), ("R-454B", "dew", 40)],
            "R-22": [("R-22", "dew", 40), ("R-22", "bubble", 105), ("R-410A", "dew", 40), ("R-410A", "bubble", 105)],
            "R-134a": [("R-134a", "bubble", -15), ("R-134a", "bubble", -20), ("R-134a", "bubble", -40), ("R-513A", "dew", 40),
                       ("R-134a", "dew", 40), ("R-513A", "bubble", 105), ("R-134a", "bubble", 105)],
            "R-404A": [("R-404A", "dew", -50), ("R-404A", "dew", -10), ("R-404A", "dew", 20)],
        }
        for rid, cells in quoted.items():
            about = text(re.search(r"<h2>What is particular about.*?</section>", page(ph.sh_path(rid)), re.S).group(0))
            for chart, phase, t in cells:
                p = source_cell(src, chart, phase, t)
                self.assertIn(f"{abs(p):.1f}″ Hg vacuum" if p < 0 else f"{p:.1f} psig", about, f"{rid}: {chart} {phase} at {t} °F")
        # R-134a crosses atmospheric pressure where the text says it does.
        self.assertEqual(source_cell(src, "R-134a", "bubble", -15), 0.0)
        self.assertLess(source_cell(src, "R-134a", "bubble", -20), 0)

    def test_facts_in_the_text_are_the_sourced_ones(self):
        for rid in ph.OWN_PAGES:
            h = page(ph.sh_path(rid))
            about = text(re.search(r"<h2>What is particular about.*?</section>", h, re.S).group(0))
            self.assertIn(f"GWP of {refdata.GWP[rid][0]}" if rid != "R-410A" else f"GWP is {refdata.GWP[rid][0]}", about, rid)
            self.assertIn(f"safety class {build.PT[rid]['safety']}", about, rid)
            self.assertIn(refdata.SOURCES[refdata.GWP[rid][1]][1], h, rid)
            self.assertIn(refdata.SOURCES[refdata.SAFETY_SOURCE[rid]][1], h, rid)
        self.assertIn(refdata.ODP["R-22"][0], page(ph.sh_path("R-22")))
        self.assertIn(refdata.SOURCES["epa_hcfc22"][1], page(ph.sh_path("R-22")))
        self.assertIn(text(refdata.COMPOSITION["R-454B"][0]), text(page(ph.sh_path("R-454B"))))
        self.assertEqual(max(ph.OWN_PAGES, key=lambda x: num(refdata.GWP[x][0])), "R-404A")

    def test_each_page_has_its_own_text(self):
        """These pages were 80 % the same text with other numbers. What they still share is the calculator's labels,
        the app banner, the site's disclaimers and the caveat about targets; the rest is written per refrigerant."""
        pages_ = {rid: page(ph.sh_path(rid)) for rid in ph.OWN_PAGES}
        heads = [re.findall(r"<h3>(.*?)</h3>", re.search(r"<h2>What is particular about.*?</section>", h, re.S).group(0)) for h in pages_.values()]
        self.assertTrue(all(len(x) >= 3 for x in heads))
        questions = [q for h in pages_.values() for q in re.findall(r"<summary>(.*?)</summary>", h)]
        own_q = [q for q in questions if q != "Where does the data come from?"]
        self.assertEqual(len(own_q), len(set(own_q)))
        self.assertGreaterEqual(len(own_q), 3 * len(pages_))
        shares = [shared_text(pages_[a], pages_[b]) for a in pages_ for b in pages_ if a != b]
        self.assertLess(max(shares), 0.65)
        self.assertLess(sum(shares) / len(shares), 0.55)

    def test_inline_data_is_the_pt_table(self):
        for rid in ph.OWN_PAGES:
            r = build.PT[rid]
            h = page(ph.sh_path(rid))
            data = json.loads(re.search(r"window\.PT_DATA = (\{.*?\});window\.HVAC_EXAMPLES", h).group(1))
            self.assertEqual(data, {rid: r})
            ex = ph.example(r)
            self.assertEqual(json.loads(re.search(r"window\.HVAC_EXAMPLES = (\{.*?\});", h).group(1)),
                             {rid: {"sh": [ex["p_s"], ex["line_s"]], "sc": [ex["p_l"], ex["line_l"]]}})
            self.assertIn('data-calc="hvac"', h)
            self.assertIn("assets/calc.js", h)
            self.assertEqual(sorted(d["@type"] for d in jsonld(h)), ["FAQPage", "WebApplication"])
            self.assertEqual(crumb_names(h)[2:4], ["HVAC", "Superheat & subcooling"], rid)
            self.assertIn("equipment manufacturer", h)

    def test_example_pressures_are_positive_gauge(self):
        for rid, r in build.PT.items():
            ex = ph.example(r)
            self.assertGreater(ex["p_s"], 0, rid)
            self.assertGreater(ex["p_l"], ex["p_s"], rid)


class Comparisons(unittest.TestCase):
    def test_tables_come_from_the_source_cells(self):
        src = dart_pt()

        def psia(p):
            return ATM + p if p >= 0 else ATM + p * INHG

        for a, c in ph.PAIRS:
            h = page(ph.cmp_path(a, c))
            cmp_tables = [t for t in tables(h) if t[0][0] == "Temperature"]
            phases = ["dew", "bubble"] if len(cmp_tables) == 2 else ["bubble"]
            for phase, tbl in zip(phases, cmp_tables):
                self.assertGreaterEqual(len(tbl), 8)
                for row in tbl[1:]:
                    t = int(num(row[0]))
                    pa, pc = source_cell(src, a, phase, t), source_cell(src, c, phase, t)
                    self.assertEqual(row[2:4], [shown(pa), shown(pc)], f"{a} vs {c} {phase} {t}")
                    self.assertEqual(row[4], f"{psia(pa) - psia(pc):+.1f}")

    def test_same_gauge_rows_match_the_live_calculator(self):
        ops, plan = [], []
        for a, c in ph.PAIRS:
            s = ph.cmp_data(build, a, c)["same"]
            for rid in (a, c):
                ops.append({"op": "hvac", "rid": rid, "data": build.PT[rid], "mode": "sh", "p": s["p_s"], "t": 0})
                ops.append({"op": "hvac", "rid": rid, "data": build.PT[rid], "mode": "sc", "p": s["p_l"], "t": 0})
            plan.append((a, c, s))
        res = iter(js(ops))
        for a, c, s in plan:
            sat = [next(res)["sat"].split(" (")[0] for _ in range(4)]  # a suction, a liquid, c suction, c liquid
            tbl = next(t for t in tables(page(ph.cmp_path(a, c))) if t[0][0] == "Reading")
            self.assertEqual(tbl[1][1:4], [f"{s['p_s']} psig", sat[0], sat[2]])
            self.assertEqual(tbl[2][1:4], [f"{s['p_l']} psig", sat[1], sat[3]])

    def test_page_furniture(self):
        idx = page(ph.CMP_INDEX)
        for a, c in ph.PAIRS:
            h = page(ph.cmp_path(a, c))
            self.assertEqual(sorted(d["@type"] for d in jsonld(h)), ["Dataset", "FAQPage"])
            self.assertEqual(crumb_names(h)[2:4], ["HVAC", "Comparisons"])
            self.assertIn("Checked <time", h)
            self.assertIn("local codes", h)
            self.assertIn(f"{ph.slug(a)}-vs-{ph.slug(c)}.html", idx)
            for rid in (a, c):  # the refrigerant's own PT page links to the comparison
                self.assertIn(f"{ph.slug(a)}-vs-{ph.slug(c)}.html", page(ph.pt_path(rid)))


class TargetSuperheat(unittest.TestCase):
    def setUp(self):
        self.od, self.wb, self.rows = dart_tsh()
        self.tbl = ph.load_tsh(build)

    def test_table_is_the_apps_table(self):
        self.assertEqual((self.tbl["outdoorF"], self.tbl["wetBulbF"], self.tbl["superheatF"]), (self.od, self.wb, self.rows))
        self.assertEqual((len(self.od), len(self.wb)), (13, 14))
        self.assertTrue(all(len(r) == 14 for r in self.rows) and len(self.rows) == 13)
        # Cells read by eye in charge.dart.
        cell = lambda o, w: self.rows[self.od.index(o)][self.wb.index(w)]  # noqa: E731
        self.assertEqual([cell(55, 50), cell(95, 66), cell(95, 68), cell(115, 76), cell(65, 50)], [9, 10, 14, 23, None])

    def test_page_shows_the_table(self):
        h = page(ph.TSH)
        grid = next(t for t in tables(h) if t[0][0].startswith("Outdoor"))
        self.assertEqual(grid[0][1:], [str(x) for x in self.wb])
        for o, row, want in zip(self.od, grid[1:], self.rows):
            self.assertEqual(row, [str(o)] + ["–" if v is None else str(v) for v in want])
        self.assertEqual(json.loads(re.search(r"window\.TSH_TABLE = (\{.*?\});</script>", h).group(1)), self.tbl)
        self.assertIn(refdata.SOURCES["bryant_tsh"][1], h)
        self.assertIn("Your unit's own charging chart", h)
        self.assertEqual(sorted(d["@type"] for d in jsonld(h)), ["Dataset", "FAQPage", "WebApplication"])

    def test_lookup_matches_ref_pages_js(self):
        points = [(o / 2, w / 4) for o in range(100, 241, 7) for w in range(190, 313, 5)]
        res = js([{"op": "tsh", "table": self.tbl, "od": o, "wb": w} for o, w in points])
        kinds = set()
        for (o, w), got in zip(points, res):
            kind, v = ph.tsh_lookup(self.tbl, o, w)
            kinds.add(kind)
            self.assertEqual(got["kind"], kind, (o, w))
            if kind == "value":
                self.assertAlmostEqual(got["value"], v, places=9)
        self.assertEqual(kinds, {"value", "none", "range"})

    def test_worked_example_and_quick_answer(self):
        h = page(ph.TSH)
        o, w = ph.TSH_EXAMPLE
        got = js([{"op": "tsh", "table": self.tbl, "od": o, "wb": w}, {"op": "tsh", "table": self.tbl, "od": 95, "wb": 66},
                  {"op": "tsh", "table": self.tbl, "od": 85, "wb": 66}])
        self.assertIn(f"gives {got[0]['value']:.1f} °F.", h)
        self.assertIn(f'id="tsh-od" inputmode="decimal" value="{o}"', h)
        self.assertIn(f"target superheat of {got[1]['value']:.0f} °F; at 85 °F outdoors", text(h))
        self.assertIn(f"and the same wet bulb, {got[2]['value']:.0f} °F", " ".join(text(h).split()))


class Guides(unittest.TestCase):
    def test_r454b_article(self):
        h = page(ph.CHARGE_454B)
        r = build.PT["R-454B"]
        ex = ph.example(r)
        out = js([{"op": "hvac", "rid": "R-454B", "data": r, "mode": "sc", "p": ex["p_l"], "t": ex["line_l"]}])[0]
        self.assertIn(f"= {text(out['out']).replace(' °F', '')} °F.</li>", h)
        self.assertIn(out["sat"].split(" °F")[0] + " °F", h)
        self.assertIn("The target is on the equipment, not on this page.", h)
        self.assertIn("rating plate", h)
        for key in ("carrier_ph5", "lennox_ml13", "carrier_llg", "chemours_pt", "york_yh9"):
            self.assertIn(html.escape(refdata.SOURCES[key][1]), h)
        self.assertEqual(sorted(d["@type"] for d in jsonld(h)), ["FAQPage", "TechArticle"])

    def test_bubble_dew_guide(self):
        h = page(ph.BUBBLE_DEW)
        r = build.PT["R-407C"]
        ex = ph.example(r)
        out = js([{"op": "hvac", "rid": "R-407C", "data": r, "mode": "sh", "p": ex["p_s"], "t": ex["line_s"], "ptin": ex["p_s"]}])[0]
        spans = [text(s) for s in re.findall(r"<span>(.*?)</span>", out["pt"])]
        both = dict(zip(spans[0::2], spans[1::2]))
        self.assertIn(f"Vapor (dew) column at {ex['p_s']} psig: {both['Dew (vapour)'].split(' °F')[0]} °F.", h)
        self.assertIn(f"reads {both['Bubble (liquid)'].split(' °F')[0]} °F, which is the wrong value here", h)
        glide = next(t for t in tables(h) if t[0][0] == "Refrigerant")
        self.assertEqual([row[0] for row in glide[1:]], [rid for rid, rr in build.PT.items() if rr["dew"]])
        for row in glide[1:]:
            g = ph.glide(build.PT[row[0]])
            self.assertEqual(row[1:], ["–" if x is None else f"{x:.1f}" for x in g])
            self.assertTrue(all(x is None or 0 < x < 20 for x in g), row)


class Electrical(unittest.TestCase):
    def test_ampacity_chart_matches_calc_js_and_the_app(self):
        cu, al, ambient = dart_nec()
        amp, sizes = [json.loads(x) for x in js([{"op": "eval", "code": "JSON.stringify(AMPACITY)"}, {"op": "eval", "code": "JSON.stringify(NEC_SIZES)"}])]
        h = page(pe.AMPACITY_PAGE)
        chart = next(t for t in tables(h) if t[0][0] == "Size")
        self.assertEqual(len(chart) - 1, len(sizes))
        for i, row in enumerate(chart[1:]):
            self.assertEqual(row[0], guides.awg(sizes[i]))
            want_js = [amp[c][t][i] for c in ("cu", "al") for t in ("60", "75", "90")]
            want_app = [int(d[t][i]) for d in (cu, al) for t in (60, 75, 90)]
            self.assertEqual(want_js, want_app, sizes[i])
            self.assertEqual(row[1:], [str(v) if v else "–" for v in want_js], sizes[i])
        # A few cells of Table 310.16 pinned by hand.
        cell = lambda size, col: chart[1 + sizes.index(size)][col]  # noqa: E731
        self.assertEqual([cell("12", 2), cell("6", 2), cell("4/0", 2), cell("500", 3), cell("2", 5), cell("14", 4)], ["25", "65", "230", "430", "90", "–"])
        amb = next(t for t in tables(h) if t[0][0] == "Ambient temperature")
        for i, row in enumerate(amb[1:]):
            self.assertEqual(row[1:], [f"{ambient[t][i]:.2f}" if ambient[t][i] else "–" for t in (60, 75, 90)])
        adj = next(t for t in tables(h) if t[0][0] == "Current-carrying conductors")
        self.assertEqual(adj[1:], [["4–6", "0.80"], ["7–9", "0.70"], ["10–20", "0.50"], ["21–30", "0.45"], ["31–40", "0.40"], ["41+", "0.35"]])
        self.assertIn("NFPA 70, National Electrical Code, 2023 edition", h)
        self.assertTrue("30 × 0.91 × 0.80 = 21.8 A." in h)  # 12 AWG at 90 °C, 36–40 °C ambient, 4–6 conductors

    def test_wire_size_by_distance_matches_the_live_calculator(self):
        combos = [(120, "cu"), (240, "cu"), (240, "al")]
        ops = [{"op": "wire", "amps": a, "len": ft, "volts": v, "cond": c} for v, c in combos for a in pe.DIST_LOADS for ft in pe.DIST_FEET]
        res = iter(js(ops))
        charts = [t for t in tables(page(pe.BY_DISTANCE)) if t[0][0].startswith("Load")]
        self.assertEqual(len(charts), 3)
        for chart in charts:
            self.assertEqual(chart[0][1:], [f"{ft} ft" for ft in pe.DIST_FEET])
            for row in chart[1:]:
                for cell in row[1:]:
                    got = text(next(res)["size"]).replace(" copper", "").replace(" aluminum", "")
                    want = "> 500" if got == "no size fits" else got.replace(" AWG", "")
                    self.assertEqual(cell, want, row[0])

    def test_wire_size_example(self):
        got = js([{"op": "wire", "amps": 30, "len": 150, "volts": 240}])[0]
        h = page(pe.BY_DISTANCE)
        self.assertIn(f"Result: {text(got['size']).replace(' copper', '')} copper for 30 A at 150 ft on 240 V.", h)
        self.assertIn(got["drop"].split(" %")[0] + " %. Under 3 %.", h)

    def test_12_awg_page_matches_the_live_calculator(self):
        h = page(pe.VD_12AWG)
        loads, feet = [5, 10, 15, 20], [25, 50, 75, 100, 150, 200]
        res = iter(js([{"op": "vd", "amps": a, "size": "12 AWG", "len": ft, "volts": 120} for a in loads for ft in feet]))
        chart = next(t for t in tables(h) if t[0][0].startswith("Load"))
        for row in chart[1:]:
            for cell in row[1:]:
                got = next(res)
                self.assertEqual(cell.split(" (")[0], got["v"])
                self.assertAlmostEqual(float(cell.split("(")[1].split(" %")[0]), num(text(got["pct"])), delta=0.051)
        sizes = ["14", "12", "10", "8", "6", "4", "2"]
        per = js([{"op": "eval", "code": f"dropVolts({{supply:'single',cond:'{c}',mm2:NEC.find((x) => x[0] === '{s}')[1] * MM2_PER_CMIL,metres:0.3048,amps:1,iec:false,pf:1}})"}
                  for s in sizes for c in ("cu", "al")])
        tbl = next(t for t in tables(h) if t[0][0] == "Wire")
        for i, row in enumerate(tbl[1:]):
            self.assertEqual(row[1], f"{per[2 * i] * 1000:.3f}")
            if row[2] != "–":
                self.assertEqual(row[2], f"{per[2 * i + 1] * 1000:.3f}")
        self.assertIn(f"{per[2] * 1000:.2f} mV per amp per foot", text(h))
        # One method on the page: the K it names is the K behind its numbers (12 AWG is 6,530 cmil).
        self.assertAlmostEqual(2 * pe.K_CU / 6530, per[2], places=12)
        self.assertIn(f"K = {pe.K_CU:.2f} Ω·cmil/ft for copper", text(h))
        self.assertIn(f"2 × {pe.K_CU:.3f} ÷ 6,530 = {per[2] * 1000:.3f} mV per amp per foot", text(h))
        self.assertNotIn("K = 12.9 ", text(h))

    def test_three_phase_lengths_reach_three_percent(self):
        h = page(pe.VD_3PH)
        tbl = next(t for t in tables(h) if t[0][0] == "Wire")
        ops, n = [], 0
        for row in tbl[1:]:
            for cell, volts, cond in zip(row[2:], (208, 240, 480, 480), ("cu", "cu", "cu", "al")):
                if cell != "–":
                    ops.append({"op": "vd", "supply": "three", "cond": cond, "amps": num(row[1]), "size": row[0], "len": num(cell), "volts": volts})
        for got in js(ops):
            self.assertAlmostEqual(num(text(got["pct"])), 3.0, delta=0.05)
            n += 1
        self.assertGreater(n, 30)
        got = js([{"op": "vd", "supply": "three", "amps": 40, "size": "8 AWG", "len": 250, "volts": 480}])[0]
        self.assertIn(f"gives {got['v'].split()[0]} V line to line, which is {text(got['pct']).split()[0]} % of 480 V", h)

    def test_12v_dc_charts_match_calc_js(self):
        h = page(pe.VD_12V)
        charts = [t for t in tables(h) if t[0][0].startswith("Current")]
        self.assertEqual(len(charts), 2)
        ops = [{"op": "eval", "code": "(sizesFor('nec').find((x) => dropVolts({supply:'dc',cond:'cu',mm2:x.mm2,metres:%s*0.3048,amps:%s,iec:false,pf:1}) / 12 * 100 <= %s) || {label:'> 500'}).label" % (ft, a, lim)}
               for lim in (3, 10) for a in pe.DC_AMPS for ft in pe.DC_FEET]
        res = iter(js(ops))
        for chart in charts:
            for row in chart[1:]:
                for cell in row[1:]:
                    self.assertEqual(cell, next(res).replace(" AWG", ""))
        # The 3 % chart is also what the calculator's own "smallest size for ≤ 3 %" row shows.
        got = js([{"op": "vd", "supply": "dc", "amps": 20, "size": "14 AWG", "len": 15, "volts": 12}])[0]
        self.assertIn(f"has to be {got['min']}:", h)
        self.assertIn(f"drop {got['v']}, which is", h)

    def test_dc_wire_calculator_matches_calc_js(self):
        h = page(pe.DC_WIRE)
        self.assertIn('data-calc="dcwire"', h)
        self.assertEqual(crumb_names(h)[2], "Electrical")
        cases = ([(v, pe.DC_EX_WATTS / v, pe.DC_EX_FEET) for v in pe.DC_SYSTEMS]
                 + [(pe.PV_EX_VMP * n, pe.PV_EX_AMPS, pe.PV_EX_FEET) for n in (1, 2, 4)]
                 + [(12, 2, 10), (12, 500, 10), (48, 30, 5)])  # under 14 AWG by drop, nothing fits, ampacity governs
        code = "JSON.stringify(dcWire({volts:%r,amps:%r,metres:%r*0.3048,cond:'cu',limit:3}))"
        for (v, a, ft), raw in zip(cases, js([{"op": "eval", "code": code % c} for c in cases])):
            got, mine = json.loads(raw), pe.dc_wire(v, a, ft)
            if mine is None:
                self.assertIsNone(got["size"], (v, a, ft))
                continue
            size, by_drop, by_amps, dv = mine
            self.assertEqual((got["size"], got["byDrop"], got["byAmps"]), tuple(guides.awg(x) for x in (size, by_drop, by_amps)), (v, a, ft))
            self.assertAlmostEqual(got["dv"], dv, places=9)
            self.assertLessEqual(got["pct"], 3)
            self.assertGreaterEqual(got["rated"], a)
        for v, a, ft in cases[:6]:  # the rows printed on the page
            size, _, _, dv = pe.dc_wire(v, a, ft)
            self.assertIn(f"<td>{guides.awg(size)}</td><td>{dv:.2f} V ({dv / v * 100:.2f} %)</td><td>{dv * a:.1f} W</td>", h)
        self.assertEqual(pe.dc_wire(12, 2, 10)[:3], ("14", "18", "14"))
        size, by_drop, by_amps, _ = pe.dc_wire(48, 30, 5)
        self.assertEqual((size, by_amps), ("10", "10"))
        self.assertLess(pe.ALL_SIZES.index(by_drop), pe.ALL_SIZES.index(by_amps))
        # The voltage drop calculator and the 12 V chart send DC readers here.
        self.assertIn("dc-wire-size-calculator.html", page(pe.VD_CALC))
        self.assertIn("dc-wire-size-calculator.html", page(pe.VD_12V))

    def test_page_furniture(self):
        for path in (pe.AMPACITY_PAGE, pe.BY_DISTANCE, pe.VD_12AWG, pe.VD_3PH, pe.VD_12V):
            h = page(path)
            types = [d["@type"] for d in jsonld(h)]
            self.assertEqual(crumb_names(h)[2], "Electrical", path)
            self.assertIn("FAQPage", types)
            self.assertIn("Checked <time", h)
            self.assertIn("data-print", h)
            self.assertIn("amendments adopted where you work", h)
            self.assertIn("manufacturer's instructions", h)


class AppTablePages(unittest.TestCase):
    """Subpanel feeders, conduit fill, box fill and EV chargers: every number is the app engine's (the ENGINE_* values
    above), the wire sizes are also the live calculator's, and the tables are the cells of nec_tables.dart."""
    PAGES = (pe.SUBPANEL, pe.FILL_CHART, pe.FILL_12_EMT, pe.BOX_FILL, pe.EV_WIRE)

    def run_charts(self, path, loads, feet, conds, cont):
        """The length charts of a page as {(cond, amps): 'size pct, ...'}, checked cell by cell against calc.js."""
        charts = [t for t in tables(page(path)) if t[0][0] == "One-way length"]
        self.assertEqual(len(charts), len(conds))
        res = iter(js([{"op": "wire", "amps": a, "len": ft, "volts": 240, "cond": c, "cont": cont} for c in conds for ft in feet for a in loads]))
        out = {}
        for cond, chart in zip(conds, charts):
            self.assertEqual(chart[0][1:], [f"{a} A" for a in loads])
            self.assertEqual([r[0] for r in chart[1:]], [f"{ft} ft" for ft in feet])
            for row in chart[1:]:
                for amps, cell in zip(loads, row[1:]):
                    got = next(res)
                    size, pct = re.fullmatch(r"(\S+) AWG (\d\.\d\d) %", cell).groups()
                    self.assertEqual(f"{size} AWG", text(got["size"]).replace(" copper", "").replace(" aluminum", ""), (path, cond, amps, row[0]))
                    self.assertEqual(got["drop"], f"{pct} % with {size} AWG", (path, cond, amps, row[0]))
                    out.setdefault((cond, amps), []).append(f"{size} {pct}")
        return {k: ", ".join(v) for k, v in out.items()}

    def test_subpanel_chart_is_the_engine_and_the_live_calculator(self):
        self.assertEqual(self.run_charts(pe.SUBPANEL, pe.SUB_FEEDERS, pe.SUB_FEET, ("cu", "al"), False), ENGINE_SUB)
        h = page(pe.SUBPANEL)
        grounds = next(t for t in tables(h) if t[0][0] == "Feeder breaker")
        self.assertEqual(grounds[1:], [[f"{a} A", f"{cu} AWG", f"{al} AWG"] for a, (cu, al) in ENGINE_SUB_GROUND.items()])
        egc = dart_fill()[4]
        self.assertEqual((egc[60], egc[100]), (("10", "8"), ("8", "6")))
        plain = text(h)
        self.assertIn("a 50 amp subpanel needs 8 AWG copper or 6 AWG aluminum feeder conductors", plain)
        self.assertIn("up to 75 ft one way; at 100 ft use 6 AWG copper or 4 AWG aluminum", plain)
        self.assertIn("The feeder has four conductors: two hots, a neutral and a ground.", plain)
        # Worked example, 60 A at 150 ft: 6 AWG by ampacity, 4 AWG for the drop, and the engine's 250.122(B) ground.
        got = js([{"op": "wire", "amps": 60, "len": 150, "volts": 240}])[0]
        self.assertEqual((text(got["size"]), got["amp"].split(" · ")[0]), ("4 AWG copper", "6 AWG"))
        self.assertIn("Next size up, 4 AWG: 5.59 V, or 2.33 %. Under 3 %.", plain)
        self.assertIn("250.122(B) increases the ground in the same proportion: 6 AWG.", plain)
        # NM-B at the 60 °C column, as the engine sizes it: 6 AWG for 50 A, 4 AWG for 60 A.
        nmb = js([{"op": "wire", "amps": a, "wire": "nmb"} for a in (50, 60)])
        self.assertEqual([text(r["size"]) for r in nmb], ["6 AWG copper", "4 AWG copper"])
        self.assertIn("On NM-B a 50 A feeder needs 6 AWG copper and a 60 A feeder 4 AWG.", plain)

    def test_ev_charger_charts_are_the_engine_and_the_live_calculator(self):
        charts = self.run_charts(pe.EV_WIRE, pe.EV_AMPS, pe.EV_FEET, ("cu",), True)
        self.assertEqual(charts, {("cu", a): v[3] for a, v in ENGINE_EV.items()})
        h = page(pe.EV_WIRE)
        summary = next(t for t in tables(h) if t[0][0].startswith("Charger current"))
        live = js([{"op": "wire", "amps": a, "cont": True, "wire": w} for a in pe.EV_AMPS for w in ("thhn", "nmb")])
        for i, (row, amps) in enumerate(zip(summary[1:], pe.EV_AMPS)):
            ocpd, ground, nmb, runs = ENGINE_EV[amps]
            # NM-B is not made above 2 AWG: where the engine answers 1 AWG, the page says so instead.
            want_nmb = f"{nmb} AWG" if nmb in guides.NMB_MADE else "–"
            self.assertEqual(row, [f"{amps} A {amps * 240 / 1000:.1f} kW", f"{ocpd} A", runs.split()[0] + " AWG", want_nmb, f"{ground} AWG"], amps)
            self.assertEqual((live[2 * i]["ocpd"], text(live[2 * i]["size"])), (row[1], row[2] + " copper"))
            self.assertEqual(text(live[2 * i + 1]["size"]), f"{nmb} AWG copper")
        plain = text(h)
        self.assertIn("48 A charger: 60 A breaker and 6 AWG copper for runs up to 150 ft.", plain)
        self.assertIn("where 6 AWG is 55 A: less than the 60 A a 48 A charger needs, so NM-B has to be 4 AWG", plain)
        self.assertIn("Next size up, 4 AWG: 2.48 %. Under 3 %.", plain)
        self.assertIn("250.122(B) increases it to 6 AWG.", plain)  # the engine's ground for 6 AWG upsized to 4 AWG on 60 A

    def table1_count(self, wire, area):
        """Chapter 9 Table 1 worked out here, apart from calc_math.py: 53 % for one conductor, 31 % for two, 40 % above."""
        n = 0
        while (0.53 if n == 0 else 0.31 if n == 1 else 0.40) * area >= (n + 1) * wire:
            n += 1
        return n

    def test_conduit_fill_chart_is_the_engine_and_the_apps_tables(self):
        thhn, raceway, _, _, _ = dart_fill()
        h = page(pe.FILL_CHART)
        charts = [t for t in tables(h) if t[0][0].startswith("Wire")]
        self.assertEqual(len(charts), 2)
        stars = 0
        for (kind, want), chart in zip(ENGINE_FILL.items(), charts):
            self.assertEqual(chart[0][1:], ["½", "¾", "1", "1¼", "1½", "2"])
            self.assertEqual([r[0] for r in chart[1:]], [guides.awg(s) for s in want])
            for row, size in zip(chart[1:], want):
                for i, cell in enumerate(row[1:]):
                    n, mark = int(cell.rstrip("*†")), cell.lstrip("0123456789")
                    area = raceway[kind][i]
                    self.assertEqual(n, want[size][i], (kind, size, i))
                    self.assertEqual(n, self.table1_count(thhn[size], area), (kind, size, i))
                    exact = 0.40 * area / thhn[size]
                    self.assertEqual(mark, "*" if n >= 2 and exact - n >= 0.8 - 1e-9 else "†" if n == 1 and exact >= 2 else "", (kind, size, i))
                    stars += mark == "*"
        self.assertEqual(stars, 22)
        # The app's own unit test (nec_test.dart): nine 12 AWG and twelve 14 AWG in 1/2 in. EMT.
        emt = charts[0]
        self.assertEqual((emt[2][1], emt[1][1]), ("9", "12"))
        areas = next(t for t in tables(h) if t[0][0] == "Trade size")
        for i, row in enumerate(areas[1:]):
            e_, p_ = raceway["emt"][i], raceway["pvc40"][i]
            self.assertEqual(row[1:], [f"{e_:.3f}", f"{e_ * 0.4:.4f}", f"{p_:.3f}", f"{p_ * 0.4:.4f}"])
        wires = next(t for t in tables(h) if t[0][0].startswith("THHN"))
        self.assertEqual(wires[1:], [[guides.awg(s), f"{thhn[s]:.4f}"] for s in ENGINE_FILL["emt"]])
        # Pinned by hand from Chapter 9 Tables 4 and 5 as the app holds them.
        self.assertEqual((thhn["12"], thhn["10"], raceway["emt"][:2], raceway["pvc40"][:2]), (0.0133, 0.0211, [0.304, 0.533], [0.285, 0.508]))
        plain = text(h)
        self.assertIn("0.2132 ÷ 0.0133 = 16.03.", plain)
        self.assertIn("3 × 0.0211 + 0.0133 = 0.0766 in².", plain)  # test/conduit_fill_test.dart
        self.assertIn("Result: 25.2 % fill, within the 40 % limit.", plain)
        self.assertIn("53 % fill for one conductor, 31 % for two, 40 % for more than two", plain)
        self.assertIn("This chart rounds down, as the Electrician Calc app does.", plain)
        self.assertNotIn("RMC", plain)  # the app has no rigid metal conduit table, so the page has no RMC chart

    def test_12_awg_in_emt_counts_and_derating(self):
        thhn, raceway, _, _, _ = dart_fill()
        h = page(pe.FILL_12_EMT)
        counts = next(t for t in tables(h) if t[0][0] == "THHN wire")
        self.assertEqual(counts[1:], [[f"{s} AWG"] + [str(n) for n in ENGINE_FILL["emt"][s][:2]] for s in ("12", "10")])
        self.assertEqual(counts[1:], [["12 AWG", "9", "16"], ["10 AWG", "5", "10"]])
        derate = next(t for t in tables(h) if t[0][0].startswith("Current-carrying wires"))
        self.assertEqual(derate[1:], ENGINE_DERATE)
        plain = text(h)
        self.assertIn("16 THHN conductors of 12 AWG fit in ¾ in. EMT at the 40 % fill limit, and 9 fit in ½ in. EMT.", plain)
        self.assertIn("For 10 AWG THHN it is 10 and 5", plain)
        self.assertIn("stays good for 20 A circuits up to 9 current-carrying conductors, and from 10 up the circuits need 10 AWG", plain)
        self.assertIn("Why other sites give a smaller number:", plain)
        # Five circuits: ten 10 AWG and a 12 AWG ground against 3/4 and 1 in. EMT; four circuits: nine 12 AWG.
        five = 10 * thhn["10"] + thhn["12"]
        self.assertIn(f"= {five:.4f} in². In ¾ in. EMT (0.533 in²) that is {five / raceway['emt'][1] * 100:.1f} %, over the 40 % limit; "
                      f"in 1 in. EMT (0.864 in²) it is {five / raceway['emt'][2] * 100:.1f} %.", plain)
        self.assertIn("that is 42.1 %, over the 40 % limit", plain)
        self.assertIn(f"fill ¾ in. EMT to {9 * thhn['12'] / raceway['emt'][1] * 100:.1f} %.", plain)

    def test_box_fill_is_the_engine_and_the_apps_tables(self):
        _, _, volume, boxes, _ = dart_fill()
        h = page(pe.BOX_FILL)
        per = next(t for t in tables(h) if t[0][0] == "Conductor size")
        self.assertEqual(per[1:], [[f"{s} AWG", f"{v:.2f} in³"] for s, v in volume.items()])
        # Table 314.16(B)(1) pinned by hand.
        self.assertEqual(per[1:], [["18 AWG", "1.50 in³"], ["16 AWG", "1.75 in³"], ["14 AWG", "2.00 in³"], ["12 AWG", "2.25 in³"],
                                   ["10 AWG", "2.50 in³"], ["8 AWG", "3.00 in³"], ["6 AWG", "5.00 in³"]])
        cap = next(t for t in tables(h) if t[0][0] == "Metal box")
        self.assertEqual(cap[1:], [[name, f"{v:g} in³"] + [str(n) for n in ENGINE_BOXES[name]] for name, v in boxes])
        counts = next(t for t in tables(h) if t[0][0] == "What is in the box")
        self.assertEqual([r[1] for r in counts[1:]], ["1", "1", "0", "1", "1", "2", "1", "¼"])
        plain = text(h)
        # The app's unit test (customer_voice_test.dart): 8 allowances, 18 in³. Engine run: 12.25 allowances, 27.5625 in³.
        self.assertIn("Total: 4 + 1 + 2 + 1 = 8 allowances.", plain)
        self.assertIn("8 × 2.25 = 18 in³.", plain)
        self.assertIn("The smallest standard metal box is a 4 in square × 1¼ in box (18 in³).", plain)
        self.assertIn("Total: 10 + 1 + 1¼ = 12.25 allowances. 12.25 × 2.25 = 27.56 in³.", plain)
        self.assertIn("The smallest standard metal box is a 4 11/16 in square × 1½ in box (29.5 in³).", plain)
        self.assertIn("needs 12.25 allowances (27.56 in³) where an older guide says 12 (27 in³)", plain)
        self.assertIn("takes 9 conductors of 12 AWG", plain)  # 21 in³: the app's unit test

    def test_page_furniture(self):
        for path in self.PAGES:
            h = page(path)
            self.assertEqual(crumb_names(h)[2], "Electrical", path)
            self.assertIn("FAQPage", [d["@type"] for d in jsonld(h)], path)
            self.assertIn('Checked <time datetime="2026-11-16">16 November 2026</time>', h, path)
            self.assertIn("NFPA 70, National Electrical Code, 2023 edition", h, path)
            self.assertIn("data-print", h)
            self.assertIn("amendments adopted where you work", h)
            # One line on what the app adds, under the answer, with the store buttons build.py generates.
            self.assertEqual(h.count("<!-- app:electrician-calc -->"), 1, path)
            line = h.split('<div class="appline">', 1)[1].split("</div>", 1)[0] + "</div>"
            self.assertLess(h.index('class="answer"'), h.index('<div class="appline">'), path)
            self.assertLess(h.index('<div class="appline">'), h.index("<table>"), path)
            self.assertIn(build.CFG["apps"]["electrician-calc"]["app_store_url"], line, path)
            self.assertIn("play.google.com/store/apps/details?id=com.andrii.electriccalc", line, path)
        # What is free and what is Pro (catalog.dart on the app's main, read on 16 November 2026).
        self.assertIn("Conduit Fill is free.", page(pe.FILL_CHART))
        self.assertIn("The Panel Planner, which assigns a panel's circuits to breakers and wire sizes, is in Pro.", page(pe.SUBPANEL))
        self.assertIn("The EV Charger &amp; Heat Pump Check (Pro)", page(pe.EV_WIRE))


class Site(unittest.TestCase):
    NEW = ([ph.HUB, ph.CMP_INDEX, ph.TSH, ph.BUBBLE_DEW, ph.CHARGE_454B, pe.HUB, pe.AMPACITY_PAGE, pe.BY_DISTANCE, pe.VD_12AWG, pe.VD_3PH, pe.VD_12V]
           + list(AppTablePages.PAGES) + [ph.sh_path(rid) for rid in ph.OWN_PAGES] + [ph.cmp_path(a, c) for a, c in ph.PAIRS])

    def test_new_pages_exist_and_are_in_the_sitemap(self):
        sitemap = (SITE / "sitemap.xml").read_text()
        self.assertEqual(len(self.NEW), 30)
        for path in self.NEW + [ph.pt_path(rid) for rid in build.PT]:
            self.assertTrue((SITE / path).exists(), path)
            self.assertIn(f"<loc>{build.BASE}/{path}</loc>".replace("/index.html<", "/<"), sitemap)

    def test_section_navigation_reaches_every_new_page(self):
        hvac_hub, elec_hub, cmp_idx = page(ph.HUB), page(pe.HUB), page(ph.CMP_INDEX)
        for path in self.NEW:
            if path in (ph.HUB, pe.HUB):
                continue
            hub = elec_hub if path.startswith("electrical/") else hvac_hub
            link = path.removesuffix("index.html")
            self.assertTrue(f'href="../{link}"' in hub or f'href="../../{link}"' in cmp_idx, path)
        # ...and the hubs are reachable from pages that already existed: every PT chart links to the HVAC hub.
        self.assertIn('href="../../hvac/"', page(ph.pt_path("R-410A")))
        for path in (pe.AMPACITY_PAGE, pe.VD_12V):
            self.assertIn('href="../electrical/"', page(path))
        # The menu under the header goes to the two hubs on every page.
        home = page("index.html")
        self.assertIn('href="hvac/"', home)
        self.assertIn('href="electrical/"', home)

    def test_no_broken_internal_links(self):
        broken = []
        for f in SITE.rglob("*.html"):
            for link in re.findall(r'(?:href|src)="([^"]+)"', f.read_text()):
                if re.match(r"(https?:|mailto:|data:|#|//)", link):
                    continue
                target = (f.parent / link.split("#")[0].split("?")[0]).resolve()
                if target.is_dir():
                    target = target / "index.html"
                if not target.exists():
                    broken.append(f"{f.relative_to(SITE)} -> {link}")
        self.assertEqual(broken, [])

    def test_json_ld_parses_everywhere(self):
        for f in SITE.rglob("*.html"):
            h = f.read_text()
            for block in jsonld(h) + jsonld(h, graph=True):
                self.assertIn("@type", block, f)

    def test_cards_point_at_real_pages(self):
        for path, _, title, desc, _ in ph.CARDS + pe.CARDS:
            self.assertTrue((SITE / path).exists() and title and desc, path)


class NecByState(unittest.TestCase):
    """The NEC edition table is the app's state_code.dart (origin/main), row for row."""

    def test_every_state_is_a_row_with_the_apps_edition(self):
        rows = pe.state_codes(build)
        self.assertEqual(len(rows), 52)  # 50 states, DC and Puerto Rico
        chart = next(t for t in tables(page(pe.NEC_BY_STATE)) if t[0][0] == "State" and t[0][1] == "NEC edition in force")
        self.assertEqual([r[0] for r in chart[1:]], [r["name"] for r in rows])
        for r, row in zip(rows, chart[1:]):
            want = f"NEC {r['edition']}" if r["edition"] else ("Not confirmed" if r["unconfirmed"] else "No statewide edition")
            self.assertEqual(row[1], want, r["name"])
            self.assertEqual(row[2], r["effective"] or "—", r["name"])

    def test_the_states_named_in_the_answers_are_the_ones_in_the_table(self):
        rows = pe.state_codes(build)
        self.assertEqual([r["code"] for r in rows if not r["edition"] and not r["unconfirmed"]], ["AZ", "IL", "KS", "MS", "MO"])
        h = page(pe.NEC_BY_STATE)
        self.assertIn(pe.names([r for r in rows if r["edition"] == 2026]), h)
        self.assertIn("Dataset", h)
        self.assertIn("FAQPage", h)
        self.assertIn(pe.NFPA_MAP, h)

    def test_most_common_edition_names_every_edition_in_a_tie(self):
        from collections import Counter
        self.assertEqual(pe.leaders(Counter({2023: 18, 2020: 17, 2026: 6})), ([2023], 18, [2026, 2020]))
        self.assertEqual(pe.leaders(Counter({2020: 17, 2023: 17, 2026: 7})), ([2023, 2020], 17, [2026]))
        self.assertEqual(pe.eds([2023, 2020]), "NEC 2023 and NEC 2020")
        rows = pe.state_codes(build)
        lead, n, _ = pe.leaders(Counter(r["edition"] for r in rows if r["edition"]))
        h = page(pe.NEC_BY_STATE)
        if len(lead) > 1:
            self.assertIn(f"{pe.eds(lead)} are tied as the most common statewide editions, each in force in {n} states", h)
            self.assertNotIn("is the most common statewide edition", h)
        else:
            self.assertIn(f"NEC {lead[0]} is the most common statewide edition, in force in {n} states", h)



class BatteryUk(unittest.TestCase):
    """The Ukrainian battery and UPS runtime page: metric, sourced, reachable, and its numbers are calc_math.py's."""

    def setUp(self):
        self.h = page(pe.BATTERY_UK)

    def test_language_and_place(self):
        self.assertIn('<html lang="uk">', self.h)
        self.assertIn('data-calc="battery"', self.h)
        self.assertRegex(self.h, r'assets/battery-uk\.js\?v=[0-9a-f]+"></script>')  # content hash since PR #12
        self.assertNotIn("{rel}", self.h)
        self.assertIn(f"<loc>{build.BASE}/{pe.BATTERY_UK}</loc>", (SITE / "sitemap.xml").read_text())
        self.assertIn('href="../electrical/uk/battery-runtime.html"', page(pe.HUB))
        for ld in jsonld(self.h):
            self.assertEqual(ld["inLanguage"], "uk", ld["@type"])
        self.assertEqual({ld["@type"] for ld in jsonld(self.h)}, {"WebApplication", "FAQPage"})
        self.assertEqual(len(jsonld(self.h)[1]["mainEntity"]), 4)

    def test_no_imperial_units(self):
        body = text(self.h.split("<main", 1)[1].split("</main>", 1)[0])
        for unit in ("AWG", " ft", "°F", "gallon", "inch"):
            self.assertNotIn(unit, body, unit)

    def test_every_factor_has_a_source_and_a_date(self):
        method = self.h.split('id="method"', 1)[1].split("</section>", 1)[0]
        for _, link in pe.BATTERY_SRC.values():
            self.assertIn(f'href="{html.escape(link)}"', method, link)
        self.assertEqual(method.count(f"перевірено {pe.BATTERY_CHECKED[0]}"), len(pe.BATTERY_SRC))
        self.assertIn("інструкціями до своїх акумуляторів та інвертора", method)

    def test_example_and_table_use_calc_math(self):
        t = cm.battery_runtime(12, 100, 2, 223, pe.AGM_DOD, pe.INV_EFF)
        self.assertIn(pe.ua_hm(t), self.h)
        self.assertIn(f"{pe.ua(cm.charge_hours(100, 20, pe.AGM_CE), 1)} год", self.h)
        rows = next(t for t in tables(self.h) if t[0][0] == "Банк")
        self.assertEqual(rows[2][2:], [f"{pe.ua(cm.battery_runtime(12, 100, 2, w, 0.5, 0.85), 1)} год" for w in (50, 100, 200, 300, 500, 1000)])

    def test_cta(self):
        utm = "utm_source=site&amp;utm_medium=calculator&amp;utm_campaign=ua-backup"
        self.assertIn('href="https://play.google.com/store/apps/details?id=com.andrii.electriccalc&amp;referrer=utm_source%3Dsite%26utm_medium%3Dcalculator%26utm_campaign%3Dua-backup"', self.h)
        self.assertIn(f'href="https://zhukovskyi.space/apps/electrician-calc/?{utm}"', self.h)
        self.assertIn("Battery &amp; UPS Runtime", self.h)
        self.assertIn("Знайшли помилку? Напишіть мені", self.h)

    def test_presets_are_editable_defaults(self):
        for name, w in pe.BATTERY_PRESETS:
            self.assertIn(f'data-w="{w}">+ {html.escape(name)} {w} Вт</button>', self.h)
        self.assertIn("Потужності орієнтовні", self.h)


if __name__ == "__main__":
    unittest.main()
