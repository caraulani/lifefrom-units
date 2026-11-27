"""Hand-curated specification for lifefrom-units.

Everything numeric that is not pure unit arithmetic is resolved at build time from a raw
source file fetched by scripts/fetch_sources.sh (PubChem, CIAAW, NHANES, NGSP). This file
holds only identifiers (CIDs, element symbols), unit definitions, and text.

Access date for all sources: 2026-11-25.
"""
from __future__ import annotations

from fractions import Fraction as F

ACCESSED = "2026-11-25"

# ---------------------------------------------------------------------------
# Dimensions. "base" is the unit whose scale is 1. convertible=False marks
# assay-specific (arbitrary) or descriptive units: only identity is allowed.
# ---------------------------------------------------------------------------
DIMENSIONS = {
    "mass_concentration": ("mass concentration", "g/L", True),
    "substance_concentration": ("amount-of-substance concentration", "mol/L", True),
    "equivalent_concentration": ("charge-equivalent concentration", "Eq/L", True),
    "osmolality": ("osmolality", "Osm/kg", True),
    "osmolarity": ("osmolarity", "Osm/L", True),
    "catalytic_concentration": ("catalytic activity concentration (SI, katal)", "kat/L", True),
    "unit_concentration": ("'U' per volume (enzyme unit or assay unit, depends on the analyte)", "U/L", True),
    "iu_concentration": ("international units per volume (analyte-specific WHO standard)", "IU/L", True),
    "iu_amount": ("international units (dose)", "IU", True),
    "number_concentration": ("number concentration (cells or particles per volume)", "/L", True),
    "fraction": ("fraction (dimensionless, of 1)", "fraction", True),
    "substance_fraction": ("amount-of-substance fraction", "mol/mol", True),
    "mass_fraction": ("mass fraction (mass content)", "g/g", True),
    "mass_per_substance": ("mass per amount of substance", "g/mol", True),
    "mass_rate": ("mass per time (e.g. 24-hour urine)", "g/s", True),
    "substance_rate": ("amount of substance per time", "mol/s", True),
    "mass_concentration_rate": ("mass concentration generated per time (plasma renin activity)", "g/L/s", True),
    "time": ("time", "s", True),
    "length_rate": ("length per time (sedimentation rate)", "m/s", True),
    "volume": ("volume (cell volume)", "L", True),
    "mass": ("mass", "g", True),
    "volume_rate_bsa": ("volume per time per 1.73 m² body surface area", "mL/min/1.73m²", True),
    "mass_concentration_feu": ("mass concentration in fibrinogen-equivalent units (D-dimer)", "g/L FEU", True),
    "mass_concentration_ddu": ("mass concentration in D-dimer units", "g/L DDU", True),
}

# Arbitrary or descriptive units: each is its own non-convertible dimension.
ARBITRARY = [
    # (canonical, aliases, case_sensitive_aliases, ucum or None, note)
    ("S/CO", ["s/co", "S/C.O.", "signal/cutoff"], [], None, "signal-to-cut-off ratio of one assay"),
    ("index", ["Index"], [], None, "assay index value"),
    ("AI", ["antibody index"], [], None, "antibody index of one assay"),
    ("EU", ["ELISA units"], [], None, "ELISA units of one assay"),
    ("CU", ["chemiluminescent units"], [], None, "chemiluminescent units of one assay"),
    ("AU/mL", ["arb. U/mL", "arbitrary units/mL"], [], "[arb'U]/mL", "arbitrary units per mL"),
    ("titer", ["titre", "Titer", "Titre"], [], None, "dilution titer"),
    ("ratio", ["Ratio"], [], None, "a ratio of two results, unit not stated"),
    ("qualitative", [], [], None, "qualitative result"),
    ("semiquantitative", ["semi-quantitative"], [], None, "dipstick grade"),
    ("descriptive", [], [], None, "descriptive result"),
    ("calculated", [], [], None, "calculated index"),
    ("pH", ["pH units", "pH unit"], [], "[pH]", "pH"),
    ("/hpf", ["/HPF", "per hpf", "/hpf field"], [], "/[HPF]", "per high-power field"),
    ("/lpf", ["/LPF", "per lpf"], [], "/[LPF]", "per low-power field"),
    ("EU/dL", ["Ehrlich units/dL", "Ehrlich U/dL"], [], None, "Ehrlich units (urobilinogen)"),
    ("/100 WBC", ["/100WBC", "per 100 WBC", "/100 leukocytes"], [], None, "count per 100 white cells"),
    ("(ng/dL)/(ng/mL/h)", ["ng/dL per ng/mL/h"], [], None, "aldosterone-renin ratio unit"),
]

PREFIX = {"": F(1), "k": F(1000), "d": F(1, 10), "c": F(1, 100), "m": F(1, 1000),
          "µ": F(1, 10**6), "n": F(1, 10**9), "p": F(1, 10**12), "f": F(1, 10**15)}
VOL = {"L": F(1), "dL": F(1, 10), "mL": F(1, 1000), "µL": F(1, 10**6)}


def _u(pfx: str, atom: str) -> str:
    return pfx + atom


