"""Core engine for lifefrom-units. Pure Python, no runtime dependencies.

All data (unit spellings, scales, analyte bridges, forbidden pairs, sources) comes from
``units.json``, the same file the TypeScript package uses.
"""
from __future__ import annotations

import json
import math
import re
from collections import deque
from importlib import resources
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ._rules import compile_rules, unit_key

Number = Union[int, float]

__all__ = [
    "LifeFromUnitsError", "UnknownUnitError", "UnknownAnalyteError", "IncompatibleUnitsError",
    "ForbiddenConversionError", "NoSourcedConversionError", "InvalidValueError", "AmbiguousValueError",
    "AmbiguousUnitError", "QualifiedValueError", "normalize_unit", "unit_info", "parse_value", "parse_result", "convert",
    "convert_result", "same_unit", "explain", "analytes", "SPEC",
]


# ---------------------------------------------------------------------------
# Errors. Each has a stable ``code`` shared with the TypeScript package.
# ---------------------------------------------------------------------------
class LifeFromUnitsError(ValueError):
    """Base class for every error raised by lifefrom-units."""

    code = "error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = details


class UnknownUnitError(LifeFromUnitsError):
    """The unit string is not in the lifefrom-units spelling table."""

    code = "unknown_unit"


class UnknownAnalyteError(LifeFromUnitsError):
    """The analyte is neither a lifefrom-units analyte id nor a known marker slug."""

    code = "unknown_analyte"


class IncompatibleUnitsError(LifeFromUnitsError):
    """The units measure different quantities and no analyte was given to bridge them."""

    code = "incompatible_units"


class ForbiddenConversionError(LifeFromUnitsError):
    """The conversion must not be done (for example Lp(a) mg/dL to nmol/L)."""

    code = "forbidden"


class NoSourcedConversionError(LifeFromUnitsError):
    """The analyte is known but lifefrom-units has no sourced factor between these quantities."""

    code = "no_sourced_conversion"


class InvalidValueError(LifeFromUnitsError):
    """The value is not a finite number (for example '<5' or 'positive')."""

    code = "invalid_value"


class QualifiedValueError(LifeFromUnitsError):
    """The value carries a qualifier ('<5', '>1000', '5.4 H'). Use parse_result / convert_result."""

    code = "qualified_value"


class AmbiguousValueError(LifeFromUnitsError):
    """The value could be read two ways (for example '1,234': 1.234 or 1234)."""

    code = "ambiguous_value"


class AmbiguousUnitError(LifeFromUnitsError):
    """The unit spelling means different units in different languages ('mil/mm3': thousand in Spanish,
    million in English). Pass ``locale=`` (for example ``"es"``) to say which convention the report follows."""

    code = "ambiguous_unit"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _load_spec() -> Dict[str, Any]:
    text = resources.files("lifefrom_units").joinpath("units.json").read_text(encoding="utf-8")
    return json.loads(text)


SPEC: Dict[str, Any] = _load_spec()


_RULES = compile_rules(SPEC["normalization"]["rules"])
_UNITS: Dict[str, Dict[str, Any]] = {u["unit"]: u for u in SPEC["units"]}
_EXACT: Dict[str, str] = SPEC["lookup"]["exact"]
_FOLDED: Dict[str, str] = SPEC["lookup"]["casefold"]
_AMBIG_KEYS: Dict[str, str] = SPEC["lookup"].get("ambiguous", {})
_AMBIG: Dict[str, Dict[str, Any]] = {a["id"]: a for a in SPEC.get("ambiguous", [])}
_READINGS: Dict[str, Dict[str, Any]] = SPEC.get("language_readings", {})
_ANALYTES: Dict[str, Dict[str, Any]] = {a["id"]: a for a in SPEC["analytes"]}
_ANALYTE_INDEX: Dict[str, str] = SPEC["lookup"]["analytes"]
_SOURCES: Dict[str, Dict[str, Any]] = SPEC["sources"]


def _key(text: str) -> str:
    return unit_key(text, _RULES)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_LANG = re.compile(r"^([A-Za-z]{2,3})(?:[-_][A-Za-z0-9]{1,8})*$")


