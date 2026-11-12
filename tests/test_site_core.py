"""Checks of the site shell: store buttons, clean links, structured data, lastmod, and the built site/ itself.

    python3 build.py && python3 -m unittest discover tests -v
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

SITE = HERE / "site"
# embed/<name>.html are bare calculators for iframes on other sites (pages_embed.py): no shell, noindex, not in the sitemap.
PAGES = sorted(p for p in SITE.rglob("*.html") if p.name != "404.html" and not (p.parent.name == "embed" and p.name != "index.html"))


def rel(p):
    return p.relative_to(SITE).as_posix()


def graph(text):
    """The shared @graph of a page: {type: node}."""
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
        data = json.loads(raw)
        if "@graph" in data:
            return {n["@type"]: n for n in data["@graph"]}
    return {}


class StoreButtons(unittest.TestCase):
    """config.json decides what the app button says: a store link once the app is live, the tester page before."""

    def setUp(self):
        self.saved = copy.deepcopy(build.CFG["apps"]["hvac-charge"])

    def tearDown(self):
        build.CFG["apps"]["hvac-charge"] = self.saved

    def test_closed_test_sends_people_to_the_tester_page(self):
        html = build.store_buttons("hvac-charge", "t")
        self.assertIn("Become a tester, free", html)
        self.assertIn('href="https://zhukovskyi.space/apps/hvac-charge/"', html)
        self.assertNotIn("play.google.com/store", html)

    def test_google_play_live_switches_to_the_store_link(self):
        build.CFG["apps"]["hvac-charge"]["google_play_live"] = True
        html = build.store_buttons("hvac-charge", "pt-r-454b")
        self.assertIn("Get it on Google Play", html)
        self.assertIn("https://play.google.com/store/apps/details?id=com.andrii.hvaccharge", html)
        self.assertIn("utm_campaign%3Dpt-r-454b", html)
        self.assertNotIn("Become a tester", html)
        self.assertNotIn("coming soon", html)

    def test_app_store_url_adds_the_app_store_button(self):
        build.CFG["apps"]["hvac-charge"]["app_store_url"] = "https://apps.apple.com/app/id123456789"
        html = build.store_buttons("hvac-charge", "t")
        self.assertIn('href="https://apps.apple.com/app/id123456789">Download on the App Store', html)
        self.assertNotIn("Become a tester", html)

    def test_live_app_on_the_site(self):
        # Electrician Calc is on the App Store in config.json today: its calculator pages must link there.
        html = (SITE / "electrical/voltage-drop-calculator.html").read_text()
        self.assertIn(build.CFG["apps"]["electrician-calc"]["app_store_url"], html)


class Shell(unittest.TestCase):
    def test_index_links_are_rewritten(self):
        self.assertEqual(build.clean_links('<a href="../index.html">x</a>'), '<a href="../">x</a>')
        self.assertEqual(build.clean_links('<a href="index.html#apps">x</a>'), '<a href="./#apps">x</a>')
        self.assertEqual(build.clean_links('<a href="../hvac/pt-chart/index.html">x</a>'), '<a href="../hvac/pt-chart/">x</a>')
        self.assertEqual(build.clean_links('<a href="https://example.com/index.html">x</a>'), '<a href="https://example.com/index.html">x</a>')
        self.assertEqual(build.clean_links('<a href="reindex.html">x</a>'), '<a href="reindex.html">x</a>')

    def test_breadcrumbs_follow_the_visible_crumbs(self):
        body = '<div class="crumbs"><a href="../">Tools</a> › <a href="../hvac/x.html">HVAC</a> › PT charts</div><h1>R-32 PT <b>Chart</b></h1>'
        ld = build.breadcrumb_ld("hvac/pt-chart/r-32.html", f"{build.BASE}/hvac/pt-chart/r-32.html", body.replace("../", "../../"), "t")
        got = [(i["position"], i["name"], i["item"]) for i in ld["itemListElement"]]
        self.assertEqual(got, [
            (1, "Home", "https://zhukovskyi.space/"),
            (2, "Free tools", "https://zhukovskyi.space/calculators/"),
            (3, "HVAC", "https://zhukovskyi.space/calculators/hvac/x.html"),
            (4, "R-32 PT Chart", "https://zhukovskyi.space/calculators/hvac/pt-chart/r-32.html")])

    def test_lastmod_moves_only_when_the_content_changes(self):
        saved, today = copy.deepcopy(build.LASTMOD), build.TODAY
        try:
            url = "https://example.test/page.html"
            build.TODAY = "2026-01-01"
            self.assertEqual(build.lastmod(url, "title", "body"), "2026-01-01")
            build.TODAY = "2026-02-02"
            self.assertEqual(build.lastmod(url, "title", "body"), "2026-01-01")   # same content, a later build
            self.assertEqual(build.lastmod(url, "title", "body!"), "2026-02-02")  # the text changed
        finally:
            build.LASTMOD.clear()
            build.LASTMOD.update(saved)
            build.TODAY = today
            build.page_dates.pop("https://example.test/page.html", None)


class BuiltSite(unittest.TestCase):
    """Reads site/ as built by `python3 build.py`."""

    @classmethod
    def setUpClass(cls):
        cls.html = {rel(p): p.read_text() for p in PAGES}

    def test_no_links_to_index_html(self):
        bad = [f"{name}: {m}" for name, text in self.html.items() for m in re.findall(r'href="[^"]*index\.html[^"]*"', text)]
        self.assertEqual(bad, [])

    def test_internal_links_resolve(self):
        missing = []
        for name, text in self.html.items():
            page = f"{build.BASE}/{name}"
            for href in re.findall(r'(?:href|src)="([^"]+)"', text):
                if href.startswith(("mailto:", "data:", "#", "tel:")):
                    continue
                target = urljoin(page, href).split("#")[0].split("?")[0]
                if not target.startswith(build.BASE + "/"):
                    continue
                path = SITE / target[len(build.BASE) + 1:]
                if not (path.is_file() or (path / "index.html").is_file()):
                    missing.append(f"{name} -> {href}")
        self.assertEqual(missing, [])

    def test_every_page_has_the_shared_head_and_graph(self):
        for name, text in self.html.items():
            with self.subTest(page=name):
                self.assertEqual(len(re.findall(r'<link rel="canonical"', text)), 1)
                self.assertIn(f'<meta property="og:image" content="{build.BASE}/assets/og.jpg">', text)
                self.assertIn('<meta name="twitter:card" content="summary_large_image">', text)
                g = graph(text)
                self.assertEqual(g["Organization"]["@id"], "https://zhukovskyi.space/#dredev")
                self.assertEqual(g["Person"]["@id"], "https://zhukovskyi.space/#person")
                crumbs = g["BreadcrumbList"]["itemListElement"]
                self.assertEqual([c["position"] for c in crumbs], list(range(1, len(crumbs) + 1)))
                self.assertRegex((g.get("WebPage") or g["CollectionPage"])["dateModified"], r"^\d{4}-\d\d-\d\d$")
                self.assertNotIn(build.LASTMOD_TOKEN, text)
        self.assertTrue((SITE / "assets/og.jpg").is_file())

    def test_index_pages_carry_the_full_publisher_record(self):
        for name in ("index.html", "hvac/pt-chart/index.html"):
            org = graph(self.html[name])["Organization"]
            self.assertEqual(org["sameAs"], build.CFG["same_as"])
            self.assertEqual(org["founder"], {"@id": "https://zhukovskyi.space/#person"})

    def test_calculator_pages_have_one_disclaimer_and_the_trust_links(self):
        for name, text in self.html.items():
            with self.subTest(page=name):
                plain = name in {"index.html", *build.TRUST_PAGES} or 'data-calc="xmas"' in text
                self.assertEqual(text.count('class="note disclaimer"'), 0 if plain else 1)
                self.assertIn("Found an error? Tell me", text)
                for page in build.TRUST_PAGES - {name}:
                    self.assertRegex(text, rf'href="(\.\./)*{page}"')
                self.assertIn('href="https://zhukovskyi.space/about/"', text)
                self.assertIn('href="https://zhukovskyi.space/privacy/"', text)

    def test_app_banner_only_where_an_app_store_app_is_promoted(self):
        with_banner = {name for name, text in self.html.items() if 'name="apple-itunes-app"' in text}
        for name in with_banner:
            self.assertIn("app-id=6830185126", self.html[name])
            self.assertIn("<!-- app:electrician-calc -->", self.html[name])
        self.assertIn("electrical/voltage-drop-calculator.html", with_banner)
        self.assertNotIn("hvac/superheat-subcooling-calculator.html", with_banner)
        self.assertNotIn("index.html", with_banner)

    def test_no_app_pages_and_old_addresses_forward(self):
        self.assertFalse((SITE / "apps").exists())
        stub = (HERE / "docs/apps/hvac-charge.html").read_text()
        self.assertIn('<link rel="canonical" href="https://zhukovskyi.space/apps/hvac-charge/">', stub)
        stub = (HERE / "docs/apps/leben-in-deutschland.html").read_text()
        self.assertIn('<link rel="canonical" href="https://zhukovskyi.space/apps/lid-test/uk/">', stub)

    def test_sitemap_lists_every_page_with_its_own_lastmod(self):
        xml = (SITE / "sitemap.xml").read_text()
        entries = dict(re.findall(r"<url><loc>([^<]+)</loc><lastmod>(\d{4}-\d\d-\d\d)</lastmod></url>", xml))
        want = {f"{build.BASE}/{name}".replace("/index.html", "/") for name in self.html}
        self.assertEqual(set(entries), want)
        stored = json.loads((HERE / "lastmod.json").read_text())
        self.assertEqual(entries, {u: v["date"] for u, v in stored.items()})

    def test_robots_names_the_search_bots(self):
        robots = (SITE / "robots.txt").read_text()
        for bot in ("OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Bingbot"):
            self.assertIn(f"User-agent: {bot}\n", robots)
        self.assertNotIn("Disallow", robots)

    def test_lye_calculator_has_its_oils(self):
        oils = json.loads(re.search(r"window\.OILS = (\[.*?\]);", self.html["soap/lye-calculator.html"]).group(1))
        self.assertEqual(len(oils), len(build.LYE_OILS))


if __name__ == "__main__":
    unittest.main()
