import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { convert, convertResult, explain, LifeFromUnitsError, normalizeUnit, sameUnit, SPEC } from '../src/index.js';

const ambiguous = (e: unknown): boolean => e instanceof LifeFromUnitsError && e.code === 'ambiguous_unit';

test('Spanish WBC 7,5 mil/mm3 with locale es is 7.5 x10^3/µL', () => {
  assert.equal(convert('7,5', 'mil/mm3', '10^3/µL', null, null, { locale: 'es' }), 7.5);
  assert.equal(convertResult('7,5', 'mil/mm3', 'K/µL', null, null, { locale: 'es-ES' }).value, 7.5);
  assert.equal(normalizeUnit('mil/mm3', { locale: 'es' }), '10^3/mm³');
});

test('mil/mm3 without a locale is refused', () => {
  assert.throws(() => convert(7.5, 'mil/mm3', '10^3/µL'), (e: unknown) => ambiguous(e) && (e as LifeFromUnitsError).message.includes('thousand in Spanish'));
  for (const u of ['Mil/mm3', 'mil/µL', 'Mil/uL', 'mil./µL']) assert.throws(() => normalizeUnit(u), ambiguous);
  assert.throws(() => sameUnit('mil/mm3', 'K/µL'), ambiguous);
  assert.throws(() => normalizeUnit('mil/mm3', { locale: 'it' }), ambiguous);
});

test('US Mil/µL RBC with locale en is 10^6/µL', () => {
  assert.equal(normalizeUnit('Mil/µL', { locale: 'en' }), '10^6/µL');
  assert.equal(convert(4.5, 'Mil/µL', '10^12/L', null, null, { locale: 'en-US' }), 4.5);
  assert.equal(normalizeUnit('mil./µL', { locale: 'ro' }), '10^6/µL');
});

test('unambiguous spellings need no locale', () => {
  for (const [u, c] of [['mill/mm3', '10^6/mm³'], ['millones/mm3', '10^6/mm³'], ['Million/µL', '10^6/µL'], ['mii/µL', '10^3/µL'], ['K/µL', '10^3/µL']]) {
    assert.equal(normalizeUnit(u), c);
    assert.equal(normalizeUnit(u, { locale: 'es' }), c);
  }
});

test('the locale reading is explained with sources', () => {
  const e = explain('mil/mm3', '10^9/L', null, undefined, null, { locale: 'es' });
  assert.equal(e.steps[0].kind, 'spelling_reading');
  assert.deepEqual(e.sources.map((s) => s.id), ['eswiktionary-mil', 'nih-cc-cbc-es']);
});

// German, Austrian and Swiss reports (1.2.0).
const close = (a: number, b: number): void => assert.ok(Math.abs(a - b) <= 1e-12 * Math.abs(b), `${a} != ${b}`);

test('German WBC and platelets: G/l and Tsd./µl', () => {
  assert.equal(normalizeUnit('G/l'), '10^9/L');
  assert.equal(normalizeUnit('g/l'), 'g/L');
  assert.equal(normalizeUnit('Tsd./µl'), '10^3/µL');
  assert.equal(normalizeUnit('Tsd/μl'), '10^3/µL');
  assert.equal(normalizeUnit('Gpt/l'), '10^9/L');
  close(convert('6,2', 'Tsd/µl', 'x10^9/L'), 6.2);
  close(convert('6,2', 'G/l', 'Tsd./µl'), 6.2);
  close(convert('6,2', 'G/l', '/nl'), 6.2);
  assert.ok(sameUnit('Tsd./µl', 'G/l'));
  assert.ok(!sameUnit('G/l', 'g/l'));
});

test('German RBC: T/l and Mio./µl', () => {
  assert.equal(normalizeUnit('Mio./µl'), '10^6/µL');
  assert.equal(normalizeUnit('T/l'), '10^12/L');
  close(convert('4,8', 'Mio/µl', 'x10^12/L'), 4.8);
  close(convert('4,8', 'T/l', 'Mio./µl'), 4.8);
  assert.equal(normalizeUnit('Mil./µl', { locale: 'de-AT' }), '10^6/µL');
});

test('German spellings carry sources that resolve', () => {
  let n = 0;
  for (const u of SPEC.units) {
    for (const e of u.spelling_sources ?? []) {
      for (const sp of e.spellings) assert.equal(normalizeUnit(sp), u.unit, sp);
      for (const sid of e.sources) assert.ok(sid in SPEC.sources, sid);
      n += 1;
    }
  }
  assert.ok(n >= 7);
});
