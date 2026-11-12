# Dre Dev Tools

Free calculators for the trades (HVAC, electrical, floor coating) that promote the Dre Dev apps.

- `build.py` generates the static site into `site/`. It is served at https://zhukovskyi.space/calculators/: in the `my_space` repo run `python3 tools/sync_calculators.py`, then `./deploy.sh`.
- `docs/` (GitHub Pages, the old address andronaft.github.io/dredev-tools) holds only redirect pages to the new address. Commit and push it when the list of pages changes.
- PT data, screenshots and icons are read from the app repos next to this folder (`~/Desktop/mobile_sub_app/*`), so the build runs only on that machine. Commit the regenerated `site/` and `docs/` after every build.
- `config.json`: site URL, store links and the beta tester group. Fill a link in, run `python3 build.py`, commit, push.
- `assets/calc.js` mirrors the apps' Dart engines (PT interpolation, voltage drop, coating coverage). Keep them in step.
- Trust pages (`trust.py`): `methodology.html`, `verification.html` (checked examples) and `changelog.html`. Add a line to `CHANGES` in `trust.py` whenever a formula or a number changes.
- `verification.json`: rows from the sources next to the expected answer. `build.py` runs them through `assets/calc.js` (`tools/verify.mjs`, needs `node`) and stops if one is off. Change `"checked"` only after reading the sources again: that date is printed on the calculator pages.
- `lastmod.json`: hash and date of each page's content, so the sitemap's `lastmod` and `dateModified` move only when a page really changes. Commit it with `site/`.
- The apps have no pages here any more: links go to `zhukovskyi.space/apps/<slug>/`. `config.json` still decides the buttons: set `google_play_live` or `app_store_url` and the "Become a tester" button becomes a store link.
- Tests: `python3 build.py && python3 -m unittest discover tests && node --test "tests/*.test.mjs"`.
- Share image: `/usr/bin/python3 tools/og_image.py` writes `assets/og.jpg`.
