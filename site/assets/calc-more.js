// Calculators for the hobby and trade pages built by pages_hobby.py and pages_trades.py.
// The maths mirrors the apps' Dart engines (the file is named above each block) and calc_math.py, which fills the
// static tables on the same pages. tests/test_calc_more.js checks both against the apps' control values.
(function () {
  'use strict';

  /* ---------- maths (no DOM) ---------- */

  const ceilCount = (v) => (Number.isFinite(v) && v > 0 ? Math.ceil(v - 1e-9) : 0);

  // Ferment: ferment-app/lib/calc/gravity.dart, sugar.dart
  const HONEY_PPG = 35;
  const L_PER_GAL = 3.785411784;
  const KG_PER_LB = 0.45359237;
  const degreesToSg = (d) => 1 + d / (258.6 - (d / 258.2) * 227.1);
  const sgToDegrees = (sg) => -616.868 + 1111.14 * sg - 630.272 * sg * sg + 135.997 * sg * sg * sg;
  const abvStandard = (og, fg) => (og - fg) * 131.25;
  const abvAlternate = (og, fg) => ((76.08 * (og - fg)) / (1.775 - og)) * (fg / 0.794);
  const attenuation = (og, fg) => (og <= 1 ? 0 : ((og - fg) / (og - 1)) * 100);
  const honeyPoints = (lb, gal) => (gal <= 0 ? 0 : (HONEY_PPG * lb) / gal);
  const honeyLbFor = (points, gal) => (points <= 0 ? 0 : (points * gal) / HONEY_PPG);

  // GrowLab: growlab-app/lib/feature/calc.dart EcScale (ppm shown per 1 mS/cm)
  const EC_SCALES = { ms: 1, us: 1000, ppm500: 500, ppm640: 640, ppm700: 700 };
  const toEc = (shown, scale) => shown / EC_SCALES[scale];
  const fromEc = (ec, scale) => ec * EC_SCALES[scale];

  // WickCalc: wickcalc-app/lib/feature/calc.dart
  const WAX_FACTOR = 0.86;
  const fillFromWater = (water, factor) => Math.max(0, water) * factor;
  function candleSplit(fill, loadPct, ofWax) {
    const f = Math.min(Math.max(loadPct, 0), 100) / 100;
    if (ofWax) { const wax = fill / (1 + f); return [wax, fill - wax]; }
    return [fill - fill * f, fill * f];
  }
  const convertLoad = (pct, fromWax) => 100 * (fromWax ? pct / 100 / (1 + pct / 100) : pct / 100 / (1 - pct / 100));

  // RoofCalc: roofcalc-app/lib/feature/roof.dart
  const BUNDLE_SQFT = 100 / 3;
  const pitchFactor = (rise) => Math.sqrt(144 + rise * rise) / 12;
  const hipFactor = (rise) => Math.sqrt(288 + rise * rise) / 12;
  const pitchDegrees = (rise) => (Math.atan(rise / 12) * 180) / Math.PI;
  function roof(planSqft, rise, waste) {
    const area = planSqft * pitchFactor(rise);
    return { area, squares: area / 100, bundles: ceilCount((area * (1 + Math.max(0, waste))) / BUNDLE_SQFT) };
  }

  // Dial In: dialin-coffee-app/lib/feature/models.dart, dial_in.dart
  const brewRatio = (dose, out) => (dose <= 0 ? 0 : out / dose);
  const shotStyle = (ratio) => (ratio <= 1.5 ? 'ristretto' : ratio <= 2.5 ? 'normale' : 'lungo');

  // RowKeeper: rowcounter-app/lib/feature/yarn_math.dart
  const M_PER_YD = 0.9144;
  function skeinsNeeded(lengthNeeded, skeinLength, extraPct) {
    const needed = lengthNeeded * (1 + extraPct / 100);
    const exact = skeinLength <= 0 ? 0 : needed / skeinLength;
    return { needed, skeins: exact > 0 ? Math.ceil(exact - 1e-9) : 0 };
  }
  const swatchYarn = (sw, sh, swatchLen, width, length) => (sw * sh <= 0 ? 0 : (swatchLen * width * length) / (sw * sh));
  const lengthFromWeight = (labelWeight, labelLength, weight) => (labelWeight <= 0 ? 0 : (weight * labelLength) / labelWeight);
  const gaugeCount = (per4, inches) => Math.floor((per4 / 4) * inches + 0.5);

  // ShiftWise: shift-calendar-app/lib/feature/patterns.dart, rota.dart (cycle day = days since the start mod length)
  const dayNumber = (y, m, d) => Math.round(Date.UTC(y, m, d) / 86400000);
  const cycleDay = (start, day, n) => (((day - start) % n) + n) % n;
  function yearStats(cycle, year, start, hours) {
    const n = cycle.length;
    const first = dayNumber(year, 0, 1);
    const last = dayNumber(year + 1, 0, 1);
    let shifts = 0, off = 0, total = 0, weekends = 0;
    for (let d = first; d < last; d++) {
      const c = cycle[cycleDay(start, d, n)];
      if (c === 'O') {
        off++;
        // 1 January 1970 was a Thursday: day number 2 is a Saturday.
        if ((((d - 2) % 7) + 7) % 7 === 0 && d + 1 < last && cycle[cycleDay(start, d + 1, n)] === 'O') weekends++;
      } else { shifts++; total += hours[c]; }
    }
    return { shifts, off, hours: total, weekends };
  }

  // CoatCalc: coatcalc-app/lib/feature/calc.dart
  const SQFT_PER_GAL_1MIL = 1604;
  const coatGallons = (sqft, mils, solids, waste) => ((sqft * mils) / (SQFT_PER_GAL_1MIL * solids)) * (1 + waste);
  const coatRate = (mils, solids) => (SQFT_PER_GAL_1MIL * solids) / mils;
  const kits = (gal, kit) => (kit > 0 ? ceilCount(gal / kit) : 0);

  // SlabCalc: slabcalc-app/lib/feature/calc.dart
  const BAGS = [['80 lb', 0.6], ['60 lb', 0.45], ['40 lb', 0.3]];
  const REBAR = { '#3': [0.375, 0.376], '#4': [0.5, 0.668], '#5': [0.625, 1.043] };
  const slabFt3 = (l, w, thickIn, extraPct) => ((l * w * thickIn) / 12) * (1 + extraPct / 100);
  const bagsFor = (ft3, yieldFt3) => ceilCount(ft3 / yieldFt3);
  const orderRounded = (ft3) => ceilCount((ft3 / 27) * 4) / 4;
  function piecesFor(runs, run, stock, lap) {
    if (runs <= 0 || run <= 0 || stock <= 0) return [0, 0];
    if (run <= stock + 1e-9) return [ceilCount(runs / Math.floor(stock / run + 1e-9)), 0];
    if (stock <= lap) return [0, 0];
    const perRun = ceilCount((run - lap) / (stock - lap));
    const last = run - (perRun - 1) * (stock - lap);
    return [runs * (perRun - 1) + ceilCount(runs / Math.floor(stock / last + 1e-9)), perRun - 1];
  }
  function rebarGrid(length, width, spacingIn, edgeIn, stock, bar, lapDiameters) {
    const [dia, lbFt] = REBAR[bar];
    const spacing = spacingIn / 12, edge = edgeIn / 12, lap = (lapDiameters * dia) / 12;
    const longBar = Math.max(length, width) - 2 * edge, shortBar = Math.min(length, width) - 2 * edge;
    if (!(longBar > 0) || !(shortBar > 0) || !(spacing > 0)) return null;
    const barsLong = ceilCount(shortBar / spacing) + 1;
    const barsShort = ceilCount(longBar / spacing) + 1;
    const [a, aLaps] = piecesFor(barsLong, longBar, stock, lap);
    const [b, bLaps] = piecesFor(barsShort, shortBar, stock, lap);
    const total = barsLong * (longBar + aLaps * lap) + barsShort * (shortBar + bLaps * lap);
    return { barsLong, barsShort, pieces: a + b, totalFt: total, weightLb: total * lbFt };
  }

  // PoolPro: pool-chem-app/lib/feature/chem/products.dart, dosing.dart
  const MW = { cl2: 70.906, naocl: 74.44, cya: 129.07, caco3: 100.09 };
  const bleachGpl = (pct) => (pct * 10 * (1.0174 + 0.01003 * pct) * MW.cl2) / MW.naocl;
  const CHLORINE = {
    liquid10: { name: 'Liquid chlorine 10 %', kind: 'liquid', v: 100 },
    liquid125: { name: 'Liquid chlorine 12.5 %', kind: 'liquid', v: 125 },
    bleach6: { name: 'Bleach 6 %', kind: 'liquid', v: bleachGpl(6) },
    bleach825: { name: 'Bleach 8.25 %', kind: 'liquid', v: bleachGpl(8.25) },
    calhypo65: { name: 'Cal-hypo 65 %', kind: 'calhypo', v: 0.65 },
    calhypo73: { name: 'Cal-hypo 73 %', kind: 'calhypo', v: 0.73 },
    dichlor: { name: 'Dichlor 56 %', kind: 'dichlor', v: 0.56 },
    trichlor: { name: 'Trichlor 90 %', kind: 'trichlor', v: 0.9 },
  };
  // Millilitres of a liquid or grams of a dry product that raise FC by ppm in litres of water.
  function chlorineDose(product, ppm, litres) {
    const p = CHLORINE[product];
    const grams = (ppm * litres) / 1000;
    return p.kind === 'liquid' ? { ml: (grams / p.v) * 1000 } : { grams: grams / p.v };
  }
  function chlorineSide(product, ppm) {
    const k = CHLORINE[product].kind;
    return {
      cya: k === 'dichlor' ? (MW.cya / (2 * MW.cl2)) * ppm : k === 'trichlor' ? (MW.cya / (3 * MW.cl2)) * ppm : 0,
      ch: k === 'calhypo' ? (MW.caco3 / (2 * MW.cl2)) * ppm : 0,
    };
  }

  const math = {
    ceilCount, degreesToSg, sgToDegrees, abvStandard, abvAlternate, attenuation, honeyPoints, honeyLbFor, toEc, fromEc,
    fillFromWater, candleSplit, convertLoad, pitchFactor, hipFactor, pitchDegrees, roof, brewRatio, shotStyle, skeinsNeeded,
    swatchYarn, lengthFromWeight, gaugeCount, dayNumber, cycleDay, yearStats, coatGallons, coatRate, kits, slabFt3, bagsFor,
    orderRounded, piecesFor, rebarGrid, chlorineDose, chlorineSide, CHLORINE,
  };
  if (typeof module !== 'undefined' && module.exports) { module.exports = math; return; }

  /* ---------- pages ---------- */

  const $ = (id) => document.getElementById(id);
  const num = (id) => parseFloat(String($(id).value).replace(',', '.'));
  const fmt = (v, d = 1) => (Number.isFinite(v) ? v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) : '–');
  const trim = (v, d = 2) => (Number.isFinite(v) ? v.toLocaleString('en-US', { maximumFractionDigits: d }) : '–');
  const set = (id, text) => { const el = $(id); if (el) el.textContent = text; };
  const big = (id, value, unit) => { $(id).innerHTML = value === '–' ? '–' : `${value}<small> ${unit}</small>`; };
  const DATA = window.CALC_DATA || {};

  function segmented(id, onChange) {
    const root = $(id);
    if (!root) return () => null;
    root.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      root.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      onChange();
    });
    return () => root.querySelector('button[aria-pressed="true"]').dataset.v;
  }
  function listen(ids, run) {
    ids.forEach((id) => { const el = $(id); if (el) el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', run); });
  }
  function verdict(id, cls, text) { const v = $(id); if (v) { v.className = cls ? `verdict ${cls}` : 'verdict'; v.textContent = text; } }

  /* Mead, cider and wine ABV */
  function initAbv() {
    let cur = 'sg';
    const show = (sg, u) => (u === 'sg' ? sg.toFixed(3) : sgToDegrees(sg).toFixed(1));
    const read = (id, u) => { const v = num(id); return u === 'sg' ? v : degreesToSg(v); };
    const unit = segmented('gunit', () => {
      const next = unit();
      ['og', 'fg'].forEach((id) => { const sg = read(id, cur); if (Number.isFinite(sg)) $(id).value = show(sg, next); });
      cur = next;
      const name = { sg: 'SG', brix: '°Bx', plato: '°P' }[cur];
      set('og-unit', `(${name})`); set('fg-unit', `(${name})`);
      run();
    });
    function run() {
      const og = read('og', cur), fg = read('fg', cur);
      const ok = og > 0.9 && fg > 0.9 && og < 1.6 && og >= fg;
      const abv = ok ? abvStandard(og, fg) : NaN;
      big('abv-std', ok ? fmt(abv, 1) : '–', '% ABV');
      set('abv-alt', ok ? `${fmt(abvAlternate(og, fg), 1)} %` : '–');
      set('abv-att', ok ? `${fmt(attenuation(og, fg), 0)} %` : '–');
      set('abv-sg', ok ? `${og.toFixed(3)} → ${fg.toFixed(3)}` : '–');
      set('abv-deg', ok ? `${fmt(sgToDegrees(og), 1)} → ${fmt(sgToDegrees(fg), 1)} °P` : '–');
      set('abv-sweet', !ok ? '–' : fg < 0.99 || fg > 1.05 ? 'outside the 0.990–1.050 range' : fg < 1.01 ? 'dry' : fg < 1.025 ? 'semi-sweet' : 'sweet');
      set('abv-strength', !ok ? '–' : abv < 3.5 || abv > 18 ? 'outside the 3.5–18 % range' : abv < 7.5 ? 'hydromel' : abv <= 14 ? 'standard' : 'sack');
      verdict('abv-note', cur === 'sg' || !ok ? '' : 'warn', cur === 'sg' || !ok ? '' : 'A refractometer reads too high once alcohol is present. Take the final gravity with a hydrometer.');
    }
    listen(['og', 'fg'], run);
    run();
  }

  /* Honey for a target gravity */
  function initHoney() {
    const mode = segmented('hmode', run);
    let metric = false;
    const unit = segmented('hunit', () => {
      const m = unit() === 'metric';
      if (m !== metric) {
        const v = num('hvol'), a = num('hamt');
        if (Number.isFinite(v)) $('hvol').value = trim(m ? v * L_PER_GAL : v / L_PER_GAL, 1).replace(/,/g, '');
        if (Number.isFinite(a)) $('hamt').value = trim(m ? a * KG_PER_LB : a / KG_PER_LB, 2).replace(/,/g, '');
        metric = m;
      }
      set('hvol-unit', m ? '(litres)' : '(US gallons)'); set('hamt-unit', m ? '(kg)' : '(lb)');
      run();
    });
    function run() {
      const need = mode() === 'need';
      $('hog-row').hidden = !need; $('hamt-row').hidden = need;
      const gal = metric ? num('hvol') / L_PER_GAL : num('hvol');
      let start = num('hstart');
      if (!Number.isFinite(start)) start = 1;
      let lb, og;
      if (need) { og = num('hog'); lb = honeyLbFor((og - start) * 1000, gal); }
      else { lb = metric ? num('hamt') / KG_PER_LB : num('hamt'); og = start + honeyPoints(lb, gal) / 1000; }
      const ok = gal > 0 && lb > 0 && og > start && og < 1.6;
      if (need) big('h-main', ok ? fmt(metric ? lb * KG_PER_LB : lb, 2) : '–', metric ? 'kg honey' : 'lb honey');
      else big('h-main', ok ? og.toFixed(3) : '–', 'OG');
      set('h-alt', ok ? (metric ? `${fmt(lb, 2)} lb` : `${fmt(lb * KG_PER_LB, 2)} kg`) : '–');
      set('h-per', ok ? `${fmt(lb / gal, 2)} lb per US gallon (${fmt((lb * KG_PER_LB) / (gal * L_PER_GAL) * 1000, 0)} g per litre)` : '–');
      set('h-og', ok ? `${og.toFixed(3)} (${fmt(sgToDegrees(og), 1)} °Bx)` : '–');
      set('h-abv', ok ? `${fmt(abvStandard(og, 1), 1)} %` : '–');
    }
    listen(['hvol', 'hog', 'hstart', 'hamt'], run);
    run();
  }

  /* EC ↔ ppm */
  function initEc() {
    const crops = DATA.crops || [];
    const sel = $('eccrop');
    if (sel) sel.innerHTML = '<option value="">No crop selected</option>' + crops.map((c, i) => `<option value="${i}">${c[0]}</option>`).join('');
    function run() {
      const ec = toEc(num('ecval'), $('ecfrom').value);
      const ok = ec >= 0 && Number.isFinite(ec);
      big('ec-ms', ok ? fmt(ec, 2) : '–', 'mS/cm');
      set('ec-us', ok ? `${fmt(fromEc(ec, 'us'), 0)} µS/cm` : '–');
      ['500', '640', '700'].forEach((s) => set(`ec-${s}`, ok ? `${fmt(fromEc(ec, `ppm${s}`), 0)} ppm` : '–'));
      const c = sel && sel.value !== '' ? crops[+sel.value] : null;
      set('ec-crop', c ? `${fmt(c[1], 1)}–${fmt(c[2], 1)} mS/cm · ${fmt(c[1] * 500, 0)}–${fmt(c[2] * 500, 0)} ppm (500) · ${fmt(c[1] * 700, 0)}–${fmt(c[2] * 700, 0)} ppm (700)` : '–');
      set('ec-ph', c ? (c[3] === c[4] ? fmt(c[3], 1) : `${fmt(c[3], 1)}–${fmt(c[4], 1)}`) : '–');
      if (!c || !ok) verdict('ec-verdict', '', '');
      else if (ec < c[1]) verdict('ec-verdict', 'warn', `Below the published range for ${c[0].toLowerCase()}.`);
      else if (ec > c[2]) verdict('ec-verdict', 'warn', `Above the published range for ${c[0].toLowerCase()}.`);
      else verdict('ec-verdict', 'good', `Inside the published range for ${c[0].toLowerCase()}.`);
    }
    listen(['ecval', 'ecfrom', 'eccrop'], run);
    run();
  }

  /* Fragrance for a wax weight */
  function initFragrance() {
    const waxes = DATA.waxes || [];
    $('fwaxtype').innerHTML = '<option value="">Any wax</option>' + waxes.map((w, i) => `<option value="${i}">${w[0]}</option>`).join('');
    const unit = segmented('funit', () => { set('fwax-unit', `(${unit()})`); run(); });
    function run() {
      const u = unit(), wax = num('fwax'), load = num('fload');
      const ok = wax > 0 && load >= 0 && load < 100;
      const fo = ok ? (wax * load) / 100 : NaN;
      big('f-fo', ok ? fmt(fo, u === 'g' ? 0 : 2) : '–', `${u} fragrance`);
      set('f-total', ok ? `${fmt(wax + fo, u === 'g' ? 0 : 2)} ${u}` : '–');
      set('f-total-pct', ok ? `${fmt(convertLoad(load, true), 2)} % of the finished candle` : '–');
      set('f-perlb', ok ? `${fmt((load / 100) * 16, 2)} oz per lb of wax` : '–');
      const w = $('fwaxtype').value !== '' ? waxes[+$('fwaxtype').value] : null;
      if (!ok) verdict('f-warn', '', '');
      else if (w && load > w[1] + 1e-9) verdict('f-warn', 'bad', `Above the ${w[1]} % the supplier lists for ${w[0]}. Extra oil can seep out and burn poorly.`);
      else if (w) verdict('f-warn', 'good', `Within the ${w[1]} % the supplier lists for ${w[0]}.`);
      else if (load > 12) verdict('f-warn', 'warn', 'Above 12 %: most waxes hold 6–12 %. Check the wax maker\'s data sheet.');
      else verdict('f-warn', '', '');
    }
    listen(['fwax', 'fload', 'fwaxtype'], run);
    run();
  }

  /* Wax for a jar */
  function initJar() {
    const unit = segmented('junit', () => { set('jwater-unit', `(${unit()} of water)`); run(); });
    function run() {
      const u = unit(), d = u === 'g' ? 0 : 2;
      const fill = fillFromWater(num('jwater'), num('jfactor'));
      const load = num('jload'), count = Math.max(0, Math.round(num('jcount') || 0)), extra = Math.max(0, num('jextra') || 0);
      const ok = fill > 0 && load >= 0 && load < 100 && count > 0;
      const [wax, fo] = ok ? candleSplit(fill, load, true) : [NaN, NaN];
      const k = count * (1 + extra / 100);
      const more = (v) => (u === 'oz' && v >= 16 ? ` (${fmt(v / 16, 2)} lb)` : u === 'g' && v >= 1000 ? ` (${fmt(v / 1000, 2)} kg)` : '');
      big('j-wax', ok ? fmt(wax, d) : '–', `${u} wax per candle`);
      set('j-fo', ok ? `${fmt(fo, d)} ${u}` : '–');
      set('j-fill', ok ? `${fmt(fill, d)} ${u}` : '–');
      set('j-twax', ok ? `${fmt(wax * k, d)} ${u}${more(wax * k)}` : '–');
      set('j-tfo', ok ? `${fmt(fo * k, d)} ${u}${more(fo * k)}` : '–');
    }
    listen(['jwater', 'jfactor', 'jload', 'jcount', 'jextra'], run);
    run();
  }

  /* Roof area, squares and bundles */
  function initRoof() {
    function run() {
      const plan = num('rlen') * num('rwid'), rise = +$('rpitch').value, waste = +$('rwaste').value / 100;
      const ok = plan > 0;
      const r = ok ? roof(plan, rise, waste) : null;
      big('r-sq', ok ? fmt(r.squares, 1) : '–', 'squares');
      set('r-area', ok ? `${fmt(r.area, 0)} sq ft` : '–');
      set('r-plan', ok ? `${fmt(plan, 0)} sq ft` : '–');
      set('r-factor', `${pitchFactor(rise).toFixed(3)} (${fmt(pitchDegrees(rise), 1)}°)`);
      set('r-bundles', ok ? `${r.bundles} bundles` : '–');
      verdict('r-note', rise < 2 ? 'bad' : rise < 4 ? 'warn' : '',
        rise < 2 ? 'Below 2/12: too flat for asphalt shingles (IRC R905.2.2).' : rise < 4 ? 'From 2/12 up to 4/12 asphalt shingles need double underlayment (IRC R905.2.2).' : '');
    }
    listen(['rlen', 'rwid', 'rpitch', 'rwaste'], run);
    run();
  }

  /* Espresso brew ratio */
  function initRatio() {
    const mode = segmented('emode', run);
    function run() {
      const m = mode();
      $('edose-row').hidden = m === 'dose'; $('eyield-row').hidden = m === 'yield'; $('eratio-row').hidden = m === 'ratio';
      let dose = num('edose'), out = num('eyield'), ratio = num('eratio');
      if (m === 'ratio') ratio = brewRatio(dose, out);
      else if (m === 'yield') out = dose * ratio;
      else dose = ratio > 0 ? out / ratio : NaN;
      const ok = dose > 0 && out > 0 && ratio > 0;
      if (m === 'ratio') $('e-main').textContent = ok ? `1:${ratio.toFixed(1)}` : '–';
      else big('e-main', ok ? fmt(m === 'yield' ? out : dose, 1) : '–', m === 'yield' ? 'g out' : 'g in');
      set('e-dose', ok ? `${fmt(dose, 1)} g` : '–');
      set('e-yield', ok ? `${fmt(out, 1)} g` : '–');
      set('e-ratio', ok ? `1:${ratio.toFixed(2)}` : '–');
      set('e-style', ok ? shotStyle(ratio) : '–');
    }
    listen(['edose', 'eyield', 'eratio'], run);
    run();
  }

  /* Yarn from a swatch */
  function initYarn() {
    const sizes = DATA.sizes || [];
    $('yproj').innerHTML = sizes.map((s, i) => `<option value="${i}">${s[0]}</option>`).join('') + '<option value="">Your own size</option>';
    let cm = false;
    const unit = segmented('yunit', () => {
      const next = unit() === 'cm';
      if (next !== cm) {
        ['yw', 'yh', 'ypw', 'ypl'].forEach((id) => { const v = num(id); if (Number.isFinite(v)) $(id).value = trim(next ? v * 2.54 : v / 2.54, 1).replace(/,/g, ''); });
        const l = num('ybl'); if (Number.isFinite(l)) $('ybl').value = trim(next ? l * M_PER_YD : l / M_PER_YD, 0).replace(/,/g, '');
        cm = next;
      }
      document.querySelectorAll('.y-dim').forEach((el) => { el.textContent = cm ? '(cm)' : '(in)'; });
      set('ybl-unit', cm ? '(m)' : '(yd)');
      run();
    });
    function preset() {
      const s = $('yproj').value === '' ? null : sizes[+$('yproj').value];
      if (s) { $('ypw').value = trim(cm ? s[1] * 2.54 : s[1], 1); $('ypl').value = trim(cm ? s[2] * 2.54 : s[2], 1); }
      run();
    }
    function run() {
      const ballLen = num('ybl'), ballWt = num('ybw');
      const swatchLen = lengthFromWeight(ballWt, ballLen, num('ysw'));
      const need = swatchYarn(num('yw'), num('yh'), swatchLen, num('ypw'), num('ypl'));
      const r = skeinsNeeded(need, ballLen, Math.max(0, num('yextra') || 0));
      const ok = need > 0 && Number.isFinite(need) && r.skeins > 0;
      big('y-len', ok ? fmt(r.needed, 0) : '–', cm ? 'm' : 'yd');
      set('y-alt', ok ? (cm ? `${fmt(r.needed / M_PER_YD, 0)} yd` : `${fmt(r.needed * M_PER_YD, 0)} m`) : '–');
      set('y-wt', ok ? `${fmt((r.needed / ballLen) * ballWt, 0)} g` : '–');
      set('y-sk', ok ? `${r.skeins} × ${trim(ballWt, 0)} g` : '–');
      set('y-swatch', swatchLen > 0 ? `${fmt(swatchLen, 1)} ${cm ? 'm' : 'yd'}` : '–');
    }
    $('yproj').addEventListener('change', preset);
    listen(['yw', 'yh', 'ysw', 'ybw', 'ybl', 'yextra'], run);
    ['ypw', 'ypl'].forEach((id) => $(id).addEventListener('input', () => { $('yproj').value = ''; run(); }));
    preset();
  }

  /* Gauge: cast-on stitches and rows */
  function initGauge() {
    let cm = false;
    const unit = segmented('gunit2', () => {
      const next = unit() === 'cm';
      if (next !== cm) {
        ['gsw', 'gsh', 'gw', 'gl'].forEach((id) => { const v = num(id); if (Number.isFinite(v)) $(id).value = trim(next ? v * 2.54 : v / 2.54, 1).replace(/,/g, ''); });
        cm = next;
      }
      document.querySelectorAll('.g-dim').forEach((el) => { el.textContent = cm ? '(cm)' : '(in)'; });
      run();
    });
    function run() {
      const four = cm ? 10 : 4;
      const sts4 = (num('gsts') / num('gsw')) * four, rows4 = (num('grows') / num('gsh')) * four;
      const cast = Math.floor((sts4 / four) * num('gw') + 0.5), rows = Math.floor((rows4 / four) * num('gl') + 0.5);
      const ok = sts4 > 0 && Number.isFinite(sts4) && cast > 0;
      big('g-cast', ok ? String(cast) : '–', 'stitches');
      set('g-rows', rows > 0 && Number.isFinite(rows) ? `${rows} rows` : '–');
      set('g-gauge', ok ? `${fmt(sts4, 1)} sts${rows4 > 0 ? ` × ${fmt(rows4, 1)} rows` : ''} per ${cm ? '10 cm' : '4 in'}` : '–');
      set('g-per1', ok ? `${fmt(sts4 / four, 2)} sts per ${cm ? 'cm' : 'inch'}` : '–');
    }
    listen(['gsts', 'gsw', 'grows', 'gsh', 'gw', 'gl'], run);
    run();
  }

  /* Shift pattern calendar */
  function initShift() {
    const cycle = DATA.cycle.split(''), names = DATA.names, n = cycle.length;
    const now = new Date();
    const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    $('sdate').value = iso(now);
    $('sday').innerHTML = cycle.map((c, i) => `<option value="${i}">Day ${i + 1} of ${n}: ${names[c]}</option>`).join('');
    const SHORT = { M: 'Morn', A: 'Aft' }; // full names are in the cell's title and the legend
    const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    function run() {
      const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec($('sdate').value);
      const len = num('slen');
      if (!m || !(len > 0)) { $('s-cal').innerHTML = ''; return; }
      const y = +m[1], date = dayNumber(y, +m[2] - 1, +m[3]);
      const start = date - +$('sday').value; // day number of cycle day 1
      const hours = {}; Object.keys(names).forEach((c) => { hours[c] = c === 'O' ? 0 : len; });
      const st = yearStats(cycle, y, start, hours);
      const perCycle = cycle.filter((c) => c !== 'O').length * len;
      big('s-week', fmt((perCycle / n) * 7, 1), 'h per week');
      set('s-year', String(y));
      set('s-shifts', `${st.shifts} shifts`);
      set('s-off', `${st.off} days`);
      set('s-hours', `${fmt(st.hours, 0)} h`);
      set('s-weekends', String(st.weekends));
      // 12 weeks from the Monday of the chosen week (day number 4 was a Monday).
      const monday = date - ((((date - 4) % 7) + 7) % 7);
      let html = '<table class="cal"><thead><tr>' + ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => `<th>${d}</th>`).join('') + '</tr></thead><tbody>';
      for (let w = 0; w < 12; w++) {
        html += '<tr>';
        for (let i = 0; i < 7; i++) {
          const d = monday + w * 7 + i, dt = new Date(d * 86400000), c = cycle[cycleDay(start, d, n)];
          const label = dt.getUTCDate() === 1 || (w === 0 && i === 0) ? `${MONTHS[dt.getUTCMonth()].slice(0, 3)} ${dt.getUTCDate()}` : dt.getUTCDate();
          html += `<td class="s-${c}" title="${names[c]}"${d === date ? ' style="outline:2px solid var(--accent)"' : ''}><b>${label}</b><small>${c === 'O' ? 'off' : SHORT[c] || names[c]}</small></td>`;
        }
        html += '</tr>';
      }
      $('s-cal').innerHTML = html + '</tbody></table>';
    }
    listen(['sdate', 'sday', 'slen'], run);
    run();
  }

  /* Garage floor coating */
  function initGarage() {
    const products = DATA.products || [];
    $('gsys').innerHTML = products.map((p, i) => `<option value="${i}">${p.name}</option>`).join('');
    $('gsys').value = String(Math.max(0, products.findIndex((p) => p.def)));
    function system() {
      const p = products[+$('gsys').value];
      if (p) { $('gmils').value = p.mils; $('gsolids').value = Math.round(p.solids * 100); $('gkit').value = p.kit; }
      run();
    }
    function size() { if ($('gsize').value) $('garea').value = $('gsize').value; run(); }
    function run() {
      const sqft = num('garea'), mils = num('gmils'), solids = num('gsolids') / 100, waste = (num('gwaste') || 0) / 100, kit = num('gkit');
      const ok = [sqft, mils, solids].every((v) => Number.isFinite(v) && v > 0);
      const gal = ok ? coatGallons(sqft, mils, solids, waste) : NaN;
      big('ga-gal', ok ? fmt(gal, 2) : '–', 'gal');
      set('ga-l', ok ? `${fmt(gal * 3.78541, 1)} L` : '–');
      set('ga-rate', ok ? `${fmt(coatRate(mils, solids), 0)} sq ft per gallon` : '–');
      set('ga-kits', ok && kit > 0 ? `${kits(gal, kit)} × ${trim(kit)} gal` : '–');
    }
    $('gsys').addEventListener('change', system);
    $('gsize').addEventListener('change', size);
    $('garea').addEventListener('input', () => { $('gsize').value = ''; run(); });
    listen(['gmils', 'gsolids', 'gwaste', 'gkit'], run);
    system();
  }

  /* Concrete slab */
  function initSlab() {
    if (DATA.slab) { $('sl').value = DATA.slab[0]; $('sw').value = DATA.slab[1]; }
    function run() {
      const l = num('sl'), w = num('sw'), t = num('st'), extra = Math.max(0, num('sextra') || 0);
      const ok = l > 0 && w > 0 && t > 0;
      const ft3 = ok ? slabFt3(l, w, t, extra) : NaN;
      big('sb-yd', ok ? fmt(ft3 / 27, 2) : '–', 'cu yd');
      set('sb-ft3', ok ? `${fmt(ft3, 1)} cu ft` : '–');
      set('sb-order', ok ? `${trim(orderRounded(ft3))} cu yd` : '–');
      BAGS.forEach(([label, y]) => set(`sb-${parseInt(label, 10)}`, ok ? `${bagsFor(ft3, y).toLocaleString('en-US')} bags` : '–'));
      const g = ok ? rebarGrid(l, w, +$('sspace').value, 3, 20, '#4', 40) : null;
      set('sb-rebar', g ? `${g.pieces} × 20 ft sticks · ${fmt(g.totalFt, 0)} ft · ${fmt(g.weightLb, 0)} lb` : '–');
    }
    listen(['sl', 'sw', 'st', 'sextra', 'sspace'], run);
    run();
  }

  /* Chlorine for a pool */
  function initChlorine() {
    $('cprod').innerHTML = Object.keys(CHLORINE).map((k) => `<option value="${k}">${CHLORINE[k].name}</option>`).join('');
    if (DATA.gallons) $('cvol').value = DATA.gallons;
    const unit = segmented('cunit', run);
    function run() {
      const vol = num('cvol'), litres = unit() === 'gal' ? vol * 3.78541 : vol;
      const delta = num('cto') - num('cfrom'), key = $('cprod').value;
      const ok = litres > 0 && Number.isFinite(delta);
      if (!ok || delta <= 0) {
        $('cl-amt').textContent = ok ? 'Already at target' : '–';
        ['cl-alt', 'cl-rise', 'cl-side'].forEach((id) => set(id, '–'));
        return;
      }
      const d = chlorineDose(key, delta, litres), side = chlorineSide(key, delta);
      if (d.ml != null) {
        big('cl-amt', fmt(d.ml / 29.5735, 1), 'fl oz');
        set('cl-alt', `${fmt(d.ml / 3785.41, 2)} gal · ${fmt(d.ml / 1000, 2)} L`);
      } else {
        const oz = d.grams / 28.3495;
        if (oz >= 16) big('cl-amt', fmt(oz / 16, 2), 'lb'); else big('cl-amt', fmt(oz, 1), 'oz by weight');
        set('cl-alt', d.grams >= 1000 ? `${fmt(d.grams / 1000, 2)} kg` : `${fmt(d.grams, 0)} g`);
      }
      set('cl-rise', `+${trim(delta, 1)} ppm free chlorine`);
      set('cl-side', side.cya > 0 ? `+${fmt(side.cya, 1)} ppm stabilizer (CYA)` : side.ch > 0 ? `+${fmt(side.ch, 1)} ppm calcium hardness` : 'salt only');
    }
    listen(['cvol', 'cfrom', 'cto', 'cprod'], run);
    run();
  }

  /* Embed page: select all on focus */
  function initEmbed() {
    document.querySelectorAll('.embed-code').forEach((t) => t.addEventListener('focus', () => t.select()));
  }

  document.addEventListener('DOMContentLoaded', () => {
    const inits = { abv: initAbv, honey: initHoney, ec: initEc, frag: initFragrance, jar: initJar, roof: initRoof, ratio: initRatio,
      yarn: initYarn, gauge: initGauge, shift: initShift, garage: initGarage, slab: initSlab, chlor: initChlorine, embed: initEmbed };
    const init = inits[document.body.dataset.calc];
    if (init) init();
  });
})();
