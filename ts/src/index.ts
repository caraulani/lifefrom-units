/**
 * @lifefrom/units: normalise clinical lab unit spellings and convert lab values with sourced,
 * analyte-specific factors. Zero runtime dependencies. Same data and API as the Python package.
 */
import { SPEC } from './data.js';
import type { AmbiguousSpelling, Analyte, Bridge, Forbidden, ReferenceCompound, Source, UnitRecord } from './types.js';

export type { AmbiguousSpelling, Analyte, Bridge, Forbidden, LanguageReading, ReferenceCompound, Source, Spec, UnitRecord } from './types.js';
export { SPEC } from './data.js';

export const VERSION: string = SPEC.version;

// ---------------------------------------------------------------------------
// Errors (codes shared with Python)
// ---------------------------------------------------------------------------
export type ErrorCode =
  | 'unknown_unit'
  | 'unknown_analyte'
  | 'incompatible_units'
  | 'forbidden'
  | 'no_sourced_conversion'
  | 'invalid_value'
  | 'qualified_value'
  | 'ambiguous_value'
  | 'ambiguous_unit';

export class LifeFromUnitsError extends Error {
  readonly code: ErrorCode;
  readonly details: Record<string, unknown>;
  constructor(code: ErrorCode, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'LifeFromUnitsError';
    this.code = code;
    this.details = details;
  }
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------
const RULES: Array<[RegExp, string]> = SPEC.normalization.rules.map((r) => [new RegExp(r.pattern, 'g'), r.replacement]);
const UNITS = new Map<string, UnitRecord>(SPEC.units.map((u) => [u.unit, u]));
const ANALYTES = new Map<string, Analyte>(SPEC.analytes.map((a) => [a.id, a]));
const has = (o: object, k: string): boolean => Object.prototype.hasOwnProperty.call(o, k);

function unitKey(text: string): string {
  let s = text.trim();
  for (const [re, repl] of RULES) {
    re.lastIndex = 0;
    s = s.replace(re, repl);
  }
  return s.replace(/\s+/g, '');
}

/** Options shared by the functions that read unit spellings. */
export interface UnitOptions {
  /**
   * Language of the report (a language tag such as 'es', 'es-AR', 'en-US', 'ro'). Used only for spellings that mean
   * different units in different languages: 'mil/mm3' and 'mil/µL' are thousands in Spanish ('es') and millions on
   * English ('en') and Romanian ('ro') reports. Without it those spellings throw 'ambiguous_unit'.
   */
  locale?: string | null;
}

interface Reading {
  spelling: string;
  unit: string;
  locale: string;
  meaning: string;
  note: string;
  sources: string[];
}

const AMBIG = new Map<string, AmbiguousSpelling>((SPEC.ambiguous ?? []).map((a) => [a.id, a]));
const AMBIG_KEYS: Record<string, string> = SPEC.lookup.ambiguous ?? {};
const LANG = /^([A-Za-z]{2,3})(?:[-_][A-Za-z0-9]{1,8})*$/;

function language(locale: string | null | undefined): string | null {
  if (locale === null || locale === undefined) return null;
  const m = typeof locale === 'string' ? LANG.exec(locale.trim()) : null;
  if (!m) throw new LifeFromUnitsError('invalid_value', `locale must be a language tag such as 'es' or 'es-AR', got '${locale}'`, { locale });
  return m[1].toLowerCase();
}

function lookupRead(unit: string, locale?: string | null): [UnitRecord, Reading | null] {
  const lang = language(locale);
  if (typeof unit !== 'string' || unit.trim() === '') {
    throw new LifeFromUnitsError('unknown_unit', 'empty unit', { unit });
  }
  const k = unitKey(unit);
  if (has(SPEC.lookup.exact, k)) return [UNITS.get(SPEC.lookup.exact[k])!, null];
  const kf = unitKey(unit.toLowerCase());
  if (has(AMBIG_KEYS, kf)) {
    const a = AMBIG.get(AMBIG_KEYS[kf])!;
    const langs = Object.keys(a.readings).sort();
    if (lang === null || !has(a.readings, lang)) {
      const why = lang === null ? 'no locale given' : `no reading for locale '${locale}'`;
      throw new LifeFromUnitsError('ambiguous_unit', `ambiguous unit '${unit}' (${why}): ${a.reason} Pass a locale (one of ${langs.join(', ')}).`, {
        unit,
        ambiguity: a.id,
        locale: locale ?? null,
        readings: { ...a.readings },
        reason: a.reason,
      });
    }
    const r = SPEC.language_readings[lang];
    const canon = a.readings[lang];
    return [UNITS.get(canon)!, { spelling: unit, unit: canon, locale: lang, meaning: r.meaning, note: r.note, sources: r.sources }];
  }
  const canon = has(SPEC.lookup.casefold, kf) ? SPEC.lookup.casefold[kf] : undefined;
  if (canon === undefined) throw new LifeFromUnitsError('unknown_unit', `unknown unit: '${unit}'`, { unit });
  return [UNITS.get(canon)!, null];
}

function lookup(unit: string, locale?: string | null): UnitRecord {
  return lookupRead(unit, locale)[0];
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Canonical spelling of a unit (µ/u/mcg, superscripts, ×10⁹/L, UI/IU, case, spacing).
 * normalizeUnit('mil/mm3', { locale: 'es' }) -> '10^3/mm³'; without a locale it throws 'ambiguous_unit'.
 */
export function normalizeUnit(unit: string, opts?: UnitOptions): string {
  return lookup(unit, opts?.locale).unit;
}

/** Canonical spelling, dimension, scale to the base unit, and UCUM code of a unit. */
export function unitInfo(unit: string, opts?: UnitOptions): { unit: string; dimension: string; scale: number; ucum: string | null } {
  const u = lookup(unit, opts?.locale);
  return { unit: u.unit, dimension: u.dimension, scale: u.scale, ucum: u.ucum };
}

const SEP_SPACES = /(?<=\d)[    '](?=\d)/g;
const NUM = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/;
const isDigits = (s: string): boolean => /^\d+$/.test(s);
const stripSign = (s: string): string => s.replace(/^[+-]+/, '');

const COMPARATOR = /^\s*(<=|>=|=<|=>|≤|≥|<|>)\s*/;
const FLAG = /\s*(?:\(\s*(HH|LL|H|L|A|AA)\s*\)|\[\s*(HH|LL|H|L|A|AA)\s*\]|(HH|LL|H|L|A|AA|↑|↓|\*|!))\s*$/i;
const CMP_NORMAL: Record<string, string> = { '<': '<', '>': '>', '<=': '<=', '>=': '>=', '=<': '<=', '=>': '>=', '≤': '<=', '≥': '>=' };

function splitQualifiers(text: string): [string | null, string, string | null] {
  let comparator: string | null = null;
  let flag: string | null = null;
  let s = text.trim();
  const m = COMPARATOR.exec(s);
  if (m) {
    comparator = CMP_NORMAL[m[1]];
    s = s.slice(m[0].length);
  }
  const f = FLAG.exec(s);
  if (f && f.index > 0 && /[0-9.]/.test(s.slice(0, f.index))) {
    flag = (f[1] ?? f[2] ?? f[3]).toUpperCase();
    s = s.slice(0, f.index);
  }
  return [comparator, s.trim(), flag];
}

export interface ParsedResult {
  value: number;
  comparator: string | null;
  flag: string | null;
  text: string;
}

/** Parse a reported value with an optional comparator ("<5") or flag ("5,4 H"). Never drops the qualifier. */
export function parseResult(value: number | string): ParsedResult {
  if (typeof value === 'number') return { value: parseValue(value), comparator: null, flag: null, text: String(value) };
  if (typeof value !== 'string') throw new LifeFromUnitsError('invalid_value', `unsupported value type: ${typeof value}`, { value });
  const [comparator, num, flag] = splitQualifiers(value);
  return { value: parseNumber(num, value), comparator, flag, text: value };
}

/**
 * Parse a number, accepting a decimal comma ("5,4" -> 5.4). "1,234" is ambiguous and throws.
 * Values with a comparator or flag throw qualified_value: use parseResult / convertResult.
 */
export function parseValue(value: number | string): number {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new LifeFromUnitsError('invalid_value', 'value is not finite', { value });
    return value;
  }
  if (typeof value !== 'string') throw new LifeFromUnitsError('invalid_value', `unsupported value type: ${typeof value}`, { value });
  const [comparator, num, flag] = splitQualifiers(value);
  if (comparator || flag) {
    parseNumber(num, value); // a malformed number is reported as such
    throw new LifeFromUnitsError('qualified_value', `value '${value}' has a qualifier (${comparator || flag}); use parseResult()/convertResult() so it is kept`, { value, comparator, flag });
  }
  return parseNumber(value, value);
}

function parseNumber(text: string, value: string): number {
  let s = text.trim().replace(/\u2212/g, '-');
  s = s.replace(SEP_SPACES, '');
  if (s.includes(',') && s.includes('.')) {
    const dec = s.lastIndexOf(',') > s.lastIndexOf('.') ? ',' : '.';
    const thou = dec === ',' ? '.' : ',';
    const at = s.lastIndexOf(dec);
    const intPart = s.slice(0, at);
    const frac = s.slice(at + 1);
    const groups = stripSign(intPart).split(thou);
    const ok = groups.length >= 2 && groups.slice(1).every((g) => g.length === 3) && groups[0].length >= 1 && groups[0].length <= 3;
    if (!ok) throw new LifeFromUnitsError('ambiguous_value', `cannot read '${value}': mixed separators`, { value });
    s = intPart.split(thou).join('') + '.' + frac;
  } else if (s.includes(',')) {
    const parts = s.split(',');
    if (parts.length === 2) {
      const head = stripSign(parts[0]);
      if (parts[1].length === 3 && isDigits(parts[1]) && isDigits(head) && head.length >= 1 && head.length <= 3 && head !== '0') {
        throw new LifeFromUnitsError('ambiguous_value', `cannot read '${value}': the comma may be a decimal or a thousands separator`, { value });
      }
      s = parts[0] + '.' + parts[1];
    } else {
      const head = stripSign(parts[0]);
      if (parts.slice(1).every((p) => p.length === 3) && head.length >= 1 && head.length <= 3) s = parts.join('');
      else throw new LifeFromUnitsError('invalid_value', `cannot read '${value}'`, { value });
    }
  } else if ((s.match(/\./g) ?? []).length > 1) {
    const parts = s.split('.');
    const head = stripSign(parts[0]);
    if (parts.slice(1).every((p) => p.length === 3) && head.length >= 1 && head.length <= 3) s = parts.join('');
    else throw new LifeFromUnitsError('invalid_value', `cannot read '${value}'`, { value });
  }
  if (!NUM.test(s)) throw new LifeFromUnitsError('invalid_value', `not a number: '${value}'`, { value });
  const v = Number(s);
  if (!Number.isFinite(v)) throw new LifeFromUnitsError('invalid_value', 'value is not finite', { value });
  return v;
}

function resolveAnalyte(analyte: string | null | undefined): Analyte | null {
  if (analyte === null || analyte === undefined) return null;
  if (typeof analyte !== 'string' || analyte.trim() === '') throw new LifeFromUnitsError('unknown_analyte', 'empty analyte', { analyte });
  const k = analyte.trim().toLowerCase();
  const id = has(SPEC.lookup.analytes, k) ? SPEC.lookup.analytes[k] : undefined;
  if (id === undefined) throw new LifeFromUnitsError('unknown_analyte', `unknown analyte: '${analyte}'`, { analyte });
  return ANALYTES.get(id)!;
}

/** Analytes: id, name, marker slugs, and whether lifefrom-units has conversions for them. */
export function analytes(): Array<{ id: string; name: string; marker_slugs: string[]; has_conversions: boolean }> {
  return SPEC.analytes.map((a) => ({ id: a.id, name: a.name, marker_slugs: [...a.marker_slugs], has_conversions: a.bridges.length > 0 }));
}

export interface StepSource extends Source {
  id: string;
}
export interface Step {
  kind: string;
  description: string;
  basis?: string;
  factor?: number;
  inverse?: boolean;
  sources: StepSource[];
  reference_compound?: ReferenceCompound | null;
}

export interface UserFactorRecord {
  value: number;
  overrides: string | null;
  library_kind: string | null;
  library_factor: number | null;
}
export interface Explanation {
  from_unit: string;
  to_unit: string;
  analyte: string | null;
  kind: 'identity' | 'unit_arithmetic' | 'label_equivalence' | 'analyte_factor' | 'equation' | 'user_factor';
  factor: number | null;
  equation: { slope: number; intercept: number; text: string } | null;
  derived: boolean;
  steps: Step[];
  sources: StepSource[];
  reference_compounds: ReferenceCompound[];
  warnings: string[];
  user_factor: UserFactorRecord | null;
  text: string;
  value?: number;
  result?: number;
}

function sourceList(ids: string[]): StepSource[] {
  return ids.map((i) => ({ ...SPEC.sources[i], id: i }));
}

function forbiddenMatch(f: Forbidden, ua: UnitRecord, ub: UnitRecord): boolean {
  const side = (dim: string, units: string[] | null, u: UnitRecord): boolean => {
    if (dim !== '*' && dim !== u.dimension) return false;
    return units === null || units === undefined || units.includes(u.unit);
  };
  return (side(f.a, f.a_units, ua) && side(f.b, f.b_units, ub)) || (side(f.a, f.a_units, ub) && side(f.b, f.b_units, ua));
}

function raiseForbidden(f: Forbidden, ua: UnitRecord, ub: UnitRecord): never {
  throw new LifeFromUnitsError('forbidden', `${ua.unit} -> ${ub.unit}: ${f.reason}`, { rule: f.id, reason: f.reason, sources: sourceList(f.sources) });
}

interface Plan {
  from_unit: string;
  to_unit: string;
  analyte: string | null;
  a: number;
  b: number;
  kind: Explanation['kind'];
  steps: Step[];
}

function readingStep(r: Reading): Step {
  return {
    kind: 'spelling_reading',
    description: `'${r.spelling}' read as ${r.unit} ('mil' = ${r.meaning}, locale '${r.locale}')`,
    basis: r.note,
    sources: sourceList(r.sources),
  };
}

function plan(fromUnit: string, toUnit: string, analyte?: string | null, locale?: string | null): Plan {
  const [ua, ra] = lookupRead(fromUnit, locale);
  const [ub, rb] = lookupRead(toUnit, locale);
  const p = planUnits(ua, ub, analyte);
  const reads = [ra, rb].filter((r): r is Reading => r !== null).map(readingStep);
  if (reads.length) p.steps = [...reads, ...p.steps];
  return p;
}

function planUnits(ua: UnitRecord, ub: UnitRecord, analyte?: string | null): Plan {
  const an = resolveAnalyte(analyte);
  const base = { from_unit: ua.unit, to_unit: ub.unit, analyte: an ? an.id : null };
  const da = ua.dimension;
  const db = ub.dimension;

  if (an) {
    for (const f of SPEC.forbidden) if (f.analyte === an.id && forbiddenMatch(f, ua, ub)) raiseForbidden(f, ua, ub);
  }
  if (ua.unit === ub.unit) {
    return { ...base, a: 1, b: 0, kind: 'identity', steps: [{ kind: 'identity', description: 'same unit', sources: [] }] };
  }
  if (da.startsWith('arbitrary:') || db.startsWith('arbitrary:')) {
    throw new LifeFromUnitsError('forbidden', `${ua.unit} -> ${ub.unit}: ${SPEC.arbitrary_reason}`, {
      rule: 'arbitrary-units',
      reason: SPEC.arbitrary_reason,
      sources: sourceList(['ucum-2.2']),
    });
  }
  if (da === db) {
    const a = ua.scale / ub.scale;
    return {
      ...base,
      a,
      b: 0,
      kind: 'unit_arithmetic',
      steps: [
        {
          kind: 'unit_arithmetic',
          factor: a,
          description: `same quantity (${SPEC.dimensions[da].name}); factor from unit prefixes`,
          basis: 'derived: unit arithmetic',
          sources: [],
        },
      ],
    };
  }
  const genericForbidden = (): void => {
    for (const f of SPEC.forbidden) if (f.analyte === null && forbiddenMatch(f, ua, ub)) raiseForbidden(f, ua, ub);
  };
  if (!an) {
    genericForbidden();
    throw new LifeFromUnitsError(
      'incompatible_units',
      `${ua.unit} (${da}) and ${ub.unit} (${db}) measure different quantities; pass analyte to convert between them`,
      { from_dimension: da, to_dimension: db },
    );
  }

  // Breadth-first search over the analyte's bridges.
  const edges = new Map<string, Array<[string, Bridge, boolean]>>();
  const push = (k: string, v: [string, Bridge, boolean]): void => {
    if (!edges.has(k)) edges.set(k, []);
    edges.get(k)!.push(v);
  };
  for (const br of an.bridges) {
    push(br.from, [br.to, br, false]);
    push(br.to, [br.from, br, true]);
  }
  const prev = new Map<string, [string, Bridge, boolean]>();
  const seen = new Set<string>([da]);
  const q: string[] = [da];
  while (q.length) {
    const d = q.shift()!;
    if (d === db) break;
    for (const [nd, br, inv] of edges.get(d) ?? []) {
      if (!seen.has(nd)) {
        seen.add(nd);
        prev.set(nd, [d, br, inv]);
        q.push(nd);
      }
    }
  }
  if (!seen.has(db)) {
    genericForbidden();
    throw new LifeFromUnitsError(
      'no_sourced_conversion',
      `no sourced conversion for ${an.id} between ${ua.unit} (${da}) and ${ub.unit} (${db})`,
      { analyte: an.id, from_dimension: da, to_dimension: db },
    );
  }
  const path: Array<[Bridge, boolean]> = [];
  let d = db;
  while (d !== da) {
    const [p, br, inv] = prev.get(d)!;
    path.push([br, inv]);
    d = p;
  }
  path.reverse();

  let a = ua.scale;
  let b = 0;
  const steps: Step[] = [];
  for (const [br, inv] of path) {
    let ba = br.a;
    let bb = br.b;
    if (inv) {
      const ia = 1 / ba;
      const ib = -bb / ba;
      ba = ia;
      bb = ib;
    }
    a = a * ba;
    b = b * ba + bb;
    steps.push({
      kind: br.kind,
      description: br.description,
      basis: br.basis,
      inverse: inv,
      sources: sourceList(br.sources),
      reference_compound: br.reference_compound ?? null,
    });
  }
  a = a / ub.scale;
  b = b / ub.scale;
  const kinds = new Set(steps.map((s) => s.kind));
  kinds.delete('label_equivalence');
  const kind: Explanation['kind'] = b !== 0 ? 'equation' : kinds.size > 0 ? 'analyte_factor' : 'label_equivalence';
  return { ...base, a, b, kind, steps };
}

interface FullPlan extends Plan {
  user_factor: UserFactorRecord | null;
  warnings: string[];
}

function userFactor(factor: number | string): number {
  let f: number;
  try {
    f = parseValue(factor);
  } catch {
    throw new LifeFromUnitsError('invalid_value', `factor must be a positive number, got '${factor}'`, { factor });
  }
  if (!(f > 0)) throw new LifeFromUnitsError('invalid_value', `factor must be a positive number, got '${factor}'`, { factor });
  return f;
}

function pct(x: number): string {
  const s = (x * 100).toFixed(2);
  return (s.startsWith('-') ? s : '+' + s) + '%';
}

function planWith(
  fromUnit: string,
  toUnit: string,
  analyte: string | null | undefined,
  factor: number | string | null | undefined,
  locale?: string | null,
): FullPlan {
  if (factor === undefined || factor === null) return { ...plan(fromUnit, toUnit, analyte, locale), user_factor: null, warnings: [] };
  const f = userFactor(factor);
  const [ua, ra] = lookupRead(fromUnit, locale);
  const [ub, rb] = lookupRead(toUnit, locale);
  const an = resolveAnalyte(analyte);
  const warnings = [`Factor ${fmtG(f)} supplied by the caller; lifefrom-units has not checked it.`];
  const record: UserFactorRecord = { value: f, overrides: null, library_kind: null, library_factor: null };
  try {
    const lib = plan(fromUnit, toUnit, analyte, locale);
    record.library_kind = lib.kind;
    if (lib.b !== 0) warnings.push('lifefrom-units uses an equation for this pair, not a factor.');
    else {
      record.library_factor = lib.a;
      if (Math.abs(lib.a - f) > 1e-9 * Math.abs(lib.a)) {
        warnings.push(`The library factor is ${fmtG(lib.a)} (${lib.kind}); the supplied factor differs by ${pct((f - lib.a) / lib.a)}.`);
      }
    }
  } catch (e) {
    if (e instanceof LifeFromUnitsError && (e.code === 'incompatible_units' || e.code === 'forbidden' || e.code === 'no_sourced_conversion')) {
      record.overrides = e.code;
      const reason = (e.details.reason as string | undefined) || e.message;
      warnings.push(`Overrides lifefrom-units (${e.code}): ${reason}`);
    } else throw e;
  }
  return {
    from_unit: ua.unit,
    to_unit: ub.unit,
    analyte: an ? an.id : null,
    a: f,
    b: 0,
    kind: 'user_factor',
    user_factor: record,
    warnings,
    steps: [
      ...[ra, rb].filter((r): r is Reading => r !== null).map(readingStep),
      {
        kind: 'user_factor',
        factor: f,
        description: `factor supplied by the caller: 1 ${ua.unit} = ${fmtG(f)} ${ub.unit}`,
        basis: 'caller-supplied; not checked by lifefrom-units',
        sources: [],
      },
    ],
  };
}

/**
 * Convert `value` from `fromUnit` to `toUnit`. `analyte` (lifefrom-units analyte id such as "glucose" or a
 * LifeFrom marker slug such as "glucose-fasting") is needed when the units measure different quantities.
 * `factor` (optional, never a default) is a caller-supplied multiplier recorded by explain().
 * `opts.locale` (optional language tag) says which convention the report follows for spellings that are ambiguous
 * across languages: convert('7,5', 'mil/mm3', 'K/µL', null, null, { locale: 'es' }) -> 7.5.
 * Throws LifeFromUnitsError with code incompatible_units, forbidden, no_sourced_conversion, unknown_unit,
 * ambiguous_unit, unknown_analyte, invalid_value, qualified_value or ambiguous_value.
 */
export function convert(
  value: number | string,
  fromUnit: string,
  toUnit: string,
  analyte?: string | null,
  factor?: number | string | null,
  opts?: UnitOptions,
): number {
  const v = parseValue(value);
  const p = planWith(fromUnit, toUnit, analyte, factor, opts?.locale);
  return p.a * v + p.b;
}

export const FLAG_NOTE =
  "The flag is copied unchanged from the original report. It refers to that laboratory's reference interval, not to anything lifefrom-units computed.";

export interface ConvertedResult {
  value: number;
  comparator: string | null;
  flag: string | null;
  unit: string;
  text: string;
  flag_note?: string;
}

/** Convert a reported value that may carry a comparator ("<5") or a flag ("5,4 H"); both are kept. */
export function convertResult(
  value: number | string,
  fromUnit: string,
  toUnit: string,
  analyte?: string | null,
  factor?: number | string | null,
  opts?: UnitOptions,
): ConvertedResult {
  const r = parseResult(value);
  const p = planWith(fromUnit, toUnit, analyte, factor, opts?.locale);
  let comparator = r.comparator;
  if (p.a < 0 && comparator) comparator = ({ '<': '>', '>': '<', '<=': '>=', '>=': '<=' } as Record<string, string>)[comparator];
  const v = p.a * r.value + p.b;
  const out: ConvertedResult = { value: v, comparator, flag: r.flag, unit: p.to_unit, text: `${comparator ?? ''}${fmtG(v)}${r.flag ? ' ' + r.flag : ''}` };
  if (r.flag) out.flag_note = FLAG_NOTE;
  return out;
}

/** True if a value in unit `a` equals the same number in unit `b` (e.g. µg/L and ng/mL). */
export function sameUnit(a: string, b: string, analyte?: string | null, opts?: UnitOptions): boolean {
  let p: Plan;
  try {
    p = plan(a, b, analyte, opts?.locale);
  } catch (e) {
    if (e instanceof LifeFromUnitsError && (e.code === 'incompatible_units' || e.code === 'forbidden' || e.code === 'no_sourced_conversion')) return false;
    throw e;
  }
  return p.b === 0 && Math.abs(p.a - 1) <= 1e-12;
}

/** Format like Python's "{:.6g}". */
export function fmtG(x: number): string {
  if (x === 0) return '0';
  if (!Number.isFinite(x)) return String(x);
  const [, e] = x.toExponential(5).split('e');
  const exp = Number(e);
  if (exp < -4 || exp >= 6) {
    let [m, ex] = x.toExponential(5).split('e');
    if (m.includes('.')) m = m.replace(/0+$/, '').replace(/\.$/, '');
    const n = Number(ex);
    return `${m}e${n < 0 ? '-' : '+'}${String(Math.abs(n)).padStart(2, '0')}`;
  }
  let s = x.toFixed(Math.max(0, 5 - exp));
  if (s.includes('.')) s = s.replace(/0+$/, '').replace(/\.$/, '');
  return s;
}

/** Explain a conversion: factor or equation, steps, basis, sources, reference compounds and warnings. */
export function explain(
  fromUnit: string,
  toUnit: string,
  analyte?: string | null,
  value?: number | string | null,
  factor?: number | string | null,
  opts?: UnitOptions,
): Explanation {
  const p = planWith(fromUnit, toUnit, analyte, factor, opts?.locale);
  const out: Explanation = {
    from_unit: p.from_unit,
    to_unit: p.to_unit,
    analyte: p.analyte,
    kind: p.kind,
    factor: p.b === 0 ? p.a : null,
    equation: null,
    derived: p.kind === 'identity' || p.kind === 'unit_arithmetic',
    steps: p.steps,
    sources: [],
    reference_compounds: [],
    warnings: [...p.warnings],
    user_factor: p.user_factor,
    text: '',
  };
  if (p.b !== 0) {
    const text = `${p.to_unit} = ${fmtG(p.a)} × ${p.from_unit} ${p.b >= 0 ? '+' : '-'} ${fmtG(Math.abs(p.b))}`;
    out.equation = { slope: p.a, intercept: p.b, text };
    out.text = text;
  } else {
    out.text = `1 ${p.from_unit} = ${fmtG(p.a)} ${p.to_unit}`;
  }
  const seen = new Set<string>();
  for (const s of p.steps) {
    for (const src of s.sources) {
      if (!seen.has(src.id)) {
        seen.add(src.id);
        out.sources.push(src);
      }
    }
    if (s.reference_compound) out.reference_compounds.push(s.reference_compound);
  }
  if (p.analyte && p.kind !== 'identity' && p.kind !== 'unit_arithmetic') out.warnings.push(...(ANALYTES.get(p.analyte)!.caveats ?? []));
  if (value !== undefined && value !== null) {
    const v = parseValue(value);
    out.value = v;
    out.result = p.a * v + p.b;
  }
  return out;
}

/** snake_case aliases matching the Python API names. */
export const normalize_unit = normalizeUnit;
export const same_unit = sameUnit;
export const parse_value = parseValue;
export const parse_result = parseResult;
export const convert_result = convertResult;
export const unit_info = unitInfo;
