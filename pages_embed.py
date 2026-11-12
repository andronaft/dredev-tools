"""The "Embed this calculator" page: iframe code for the calculators that have a bare embed copy (calcs_common.EMBEDS)."""
from html import escape as e

import calcs_common as c

HOME_CARDS = [("embed/index.html", "For your site", "Embed a calculator", "Free iframe code for your blog or shop. No sign-up.", "")]
FEATURED = ["concrete-slab", "roof-pitch", "mead-abv", "ec-ppm"]  # shown with a live preview; the rest as code only


def snippet(name, title, height):
    return (f'<iframe src="{c.B.BASE}/embed/{name}.html" title="{e(title)}" width="100%" height="{height}" '
            f'style="border:0;max-width:720px" loading="lazy"></iframe>')


def build():
    items = sorted(c.EMBEDS, key=lambda x: (x[0] not in FEATURED, FEATURED.index(x[0]) if x[0] in FEATURED else 0, x[1]))
    blocks = []
    for name, title, path, height in items:
        code = snippet(name, title, height)
        preview = (f'<iframe src="{{rel}}embed/{name}.html" title="{e(title)} preview" height="{height}" loading="lazy"></iframe>'
                   if name in FEATURED else "")
        blocks.append(f'<div class="embed-item"><h3>{e(title)}</h3><p class="muted">Full page: <a href="{{rel}}{path}">{e(title)}</a></p>'
                      f'<textarea class="embed-code" readonly rows="4" aria-label="Embed code for {e(title)}">{e(code)}</textarea>{preview}</div>')
    faq_html, faq_ld = c.B.faq([
        ("Is it free? Do I need an account?",
         "Free, with no sign-up and no key. Copy the code and paste it into your page."),
        ("What does the embedded calculator show?",
         "Only the calculator and one small line, \"Powered by Dre Dev Tools\", that links to the full page with the charts and sources. No ads, no cookies and no analytics inside the frame."),
        ("Can I change the size?",
         "Yes. The width follows your page up to 720 px. If the calculator is cut off or leaves a gap on your layout, change the height number in the code."),
        ("Will the numbers stay up to date?",
         "Yes. The frame loads the calculator from this site, so fixes and updates reach your page without any change on your side."),
        ("Which platforms does it work on?",
         "Anywhere you can paste HTML: WordPress (Custom HTML block), Squarespace (Code block), Wix (Embed HTML), Shopify pages and plain HTML sites."),
    ])
    body = f"""
{c.CSS}
<div class="crumbs"><a href="{{rel}}index.html">Tools</a> › Embed</div>
<div class="hero"><div class="eyebrow">For blogs, shops and course sites</div><h1>Embed this calculator</h1>
<p class="lead">Put one of our calculators on your own site with one line of code. Free, no sign-up, no ads inside the frame.</p></div>
<section class="prose"><h2>How to add it</h2>
<ol><li>Pick a calculator below and copy its code.</li>
<li>Paste it into your page where the calculator should appear (an HTML or code block in your site builder).</li>
<li>Publish. If it looks cut off, change the <code>height</code> number.</li></ol>
<p>Each calculator carries a small "Powered by {e(c.B.CFG["brand"])} Tools" line. Please keep the code as it is.</p></section>
<section><h2>Calculators you can embed</h2>{"".join(blocks)}</section>
{faq_html}
<p class="note">Questions or a calculator you would like to embed that is not here: <a href="mailto:{c.B.CFG["support_email"]}">{c.B.CFG["support_email"]}</a>.</p>
"""
    c.B.shell("embed/index.html", "Embed a Free Calculator on Your Site (iframe code) | Dre Dev Tools",
              "Free embeddable calculators for your blog or shop: concrete slab, roof pitch, mead ABV, EC to ppm and more. Copy one line of iframe code, no sign-up.",
              body, "", "embed", [faq_ld], c.scripts())