def _language(locale: Optional[str]) -> Optional[str]:
    """'es', 'es-AR', 'es_MX', 'ES' -> 'es'. None -> None."""
    if locale is None:
        return None
    m = _LANG.match(locale.strip()) if isinstance(locale, str) else None
    if not m:
        raise InvalidValueError(f"locale must be a language tag such as 'es' or 'es-AR', got {locale!r}",
                                locale=locale)
    return m.group(1).lower()


def _lookup_read(unit: str, locale: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Resolve a spelling to its unit record, plus the reading used when the spelling is ambiguous."""
    lang = _language(locale)
    if not isinstance(unit, str) or not unit.strip():
        raise UnknownUnitError("empty unit", unit=unit)
    k = _key(unit)
    canon = _EXACT.get(k)
    if canon is not None:
        return _UNITS[canon], None
    kf = _key(unit.lower())
    aid = _AMBIG_KEYS.get(kf)
    if aid is not None:
        a = _AMBIG[aid]
        langs = sorted(a["readings"])
        if lang is None or lang not in a["readings"]:
            why = ("no locale given" if lang is None else
                   f"no reading for locale {locale!r}")
            raise AmbiguousUnitError(
                f"ambiguous unit {unit!r} ({why}): {a['reason']} Pass a locale (one of {', '.join(langs)}).",
                unit=unit, ambiguity=aid, locale=locale, readings=dict(a["readings"]), reason=a["reason"])
        r = _READINGS[lang]
        canon = a["readings"][lang]
        return _UNITS[canon], {"spelling": unit, "unit": canon, "locale": lang, "meaning": r["meaning"],
                               "note": r["note"], "sources": r["sources"]}
    canon = _FOLDED.get(kf)
    if canon is None:
        raise UnknownUnitError(f"unknown unit: {unit!r}", unit=unit)
    return _UNITS[canon], None


def _lookup(unit: str, locale: Optional[str] = None) -> Dict[str, Any]:
    return _lookup_read(unit, locale)[0]


def _reading_step(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"kind": "spelling_reading",
            "description": f"'{r['spelling']}' read as {r['unit']} ('mil' = {r['meaning']}, locale '{r['locale']}')",
            "basis": r["note"], "sources": _source_list(r["sources"])}


def normalize_unit(unit: str, locale: Optional[str] = None) -> str:
    """Return the canonical spelling of a unit string.

    Handles µ/u/mc/Greek mu, superscripts, ×10⁹/L-style powers, UI/IU, case, and spacing.
    Numerically equal units keep their own spelling (``K/µL`` -> ``10^3/µL``, ``/nL`` stays
    ``/nL``); use :func:`same_unit` to compare them.

    >>> normalize_unit("ug/l")
    'µg/L'
    >>> normalize_unit("x10E9/L")
    '10^9/L'
    >>> normalize_unit("mil/mm3", locale="es")
    '10^3/mm³'

    ``locale`` (optional, a language tag such as ``"es"``, ``"en-US"`` or ``"ro"``) is used only for
    spellings that mean different units in different languages: ``mil/mm3`` and ``mil/µL`` are thousands
    in Spanish (``es``) and millions on English (``en``) and Romanian (``ro``) reports. Without a locale
    these raise :class:`AmbiguousUnitError`. Unambiguous spellings (``mill/mm3``, ``millones/mm3``,
    ``Million/µL``, ``mii/µL``, ``K/µL``, ``10^6/µL``) ignore it.

    Raises :class:`UnknownUnitError` if the spelling is not known.
    """
    return _lookup(unit, locale)["unit"]


def unit_info(unit: str, locale: Optional[str] = None) -> Dict[str, Any]:
    """Return the record for a unit: canonical spelling, dimension, scale to the base unit, UCUM code."""
    u = _lookup(unit, locale)
    return {"unit": u["unit"], "dimension": u["dimension"], "scale": u["scale"], "ucum": u.get("ucum")}


_SEP_SPACES = re.compile(r"(?<=\d)[ \u00a0\u2009\u202f'](?=\d)")
_NUM = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


_COMPARATOR = re.compile(r"^\s*(<=|>=|=<|=>|≤|≥|<|>)\s*")
_FLAG = re.compile(r"\s*(?:\(\s*(HH|LL|H|L|A|AA)\s*\)|\[\s*(HH|LL|H|L|A|AA)\s*\]|(HH|LL|H|L|A|AA|↑|↓|\*|!))\s*$",
                   re.IGNORECASE)
_CMP_NORMAL = {"<": "<", ">": ">", "<=": "<=", ">=": ">=", "=<": "<=", "=>": ">=", "≤": "<=", "≥": ">="}


def _split_qualifiers(text: str) -> Tuple[Optional[str], str, Optional[str]]:
    """Split '<5' / '5,4 H' into (comparator, number text, flag). No qualifier -> (None, text, None)."""
    comparator = None
    flag = None
    s = text.strip()
    m = _COMPARATOR.match(s)
    if m:
        comparator = _CMP_NORMAL[m.group(1)]
        s = s[m.end():]
    m = _FLAG.search(s)
    if m and m.start() > 0 and re.search(r"[0-9.]", s[:m.start()]):
        flag = next(g for g in m.groups() if g).upper()
        s = s[:m.start()]
    return comparator, s.strip(), flag


def parse_result(value: Union[Number, str]) -> Dict[str, Any]:
    """Parse a reported value that may carry a comparator or an abnormal flag.

    Returns ``{"value", "comparator", "flag", "text"}``. ``comparator`` is one of ``<``, ``>``,
    ``<=``, ``>=`` or None; ``flag`` is the lab's flag as printed (``H``, ``L``, ``HH``, ``LL``,
    ``A``, ``AA``, ``↑``, ``↓``, ``*``, ``!``; letters upper-cased) or None. The number part follows
    :func:`parse_value` (decimal commas accepted).

    >>> parse_result("<5")["comparator"], parse_result("5,4 L")["flag"]
    ('<', 'L')
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"value": parse_value(value), "comparator": None, "flag": None, "text": str(value)}
    if not isinstance(value, str):
        raise InvalidValueError(f"unsupported value type: {type(value).__name__}", value=value)
    comparator, num, flag = _split_qualifiers(value)
    return {"value": _parse_number(num, value), "comparator": comparator, "flag": flag, "text": value}


