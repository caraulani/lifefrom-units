"""Generate tests/vectors.json, the shared test vectors for the Python and TypeScript packages.

Expected values are computed here independently of the lifefrom-units engine: unit scales come from
a separate hand-written prefix table, molar masses are read straight from the raw PubChem and
CIAAW files, and a set of hand-checked cases is typed in directly. Run: python3 -I scripts/make_vectors.py
"""
from __future__ import annotations

import html
import json
import os
import re
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = Path(os.environ.get("LABUNITS_RAW", ROOT.parent / "_raw"))

V: list = []


def add(op, inp, expect=None, error=None, note=None, tol=1e-9, abs_tol=None):
    v = {"id": f"{op}-{len(V) + 1:04d}", "op": op, "input": inp}
    if error:
        v["error"] = error
    else:
        v["expect"] = expect
        if op in ("convert", "roundtrip", "convert_result"):
            v["rel_tol"] = tol
            if abs_tol is not None:
                v["abs_tol"] = abs_tol
    if note:
        v["note"] = note
    V.append(v)


# ---------------------------------------------------------------------------
# Independent scale table (value in unit × scale = value in base unit)
# ---------------------------------------------------------------------------
P = {"": F(1), "k": F(10**3), "d": F(1, 10), "m": F(1, 10**3), "µ": F(1, 10**6), "n": F(1, 10**9),
     "p": F(1, 10**12), "f": F(1, 10**15)}
VOLS = {"L": F(1), "dL": F(1, 10), "mL": F(1, 10**3)}


def scale(u: str) -> F:
    m = re.fullmatch(r"([kdmµnpf]?)(g|mol|IU|U|Eq)/(L|dL|mL)", u)
    if m:
        return P[m.group(1)] / VOLS[m.group(3)]
    table = {"/L": 1, "/µL": 10**6, "/mm³": 10**6, "/nL": 10**9, "10^3/µL": 10**9, "10^9/L": 10**9,
             "10^6/µL": 10**12, "10^12/L": 10**12, "%": F(1, 100), "fraction": 1, "L/L": 1, "‰": F(1, 1000),
             "mmol/mol": F(1, 1000), "mg/24h": F(1, 1000) / 86400, "g/24h": F(1, 86400),
             "mmol/24h": F(1, 1000) / 86400, "µkat/L": F(1, 10**6), "nkat/L": F(1, 10**9),
             "mg/g": F(1, 1000), "µg/g": F(1, 10**6), "mg/kg": F(1, 10**6), "mg/mmol": 1, "s": 1, "min": 60,
             "h": 3600, "fL": F(1, 10**15), "µg": F(1, 10**6), "mg": F(1, 1000), "IU": 1}
    return F(table[u])


def lin(v, a, b):
    return float(F(str(v)) * scale(a) / scale(b))


# ---------------------------------------------------------------------------
# Raw molar masses
# ---------------------------------------------------------------------------
def pubchem(cid):
    p = json.loads((RAW / "pubchem" / f"cid_{cid}.json").read_text())["PropertyTable"]["Properties"][0]
    return F(p["MolecularWeight"])


def ciaaw(sym):
    t = (RAW / "ciaaw" / "abridged.htm").read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"[ \t\xa0]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    m = re.search(r"\n\s*\d+\s+" + sym + r"\s+[a-z]+\s+([0-9.]+)\s*±", t)
    return F(m.group(1))


MOLAR = {
    "glucose": ("pubchem", 5793), "cholesterol": ("pubchem", 5997), "creatinine": ("pubchem", 588),
    "uric-acid": ("pubchem", 1175), "bilirubin": ("pubchem", 5280352), "urea": ("pubchem", 1176),
    "calcium": ("ciaaw", "Ca"), "magnesium": ("ciaaw", "Mg"), "phosphorus": ("ciaaw", "P"),
    "iron": ("ciaaw", "Fe"), "zinc": ("ciaaw", "Zn"), "copper": ("ciaaw", "Cu"), "selenium": ("ciaaw", "Se"),
    "manganese": ("ciaaw", "Mn"), "chromium": ("ciaaw", "Cr"), "sodium": ("ciaaw", "Na"),
    "potassium": ("ciaaw", "K"), "chloride": ("ciaaw", "Cl"), "cortisol": ("pubchem", 5754),
    "testosterone": ("pubchem", 6013), "estradiol": ("pubchem", 5757), "estrone": ("pubchem", 5870),
    "dhea-s": ("pubchem", 12594), "dhea": ("pubchem", 5881), "androstenedione": ("pubchem", 6128),
    "17-hydroxyprogesterone": ("pubchem", 6238), "progesterone": ("pubchem", 5994),
    "aldosterone": ("pubchem", 5839), "dihydrotestosterone": ("pubchem", 10635),
    "pregnenolone": ("pubchem", 8955), "folate": ("pubchem", 135398658), "triiodothyronine": ("pubchem", 5920),
    "thyroxine": ("pubchem", 5819), "vitamin-b12": ("pubchem", 5311498),
    "25-hydroxyvitamin-d": ("pubchem", 5283731), "1-25-dihydroxyvitamin-d": ("pubchem", 5280453),
    "homocysteine": ("pubchem", 91552), "methylmalonic-acid": ("pubchem", 487), "vitamin-a": ("pubchem", 445354),
    "vitamin-c": ("pubchem", 54670067), "vitamin-e": ("pubchem", 14985), "vitamin-k": ("pubchem", 5284607),
    "lactate": ("pubchem", 612),
}
MARKER = {"glucose": "glucose-fasting", "cholesterol": "ldl-cholesterol", "creatinine": "creatinine-serum",
          "bilirubin": "total-bilirubin", "calcium": "calcium-total", "magnesium": "magnesium-serum",
          "iron": "serum-iron", "testosterone": "testosterone-total", "cortisol": "cortisol-am",
          "25-hydroxyvitamin-d": "vitamin-d-25-oh", "thyroxine": "free-t4", "triiodothyronine": "free-t3",
          "folate": "folate-serum", "sodium": "sodium-serum", "potassium": "potassium-serum"}