def unit_defs():
    """Return list of dicts: unit, dimension, scale (Fraction), aliases, cs_aliases, ucum."""
    out = []

    def add(unit, dim, scale, aliases=(), cs=(), ucum=None, note=None):
        out.append(dict(unit=unit, dimension=dim, scale=F(scale), aliases=list(aliases),
                        cs_aliases=list(cs), ucum=ucum, note=note))

    def ucum_of(s: str) -> str:
        return s.replace("µ", "u")

    # mass concentration
    for m in ["g", "mg", "µg", "ng", "pg"]:
        for v in ["L", "dL", "mL"]:
            u = f"{m}/{v}"
            al = []
            if u == "mg/dL":
                al = ["mg%", "mg/100mL", "mg/100 mL", "mg per dL"]
            if u == "g/dL":
                al = ["g%", "g/100mL", "g/100 mL"]
            if u == "µg/dL":
                al = ["µg%", "µg/100mL"]
            add(u, "mass_concentration", PREFIX[m[:-1]] / VOL[v], al, ucum=ucum_of(u))
    # substance concentration
    for p in ["", "m", "µ", "n", "p", "f"]:
        for v in ["L", "dL", "mL"]:
            u = f"{p}mol/{v}"
            cs = [f"{p}M"] if v == "L" and p else []
            add(u, "substance_concentration", PREFIX[p] / VOL[v], [], cs, ucum=ucum_of(u))
    # charge equivalents
    for p in ["", "m", "µ"]:
        u = f"{p}Eq/L"
        add(u, "equivalent_concentration", PREFIX[p], [f"{p}eq/L"], ucum=ucum_of(f"{p}eq/L"))
    # osmolality / osmolarity
    add("mOsm/kg", "osmolality", F(1, 1000),
        ["mOsm/kg H2O", "mOsm/kgH2O", "mosmol/kg", "mOsmol/kg", "mOsm/kg water"], ucum="mosm/kg")
    add("mOsm/L", "osmolarity", F(1, 1000), ["mosmol/L", "mOsmol/L"], ucum="mosm/L")
    # catalytic (katal) and enzyme rate expressed in mol/time
    add("kat/L", "catalytic_concentration", 1, ucum="kat/L")
    add("µkat/L", "catalytic_concentration", F(1, 10**6), ucum="ukat/L")
    add("nkat/L", "catalytic_concentration", F(1, 10**9), ucum="nkat/L")
    add("nmol/min/mL", "catalytic_concentration", F(1, 10**9) / 60 / F(1, 1000),
        ["nmol/mL/min", "nmol/min/ml"], ucum="nmol/min/mL")
    add("µmol/min/L", "catalytic_concentration", F(1, 10**6) / 60, ["µmol/L/min"], ucum="umol/min/L")
    # U per volume
    for p in ["", "m", "µ", "k"]:
        for v in ["L", "mL", "dL"]:
            u = f"{p}U/{v}"
            add(u, "unit_concentration", PREFIX[p] / VOL[v], ucum=ucum_of(u))
    # IU per volume
    for p in ["", "m", "µ", "k", "p"]:
        for v in ["L", "mL", "dL"]:
            u = f"{p}IU/{v}"
            add(u, "iu_concentration", PREFIX[p] / VOL[v], ucum=ucum_of(f"{p}[IU]/{v}"))
    add("IU", "iu_amount", 1, ["I.U.", "international units"], ucum="[IU]")
    # number concentration
    add("/L", "number_concentration", 1, ["per L", "cells/L"], ucum="/L")
    add("/mL", "number_concentration", 1000, ["cells/mL", "per mL"], ucum="/mL")
    add("/µL", "number_concentration", 10**6, ["cells/µL", "per µL", "cells/uL", "pro µL"], ucum="/uL")
    add("/mm³", "number_concentration", 10**6, ["/mm3", "/cmm", "cells/mm3", "cells/mm³", "/cu mm", "/mm^3"],
        ucum="/mm3")
    add("/nL", "number_concentration", 10**9, ["cells/nL", "per nL", "pro nL"], ucum="/nL")
    add("/pL", "number_concentration", 10**12, ["cells/pL"], ucum="/pL")
    # "mil/µL" and "mil/mm3" are NOT aliases: they are in AMBIGUOUS below (thousand in Spanish, million in English).
    add("10^3/µL", "number_concentration", 10**9,
        ["K/µL", "Thousand/µL", "Thou/µL", "x1000/µL", "1000/µL", "10^3 cells/µL", "10^3/µl", "K/uL",
         "mii/µL", "miles/µL", "Tsd/µL", "Tsd./µL", "Tausend/µL"],
        ["K/μL"], ucum="10*3/uL")
    add("10^3/mm³", "number_concentration", 10**9,
        ["K/mm³", "K/mm3", "10^3/mm3", "10^3/cmm", "Thou/mm3", "Thousand/mm3", "mii/mm3", "mii/mm³", "miles/mm3",
         "miles/mm³"], ucum="10*3/mm3")
    add("10^6/µL", "number_concentration", 10**12,
        ["Million/µL", "mill/µL", "mill./µL", "millones/µL", "10^6 cells/µL", "Mio/µL", "Mio./µL", "Millionen/µL"],
        ["M/µL", "M/uL"], ucum="10*6/uL")
    add("10^6/mm³", "number_concentration", 10**12,
        ["10^6/mm3", "Million/mm3", "mill/mm3", "mill/mm³", "mill./mm3", "millones/mm3", "millones/mm³"],
        ucum="10*6/mm3")
    add("10^3/L", "number_concentration", 10**3, [], ucum="10*3/L")
    add("10^6/L", "number_concentration", 10**6, [], ucum="10*6/L")
    add("10^9/L", "number_concentration", 10**9, ["10^9 cells/L", "Giga/L"], ["G/L", "Gpt/L", "G/l", "Gpt/l"],
        ucum="10*9/L")
    add("10^12/L", "number_concentration", 10**12, ["10^12 cells/L", "Tera/L"], ["T/L", "Tpt/L", "T/l", "Tpt/l"],
        ucum="10*12/L")
    add("10^3/mL", "number_concentration", 10**6, [], ucum="10*3/mL")
    add("10^6/mL", "number_concentration", 10**9, [], ucum="10*6/mL")
    # fractions
    add("%", "fraction", F(1, 100), ["percent", "pct", "per cent"], ucum="%")
    add("‰", "fraction", F(1, 1000), ["per mille", "permille"], ucum="[ppth]")
    add("fraction", "fraction", 1, ["proportion", "fraction of 1"], ucum="1")
    add("L/L", "fraction", 1, ["l/l"], ucum="L/L")
    add("mmol/mol", "substance_fraction", F(1, 1000), ["mmol/mol Hb", "mmol/molHb"], ucum="mmol/mol")
    add("mol/mol", "substance_fraction", 1, [], ucum="mol/mol")
    add("µmol/mol", "substance_fraction", F(1, 10**6), [], ucum="umol/mol")
    # mass fractions / contents
    add("g/g", "mass_fraction", 1, [], ucum="g/g")
    add("mg/g", "mass_fraction", F(1, 1000),
        ["mg/g creatinine", "mg/g Cr", "mg/gCr", "mg/g creat", "mg/g Creat", "mg/g crea"], ucum="mg/g")
    add("µg/g", "mass_fraction", F(1, 10**6),
        ["µg/g creatinine", "µg/g Cr", "µg/gCr", "µg/g creat"], ucum="ug/g")
    add("ng/g", "mass_fraction", F(1, 10**9), [], ucum="ng/g")
    add("mg/kg", "mass_fraction", F(1, 10**6), [], ucum="mg/kg")
    add("µg/kg", "mass_fraction", F(1, 10**9), [], ucum="ug/kg")
    add("g/kg", "mass_fraction", F(1, 1000), [], ucum="g/kg")
    add("ng/mg", "mass_fraction", F(1, 10**6), [], ucum="ng/mg")
    add("mg/mmol", "mass_per_substance", 1, ["mg/mmol creatinine", "mg/mmol Cr", "mg/mmolCr", "mg/mmol creat"],
        ucum="mg/mmol")
    add("g/mol", "mass_per_substance", 1, [], ucum="g/mol")
    add("g/mmol", "mass_per_substance", 1000, [], ucum="g/mmol")
    # rates (24-hour collections etc.)
    DAY = 86400
    for m in ["g", "mg", "µg"]:
        add(f"{m}/24h", "mass_rate", PREFIX[m[:-1]] / DAY, [f"{m}/24 h", f"{m}/day", f"{m}/d"],
            ucum=ucum_of(f"{m}/(24.h)"))
    add("µg/min", "mass_rate", F(1, 10**6) / 60, [], ucum="ug/min")
    add("mg/min", "mass_rate", F(1, 1000) / 60, [], ucum="mg/min")
    for p in ["", "m", "µ"]:
        add(f"{p}mol/24h", "substance_rate", PREFIX[p] / DAY, [f"{p}mol/24 h", f"{p}mol/day", f"{p}mol/d"],
            ucum=ucum_of(f"{p}mol/(24.h)"))
    add("ng/mL/h", "mass_concentration_rate", F(1, 10**6) / 3600, ["ng/mL/hr", "ng/ml/h"], ucum="ng/mL/h")
    add("µg/L/h", "mass_concentration_rate", F(1, 10**6) / 3600, [], ucum="ug/L/h")
    add("ng/L/s", "mass_concentration_rate", F(1, 10**9), [], ucum="ng/L/s")
    # time
    add("s", "time", 1, ["sec", "secs", "second", "seconds"], ucum="s")
    add("min", "time", 60, ["minute", "minutes", "mins"], ucum="min")
    add("h", "time", 3600, ["hr", "hrs", "hour", "hours"], ucum="h")
    add("mm/h", "length_rate", F(1, 1000) / 3600, ["mm/1h", "mm/1 h", "mm/1st h", "mm in 1 h", "mm/60min"],
        ucum="mm/h")
    # cell volume and mass
    add("fL", "volume", F(1, 10**15), ["µm³", "µm3", "um3", "cubic microns"], ucum="fL")
    add("pL", "volume", F(1, 10**12), [], ucum="pL")
    add("g", "mass", 1, [], ucum="g")
    add("mg", "mass", F(1, 1000), [], ucum="mg")
    add("µg", "mass", F(1, 10**6), [], ucum="ug")
    add("ng", "mass", F(1, 10**9), [], ucum="ng")
    add("pg", "mass", F(1, 10**12), [], ucum="pg")
    add("mL/min/1.73m²", "volume_rate_bsa", 1,
        ["mL/min/1.73m2", "mL/min/1.73 m2", "mL/min/1.73 m²", "mL/min/1,73m2", "mL/min/1,73 m2",
         "mL/min/1,73m²", "mL/min/1.73m^2", "mL/min per 1.73 m2", "mL/min/{1.73_m2}"], ucum=None,
        note="UCUM has no single agreed code for this; none is shipped")
    # D-dimer
    for m, s in [("mg", F(1, 1000)), ("µg", F(1, 10**6)), ("ng", F(1, 10**9))]:
        for v in ["L", "mL"]:
            add(f"{m}/{v} FEU", "mass_concentration_feu", s / VOL[v], [f"{m}/{v}FEU", f"{m}/{v} (FEU)"],
                ucum=ucum_of(f"{m}/{v}") + "{FEU}")
            add(f"{m}/{v} DDU", "mass_concentration_ddu", s / VOL[v], [f"{m}/{v}DDU", f"{m}/{v} (DDU)"],
                ucum=ucum_of(f"{m}/{v}") + "{DDU}")
    # arbitrary
    for canon, al, cs, ucum, note in ARBITRARY:
        out.append(dict(unit=canon, dimension="arbitrary:" + canon, scale=F(1), aliases=al, cs_aliases=cs,
                        ucum=ucum, note=note))
    return out


