// Calculators for the static pages. The maths mirrors the apps' Dart engines:
// hvac-charge-app/lib/feature/engine/{pt,charge}.dart, Calculator_for_electrical/lib/feature/engine/electrical.dart,
// coatcalc-app/lib/feature/calc.dart. Keep them in step when the apps change.

const $ = (id) => document.getElementById(id);
const num = (id) => parseFloat(String($(id).value).replace(',', '.'));
const fmt = (v, d = 1) => (Number.isFinite(v) ? v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) : '–');

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

/* ---------- HVAC: PT, superheat, subcooling ---------- */

const ATM_PSIA = 14.695949;
const PSI_PER_INHG = 0.4911541;
const STEP_F = 5;
const cellPsia = (p) => (p >= 0 ? ATM_PSIA + p : ATM_PSIA + p * PSI_PER_INHG);
const inv = (f) => 1 / (f + 459.67);

function tempAtPsia(curve, psia) {
  const ps = curve.psig;
  if (psia <= 0) return null;
  if (psia < cellPsia(ps[0]) - 1e-9 || psia > cellPsia(ps[ps.length - 1]) + 1e-9) return null;
  const lp = Math.log(psia);
  for (let i = 0; i < ps.length - 1; i++) {
    const p0 = Math.log(cellPsia(ps[i]));
    const p1 = Math.log(cellPsia(ps[i + 1]));
    if (lp <= p1 + 1e-12 || i === ps.length - 2) {
      const t0 = curve.startF + i * STEP_F;
      const f = p1 === p0 ? 0 : (lp - p0) / (p1 - p0);
      return 1 / (inv(t0) + (inv(t0 + STEP_F) - inv(t0)) * f) - 459.67;
    }
  }
  return null;
}

function psiaAt(curve, tempF) {
  const end = curve.startF + STEP_F * (curve.psig.length - 1);
  if (tempF < curve.startF - 1e-9 || tempF > end + 1e-9) return null;
  const i = Math.min(Math.floor((tempF - curve.startF) / STEP_F), curve.psig.length - 2);
  const t0 = curve.startF + i * STEP_F;
  const p0 = Math.log(cellPsia(curve.psig[i]));
  const p1 = Math.log(cellPsia(curve.psig[i + 1]));
  const f = (inv(tempF) - inv(t0)) / (inv(t0 + STEP_F) - inv(t0));
  return Math.exp(p0 + (p1 - p0) * f);
}

const fToC = (f) => ((f - 32) * 5) / 9;

