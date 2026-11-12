// Runs the site's real calculator code (assets/calc.js, assets/ref-pages.js) in Node with a stub page, so the tests
// can ask "what would the live calculator show for these inputs?". Reads {ops: [...]} on stdin, prints the results.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const els = {};
function mk() {
  const o = {
    value: '', textContent: '', innerHTML: '', className: '', hidden: false, dataset: {}, listeners: {}, seg: null,
    firstChild: { textContent: '' },
    addEventListener(type, fn) { o.listeners[type] = fn; },
    dispatchEvent() {},
    querySelectorAll() { return []; },
    querySelector(sel) { return sel.includes('aria-pressed') ? { dataset: { v: o.seg } } : { textContent: '' }; },
  };
  return o;
}
const document = {
  body: { dataset: {} },
  getElementById(id) { return els[id] || (els[id] = mk()); },
  addEventListener() {},
  querySelectorAll() { return []; },
};
const ctx = vm.createContext({ document, console, Event: function () {} });
ctx.window = ctx;
const root = path.join(__dirname, '..', 'assets');
vm.runInContext(fs.readFileSync(path.join(root, 'calc.js'), 'utf8'), ctx);
vm.runInContext(fs.readFileSync(path.join(root, 'ref-pages.js'), 'utf8'), ctx);
const run = (code) => vm.runInContext(code, ctx);
const reset = () => Object.keys(els).forEach((k) => delete els[k]);
const el = (id) => document.getElementById(id);

const ops = {
  eval: (o) => run(o.code),
  hvac(o) {
    reset();
    ctx.PT_DATA = { [o.rid]: o.data };
    el('ref').value = o.rid;
    el('mode').seg = o.mode;
    el('ptmode').seg = o.ptmode || 'p2t';
    el('p').value = String(o.p);
    el('t').value = String(o.t);
    el('pt-in').value = String(o.ptin === undefined ? o.p : o.ptin);
    run('initHvac()');
    return { out: el('out').innerHTML, sat: el('sat').textContent, pt: el('pt-out').innerHTML };
  },
  wire(o) {
    reset();
    el('amps').value = String(o.amps);
    el('wire').value = o.wire || 'thhn';
    el('cond').seg = o.cond || 'cu';
    el('cont').seg = o.cont ? 'yes' : 'no';
    el('term').value = String(o.term || 75);
    el('phase').value = o.phase || 'single';
    el('len').value = o.len === undefined ? '' : String(o.len);
    el('volts').value = String(o.volts || 240);
    run('initWireSize()');
    return { size: el('ws-size').innerHTML, ocpd: el('ws-ocpd').textContent, amp: el('ws-amp').textContent, drop: el('ws-drop').textContent };
  },
  vd(o) {
    reset();
    el('std').seg = 'nec';
    el('supply').seg = o.supply || 'single';
    el('cond').seg = o.cond || 'cu';
    el('amps').value = String(o.amps);
    el('pf').value = '1';
    run('initVoltageDrop()');
    el('size').value = String(run(`sizesFor('nec').findIndex((s) => s.label === ${JSON.stringify(o.size)})`));
    el('len').value = String(o.len);
    el('volts').value = String(o.volts);
    el('size').listeners.change();
    return { pct: el('vd-pct').innerHTML, v: el('vd-v').textContent, min: el('vd-min').textContent };
  },
  tsh: (o) => run(`RefPages.targetSuperheat(${JSON.stringify(o.table)}, ${o.od}, ${o.wb})`),
};

const input = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(input.ops.map((o) => ops[o.op](o))));