# ---------------------------------------------------------------------------
# Ambiguous spellings. The same letters mean different numbers in different
# languages, so these are refused unless the caller passes a locale. "mil" is
# the Spanish word for one thousand (miles = thousands; millions are "mill." or
# "millones"), while US reports use "Mil" for million (RBC "mil/uL") and
# Romanian reports use "mil." for milioane (thousands are "mii"). Matching is
# case-insensitive: capitalisation does not tell the conventions apart.
# readings: language subtag -> canonical unit.
# ---------------------------------------------------------------------------
AMBIGUOUS = [
    dict(id="mil-per-mm3", spellings=["mil/mm3", "mil/mm³", "mil/cmm", "mil./mm3", "mil./mm³"],
         readings={"es": "10^3/mm³", "en": "10^6/mm³", "ro": "10^6/mm³", "de": "10^6/mm³"}),
    dict(id="mil-per-uL", spellings=["mil/µL", "mil./µL"],
         readings={"es": "10^3/µL", "en": "10^6/µL", "ro": "10^6/µL", "de": "10^6/µL"}),
]

# What "mil" means in each language for which a reading is shipped, and why.
LANGUAGE_READINGS = {
    "es": dict(meaning="thousand",
               note="Spanish: 'mil' is the numeral one thousand (miles = thousands), so 'mil/mm3' = 10^3/mm³. "
                    "Spanish has no conventional abbreviation for millón; millions are written out ('millones') or "
                    "shortened to 'mill.'. Spanish-language documents translated from US usage can still use 'mil' "
                    "for million (NIH Clinical Center), so pass locale='es' only for reports that follow Spanish usage.",
               sources=["eswiktionary-mil", "nih-cc-cbc-es"]),
    "en": dict(meaning="million",
               note="English (US reports): 'Mil' abbreviates million, for example red cell counts in 'mil/uL'.",
               sources=["uw-dlmp-rbc", "nih-cc-cbc-es"]),
    "ro": dict(meaning="million",
               note="Romanian: 'mil.' is read as an abbreviation of milion (plural milioane); thousands are 'mii' "
                    "(plural of mie). No dictionary entry for the abbreviation 'mil.' itself was found; the reading "
                    "rests on the two numerals.",
               sources=["dexonline-milion", "dexonline-mie"]),
    "de": dict(meaning="million",
               note="German: 'Mio.' is the usual abbreviation of Million (plural Millionen), with 'Mill.' and 'Mil.' "
                    "as alternative spellings; thousands are 'Tsd.' (Tausend). 'mil' is never German for thousand.",
               sources=["dewiktionary-mio", "dewiktionary-tsd"]),
}
AMBIGUOUS_REASON = ("'mil' means thousand in Spanish ('7,5 mil/mm3' white cells = 7.5 × 10^3/mm³) but million on "
                    "English and Romanian reports ('4.5 Mil/µL' red cells = 4.5 × 10^6/µL), a factor of 1000 apart.")


