// Runs the checked examples in verification.json through the real assets/calc.js and prints the answers as JSON.
//
//   node tools/verify.mjs [site dir]        (build.py runs it; tests/verification.test.mjs asserts on it)
//
// Each case names a calculator page, the inputs to change and the output to read. The page's own HTML gives the
// starting values, calc.js runs unchanged against a small stand-in for the browser DOM, and the case's inputs are
// applied the way a person would: press a segment button, type a value, read the result.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SITE = process.argv[2] || path.join(ROOT, 'site');

const strip = (s) => String(s ?? '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const numbers = (s) => (strip(s).replace(/(\d),(?=\d{3})/g, '$1').match(/-?\d+(?:\.\d+)?/g) || []).map(Number);

function optionsOf(html) {
  return [...String(html).matchAll(/<option\b([^>]*)>([^<]*)/g)].map(([, attrs, label]) => ({
    value: (attrs.match(/value="([^"]*)"/) || [null, label.trim()])[1],
    label: label.trim(),
    selected: /\bselected\b/.test(attrs),
  }));
}

class El {
  constructor(id) {
    this.id = id; this.value = ''; this.text = ''; this.hidden = false; this.className = '';
    this.handlers = {}; this.children = []; this.buttons = null; this.options = [];
    this.dataset = {}; this.firstChild = { textContent: '' };
  }
  set innerHTML(v) {
    this.text = v;
    const opts = optionsOf(v);
    if (opts.length) { this.options = opts; this.value = (opts.find((o) => o.selected) || opts[0]).value; }
  }
  get innerHTML() { return this.text; }
  set textContent(v) { this.text = v; }
  get textContent() { return strip(this.text); }
  addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }
  fire(type, event = {}) { (this.handlers[type] || []).forEach((fn) => fn(event)); }
  appendChild(child) { this.children.push(child); }
  setAttribute() {}
  querySelectorAll(sel) {
    if (sel === 'button') return this.buttons || [];
    if (sel === '.oilrow') return this.children;
    return [];
  }
  querySelector(sel) {
    if (sel === 'button[aria-pressed="true"]' && this.buttons) return this.buttons.find((b) => b.pressed);
    return new El(`${this.id} ${sel}`);
  }
  // A person picks a select option by its label; plain inputs take the text as typed.
  set(v) {
    const o = this.options.find((x) => x.label === String(v) || x.value === String(v));
    this.value = o ? o.value : String(v);
  }
}

// One row of the lye calculator's oil list, as calc.js builds it.
class OilRow {
  constructor() { this.select = new El('oil'); this.input = new El('grams'); }
  set innerHTML(v) {
    this.select.innerHTML = v;
    this.input.value = (v.match(/<input\b[^>]*value="([^"]*)"/) || [null, ''])[1];
  }
  querySelector(sel) { return sel === 'select' ? this.select : sel === 'input' ? this.input : new El(sel); }
  querySelectorAll() { return [this.select, this.input]; }
  remove() {}
}

function pageDom(html) {
  const els = new Map();
  const get = (id) => { if (!els.has(id)) els.set(id, new El(id)); return els.get(id); };
  for (const [tag] of html.matchAll(/<input\b[^>]*>/g)) {
    const id = (tag.match(/\bid="([^"]+)"/) || [])[1];
    if (id) get(id).value = (tag.match(/\bvalue="([^"]*)"/) || [null, ''])[1];
  }
  for (const [, attrs, inner] of html.matchAll(/<select\b([^>]*)>([\s\S]*?)<\/select>/g)) {
    const id = (attrs.match(/\bid="([^"]+)"/) || [])[1];
    if (id) get(id).innerHTML = inner;
  }
  for (const [, id, inner] of html.matchAll(/<div class="seg" id="([^"]+)"[^>]*>([\s\S]*?)<\/div>/g)) {
    get(id).buttons = [...inner.matchAll(/<button\b([^>]*)>/g)].map(([, attrs]) => {
      const b = { dataset: { v: (attrs.match(/data-v="([^"]*)"/) || [])[1] }, pressed: /aria-pressed="true"/.test(attrs) };
      b.setAttribute = (_name, val) => { b.pressed = val === 'true'; };
      b.closest = () => b;
      return b;
    });
  }
  return { els, get };
}

function load() {
  const spec = JSON.parse(fs.readFileSync(path.join(ROOT, 'verification.json'), 'utf8'));
  const calcJs = fs.readFileSync(path.join(ROOT, 'assets', 'calc.js'), 'utf8');
  const ptJs = fs.readFileSync(path.join(SITE, 'assets', 'pt-data.js'), 'utf8');
  return { spec, calcJs, ptJs };
}

function runCase(c, spec, calcJs, ptJs) {
  const { page, init } = spec.calculators[c.calc];
  const html = fs.readFileSync(path.join(SITE, page), 'utf8');
  const dom = pageDom(html);
  const document = {
    getElementById: dom.get,
    createElement: () => new OilRow(),
    addEventListener() {},
    body: { dataset: {} },
  };
  const ctx = vm.createContext({ document, console, setInterval() {}, Intl, Math, Number, String, Date });
  ctx.window = ctx;
  vm.runInContext(ptJs, ctx);
  const oils = html.match(/window\.OILS = (\[[\s\S]*?\]);/);
  if (oils) ctx.OILS = JSON.parse(oils[1]);
  vm.runInContext(calcJs, ctx);
  vm.runInContext(`${init}()`, ctx);

  for (const [id, v] of Object.entries(c.press || {})) {
    const root = dom.get(id);
    const b = (root.buttons || []).find((x) => x.dataset.v === v);
    if (!b) throw new Error(`${c.id}: no button "${v}" in #${id} on ${page}`);
    root.fire('click', { target: b });
  }
  for (const [id, v] of Object.entries(c.set || {})) {
    if (!dom.els.has(id)) throw new Error(`${c.id}: no field #${id} on ${page}`);
    const el = dom.get(id);
    el.set(v);
    el.fire('input'); el.fire('change');
  }
  if (c.oils) {
    dom.get('oils').children = c.oils.map(([id, grams]) => {
      const row = new OilRow();
      row.select.value = id; row.input.value = String(grams);
      return row;
    });
    dom.get('sf').fire('input');
  }
  if (!dom.els.has(c.read)) throw new Error(`${c.id}: calc.js never wrote #${c.read} on ${page}`);
  const text = strip(dom.get(c.read).innerHTML);
  const out = { id: c.id, text };
  if ('expect_text' in c) {
    out.ok = text === c.expect_text;
  } else {
    out.value = numbers(text)[c.pick || 0];
    out.diff = out.value - c.expect;
    out.ok = Number.isFinite(out.value) && Math.abs(out.diff) <= c.tolerance + 1e-9;
  }
  return out;
}

export function verify() {
  const { spec, calcJs, ptJs } = load();
  return spec.cases.map((c) => runCase(c, spec, calcJs, ptJs));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.stdout.write(JSON.stringify(verify(), null, 1) + '\n');
}
