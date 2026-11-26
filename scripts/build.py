"""Build data/units.json, web/lifefrom-units.json, data/*.csv and the package data copies.

Reads only raw files fetched by scripts/fetch_sources.sh plus scripts/spec.py and the
LifeFrom release-1 CSVs. Run with: python3 -I scripts/build.py  (no third-party packages).
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
import shutil
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = Path(os.environ.get("LABUNITS_RAW", ROOT.parent / "_raw"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "python" / "src" / "lifefrom_units"))

import spec  # noqa: E402
from _rules import compile_rules, unit_key  # noqa: E402
import ucum_validate  # noqa: E402

VERSION = "1.1.0"


def page_text(path: Path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def load_pubchem(cid: int) -> dict:
    p = json.loads((RAW / "pubchem" / f"cid_{cid}.json").read_text())["PropertyTable"]["Properties"][0]
    assert p["CID"] == cid
    return p


def load_ciaaw() -> dict:
    t = (RAW / "ciaaw" / "abridged.htm").read_text(encoding="utf-8", errors="replace")
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    out = {}
    for m in re.finditer(r"\n\s*(\d+)\s+([A-Z][a-z]?)\s+([a-z]+)\s+([0-9.]+)\s*±\s*([0-9.]+)", t):
        out[m.group(2)] = dict(z=int(m.group(1)), name=m.group(3), value=m.group(4), unc=m.group(5))
    return out


CIAAW = load_ciaaw()


def molar_mass(ref) -> tuple[F, str, dict]:
    kind, key = ref
    if kind == "pubchem":
        p = load_pubchem(key)
        sid = f"pubchem-{key}"
        title = p["Title"]
        if key == 5311498:
            title = "Cyanocobalamin (PubChem title: Anacobin)"
        src = dict(label=f"PubChem CID {key} ({title}), {p['MolecularFormula']}, molecular weight "
                         f"{p['MolecularWeight']} g/mol",
                   url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{key}",
                   api_url=f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{key}/property/"
                           "Title,MolecularFormula,MolecularWeight/JSON",
                   kind="molar_mass", pubchem_cid=key, title=title, formula=p["MolecularFormula"],
                   molar_mass=p["MolecularWeight"], accessed=spec.ACCESSED)
        return F(p["MolecularWeight"]), sid, src
    if kind == "ciaaw":
        e = CIAAW[key]
        sid = f"ciaaw-{key}"
        src = dict(label=f"CIAAW abridged standard atomic weight of {e['name']} ({key}): {e['value']} ± "
                         f"{e['unc']}", url="https://www.ciaaw.org/abridged-atomic-weights.htm",
                   kind="atomic_weight", element=key, molar_mass=e["value"], accessed=spec.ACCESSED)
        return F(e["value"]), sid, src
    raise ValueError(ref)


SOURCES: dict = {k: {"accessed": spec.ACCESSED, **v} for k, v in spec.SOURCES.items()}


def check_published(src_id: str, frm: str, to: str, factor: float) -> None:
    """Assert that the published factor really appears in the fetched page."""
    fname = {"nhanes-biopro-l": "BIOPRO_L", "nhanes-trigly-l": "TRIGLY_L", "nhanes-tchol-l": "TCHOL_L",
             "nhanes-glu-l": "GLU_L", "nhanes-tst-l": "TST_L", "nhanes-folate-l": "FOLATE_L",
             "nhanes-alb-cr-l": "ALB_CR_L"}[src_id]
    t = page_text(RAW / "nhanes-docs-labunits" / f"{fname}.htm")
    txt = repr(factor) if factor != int(factor) else str(factor)
    pats = {txt, f"{factor:.3f}", f"{factor:.1f}", f"{factor:g}"}
    if not any(re.search(r"(?:multiplying|dividing)[^.]{0,40}?by\s+" + re.escape(p) + r"(?![0-9])", t)
               for p in pats):
        raise SystemExit(f"published factor {factor} not found in {fname}")


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
UNITDEFS = spec.unit_defs()
UNIT = {u["unit"]: u for u in UNITDEFS}
assert len(UNIT) == len(UNITDEFS), "duplicate canonical unit"
RULES_JSON = [dict(pattern=p, replacement=r, note=n) for p, r, n in spec.NORMALIZATION_RULES]
RULES = compile_rules(RULES_JSON)


def key(s: str) -> str:
    return unit_key(s, RULES)


def build_lookup():
    exact, folded, folded_src = {}, {}, {}
    for u in UNITDEFS:
        names = [u["unit"]] + u["aliases"]
        for n in names + u["cs_aliases"]:
            k = key(n)
            if k in exact and exact[k] != u["unit"]:
                raise SystemExit(f"exact key collision {k!r}: {exact[k]} vs {u['unit']}")
            exact[k] = u["unit"]
        for n in names:
            k = key(n.lower())
            if k in folded and folded[k] != u["unit"]:
                raise SystemExit(f"case-insensitive collision {k!r}: {folded[k]} ({folded_src[k]}) vs "
                                 f"{u['unit']} ({n})")
            folded[k] = u["unit"]
            folded_src[k] = n
    return exact, folded


def build_ambiguous(exact, folded):
    """Spellings refused without a locale. Keyed like lookup.casefold (rules on the lower-cased input)."""
    keys, entries = {}, []
    for a in spec.AMBIGUOUS:
        for lang, unit in a["readings"].items():
            if unit not in UNIT:
                raise SystemExit(f"{a['id']}: reading {lang} -> {unit} is not a canonical unit")
            if lang not in spec.LANGUAGE_READINGS:
                raise SystemExit(f"{a['id']}: no LANGUAGE_READINGS entry for {lang}")
        for sp in a["spellings"]:
            k = key(sp.lower())
            if k in folded or k in exact or k.lower() in exact:
                raise SystemExit(f"ambiguous spelling {sp!r} also resolves as a unit")
            if k in keys and keys[k] != a["id"]:
                raise SystemExit(f"ambiguous spelling {sp!r} in two entries")
            keys[k] = a["id"]
        entries.append(dict(id=a["id"], spellings=a["spellings"], readings=a["readings"],
                            reason=spec.AMBIGUOUS_REASON))
    # no case-sensitive alias may fold onto an ambiguous key
    for u in UNITDEFS:
        for n in [u["unit"]] + u["aliases"] + u["cs_aliases"]:
            if key(n.lower()) in keys:
                raise SystemExit(f"{n!r} ({u['unit']}) folds onto an ambiguous spelling")
    return keys, entries


def scale_float(u) -> float:
    return float(u["scale"])


# ---------------------------------------------------------------------------
# Analytes and bridges
# ---------------------------------------------------------------------------
def bridge(frm, to, a, b, kind, description, basis, sources, display=None):
    return dict(**{"from": frm, "to": to}, a=float(a), b=float(b), kind=kind, description=description,
                basis=basis, sources=sources, display=display)


def published_a(frm: str, to: str, f: F) -> F:
    # value_to = f * value_from  ->  base_to = f * base_from * s_to / s_from
    return f * UNIT[to]["scale"] / UNIT[frm]["scale"]


def build_analytes(markers: set):
    out = []
    crosschecks = []
    for a in spec.ANALYTES:
        bridges = []
        mm = None
        mm_src = None
        caveat_sources = []
        for m in a["markers"]:
            if m not in markers:
                raise SystemExit(f"{a['id']}: marker {m} not in markers.csv")
        if "mm" in a:
            mm, sid, src = molar_mass(a["mm"])
            SOURCES[sid] = src
            mm_src = sid
            mms = src["molar_mass"]
            srcs = [sid] + a.get("extra_sources", [])
            refc = dict(name=(src["title"] if a["mm"][0] == "pubchem" else CIAAW[a["mm"][1]]["name"]),
                        molar_mass=float(mm), molar_mass_text=mms, unit="g/mol", source=sid)
            if a["mm"][0] == "pubchem":
                refc["pubchem_cid"] = a["mm"][1]
                refc["formula"] = src["formula"]
            else:
                refc["element"] = a["mm"][1]
            if "alt_compound" in a:
                _, asid, asrc = molar_mass(a["alt_compound"])
                SOURCES[asid] = asrc
                caveat_sources.append(asid)
            bridges.append(bridge("mass_concentration", "substance_concentration", 1 / mm, 0, "molar_mass",
                                  f"mass = amount × molar mass of {a['name'].split(' (')[0]} "
                                  f"({mms} g/mol)", f"molar mass {mms} g/mol", srcs))
            bridges[-1]["reference_compound"] = refc
            bridges.append(bridge("mass_rate", "substance_rate", 1 / mm, 0, "molar_mass",
                                  f"mass = amount × molar mass ({mms} g/mol)", f"molar mass {mms} g/mol", srcs))
            bridges[-1]["reference_compound"] = refc
        if "bun" in a:
            mm, sid, src = molar_mass(a["bun"])
            SOURCES[sid] = src
            mm_src = sid
            bridges.append(bridge("mass_concentration", "substance_concentration", 1 / mm, 0, "urea_nitrogen",
                                  f"mass of urea nitrogen / molar mass of N2 ({src['molar_mass']} g/mol) = amount of urea",
                                  "urea (CH4N2O) holds 2 N per molecule; molar mass of N2", [sid]))
        if "published" in a:
            sid, frm, to, f = a["published"]
            check_published(sid, frm, to, f)
            bridges.append(bridge("mass_concentration", "substance_concentration", published_a(frm, to, F(str(f))),
                                  0, "published_factor", f"published factor: {frm} × {f} = {to}",
                                  f"published factor {f}", [sid]))
            if "mm_check" in a:
                mmc, sidc, srcc = molar_mass(a["mm_check"])
                SOURCES[sidc] = srcc
        if a.get("charge"):
            z = a["charge"]
            bridges.append(bridge("substance_concentration", "equivalent_concentration", z, 0, "charge",
                                  f"multiply amount by the ion charge |z| = {z}",
                                  f"derived: unit arithmetic with ion charge {z} (1 Eq = 1 mol of charge / |z|)",
                                  ["ucum-2.2"]))
        if a.get("enzyme"):
            bridges.append(bridge("unit_concentration", "catalytic_concentration", F(1, 10**6) / 60, 0,
                                  "enzyme_unit", "1 U = 1 µmol/min = 1/60 µkat",
                                  "derived: unit arithmetic from the UCUM definitions U = umol/min, kat = mol/s",
                                  ["ucum-2.2", "ramsay-tipton-2017"]))
            bridges.append(bridge("iu_concentration", "unit_concentration", 1, 0, "label_equivalence",
                                  "for enzyme activity, 'IU' is another name for the enzyme unit U",
                                  "label equivalence for enzyme activity", ["ramsay-tipton-2017"]))
        if "creat_denominator" in a:
            mm, sid, src = molar_mass(a["creat_denominator"])
            SOURCES[sid] = src
            bridges.append(bridge("mass_fraction", "mass_per_substance", mm, 0, "creatinine_denominator",
                                  f"per gram of creatinine -> per mole of creatinine (× {src['molar_mass']} g/mol)",
                                  f"creatinine molar mass {src['molar_mass']} g/mol in the denominator", [sid]))
        if a.get("hba1c"):
            t = page_text(RAW / "ngsp" / "ifccngsp.html")
            m = re.search(r"NGSP = \(([0-9.]+)\*IFCC\) \+ ([0-9.]+)", t)
            if not m:
                raise SystemExit("NGSP master equation not found")
            slope, icpt = F(m.group(1)), F(m.group(2))
            # base: IFCC mol/mol x -> NGSP fraction f = (slope*1000*x + icpt)/100
            bridges.append(bridge("substance_fraction", "fraction", slope * 1000 / 100, icpt / 100, "equation",
                                  f"IFCC-NGSP master equation: NGSP % = {m.group(1)} × IFCC mmol/mol + {m.group(2)}",
                                  "IFCC-NGSP master equation", ["ngsp-ifcc", "hoelzel-2004"],
                                  display=dict(to="%", frm="mmol/mol", slope=m.group(1), intercept=m.group(2))))
        if a.get("vitd_dose"):
            bridges.append(bridge("mass", "iu_amount", 40 * 10**6, 0, "dose_equivalence",
                                  "1 µg of vitamin D (cholecalciferol) = 40 IU",
                                  "IU of vitamin D defined as the activity of 0.025 µg cholecalciferol",
                                  ["iom-2011-vitd"]))
        for sid, frm, to, f in a.get("crosscheck", []):
            check_published(sid, frm, to, f)
            crosschecks.append((a["id"], sid, frm, to, f))
        out.append(dict(id=a["id"], name=a["name"], marker_slugs=a["markers"],
                        molar_mass=(dict(value=float(mm), unit="g/mol", source=mm_src) if mm is not None
                                    and mm_src else None),
                        charge=a.get("charge"), bridges=bridges, note=a.get("note"),
                        caveats=a.get("caveats", []), caveat_sources=caveat_sources))
    return out, crosschecks


def build_forbidden():
    out = []
    for f in spec.FORBIDDEN:
        out.append(dict(id=f["id"], analyte=f["analyte"], a=f["a"], b=f["b"], a_units=f.get("a_units"),
                        b_units=f.get("b_units"), example=list(f["example"]), reason=f["reason"],
                        sources=f["sources"]))
    return out


# ---------------------------------------------------------------------------
def main():
    r1 = RAW / "lifefrom-release-1"
    markers = {r["marker_slug"]: r for r in csv.DictReader(open(r1 / "markers.csv", encoding="utf-8"))}
    units_rows = list(csv.DictReader(open(r1 / "units.csv", encoding="utf-8")))

    exact, folded = build_lookup()
    ambiguous_keys, ambiguous = build_ambiguous(exact, folded)
    analytes_list, crosschecks = build_analytes(set(markers))
    forbidden = build_forbidden()

    # analyte index: ids, marker slugs (every release-1 marker is a known analyte key)
    index = {}
    for a in analytes_list:
        index[a["id"]] = a["id"]
    for a in analytes_list:
        for m in a["marker_slugs"]:
            if m in index and index[m] != a["id"]:
                raise SystemExit(f"marker {m} in two analytes")
            index[m] = a["id"]
    for m, row in markers.items():
        if m not in index:
            analytes_list.append(dict(id=m, name=row["canonical_name"], marker_slugs=[m], molar_mass=None,
                                      charge=None, bridges=[], note=None, caveats=[], caveat_sources=[]))
            index[m] = m

    # UCUM validation of every code we ship
    essence = ucum_validate.load_essence(RAW / "ucum" / "ucum-essence.xml")
    bad = []
    for u in UNITDEFS:
        if u["ucum"]:
            ok, why = ucum_validate.validate(u["ucum"], essence)
            if not ok:
                bad.append((u["unit"], u["ucum"], why))
    if bad:
        raise SystemExit(f"invalid UCUM codes: {bad}")

    dims = {k: dict(name=v[0], base=v[1], convertible=v[2]) for k, v in spec.DIMENSIONS.items()}
    for u in UNITDEFS:
        if u["dimension"].startswith("arbitrary:"):
            dims[u["dimension"]] = dict(name=f"arbitrary unit: {u['note']}", base=u["unit"], convertible=False)

    used_sources = set()
    for a in analytes_list:
        for b in a["bridges"]:
            used_sources.update(b["sources"])
    for f in forbidden:
        used_sources.update(f["sources"])
    used_sources.add("ucum-2.2")
    for r in spec.LANGUAGE_READINGS.values():
        used_sources.update(r["sources"])
    for _, sid, *_ in crosschecks:
        used_sources.add(sid)
    for a in analytes_list:
        if a.get("molar_mass"):
            used_sources.add(a["molar_mass"]["source"])
        used_sources.update(a.get("caveat_sources", []))
    if "pubchem-5497163" in SOURCES:
        used_sources.add("pubchem-5497163")

    spec_json = dict(
        name="lifefrom-units", version=VERSION, schema_version=1, released="2026-11-26",
        license="CC-BY-4.0 (data), MIT (code)",
        homepage="https://lifefrom.ai",
        notice="Not a medical device. Converts units only; it does not interpret results.",
        ucum_notice=("UCUM code strings are expressions in the Unified Code for Units of Measure, Copyright "
                     "1999-2024 Regenstrief Institute, Inc., used under the UCUM License "
                     "(https://ucum.org/license). This mapping from lab spellings to UCUM codes is not part of UCUM "
                     "and is not a units standard."),
        normalization=dict(rules=RULES_JSON,
                           procedure="key = rules applied in order to the trimmed input, then all whitespace removed. "
                                     "Look up key in lookup.exact; if absent, apply the same to the lower-cased "
                                     "input and look up in lookup.ambiguous, then in lookup.casefold. A spelling "
                                     "found in lookup.ambiguous resolves only with a locale whose primary language "
                                     "subtag (lower-cased, e.g. 'es' from 'es-AR') is in that entry's readings; "
                                     "otherwise it is refused (ambiguous_unit)."),
        dimensions=dims,
        units=[dict(unit=u["unit"], dimension=u["dimension"], scale=scale_float(u), aliases=u["aliases"],
                    case_sensitive_aliases=u["cs_aliases"], ucum=u["ucum"], note=u["note"]) for u in UNITDEFS],
        lookup=dict(exact=dict(sorted(exact.items())), casefold=dict(sorted(folded.items())),
                    ambiguous=dict(sorted(ambiguous_keys.items())), analytes=dict(sorted(index.items()))),
        ambiguous=ambiguous,
        language_readings=spec.LANGUAGE_READINGS,
        analytes=analytes_list,
        forbidden=forbidden,
        arbitrary_reason=spec.ARBITRARY_REASON,
        sources={k: SOURCES[k] for k in sorted(used_sources)},
    )
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    txt = json.dumps(spec_json, ensure_ascii=False, indent=1) + "\n"
    (data_dir / "units.json").write_text(txt, encoding="utf-8")
    shutil.copyfile(data_dir / "units.json", ROOT / "python" / "src" / "lifefrom_units" / "units.json")
    (ROOT / "ts" / "src" / "data.ts").write_text(
        "// Generated by scripts/build.py from data/units.json. Do not edit.\n"
        "import type { Spec } from './types.js';\n"
        f"export const SPEC: Spec = {json.dumps(spec_json, ensure_ascii=False)} as unknown as Spec;\n",
        encoding="utf-8")

    # Now use the runtime itself for derived outputs.
    sys.path.insert(0, str(ROOT / "python" / "src"))
    for m in list(sys.modules):
        if m == "lifefrom_units" or m.startswith("lifefrom_units."):
            del sys.modules[m]
    import lifefrom_units as L

    write_factor_table(L, analytes_list, crosschecks)
    write_release1_comparison(L, units_rows, markers)
    write_web(L, analytes_list, units_rows, forbidden, ambiguous)
    print(f"units: {len(UNITDEFS)}  spellings(exact keys): {len(exact)}  analytes with bridges: "
          f"{sum(1 for a in analytes_list if a['bridges'])}  forbidden rules: {len(forbidden)}  sources: "
          f"{len(spec_json['sources'])}")


def write_factor_table(L, analytes_list, crosschecks):
    """data/analyte_factors.csv: one row per analyte bridge in conventional units + cross-checks."""
    conv = {"molar_mass": None, "urea_nitrogen": ("mg/dL", "mmol/L")}
    rows = []
    for a in analytes_list:
        for b in a["bridges"]:
            if b["kind"] in ("molar_mass", "urea_nitrogen", "published_factor"):
                if b["from"] != "mass_concentration":
                    continue
                pairs = [("mg/dL", "mmol/L")]
                for _, sid, frm, to, f in [c for c in crosschecks if c[0] == a["id"]]:
                    pairs.append((frm, to))
            elif b["kind"] == "charge":
                pairs = [("mmol/L", "mEq/L")]
            elif b["kind"] == "enzyme_unit":
                pairs = [("U/L", "µkat/L")]
            elif b["kind"] == "label_equivalence":
                pairs = [("IU/L", "U/L")]
            elif b["kind"] == "creatinine_denominator":
                pairs = [("mg/g", "mg/mmol")]
            elif b["kind"] == "equation":
                pairs = [("mmol/mol", "%")]
            elif b["kind"] == "dose_equivalence":
                pairs = [("µg", "IU")]
            else:
                pairs = []
            for frm, to in dict.fromkeys(pairs):
                e = L.explain(frm, to, analyte=a["id"])
                pub = [c for c in crosschecks if c[0] == a["id"] and c[2] == frm and c[3] == to]
                src = [s for s in e["sources"]]
                rows.append(dict(
                    analyte=a["id"], marker_slugs=" | ".join(a["marker_slugs"]), from_unit=frm, to_unit=to,
                    kind=e["kind"], factor=("" if e["factor"] is None else f"{e['factor']:.6g}"),
                    equation=(e["equation"]["text"] if e["equation"] else ""),
                    basis=b["basis"],
                    molar_mass_g_per_mol=(a["molar_mass"]["value"] if a.get("molar_mass") else ""),
                    source_ids=" | ".join(s["id"] for s in src),
                    source_urls=" | ".join(s["url"] for s in src),
                    published_crosscheck=(" | ".join(f"{c[4]} ({c[1]})" for c in pub)),
                    crosscheck_rel_diff=(" | ".join(f"{(e['factor'] - c[4]) / c[4]:+.4%}" for c in pub))))
    with open(ROOT / "data" / "analyte_factors.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_release1_comparison(L, units_rows, markers):
    pref = {r["marker_slug"]: r["unit"] for r in units_rows if r["is_preferred"] == "yes"}
    out = []
    unknown = []
    for r in units_rows:
        forms = [r["unit"]] + [x.strip() for x in r["equivalent_forms"].split("|") if x.strip()]
        for f in forms:
            try:
                L.normalize_unit(f)
            except L.LifeFromUnitsError:
                unknown.append((r["marker_slug"], f))
        if r["is_preferred"] == "yes":
            continue
        slug, unit, p = r["marker_slug"], r["unit"], pref.get(r["marker_slug"])
        r1 = r["factor_to_preferred"]
        try:
            e = L.explain(unit, p, analyte=slug)
            ours = e["factor"]
            status = e["kind"]
            eq = e["equation"]["text"] if e["equation"] else ""
        except L.LifeFromUnitsError as ex:
            ours, status, eq = None, ex.code, ""
        rel = ""
        flag = ""
        if r1 and ours is not None:
            relv = (ours - float(r1)) / float(r1)
            rel = f"{relv:+.5%}"
            if abs(relv) > 1e-6:
                flag = "differs" if abs(relv) < 1e-3 else "differs>0.1%"
        elif r1 and ours is None:
            flag = "release-1 converts, lifefrom-units does not"
        elif not r1 and ours is not None:
            flag = "new in lifefrom-units"
        elif r["factor_basis"].startswith("LifeFrom reader formula") and eq:
            flag = "equation"
        out.append(dict(marker_slug=slug, unit=unit, preferred_unit=p, release1_factor=r1,
                        release1_basis=r["factor_basis"], lifefrom_units_factor=("" if ours is None else f"{ours:.8g}"),
                        lifefrom_units_equation=eq, lifefrom_units_status=status, rel_diff=rel, flag=flag,
                        release1_note=r["note"]))
    with open(ROOT / "data" / "release1_comparison.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    with open(ROOT / "data" / "release1_unknown_units.txt", "w", encoding="utf-8") as fh:
        for s, f in unknown:
            fh.write(f"{s}\t{f}\n")
    if unknown:
        print(f"WARNING: {len(unknown)} release-1 unit spellings not recognised (see data/release1_unknown_units.txt)")


def web_spellings(u):
    s = [u["unit"]] + u["aliases"] + u["cs_aliases"]
    extra = []
    for x in s:
        if "µ" in x:
            extra.append(x.replace("µ", "u"))
            if "µg" in x:
                extra.append(x.replace("µg", "mcg"))
    return list(dict.fromkeys(s + extra))


def write_web(L, analytes_list, units_rows, forbidden, ambiguous):
    units = []
    for u in UNITDEFS:
        for sp in web_spellings(u):
            assert L.normalize_unit(sp) == u["unit"], (sp, u["unit"])
            units.append(dict(unit=sp, normalized=u["unit"], dimension=u["dimension"]))
    by_marker = {}
    for r in units_rows:
        by_marker.setdefault(r["marker_slug"], []).append(r)
    an_out = []
    for a in analytes_list:
        if not a["bridges"]:
            continue
        slugs = a["marker_slugs"] or [a["id"]]
        for slug in slugs:
            rows = by_marker.get(slug, [])
            us = [r["unit"] for r in rows]
            if not us:
                us = {"vitamin-d-dose": ["µg", "IU"]}.get(a["id"], [])
            convs = []
            for i, x in enumerate(us):
                for y in us[i + 1:]:
                    for frm, to in ((x, y), (y, x)):
                        try:
                            e = L.explain(frm, to, analyte=slug if slug in L.core._ANALYTE_INDEX else a["id"])
                        except L.LifeFromUnitsError:
                            continue
                        if e["kind"] == "identity":
                            continue
                        c = {"from": e["from_unit"], "to": e["to_unit"]}
                        if e["factor"] is not None:
                            c["factor"] = e["factor"]
                        else:
                            c["equation"] = {"slope": e["equation"]["slope"], "intercept": e["equation"]["intercept"],
                                             "text": e["equation"]["text"]}
                        srcs = e["sources"]
                        c["source_label"] = "; ".join(s["label"] for s in srcs) if srcs else "derived: unit arithmetic"
                        c["source_url"] = srcs[0]["url"] if srcs else None
                        if e["reference_compounds"]:
                            rc = e["reference_compounds"][0]
                            c["reference_compound"] = rc["name"] + (f" (PubChem CID {rc['pubchem_cid']})"
                                                                    if rc.get("pubchem_cid") else "")
                        if e["warnings"]:
                            c["warnings"] = e["warnings"]
                        convs.append(c)
            if convs:
                an_out.append(dict(slug=slug, analyte=a["id"], name=a["name"], conversions=convs))
    fb = []
    for f in forbidden:
        if f["analyte"] is None:
            fb.append(dict(slug=None, a=f["example"][0], b=f["example"][1], reason=f["reason"]))
            continue
        a = next(x for x in analytes_list if x["id"] == f["analyte"])
        for slug in a["marker_slugs"] or [a["id"]]:
            fb.append(dict(slug=slug, a=f["example"][0], b=f["example"][1], reason=f["reason"]))
    amb = []
    for a in ambiguous:
        for sp in a["spellings"]:
            amb.append(dict(unit=sp, readings=a["readings"], reason=a["reason"]))
            if "µ" in sp:
                amb.append(dict(unit=sp.replace("µ", "u"), readings=a["readings"], reason=a["reason"]))
    for x in amb:
        try:
            L.normalize_unit(x["unit"])
            raise SystemExit(f"{x['unit']} resolves without a locale")
        except L.AmbiguousUnitError:
            pass
        for lang, u in x["readings"].items():
            assert L.normalize_unit(x["unit"], locale=lang) == u, (x, lang)
    web = dict(name="lifefrom-units", version=VERSION, units=units, analytes=an_out, forbidden=fb, ambiguous=amb)
    (ROOT / "web").mkdir(exist_ok=True)
    (ROOT / "web" / "lifefrom-units.json").write_text(json.dumps(web, ensure_ascii=False, separators=(",", ":")) + "\n",
                                               encoding="utf-8")
    print(f"web: {len(units)} spellings, {len(an_out)} marker entries, {len(fb)} forbidden entries")


if __name__ == "__main__":
    main()
