"""Checks on the built site (run python3 build.py first): the hobby and trade pages exist, follow the page pattern,
are in the sitemap and on the home page, and no internal link is broken."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT))
import calcs_more  # noqa: E402
import pages_hobby  # noqa: E402
import pages_trades  # noqa: E402

BASE = "https://zhukovskyi.space/calculators"
NEW_DIRS = ("brewing", "hydroponics", "candles", "coffee", "knitting", "roofing", "shifts", "concrete")
NEW_FILES = ("coating/garage-floor-epoxy-calculator.html", "pool/how-much-chlorine-to-add.html")


def new_pages():
    # index.html in these folders is a generated category hub (build_hubs), except the shifts page, which is real.
    out = [p for d in NEW_DIRS for p in sorted((SITE / d).glob("*.html")) if p.name != "index.html" or d == "shifts"]
    return out + [SITE / f for f in NEW_FILES]


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sitemap = (SITE / "sitemap.xml").read_text()
        cls.home = (SITE / "index.html").read_text()

    def test_page_count(self):
        # hobby 9, roofing 2, shifts 7, concrete 2 (slab, rebar chart), garage 1, chlorine 1
        self.assertEqual(len(new_pages()), 9 + 2 + 7 + 2 + 1 + 1)

    def test_sizes_are_rows_not_pages(self):
        """Slab sizes and pool volumes live in one table on one page each; a row's link loads the size into the calculator."""
        self.assertEqual(sorted(p.name for p in (SITE / "concrete").glob("*.html") if p.name != "index.html"),
                         ["concrete-slab-calculator.html", "rebar-size-chart.html"])
        self.assertEqual(sorted(p.name for p in (SITE / "pool").glob("*.html") if p.name != "index.html"), ["how-much-chlorine-to-add.html", "pool-chemical-calculator.html"])
        slab = (SITE / pages_trades.SLAB_PAGE).read_text()
        for l, w in pages_trades.SLABS:
            self.assertIn(f'<a id="{l}x{w}" href="#{l}x{w}">', slab)
        pool = (SITE / "pool/how-much-chlorine-to-add.html").read_text()
        for g in pages_trades.POOL_VOLUMES:
            self.assertIn(f'<a id="{g}-gallons" href="#{g}-gallons">', pool)
        garage = (SITE / "coating/garage-floor-epoxy-calculator.html").read_text()
        self.assertEqual(garage.count("Worked example:"), 3)
        for size in ("a one-car garage", "a two-car garage", "a three-car garage"):
            self.assertIn(f"Worked example: {size}", garage)
        for name in ("sitemap.xml", "index.html", "llms.txt"):
            text = (SITE / name).read_text()
            self.assertNotRegex(text, r"\d+x\d+-concrete-slab|chlorine-for-\d+")

    def test_pattern(self):
        """Quick answer, tables with a worked example, questions, author and date, a link to the app, FAQ data."""
        for p in new_pages():
            html = p.read_text()
            name = p.relative_to(SITE).as_posix()
            for needle in ('class="answer"', 'class="guide"', "Worked example", 'class="faq"', "Made and checked by <a", "methodology.html",
                           'class="promo"', '"@type": "FAQPage"', "dateModified"):
                self.assertIn(needle, html, f"{name}: {needle}")
            if name != "shifts/index.html":
                self.assertIn('class="calc card"', html, name)
                self.assertIn("assets/calc-more.js", html, name)
            self.assertNotIn("{rel}", html, name)
            self.assertEqual(html.count("<h1"), 1, name)

    def test_in_sitemap(self):
        for p in new_pages() + [SITE / "embed/index.html"]:
            url = f"{BASE}/{p.relative_to(SITE).as_posix()}".replace("/index.html", "/")
            self.assertIn(f"<loc>{url}</loc>", self.sitemap)

    def test_on_home(self):
        for path, *_ in calcs_more.HOME_CARDS:
            self.assertIn(f'href="{path.removesuffix("index.html")}"', self.home, path)
            self.assertTrue((SITE / path).exists(), path)

    def test_in_menu_methodology_and_changelog(self):
        page = (SITE / pages_trades.SLAB_PAGE).read_text()
        for label, path in calcs_more.SUBNAV:
            self.assertIn(f'href="../{path}">{label}</a>', page, label)
        method = (SITE / "methodology.html").read_text()
        for name, path, *_ in pages_trades.METHODS + pages_hobby.METHODS:
            self.assertIn(f'href="{path}">{name}</a>', method, name)
        self.assertIn(calcs_more.CHANGE[2][:60], (SITE / "changelog.html").read_text())

    def test_embed_copies(self):
        copies = [p for p in sorted((SITE / "embed").glob("*.html")) if p.name != "index.html"]
        self.assertGreaterEqual(len(copies), 4)
        index = (SITE / "embed/index.html").read_text()
        for p in copies:
            html = p.read_text()
            self.assertIn('<meta name="robots" content="noindex">', html, p.name)
            self.assertIn("Powered by", html, p.name)
            self.assertNotIn("cloudflareinsights", html, p.name)
            self.assertNotIn(f"/embed/{p.name}</loc>", self.sitemap)
            self.assertIn(f"{BASE}/embed/{p.name}", index, p.name)  # the iframe code on the embed page
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
            self.assertTrue((SITE / canonical[len(BASE) + 1:]).is_file(), p.name)  # the full page it points to
        for name in ("candle-wax", "lye", "voltage-drop", "superheat-subcooling"):  # the calc.js calculators too
            self.assertTrue((SITE / f"embed/{name}.html").is_file(), name)

    def test_embed_credit_is_branded_and_nofollow(self):
        """The line under the frame links with the brand only and rel="nofollow" (Google: widget links)."""
        import html as h
        for index in ("embed/index.html", "embed/uk/index.html"):
            code = h.unescape("".join(re.findall(r'<textarea class="embed-code"[^>]*>(.*?)</textarea>', (SITE / index).read_text(), re.S)))
            credits = re.findall(r'<p style="font-size:14px;margin:6px 0 0">(.*?)</p>', code)
            self.assertGreaterEqual(len(credits), 3, index)
            for line in credits:
                self.assertRegex(line, r'^(Calculator|Калькулятор): <a href="[^"]+" rel="nofollow">Dre Dev Tools</a>$', index)

    def test_embed_uk(self):
        """The Ukrainian widgets: bare, noindex, in Ukrainian, listed on embed/uk/, which pairs with embed/ by hreflang."""
        index = (SITE / "embed/uk/index.html").read_text()
        self.assertIn('<html lang="uk">', index)
        self.assertIn(f"<loc>{BASE}/embed/uk/</loc>", self.sitemap)
        for page in ("embed/index.html", "embed/uk/index.html"):
            text = (SITE / page).read_text()
            self.assertIn(f'<link rel="alternate" hreflang="uk" href="{BASE}/embed/uk/">', text, page)
            self.assertIn(f'<link rel="alternate" hreflang="en" href="{BASE}/embed/">', text, page)
        for name, calc in (("battery-runtime", "battery"), ("inverter-cable", "cable-uk"), ("voltage-drop", "vd-uk")):
            html = (SITE / f"embed/uk/{name}.html").read_text()
            self.assertIn('<html lang="uk">', html, name)
            self.assertIn('<meta name="robots" content="noindex">', html, name)
            self.assertIn(f'data-calc="{calc}"', html, name)
            self.assertIn('Калькулятор: <a href=', html, name)
            self.assertIn('href="../../assets/style.css', html, name)
            self.assertNotIn("cloudflareinsights", html, name)
            self.assertNotIn(f"/embed/uk/{name}.html</loc>", self.sitemap)
            self.assertIn(f"{BASE}/embed/uk/{name}.html", index, name)

    def test_embed_uk_maths(self):
        """assets/embed-uk.js: the drop equals calc.js's IEC formula, the cable is the larger of the two sizes."""
        code = ("const m=require('./assets/embed-uk.js');console.log(JSON.stringify(["
                "m.dropVolts({supply:'single',cond:'cu',mm2:2.5,metres:30,amps:16,pf:1}),"
                "m.inverterCable({volts:12,watts:1000,eff:0.85,metres:1.5,limit:2}),"
                "m.inverterCable({volts:48,watts:3000,eff:0.9,metres:1,limit:3})]))")
        vd, a, b = json.loads(subprocess.run(["node", "-e", code], cwd=ROOT, check=True, capture_output=True, text=True).stdout)
        self.assertAlmostEqual(vd, 2 * 16 * 30 * 0.0225 / 2.5)  # 8.64 V
        self.assertAlmostEqual(a["amps"], 1000 / (12 * 0.85))  # 98 A
        self.assertEqual((a["byDrop"], a["byAmps"], a["size"]), (35, 25, 35))  # drop decides; 25 mm² carries 112 A
        self.assertAlmostEqual(b["amps"], 3000 / (48 * 0.9))  # 69 A
        self.assertEqual((b["byDrop"], b["byAmps"], b["size"]), (2.5, 16, 16))  # current decides: 10 mm² is 63 A, 16 mm² 85 A

    def test_open_pt_data(self):
        """The CSV and JSON downloads hold the same cells as the PT chart pages, and the page describes them."""
        import csv
        import json
        import build
        import pages_data
        rows = list(csv.DictReader((SITE / pages_data.CSV_PATH).open()))
        data = json.loads((SITE / pages_data.JSON_PATH).read_text())
        self.assertEqual(len(rows), len(data["rows"]))
        self.assertEqual({r["refrigerant"] for r in rows}, set(build.PT))
        self.assertEqual({r["source"] for r in rows}, {s["id"] for s in data["sources"]})
        self.assertNotIn("nist-webbook", {r["source"] for r in rows})
        self.assertEqual({r["refrigerant"] for r in rows if r["source"] == "coolprop"}, set(pages_data.COOLPROP["psia"]))
        for r in rows:
            curve = build.PT[r["refrigerant"]]["bubble"]
            cell = curve["psig"][(int(r["temp_f"]) - curve["startF"]) // 5]
            want = cell if cell >= 0 else cell * build.PSI_PER_INHG
            # Computed (CoolProp) rows keep 0.01 psi; the chart cell they must match is rounded to 0.1 psi or 0.1 inHg.
            self.assertAlmostEqual(float(r["liquid_psig"]), want, delta=0.06 if r["source"] == "coolprop" else 0.006, msg=str(r))
            self.assertAlmostEqual(float(r["liquid_psia"]), float(r["liquid_psig"]) + build.ATM_PSIA, delta=0.006)
        # One printed cell end to end: the chart page and the file agree for R-410A at 40 °F.
        cell = re.search(r"<td>40</td><td>4.4</td><td>([0-9.]+)</td>", (SITE / "hvac/pt-chart/r-410a.html").read_text()).group(1)
        self.assertEqual([r["liquid_psig"] for r in rows if r["refrigerant"] == "R-410A" and r["temp_f"] == "40"], [cell])
        page = (SITE / pages_data.PATH).read_text()
        for needle in ('"@type": "Dataset"', "creativecommons.org/licenses/by/4.0/", "How to cite", f"{BASE}/{pages_data.CSV_PATH}"):
            self.assertIn(needle, page)
        self.assertIn(f"<loc>{BASE}/{pages_data.PATH}</loc>", self.sitemap)

    def test_no_broken_internal_links(self):
        broken = []
        for p in SITE.rglob("*.html"):
            for href in re.findall(r'(?:href|src)="([^"#?]+)', p.read_text()):
                if re.match(r"^(https?:|mailto:|data:|//)", href):
                    if href.startswith(BASE + "/"):
                        target = SITE / href[len(BASE) + 1:]
                    else:
                        continue
                else:
                    target = (p.parent / href).resolve()
                if target.is_dir():
                    target = target / "index.html"
                if not target.exists():
                    broken.append(f"{p.relative_to(SITE)} -> {href}")
        self.assertEqual(broken, [])

    def test_tables_name_a_source(self):
        """Every table on the new pages is followed by a note; data tables say where the numbers come from."""
        for p in new_pages():
            html = p.read_text()
            guide = html[html.index('class="guide"'):]
            tables = guide.count("<table>")
            notes = len(re.findall(r'</table></div><p class="note">', guide))
            self.assertEqual(tables, notes, p.name)

    def test_category_hubs(self):
        """Every calculator folder has an index page (a hub where there is no hand-made one), so no folder
        address answers 403, and each hub is in the sitemap and links every calculator in its folder."""
        for d in SITE.iterdir():
            if not d.is_dir() or d.name in ("assets", "img", "embed", "data") or not list(d.glob("*.html")):
                continue
            self.assertTrue((d / "index.html").exists(), d.name)
            hub = (d / "index.html").read_text()
            self.assertIn(f"<loc>{BASE}/{d.name}/</loc>", self.sitemap, d.name)
            if 'class="crumbs"><a href="../">Tools</a> › ' in hub and "<h1>" in hub and "calculators</h1>" in hub:
                for f in d.glob("*.html"):
                    if f.name != "index.html" and f"{BASE}/{d.name}/{f.name}" in self.sitemap:
                        self.assertIn(f'href="../{d.name}/{f.name}"', hub, f"{d.name}: {f.name}")


if __name__ == "__main__":
    unittest.main()