# ---------------------------------------------------------------------------
# Sources for spellings whose meaning is not plain unit notation: number words,
# their abbreviations and letter prefixes used by labs in one language. Each
# entry names the canonical unit, the spellings it covers (each must resolve to
# that unit) and the sources that show the spelling or its meaning.
# ---------------------------------------------------------------------------
SPELLING_SOURCES = [
    dict(unit="10^9/L", spellings=["G/L", "G/l", "Giga/L", "Giga/l"],
         note="German, Austrian and Swiss reports: G is the SI prefix giga (10^9) and l or L the litre, so "
              "'6,2 G/l' white cells = 6.2 × 10^9/L. Lower-case 'g/l' is gram per litre: only a capital G reads "
              "as giga.",
         sources=["gesundheit-gv-leukozyten", "insel-zlm-haematologie", "ukulm-kleines-blutbild",
                  "dewikipedia-leukozyt"]),
    dict(unit="10^9/L", spellings=["Gpt/L", "Gpt/l"],
         note="German (mainly eastern German) reports: Gpt = Gigapartikel, 10^9 particles.",
         sources=["ukmd-laborparameter"]),
    dict(unit="10^12/L", spellings=["T/L", "T/l", "Tera/L", "Tera/l"],
         note="German, Austrian and Swiss reports: T is the SI prefix tera (10^12), so '4,8 T/l' red cells = "
              "4.8 × 10^12/L. Lower-case 't/l' is not read.",
         sources=["gesundheit-gv-erythrozyten", "insel-zlm-haematologie", "ukulm-kleines-blutbild"]),
    dict(unit="10^12/L", spellings=["Tpt/L", "Tpt/l"],
         note="German (mainly eastern German) reports: Tpt = Terapartikel, 10^12 particles.",
         sources=["ukmd-laborparameter"]),
    dict(unit="10^3/µL", spellings=["Tsd/µL", "Tsd./µL", "Tausend/µL"],
         note="German: 'Tsd.' abbreviates Tausend (thousand), so '6,2 Tsd./µl' = 6.2 × 10^3/µL = 6.2 × 10^9/L.",
         sources=["dewiktionary-tsd", "mhh-zla-referenzbereiche", "dewikipedia-blutbild"]),
    dict(unit="10^6/µL", spellings=["Mio/µL", "Mio./µL", "Millionen/µL"],
         note="German: 'Mio.' abbreviates Million(en), so '4,8 Mio./µl' red cells = 4.8 × 10^6/µL = "
              "4.8 × 10^12/L.",
         sources=["dewiktionary-mio", "mhh-zla-referenzbereiche", "dewikipedia-blutbild"]),
    dict(unit="/nL", spellings=["/nL", "pro nL"],
         note="German: counts per nanolitre (nl), 1/nL = 10^9/L; 'pro' is German for 'per'.",
         sources=["dewikipedia-leukozyt"]),
]


# ---------------------------------------------------------------------------
# Normalisation rules. Applied in order to the input, and again to the
# lower-cased input for the case-insensitive pass. Replacement strings use
# $1-style group references (translated for Python by the runtimes).
# Only regex features that behave identically in Python `re` and JavaScript
# are used: no \b, no lookbehind, no Unicode classes.
# ---------------------------------------------------------------------------
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
NORMALIZATION_RULES = [
    ("μ", "µ", "Greek small mu (U+03BC) to micro sign (U+00B5)"),
    ("Μ(?=[gmLlIU])", "µ", "Greek capital mu used as micro"),
    ("[   \t]", " ", "thin, narrow and non-breaking spaces to space"),
    ("−", "-", "minus sign to hyphen"),
    ("10(?=[" + SUP + "])", "10^", "superscript exponent after 10: insert ^"),
] + [(d, str(i), f"superscript {i}") for i, d in enumerate(SUP)] + [
    ("10 *(?:\\*\\*|\\*|E|e|\\^) *([0-9]+)", "10^$1", "10E9, 10e9, 10*9, 10**9 to 10^9"),
    ("^ *[xX×*] *(?=10\\^)", "", "leading multiplication sign before 10^n"),
    ("^ *(?:[xX×] *)?(?:1000|10\\^3) *(?=/)", "10^3", "x1000/µL, 1000/µL"),
    ("\\[(?:IU|iU|iu)\\]", "IU", "UCUM [IU] to IU"),
    ("mc(?=(?:g|mol|L|l|IU|iu|U|u|kat|M)(?:[^a-z]|$))", "µ", "mcg, mcmol, mcL to µ"),
    ("(^|[^A-Za-z])u(?=(?:g|mol|L|l|IU|iu|U|u|kat|Eq|eq|m3|m³|M)(?:[^a-z]|$))", "$1µ", "u prefix to µ"),
    ("(^|[^A-Za-z])([mµk]?)UI(?=/)", "$1$2IU", "French/Romanian UI to IU"),
    ("(^|[^A-Za-z])([mµk]?)ui(?=/)", "$1$2iu", "lower-case ui to iu"),
    ("/ *24 *(?:hours?|hrs?|h)(?![a-z])", "/24h", "/24 hr to /24h"),
    ("/ *(?:hours?|hrs?)(?![a-z])", "/h", "/hr, /hour to /h"),
    (" *(/) *", "$1", "no spaces around /"),
    (" +", " ", "collapse spaces"),
]