def parse_value(value: Union[Number, str]) -> float:
    """Parse a number, accepting a decimal comma.

    ``"5,4"`` -> 5.4; ``"1.234,5"`` -> 1234.5; ``"1,234.5"`` -> 1234.5. A single comma followed by
    exactly three digits (``"1,234"``) is ambiguous and raises :class:`AmbiguousValueError`.
    Values with a comparator or flag (``"<5"``, ``"5,4 H"``) raise :class:`QualifiedValueError` so the
    qualifier is never dropped silently: use :func:`parse_result`. Words raise :class:`InvalidValueError`.
    """
    if isinstance(value, bool):
        raise InvalidValueError("boolean is not a value", value=value)
    if isinstance(value, (int, float)):
        v = float(value)
        if not math.isfinite(v):
            raise InvalidValueError("value is not finite", value=value)
        return v
    if not isinstance(value, str):
        raise InvalidValueError(f"unsupported value type: {type(value).__name__}", value=value)
    comparator, num, flag = _split_qualifiers(value)
    if comparator or flag:
        _parse_number(num, value)  # a malformed number is reported as such
        raise QualifiedValueError(
            f"value {value!r} has a qualifier ({comparator or flag}); use parse_result()/convert_result() "
            "so it is kept", value=value, comparator=comparator, flag=flag)
    return _parse_number(value, value)