function initHvac() {
  const data = window.PT_DATA;
  const sel = $('ref');
  const mode = segmented('mode', run);
  const ptMode = segmented('ptmode', runPt);

  // Superheat is read from the dew curve, subcooling from the bubble curve; single-column fluids use one curve.
  const curveFor = (r, phase) => (phase === 'dew' && r.dew ? r.dew : r.bubble);

  function run() {
    const r = data[sel.value];
    const sh = mode() === 'sh';
    $('p-label').firstChild.textContent = sh ? 'Suction pressure ' : 'Liquid pressure ';
    $('t-label').firstChild.textContent = sh ? 'Suction line temp ' : 'Liquid line temp ';
    $('out-title').textContent = sh ? 'Superheat' : 'Subcooling';
    const psig = num('p');
    const line = num('t');
    const phase = sh ? 'dew' : 'bubble';
    const sat = Number.isFinite(psig) ? tempAtPsia(curveFor(r, phase), psig + ATM_PSIA) : null;
    const v = sat == null || !Number.isFinite(line) ? NaN : sh ? line - sat : sat - line;
    $('out').innerHTML = `${fmt(v)}<small> °F</small>`;
    $('out-c').textContent = Number.isFinite(v) ? `${fmt((v * 5) / 9)} K` : '';
    $('sat').textContent = sat == null ? (Number.isFinite(psig) ? 'outside the chart' : '–') : `${fmt(sat)} °F (${fmt(fToC(sat))} °C)`;
    $('sat-label').textContent = r.dew ? (sh ? 'Dew point (vapour)' : 'Bubble point (liquid)') : 'Saturation temp';
    const warn = $('hvac-warn');
    if (Number.isFinite(v) && v < 0) {
      warn.className = 'verdict bad';
      warn.textContent = sh ? 'Negative superheat: liquid may be reaching the compressor. Recheck readings.' : 'Negative subcooling: the liquid line is not full of liquid. Recheck readings.';
    } else {
      warn.className = 'verdict';
      warn.textContent = '';
    }
  }

  function runPt() {
    const r = data[sel.value];
    const toTemp = ptMode() === 'p2t';
    $('pt-in-label').firstChild.textContent = toTemp ? 'Pressure ' : 'Temperature ';
    $('pt-in-label').querySelector('small').textContent = toTemp ? '(psig)' : '(°F)';
    const x = num('pt-in');
    const rows = [];
    for (const phase of r.dew ? ['bubble', 'dew'] : ['bubble']) {
      const c = curveFor(r, phase);
      let txt = '–';
      if (Number.isFinite(x)) {
        if (toTemp) {
          const t = tempAtPsia(c, x + ATM_PSIA);
          txt = t == null ? 'outside the chart' : `${fmt(t)} °F (${fmt(fToC(t))} °C)`;
        } else {
          const p = psiaAt(c, x);
          txt = p == null ? 'outside the chart' : p - ATM_PSIA >= 0 ? `${fmt(p - ATM_PSIA)} psig` : `${fmt((ATM_PSIA - p) / PSI_PER_INHG)} inHg vac`;
        }
      }
      const name = r.dew ? (phase === 'dew' ? 'Dew (vapour)' : 'Bubble (liquid)') : 'Saturation';
      rows.push(`<div><span>${name}</span><span>${txt}</span></div>`);
    }
    $('pt-out').innerHTML = rows.join('');
  }

  sel.addEventListener('change', () => { run(); runPt(); });
  ['p', 't'].forEach((id) => $(id).addEventListener('input', run));
  $('pt-in').addEventListener('input', runPt);
  run();
  runPt();
}

/* ---------- Voltage drop ---------- */

const RHO20 = { cu: 0.017241, al: 0.028264 };
const RHO_IEC = { cu: 0.0225, al: 0.036 };
const REACTANCE = 0.00008;
const MM2_PER_CMIL = 0.000506707;
const NEC = [
  ['18', 1620], ['16', 2580], ['14', 4110], ['12', 6530], ['10', 10380], ['8', 16510], ['6', 26240], ['4', 41740],
  ['3', 52620], ['2', 66360], ['1', 83690], ['1/0', 105600], ['2/0', 133100], ['3/0', 167800], ['4/0', 211600],
  ['250', 250000], ['300', 300000], ['350', 350000], ['400', 400000], ['500', 500000],
];
const IEC = [0.5, 0.75, 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300];

function sizesFor(std) {
  return std === 'nec'
    ? NEC.map(([s, c]) => ({ label: +s >= 250 ? `${s} kcmil` : `${s} AWG`, mm2: c * MM2_PER_CMIL }))
    : IEC.map((a) => ({ label: `${a} mm²`, mm2: a }));
}

function dropVolts({ supply, cond, mm2, metres, amps, iec, pf }) {
  const ac = supply !== 'dc';
  const rho = iec ? RHO_IEC[cond] : RHO20[cond] * 1.25;
  const z = (rho / mm2) * (ac ? pf : 1) + (ac ? REACTANCE * Math.sqrt(Math.max(0, 1 - pf * pf)) : 0);
  return (supply === 'three' ? Math.sqrt(3) : 2) * amps * metres * z;
}

