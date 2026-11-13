"""Checks that the numbers on the HVAC and electrical reference pages are the ones the live calculator gives
(assets/calc.js and assets/ref-pages.js, run in Node by calc_harness.js) and the ones in the source data
(hvac-charge-app pt_data.dart and charge.dart, Calculator_for_electrical nec_tables.dart, refdata.py).
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
            self.assertIn(f'href="../../{ph.sh_path(rid)}"', h)

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


class SuperheatPages(unittest.TestCase):
    def test_examples_and_tables_match_the_live_calculator(self):
        ops, plan = [], []
        for rid, r in build.PT.items():
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
            if kind == "sh":
                self.assertEqual(value, ph.t1(x["sh"]), rid)
                self.assertIn(f"Saturation temperature at {x['p_s']} psig in the", h)
                self.assertIn(f": {sat} °F.</li>", h)
                self.assertIn(f"= {value} °F.</li>", h)
                self.assertIn(f"Result: {value} °F of superheat.", h)
                self.assertIn(f'id="p" inputmode="decimal" value="{x["p_s"]}"', h)
                self.assertIn(f'id="t" inputmode="decimal" value="{x["line_s"]}"', h)
            else:
                self.assertEqual(value, ph.t1(x["sc"]), rid)
                self.assertIn(f"Subcooling = {sat} − {x['line_l']} = {value} °F.", h)
                self.assertIn(f"Result: {value} °F of subcooling.", h)
            self.assertGreater(float(value), 0, rid)
        for rid, r in build.PT.items():
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

    def test_inline_data_is_the_pt_table(self):
        for rid, r in build.PT.items():
            h = page(ph.sh_path(rid))
            data = json.loads(re.search(r"window\.PT_DATA = (\{.*?\});window\.HVAC_EXAMPLE", h).group(1))
            self.assertEqual(data, {rid: r})
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


class Site(unittest.TestCase):
    NEW = ([ph.HUB, ph.CMP_INDEX, ph.TSH, ph.BUBBLE_DEW, ph.CHARGE_454B, pe.HUB, pe.AMPACITY_PAGE, pe.BY_DISTANCE, pe.VD_12AWG, pe.VD_3PH, pe.VD_12V]
           + [ph.sh_path(rid) for rid in build.PT] + [ph.cmp_path(a, c) for a, c in ph.PAIRS])

    def test_new_pages_exist_and_are_in_the_sitemap(self):
        sitemap = (SITE / "sitemap.xml").read_text()
        self.assertEqual(len(self.NEW), 41)
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


if __name__ == "__main__":
    unittest.main()