# ---------------------------------------------------------------------------
# Sources that are not PubChem compound records.
# ---------------------------------------------------------------------------
SOURCES = {
    "dewiktionary-tsd": dict(
        label="Wiktionary (German), entry 'Tsd.' (Abkürzung)",
        url="https://de.wiktionary.org/wiki/Tsd.", kind="dictionary", accessed="2026-11-27",
        location="Bedeutungen: '[1] Tausend'; Beispiele: '10 Tsd. Stück'"),
    "dewiktionary-mio": dict(
        label="Wiktionary (German), entry 'Mio.' (Abkürzung)",
        url="https://de.wiktionary.org/wiki/Mio.", kind="dictionary", accessed="2026-11-27",
        location="Bedeutungen: '[1] Million(en)'; Alternative Schreibweisen: 'Mill., auch Mil.'"),
    "dewikipedia-blutbild": dict(
        label="Wikipedia (German), article 'Blutbild'",
        url="https://de.wikipedia.org/wiki/Blutbild", kind="encyclopedia", accessed="2026-11-27",
        location="section '„Kleines“ Blutbild', table: Leukozyten and Thrombozyten in 'Tsd./µl', Erythrozyten in "
                 "'Mio./µl'"),
    "dewikipedia-leukozyt": dict(
        label="Wikipedia (German), article 'Leukozyt'",
        url="https://de.wikipedia.org/wiki/Leukozyt", kind="encyclopedia", accessed="2026-11-27",
        location="section 'Zahlen und Werte': 'Dies sind die Zellanzahl pro Mikroliter (µl) und die pro Nanoliter "
                 "(nl). In SI-Einheiten und SI-Präfixen können diese Einheiten als 10^6/l = Mega/Liter und "
                 "10^9/l = Giga/Liter ausgedrückt werden.'"),
    "gesundheit-gv-leukozyten": dict(
        label="gesundheit.gv.at (Austrian public health portal), Laborwerte: Leukozyten",
        url="https://www.gesundheit.gv.at/labor/laborwerte/blutbild/leukozyten", kind="patient_education",
        accessed="2026-11-27",
        location="reference table: unit 'G/L (Giga pro Liter)', adults '4,0–10,0 G/L'"),
    "gesundheit-gv-erythrozyten": dict(
        label="gesundheit.gv.at (Austrian public health portal), Laborwerte: Erythrozyten",
        url="https://www.gesundheit.gv.at/labor/laborwerte/blutbild/erythrozyten", kind="patient_education",
        accessed="2026-11-27",
        location="reference table: unit 'T/L (Tera pro Liter)', men '4,5–5,5 T/L', women '4,0–5,0 T/L'"),
    "insel-zlm-haematologie": dict(
        label="Inselspital Bern, Zentrum für Labormedizin: Referenzwerte Morphologische Hämatologie, version 7.0, "
              "10.10.2023",
        url="https://zlm.insel.ch/fileadmin/Zentrum_f%C3%BCr_Labormedizin/Dokumente/"
            "Akkreditierungsurkunden_und_Referenzwerte/Referenzwerte__Morphologische_Haematologie.pdf",
        kind="lab_test_guide", accessed="2026-11-27",
        location="p. 1, Blutbild: 'Leukozyten G/L', 'Erythrozyten T/L', 'Thrombozyten G/L' (Swiss usage)"),
    "ukulm-kleines-blutbild": dict(
        label="Universitätsklinikum Ulm, Klinische Chemie: Leistungsverzeichnis Kleines Blutbild und maschinelle "
              "Differenzierung (FB-PÄ 6 BB OE)",
        url="https://www.uniklinik-ulm.de/fileadmin/default/09_Sonstige/Klinische-Chemie/Seiteninhalte/"
            "Seiteninhalte_B/Kleines_Blutbild_und_maschinelle_Differenzierung_FB-PAE_6_BB_OE.pdf",
        kind="lab_test_guide", accessed="2026-11-27",
        location="p. 2: 'Erythrozyten Tera/l', 'Leukozyten Giga/l', 'Thrombozyten Giga/l'; p. 3: "
                 "'Erythrozyten 4,5 – 5,9 Tera/l', 'Leukozyten 4,4 – 11,3 Giga/l'"),
    "ukmd-laborparameter": dict(
        label="Universitätsklinikum Magdeburg, Klinik für Hämatologie und Onkologie: Informationen zu den "
              "Laborparametern (2007)",
        url="https://www.med.uni-magdeburg.de/unimagdeburg_mm/Downloads/Kliniken/KHAE/haemalabor/InfoLabParm.pdf",
        kind="lab_test_guide", accessed="2026-11-27",
        location="p. 4: 'Leukozyten: 4,0 - 10,0 Gpt/l', 'Erythrozyten: weibl.: 4,0 – 5,5 Tpt/l', "
                 "'Thrombozyten: 150 - 375 Gpt/l'"),
    "mhh-zla-referenzbereiche": dict(
        label="Medizinische Hochschule Hannover, Zentrallabor (ZLA): Leistungsverzeichnis ZLA Referenzbereiche, "
              "version 7.0, 18.06.2025",
        url="https://www.mhh.de/fileadmin/mhh/zentrallabor-zla/downloads/LVZ_ZLA_Referenzbereiche.pdf",
        kind="lab_test_guide", accessed="2026-11-27",
        location="p. 26, Tabelle 02: 'Erythrozyten (Mio./µl)'; p. 27-28: Normoblasten and Thrombozyten in "
                 "'Tsd./µl'"),
    "eswiktionary-mil": dict(
        label="Wikcionario (Spanish Wiktionary), entry 'mil' (Spanish)",
        url="https://es.wiktionary.org/wiki/mil", kind="dictionary", accessed="2026-11-26",
        location="Adjetivo, sense 1: 'Diez veces cien.'; Sustantivo masculino, sense 4: 'El número 1000, 10^3.' "
                 "(The RAE Diccionario de la lengua española, https://dle.rae.es/mil, gives the same definition but "
                 "refused a scripted download, HTTP 403.)"),
    "nih-cc-cbc-es": dict(
        label="NIH Clinical Center, Patient Education: 'Entendiendo su conteo sanguíneo completo' (Spanish edition "
              "of 'Understanding your complete blood count'), archived 2009-01-09",
        url="https://web.archive.org/web/20090109175010/http://www.cc.nih.gov/ccc/patient_education/pepubs_sp/cbcsp.pdf",
        kind="patient_education", accessed="2026-11-26",
        location="p. 1: 'Los glóbulos rojos se miden en millones por milímetro cúbico (mil/mm3) de sangre.' and "
                 "white cells 'se miden en miles por milímetro cúbico (K/mm3)'; 'RBC: 3.58-4.99 mil/mm3'. A Spanish "
                 "text that uses 'mil' for million, following US usage."),
    "uw-dlmp-rbc": dict(
        label="UW Medicine Department of Laboratory Medicine and Pathology, Test Guide: Red Blood Cell Count (RBC)",
        url="https://dlmp.uw.edu/test-guide/view/RBC", kind="lab_test_guide", accessed="2026-11-26",
        location="reference ranges in 'mil/uL', for example adults 3.80-5.00 (female) and 4.40-5.60 (male)"),
    "dexonline-mie": dict(
        label="DEX '09 (Dicționarul explicativ al limbii române), entry 'mie', via dexonline.ro",
        url="https://dexonline.ro/definitie/mie", kind="dictionary", accessed="2026-11-26",
        location="'MIE, mii, num. card. ... Numărul care în numărătoare are locul între 999 și 1001.'"),
    "dexonline-milion": dict(
        label="DEX '09 (Dicționarul explicativ al limbii române), entry 'milion', via dexonline.ro",
        url="https://dexonline.ro/definitie/milion", kind="dictionary", accessed="2026-11-26",
        location="'MILION, milioane, num. card. Număr egal cu o mie de mii.'"),
    "ciaaw-abridged": dict(
        label="CIAAW, Abridged standard atomic weights (five significant digits)",
        url="https://www.ciaaw.org/abridged-atomic-weights.htm", kind="atomic_weight",
        location="table of abridged atomic weights"),
    "ngsp-ifcc": dict(
        label="NGSP, IFCC Standardization of HbA1c: The IFCC and NGSP, Table 2 (master equation)",
        url="https://ngsp.org/ifccngsp.asp", kind="equation",
        location="Table 2: NGSP = (0.09148*IFCC) + 2.152; IFCC = (10.93*NGSP) - 23.50"),
    "hoelzel-2004": dict(
        label="Hoelzel W et al. IFCC reference system for measurement of hemoglobin A1c in human blood and the "
              "national standardization schemes in the United States, Japan, and Sweden: a method-comparison "
              "study. Clin Chem 2004;50(1):166-174",
        url="https://doi.org/10.1373/clinchem.2003.024802", doi="10.1373/clinchem.2003.024802", kind="literature",
        location="cited by NGSP as the origin of the master equation; coefficients read from the NGSP page"),
    "kronenberg-2022": dict(
        label="Kronenberg F et al. Lipoprotein(a) in atherosclerotic cardiovascular disease and aortic stenosis: "
              "a European Atherosclerosis Society consensus statement. Eur Heart J 2022;43(39):3925-3946",
        url="https://doi.org/10.1093/eurheartj/ehac361", doi="10.1093/eurheartj/ehac361", kind="literature",
        location="section on Lp(a) measurement: 'This panel does not recommend using a standard factor to "
                 "convert between mg/dL and nmol/L, as assays vary extensively.' (full text PMC9639807)"),
    "rosli-2022": dict(
        label="Rosli N, Kwon H, Lim J, Yoon Y, Jeong J. Measurement comparability of insulin assays using "
              "conventional immunoassay kits. J Clin Lab Anal 2022;36(7)",
        url="https://doi.org/10.1002/jcla.24521", doi="10.1002/jcla.24521", kind="literature",
        location="Results/Discussion: 'Even a harmonized conversion factor are recommended, 6.00 pmol/L, there "
                 "are still several different conversion factors available depending on the manufacturer or "
                 "field.' (full text PMC9279959)"),
    "iom-2011-vitd": dict(
        label="Institute of Medicine. Dietary Reference Intakes for Calcium and Vitamin D. Washington, DC: The "
              "National Academies Press; 2011",
        url="https://doi.org/10.17226/13050", doi="10.17226/13050", kind="literature",
        location="Chapter 3, Box 3-1, p. 78: '1 IU of vitamin D is defined as the activity of 0.025 μg of "
                 "cholecalciferol'; 'The biological activity of 1 μg of vitamin D is equivalent to 40 IU.'; "
                 "serum nmol/L to ng/mL 'by dividing by a factor of 2.5'"),
    "ucum-2.2": dict(
        label="Schadow G, McDonald CJ. The Unified Code for Units of Measure, version 2.2 (2024-06-17)",
        url="https://ucum.org/ucum", kind="standard",
        location="§24-§25 arbitrary units; unit atoms U (= umol/min), kat (= mol/s), [IU] (arbitrary), eq, osm"),
    "ramsay-tipton-2017": dict(
        label="Ramsay R, Tipton K. Assessment of enzyme inhibition: a review with examples from the "
              "development of monoamine oxidase and cholinesterase inhibitory drugs. Molecules 2017;22(7):1192",
        url="https://doi.org/10.3390/molecules22071192", doi="10.3390/molecules22071192", kind="literature",
        location="'The most commonly used quantity is the Unit, sometimes referred to as the International Unit "
                 "(IU) or Enzyme Unit.' and '1 Unit = 1 μmol·min−1' (full text PMC6152246)"),
    "nhanes-biopro-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation BIOPRO_L (Standard Biochemistry Profile)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BIOPRO_L.htm", kind="published_table",
        location="Data Processing and Editing: '... was converted to ... by multiplying by ...'"),
    "nhanes-trigly-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation TRIGLY_L (Triglyceride and LDL-cholesterol)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TRIGLY_L.htm", kind="published_table",
        location="'The triglyceride values in mg/dL (LBXTLG) were converted to mmol/L (LBDTRSI) by multiplying "
                 "by 0.01129.'"),
    "nhanes-tchol-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation TCHOL_L (Total cholesterol)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TCHOL_L.htm", kind="published_table",
        location="'... converted to mmol/L (LBDTCSI) by multiplying by 0.02586.'"),
    "nhanes-glu-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation GLU_L (Plasma fasting glucose)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/GLU_L.htm", kind="published_table",
        location="'... converted to mmol/L (LBDGLUSI) by multiplying by 0.05551'"),
    "nhanes-tst-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation TST_L (Sex steroid hormone panel)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/TST_L.htm", kind="published_table",
        location="Data Processing and Editing: SI conversions for each hormone"),
    "nhanes-folate-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation FOLATE_L (RBC folate)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/FOLATE_L.htm", kind="published_table",
        location="'... converted to ng/mL RBC (LBDRFO) by dividing LBDRFOSI by 2.265'"),
    "nhanes-alb-cr-l": dict(
        label="CDC NHANES 2021-2023 laboratory documentation ALB_CR_L (Albumin and creatinine, urine)",
        url="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/ALB_CR_L.htm", kind="published_table",
        location="'... urine creatinine value in mg/dL (URXUCR) was converted to µmol/L (URXCRS) by multiplying "
                 "by 88.4'"),
}