function initVoltageDrop() {
  const std = segmented('std', () => { fillSizes(); defaults(); run(); });
  const supply = segmented('supply', run);
  const cond = segmented('cond', run);
  const sizeSel = $('size');

  function fillSizes() {
    const list = sizesFor(std());
    sizeSel.innerHTML = list.map((s, i) => `<option value="${i}">${s.label}</option>`).join('');
    sizeSel.value = String(list.findIndex((s) => s.label === (std() === 'nec' ? '12 AWG' : '2.5 mm²')));
    $('len-unit').textContent = std() === 'nec' ? '(ft, one way)' : '(m, one way)';
  }
  function defaults() {
    const nec = std() === 'nec';
    $('volts').value = nec ? '120' : '230';
    $('len').value = nec ? '100' : '30';
  }

  function run() {
    const nec = std() === 'nec';
    const list = sizesFor(std());
    const s = list[+sizeSel.value];
    const len = num('len');
    const metres = nec ? len * 0.3048 : len;
    const amps = num('amps');
    const volts = num('volts');
    let pf = num('pf');
    if (!Number.isFinite(pf) || pf <= 0 || pf > 1) pf = 1;
    const args = { supply: supply(), cond: cond(), metres, amps, iec: !nec, pf };
    const dv = dropVolts({ ...args, mm2: s.mm2 });
    const pct = (dv / volts) * 100;
    const ok = [metres, amps, volts].every((v) => Number.isFinite(v) && v > 0);
    $('vd-pct').innerHTML = ok ? `${fmt(pct, 2)}<small> %</small>` : '–';
    $('vd-v').textContent = ok ? `${fmt(dv, 2)} V` : '–';
    $('vd-end').textContent = ok ? `${fmt(volts - dv, 1)} V` : '–';
    const limit = 3;
    const fit = ok ? list.find((x) => (dropVolts({ ...args, mm2: x.mm2 }) / volts) * 100 <= limit) : null;
    $('vd-min').textContent = !ok ? '–' : fit ? fit.label : 'larger than the list (use parallel runs)';
    const v = $('vd-verdict');
    if (!ok) { v.className = 'verdict'; v.textContent = ''; return; }
    if (pct <= 3) { v.className = 'verdict good'; v.textContent = 'Within 3 %: fine for a branch circuit.'; }
    else if (pct <= 5) { v.className = 'verdict warn'; v.textContent = 'Between 3 % and 5 %: OK only if the feeder drop is small. Consider the next size up.'; }
    else { v.className = 'verdict bad'; v.textContent = 'Over 5 %: upsize the conductor or shorten the run.'; }
  }

  fillSizes();
  defaults();
  sizeSel.addEventListener('change', run);
  ['len', 'amps', 'volts', 'pf'].forEach((id) => $(id).addEventListener('input', run));
  run();
}

/* ---------- Epoxy coverage ---------- */

const SQFT_PER_GAL_1MIL = 1604;

function initCoat() {
  const unit = segmented('unit', () => {
    const m = unit() === 'm2';
    const a = num('area');
    if (Number.isFinite(a)) $('area').value = m ? (a * 0.092903).toFixed(1) : Math.round(a / 0.092903);
    $('area-unit').textContent = m ? '(m²)' : '(sq ft)';
    run();
  });

  function run() {
    const raw = num('area');
    const sqft = unit() === 'm2' ? raw / 0.092903 : raw;
    const mils = num('mils');
    const solids = num('solids') / 100;
    const waste = (num('waste') || 0) / 100;
    const kit = num('kit');
    const price = num('price');
    const ok = [sqft, mils, solids].every((v) => Number.isFinite(v) && v > 0);
    const gal = ok ? ((sqft * mils) / (SQFT_PER_GAL_1MIL * solids)) * (1 + waste) : NaN;
    const kits = ok && kit > 0 ? Math.ceil(gal / kit - 1e-9) : NaN;
    $('c-gal').innerHTML = ok ? `${fmt(gal, 2)}<small> gal</small>` : '–';
    $('c-l').textContent = ok ? `${fmt(gal * 3.78541, 1)} L` : '–';
    $('c-kits').textContent = Number.isFinite(kits) ? `${kits} × ${fmt(kit, 2)} gal` : '–';
    $('c-rate').textContent = ok ? `${fmt((SQFT_PER_GAL_1MIL * solids) / mils, 0)} sq ft/gal` : '–';
    $('c-cost').textContent = Number.isFinite(kits) && price > 0 ? `$${fmt(kits * price, 2)}` : '–';
    const tip = $('c-tip');
    tip.textContent = '';
    if (Number.isFinite(kits) && kits >= 2) {
      const fewer = (kits - 1) * kit;
      if (gal - fewer <= kit * 0.15) {
        const bare = (sqft * mils) / (SQFT_PER_GAL_1MIL * solids);
        const maxWaste = (fewer / bare - 1) * 100;
        tip.className = 'verdict warn';
        tip.textContent = `Just ${fmt(gal - fewer, 2)} gal over ${kits - 1} kits. ${maxWaste >= 0 ? `At ${fmt(maxWaste, 0)} % waste` : `At ${fmt((mils * fewer) / gal, 1)} mils`} you would save one kit.`;
      }
    }
  }

  ['area', 'mils', 'solids', 'waste', 'kit', 'price'].forEach((id) => $(id).addEventListener('input', run));
  run();
}

