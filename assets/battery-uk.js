// Battery and UPS runtime, the Ukrainian page electrical/uk/battery-runtime.html (pages_electrical.py).
// The runtime and capacity formulas are the Electrician Calc app's (lib/feature/engine/electrical.dart); calc_math.py
// has the same functions for the static table and the worked example, and tests/test_calc_math.py checks both.
(function () {
  'use strict';

  const ceilCount = (v) => (Number.isFinite(v) && v > 0 ? Math.ceil(v - 1e-9) : 0);

  // batteryRuntime and batteryCapacityFor as in electrical.dart; the bank, the charge time and the battery count are this page's own.
  const batteryBank = (volts, ah, series, parallel) => ({ volts: volts * series, ah: ah * parallel, wh: volts * series * ah * parallel });
  const batteryRuntime = (volts, ah, count, loadW, dod, eff) => (loadW > 0 ? (volts * ah * count * dod * eff) / loadW : 0);
  const batteryCapacityFor = (volts, loadW, hours, dod, eff) => (loadW * hours) / (volts * dod * eff);
  const chargeHours = (ah, amps, chargeEff) => (amps > 0 && chargeEff > 0 ? ah / (amps * chargeEff) : 0);
  function batteriesFor(needAh, ahOne, series) {
    const strings = ahOne > 0 ? ceilCount(needAh / ahOne) : 0;
    return { strings, total: strings * series };
  }

  const math = { batteryBank, batteryRuntime, batteryCapacityFor, chargeHours, batteriesFor };
  if (typeof module !== 'undefined' && module.exports) { module.exports = math; return; }

  const $ = (id) => document.getElementById(id);
  const num = (id) => parseFloat(String($(id).value).replace(',', '.'));
  const set = (id, text) => { const el = $(id); if (el) el.textContent = text; };
  function listen(ids, run) {
    ids.forEach((id) => { const el = $(id); if (el) el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', run); });
  }
  function verdict(id, cls, text) { const v = $(id); if (v) { v.className = cls ? `verdict ${cls}` : 'verdict'; v.textContent = text; } }

  /* Battery and UPS runtime (Ukrainian page, metric units) */
  function initBattery() {
    const uk = (v, d = 1) => (Number.isFinite(v) ? v.toLocaleString('uk-UA', { minimumFractionDigits: d, maximumFractionDigits: d }) : '–');
    const ukt = (v, d = 2) => (Number.isFinite(v) ? v.toLocaleString('uk-UA', { maximumFractionDigits: d }) : '–');
    const hm = (t) => {
      if (!(t > 0) || !Number.isFinite(t)) return '–';
      if (t >= 100) return `${ukt(t, 0)} год`;
      let h = Math.floor(t), m = Math.round((t - h) * 60);
      if (m === 60) { h += 1; m = 0; }
      return `${h} год ${String(m).padStart(2, '0')} хв`;
    };
    // Usable depth, charge (coulombic) efficiency and the charge current the cited datasheets recommend, per C.
    const TYPES = { agm: { dod: 50, ceff: 90, c: 0.2 }, lfp: { dod: 80, ceff: 99, c: 0.5 } };
    $('bt-type').addEventListener('change', () => {
      const t = TYPES[$('bt-type').value];
      $('bt-dod').value = t.dod;
      $('bt-ceff').value = t.ceff;
      run();
    });
    document.querySelectorAll('#bt-presets button').forEach((b) => b.addEventListener('click', () => {
      const w = +b.dataset.w;
      const now = num('bt-load');
      $('bt-load').value = w === 0 ? '0' : String(Math.round(((Number.isFinite(now) ? now : 0) + w) * 10) / 10);
      run();
    }));
    function run() {
      const v = +$('bt-v').value, ah = num('bt-ah'), s = Math.round(num('bt-s')), p = Math.round(num('bt-p'));
      const dod = num('bt-dod') / 100, eff = num('bt-eff') / 100, ceff = num('bt-ceff') / 100;
      const load = num('bt-load'), amps = num('bt-amps'), hours = num('bt-hours');
      const t = TYPES[$('bt-type').value];
      const ok = ah > 0 && s >= 1 && p >= 1 && dod > 0 && dod <= 1 && eff > 0 && eff <= 1;
      const steps = [];
      if (!ok) {
        $('bt-time').textContent = '–';
        ['bt-wh', 'bt-use', 'bt-cur', 'bt-charge', 'bt-crate', 'bt-need', 'bt-count'].forEach((id) => set(id, '–'));
        $('bt-steps').innerHTML = '';
        verdict('bt-note', 'warn', 'Перевірте ємність, кількість АКБ, глибину розряду і ККД (від 1 до 100 %).');
        return;
      }
      const bank = batteryBank(v, ah, s, p), n = s * p;
      const usable = bank.wh * dod * eff;
      steps.push(`Банк: ${s} послідовно × ${p} паралельно = ${n} АКБ, ${ukt(bank.volts)} В × ${ukt(bank.ah)} А·год.`);
      steps.push(`Енергія: U × А·год = ${ukt(bank.volts)} × ${ukt(bank.ah)} = ${ukt(bank.wh, 0)} Вт·год (${uk(bank.wh / 1000, 2)} кВт·год).`);
      steps.push(`Корисна енергія: ${ukt(bank.wh, 0)} × ${ukt(dod)} (глибина розряду) × ${ukt(eff)} (ККД інвертора) = ${ukt(usable, 0)} Вт·год.`);
      set('bt-wh', `${uk(bank.wh / 1000, 2)} кВт·год · ${ukt(bank.volts)} В × ${ukt(bank.ah)} А·год`);
      set('bt-use', `${uk(usable / 1000, 2)} кВт·год`);
      if (load > 0) {
        const time = batteryRuntime(v, ah, n, load, dod, eff);
        $('bt-time').textContent = hm(time);
        set('bt-cur', `${uk(load / eff / bank.volts, 1)} А`);
        steps.push(`Час роботи: ${ukt(usable, 0)} Вт·год ÷ ${ukt(load)} Вт = ${uk(time, 2)} год (${hm(time)}).`);
        steps.push(`Струм з АКБ: ${ukt(load)} Вт ÷ ${ukt(eff)} ÷ ${ukt(bank.volts)} В = ${uk(load / eff / bank.volts, 1)} А.`);
      } else {
        $('bt-time').textContent = '–';
        set('bt-cur', '–');
      }
      const back = bank.ah * dod;
      if (amps > 0 && ceff > 0) {
        const ch = chargeHours(back, amps, ceff), crate = amps / bank.ah;
        set('bt-charge', hm(ch));
        set('bt-crate', `${uk(crate, 2)} C`);
        steps.push(`Заряд: ${ukt(bank.ah)} А·год × ${ukt(dod)} = ${ukt(back, 1)} А·год; ${ukt(back, 1)} ÷ (${ukt(amps)} А × ${ukt(ceff)}) = ${uk(ch, 1)} год.`);
        const limit = t.c * bank.ah;
        if ($('bt-type').value === 'agm') {
          verdict('bt-note', crate > t.c + 1e-9 ? 'warn' : '', crate > t.c + 1e-9
            ? `Струм заряду ${uk(crate, 2)} C більший за 0,2 C (${ukt(limit, 0)} А для цього банку), який радить паспорт AGM і гелевих АКБ Victron. Перевірте паспорт своїх АКБ.`
            : 'Для AGM і гелю це час основного етапу. Останню частину заряду (за Battery University, близько 30 %) батарея добирає меншим струмом, тож повний заряд триває довше.');
        } else {
          verdict('bt-note', crate > t.c + 1e-9 ? 'warn' : '', crate > t.c + 1e-9
            ? `Струм заряду ${uk(crate, 2)} C більший за 0,5 C (${ukt(limit, 0)} А для цього банку), рекомендований для LiFePO4 Victron. Перевірте паспорт і налаштування BMS своїх АКБ.`
            : 'BMS LiFePO4 може зменшувати струм заряду на холоді, тоді заряд триває довше.');
        }
      } else {
        set('bt-charge', '–');
        set('bt-crate', '–');
        verdict('bt-note', '', '');
      }
      if (load > 0 && hours > 0) {
        const need = batteryCapacityFor(bank.volts, load, hours, dod, eff);
        const fit = batteriesFor(need, ah, s);
        set('bt-need', `${ukt(need, 0)} А·год при ${ukt(bank.volts)} В · ${uk(need * bank.volts / 1000, 2)} кВт·год`);
        set('bt-count', `${fit.total} × ${ukt(v)} В ${ukt(ah)} А·год (${s} посл. × ${fit.strings} пар.)`);
        steps.push(`На ${ukt(hours)} год: ${ukt(load)} × ${ukt(hours)} ÷ (${ukt(bank.volts)} × ${ukt(dod)} × ${ukt(eff)}) = ${ukt(need, 0)} А·год; `
          + `${ukt(need, 0)} ÷ ${ukt(ah)}, округлено вгору: гілок паралельно ${fit.strings}, у кожній ${s} АКБ, разом ${fit.total}.`);
      } else {
        set('bt-need', '–');
        set('bt-count', '–');
      }
      $('bt-steps').innerHTML = steps.map((x) => `<li>${x}</li>`).join('');
    }
    listen(['bt-v', 'bt-ah', 'bt-s', 'bt-p', 'bt-dod', 'bt-eff', 'bt-ceff', 'bt-load', 'bt-amps', 'bt-hours'], run);
    run();
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.calc === 'battery') initBattery();
  });
})();
