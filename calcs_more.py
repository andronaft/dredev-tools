"""Entry point for the hobby and trade calculator pages. build.py calls build(build module) once, before the trust
pages are written, adds HOME_CARDS to its list of calculators and SUBNAV to the category menu."""
import calcs_common
import pages_embed
import pages_hobby
import pages_trades
import trust

HOME_CARDS = pages_trades.HOME_CARDS + pages_hobby.HOME_CARDS + pages_embed.HOME_CARDS
app_promo = calcs_common.app_promo
# Categories for the menu under the header: (label, page).
SUBNAV = [
    ("Roofing", "roofing/roof-pitch-multiplier-chart.html"),
    ("Concrete", "concrete/concrete-slab-calculator.html"),
    ("Shifts", "shifts/"),
    ("Brewing", "brewing/mead-abv-calculator.html"),
    ("Hydroponics", "hydroponics/ec-to-ppm-converter.html"),
    ("Candles", "candles/fragrance-load-calculator.html"),
    ("Coffee", "coffee/espresso-ratio-calculator.html"),
    ("Knitting", "knitting/yarn-yardage-calculator.html"),
]
CHANGE = ("2026-11-13", "New", "Calculators for roofing, concrete slabs, garage floor coatings, pool chlorine and shift patterns, and for "
          "mead and cider, hydroponics, candles, espresso and knitting. Each uses the formulas of the matching Dre Dev app. "
          "Some can be embedded on other sites.")


def build(b):
    calcs_common.init(b)
    # The methodology and the changelog (trust.py) get these calculators' rows; trust.build() runs after this.
    for row in pages_trades.METHODS + pages_hobby.METHODS:
        if row not in trust.METHODS:
            trust.METHODS.append(row)
    if CHANGE not in trust.CHANGES:
        trust.CHANGES.insert(0, CHANGE)
    pages_trades.build()
    pages_hobby.build()
    pages_embed.build()  # last: it lists the calculators the pages above registered