/* ---------- AWG ↔ mm² ---------- */

function initAwg() {
  const rows = NEC.map(([s, c]) => ({ label: +s >= 250 ? `${s} kcmil` : `${s} AWG`, cmil: c, mm2: c * MM2_PER_CMIL }));
  const sel = $('awg');
  sel.innerHTML = rows.map((r, i) => `<option value="${i}">${r.label}</option>`).join('');
  sel.value = String(rows.findIndex((r) => r.label === '12 AWG'));
  function fromAwg() {
    const r = rows[+sel.value];
    $('awg-mm2').innerHTML = `${fmt(r.mm2, 2)}<small> mm²</small>`;
    $('awg-cmil').textContent = `${r.cmil.toLocaleString('en-US')} cmil`;
    const std = IEC.find((a) => a >= r.mm2 - 1e-9);
    $('awg-iec').textContent = std ? `${std} mm²` : 'larger than 300 mm²';
  }
  function fromMm2() {
    const a = num('mm2');
    if (!Number.isFinite(a) || a <= 0) { $('mm2-awg').textContent = '–'; $('mm2-near').textContent = '–'; return; }
    const up = rows.find((r) => r.mm2 >= a - 1e-9);
    let near = rows[0];
    rows.forEach((r) => { if (Math.abs(r.mm2 - a) < Math.abs(near.mm2 - a)) near = r; });
    $('mm2-awg').innerHTML = up ? `${up.label}` : 'over 500 kcmil';
    $('mm2-near').textContent = `${near.label} (${fmt(near.mm2, 2)} mm²)`;
  }
  sel.addEventListener('change', fromAwg);
  $('mm2').addEventListener('input', fromMm2);
  fromAwg();
  fromMm2();
}

/* ---------- Wire size (NEC 310.16, 30 °C, ≤ 3 current-carrying conductors) ---------- */

const NEC_SIZES = ['14', '12', '10', '8', '6', '4', '3', '2', '1', '1/0', '2/0', '3/0', '4/0', '250', '300', '350', '400', '500'];
const AMPACITY = {
  cu: { 60: [15, 20, 30, 40, 55, 70, 85, 95, 110, 125, 145, 165, 195, 215, 240, 260, 280, 320],
        75: [20, 25, 35, 50, 65, 85, 100, 115, 130, 150, 175, 200, 230, 255, 285, 310, 335, 380],
        90: [25, 30, 40, 55, 75, 95, 115, 130, 145, 170, 195, 225, 260, 290, 320, 350, 380, 430] },
  al: { 60: [0, 15, 25, 35, 40, 55, 65, 75, 85, 100, 115, 130, 150, 170, 195, 210, 225, 260],
        75: [0, 20, 30, 40, 50, 65, 75, 90, 100, 120, 135, 155, 180, 205, 230, 250, 270, 310],
        90: [0, 25, 35, 45, 55, 75, 85, 100, 115, 135, 150, 175, 205, 230, 260, 280, 305, 350] },
};
const BREAKERS = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450, 500, 600];
// Wire type → [insulation column, highest column usable for the final ampacity]; NM-B is held to 60 °C by 334.80.
const WIRES = { nmb: [90, 60], uf: [60, 60], thwn: [75, 75], thhn: [90, 75] };
const SMALL = { cu: { 14: 15, 12: 20, 10: 30 }, al: { 12: 15, 10: 25 } }; // 240.4(D)

