#!/usr/bin/env python3
"""Tells IndexNow search engines (Bing, Yandex, Seznam, Naver) about every page in docs/sitemap.xml.
Run after a push once GitHub Pages has published it: python3 indexnow.py"""
import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "config.json").read_text())
base = cfg["base_url"].rstrip("/")
key = cfg["indexnow_key"]
urls = re.findall(r"<loc>([^<]+)</loc>", (HERE / "docs/sitemap.xml").read_text())
body = json.dumps({"host": base.split("/")[2], "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
with urllib.request.urlopen(req, timeout=30) as r:
    print(r.status, f"{len(urls)} URLs submitted")
