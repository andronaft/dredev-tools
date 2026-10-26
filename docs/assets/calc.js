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

document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.calc;
  if (page === 'hvac') initHvac();
  if (page === 'vd') initVoltageDrop();
  if (page === 'coat') initCoat();
});
