"""The aquarium pages (pages_aquarium.py, assets/aquarium.js): the maths against published check values (the Emerson
et al. 1975 table as US EPA reprints it, the UNESCO EOS-80 check values, the TankLog app's unit tests), the live
calculator against the static tables, and the page furniture (Dataset markup, hub, sitemap, app promo, methodology).

    python3 -m unittest tests/test_aquarium.py

The run rebuilds site/ first (the same as python3 build.py).
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
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import build  # noqa: E402
import opendata  # noqa: E402
import pages_aquarium as aq  # noqa: E402

SITE = build.OUT
# US EPA, Ambient Water Quality Criteria for Ammonia – 1984 (EPA 440/5-85-001), p. 3: percent NH3, reproduced from
# Emerson et al. (1975). (temp °C, pH): percent as printed.
EPA_1984 = {(0, 6.0): 0.00827, (0, 8.0): 0.820, (5, 7.0): 0.125, (10, 7.5): 0.586, (15, 8.0): 2.67, (20, 7.0): 0.396,
            (20, 8.0): 3.82, (20, 9.0): 28.4, (25, 7.0): 0.566, (25, 8.0): 5.38, (25, 8.5): 15.3, (28, 8.5): 18.2,
            (30, 8.0): 7.46, (30, 9.0): 44.6}
# EOS-80 one-atmosphere check values (UNESCO 1981), kg/m³, as pinned by tanklog-app test/calc_test.dart.
UNESCO = {(0, 5): 999.96675, (0, 25): 997.04796, (35, 5): 1027.67547, (35, 25): 1023.34306}


def setUpModule():
    build.pages.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        build.main()


def page(path):
    return (SITE / path).read_text()


def text(h):
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


def tables(h):
    return [[[text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)] for row in re.findall(r"<tr>(.*?)</tr>", t, re.S)]
            for t in re.findall(r"<table>(.*?)</table>", h, re.S)]


def jsonld(h):
    blocks = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)]
    return [b for b in blocks if "@graph" not in b]


def js(expr):
    """Evaluates an expression against the maths exported by assets/aquarium.js (node)."""
    code = f"const m = require({json.dumps(str(REPO / 'assets/aquarium.js'))}); console.log(JSON.stringify({expr}));"
    return json.loads(subprocess.run(["node", "-e", code], check=True, capture_output=True, text=True).stdout)


class Maths(unittest.TestCase):
    def test_ammonia_reproduces_the_emerson_table(self):
        for (t, ph), printed in EPA_1984.items():
            self.assertEqual(aq.sig(100 * aq.nh3_fraction(ph, t)), f"{printed:#.3g}".rstrip("."), (t, ph))

    def test_ammonia_matches_tanklog(self):  # tanklog-app/test/calc_test.dart (which uses 273.15 K)
        self.assertAlmostEqual(aq.nh3_fraction(7, 25) * 100, 0.56, delta=0.01)
        self.assertAlmostEqual(aq.nh3_fraction(8, 25) * 100, 5.37, delta=0.03)
        self.assertAlmostEqual(aq.nh3_fraction(7, 20) * 100, 0.40, delta=0.01)
        self.assertAlmostEqual(aq.nh3_fraction(8.2, 26), 0.088, delta=0.002)

    def test_seawater_unesco_check_values(self):
        for (s, t), v in UNESCO.items():
            self.assertAlmostEqual(aq.density(s, t), v, delta=0.00001, msg=(s, t))

    def test_seawater_matches_tanklog(self):
        self.assertAlmostEqual(aq.sg(35), 1.02637, delta=0.00001)
        self.assertAlmostEqual(aq.salinity_from_sg(aq.sg(35)), 35, delta=0.001)
        self.assertAlmostEqual(aq.salinity_from_sg(1.025), 33.2, delta=0.1)
        self.assertEqual(aq.salinity_from_sg(0.99), 0)
        self.assertAlmostEqual(aq.salt_g_per_l(35) * 100, 3581.7, delta=0.1)

    def test_js_is_the_same_maths(self):
        pts = [(ph / 10, t) for ph in range(60, 91, 3) for t in range(0, 41, 5)]
        got = js(f"{json.dumps(pts)}.map(([ph, t]) => [m.pKa(t), m.nh3Fraction(ph, t)])")
        for (ph, t), (p, f) in zip(pts, got):
            self.assertAlmostEqual(p, aq.pka(t), places=12)
            self.assertAlmostEqual(f, aq.nh3_fraction(ph, t), places=12)
        sal = [s / 2 for s in range(0, 91, 7)]
        got = js(f"{json.dumps(sal)}.map((s) => [m.density(s, 25), m.sgFromSalinity(s, m.SCALES.s25), m.sgFromSalinity(s, m.SCALES.s20), "
                 f"m.sgFromSalinity(s, m.SCALES.s60f), m.saltGPerL(s)])")
        for s, row in zip(sal, got):
            want = [aq.density(s, 25), aq.sg(s, 25), aq.sg(s, 20), aq.sg(s, aq.f_to_c(60)), aq.salt_g_per_l(s)]
            for a, b in zip(row, want):
                self.assertAlmostEqual(a, b, places=9, msg=s)
        sgs = [1.0, 1.018, 1.020, 1.023, 1.025, 1.0264, 1.03]
        got = js(f"{json.dumps(sgs)}.map((v) => [m.salinityFromSg(v, 25), m.salinityFromSg(v, m.SCALES.s60f)])")
        for v, (a, b) in zip(sgs, got):
            self.assertAlmostEqual(a, aq.salinity_from_sg(v, 25), places=9)
            self.assertAlmostEqual(b, aq.salinity_from_sg(v, aq.f_to_c(60)), places=9)


class Pages(unittest.TestCase):
    def test_ammonia_chart(self):
        h = page(aq.NH3_PAGE)
        chart = tables(h)[0]
        self.assertEqual(chart[0][1:], [f"{t} °C ({t * 9 / 5 + 32:.0f} °F)" for t in aq.NH3_TEMPS])
        self.assertEqual([r[0] for r in chart[1:]], [f"{6 + i / 5:.1f}" for i in range(16)])
        col = {t: i for i, t in enumerate(aq.NH3_TEMPS, 1)}
        rows = {r[0]: r for r in chart[1:]}
        # Cells that are also in the Emerson et al. table, as printed there.
        for (t, ph), printed in EPA_1984.items():
            if t in col and f"{ph:.1f}" in rows:
                self.assertEqual(rows[f"{ph:.1f}"][col[t]], f"{printed:#.3g}".rstrip(".") + " %", (t, ph))
        kit = tables(h)[1]
        self.assertEqual(kit[0][1:], [f"Kit reads {r:g} ppm" for r in aq.READINGS])
        for r in kit[1:]:
            ph = float(r[0])
            self.assertEqual(r[1:], [f"{aq.sig(x * aq.nh3_fraction(ph, aq.KIT_T), 2)} ppm" for x in aq.READINGS])
        plain = text(h)
        self.assertIn("At 25 °C the share is 0.566 % at pH 7.0, 5.38 % at pH 8.0", plain)
        self.assertIn("Free ammonia: 1 ppm × 0.0882 = 0.088 ppm NH₃", plain)  # TankLog: free(1, pH 8.2, 26 °C) = 0.088
        self.assertIn("Web sources were read on 26 November 2026.", plain)
        self.assertIn('data-calc="nh3"', h)
        self.assertIn("assets/aquarium.js", h)

    def test_salinity_chart(self):
        h = page(aq.SALT_PAGE)
        t1, t2 = tables(h)[:2]
        r35 = next(r for r in t1 if r[0] == "35")
        self.assertEqual(r35[1:], ["1.0264", "1.0266", "1.0269", "1023.3 kg/m³", "35.8 g/L"])
        r1025 = next(r for r in t2 if r[0] == "1.025")
        self.assertEqual(r1025[1], "33.2 ppt")
        self.assertIn('data-calc="salt"', h)
        self.assertIn("A reading of 1.025 at 77 °F is 33.2 ppt", text(h))

    def test_dataset_markup(self):
        for path, key in ((aq.NH3_PAGE, "aquarium-ammonia-fraction"), (aq.SALT_PAGE, "seawater-salinity-specific-gravity")):
            h = page(path)
            types = sorted(d["@type"] for d in jsonld(h))
            self.assertEqual(types, ["Dataset", "FAQPage", "WebApplication"], path)
            ds = next(d for d in jsonld(h) if d["@type"] == "Dataset")
            self.assertEqual(ds["@id"], f"{build.BASE}/{path}#dataset")
            self.assertEqual(ds["url"], f"{build.BASE}/{path}")
            self.assertEqual(ds["license"], "https://creativecommons.org/licenses/by/4.0/")
            self.assertTrue(ds["isBasedOn"] and ds["variableMeasured"])
            self.assertIn(key, opendata.DOI)
            if not opendata.DOI[key]:  # not on Zenodo yet: no DOI, no download links that do not exist
                self.assertNotIn("identifier", ds)
                self.assertNotIn("distribution", ds)
                self.assertNotIn("zenodo", h)

    def test_doi_fills_the_markup(self):
        with mock.patch.dict(opendata.DOI, {"aquarium-ammonia-fraction": "10.5281/zenodo.1234567"}):
            d = aq.dataset_ld("aquarium-ammonia-fraction", aq.NH3_LD)
            note = aq.dataset_note("aquarium-ammonia-fraction", "x")
        self.assertEqual(d["identifier"], ["https://doi.org/10.5281/zenodo.1234567", "doi:10.5281/zenodo.1234567"])
        self.assertEqual(d["distribution"][0]["contentUrl"], "https://zenodo.org/records/1234567/files/aquarium-ammonia-fraction.csv?download=1")
        self.assertIn("https://doi.org/10.5281/zenodo.1234567", note)
        self.assertEqual(opendata.doi_props("aquarium-ammonia-fraction"), {})
        self.assertNotIn("identifier", aq.NH3_LD)

    def test_section_hub_sitemap_and_promo(self):
        hub = page("aquarium/index.html")
        sitemap = (SITE / "sitemap.xml").read_text()
        self.assertIn(f"<loc>{build.BASE}/aquarium/</loc>", sitemap)
        for path in (aq.NH3_PAGE, aq.SALT_PAGE):
            h = page(path)
            self.assertIn(f"<loc>{build.BASE}/{path}</loc>", sitemap)
            self.assertIn(f'href="../{path}"', hub)
            self.assertIn(f'href="{path}"', page("index.html"))
            self.assertIn("<h3>TankLog: Aquarium Log &amp; Dosing</h3>", h)
            self.assertIn(f'{build.CFG["developer_site"]}/apps/tanklog/', h)
            self.assertIn('href="../aquarium/"', h)  # the category menu
        methods = page("methodology.html")
        self.assertIn("Ammonia toxicity chart", methods)
        self.assertIn("Salinity to specific gravity", methods)


if __name__ == "__main__":
    unittest.main()