function initWireSize() {
  const cond = segmented('cond', run);
  const cont = segmented('cont', run);
  function run() {
    const amps = num('amps');
    const [insulT, limitT] = WIRES[$('wire').value];
    const term = +$('term').value;
    const c = cond();
    if (!(amps > 0)) { $('ws-size').textContent = '–'; return; }
    const design = cont() === 'yes' ? amps * 1.25 : amps;
    const ocpd = BREAKERS.find((b) => b >= design - 1e-9);
    const cap = Math.min(limitT, term);
    let pick = null;
    for (let i = 0; i < NEC_SIZES.length && ocpd; i++) {
      const insul = AMPACITY[c][insulT][i];
      const termA = AMPACITY[c][cap][i];
      if (!insul) continue;
      const a = Math.min(insul, termA);
      const small = SMALL[c][NEC_SIZES[i]];
      if (small && ocpd > small) continue;
      if (termA < design || a < amps) continue;
      const next = BREAKERS.find((b) => b >= a - 1e-9);
      if (!(a >= ocpd || (ocpd <= 800 && next >= ocpd))) continue;
      pick = { i, a };
      break;
    }
    let final = pick;
    const len = num('len');
    const volts = num('volts');
    let dropTxt = 'not checked';
    if (pick && len > 0 && volts > 0) {
      const metres = len * 0.3048;
      const supply = $('phase').value;
      for (let i = pick.i; i < NEC_SIZES.length; i++) {
        const mm2 = NEC[i + 2][1] * MM2_PER_CMIL; // NEC table starts at 18 AWG, sizes here at 14
        const pct = (dropVolts({ supply, cond: c, mm2, metres, amps, iec: false, pf: 1 }) / volts) * 100;
        if (pct <= 3) { final = { i, a: pick.a }; dropTxt = `${fmt(pct, 2)} % with ${label(i)}`; break; }
        if (i === NEC_SIZES.length - 1) { final = null; dropTxt = 'over 3 % even at 500 kcmil'; }
      }
    }
    function label(i) { return +NEC_SIZES[i] >= 250 ? `${NEC_SIZES[i]} kcmil` : `${NEC_SIZES[i]} AWG`; }
    $('ws-size').innerHTML = final ? `${label(final.i)}<small> ${c === 'cu' ? 'copper' : 'aluminum'}</small>` : (ocpd ? 'no size fits' : 'over 600 A');
    $('ws-ocpd').textContent = ocpd ? `${ocpd} A` : '–';
    $('ws-design').textContent = `${fmt(design, 1)} A${cont() === 'yes' ? ' (125 % of continuous load)' : ''}`;
    $('ws-amp').textContent = pick ? `${label(pick.i)} · ${pick.a} A at ${cap} °C` : '–';
    $('ws-drop').textContent = dropTxt;
  }
  ['amps', 'len', 'volts'].forEach((id) => $(id).addEventListener('input', run));
  ['wire', 'term', 'phase'].forEach((id) => $(id).addEventListener('change', run));
  run();
}

/* ---------- Pool chemicals (same math as PoolPro) ---------- */

const MW = { cl2: 70.906, naocl: 74.44, caco3Eq: 50.04, nahco3: 84.007 };
const POOL_PRODUCTS = {
  liquid10: { name: 'Liquid chlorine 10 %', liquid: true, gpl: 100 },
  liquid125: { name: 'Liquid chlorine 12.5 %', liquid: true, gpl: 125 },
  bleach6: { name: 'Bleach 6 %', liquid: true, gpl: 6 * 10 * (1.0174 + 0.01003 * 6) * MW.cl2 / MW.naocl },
  bleach825: { name: 'Bleach 8.25 %', liquid: true, gpl: 8.25 * 10 * (1.0174 + 0.01003 * 8.25) * MW.cl2 / MW.naocl },
  calhypo65: { name: 'Cal-hypo 65 %', share: 0.65 },
  dichlor: { name: 'Dichlor 56 %', share: 0.56 },
};