def _parse_number(text: str, value: Any) -> float:
    s = text.strip().replace("\u2212", "-")
    s = _SEP_SPACES.sub("", s)
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        int_part, _, frac = s.rpartition(dec)
        groups = int_part.lstrip("+-").split(thou)
        if len(groups) < 2 or not all(len(g) == 3 for g in groups[1:]) or not (1 <= len(groups[0]) <= 3):
            raise AmbiguousValueError(f"cannot read {value!r}: mixed separators", value=value)
        s = int_part.replace(thou, "") + "." + frac
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2:
            head = parts[0].lstrip("+-")
            if len(parts[1]) == 3 and parts[1].isdigit() and head.isdigit() and 1 <= len(head) <= 3 and head != "0":
                raise AmbiguousValueError(
                    f"cannot read {value!r}: the comma may be a decimal or a thousands separator", value=value)
            s = parts[0] + "." + parts[1]
        else:
            head = parts[0].lstrip("+-")
            if all(len(p) == 3 for p in parts[1:]) and 1 <= len(head) <= 3:
                s = "".join(parts)
            else:
                raise InvalidValueError(f"cannot read {value!r}", value=value)
    elif s.count(".") > 1:
        parts = s.split(".")
        head = parts[0].lstrip("+-")
        if all(len(p) == 3 for p in parts[1:]) and 1 <= len(head) <= 3:
            s = "".join(parts)
        else:
            raise InvalidValueError(f"cannot read {value!r}", value=value)
    if not _NUM.fullmatch(s):
        raise InvalidValueError(f"not a number: {value!r}", value=value)
    v = float(s)
    if not math.isfinite(v):
        raise InvalidValueError("value is not finite", value=value)
    return v


def _resolve_analyte(analyte: Optional[str]) -> Optional[Dict[str, Any]]:
    if analyte is None:
        return None
    if not isinstance(analyte, str) or not analyte.strip():
        raise UnknownAnalyteError("empty analyte", analyte=analyte)
    aid = _ANALYTE_INDEX.get(analyte.strip().lower())
    if aid is None:
        raise UnknownAnalyteError(f"unknown analyte: {analyte!r}", analyte=analyte)
    return _ANALYTES[aid]


def analytes() -> List[Dict[str, Any]]:
    """List lifefrom-units analytes: id, name, marker slugs, and whether they have conversions."""
    return [{"id": a["id"], "name": a["name"], "marker_slugs": list(a["marker_slugs"]),
             "has_conversions": bool(a["bridges"])} for a in SPEC["analytes"]]


def _source_list(ids: Sequence[str]) -> List[Dict[str, Any]]:
    out = []
    for i in ids:
        s = dict(_SOURCES[i])
        s["id"] = i
        out.append(s)
    return out


def _forbidden_match(f: Dict[str, Any], ua: Dict[str, Any], ub: Dict[str, Any]) -> bool:
    def side(dim_spec: str, units: Optional[List[str]], u: Dict[str, Any]) -> bool:
        if dim_spec != "*" and dim_spec != u["dimension"]:
            return False
        return units is None or u["unit"] in units

    a_units, b_units = f.get("a_units"), f.get("b_units")
    return (side(f["a"], a_units, ua) and side(f["b"], b_units, ub)) or \
           (side(f["a"], a_units, ub) and side(f["b"], b_units, ua))


def _raise_forbidden(f: Dict[str, Any], ua: Dict[str, Any], ub: Dict[str, Any]) -> None:
    raise ForbiddenConversionError(
        f"{ua['unit']} -> {ub['unit']}: {f['reason']}", rule=f["id"], reason=f["reason"],
        sources=_source_list(f["sources"]))


def _plan(from_unit: str, to_unit: str, analyte: Optional[str], locale: Optional[str] = None) -> Dict[str, Any]:
    """Work out the affine map y = a*x + b from from_unit to to_unit, with its steps and sources."""
    ua, ra = _lookup_read(from_unit, locale)
    ub, rb = _lookup_read(to_unit, locale)
    p = _plan_units(ua, ub, analyte)
    reads = [_reading_step(r) for r in (ra, rb) if r is not None]
    if reads:
        p["steps"] = reads + p["steps"]
    return p


