"""Shared pieces for the reference pages in pages_hvac.py and pages_electrical.py.

These modules never import build.py (it imports them). build.py passes itself in as `b`, so the pages use its
shell(), promo(), faq() and data without a second copy of the module being loaded.
"""
import re
from html import escape as e

import guides
import refdata

REL = "{rel}"  # build.shell() swaps this for the path back to the site root
CSS = f'<link rel="stylesheet" href="{REL}assets/ref-pages.css">'
JS = f'<script src="{REL}assets/ref-pages.js"></script>'

HVAC_NOTE = ("Reference only. Charging targets and procedures come from the equipment manufacturer's data plate and "
             "installation instructions, and local codes apply. Handling refrigerants requires EPA Section 608 certification in the US.")
ELEC_NOTE = ("Reference only. The code edition and amendments adopted where you work, the equipment's listing and the "
             "manufacturer's instructions govern. Have a licensed electrician check the installation.")


def url(b, path):
    return f"{b.BASE}/{path}".replace("/index.html", "/")


def crumbs(trail):
    """trail: [(name, path)], the last item is the page itself. build.shell() turns these crumbs into the page's
    BreadcrumbList, so the visible trail and the structured one cannot drift apart."""
    parts = [f'<a href="{REL}{p}">{e(n)}</a>' if i < len(trail) - 1 else e(n) for i, (n, p) in enumerate(trail)]
    return f'<div class="crumbs">{" › ".join(parts)}</div>'


def src(key):
    title, link = refdata.SOURCES[key]
    return f'<a href="{e(link)}" rel="noopener">{e(title)}</a>'


def byline(what):
    """Visible check date and author. `what` says what was checked against what, as HTML."""
    return (f'<p class="note byline">Checked <time datetime="{refdata.CHECKED_ISO}">{refdata.CHECKED}</time> by '
            f'{guides.AUTHOR}. {what}</p>')


def printbar(label="Print this chart"):
    return f'<p class="printbar"><button type="button" class="btn ghost" data-print>{label}</button></p>'


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap {cls}"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def facts(rows):
    """Two-column fact sheet: [(label, value html, source html or "")]."""
    body = "".join(f'<tr><th scope="row">{l}</th><td>{v}{f"<small>{s}</small>" if s else ""}</td></tr>' for l, v, s in rows)
    return f'<div class="tablewrap facts"><table><tbody>{body}</tbody></table></div>'


def related(title, links):
    items = "".join(f'<a href="{REL}{p}">{e(t)}</a>' for p, t in links)
    return f'<section class="related"><h2>{title}</h2><div class="chips">{items}</div></section>'


def person(b):
    return {"@type": "Person", "@id": b.PERSON_ID, "name": guides.AUTHOR, "url": f"{b.SITE}/"}


def article_ld(b, path, headline, desc):
    return {"@context": "https://schema.org", "@type": "TechArticle", "headline": headline, "description": desc,
            "url": url(b, path), "author": person(b), "publisher": {"@id": b.ORG_ID}, "dateModified": refdata.CHECKED_ISO, "inLanguage": "en"}


def dataset_ld(b, path, name, desc, based_on, variables):
    return {"@context": "https://schema.org", "@type": "Dataset", "name": name, "description": desc, "url": url(b, path),
            "creator": person(b), "dateModified": refdata.CHECKED_ISO, "isAccessibleForFree": True, "isBasedOn": based_on,
            "variableMeasured": [{"@type": "PropertyValue", "name": n, "unitText": u} for n, u in variables]}


def plain(html_text):
    return re.sub("<[^>]+>", "", html_text)