function initPool() {
  const unit = segmented('punit', run);
  function run() {
    const vol = num('pvol');
    const litres = unit() === 'gal' ? vol * 3.78541 : vol;
    const what = $('pwhat').value;
    const from = num('pfrom');
    const to = num('pto');
    $('pprod-row').hidden = what !== 'fc';
    const delta = to - from;
    const ok = litres > 0 && Number.isFinite(delta);
    if (!ok || delta <= 0) {
      $('p-amount').textContent = ok ? 'Already at target' : '–';
      $('p-alt').textContent = '–';
      return;
    }
    const gramsOf = (mgPerL) => (mgPerL * litres) / 1000;
    let grams = null; let ml = null;
    if (what === 'fc') {
      const p = POOL_PRODUCTS[$('pprod').value];
      if (p.liquid) ml = (gramsOf(delta) / p.gpl) * 1000; else grams = gramsOf(delta) / p.share;
    } else if (what === 'ta') {
      grams = gramsOf((delta / MW.caco3Eq) * MW.nahco3);
    } else if (what === 'cya' || what === 'salt') {
      grams = gramsOf(delta) / 0.99;
    }
    if (ml != null) {
      $('p-amount').innerHTML = `${fmt(ml / 29.5735, 1)}<small> fl oz</small>`;
      $('p-alt').textContent = `${fmt(ml / 1000, 2)} L · ${fmt(ml / 3785.41, 2)} gal`;
    } else {
      const lb = grams / 453.592;
      $('p-amount').innerHTML = lb >= 1 ? `${fmt(lb, 2)}<small> lb</small>` : `${fmt(grams / 28.3495, 1)}<small> oz</small>`;
      $('p-alt').textContent = grams >= 1000 ? `${fmt(grams / 1000, 2)} kg` : `${fmt(grams, 0)} g`;
    }
  }
  ['pvol', 'pfrom', 'pto'].forEach((id) => $(id).addEventListener('input', run));
  ['pwhat', 'pprod'].forEach((id) => $(id).addEventListener('change', run));
  run();
}

/* ---------- Baker's percentages (same math as Levain) ---------- */

function initBread() {
  const mode = segmented('bmode', run);
  const count = segmented('bcount', run);
  function run() {
    const byFlour = mode() === 'flour';
    $('b-flour-row').hidden = !byFlour;
    $('b-dough-row').hidden = byFlour;
    const h = num('bhyd') / 100, st = num('bst') / 100, s = num('bsalt') / 100;
    const share = 1 / (1 + num('bsth') / 100);
    const counted = count() === 'yes';
    const a = st * share;
    let bowl;
    if (byFlour) bowl = num('bflour');
    else {
      const perGram = counted ? (1 + a) * (1 + h + s) : 1 + h + st + s;
      bowl = num('bdough') / perGram;
    }
    const ok = [bowl, h, st, s, share].every(Number.isFinite) && bowl > 0;
    const starter = st * bowl, sFlour = starter * share, sWater = starter - sFlour;
    const base = counted ? bowl + sFlour : bowl;
    const water = h * base - (counted ? sWater : 0);
    const salt = s * base;
    const trueHyd = ((water + sWater) / (bowl + sFlour)) * 100;
    $('b-flour').innerHTML = ok ? `${fmt(bowl, 0)}<small> g flour</small>` : '–';
    $('b-water').textContent = ok ? `${fmt(water, 0)} g` : '–';
    $('b-starter').textContent = ok ? `${fmt(starter, 0)} g` : '–';
    $('b-salt').textContent = ok ? `${fmt(salt, 1)} g` : '–';
    $('b-total').textContent = ok ? `${fmt(bowl + water + starter + salt, 0)} g` : '–';
    $('b-true').textContent = ok ? `${fmt(trueHyd, 1)} %` : '–';
  }
  ['bflour', 'bdough', 'bhyd', 'bst', 'bsth', 'bsalt'].forEach((id) => $(id).addEventListener('input', run));
  run();
}

/* ---------- Lye (same math as Lye Calc; SAP in g KOH per g oil) ---------- */