def _plan_units(ua: Dict[str, Any], ub: Dict[str, Any], analyte: Optional[str]) -> Dict[str, Any]:
    an = _resolve_analyte(analyte)
    base = {"from_unit": ua["unit"], "to_unit": ub["unit"], "analyte": an["id"] if an else None}
    da, db = ua["dimension"], ub["dimension"]

    if an is not None:
        for f in SPEC["forbidden"]:
            if f["analyte"] == an["id"] and _forbidden_match(f, ua, ub):
                _raise_forbidden(f, ua, ub)

    if ua["unit"] == ub["unit"]:
        return dict(base, a=1.0, b=0.0, kind="identity",
                    steps=[{"kind": "identity", "description": "same unit", "sources": []}])

    if da.startswith("arbitrary:") or db.startswith("arbitrary:"):
        raise ForbiddenConversionError(
            f"{ua['unit']} -> {ub['unit']}: {SPEC['arbitrary_reason']}", rule="arbitrary-units",
            reason=SPEC["arbitrary_reason"], sources=_source_list(["ucum-2.2"]))

    if da == db:
        a = ua["scale"] / ub["scale"]
        return dict(base, a=a, b=0.0, kind="unit_arithmetic", steps=[{
            "kind": "unit_arithmetic", "factor": a,
            "description": f"same quantity ({SPEC['dimensions'][da]['name']}); factor from unit prefixes",
            "basis": "derived: unit arithmetic", "sources": []}])

    def generic_forbidden() -> None:
        for f in SPEC["forbidden"]:
            if f["analyte"] is None and _forbidden_match(f, ua, ub):
                _raise_forbidden(f, ua, ub)

    if an is None:
        generic_forbidden()
        raise IncompatibleUnitsError(
            f"{ua['unit']} ({da}) and {ub['unit']} ({db}) measure different quantities; "
            "pass analyte=... to convert between them", from_dimension=da, to_dimension=db)

    # Breadth-first search over the analyte's bridges between dimensions.
    edges: Dict[str, List[Tuple[str, Dict[str, Any], bool]]] = {}
    for br in an["bridges"]:
        edges.setdefault(br["from"], []).append((br["to"], br, False))
        edges.setdefault(br["to"], []).append((br["from"], br, True))
    prev: Dict[str, Tuple[str, Dict[str, Any], bool]] = {}
    seen = {da}
    q = deque([da])
    while q:
        d = q.popleft()
        if d == db:
            break
        for nd, br, inv in edges.get(d, []):
            if nd not in seen:
                seen.add(nd)
                prev[nd] = (d, br, inv)
                q.append(nd)
    if db not in seen:
        generic_forbidden()
        raise NoSourcedConversionError(
            f"no sourced conversion for {an['id']} between {ua['unit']} ({da}) and {ub['unit']} ({db})",
            analyte=an["id"], from_dimension=da, to_dimension=db)
    path = []
    d = db
    while d != da:
        p, br, inv = prev[d]
        path.append((br, inv))
        d = p
    path.reverse()

    a, b = ua["scale"], 0.0
    steps = []
    for br, inv in path:
        ba, bb = br["a"], br["b"]
        if inv:
            ba, bb = 1.0 / ba, -bb / ba
        a, b = a * ba, b * ba + bb
        steps.append({"kind": br["kind"], "description": br["description"], "basis": br["basis"],
                      "inverse": inv, "sources": _source_list(br["sources"]),
                      "reference_compound": br.get("reference_compound")})
    a, b = a / ub["scale"], b / ub["scale"]
    kinds = {s["kind"] for s in steps}
    kind = "equation" if b != 0.0 else ("analyte_factor" if kinds - {"label_equivalence"} else "label_equivalence")
    return dict(base, a=a, b=b, kind=kind, steps=steps)


def _user_factor(factor: Union[Number, str]) -> float:
    try:
        f = parse_value(factor)
    except LifeFromUnitsError:
        raise InvalidValueError(f"factor must be a positive number, got {factor!r}", factor=factor)
    if not f > 0:
        raise InvalidValueError(f"factor must be a positive number, got {factor!r}", factor=factor)
    return f


