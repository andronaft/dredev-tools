"""Checks on the built site (run python3 build.py first): the hobby and trade pages exist, follow the page pattern,
are in the sitemap and on the home page, and no internal link is broken."""
import re
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
    out = [p for d in NEW_DIRS for p in sorted((SITE / d).glob("*.html"))]
    out += [SITE / f for f in NEW_FILES] + sorted((SITE / "pool").glob("chlorine-for-*.html"))
    return out


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sitemap = (SITE / "sitemap.xml").read_text()
        cls.home = (SITE / "index.html").read_text()

    def test_page_count(self):
        self.assertEqual(len(new_pages()), 9 + 2 + 7 + (1 + len(pages_trades.SLABS)) + 1 + (1 + len(pages_trades.POOL_SIZES)))

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
        page = (SITE / "concrete/20x20-concrete-slab.html").read_text()
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


if __name__ == "__main__":
    unittest.main()
