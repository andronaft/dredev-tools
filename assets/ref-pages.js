// Extras for the reference pages (pages_hvac.py, pages_electrical.py): the print button, example readings on the
// per-refrigerant calculators and the target superheat lookup. Loaded after calc.js where a page has a calculator;
// everything lives inside one function so no name here can clash with calc.js.
(function () {
  const byId = (id) => document.getElementById(id);
  const val = (id) => parseFloat(String(byId(id).value).replace(',', '.'));
  const one = (v) => v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  // Target superheat for a fixed orifice: bilinear between the cells of the manufacturer's charging table.
  // Mirrors TargetSuperheatTable.lookup in hvac-charge-app/lib/feature/engine/charge.dart.
  function bracket(axis, x) {
    for (let i = 0; i < axis.length - 1; i++) {
      if (x <= axis[i + 1]) return [i, i + 1, (x - axis[i]) / (axis[i + 1] - axis[i])];
    }
    return [axis.length - 2, axis.length - 1, 1];
  }

  function targetSuperheat(table, outdoor, wetBulb) {
    const od = table.outdoorF, wb = table.wetBulbF, cells = table.superheatF;
    if (!(outdoor >= od[0] && outdoor <= od[od.length - 1] && wetBulb >= wb[0] && wetBulb <= wb[wb.length - 1])) return { kind: 'range' };
    const [r0, r1, fr] = bracket(od, outdoor);
    const [c0, c1, fc] = bracket(wb, wetBulb);
    const corners = [cells[r0][c0], cells[r0][c1], cells[r1][c0], cells[r1][c1]];
    const needed = [(1 - fr) * (1 - fc) > 1e-9, (1 - fr) * fc > 1e-9, fr * (1 - fc) > 1e-9, fr * fc > 1e-9];
    for (let i = 0; i < 4; i++) if (needed[i] && corners[i] == null) return { kind: 'none' };
    const v = corners.map((x) => x || 0);
    const top = v[0] + (v[1] - v[0]) * fc;
    const bottom = v[2] + (v[3] - v[2]) * fc;
    return { kind: 'value', value: top + (bottom - top) * fr, rows: [od[r0], od[r1]], cols: [wb[c0], wb[c1]] };
  }

  function initTargetSuperheat() {
    const table = window.TSH_TABLE;
    function run() {
      const od = val('tsh-od'), wb = val('tsh-wb');
      const msg = byId('tsh-msg');
      msg.className = 'verdict';
      msg.textContent = '';
      byId('tsh-k').textContent = '–';
      byId('tsh-cells').textContent = '–';
      if (!Number.isFinite(od) || !Number.isFinite(wb)) { byId('tsh-out').textContent = '–'; return; }
      const r = targetSuperheat(table, od, wb);
      if (r.kind === 'value') {
        byId('tsh-out').innerHTML = `${one(r.value)}<small> °F</small>`;
        byId('tsh-k').textContent = `${one((r.value * 5) / 9)} K`;
        byId('tsh-cells').textContent = `${r.rows[0]}–${r.rows[1]} °F outdoor, ${r.cols[0]}–${r.cols[1]} °F wet bulb`;
      } else if (r.kind === 'none') {
        byId('tsh-out').textContent = 'No target';
        msg.className = 'verdict warn';
        msg.textContent = 'The table has a dash here: do not set the charge by superheat in these conditions. Weigh in the charge.';
      } else {
        byId('tsh-out').textContent = 'Outside the table';
        msg.className = 'verdict warn';
        msg.textContent = `The table covers ${table.outdoorF[0]}–${table.outdoorF[table.outdoorF.length - 1]} °F outdoors and ${table.wetBulbF[0]}–${table.wetBulbF[table.wetBulbF.length - 1]} °F indoor wet bulb.`;
      }
    }
    ['tsh-od', 'tsh-wb'].forEach((id) => byId(id).addEventListener('input', run));
    run();
  }

  // On a per-refrigerant calculator, switching between superheat and subcooling swaps in that mode's example
  // readings, unless the user has already typed their own.
  function initExamples() {
    const ex = window.HVAC_EXAMPLE, p = byId('p'), t = byId('t');
    byId('mode').addEventListener('click', (ev) => {
      const b = ev.target.closest('button');
      if (!b) return;
      const to = ex[b.dataset.v], from = ex[b.dataset.v === 'sh' ? 'sc' : 'sh'];
      if (to && from && p.value === String(from[0]) && t.value === String(from[1])) {
        p.value = to[0];
        t.value = to[1];
        p.dispatchEvent(new Event('input'));
      }
    });
  }

  window.RefPages = { targetSuperheat };

  if (typeof document === 'undefined' || !document.addEventListener) return;
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-print]').forEach((b) => b.addEventListener('click', () => window.print()));
    if (window.HVAC_EXAMPLE && byId('mode')) initExamples();
    if (window.TSH_TABLE && byId('tsh-out')) initTargetSuperheat();
  });
})();
