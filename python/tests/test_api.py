"""API behaviour beyond the shared vectors: error types, explain structure, CLI."""
from __future__ import annotations

import json

import pytest

import lifefrom_units as L
from lifefrom_units.cli import main


def test_error_hierarchy():
    for cls in (L.UnknownUnitError, L.UnknownAnalyteError, L.IncompatibleUnitsError, L.ForbiddenConversionError,
                L.NoSourcedConversionError, L.InvalidValueError, L.AmbiguousValueError, L.AmbiguousUnitError):
        assert issubclass(cls, L.LifeFromUnitsError)
        assert issubclass(cls, ValueError)


def test_forbidden_carries_reason_and_source():
    with pytest.raises(L.ForbiddenConversionError) as ei:
        L.convert(50, "mg/dL", "nmol/L", analyte="lipoprotein-a")
    d = ei.value.details
    assert d["rule"] == "lpa-mass-vs-molar"
    assert d["sources"][0]["doi"] == "10.1093/eurheartj/ehac361"


def test_explain_structure():
    e = L.explain("mmol/L", "mg/dL", analyte="glucose", value="5,4")
    assert e["kind"] == "analyte_factor" and not e["derived"]
    assert e["sources"][0]["pubchem_cid"] == 5793
    assert e["text"].startswith("1 mmol/L = 18.016")
    assert abs(e["result"] - 5.4 * 18.016) < 1e-9
    h = L.explain("%", "mmol/mol", analyte="hba1c")
    assert h["factor"] is None and h["equation"]["text"].startswith("mmol/mol = 10.9314")


def test_every_spelling_in_spec_resolves():
    for u in L.SPEC["units"]:
        for s in [u["unit"]] + u["aliases"] + u["case_sensitive_aliases"]:
            assert L.normalize_unit(s) == u["unit"], s


def test_every_analyte_bridge_has_sources():
    for a in L.SPEC["analytes"]:
        for b in a["bridges"]:
            assert b["sources"], (a["id"], b)
            for s in b["sources"]:
                src = L.SPEC["sources"][s]
                assert src["url"].startswith("https://") and src["accessed"] == "2026-11-25"


def test_unit_info_ucum():
    assert L.unit_info("x10E9/L")["ucum"] == "10*9/L"
    assert L.unit_info("mIU/mL")["ucum"] == "m[IU]/mL"


