"""Command-line interface: ``lifefrom-units convert|normalize|same|explain|analytes``."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from .core import LifeFromUnitsError, analytes, convert_result, explain, normalize_unit, same_unit


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lifefrom-units", description="Normalise lab units and convert lab values.")
    p.add_argument("--version", action="version", version=f"lifefrom-units {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="convert a value: lifefrom-units convert 5,4 mmol/L mg/dL --analyte glucose")
    c.add_argument("value")
    c.add_argument("from_unit")
    c.add_argument("to_unit")
    c.add_argument("--analyte", "-a")
    c.add_argument("--factor", help="your own factor (value_to = value_from x factor); recorded, never a default")
    c.add_argument("--json", action="store_true", help="print the result and full explanation as JSON")

    n = sub.add_parser("normalize", help="print the canonical spelling of one or more units")
    n.add_argument("units", nargs="+")

    s = sub.add_parser("same", help="exit 0 if the two units are numerically the same, 1 if not")
    s.add_argument("a")
    s.add_argument("b")
    s.add_argument("--analyte", "-a")

    e = sub.add_parser("explain", help="show the factor or equation and its sources")
    e.add_argument("from_unit")
    e.add_argument("to_unit")
    e.add_argument("--analyte", "-a")
    e.add_argument("--factor")
    e.add_argument("--json", action="store_true")

    sub.add_parser("analytes", help="list analytes that have conversions")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "convert":
            r = convert_result(args.value, args.from_unit, args.to_unit, args.analyte, factor=args.factor)
            if args.json:
                print(json.dumps({"result": r, "explanation": explain(args.from_unit, args.to_unit, args.analyte,
                                                                      factor=args.factor)},
                                 ensure_ascii=False, indent=2))
            else:
                print(r["text"])
                if args.factor is not None:
                    print("note: factor supplied by you; not checked by lifefrom-units", file=sys.stderr)
        elif args.cmd == "normalize":
            for u in args.units:
                print(normalize_unit(u))
        elif args.cmd == "same":
            ok = same_unit(args.a, args.b, args.analyte)
            print("same" if ok else "different")
            return 0 if ok else 1
        elif args.cmd == "explain":
            ex = explain(args.from_unit, args.to_unit, args.analyte, factor=args.factor)
            if args.json:
                print(json.dumps(ex, ensure_ascii=False, indent=2))
            else:
                print(ex["text"])
                for st in ex["steps"]:
                    print(f"  - {st['description']}" + (f"  [{st['basis']}]" if st.get("basis") else ""))
                for src in ex["sources"]:
                    print(f"  source: {src['label']} <{src['url']}>")
                for w in ex["warnings"]:
                    print(f"  warning: {w}")
                if ex["derived"]:
                    print("  derived: unit arithmetic")
        elif args.cmd == "analytes":
            for a in analytes():
                if a["has_conversions"]:
                    print(f"{a['id']}\t{a['name']}\t{', '.join(a['marker_slugs'])}")
    except LifeFromUnitsError as ex:
        print(f"lifefrom-units: {ex.code}: {ex}", file=sys.stderr)
        return 2
    return 0
