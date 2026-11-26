"""Run every vector through both packages and require bit-identical numeric results.

Usage: python3 -I scripts/crosscheck_languages.py   (after `npm run build` in ts/)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))
import lifefrom_units as L  # noqa: E402

JS = r"""
import { readFileSync } from 'node:fs';
import * as L from './dist/src/index.js';
const V = JSON.parse(readFileSync('../tests/vectors.json', 'utf-8')).vectors;
const out = {};
for (const v of V) {
  const i = v.input;
  const o = { locale: i.locale };
  try {
    let r;
    if (v.op === 'normalize') r = L.normalizeUnit(i.unit, o);
    else if (v.op === 'same_unit') r = L.sameUnit(i.a, i.b, i.analyte, o);
    else if (v.op === 'parse_value') r = L.parseValue(i.value);
    else if (v.op === 'convert') r = L.convert(i.value, i.from, i.to, i.analyte, i.factor, o);
    else if (v.op === 'parse_result') r = L.parseResult(i.value);
    else if (v.op === 'convert_result') r = L.convertResult(i.value, i.from, i.to, i.analyte, i.factor, o);
    else if (v.op === 'roundtrip') r = L.convert(L.convert(i.value, i.a, i.b, i.analyte), i.b, i.a, i.analyte);
    else if (v.op === 'explain') { const e = L.explain(i.from, i.to, i.analyte, undefined, i.factor, o); r = [e.kind, e.factor, e.text, e.equation && e.equation.slope, e.equation && e.equation.intercept, e.warnings, e.reference_compounds, e.user_factor, e.sources.map(s => s.id), e.steps.map(s => [s.kind, s.description, s.basis ?? null])]; }
    out[v.id] = ['ok', r];
  } catch (e) { out[v.id] = ['err', e.code, e.code === 'ambiguous_unit' ? e.message : null]; }
}
process.stdout.write(JSON.stringify(out));
"""


def py_results():
    V = json.loads((ROOT / "tests" / "vectors.json").read_text(encoding="utf-8"))["vectors"]
    out = {}
    for v in V:
        i = v["input"]
        try:
            if v["op"] == "normalize":
                r = L.normalize_unit(i["unit"], locale=i.get("locale"))
            elif v["op"] == "same_unit":
                r = L.same_unit(i["a"], i["b"], i.get("analyte"), locale=i.get("locale"))
            elif v["op"] == "parse_value":
                r = L.parse_value(i["value"])
            elif v["op"] == "convert":
                r = L.convert(i["value"], i["from"], i["to"], i.get("analyte"), factor=i.get("factor"), locale=i.get("locale"))
            elif v["op"] == "parse_result":
                r = L.parse_result(i["value"])
            elif v["op"] == "convert_result":
                r = L.convert_result(i["value"], i["from"], i["to"], i.get("analyte"), factor=i.get("factor"),
                                     locale=i.get("locale"))
            elif v["op"] == "roundtrip":
                r = L.convert(L.convert(i["value"], i["a"], i["b"], i.get("analyte")), i["b"], i["a"], i.get("analyte"))
            else:
                e = L.explain(i["from"], i["to"], i.get("analyte"), factor=i.get("factor"), locale=i.get("locale"))
                r = [e["kind"], e["factor"], e["text"], e["equation"] and e["equation"]["slope"],
                     e["equation"] and e["equation"]["intercept"], e["warnings"], e["reference_compounds"],
                     e["user_factor"], [s["id"] for s in e["sources"]],
                     [[s["kind"], s["description"], s.get("basis")] for s in e["steps"]]]
            out[v["id"]] = ["ok", r]
        except L.LifeFromUnitsError as ex:
            out[v["id"]] = ["err", ex.code, str(ex) if ex.code == "ambiguous_unit" else None]
    return out


def main():
    js = json.loads(subprocess.run(["node", "--input-type=module", "-e", JS], cwd=ROOT / "ts", check=True,
                                   capture_output=True, text=True).stdout)
    py = json.loads(json.dumps(py_results()))
    diff = [k for k in py if py[k] != js.get(k)]
    for k in diff[:20]:
        print("DIFF", k, py[k], js.get(k))
    print(f"{len(py)} vectors compared, {len(diff)} differ")
    return 1 if diff else 0


if __name__ == "__main__":
    raise SystemExit(main())