def test_cli(capsys):
    assert main(["convert", "5,4", "mmol/L", "mg/dL", "--analyte", "glucose"]) == 0
    assert capsys.readouterr().out.strip() == "97.2864"
    assert main(["normalize", "mcg/l", "K/uL"]) == 0
    assert capsys.readouterr().out.split() == ["µg/L", "10^3/µL"]
    assert main(["same", "µg/L", "ng/mL"]) == 0
    assert main(["same", "mg/dL", "mg/L"]) == 1
    capsys.readouterr()
    assert main(["convert", "50", "mg/dL", "nmol/L", "-a", "lipoprotein-a"]) == 2
    assert "forbidden" in capsys.readouterr().err
    assert main(["explain", "mg/dL", "mmol/L", "-a", "cholesterol", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "analyte_factor"


def test_cli_qualifiers_and_factor(capsys):
    assert main(["convert", "<5", "mg/dL", "mmol/L", "-a", "glucose"]) == 0
    assert capsys.readouterr().out.strip() == "<0.277531"
    assert main(["convert", "5,4 H", "mmol/L", "mg/dL", "-a", "glucose"]) == 0
    assert capsys.readouterr().out.strip() == "97.2864 H"
    assert main(["convert", "10", "µIU/mL", "pmol/L", "-a", "insulin", "--factor", "6"]) == 0
    io = capsys.readouterr()
    assert io.out.strip() == "60" and "not checked" in io.err


def test_factor_is_never_default():
    with pytest.raises(L.ForbiddenConversionError):
        L.convert(10, "µIU/mL", "pmol/L", analyte="insulin")
    e = L.explain("µIU/mL", "pmol/L", analyte="insulin", factor=6)
    assert e["user_factor"]["overrides"] == "forbidden" and e["sources"] == []


def test_amh_refused_with_reason():
    with pytest.raises(L.ForbiddenConversionError) as ei:
        L.convert(2, "ng/mL", "pmol/L", analyte="amh")
    assert "assay-independent" in ei.value.details["reason"]


# 'mil' is thousand in Spanish and million in English and Romanian: refused without a locale.
def test_spanish_wbc_mil_mm3_with_locale_es():
    assert L.convert("7,5", "mil/mm3", "10^3/µL", locale="es") == 7.5
    assert L.convert_result("7,5", "mil/mm3", "K/µL", locale="es-ES")["value"] == 7.5
    assert L.normalize_unit("mil/mm3", locale="es") == "10^3/mm³"


def test_mil_mm3_without_locale_is_refused():
    with pytest.raises(L.AmbiguousUnitError) as ei:
        L.convert(7.5, "mil/mm3", "10^3/µL")
    assert ei.value.code == "ambiguous_unit"
    assert ei.value.details["readings"] == {"es": "10^3/mm³", "en": "10^6/mm³", "ro": "10^6/mm³", "de": "10^6/mm³"}
    assert "thousand in Spanish" in str(ei.value)
    for u in ("Mil/mm3", "mil/µL", "Mil/uL", "mil./µL"):
        with pytest.raises(L.AmbiguousUnitError):
            L.normalize_unit(u)
    with pytest.raises(L.AmbiguousUnitError):
        L.same_unit("mil/mm3", "K/µL")
    with pytest.raises(L.AmbiguousUnitError):
        L.normalize_unit("mil/mm3", locale="it")


def test_us_mil_ul_rbc_with_locale_en():
    assert L.normalize_unit("Mil/µL", locale="en") == "10^6/µL"
    assert L.convert(4.5, "Mil/µL", "10^12/L", locale="en-US") == 4.5
    assert L.convert(4.5, "Mil/uL", "/µL", locale="en") == 4.5e6
    assert L.normalize_unit("mil./µL", locale="ro") == "10^6/µL"


def test_unambiguous_spellings_need_no_locale():
    for u, canon in [("mill/mm3", "10^6/mm³"), ("millones/mm3", "10^6/mm³"), ("Million/µL", "10^6/µL"),
                     ("mii/µL", "10^3/µL"), ("10^6/µL", "10^6/µL"), ("K/µL", "10^3/µL")]:
        assert L.normalize_unit(u) == canon
        assert L.normalize_unit(u, locale="es") == canon


def test_locale_reading_is_explained_with_sources():
    e = L.explain("mil/mm3", "10^9/L", locale="es")
    assert e["steps"][0]["kind"] == "spelling_reading"
    assert [s["id"] for s in e["sources"]] == ["eswiktionary-mil", "nih-cc-cbc-es"]
    with pytest.raises(L.InvalidValueError):
        L.normalize_unit("mg/dL", locale="12")


def test_cli_locale(capsys):
    assert main(["convert", "7,5", "mil/mm3", "K/uL", "--locale", "es"]) == 0
    assert capsys.readouterr().out.strip() == "7.5"
    assert main(["convert", "7,5", "mil/mm3", "K/uL"]) == 2
    assert "ambiguous_unit" in capsys.readouterr().err
    assert main(["normalize", "Mil/uL", "-l", "en"]) == 0
    assert capsys.readouterr().out.strip() == "10^6/µL"


# German, Austrian and Swiss reports (1.2.0).
def test_german_wbc_and_platelets():
    assert L.normalize_unit("G/l") == "10^9/L"
    assert L.normalize_unit("g/l") == "g/L"
    assert L.normalize_unit("Tsd./µl") == "10^3/µL"
    assert L.normalize_unit("Tsd/μl") == "10^3/µL"
    assert L.normalize_unit("Gpt/l") == "10^9/L"
    assert L.convert("6,2", "Tsd/µl", "x10^9/L") == pytest.approx(6.2, rel=1e-12)
    assert L.convert("6,2", "G/l", "Tsd./µl") == pytest.approx(6.2, rel=1e-12)
    assert L.convert("6,2", "G/l", "/nl") == pytest.approx(6.2, rel=1e-12)
    assert L.same_unit("Tsd./µl", "G/l") and not L.same_unit("G/l", "g/l")


def test_german_rbc():
    assert L.normalize_unit("Mio./µl") == "10^6/µL"
    assert L.normalize_unit("T/l") == "10^12/L"
    assert L.convert("4,8", "Mio/µl", "x10^12/L") == pytest.approx(4.8, rel=1e-12)
    assert L.convert("4,8", "T/l", "Mio./µl") == pytest.approx(4.8, rel=1e-12)
    assert L.normalize_unit("Mil./µl", locale="de-AT") == "10^6/µL"


def test_german_spellings_carry_sources():
    rec = next(u for u in L.SPEC["units"] if u["unit"] == "10^3/µL")
    entry = next(e for e in rec["spelling_sources"] if "Tsd./µL" in e["spellings"])
    assert "dewiktionary-tsd" in entry["sources"]
    for u in L.SPEC["units"]:
        for e in u.get("spelling_sources", []):
            for sp in e["spellings"]:
                assert L.normalize_unit(sp) == u["unit"], sp
            for sid in e["sources"]:
                assert sid in L.SPEC["sources"], sid
