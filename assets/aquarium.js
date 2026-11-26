// Calculators for the aquarium pages built by pages_aquarium.py: free (un-ionized) ammonia and seawater salinity
// to specific gravity. The maths is the same as pages_aquarium.py, which fills the static tables, and as the open
// datasets aquarium-ammonia-fraction and seawater-salinity-specific-gravity; tests/test_aquarium.py checks all three.
(function () {
  'use strict';

  /* ---------- maths (no DOM) ---------- */

  // Emerson et al. (1975), written as US EPA prints it (1999 Update, Eq. 3; 2013 criteria, p. 7).
  const pKa = (tC) => 0.09018 + 2729.92 / (273.2 + tC);
  const nh3Fraction = (ph, tC) => 1 / (1 + Math.pow(10, pKa(tC) - ph));
  const fToC = (f) => ((f - 32) * 5) / 9;

  // EOS-80 one-atmosphere equation of state (Millero & Poisson 1981), as in tanklog-app lib/calc/dosing.dart.
  const pureWater = (t) => 999.842594 + 6.793952e-2 * t - 9.09529e-3 * t * t + 1.001685e-4 * t ** 3 - 1.120083e-6 * t ** 4 + 6.536332e-9 * t ** 5;
  function density(s, t) {
    const a = 8.24493e-1 - 4.0899e-3 * t + 7.6438e-5 * t * t - 8.2467e-7 * t ** 3 + 5.3875e-9 * t ** 4;
    const b = -5.72466e-3 + 1.0227e-4 * t - 1.6546e-6 * t * t;
    return pureWater(t) + a * s + b * s * Math.sqrt(s) + 4.8314e-4 * s * s;
  }
  // Reference temperatures of the three specific-gravity scales, °C.
  const SCALES = { s25: 25, s20: 20, s60f: fToC(60) };
  const sgFromSalinity = (s, t) => density(s, t) / pureWater(t);
  function salinityFromSg(sg, t) {
    let lo = 0, hi = 50;
    if (!(sg > sgFromSalinity(lo, t))) return 0;
    if (sg >= sgFromSalinity(hi, t)) return hi;
    for (let i = 0; i < 60; i++) {
      const mid = (lo + hi) / 2;
      if (sgFromSalinity(mid, t) < sg) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }
  const saltGPerL = (s) => (s * density(s, 25)) / 1000;
  const L_PER_GAL = 3.785411784;

  const math = { pKa, nh3Fraction, fToC, pureWater, density, SCALES, sgFromSalinity, salinityFromSg, saltGPerL, L_PER_GAL };
  if (typeof module !== 'undefined' && module.exports) { module.exports = math; return; }

  /* ---------- pages ---------- */

  const $ = (id) => document.getElementById(id);
  const num = (id) => parseFloat(String($(id).value).replace(',', '.'));
  const fix = (v, d) => v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const sig = (v, n) => (v === 0 ? '0' : Number(v.toPrecision(n)).toLocaleString('en-US', { maximumSignificantDigits: n, minimumSignificantDigits: n }));
  const set = (id, text) => { const el = $(id); if (el) el.textContent = text; };
  const big = (id, value, unit) => { $(id).innerHTML = value === '–' ? '–' : `${value}<small> ${unit}</small>`; };
  const pressed = (id) => { const b = $(id).querySelector('[aria-pressed="true"]'); return b ? b.dataset.v : ''; };
  function segmented(id, onChange) {
    $(id).querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
      $(id).querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      onChange();
    }));
  }
  const listen = (ids, run) => ids.forEach((i) => { $(i).addEventListener('input', run); $(i).addEventListener('change', run); });

  function initNh3() {
    function run() {
      const total = num('nh3-total'), ph = num('nh3-ph'), raw = num('nh3-temp');
      const f = pressed('nh3-unit') === 'f';
      set('nh3-temp-unit', f ? '(°F)' : '(°C)');
      const t = f ? fToC(raw) : raw;
      const ok = total >= 0 && ph >= 0 && ph <= 14 && t >= 0 && t <= 40 && [total, ph, t].every(Number.isFinite);
      if (!ok) {
        big('nh3-free', '–');
        ['nh3-pct', 'nh3-nh4', 'nh3-pka', 'nh3-other'].forEach((i) => set(i, '–'));
        set('nh3-note', Number.isFinite(t) && (t < 0 || t > 40) ? 'The equation is fitted for 0–40 °C (32–104 °F).' : '');
        return;
      }
      const frac = nh3Fraction(ph, t);
      big('nh3-free', sig(total * frac, 2), 'ppm NH₃');
      set('nh3-pct', `${sig(frac * 100, 3)} %`);
      set('nh3-nh4', `${sig(total * (1 - frac), 3)} ppm`);
      set('nh3-pka', fix(pKa(t), 3));
      set('nh3-other', `pH ${fix(ph - 0.2, 1)}: ${sig(total * nh3Fraction(ph - 0.2, t), 2)} ppm · pH ${fix(ph + 0.2, 1)}: ${sig(total * nh3Fraction(ph + 0.2, t), 2)} ppm`);
      set('nh3-note', t > 30 ? 'Above 30 °C the published table stops; the equation holds to 40 °C.' : '');
    }
    segmented('nh3-unit', () => {
      const f = pressed('nh3-unit') === 'f', v = num('nh3-temp');
      if (Number.isFinite(v)) $('nh3-temp').value = f ? fix(v * 9 / 5 + 32, 0) : fix(fToC(v), 1);
      run();
    });
    listen(['nh3-total', 'nh3-ph', 'nh3-temp'], run);
    run();
  }

  function initSalt() {
    function run() {
      const mode = pressed('sal-mode'), scale = $('sal-scale').value, t = SCALES[scale];
      const v = num('sal-val');
      set('sal-val-unit', mode === 'sg' ? '(specific gravity)' : '(ppt)');
      let s = NaN;
      if (mode === 'sg') s = v >= 0.99 && v <= 1.04 ? salinityFromSg(v, t) : NaN;
      else s = v >= 0 && v <= 45 ? v : NaN;
      if (!Number.isFinite(s)) {
        big('sal-main', '–');
        ['sal-25', 'sal-20', 'sal-60', 'sal-rho', 'sal-salt'].forEach((i) => set(i, '–'));
        set('sal-note', mode === 'sg' ? 'Enter a specific gravity between 0.990 and 1.040.' : 'Enter a salinity between 0 and 45 ppt.');
        return;
      }
      set('sal-note', '');
      if (mode === 'sg') big('sal-main', fix(s, 1), 'ppt'); else big('sal-main', fix(sgFromSalinity(s, t), 4), 'SG');
      set('sal-25', fix(sgFromSalinity(s, SCALES.s25), 4));
      set('sal-20', fix(sgFromSalinity(s, SCALES.s20), 4));
      set('sal-60', fix(sgFromSalinity(s, SCALES.s60f), 4));
      set('sal-rho', `${fix(density(s, 25), 1)} kg/m³`);
      const g = saltGPerL(s);
      set('sal-salt', `${fix(g, 1)} g/L · ${fix(g * L_PER_GAL, 0)} g per US gal`);
    }
    segmented('sal-mode', () => {
      const sg = pressed('sal-mode') === 'sg', v = num('sal-val'), t = SCALES[$('sal-scale').value];
      if (Number.isFinite(v)) $('sal-val').value = sg ? fix(sgFromSalinity(Math.min(Math.max(v, 0), 45), t), 3) : fix(salinityFromSg(v, t), 1);
      run();
    });
    listen(['sal-val', 'sal-scale'], run);
    run();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const init = { nh3: initNh3, salt: initSalt }[document.body.dataset.calc];
    if (init) init();
  });
})();
