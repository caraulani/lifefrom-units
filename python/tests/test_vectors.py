"""Run the shared vectors in tests/vectors.json against the Python package."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import lifefrom_units as L

VECTORS = json.loads((Path(__file__).resolve().parents[2] / "tests" / "vectors.json").read_text(encoding="utf-8"))


def close(got, want, rel, abs_tol=None):
    if abs_tol is not None:
        return abs(got - want) <= abs_tol
    return math.isclose(got, want, rel_tol=rel, abs_tol=1e-300) or got == want


def run(v):
    i, op = v["input"], v["op"]
    if op == "normalize":
        return {"unit": L.normalize_unit(i["unit"], locale=i.get("locale"))}
    if op == "same_unit":
        return {"same": L.same_unit(i["a"], i["b"], i.get("analyte"), locale=i.get("locale"))}
    if op == "parse_value":
        return {"value": L.parse_value(i["value"])}
    if op == "convert":
        return {"value": L.convert(i["value"], i["from"], i["to"], i.get("analyte"), factor=i.get("factor"),
                                    locale=i.get("locale"))}
    if op == "parse_result":
        r = L.parse_result(i["value"])
        return {"value": r["value"], "comparator": r["comparator"], "flag": r["flag"]}
    if op == "convert_result":
        r = L.convert_result(i["value"], i["from"], i["to"], i.get("analyte"), factor=i.get("factor"),
                             locale=i.get("locale"))
        return {"value": r["value"], "comparator": r["comparator"], "flag": r["flag"], "unit": r["unit"]}
    if op == "roundtrip":
        x = L.convert(i["value"], i["a"], i["b"], i.get("analyte"))
        return {"value": L.convert(x, i["b"], i["a"], i.get("analyte"))}
    if op == "explain":
        e = L.explain(i["from"], i["to"], i.get("analyte"), factor=i.get("factor"), locale=i.get("locale"))
        out = {"kind": e["kind"], "factor": e["factor"], "derived": e["derived"],
               "source_ids": [s["id"] for s in e["sources"]],
               "reference_cids": [r["pubchem_cid"] for r in e["reference_compounds"] if "pubchem_cid" in r],
               "reference_elements": [r["element"] for r in e["reference_compounds"] if "element" in r],
               "warning_count": len(e["warnings"]), "warnings": e["warnings"],
               "user_factor_overrides": (e["user_factor"] or {}).get("overrides"),
               "user_factor_library_kind": (e["user_factor"] or {}).get("library_kind")}
        if e["equation"]:
            out["slope"] = e["equation"]["slope"]
            out["intercept"] = e["equation"]["intercept"]
        return out
    raise AssertionError(op)


@pytest.mark.parametrize("v", VECTORS["vectors"], ids=[v["id"] for v in VECTORS["vectors"]])
def test_vector(v):
    if "error" in v:
        with pytest.raises(L.LifeFromUnitsError) as ei:
            run(v)
        assert ei.value.code == v["error"], str(ei.value)
        return
    got = run(v)
    want = v["expect"]
    if v["op"] in ("convert", "roundtrip"):
        assert close(got["value"], want["value"], v["rel_tol"], v.get("abs_tol")), (got, want)
    elif v["op"] in ("parse_result", "convert_result"):
        tol = v.get("rel_tol", 1e-15)
        assert close(got["value"], want["value"], tol), (got, want)
        for k in want:
            if k != "value":
                assert got[k] == want[k], (k, got[k], want[k])
    elif v["op"] == "explain":
        for k, w in want.items():
            if k == "warnings_contain":
                for sub in w:
                    assert any(sub in x for x in got["warnings"]), (sub, got["warnings"])
            elif isinstance(w, float):
                assert math.isclose(got[k], w, rel_tol=1e-9), (k, got[k], w)
            else:
                assert got[k] == w, (k, got[k], w)
    elif v["op"] == "parse_value":
        assert math.isclose(got["value"], want["value"], rel_tol=1e-15, abs_tol=0) or got["value"] == want["value"]
    else:
        assert got == want


def test_vector_count():
    assert VECTORS["count"] == len(VECTORS["vectors"]) >= 300