def mm(a):
    k, x = MOLAR[a]
    return pubchem(x) if k == "pubchem" else ciaaw(x)


def mass_to_sub(v, mu, su, M):
    # v [mu] -> [su]
    return float(F(str(v)) * scale(mu) / M / scale(su))


def sub_to_mass(v, su, mu, M):
    return float(F(str(v)) * scale(su) * M / scale(mu))


# ---------------------------------------------------------------------------
# 1. normalize: spelling variants
# ---------------------------------------------------------------------------
NORM = {
    "µg/L": ["µg/L", "ug/L", "mcg/L", "μg/L", "ug/l", "UG/L", "MCG/L", "µg / L", " µg/L ", "μg/l", "mcg/l", "Ug/L"],
    "µg/dL": ["ug/dL", "mcg/dL", "μg/dL", "ug/dl", "MCG/DL", "µg%", "µg/100mL"],
    "µg/mL": ["ug/mL", "mcg/mL", "μg/ml", "UG/ML"],
    "mg/dL": ["mg/dL", "mg/dl", "MG/DL", "Mg/dL", "mg%", "mg/100mL", "mg/100 mL", "mg / dL"],
    "g/dL": ["g/dl", "G/DL", "g%", "g/100 mL"],
    "g/L": ["g/L", "g/l"],
    "ng/mL": ["ng/ml", "NG/ML", "ng / mL"],
    "pg/mL": ["pg/ml", "PG/ML"],
    "mmol/L": ["mmol/L", "mmol/l", "MMOL/L", "mM", "mmol / L"],
    "µmol/L": ["umol/L", "µmol/l", "μmol/L", "umol/l", "UMOL/L", "µM", "uM", "μM", "mcmol/L"],
    "nmol/L": ["nmol/l", "NMOL/L", "nM"],
    "pmol/L": ["pmol/l", "pM", "PMOL/L"],
    "mEq/L": ["mEq/L", "meq/L", "MEQ/L", "meq/l", "mEq/l"],
    "mIU/mL": ["mIU/mL", "mIU/ml", "mUI/mL", "MIU/ML", "m[IU]/mL", "mui/ml"],
    "µIU/mL": ["uIU/mL", "µIU/ml", "μIU/mL", "µUI/mL", "uUI/mL", "u[IU]/mL", "UIU/ML", "mcIU/mL"],
    "mIU/L": ["mIU/l", "mUI/L", "m[IU]/L"],
    "IU/L": ["IU/l", "UI/L", "[IU]/L", "iu/l"],
    "IU/mL": ["IU/ml", "UI/mL", "[IU]/mL"],
    "kIU/L": ["kIU/l", "kUI/L"],
    "U/L": ["U/l", "u/l"],
    "µU/mL": ["uU/mL", "μU/mL", "µU/ml"],
    "kU/L": ["kU/l", "KU/L"],
    "µkat/L": ["ukat/L", "µkat/l", "μkat/L"],
    "10^9/L": ["10^9/L", "10E9/L", "10e9/L", "10*9/L", "x10^9/L", "x10E9/L", "×10⁹/L", "×10^9/L", "X10^9/L",
               "10⁹/L", "x 10^9/L", "x10*9/L", "G/L", "Giga/L", "10**9/L", "10^9/l", "10^9 cells/L"],
    "10^12/L": ["10^12/L", "10E12/L", "x10^12/L", "×10¹²/L", "10*12/L", "T/L"],
    "10^3/µL": ["10^3/µL", "10^3/uL", "10E3/uL", "x10E3/uL", "10*3/uL", "K/uL", "K/µL", "K/μL", "×10³/µL",
                "Thousand/uL", "Thou/uL", "x1000/uL", "1000/µL", "10^3/ul", "k/ul", "K/UL"],
    "10^6/µL": ["10^6/uL", "x10E6/uL", "M/uL", "M/µL", "Million/uL", "10*6/uL", "×10⁶/µL"],
    "10^3/mm³": ["K/mm³", "K/mm3", "10^3/mm3"],
    "/µL": ["/uL", "/µL", "cells/uL", "cells/µL", "/μL", "/ul"],
    "/mm³": ["/mm3", "/mm³", "/cmm", "cells/mm3", "/MM3"],
    "/nL": ["/nL", "/nl"],
    "%": ["%", "percent", "Percent"],
    "fraction": ["fraction", "proportion"],
    "L/L": ["L/L", "l/l"],
    "mmol/mol": ["mmol/mol", "MMOL/MOL", "mmol/mol Hb"],
    "mg/24h": ["mg/24h", "mg/24 h", "mg/day", "mg/d", "mg/24hr", "mg/24 hours", "mg/24 hrs"],
    "g/24h": ["g/24h", "g/day", "g/24 h"],
    "mmol/24h": ["mmol/24h", "mmol/day", "mmol/24 h"],
    "mm/h": ["mm/h", "mm/hr", "mm/hour", "MM/HR", "mm/1h"],
    "s": ["s", "sec", "seconds"],
    "fL": ["fL", "fl", "FL", "µm3", "um3", "µm³"],
    "mg/g": ["mg/g", "mg/g creatinine", "mg/g Cr", "mg/gCr"],
    "mg/mmol": ["mg/mmol", "mg/mmol creatinine", "mg/mmol Cr"],
    "µg/g": ["ug/g", "mcg/g", "µg/g creatinine"],
    "mOsm/kg": ["mOsm/kg", "mOsm/kg H2O", "mosmol/kg", "MOSM/KG"],
    "mg/L FEU": ["mg/L FEU", "mg/l FEU", "mg/L (FEU)"],
    "µg/mL FEU": ["ug/mL FEU", "mcg/mL FEU", "µg/mL FEU"],
    "µg/L DDU": ["ug/L DDU", "µg/L DDU"],
    "ng/mL/h": ["ng/mL/hr", "ng/mL/h", "ng/ml/h"],
    "mL/min/1.73m²": ["mL/min/1.73m²", "mL/min/1.73m2", "mL/min/1.73 m2", "ml/min/1.73m2", "mL/min/1,73m2"],
    "S/CO": ["S/CO", "s/co"],
    "titer": ["titer", "titre"],
    "pH": ["pH", "pH units"],
    "/hpf": ["/hpf", "/HPF"],
    "nmol/min/mL": ["nmol/min/mL", "nmol/mL/min"],
}
for canon, variants in NORM.items():
    for s in dict.fromkeys([canon] + variants):
        add("normalize", {"unit": s}, {"unit": canon})

