# Dre Dev Tools

Free calculators for the trades (HVAC, electrical, floor coating) that promote the Dre Dev apps.

- `build.py` generates the static site into `docs/`, which GitHub Pages serves from `main:/docs`.
- PT data, screenshots and icons are read from the app repos next to this folder (`~/Desktop/mobile_sub_app/*`), so the build runs only on that machine. Commit the regenerated `docs/` after every build.
- `config.json`: site URL, store links and the beta tester group. Fill a link in, run `python3 build.py`, commit, push.
- `assets/calc.js` mirrors the apps' Dart engines (PT interpolation, voltage drop, coating coverage). Keep them in step.
