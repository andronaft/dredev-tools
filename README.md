# Dre Dev Tools

Free calculators for the trades (HVAC, electrical, floor coating) that promote the Dre Dev apps.

- `build.py` generates the static site into `site/`. It is served at https://zhukovskyi.space/calculators/: in the `my_space` repo run `python3 tools/sync_calculators.py`, then `./deploy.sh`.
- `docs/` (GitHub Pages, the old address andronaft.github.io/dredev-tools) holds only redirect pages to the new address. Commit and push it when the list of pages changes.
- PT data, screenshots and icons are read from the app repos next to this folder (`~/Desktop/mobile_sub_app/*`), so the build runs only on that machine. Commit the regenerated `site/` and `docs/` after every build.
- `config.json`: site URL, store links and the beta tester group. Fill a link in, run `python3 build.py`, commit, push.
- `assets/calc.js` mirrors the apps' Dart engines (PT interpolation, voltage drop, coating coverage). Keep them in step.