ENZYME_CAVEAT = ("Converting U/L, IU/L and µkat/L changes the unit only. It does not make results from different "
                 "methods, reaction temperatures (for example 30 °C vs 37 °C) or reference systems comparable.")

# ---------------------------------------------------------------------------
# Analytes. mm = ("pubchem", CID) | ("ciaaw", symbol) | ("ciaaw2", symbol) [diatomic N2 not needed]
# charge: |z| for mEq conversions. enzyme: U/L <-> katal and IU/L == U/L.
# crosscheck: (source_id, from_unit, to_unit, published multiplier) read from that source.
# ---------------------------------------------------------------------------
ANALYTES = [
    dict(id="glucose", name="Glucose", markers=["glucose-fasting", "ogtt-2h-glucose", "eag"],
         mm=("pubchem", 5793), crosscheck=[("nhanes-glu-l", "mg/dL", "mmol/L", 0.05551),
                                          ("nhanes-biopro-l", "mg/dL", "mmol/L", 0.0555)]),
    dict(id="cholesterol", name="Cholesterol (total, HDL, LDL, non-HDL, VLDL, remnant)",
         markers=["total-cholesterol", "hdl-cholesterol", "ldl-cholesterol", "non-hdl-cholesterol",
                  "vldl-cholesterol", "remnant-cholesterol"],
         mm=("pubchem", 5997), crosscheck=[("nhanes-tchol-l", "mg/dL", "mmol/L", 0.02586),
                                          ("nhanes-biopro-l", "mg/dL", "mmol/L", 0.0259)],
         note="Lipoprotein cholesterol fractions are reported as cholesterol mass or amount, so the cholesterol "
              "molar mass applies to each of them."),
    dict(id="triglycerides", name="Triglycerides", markers=["triglycerides"],
         published=("nhanes-trigly-l", "mg/dL", "mmol/L", 0.01129), mm_check=("pubchem", 5497163),
         crosscheck=[("nhanes-biopro-l", "mg/dL", "mmol/L", 0.0113)],
         note="Triglycerides are a mixture, not one compound. The factor is the published NHANES factor "
              "(0.01129). Triolein (PubChem CID 5497163, 885.4 g/mol) gives 0.011294, a cross-check only."),
    dict(id="creatinine", name="Creatinine", markers=["creatinine-serum", "urine-creatinine"],
         mm=("pubchem", 588), crosscheck=[("nhanes-biopro-l", "mg/dL", "µmol/L", 88.4),
                                         ("nhanes-alb-cr-l", "mg/dL", "µmol/L", 88.4)]),
    dict(id="uric-acid", name="Uric acid", markers=["uric-acid"], mm=("pubchem", 1175),
         crosscheck=[("nhanes-biopro-l", "mg/dL", "µmol/L", 59.48)]),
    dict(id="bilirubin", name="Bilirubin (total, direct, indirect)",
         markers=["total-bilirubin", "direct-bilirubin", "indirect-bilirubin"], mm=("pubchem", 5280352),
         crosscheck=[("nhanes-biopro-l", "mg/dL", "µmol/L", 17.1)]),
    dict(id="urea", name="Urea", markers=["urea"], mm=("pubchem", 1176),
         note="Mass units here are mass of urea. For blood urea nitrogen (mass of nitrogen) use "
              "analyte='blood-urea-nitrogen'."),
    dict(id="blood-urea-nitrogen", name="Blood urea nitrogen (BUN)", markers=["blood-urea-nitrogen"],
         bun=("pubchem", 947), crosscheck=[("nhanes-biopro-l", "mg/dL", "mmol/L", 0.357)],
         note="BUN is reported as the mass of urea nitrogen. One mole of urea (CH4N2O) holds two moles of "
              "nitrogen atoms, so mg/dL of urea nitrogen converts to mmol/L of urea with the molar mass of N2 "
              "(PubChem CID 947, 28.014 g/mol). Mass units mean mass of nitrogen, not mass of urea."),
    dict(id="calcium", name="Calcium (total, ionized, albumin-corrected)",
         markers=["calcium-total", "calcium-ionized", "calcium-corrected"], mm=("ciaaw", "Ca"), charge=2,
         crosscheck=[("nhanes-biopro-l", "mg/dL", "mmol/L", 0.250)]),
    dict(id="magnesium", name="Magnesium", markers=["magnesium-serum", "magnesium-rbc"], mm=("ciaaw", "Mg"),
         charge=2),
    dict(id="phosphorus", name="Phosphorus (inorganic phosphate, as P)", markers=["phosphorus-serum"],
         mm=("ciaaw", "P"), crosscheck=[("nhanes-biopro-l", "mg/dL", "mmol/L", 0.323)],
         note="Mass is reported as phosphorus (P), so the atomic weight of P is used. mEq/L is not supported "
              "because the charge of serum phosphate depends on pH."),
    dict(id="iron", name="Iron (serum iron, TIBC, UIBC)", markers=["serum-iron", "tibc", "uibc"],
         mm=("ciaaw", "Fe"), crosscheck=[("nhanes-biopro-l", "µg/dL", "µmol/L", 0.1791)],
         note="TIBC and UIBC are expressed as the amount of iron that can be bound, so the iron atomic weight "
              "applies."),
    dict(id="zinc", name="Zinc", markers=["zinc"], mm=("ciaaw", "Zn")),
    dict(id="copper", name="Copper", markers=["copper"], mm=("ciaaw", "Cu")),
    dict(id="selenium", name="Selenium", markers=["selenium"], mm=("ciaaw", "Se")),
    dict(id="manganese", name="Manganese", markers=["manganese"], mm=("ciaaw", "Mn")),
    dict(id="chromium", name="Chromium", markers=["chromium"], mm=("ciaaw", "Cr")),
    dict(id="sodium", name="Sodium", markers=["sodium-serum", "urine-sodium"], mm=("ciaaw", "Na"), charge=1),
    dict(id="potassium", name="Potassium", markers=["potassium-serum", "urine-potassium"], mm=("ciaaw", "K"),
         charge=1),
    dict(id="chloride", name="Chloride", markers=["chloride-serum"], mm=("ciaaw", "Cl"), charge=1),
    dict(id="bicarbonate", name="Bicarbonate (total CO2)", markers=["bicarbonate-co2"], charge=1,
         note="Only mEq/L <-> mmol/L (charge 1). No mass conversion: total CO2 is not a single species."),
    dict(id="anion-gap", name="Anion gap", markers=["anion-gap"], charge=1,
         note="The anion gap is computed from monovalent ions (Na+, Cl-, HCO3-), so mEq/L equals mmol/L."),
    dict(id="cortisol", name="Cortisol", markers=["cortisol-am", "cortisol-pm"], mm=("pubchem", 5754)),
    dict(id="testosterone", name="Testosterone (total, free, bioavailable)",
         markers=["testosterone-total", "testosterone-free", "testosterone-bioavailable"], mm=("pubchem", 6013),
         crosscheck=[("nhanes-tst-l", "ng/dL", "nmol/L", 0.0347)]),
    dict(id="estradiol", name="Estradiol", markers=["estradiol-e2"], mm=("pubchem", 5757),
         crosscheck=[("nhanes-tst-l", "pg/mL", "pmol/L", 3.67)]),
    dict(id="estrone", name="Estrone", markers=["estrone-e1"], mm=("pubchem", 5870),
         crosscheck=[("nhanes-tst-l", "ng/dL", "pmol/L", 37.0)]),
    dict(id="dhea-s", name="DHEA sulfate", markers=["dhea-s"], mm=("pubchem", 12594),
         crosscheck=[("nhanes-tst-l", "µg/dL", "µmol/L", 0.0271)]),
    dict(id="dhea", name="DHEA (dehydroepiandrosterone)", markers=["dhea"], mm=("pubchem", 5881)),
    dict(id="androstenedione", name="Androstenedione", markers=["androstenedione"], mm=("pubchem", 6128),
         crosscheck=[("nhanes-tst-l", "ng/dL", "nmol/L", 0.0349)]),
    dict(id="17-hydroxyprogesterone", name="17-Hydroxyprogesterone", markers=["17-hydroxyprogesterone"],
         mm=("pubchem", 6238), crosscheck=[("nhanes-tst-l", "ng/dL", "nmol/L", 0.0303)]),
    dict(id="progesterone", name="Progesterone", markers=["progesterone"], mm=("pubchem", 5994),
         crosscheck=[("nhanes-tst-l", "ng/dL", "nmol/L", 0.0318)]),
    dict(id="aldosterone", name="Aldosterone", markers=["aldosterone"], mm=("pubchem", 5839)),
    dict(id="dihydrotestosterone", name="Dihydrotestosterone", markers=["dht"], mm=("pubchem", 10635)),
    dict(id="pregnenolone", name="Pregnenolone", markers=["pregnenolone"], mm=("pubchem", 8955)),
    dict(id="folate", name="Folate (serum, red cell)", markers=["folate-serum", "folate-rbc"],
         mm=("pubchem", 135398658), crosscheck=[("nhanes-folate-l", "ng/mL", "nmol/L", 2.265)],
         alt_compound=("pubchem", 135398561),
         caveats=["Reference compound: folic acid (PubChem CID 135398658, 441.4 g/mol). If your assay is "
                  "calibrated to 5-methyltetrahydrofolate (L-methylfolate, PubChem CID 135398561, 459.5 g/mol), "
                  "the factor differs by about 4%."],
         note="Uses the molar mass of folic acid (PubChem CID 135398658)."),
    dict(id="triiodothyronine", name="Triiodothyronine (free T3, total T3, reverse T3)",
         markers=["free-t3", "total-t3", "reverse-t3"], mm=("pubchem", 5920),
         note="Reverse T3 (PubChem CID 644280) has the same formula and molar mass (650.97 g/mol)."),
    dict(id="thyroxine", name="Thyroxine (free T4, total T4)", markers=["free-t4", "total-t4"],
         mm=("pubchem", 5819)),
    dict(id="vitamin-b12", name="Vitamin B12 (cobalamin)", markers=["vitamin-b12"], mm=("pubchem", 5311498),
         note="Uses the molar mass of cyanocobalamin (PubChem CID 5311498). Other cobalamins differ slightly."),
    dict(id="25-hydroxyvitamin-d", name="25-Hydroxyvitamin D", markers=["vitamin-d-25-oh"],
         mm=("pubchem", 5283731), extra_sources=["iom-2011-vitd"], alt_compound=("pubchem", 5710148),
         caveats=["Reference compound: 25-hydroxyvitamin D3 (PubChem CID 5283731, 400.6 g/mol). "
                  "25-hydroxyvitamin D2 (PubChem CID 5710148, 412.6 g/mol) would give a factor about 3% different; "
                  "total 25(OH)D results that are largely D2 are converted with the D3 molar mass."],
         note="Uses 25-hydroxyvitamin D3 (PubChem CID 5283731, 400.6 g/mol). 25-hydroxyvitamin D2 is "
              "412.6 g/mol (CID 5710148); results that are mostly D2 would differ by about 3%. The IOM 2011 "
              "report gives the rounded divisor 2.5."),
    dict(id="1-25-dihydroxyvitamin-d", name="1,25-Dihydroxyvitamin D", markers=["vitamin-d-1-25-oh2"],
         mm=("pubchem", 5280453), note="Uses calcitriol (1,25-dihydroxyvitamin D3, PubChem CID 5280453)."),
    dict(id="homocysteine", name="Homocysteine", markers=["homocysteine"], mm=("pubchem", 91552)),
    dict(id="methylmalonic-acid", name="Methylmalonic acid", markers=["methylmalonic-acid"], mm=("pubchem", 487)),
    dict(id="vitamin-a", name="Vitamin A (retinol)", markers=["vitamin-a"], mm=("pubchem", 445354)),
    dict(id="vitamin-c", name="Vitamin C (ascorbic acid)", markers=["vitamin-c"], mm=("pubchem", 54670067)),
    dict(id="vitamin-e", name="Vitamin E (alpha-tocopherol)", markers=["vitamin-e"], mm=("pubchem", 14985)),
    dict(id="vitamin-k", name="Vitamin K1 (phylloquinone)", markers=["vitamin-k"], mm=("pubchem", 5284607)),
    dict(id="lactate", name="Lactate", markers=["lactate-serum"], mm=("pubchem", 612),
         note="Uses lactic acid (PubChem CID 612, 90.08 g/mol). The lactate anion is about 1 g/mol lighter "
              "(0.1%)."),
    dict(id="amh", name="Anti-Müllerian hormone", markers=["amh"],
         note="No conversion by default: AMH is a glycoprotein, so there is no formula-based molar mass. See the "
              "forbidden rule amh-mass-vs-molar; pass factor= with the factor your assay states."),
    # enzymes
    *[dict(id=s, name=n, markers=m, enzyme=True, caveats=[ENZYME_CAVEAT]) for s, n, m in [
        ("alp", "Alkaline phosphatase", ["alp"]), ("alt", "Alanine aminotransferase", ["alt"]),
        ("ast", "Aspartate aminotransferase", ["ast"]), ("ggt", "Gamma-glutamyl transferase", ["ggt"]),
        ("ldh", "Lactate dehydrogenase", ["ldh"]), ("ck", "Creatine kinase", ["ck-total"]),
        ("amylase", "Amylase", ["amylase"]), ("lipase", "Lipase", ["lipase"]),
        ("lp-pla2", "Lipoprotein-associated phospholipase A2 (activity)",
         ["lipoprotein-associated-phospholipase-a2"]),
    ]],
    # ratios with creatinine in the denominator
    dict(id="urine-albumin-creatinine-ratio", name="Urine albumin/creatinine ratio", markers=["urine-acr"],
         creat_denominator=("pubchem", 588)),
    dict(id="urine-protein-creatinine-ratio", name="Urine protein/creatinine ratio",
         markers=["urine-protein-creatinine-ratio"], creat_denominator=("pubchem", 588)),
    # equation
    dict(id="hba1c", name="Haemoglobin A1c", markers=["hba1c"], hba1c=True),
    # dose
    dict(id="vitamin-d-dose", name="Vitamin D (intake or dose, cholecalciferol)", markers=[], vitd_dose=True,
         note="For doses and intakes only (supplements, food). Blood levels are never in IU."),
    # forbidden-only analytes
    dict(id="lipoprotein-a", name="Lipoprotein(a)", markers=["lipoprotein-a"]),
    dict(id="insulin", name="Insulin", markers=["fasting-insulin"]),
]