for bad in ["foo", "", "   ", "mg/dL/x", "nm", "NM", "mg/dLL", "10^9", "cells", "g/mm", "kg/L/s/x"]:
    add("normalize", {"unit": bad}, error="unknown_unit")

# ---------------------------------------------------------------------------
# 2. same_unit
# ---------------------------------------------------------------------------
SAME_TRUE = [("µg/L", "ng/mL"), ("ug/L", "ng/ml"), ("mcg/L", "ng/mL"), ("mg/L", "µg/mL"), ("ng/L", "pg/mL"),
             ("nmol/L", "pmol/mL"), ("nM", "nmol/L"), ("mIU/mL", "IU/L"), ("µIU/mL", "mIU/L"), ("kU/L", "U/mL"),
             ("kIU/L", "IU/mL"), ("10^9/L", "10^3/µL"), ("K/µL", "/nL"), ("G/L", "10^9/L"), ("10^12/L", "M/µL"),
             ("/µL", "/mm³"), ("cells/uL", "/cmm"), ("L/L", "fraction"), ("mg/kg", "µg/g"), ("g/day", "g/24h"),
             ("mm/hr", "mm/h"), ("mOsm/kg H2O", "mOsm/kg"), ("µm3", "fL"), ("ng/mL/h", "µg/L/h"),
             ("µmol/mol", "µmol/mol"), ("mg/dL", "mg%")]
SAME_FALSE = [("mg/dL", "mg/L"), ("mg/dL", "mmol/L"), ("g/L", "G/L"), ("U/L", "IU/L"), ("mU/L", "mIU/L"),
              ("%", "mmol/mol"), ("%", "fraction"), ("µg/L", "µg/dL"), ("S/CO", "index"), ("mEq/L", "mmol/L"),
              ("10^9/L", "/µL"), ("mg/L FEU", "mg/L DDU"), ("mg/L FEU", "mg/L"), ("ng/mL", "ng/dL")]
for a, b in SAME_TRUE:
    add("same_unit", {"a": a, "b": b}, {"same": True})
    add("same_unit", {"a": b, "b": a}, {"same": True})
for a, b in SAME_FALSE:
    add("same_unit", {"a": a, "b": b}, {"same": False})
for an in ["sodium", "potassium", "chloride", "bicarbonate-co2", "anion-gap", "urine-sodium"]:
    add("same_unit", {"a": "mEq/L", "b": "mmol/L", "analyte": an}, {"same": True})
for an in ["calcium", "magnesium-serum"]:
    add("same_unit", {"a": "mEq/L", "b": "mmol/L", "analyte": an}, {"same": False})
add("same_unit", {"a": "IU/L", "b": "U/L", "analyte": "alt"}, {"same": True})
add("same_unit", {"a": "IU/L", "b": "U/L", "analyte": "ca-125"}, {"same": False})
add("same_unit", {"a": "mg/dL", "b": "nmol/L", "analyte": "lipoprotein-a"}, {"same": False})
add("same_unit", {"a": "xyz", "b": "mg/dL"}, error="unknown_unit")

# ---------------------------------------------------------------------------
# 3. parse_value
# ---------------------------------------------------------------------------
PV = [("5,4", 5.4), ("5.4", 5.4), ("0,5", 0.5), ("-0,5", -0.5), (",5", 0.5), ("12,75", 12.75), ("1.234,5", 1234.5),
      ("1,234.5", 1234.5), ("1 234,5", 1234.5), ("1 234,5", 1234.5), ("1 234.5", 1234.5),
      ("1.234.567", 1234567.0), ("1,234,567", 1234567.0), ("1234,567", 1234.567), ("0,123", 0.123),
      ("5.4e3", 5400.0), ("5,4e3", 5400.0), ("1e-3", 0.001), ("+7", 7.0), ("−3,2", -3.2), (" 42 ", 42.0),
      ("3.", 3.0), ("1'234.5", 1234.5), (7, 7.0), (7.25, 7.25), (0, 0.0), ("1.025", 1.025)]
for s, x in PV:
    add("parse_value", {"value": s}, {"value": x})
for s in ["1,234", "12,345", "999,000"]:
    add("parse_value", {"value": s}, error="ambiguous_value")
for s in ["<5", ">100", "5,4 H", "5.4 L", "≥ 7", "12 HH", "3,1 (L)"]:
    add("parse_value", {"value": s}, error="qualified_value", note="qualifier must not be dropped silently")