function initLye() {
  const oils = window.OILS;
  const list = $('oils');
  function row(id = 'olive', g = '') {
    const div = document.createElement('div');
    div.className = 'oilrow';
    div.innerHTML = `<select aria-label="Oil">${oils.map((o) => `<option value="${o.id}"${o.id === id ? ' selected' : ''}>${o.name}</option>`).join('')}</select>
      <input inputmode="decimal" aria-label="Grams" placeholder="g" value="${g}"><button type="button" class="btn ghost" aria-label="Remove">✕</button>`;
    div.querySelector('button').addEventListener('click', () => { div.remove(); run(); });
    div.querySelectorAll('select,input').forEach((el) => el.addEventListener('input', run));
    list.appendChild(div);
  }
  function run() {
    let total = 0, koh = 0;
    list.querySelectorAll('.oilrow').forEach((r) => {
      const o = oils.find((x) => x.id === r.querySelector('select').value);
      const g = parseFloat(String(r.querySelector('input').value).replace(',', '.'));
      if (o && g > 0) { total += g; koh += g * o.sap; }
    });
    const sf = (num('sf') || 0) / 100;
    const purity = (num('purity') || 100) / 100;
    const conc = num('conc');
    const naoh = (koh * (39.997 / 56.106) * (1 - sf)) / purity;
    const water = conc > 0 && conc < 100 ? (naoh * (100 - conc)) / conc : NaN;
    const ok = total > 0;
    $('l-naoh').innerHTML = ok ? `${fmt(naoh, 1)}<small> g NaOH</small>` : '–';
    $('l-water').textContent = ok && Number.isFinite(water) ? `${fmt(water, 1)} g` : '–';
    $('l-oils').textContent = ok ? `${fmt(total, 0)} g` : '–';
    $('l-ratio').textContent = ok && Number.isFinite(water) ? `${fmt(water / naoh, 2)} : 1` : '–';
    $('l-batch').textContent = ok && Number.isFinite(water) ? `${fmt(total + naoh + water, 0)} g` : '–';
  }
  $('add-oil').addEventListener('click', () => { row('coconut76'); run(); });
  ['sf', 'purity', 'conc'].forEach((id) => $(id).addEventListener('input', run));
  row('olive', '700'); row('coconut76', '200'); row('castor', '100');
  run();
}

/* ---------- Christmas / New Year countdown ---------- */

function initCountdown() {
  const pad = (n) => String(n).padStart(2, '0');
  // Next occurrence of month/day at local midnight; on the day itself the target is that day (shows 0).
  function next(month, day, now) {
    let t = new Date(now.getFullYear(), month, day);
    const endOfDay = new Date(now.getFullYear(), month, day + 1);
    if (now >= endOfDay) t = new Date(now.getFullYear() + 1, month, day);
    return t;
  }
  function show(prefix, target, now, sleeps) {
    const ms = Math.max(0, target - now);
    const s = Math.floor(ms / 1000);
    const days = Math.floor(s / 86400);
    $(`${prefix}-days`).innerHTML = `${days}<small> ${days === 1 ? 'day' : 'days'}</small>`;
    $(`${prefix}-hms`).textContent = `${pad(Math.floor((s % 86400) / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
    $(`${prefix}-date`).textContent = target.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    if (sleeps) {
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const n = Math.round((target - today) / 86400000);
      $(`${prefix}-sleeps`).textContent = n === 0 ? "It's Christmas! 🎄" : `${n} ${n === 1 ? 'sleep' : 'sleeps'}`;
    }
  }
  function tick() {
    const now = new Date();
    show('cd-xmas', next(11, 25, now), now, true);
    show('cd-ny', next(0, 1, now), now, false);
  }
  tick();
  setInterval(tick, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.calc;
  if (page === 'xmas') initCountdown();
  if (page === 'awg') initAwg();
  if (page === 'wire') initWireSize();
  if (page === 'pool') initPool();
  if (page === 'bread') initBread();
  if (page === 'lye') initLye();
  if (page === 'hvac') initHvac();
  if (page === 'vd') initVoltageDrop();
  if (page === 'coat') initCoat();
});
