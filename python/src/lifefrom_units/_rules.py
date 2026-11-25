"""Shared unit-spelling normalisation (no data). Used by the runtime and by scripts/build.py."""
from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

Rule = Tuple["re.Pattern[str]", str]


def compile_rules(rules: Sequence[Dict[str, str]]) -> List[Rule]:
    """Compile rules whose replacements use JavaScript-style ``$1`` group references."""
    out: List[Rule] = []
    for r in rules:
        repl = re.sub(r"\$(\d)", r"\\g<\1>", r["replacement"])
        out.append((re.compile(r["pattern"]), repl))
    return out


def unit_key(text: str, rules: Sequence[Rule]) -> str:
    """Apply the rules in order, then drop all whitespace. This is the lookup key."""
    s = text.strip()
    for pat, repl in rules:
        s = pat.sub(repl, s)
    return re.sub(r"\s+", "", s)