for s in ["5-10", "", "abc", "positive", "1,2,3", "1..2", "5 mg", "NaN", "1.2.3", "H", "<", "< H"]:
    add("parse_value", {"value": s}, error="invalid_value")
add("parse_value", {"value": "1,23,456"}, error="invalid_value")

# ---------------------------------------------------------------------------
# 4. unit arithmetic conversions (no analyte) + round trips
# ---------------------------------------------------------------------------
GROUPS = [
    ["g/L", "g/dL", "g/mL", "mg/L", "mg/dL", "mg/mL", "µg/L", "µg/dL", "µg/mL", "ng/L", "ng/dL", "ng/mL", "pg/mL"],
    ["mol/L", "mmol/L", "µmol/L", "nmol/L", "pmol/L", "nmol/mL", "pmol/mL", "fmol/mL"],
    ["IU/L", "IU/mL", "mIU/L", "mIU/mL", "µIU/mL", "kIU/L", "IU/dL"],
    ["U/L", "U/mL", "kU/L", "mU/mL", "mU/L"],
    ["/L", "/µL", "/mm³", "/nL", "10^3/µL", "10^9/L", "10^6/µL", "10^12/L"],
    ["%", "fraction", "L/L", "‰"],
    ["µkat/L", "nkat/L"],
    ["mg/24h", "g/24h"],
    ["mg/g", "µg/g", "mg/kg"],
    ["s", "min", "h"],
]
VALUES = [1, 5.4, 0.037, 250]
k = 0
for g in GROUPS:
    for a in g:
        for b in g:
            if a == b:
                continue
            v = VALUES[k % len(VALUES)]
            k += 1
            add("convert", {"value": v, "from": a, "to": b}, {"value": lin(v, a, b)})
            if k % 3 == 0:
                add("roundtrip", {"value": v, "a": a, "b": b}, {"value": float(v)}, tol=1e-12)
# spelling variants feed the same arithmetic
for v, a, b, x in [("5,4", "ug/l", "ng/ML", 5.4), ("1,5", "mcg/mL", "mg/L", 1.5), (7.2, "x10E9/L", "K/uL", 7.2),
                   (7.2, "×10⁹/L", "/nL", 7.2), (4.5, "10^12/L", "M/uL", 4.5), (250, "K/µL", "10^9/L", 250),
                   (4500, "cells/uL", "10^9/L", 4.5), (45, "%", "L/L", 0.45), (0.45, "proportion", "%", 45),
                   (12, "mm/hr", "mm/h", 12), (1.2, "g/day", "mg/24h", 1200), (3.2, "mIU/ml", "IU/L", 3.2),
                   (3.2, "µUI/mL", "mIU/L", 3.2), (2, "uIU/mL", "mIU/L", 2), (30, "IU/l", "IU/L", 30),
                   ("2,5", "μmol/l", "nmol/L", 2500), (40, "mmol/l", "µmol/L", 40000), (1, "g%", "g/L", 10)]:
    add("convert", {"value": v, "from": a, "to": b}, {"value": float(x)})

# ---------------------------------------------------------------------------
# 5. analyte conversions via molar mass
# ---------------------------------------------------------------------------
PAIRS = [("mg/dL", "mmol/L"), ("µg/dL", "µmol/L"), ("ng/mL", "nmol/L"), ("pg/mL", "pmol/L"), ("ng/dL", "nmol/L"),
         ("mg/L", "µmol/L"), ("µg/L", "nmol/L"), ("g/L", "mmol/L")]
TVAL = [100, 1.2, 37.5, "5,4", 0.85, 250, "12,5", 3]
i = 0
for a in MOLAR:
    M = mm(a)
    for j, (mu, su) in enumerate(PAIRS[:5] if a in ("glucose", "cholesterol", "creatinine") else PAIRS[:3]):
        v = TVAL[i % len(TVAL)]
        i += 1
        vv = F(str(v).replace(",", "."))
        add("convert", {"value": v, "from": mu, "to": su, "analyte": a},
            {"value": float(vv * scale(mu) / M / scale(su))})
        add("convert", {"value": v, "from": su, "to": mu, "analyte": a},
            {"value": float(vv * scale(su) * M / scale(mu))})
        if j == 0:
            add("roundtrip", {"value": 7.3, "a": mu, "b": su, "analyte": a}, {"value": 7.3}, tol=1e-12)
    if a in MARKER:
        add("convert", {"value": 2, "from": "mg/dL", "to": "µmol/L", "analyte": MARKER[a]},
            {"value": float(F(2) * scale("mg/dL") / M / scale("µmol/L"))}, note="analyte given as marker slug")
# mass_rate <-> substance_rate
for a in ["creatinine", "sodium", "potassium", "urea"]:
    M = mm(a)
    add("convert", {"value": 1500, "from": "mg/24h", "to": "mmol/24h", "analyte": a},
        {"value": float(F(1500) * scale("mg/24h") / M / scale("mmol/24h"))})

# charge
for a, z in [("sodium", 1), ("potassium", 1), ("chloride", 1), ("calcium", 2), ("magnesium", 2), ("bicarbonate", 1)]:
    add("convert", {"value": "2,4", "from": "mmol/L", "to": "mEq/L", "analyte": a}, {"value": float(F("2.4") * z)})
    add("convert", {"value": 4.8, "from": "mEq/L", "to": "mmol/L", "analyte": a}, {"value": float(F("4.8") / z)})
add("convert", {"value": 2, "from": "mEq/L", "to": "mg/dL", "analyte": "magnesium-serum"},
    {"value": float(F(2) / 2 * F(1, 1000) * ciaaw("Mg") / F(1, 100))}, note="mEq/L -> mmol/L -> mg/dL")
