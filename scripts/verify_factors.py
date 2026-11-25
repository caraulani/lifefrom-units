"""Hand-verification table for METHODS.md.

For each analyte with a PubChem molar mass, recompute the molar mass from the molecular formula with
CIAAW abridged atomic weights (an independent path), compare it with PubChem's value, and compare
the resulting mg/dL -> SI factor with the published NHANES factor where one exists.
Prints a Markdown table. Run: python3 -I scripts/verify_factors.py
"""
from __future__ import annotations

import json
import re
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))
import lifefrom_units as L  # noqa: E402

spec = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402  (for CIAAW parsing only)

AW = {k: F(v["value"]) for k, v in build.CIAAW.items()}


def formula_mass(formula: str) -> F:
    total = F(0)
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula.rstrip("+-")):
        total += AW[el] * (int(n) if n else 1)
    return total


ROWS = [  # analyte, from, to, published (source, factor) or None
    ("glucose", "mg/dL", "mmol/L", ("NHANES GLU_L", 0.05551)),
    ("cholesterol", "mg/dL", "mmol/L", ("NHANES TCHOL_L", 0.02586)),
    ("creatinine", "mg/dL", "µmol/L", ("NHANES BIOPRO_L", 88.4)),
    ("uric-acid", "mg/dL", "µmol/L", ("NHANES BIOPRO_L", 59.48)),
    ("bilirubin", "mg/dL", "µmol/L", ("NHANES BIOPRO_L", 17.1)),
    ("urea", "mg/dL", "mmol/L", None),
    ("cortisol", "µg/dL", "nmol/L", None),
    ("testosterone", "ng/dL", "nmol/L", ("NHANES TST_L", 0.0347)),
    ("estradiol", "pg/mL", "pmol/L", ("NHANES TST_L", 3.67)),
    ("estrone", "ng/dL", "pmol/L", ("NHANES TST_L", 37.0)),
    ("dhea-s", "µg/dL", "µmol/L", ("NHANES TST_L", 0.0271)),
    ("androstenedione", "ng/dL", "nmol/L", ("NHANES TST_L", 0.0349)),
    ("17-hydroxyprogesterone", "ng/dL", "nmol/L", ("NHANES TST_L", 0.0303)),
    ("progesterone", "ng/dL", "nmol/L", ("NHANES TST_L", 0.0318)),
    ("folate", "ng/mL", "nmol/L", ("NHANES FOLATE_L", 2.265)),
    ("triiodothyronine", "pg/mL", "pmol/L", None),
    ("thyroxine", "ng/dL", "pmol/L", None),
    ("vitamin-b12", "pg/mL", "pmol/L", None),
    ("25-hydroxyvitamin-d", "ng/mL", "nmol/L", ("IOM 2011 (multiply by 2.5)", 2.5)),
    ("1-25-dihydroxyvitamin-d", "pg/mL", "pmol/L", None),
    ("homocysteine", "mg/L", "µmol/L", None),
    ("methylmalonic-acid", "µg/mL", "µmol/L", None),
    ("vitamin-a", "µg/dL", "µmol/L", None),
    ("vitamin-c", "mg/dL", "µmol/L", None),
    ("vitamin-e", "mg/L", "µmol/L", None),
    ("lactate", "mg/dL", "mmol/L", None),
    ("aldosterone", "ng/dL", "pmol/L", None),
]
ELEMENTS = [("calcium", "mg/dL", "mmol/L", ("NHANES BIOPRO_L", 0.250)),
            ("iron", "µg/dL", "µmol/L", ("NHANES BIOPRO_L", 0.1791)),
            ("phosphorus", "mg/dL", "mmol/L", ("NHANES BIOPRO_L", 0.323)),
            ("magnesium", "mg/dL", "mmol/L", None), ("zinc", "µg/dL", "µmol/L", None)]

an = {a["id"]: a for a in spec["analytes"]}
print("| # | Analyte | PubChem CID / element | Formula | PubChem MW | MW from formula (CIAAW) | Diff | "
      "lifefrom-units factor | Published factor | Diff vs published |")
print("|---|---|---|---|---|---|---|---|---|---|")
n = 0
for a, frm, to, pub in ROWS:
    n += 1
    src = spec["sources"][an[a]["molar_mass"]["source"]]
    mw = F(src["molar_mass"])
    fm = formula_mass(src["formula"])
    fac = L.convert(1, frm, to, analyte=a)
    pd = f"{(fac - pub[1]) / pub[1]:+.2%}" if pub else ""
    print(f"| {n} | {a} ({frm} → {to}) | {src['pubchem_cid']} | {src['formula']} | {src['molar_mass']} | "
          f"{float(fm):.3f} | {float((mw - fm) / fm):+.3%} | {fac:.5g} | "
          f"{(str(pub[1]) + ' (' + pub[0] + ')') if pub else '—'} | {pd} |")
for a, frm, to, pub in ELEMENTS:
    n += 1
    src = spec["sources"][an[a]["molar_mass"]["source"]]
    fac = L.convert(1, frm, to, analyte=a)
    pd = f"{(fac - pub[1]) / pub[1]:+.2%}" if pub else ""
    print(f"| {n} | {a} ({frm} → {to}) | {src['element']} (CIAAW) | {src['element']} | — | {src['molar_mass']} | — | "
          f"{fac:.5g} | {(str(pub[1]) + ' (' + pub[0] + ')') if pub else '—'} | {pd} |")
