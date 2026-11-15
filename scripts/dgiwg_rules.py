"""Convert the DGIWG Portrayal Registry rules to CartoSym selectors.

The registry exposes, for each portrayal rule, its feature type, geometry type
and condition, but not the symbol or colour it applies. Each valid rule is
therefore written as a styling rule with a selector only: the feature type as
data layer and the condition as a CQL2 expression, with the rule title as name.

Usage: ``uv run python scripts/dgiwg_rules.py [--out-dir examples/dgiwg]``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from dgiwg_colours import API, fetch_items  # noqa: E402

from pycartosym.converter import Converter  # noqa: E402
from pycartosym.parser import CartoSymParser  # noqa: E402

# An identifier on the right of a comparison is an enumeration value, not a
# property: write it as a string.
_ENUM_RE = re.compile(r"(<>|<=|>=|=|<|>)\s*([A-Za-z_][A-Za-z0-9_]*)\b")
_KEEP = {"true", "false", "null"}


def quote_enumerations(condition: str) -> str:
    """Write the unquoted enumeration values of a condition as strings."""

    def _quote(match: re.Match[str]) -> str:
        word = match.group(2)
        if word.lower() in _KEEP:
            return match.group(0)
        return f"{match.group(1)} '{word}'"

    return _ENUM_RE.sub(_quote, condition)


def condition_of(props: dict[str, Any]) -> str | None:
    """Return the condition, ``""`` when there is none, ``None`` if not an expression.

    Some conditions mix an expression with prose in braces, for example
    ``( a < 46 ) { AND ( The feature is located entirely within a waterbody ) }``.
    They cannot be written as a selector.
    """
    condition = (props.get("conditionExpr") or "").strip()
    if condition == "{ feature }":
        return ""
    return None if "{" in condition else condition


def _layer(props: dict[str, Any]) -> str:
    feature_type = props.get("featureType") or {}
    return feature_type.get("alphaName") or "Feature"


def _string(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def rule_to_cscss(feature: dict[str, Any]) -> str:
    """Write one registry rule as a styling rule with a selector only."""
    props = feature["properties"]
    condition = condition_of(props) or ""
    selector = _layer(props)
    if condition:
        selector += f" [{quote_enumerations(condition)}]"
    info = f"{feature['id']} | {props.get('geometryType')}"
    return (
        f"/* {info} - {props['externalId']} */\n"
        f"{selector} {{\n  .name {_string(props['title'])}\n}}"
    )


def to_cscss(features: list[dict[str, Any]], date: str = "") -> str:
    """Write the rules as CartoSym-CSS styling rules.

    Rules whose condition is not an expression are left out.
    """
    features = [f for f in features if condition_of(f["properties"]) is not None]
    source = f"{API}/collections/rule" + (f", read on {date}" if date else "")
    header = (
        "/* DGIWG Portrayal Registry - portrayal rules (valid), selectors only */\n"
        f"/* Source: {source} */\n"
    )
    return header + "\n" + "\n\n".join(rule_to_cscss(f) for f in features) + "\n"


def split_valid(
    features: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Split the rules into those that parse as CartoSym-CSS and the skipped codes.

    A few registry conditions are malformed (unbalanced parentheses, ``OROR``).
    """
    parser = CartoSymParser()
    kept: list[dict[str, Any]] = []
    skipped: list[str] = []
    for feature in features:
        if condition_of(feature["properties"]) is None:
            skipped.append(feature["id"])
            continue
        try:
            parser.parse_string_to_pydantic(rule_to_cscss(feature))
        except Exception:  # noqa: BLE001 - any parse error means "not a selector"
            skipped.append(feature["id"])
        else:
            kept.append(feature)
    return kept, skipped


def _write(out_dir: Path) -> None:
    """Write ``dgiwg-rules.cscss`` and ``dgiwg-rules.cs.json``."""
    features, skipped = split_valid(fetch_items("rule"))
    sys.stderr.write(f"{len(features)} rules written, {len(skipped)} skipped\n")
    cscss = to_cscss(features, datetime.date.today().isoformat())
    csjson = Converter().cscss_to_csjson(cscss)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dgiwg-rules.cscss").write_text(cscss, encoding="utf-8")
    (out_dir / "dgiwg-rules.cs.json").write_text(
        json.dumps(csjson, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Write ``dgiwg-rules.cscss`` and ``dgiwg-rules.cs.json``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("examples/dgiwg"))
    args = parser.parse_args()
    _write(args.out_dir)


if __name__ == "__main__":
    main()