add("convert", {"value": 5, "from": "mEq/L", "to": "mg/dL", "analyte": "calcium-ionized"},
    {"value": float(F(5) / 2 * F(1, 1000) * ciaaw("Ca") / F(1, 100))})

# BUN and urea
N2 = pubchem(947)
for v in [7, 14, "20,5", 60]:
    vv = F(str(v).replace(",", "."))
    add("convert", {"value": v, "from": "mg/dL", "to": "mmol/L", "analyte": "blood-urea-nitrogen"},
        {"value": float(vv * F(1, 100) / N2 * 1000)}, note="mg/dL urea nitrogen -> mmol/L urea")
add("convert", {"value": 5, "from": "mmol/L", "to": "mg/dL", "analyte": "urea"},
    {"value": float(F(5) / 1000 * pubchem(1176) * 100)})

# published factors
add("convert", {"value": 150, "from": "mg/dL", "to": "mmol/L", "analyte": "triglycerides"},
    {"value": float(F(150) * F("0.01129"))}, note="NHANES TRIGLY_L factor 0.01129")
add("convert", {"value": "1,7", "from": "mmol/L", "to": "mg/dL", "analyte": "triglycerides"},
    {"value": float(F("1.7") / F("0.01129"))})
add("convert", {"value": 150, "from": "mg/dL", "to": "mmol/L", "analyte": "triglycerides"},
    {"value": float(F(150) * 10 / pubchem(5497163))}, tol=5e-4, note="triolein molar mass cross-check")
add("convert", {"value": 2, "from": "ng/mL", "to": "pmol/L", "analyte": "amh"}, error="forbidden",
    note="AMH: protein; NHANES 7.14 not stated to be assay-independent")
add("convert", {"value": 2, "from": "ng/mL", "to": "pmol/L", "analyte": "amh", "factor": 7.14}, {"value": 14.28},
    note="caller-supplied factor")

# hand-checked against published tables (relative tolerance = table rounding)
HAND = [
    (100, "mg/dL", "mmol/L", "glucose", 5.551, 2e-4, "NHANES GLU_L x 0.05551"),
    (200, "mg/dL", "mmol/L", "total-cholesterol", 5.172, 2e-4, "NHANES TCHOL_L x 0.02586"),
    (1, "mg/dL", "µmol/L", "creatinine-serum", 88.4, 1e-3, "NHANES BIOPRO_L x 88.4"),
    (1, "mg/dL", "µmol/L", "uric-acid", 59.48, 1e-3, "NHANES BIOPRO_L x 59.48"),
    (1, "mg/dL", "µmol/L", "total-bilirubin", 17.1, 1e-3, "NHANES BIOPRO_L x 17.1"),
    (100, "µg/dL", "µmol/L", "serum-iron", 17.91, 1e-3, "NHANES BIOPRO_L x 0.1791"),
    (10, "mg/dL", "mmol/L", "phosphorus-serum", 3.23, 2e-3, "NHANES BIOPRO_L x 0.323"),
    (10, "mg/dL", "mmol/L", "calcium-total", 2.50, 3e-3, "NHANES BIOPRO_L x 0.250"),
    (10, "mg/dL", "mmol/L", "blood-urea-nitrogen", 3.57, 1e-3, "NHANES BIOPRO_L x 0.357"),
    (500, "ng/dL", "nmol/L", "testosterone-total", 17.35, 2e-3, "NHANES TST_L x 0.0347"),
    (100, "pg/mL", "pmol/L", "estradiol-e2", 367, 2e-3, "NHANES TST_L x 3.67"),
    (100, "µg/dL", "µmol/L", "dhea-s", 2.71, 2e-3, "NHANES TST_L x 0.0271"),
    (100, "ng/dL", "nmol/L", "androstenedione", 3.49, 2e-3, "NHANES TST_L x 0.0349"),
    (100, "ng/dL", "nmol/L", "17-hydroxyprogesterone", 3.03, 2e-3, "NHANES TST_L x 0.0303"),
    (100, "ng/dL", "nmol/L", "progesterone", 3.18, 2e-3, "NHANES TST_L x 0.0318"),
    (10, "ng/dL", "pmol/L", "estrone-e1", 370, 3e-3, "NHANES TST_L x 37.0"),
    (10, "ng/mL", "nmol/L", "folate-rbc", 22.65, 1e-3, "NHANES FOLATE_L / 2.265"),
    (30, "ng/mL", "nmol/L", "vitamin-d-25-oh", 75, 2e-3, "IOM 2011: divide nmol/L by 2.5"),
]
for v, a, b, an, x, tol, note in HAND:
    add("convert", {"value": v, "from": a, "to": b, "analyte": an}, {"value": x}, tol=tol, note=note)

# enzymes
for an in ["alt", "ast", "alp", "ggt", "ldh", "ck-total", "amylase", "lipase"]:
    add("convert", {"value": 60, "from": "U/L", "to": "µkat/L", "analyte": an}, {"value": 1.0})
    add("convert", {"value": "0,5", "from": "µkat/L", "to": "U/L", "analyte": an}, {"value": 30.0})
    add("convert", {"value": 42, "from": "IU/L", "to": "U/L", "analyte": an}, {"value": 42.0})
    add("convert", {"value": 42, "from": "IU/L", "to": "µkat/L", "analyte": an}, {"value": 0.7})
add("convert", {"value": 200, "from": "nmol/min/mL", "to": "U/L", "analyte": "lp-pla2"}, {"value": 200.0},
    note="1 nmol/min/mL = 1 µmol/min/L = 1 U/L")
add("convert", {"value": 1, "from": "U/L", "to": "nkat/L", "analyte": "alt"}, {"value": float(F(1000, 60))})

