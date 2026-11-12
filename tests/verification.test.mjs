// The checked examples of verification.json against the real assets/calc.js, on the built site/.
//
//   python3 build.py && node --test "tests/*.test.mjs"
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { verify } from '../tools/verify.mjs';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const spec = JSON.parse(fs.readFileSync(path.join(ROOT, 'verification.json'), 'utf8'));
const results = new Map(verify().map((r) => [r.id, r]));

test('case ids are unique and every case names a known calculator and source', () => {
  assert.equal(new Set(spec.cases.map((c) => c.id)).size, spec.cases.length);
  for (const c of spec.cases) {
    assert.ok(spec.calculators[c.calc], `${c.id}: calculator ${c.calc}`);
    assert.ok(spec.sources[c.source], `${c.id}: source ${c.source}`);
  }
});

for (const c of spec.cases) {
  test(`${c.id}: ${c.title}`, () => {
    const r = results.get(c.id);
    if ('expect_text' in c) assert.equal(r.text, c.expect_text);
    else assert.ok(r.ok, `source ${c.expect} ${c.unit} ± ${c.tolerance}, calculator answered "${r.text}"`);
  });
}

test('the page shows the same answers the calculator gives now', () => {
  const html = fs.readFileSync(path.join(ROOT, 'site', 'verification.html'), 'utf8');
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  for (const r of results.values()) assert.ok(html.includes(`<b>${esc(r.text)}</b>`), `${r.id}: "${r.text}" is not on verification.html`);
});