def _plan_with(from_unit: str, to_unit: str, analyte: Optional[str],
               factor: Union[Number, str, None], locale: Optional[str] = None) -> Dict[str, Any]:
    """Plan a conversion; with ``factor`` the caller's factor replaces the library's answer."""
    if factor is None:
        p = _plan(from_unit, to_unit, analyte, locale)
        p["user_factor"] = None
        p["warnings"] = []
        return p
    f = _user_factor(factor)
    ua, ra = _lookup_read(from_unit, locale)
    ub, rb = _lookup_read(to_unit, locale)
    an = _resolve_analyte(analyte)
    warnings = [f"Factor {_fmt(f)} supplied by the caller; lifefrom-units has not checked it."]
    record: Dict[str, Any] = {"value": f, "overrides": None, "library_kind": None, "library_factor": None}
    try:
        lib = _plan(from_unit, to_unit, analyte, locale)
        record["library_kind"] = lib["kind"]
        if lib["b"] != 0.0:
            warnings.append("lifefrom-units uses an equation for this pair, not a factor.")
        else:
            record["library_factor"] = lib["a"]
            if abs(lib["a"] - f) > 1e-9 * abs(lib["a"]):
                warnings.append(f"The library factor is {_fmt(lib['a'])} ({lib['kind']}); the supplied factor "
                                f"differs by {(f - lib['a']) / lib['a']:+.2%}.")
    except (IncompatibleUnitsError, ForbiddenConversionError, NoSourcedConversionError) as ex:
        record["overrides"] = ex.code
        reason = ex.details.get("reason") or str(ex)
        warnings.append(f"Overrides lifefrom-units ({ex.code}): {reason}")
    return {"from_unit": ua["unit"], "to_unit": ub["unit"], "analyte": an["id"] if an else None,
            "a": f, "b": 0.0, "kind": "user_factor", "user_factor": record, "warnings": warnings,
            "steps": [_reading_step(r) for r in (ra, rb) if r is not None] + [{"kind": "user_factor", "factor": f,
                       "description": f"factor supplied by the caller: 1 {ua['unit']} = {_fmt(f)} {ub['unit']}",
                       "basis": "caller-supplied; not checked by lifefrom-units", "sources": []}]}


def convert(value: Union[Number, str], from_unit: str, to_unit: str, analyte: Optional[str] = None,
            factor: Union[Number, str, None] = None, locale: Optional[str] = None) -> float:
    """Convert ``value`` from ``from_unit`` to ``to_unit``.

    ``analyte`` (a lifefrom-units analyte id such as ``"glucose"`` or a LifeFrom marker slug such as
    ``"glucose-fasting"``) is needed whenever the units measure different quantities, for example
    mg/dL and mmol/L.

    ``factor`` (optional, never a default) is a caller-supplied multiplier, ``value_to = value_from ×
    factor``. Use it for conversions the library refuses or cannot source, such as insulin µIU/mL to
    pmol/L with the factor your assay states. :func:`explain` records it and what it overrode.

    ``locale`` (optional language tag) says which convention the report follows for spellings that are
    ambiguous across languages; see :func:`normalize_unit`.

    >>> round(convert(100, "mg/dL", "mmol/L", analyte="glucose"), 3)
    5.551
    >>> convert("5,4", "mmol/L", "mmol/L")
    5.4
    >>> convert(10, "µIU/mL", "pmol/L", analyte="insulin", factor=6)
    60.0
    >>> convert("7,5", "mil/mm3", "10^3/µL", locale="es")
    7.5

    Raises :class:`IncompatibleUnitsError` (needs an analyte), :class:`ForbiddenConversionError`
    (never convert, e.g. Lp(a) mg/dL to nmol/L), :class:`NoSourcedConversionError`,
    :class:`UnknownUnitError`, :class:`AmbiguousUnitError` (pass ``locale=``), :class:`UnknownAnalyteError`, :class:`InvalidValueError`,
    :class:`QualifiedValueError` (use :func:`convert_result`) or :class:`AmbiguousValueError`.
    """
    v = parse_value(value)
    p = _plan_with(from_unit, to_unit, analyte, factor, locale)
    return p["a"] * v + p["b"]


FLAG_NOTE = ("The flag is copied unchanged from the original report. It refers to that laboratory's reference "
             "interval, not to anything lifefrom-units computed.")


def convert_result(value: Union[Number, str], from_unit: str, to_unit: str, analyte: Optional[str] = None,
                   factor: Union[Number, str, None] = None, locale: Optional[str] = None) -> Dict[str, Any]:
    """Convert a reported value that may carry a comparator (``<5``) or flag (``5,4 H``).

    Returns ``{"value", "comparator", "flag", "unit", "text"}`` plus ``flag_note`` when a flag is
    present. The comparator is kept (all conversions are increasing); the flag is copied unchanged.

    >>> r = convert_result("<5", "mg/dL", "mg/L")
    >>> r["comparator"], r["value"], r["unit"]
    ('<', 50.0, 'mg/L')
    """
    r = parse_result(value)
    p = _plan_with(from_unit, to_unit, analyte, factor, locale)
    out: Dict[str, Any] = {"value": p["a"] * r["value"] + p["b"], "comparator": r["comparator"], "flag": r["flag"],
                           "unit": p["to_unit"]}
    if p["a"] < 0 and out["comparator"]:  # not reachable with current data; kept for safety
        out["comparator"] = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[out["comparator"]]
    out["text"] = f"{out['comparator'] or ''}{_fmt(out['value'])}" + (f" {out['flag']}" if out["flag"] else "")
    if r["flag"]:
        out["flag_note"] = FLAG_NOTE
    return out