# creatinine ratios
Mc = pubchem(588)
for an in ["urine-acr", "urine-protein-creatinine-ratio"]:
    add("convert", {"value": 30, "from": "mg/g", "to": "mg/mmol", "analyte": an},
        {"value": float(F(30) / 1000 * Mc)})
    add("convert", {"value": "3,4", "from": "mg/mmol", "to": "mg/g", "analyte": an},
        {"value": float(F("3.4") / Mc * 1000)})

# HbA1c master equation: NGSP = 0.09148*IFCC + 2.152
for ifcc in [20, 31, 42, 48, 53, 64, 75, 86, 97, 108]:
    add("convert", {"value": ifcc, "from": "mmol/mol", "to": "%", "analyte": "hba1c"},
        {"value": float(F("0.09148") * ifcc + F("2.152"))})
for ngsp in [4.0, 5.0, "5,7", 6.5, 7.0, 8.0, 10.0, 12.0]:
    nv = F(str(ngsp).replace(",", "."))
    add("convert", {"value": ngsp, "from": "%", "to": "mmol/mol", "analyte": "hba1c"},
        {"value": float((nv - F("2.152")) / F("0.09148"))})
# NGSP Table 1 (rounded to whole mmol/mol)
for ngsp, ifcc in [(5.0, 31), (6.0, 42), (7.0, 53), (8.0, 64), (9.0, 75), (10.0, 86), (11.0, 97), (12.0, 108)]:
    add("convert", {"value": ngsp, "from": "%", "to": "mmol/mol", "analyte": "hba1c"}, {"value": float(ifcc)},
        tol=0, abs_tol=0.5, note="NGSP Table 1, rounded")
add("roundtrip", {"value": 6.1, "a": "%", "b": "mmol/mol", "analyte": "hba1c"}, {"value": 6.1}, tol=1e-12)
add("convert", {"value": 0.065, "from": "fraction", "to": "mmol/mol", "analyte": "hba1c"}, error="forbidden")

# vitamin D dose
add("convert", {"value": 1000, "from": "IU", "to": "µg", "analyte": "vitamin-d-dose"}, {"value": 25.0})
add("convert", {"value": 10, "from": "µg", "to": "IU", "analyte": "vitamin-d-dose"}, {"value": 400.0})
add("convert", {"value": "2,5", "from": "mg", "to": "IU", "analyte": "vitamin-d-dose"}, {"value": 100000.0})

# ---------------------------------------------------------------------------
# 6. errors
# ---------------------------------------------------------------------------
for a, b in [("mg/dL", "nmol/L"), ("nmol/L", "mg/dL"), ("mg/L", "nmol/L"), ("g/L", "µmol/L"), ("mg/dl", "nM")]:
    add("convert", {"value": 50, "from": a, "to": b, "analyte": "lipoprotein-a"}, error="forbidden")
add("convert", {"value": 50, "from": "mg/dL", "to": "nmol/L", "analyte": "Lipoprotein-A"}, error="forbidden",
    note="analyte lookup is case-insensitive")
for a, b in [("µIU/mL", "pmol/L"), ("pmol/L", "µIU/mL"), ("mIU/L", "pmol/L"), ("uIU/mL", "pmol/L")]:
    add("convert", {"value": 10, "from": a, "to": b, "analyte": "fasting-insulin"}, error="forbidden")
for a, b in [("%", "mmol/mol"), ("mmol/mol", "%"), ("‰", "mmol/mol")]:
    add("convert", {"value": 6, "from": a, "to": b}, error="forbidden")
for a, b in [("%", "fraction"), ("%", "L/L"), ("fraction", "%"), ("‰", "mmol/mol")]:
    add("convert", {"value": 6, "from": a, "to": b, "analyte": "hba1c"}, error="forbidden")
for a, b in [("IU/mL", "ng/mL"), ("IU/L", "nmol/L"), ("ng/mL", "IU/mL")]:
    add("convert", {"value": 30, "from": a, "to": b, "analyte": "vitamin-d-25-oh"}, error="forbidden")
ARB = ["S/CO", "index", "AI", "EU", "CU", "AU/mL", "titer", "ratio", "qualitative", "/hpf", "EU/dL"]
for i, a in enumerate(ARB):
    b = ARB[(i + 1) % len(ARB)]
    add("convert", {"value": 1, "from": a, "to": b}, error="forbidden")
    add("convert", {"value": 1, "from": a, "to": "U/mL"}, error="forbidden")
    add("convert", {"value": 2.5, "from": a, "to": a}, {"value": 2.5}, note="identity is allowed")
add("convert", {"value": 1, "from": "urobilinogen", "to": "mg/dL"}, error="unknown_unit")
add("convert", {"value": 1, "from": "mg/dL", "to": "EU/dL", "analyte": "urine-urobilinogen"}, error="forbidden")
for a, b in [("mg/dL", "mmol/L"), ("µg/dL", "nmol/L"), ("U/L", "µkat/L"), ("IU/L", "U/L"), ("mEq/L", "mmol/L"),
             ("mg/g", "mg/mmol"), ("IU", "µg"), ("mg/dL", "U/L"), ("10^9/L", "g/L"), ("mU/L", "mIU/L")]:
    add("convert", {"value": 1, "from": a, "to": b}, error="incompatible_units")
for a, b, an in [("mU/L", "mIU/L", "tsh"), ("g/dL", "mmol/L", "hemoglobin"), ("µg/dL", "µmol/L", "ammonia"),
                 ("U/mL", "IU/mL", "rheumatoid-factor"), ("U/L", "µkat/L", "ca-125"), ("mg/dL", "mmol/L", "ferritin"),
                 ("pmol/L", "pg/mL", "pth"), ("IU/L", "U/L", "tsh"), ("mg/dL", "mmol/L", "bicarbonate"),
                 ("mEq/L", "mg/dL", "phosphorus"), ("ng/mL", "pmol/L", "c-peptide"), ("µg/L DDU", "mg/L FEU", "d-dimer")]:
    add("convert", {"value": 1, "from": a, "to": b, "analyte": an}, error="no_sourced_conversion")
