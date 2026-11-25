// Ukrainian embeddable widgets (embed/uk/): voltage drop and the cable from the battery to the inverter, metric units.
// The voltage drop formula and constants are calc.js's dropVolts() in IEC mode (resistivity 0.0225 / 0.036 Ω·mm²/m,
// reactance 0.08 mΩ/m), so the numbers match the English voltage drop calculator set to IEC · mm² · m.
// The current-carrying capacities are the Electrician Calc app's (lib/feature/engine/iec_tables.dart): IEC 60364-5-52,
// Table B.52.2, PVC 70 °C, two loaded copper conductors, reference method C (cable clipped direct), ambient 30 °C.
(function () {
  'use strict';

  const RHO_IEC = { cu: 0.0225, al: 0.036 };
  const REACTANCE = 0.00008;
  const SIZES = [0.5, 0.75, 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300];
  // Table B.52.2, method C, indexed like AMP_SIZES.
  const AMP_SIZES = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240];
  const AMP_C = [19.5, 27, 36, 46, 63, 85, 112, 138, 168, 213, 258, 299, 344, 392, 461];

  function dropVolts({ supply, cond, mm2, metres, amps, pf }) {
    const ac = supply !== 'dc';
    const z = (RHO_IEC[cond] / mm2) * (ac ? pf : 1) + (ac ? REACTANCE * Math.sqrt(Math.max(0, 1 - pf * pf)) : 0);
    return (supply === 'three' ? Math.sqrt(3) : 2) * amps * metres * z;
  }

  // The cable from a battery to an inverter: DC current from the inverter's power and efficiency, the smallest
  // copper size within the drop limit, the smallest whose capacity covers the current, and the larger of the two.
  function inverterCable({ volts, watts, eff, metres, limit }) {
    const amps = watts / (volts * eff);
    const dv = (mm2) => dropVolts({ supply: 'dc', cond: 'cu', mm2, metres, amps });
    const byDrop = SIZES.find((a) => (dv(a) / volts) * 100 <= limit) || null;
    const k = AMP_C.findIndex((a) => a >= amps);
    const byAmps = k < 0 ? null : AMP_SIZES[k];
    const out = { amps, byDrop, byAmps, size: null };
    if (!byDrop || !byAmps) return out;
    const size = Math.max(byDrop, byAmps);
    const d = dv(size);
    return { ...out, size, dv: d, pct: (d / volts) * 100, lossW: d * amps, rated: AMP_C[AMP_SIZES.indexOf(size)] };
  }

  const math = { dropVolts, inverterCable, SIZES, AMP_SIZES, AMP_C };
  if (typeof module !== 'undefined' && module.exports) { module.exports = math; return; }

  const $ = (id) => document.getElementById(id);
  const num = (id) => parseFloat(String($(id).value).replace(',', '.'));
  const uk = (v, d = 1) => (Number.isFinite(v) ? v.toLocaleString('uk-UA', { minimumFractionDigits: d, maximumFractionDigits: d }) : '–');
  const mm = (a) => `${String(a).replace('.', ',')} мм²`;
  function segmented(id, onChange) {
    const box = $(id);
    let value = box.querySelector('[aria-pressed="true"]').dataset.v;
    box.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
      value = b.dataset.v;
      box.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      onChange();
    }));
    return () => value;
  }
  function verdict(id, cls, text) { const v = $(id); v.className = cls ? `verdict ${cls}` : 'verdict'; v.textContent = text; }
  function listen(ids, run) {
    ids.forEach((id) => { const el = $(id); el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', run); });
  }

  /* Voltage drop, IEC · mm² · m */
  function initVd() {
    const supply = segmented('supply', () => { $('volts').value = supply() === 'three' ? '400' : supply() === 'dc' ? '12' : '230'; run(); });
    const cond = segmented('cond', run);
    $('size').innerHTML = SIZES.map((a, i) => `<option value="${i}"${a === 2.5 ? ' selected' : ''}>${mm(a)}</option>`).join('');
    function run() {
      const metres = num('len'), amps = num('amps'), volts = num('volts');
      let pf = num('pf');
      if (!Number.isFinite(pf) || pf <= 0 || pf > 1) pf = 1;
      $('pf').parentElement.hidden = supply() === 'dc';
      const ok = [metres, amps, volts].every((v) => Number.isFinite(v) && v > 0);
      const args = { supply: supply(), cond: cond(), metres, amps, pf };
      const dv = dropVolts({ ...args, mm2: SIZES[+$('size').value] });
      const pct = (dv / volts) * 100;
      $('vd-pct').innerHTML = ok ? `${uk(pct, 2)}<small> %</small>` : '–';
      $('vd-v').textContent = ok ? `${uk(dv, 2)} В` : '–';
      $('vd-end').textContent = ok ? `${uk(volts - dv, 1)} В` : '–';
      const fit = ok ? SIZES.find((a) => (dropVolts({ ...args, mm2: a }) / volts) * 100 <= 3) : null;
      $('vd-min').textContent = !ok ? '–' : fit ? mm(fit) : 'більше за 300 мм² (паралельні жили)';
      if (!ok) verdict('vd-verdict', '', '');
      else if (pct <= 3) verdict('vd-verdict', 'good', 'До 3 %: в межах рекомендації IEC 60364-5-52 навіть для освітлення.');
      else if (pct <= 5) verdict('vd-verdict', 'warn', 'Від 3 до 5 %: прийнятно для розеток і силових ліній, але не для освітлення. Розгляньте більший переріз.');
      else verdict('vd-verdict', 'bad', 'Понад 5 %: збільште переріз або вкоротіть лінію.');
    }
    listen(['size', 'len', 'amps', 'volts', 'pf'], run);
    run();
  }

  /* Cable from the battery to the inverter */
  function initCable() {
    const preset = segmented('ic-vpre', () => { $('ic-v').value = preset(); run(); });
    const limitSeg = segmented('ic-limit', run);
    function run() {
      const volts = num('ic-v'), watts = num('ic-w'), eff = num('ic-eff') / 100, metres = num('ic-len');
      const limit = +limitSeg();
      $('ic-limit-label').textContent = `Найменший переріз для падіння ≤ ${limit} %`;
      const ok = [volts, watts, metres].every((v) => Number.isFinite(v) && v > 0) && eff > 0 && eff <= 1;
      const set = (id, t) => { $(id).textContent = t; };
      if (!ok) {
        $('ic-size').textContent = '–';
        ['ic-amps', 'ic-bydrop', 'ic-byamps', 'ic-drop', 'ic-loss'].forEach((id) => set(id, '–'));
        verdict('ic-verdict', 'warn', 'Перевірте напругу, потужність, довжину і ККД (від 1 до 100 %).');
        return;
      }
      const r = inverterCable({ volts, watts, eff, metres, limit });
      $('ic-size').innerHTML = r.size ? `${mm(r.size)}<small> мідь</small>` : 'один кабель не підходить';
      set('ic-amps', `${uk(r.amps, 1)} А`);
      set('ic-bydrop', r.byDrop ? mm(r.byDrop) : 'понад 300 мм²');
      set('ic-byamps', r.byAmps ? mm(r.byAmps) : 'понад 240 мм²');
      set('ic-drop', r.size ? `${uk(r.dv, 2)} В · ${uk(r.pct, 2)} %` : '–');
      set('ic-loss', r.size ? `${uk(r.lossW, 1)} Вт` : '–');
      if (!r.size) verdict('ic-verdict', 'bad', 'Струм завеликий для одного кабелю. Візьміть банк і інвертор на вищу напругу (24 або 48 В) або вкоротіть кабель.');
      else if (r.size === r.byAmps && r.byAmps > r.byDrop) verdict('ic-verdict', 'warn', `За падінням напруги вистачило б ${mm(r.byDrop)}, але струм ${uk(r.amps, 0)} А потребує ${mm(r.byAmps)} (до ${uk(r.rated, 0)} А).`);
      else verdict('ic-verdict', 'good', `Переріз визначає падіння напруги. Якщо інструкція інвертора вимагає більший кабель, беріть більший.`);
    }
    listen(['ic-v', 'ic-w', 'ic-eff', 'ic-len'], run);
    run();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.calc;
    if (page === 'vd-uk') initVd();
    if (page === 'cable-uk') initCable();
  });
})();