def same_unit(a: str, b: str, analyte: Optional[str] = None, locale: Optional[str] = None) -> bool:
    """True if a value in unit ``a`` equals the same number in unit ``b``.

    ``same_unit("µg/L", "ng/mL")`` is True. With an analyte, charge equivalence counts:
    ``same_unit("mEq/L", "mmol/L", analyte="sodium")`` is True. Unknown units raise
    :class:`UnknownUnitError` (ambiguous ones :class:`AmbiguousUnitError`); impossible or forbidden
    conversions return False.
    """
    try:
        p = _plan(a, b, analyte, locale)
    except (IncompatibleUnitsError, ForbiddenConversionError, NoSourcedConversionError):
        return False
    return p["b"] == 0.0 and abs(p["a"] - 1.0) <= 1e-12


def _fmt(x: float) -> str:
    return f"{x:.6g}"


def explain(from_unit: str, to_unit: str, analyte: Optional[str] = None,
            value: Union[Number, str, None] = None, factor: Union[Number, str, None] = None,
            locale: Optional[str] = None) -> Dict[str, Any]:
    """Explain a conversion: the factor (or equation), each step, its basis and its sources.

    Returns a dict with keys ``from_unit``, ``to_unit``, ``analyte``, ``kind`` (``identity``,
    ``unit_arithmetic``, ``label_equivalence``, ``analyte_factor``, ``equation`` or ``user_factor``),
    ``factor`` (None for equations), ``equation`` (``{"slope", "intercept", "text"}`` or None),
    ``derived`` (True when only unit arithmetic is involved), ``steps``, ``sources``,
    ``reference_compounds`` (the compound or element whose molar mass was used), ``warnings``
    (caveats that ship with the factor), ``user_factor`` (what a caller-supplied factor replaced, or
    None) and, if ``value`` is given, ``value`` and ``result``. When ``locale`` resolved an ambiguous
    spelling, a ``spelling_reading`` step comes first, with its sources. Raises the same errors as
    :func:`convert`.
    """
    p = _plan_with(from_unit, to_unit, analyte, factor, locale)
    out: Dict[str, Any] = {
        "from_unit": p["from_unit"], "to_unit": p["to_unit"], "analyte": p["analyte"], "kind": p["kind"],
        "factor": p["a"] if p["b"] == 0.0 else None,
        "equation": None,
        "derived": p["kind"] in ("identity", "unit_arithmetic"),
        "steps": p["steps"],
    }
    if p["b"] != 0.0:
        out["equation"] = {"slope": p["a"], "intercept": p["b"],
                           "text": f"{p['to_unit']} = {_fmt(p['a'])} × {p['from_unit']} "
                                   f"{'+' if p['b'] >= 0 else '-'} {_fmt(abs(p['b']))}"}
        out["text"] = out["equation"]["text"]
    else:
        out["text"] = f"1 {p['from_unit']} = {_fmt(p['a'])} {p['to_unit']}"
    seen, srcs, refs = set(), [], []
    for s in p["steps"]:
        for src in s["sources"]:
            if src["id"] not in seen:
                seen.add(src["id"])
                srcs.append(src)
        if s.get("reference_compound"):
            refs.append(s["reference_compound"])
    out["sources"] = srcs
    out["reference_compounds"] = refs
    warnings = list(p["warnings"])
    if p["analyte"] and p["kind"] not in ("identity", "unit_arithmetic"):
        warnings.extend(_ANALYTES[p["analyte"]].get("caveats") or [])
    out["warnings"] = warnings
    out["user_factor"] = p["user_factor"]
    if value is not None:
        v = parse_value(value)
        out["value"] = v
        out["result"] = p["a"] * v + p["b"]
    return out
