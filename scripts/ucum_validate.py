"""Minimal UCUM syntax validator (build-time only).

Implements the case-sensitive UCUM grammar (UCUM 2.2, §1-§9 "Syntax rules"):
  main-term  := "/" term | term
  term       := component (("." | "/") component)*
  component  := annotatable annotation? | annotation | factor | "(" term ")"
  annotatable:= simple-unit exponent?
  simple-unit:= ATOM | PREFIX METRIC-ATOM
Atoms and prefixes are read from ucum-essence.xml (not redistributed).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://unitsofmeasure.org/ucum-essence}"


def load_essence(path: Path) -> dict:
    root = ET.parse(path).getroot()
    prefixes = {p.get("Code") for p in root.iter(NS + "prefix")}
    atoms = {}
    for b in root.iter(NS + "base-unit"):
        atoms[b.get("Code")] = True
    for u in root.iter(NS + "unit"):
        atoms[u.get("Code")] = u.get("isMetric") == "yes"
    return {"prefixes": prefixes, "atoms": atoms, "version": root.get("version")}


def _simple(sym: str, ess: dict) -> bool:
    if sym in ess["atoms"]:
        return True
    for n in (2, 1):
        if len(sym) > n and sym[:n] in ess["prefixes"]:
            rest = sym[n:]
            if ess["atoms"].get(rest) is True:
                return True
    return False


def _component_symbol(tok: str, ess: dict) -> bool:
    if re.fullmatch(r"\d+", tok):
        return True  # factor
    if _simple(tok, ess):
        return True
    m = re.fullmatch(r"(.*?)([+-]?\d+)", tok)
    return bool(m and m.group(1) and _simple(m.group(1), ess))


def validate(code: str, ess: dict) -> tuple[bool, str]:
    if not code or any(ord(c) < 33 or ord(c) > 126 for c in code):
        return False, "empty or non-ASCII/space character"
    i, n = 0, len(code)
    depth = 0
    expect_component = True
    if code.startswith("/"):
        i = 1
    while i < n:
        c = code[i]
        if expect_component:
            if c == "(":
                depth += 1
                i += 1
                continue
            if c == "{":
                j = code.find("}", i)
                if j < 0 or "{" in code[i + 1:j]:
                    return False, "bad annotation"
                i = j + 1
                expect_component = False
                continue
            # symbol run (square brackets may contain any char except brackets)
            j = i
            while j < n and code[j] not in ".()/{}":
                if code[j] == "[":
                    k = code.find("]", j)
                    if k < 0:
                        return False, "unclosed ["
                    j = k + 1
                else:
                    j += 1
            tok = code[i:j]
            if not tok or not _component_symbol(tok, ess):
                return False, f"unknown symbol {tok!r}"
            i = j
            if i < n and code[i] == "{":
                k = code.find("}", i)
                if k < 0:
                    return False, "bad annotation"
                i = k + 1
            expect_component = False
        else:
            if c == ")":
                depth -= 1
                if depth < 0:
                    return False, "unbalanced )"
                i += 1
                continue
            if c in "./":
                expect_component = True
                i += 1
                continue
            return False, f"unexpected {c!r}"
    if depth != 0 or expect_component:
        return False, "incomplete term"
    return True, "ok"


if __name__ == "__main__":
    import sys
    ess = load_essence(Path(sys.argv[1]))
    for c in sys.argv[2:]:
        print(c, validate(c, ess))