for an in ["glucoze", "", "mg/dL"]:
    add("convert", {"value": 1, "from": "mg/dL", "to": "mmol/L", "analyte": an}, error="unknown_analyte")
for v in ["<5", ">1000", "5,4 H"]:
    add("convert", {"value": v, "from": "mg/dL", "to": "g/L"}, error="qualified_value")
for v in ["n/a", ""]:
    add("convert", {"value": v, "from": "mg/dL", "to": "g/L"}, error="invalid_value")
add("convert", {"value": "1,234", "from": "mg/dL", "to": "g/L"}, error="ambiguous_value")
add("convert", {"value": 1, "from": "mg/dL", "to": "furlong"}, error="unknown_unit")

# ---------------------------------------------------------------------------
# 6b. censored and flagged values
# ---------------------------------------------------------------------------
PR = [("<5", 5.0, "<", None), (">1000", 1000.0, ">", None), ("5.4 H", 5.4, None, "H"), ("5,4 L", 5.4, None, "L"),
      ("<0,5", 0.5, "<", None), ("> 1.234,5", 1234.5, ">", None), ("<=3", 3.0, "<=", None), (">=3", 3.0, ">=", None),
      ("≤ 3,2", 3.2, "<=", None), ("≥7", 7.0, ">=", None), ("=<4", 4.0, "<=", None), ("12 HH", 12.0, None, "HH"),
      ("0,8 LL", 0.8, None, "LL"), ("5.4H", 5.4, None, "H"), ("5.4 h", 5.4, None, "H"), ("3,1 (L)", 3.1, None, "L"),
      ("3.1 [H]", 3.1, None, "H"), ("7 *", 7.0, None, "*"), ("7 A", 7.0, None, "A"), ("9,9 ↑", 9.9, None, "↑"),
      ("1,1 ↓", 1.1, None, "↓"), ("> 90 H", 90.0, ">", "H"), ("5,4", 5.4, None, None), (" 42 ", 42.0, None, None),
      (7.5, 7.5, None, None)]
for t, v, c, f in PR:
    add("parse_result", {"value": t}, {"value": v, "comparator": c, "flag": f})
for t in ["<", "H", "<abc", "1,234 H", "5 mg"]:
    add("parse_result", {"value": t}, error=("ambiguous_value" if t == "1,234 H" else "invalid_value"))
G = mm("glucose")
for t, v, c, f in [("<5", 5, "<", None), (">1000", 1000, ">", None), ("5,4 H", "5.4", None, "H"),
                   ("2,1 L", "2.1", None, "L"), ("≥ 7", 7, ">=", None)]:
    add("convert_result", {"value": t, "from": "mg/dL", "to": "mmol/L", "analyte": "glucose"},
        {"value": float(F(str(v)) * F(1, 100) / G * 1000), "comparator": c, "flag": f, "unit": "mmol/L"})
add("convert_result", {"value": "<0,5", "from": "mg/L", "to": "mg/dL"},
    {"value": 0.05, "comparator": "<", "flag": None, "unit": "mg/dL"})
add("convert_result", {"value": "48 H", "from": "mmol/mol", "to": "%", "analyte": "hba1c"},
    {"value": float(F("0.09148") * 48 + F("2.152")), "comparator": None, "flag": "H", "unit": "%"})
add("convert_result", {"value": "<3", "from": "µIU/mL", "to": "pmol/L", "analyte": "insulin", "factor": 6},
    {"value": 18.0, "comparator": "<", "flag": None, "unit": "pmol/L"})
add("convert_result", {"value": "<5", "from": "mg/dL", "to": "nmol/L", "analyte": "lipoprotein-a"}, error="forbidden")

# ---------------------------------------------------------------------------
# 6c. caller-supplied factor (never a default)
# ---------------------------------------------------------------------------
for v, a, b, an, f, x in [(10, "µIU/mL", "pmol/L", "insulin", 6, 60.0), (10, "µIU/mL", "pmol/L", "fasting-insulin", 6.945, 69.45),
                          (2.5, "mU/L", "mIU/L", "tsh", 1, 2.5), (120, "kU/L", "IU/mL", "ige-total", 1, 120.0),
                          (50, "mg/dL", "nmol/L", "lipoprotein-a", 2.5, 125.0), (1, "S/CO", "index", None, 1, 1.0),
                          (100, "mg/dL", "mmol/L", "glucose", 0.0555, 5.55), (3, "ng/mL", "pmol/L", "amh", 7.14, 21.42)]:
    add("convert", {"value": v, "from": a, "to": b, "analyte": an, "factor": f}, {"value": x}, tol=1e-12)
for f in [0, -2, "abc", "<5"]:
    add("convert", {"value": 1, "from": "mU/L", "to": "mIU/L", "analyte": "tsh", "factor": f}, error="invalid_value")
add("convert", {"value": 1, "from": "mU/L", "to": "furlong", "factor": 1}, error="unknown_unit")
add("convert", {"value": 1, "from": "mU/L", "to": "mIU/L", "analyte": "tshh", "factor": 1}, error="unknown_analyte")
add("convert", {"value": 1, "from": "mU/L", "to": "mIU/L", "analyte": "tsh"}, error="no_sourced_conversion",
    note="without factor the default still refuses")

# ---------------------------------------------------------------------------
# 7. explain
# ---------------------------------------------------------------------------
add("explain", {"from": "mg/L", "to": "µg/mL"}, {"kind": "unit_arithmetic", "factor": 1.0, "derived": True,
                                                 "source_ids": []})
