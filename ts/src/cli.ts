#!/usr/bin/env node
/** lifefrom-units CLI (TypeScript build): convert | normalize | same | explain */
import { convertResult, explain, LifeFromUnitsError, normalizeUnit, sameUnit } from './index.js';

function flag(args: string[], name: string): string | undefined {
  const i = args.findIndex((a) => a === `--${name}` || a === `-${name[0]}`);
  if (i < 0) return undefined;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
}

function main(argv: string[]): number {
  const args = [...argv];
  const cmd = args.shift();
  const json = args.includes('--json');
  if (json) args.splice(args.indexOf('--json'), 1);
  const analyte = flag(args, 'analyte');
  const factor = flag(args, 'factor');
  const locale = flag(args, 'locale');
  const opts = { locale };
  try {
    if (cmd === 'convert' && args.length === 3) {
      const r = convertResult(args[0], args[1], args[2], analyte, factor, opts);
      if (json) console.log(JSON.stringify({ result: r, explanation: explain(args[1], args[2], analyte, undefined, factor, opts) }, null, 2));
      else {
        console.log(r.text);
        if (factor !== undefined) console.error('note: factor supplied by you; not checked by lifefrom-units');
      }
    } else if (cmd === 'normalize' && args.length >= 1) {
      for (const u of args) console.log(normalizeUnit(u, opts));
    } else if (cmd === 'same' && args.length === 2) {
      const ok = sameUnit(args[0], args[1], analyte, opts);
      console.log(ok ? 'same' : 'different');
      return ok ? 0 : 1;
    } else if (cmd === 'explain' && args.length === 2) {
      const e = explain(args[0], args[1], analyte, undefined, factor, opts);
      if (json) console.log(JSON.stringify(e, null, 2));
      else {
        console.log(e.text);
        for (const s of e.sources) console.log(`  source: ${s.label} <${s.url}>`);
        for (const w of e.warnings) console.log(`  warning: ${w}`);
        if (e.derived) console.log('  derived: unit arithmetic');
      }
    } else {
      console.error('usage: lifefrom-units convert <value> <from> <to> [--analyte X] [--factor F] [--locale L] [--json]\n' +
        '       lifefrom-units normalize <unit>... [--locale L]\n       lifefrom-units same <a> <b> [--analyte X] [--locale L]\n' +
        '       lifefrom-units explain <from> <to> [--analyte X] [--factor F] [--locale L] [--json]\n' +
        '  --locale/-l: language of the report (es, en, ro), needed for mil/mm3 and mil/µL (thousand in Spanish, million in English)');
      return 64;
    }
  } catch (e) {
    if (e instanceof LifeFromUnitsError) {
      console.error(`lifefrom-units: ${e.code}: ${e.message}`);
      return 2;
    }
    throw e;
  }
  return 0;
}

process.exitCode = main(process.argv.slice(2));
