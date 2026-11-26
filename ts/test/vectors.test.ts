import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { convert, convertResult, explain, LifeFromUnitsError, normalizeUnit, parseResult, parseValue, sameUnit } from '../src/index.js';

interface Vector {
  id: string;
  op: string;
  input: Record<string, any>;
  expect?: Record<string, any>;
  error?: string;
  rel_tol?: number;
  abs_tol?: number;
}

const path = fileURLToPath(new URL('../../../tests/vectors.json', import.meta.url));
const VECTORS: { count: number; vectors: Vector[] } = JSON.parse(readFileSync(path, 'utf-8'));

function isClose(a: number, b: number, rel: number): boolean {
  return a === b || Math.abs(a - b) <= rel * Math.max(Math.abs(a), Math.abs(b));
}

function run(v: Vector): Record<string, any> {
  const i = v.input;
  const o = { locale: i.locale };
  switch (v.op) {
    case 'normalize':
      return { unit: normalizeUnit(i.unit, o) };
    case 'same_unit':
      return { same: sameUnit(i.a, i.b, i.analyte, o) };
    case 'parse_value':
      return { value: parseValue(i.value) };
    case 'convert':
      return { value: convert(i.value, i.from, i.to, i.analyte, i.factor, o) };
    case 'parse_result': {
      const r = parseResult(i.value);
      return { value: r.value, comparator: r.comparator, flag: r.flag };
    }
    case 'convert_result': {
      const r = convertResult(i.value, i.from, i.to, i.analyte, i.factor, o);
      return { value: r.value, comparator: r.comparator, flag: r.flag, unit: r.unit };
    }
    case 'roundtrip': {
      const x = convert(i.value, i.a, i.b, i.analyte);
      return { value: convert(x, i.b, i.a, i.analyte) };
    }
    case 'explain': {
      const e = explain(i.from, i.to, i.analyte, undefined, i.factor, o);
      const out: Record<string, any> = {
        kind: e.kind,
        factor: e.factor,
        derived: e.derived,
        source_ids: e.sources.map((s) => s.id),
        reference_cids: e.reference_compounds.filter((r) => r.pubchem_cid !== undefined).map((r) => r.pubchem_cid),
        reference_elements: e.reference_compounds.filter((r) => r.element !== undefined).map((r) => r.element),
        warning_count: e.warnings.length,
        warnings: e.warnings,
        user_factor_overrides: e.user_factor ? e.user_factor.overrides : null,
        user_factor_library_kind: e.user_factor ? e.user_factor.library_kind : null,
      };
      if (e.equation) {
        out.slope = e.equation.slope;
        out.intercept = e.equation.intercept;
      }
      return out;
    }
    default:
      throw new Error(`unknown op ${v.op}`);
  }
}

test('vector count', () => {
  assert.equal(VECTORS.count, VECTORS.vectors.length);
  assert.ok(VECTORS.count >= 300);
});

for (const v of VECTORS.vectors) {
  test(v.id, () => {
    if (v.error) {
      assert.throws(() => run(v), (e: unknown) => e instanceof LifeFromUnitsError && e.code === v.error);
      return;
    }
    const got = run(v);
    const want = v.expect!;
    if (v.op === 'convert' || v.op === 'roundtrip') {
      if (v.abs_tol !== undefined) assert.ok(Math.abs(got.value - want.value) <= v.abs_tol, `${got.value} vs ${want.value}`);
      else assert.ok(isClose(got.value, want.value, v.rel_tol!), `${got.value} vs ${want.value}`);
    } else if (v.op === 'parse_result' || v.op === 'convert_result') {
      assert.ok(isClose(got.value, want.value, v.rel_tol ?? 1e-15), `${got.value} vs ${want.value}`);
      for (const [k, w] of Object.entries(want)) if (k !== 'value') assert.deepEqual(got[k], w, k);
    } else if (v.op === 'explain') {
      for (const [k, w] of Object.entries(want)) {
        if (k === 'warnings_contain') {
          for (const sub of w as string[]) assert.ok((got.warnings as string[]).some((x) => x.includes(sub)), sub);
        } else if (typeof w === 'number' && !Number.isInteger(w)) assert.ok(isClose(got[k], w, 1e-9), `${k}: ${got[k]} vs ${w}`);
        else assert.deepEqual(got[k], w, k);
      }
    } else if (v.op === 'parse_value') {
      assert.ok(isClose(got.value, want.value, 1e-15), `${got.value} vs ${want.value}`);
    } else {
      assert.deepEqual(got, want);
    }
  });
}