add("explain", {"from": "ug/L", "to": "ug/L"}, {"kind": "identity", "factor": 1.0, "derived": True, "source_ids": []})
add("explain", {"from": "mg/dL", "to": "mmol/L", "analyte": "glucose"},
    {"kind": "analyte_factor", "factor": float(F(10) / pubchem(5793)), "derived": False,
     "source_ids": ["pubchem-5793"]})
add("explain", {"from": "ng/mL", "to": "nmol/L", "analyte": "vitamin-d-25-oh"},
    {"kind": "analyte_factor", "factor": float(F(1000) / pubchem(5283731)), "derived": False,
     "source_ids": ["pubchem-5283731", "iom-2011-vitd"]})
add("explain", {"from": "mmol/L", "to": "mg/dL", "analyte": "calcium"},
    {"kind": "analyte_factor", "factor": float(ciaaw("Ca") / 10), "derived": False, "source_ids": ["ciaaw-Ca"]})
add("explain", {"from": "%", "to": "mmol/mol", "analyte": "hba1c"},
    {"kind": "equation", "factor": None, "derived": False, "source_ids": ["ngsp-ifcc", "hoelzel-2004"],
     "slope": float(1 / F("0.09148")), "intercept": float(-F("2.152") / F("0.09148"))})
add("explain", {"from": "IU/L", "to": "U/L", "analyte": "ast"},
    {"kind": "label_equivalence", "factor": 1.0, "derived": False, "source_ids": ["ramsay-tipton-2017"]})
add("explain", {"from": "U/L", "to": "µkat/L", "analyte": "alt"},
    {"kind": "analyte_factor", "factor": float(F(1, 60)), "derived": False,
     "source_ids": ["ucum-2.2", "ramsay-tipton-2017"]})
add("explain", {"from": "mg/dL", "to": "mmol/L", "analyte": "triglycerides"},
    {"kind": "analyte_factor", "factor": 0.01129, "derived": False, "source_ids": ["nhanes-trigly-l"]})
add("explain", {"from": "IU", "to": "µg", "analyte": "vitamin-d-dose"},
    {"kind": "analyte_factor", "factor": 0.025, "derived": False, "source_ids": ["iom-2011-vitd"]})
add("explain", {"from": "mg/dL", "to": "nmol/L", "analyte": "lipoprotein-a"}, error="forbidden")
add("explain", {"from": "ng/mL", "to": "nmol/L", "analyte": "vitamin-d-25-oh"},
    {"kind": "analyte_factor", "reference_cids": [5283731], "warnings_contain": ["25-hydroxyvitamin D3", "CID 5710148"]})
add("explain", {"from": "ng/mL", "to": "nmol/L", "analyte": "folate-rbc"},
    {"kind": "analyte_factor", "reference_cids": [135398658], "warnings_contain": ["folic acid", "5-methyltetrahydrofolate"]})
add("explain", {"from": "mg/dL", "to": "mmol/L", "analyte": "calcium"},
    {"kind": "analyte_factor", "reference_cids": [], "reference_elements": ["Ca"], "warning_count": 0})
for an in ["alt", "ck-total", "lp-pla2"]:
    add("explain", {"from": "U/L", "to": "µkat/L", "analyte": an},
        {"kind": "analyte_factor", "warnings_contain": ["changes the unit only", "temperatures"]})
add("explain", {"from": "U/L", "to": "kU/L", "analyte": "alt"}, {"kind": "unit_arithmetic", "warning_count": 0})
add("explain", {"from": "µIU/mL", "to": "pmol/L", "analyte": "insulin", "factor": 6},
    {"kind": "user_factor", "factor": 6.0, "derived": False, "source_ids": [], "user_factor_overrides": "forbidden",
     "warnings_contain": ["supplied by the caller", "Overrides lifefrom-units (forbidden)"]})
add("explain", {"from": "mU/L", "to": "mIU/L", "analyte": "tsh", "factor": 1},
    {"kind": "user_factor", "factor": 1.0, "user_factor_overrides": "no_sourced_conversion"})
add("explain", {"from": "mg/dL", "to": "mmol/L", "analyte": "glucose", "factor": 0.0555},
    {"kind": "user_factor", "factor": 0.0555, "user_factor_overrides": None, "user_factor_library_kind": "analyte_factor",
     "warnings_contain": ["The library factor is 0.0555062"]})

out = {"version": "1.0.0", "description": "Shared test vectors for the lifefrom-units Python and TypeScript packages. "
       "Expected values computed independently of the engine (scripts/make_vectors.py).",
       "ops": {"normalize": "normalize_unit(unit) -> unit", "same_unit": "same_unit(a, b, analyte?) -> same",
               "parse_value": "parse_value(value) -> value",
               "convert": "convert(value, from, to, analyte?) -> value within rel_tol (or abs_tol)",
               "roundtrip": "convert(convert(value, a, b), b, a) -> value within rel_tol",
               "explain": "explain(from, to, analyte?, factor?) -> kind, factor, derived, source ids, equation slope and "
                          "intercept, reference_cids / reference_elements, warnings_contain (substrings), "
                          "warning_count, user_factor_overrides, user_factor_library_kind",
               "parse_result": "parse_result(value) -> value, comparator, flag",
               "convert_result": "convert_result(value, from, to, analyte?, factor?) -> value (rel 1e-9), comparator, "
                                 "flag, unit"},
       "count": len(V), "vectors": V}
(ROOT / "tests" / "vectors.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
from collections import Counter  # noqa: E402
print(len(V), Counter(v["op"] for v in V), Counter(v.get("error") for v in V if v.get("error")))
