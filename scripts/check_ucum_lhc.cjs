const ucum = require('@lhncbc/ucum-lhc');
const U = ucum.UcumLhcUtils.getInstance();
const spec = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf-8'));
let bad = 0, ok = 0, pairs = 0, pairBad = 0;
const coded = spec.units.filter(u => u.ucum);
for (const u of coded) {
  const r = U.validateUnitString(u.ucum, true);
  if (r.status !== 'valid') { bad++; console.log('INVALID', u.unit, u.ucum, r.status, r.msg); } else ok++;
}
// unit arithmetic: compare our scale ratios with ucum-lhc conversions, same dimension, non-arbitrary IU allowed
const byDim = {};
for (const u of coded) (byDim[u.dimension] ??= []).push(u);
const lines = [];
for (const [dim, us] of Object.entries(byDim)) {
  for (const a of us) for (const b of us) {
    if (a === b) continue;
    pairs++;
    const r = U.convertUnitTo(a.ucum, 1, b.ucum);
    const ours = a.scale / b.scale;
    if (r.status !== 'succeeded') { pairBad++; lines.push(`NOCONV ${dim} ${a.ucum} -> ${b.ucum}: ${r.status} ${r.msg}`); continue; }
    const rel = Math.abs(r.toVal - ours) / Math.abs(ours);
    if (rel > 1e-9) { pairBad++; lines.push(`DIFF ${a.ucum} -> ${b.ucum}: lhc ${r.toVal} ours ${ours}`); }
  }
}
// molar-mass conversions: mg/dL -> mmol/L with each analyte's molar mass
let mm = 0, mmBad = 0;
for (const an of spec.analytes) {
  if (!an.molar_mass) continue;
  const br = an.bridges.find(b => b.from === 'mass_concentration' && b.kind === 'molar_mass');
  if (!br) continue;
  mm++;
  const r = U.convertUnitTo('mg/dL', 1, 'mmol/L', { molecularWeight: an.molar_mass.value });
  const ours = 0.01 * br.a / 0.001;
  if (r.status !== 'succeeded' || Math.abs(r.toVal - ours) / ours > 1e-9) { mmBad++; lines.push(`MM ${an.id} ${r.status} ${r.toVal} ${ours} ${r.msg}`); }
}
console.log(lines.filter(l=>!l.includes("[IU]")).slice(0,60).join('\n'));
console.log(JSON.stringify({ codes: coded.length, valid: ok, invalid: bad, pairs, pairProblems: pairBad, molarChecks: mm, molarProblems: mmBad }));