FORBIDDEN = [
    dict(id="lpa-mass-vs-molar", analyte="lipoprotein-a", a="mass_concentration", b="substance_concentration",
         example=("mg/dL", "nmol/L"),
         reason="Lp(a) mass (mg/dL) and particle concentration (nmol/L) measure different things. Apolipoprotein(a) "
                "size varies between people, and assays vary, so there is no fixed factor.",
         sources=["kronenberg-2022"]),
    dict(id="insulin-iu-vs-molar", analyte="insulin", a="iu_concentration", b="substance_concentration",
         example=("µIU/mL", "pmol/L"),
         reason="Insulin µIU/mL to pmol/L factors differ by assay and manufacturer (6.0 is common, others are in "
                "use). Convert only with the factor stated by the assay that produced the result.",
         sources=["rosli-2022"]),
    dict(id="amh-mass-vs-molar", analyte="amh", a="mass_concentration", b="substance_concentration",
         example=("ng/mL", "pmol/L"),
         reason="AMH is a glycoprotein with no formula-based molar mass. NHANES 2021-2023 (TST_L) converts ng/mL to "
                "pmol/L by multiplying by 7.14, but does not state that the factor is assay-independent. lifefrom-units "
                "does not apply it by default; pass factor= with the factor your assay states.",
         sources=["nhanes-tst-l"]),
    dict(id="hba1c-percent-vs-mmolmol-by-factor", analyte=None, a="fraction", b="substance_fraction",
         example=("%", "mmol/mol"),
         reason="% and mmol/mol cannot be converted by a unit factor. For HbA1c, NGSP % and IFCC mmol/mol are "
                "related by the IFCC-NGSP master equation: pass analyte='hba1c'.",
         sources=["ngsp-ifcc"]),
    dict(id="hba1c-percent-as-fraction", analyte="hba1c", a="fraction", b="*",
         a_units=["fraction", "L/L", "‰"], example=("%", "fraction"),
         reason="HbA1c NGSP % is a calibrated scale tied to the DCCT, not a true fraction of total haemoglobin. "
                "Use % or mmol/mol for HbA1c, not a fraction of 1.",
         sources=["ngsp-ifcc"]),
    dict(id="vitd-serum-iu", analyte="25-hydroxyvitamin-d", a="iu_concentration", b="*",
         example=("IU/mL", "ng/mL"),
         reason="IU are used for vitamin D intake and doses. Serum 25-hydroxyvitamin D is reported in ng/mL or "
                "nmol/L; there is no IU concentration for it.",
         sources=["iom-2011-vitd"]),
]

ARBITRARY_REASON = ("Arbitrary (assay-defined) units are not commensurable with any other unit; results in "
                    "different arbitrary units, or from different assays, cannot be converted.")


def pubchem_cids():
    cids = set()
    for a in ANALYTES:
        for k in ("mm", "mm_check", "bun", "creat_denominator"):
            v = a.get(k)
            if v and v[0] == "pubchem":
                cids.add(v[1])
    cids.update([644280, 5710148, 135398561])  # reverse T3, 25(OH)D2, L-methylfolate (cited in caveats)
    return sorted(cids)
