// Extras for the reference pages (pages_hvac.py, pages_electrical.py): the print button, example readings and the
// refrigerant from the address on the superheat calculators, and the target superheat lookup. Loaded after calc.js
// where a page has a calculator; everything lives inside one function so no name here can clash with calc.js.
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

  // The refrigerant named in the address, for the shared calculator: #r-454b, or ?ref=R-454B.
  function refFromAddress(hash, search, ids) {
    const query = (String(search || '').match(/[?&]ref=([^&#]*)/) || [])[1] || '';
    for (const raw of [String(hash || '').replace(/^#/, ''), query]) {
      let want = raw;
      try { want = decodeURIComponent(raw); } catch (err) { /* keep it as typed */ }
      want = want.trim().toLowerCase();
      const hit = want && ids.find((id) => id.toLowerCase() === want);
      if (hit) return hit;
    }
    return null;
  }

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // Superheat and subcooling calculators. The fields start with example readings; changing the refrigerant or the
  // mode swaps in that example, unless the user has already typed their own. On the shared calculator the
  // refrigerant can come from the address, and the line under the select says where its data comes from.
  function initExamples() {
    const all = window.HVAC_EXAMPLES, pages = window.HVAC_PAGES || {};
    const sel = byId('ref'), p = byId('p'), t = byId('t'), pt = byId('pt-in'), info = byId('ref-info');
    let rid = sel.value, mode = 'sh';

    function show(nextRid, nextMode) {
      const from = all[rid], to = all[nextRid];
      if (from && to) {
        if (p.value === String(from[mode][0]) && t.value === String(from[mode][1])) {
          p.value = to[nextMode][0];
          t.value = to[nextMode][1];
        }
        const lookup = byId('ptmode').querySelector('button[aria-pressed="true"]');
        if (nextRid !== rid && lookup && lookup.dataset.v === 'p2t' && pt.value === String(from.sh[0])) pt.value = to.sh[0];
      }
      rid = nextRid;
      mode = nextMode;
      p.dispatchEvent(new Event('input'));
      pt.dispatchEvent(new Event('input'));
    }

    function describe() {
      const r = info && window.PT_DATA[rid];
      if (!r) return;
      const columns = r.dew ? 'two columns: dew point for superheat, bubble point for subcooling' : 'one pressure column';
      const slug = rid.toLowerCase();
      let html = `${esc(rid)} · ASHRAE ${esc(r.safety)} · ${columns}. Data: ${esc(r.source)}. `
        + `<a href="${info.dataset.charts}${slug}.html">${esc(rid)} PT chart</a>`;
      if (pages[rid]) html += ` · <a href="${pages[rid]}">${esc(rid)} worked examples</a>`;
      info.innerHTML = html;
    }

    byId('mode').addEventListener('click', (ev) => {
      const b = ev.target.closest('button');
      if (b) show(rid, b.dataset.v);
    });
    if (sel.tagName !== 'SELECT') return;

    const ids = Array.from(sel.options).map((o) => o.value);
    function fromAddress(scroll) {
      const want = refFromAddress(window.location.hash, window.location.search, ids);
      if (!want) return;
      if (want !== sel.value) {
        sel.value = want;
        show(want, mode);
        describe();
        sel.dispatchEvent(new Event('change'));
      }
      if (scroll) sel.closest('.calc').scrollIntoView({ block: 'start' });
    }
    sel.addEventListener('change', () => {
      if (sel.value === rid) return;
      show(sel.value, mode);
      describe();
      if (window.history && window.history.replaceState) window.history.replaceState(null, '', '#' + sel.value.toLowerCase());
    });
    window.addEventListener('hashchange', () => fromAddress(true));
    describe();
    fromAddress(false);
  }

  window.RefPages = { targetSuperheat, refFromAddress };

  if (typeof document === 'undefined' || !document.addEventListener) return;
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-print]').forEach((b) => b.addEventListener('click', () => window.print()));
    if (window.HVAC_EXAMPLES && byId('mode')) initExamples();
    if (window.TSH_TABLE && byId('tsh-out')) initTargetSuperheat();
  });
})();
