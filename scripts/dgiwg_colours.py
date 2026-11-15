"""Convert the DGIWG Portrayal Registry colour register to CartoSym.

Reads the colour register through the registry's read-only OGC API - Records
interface and writes one style variable per valid colour, as CartoSym-CSS and
as CS-JSON. CMYK, CIELAB and Pantone values have no counterpart in the model;
they are kept in a comment next to each variable.

Usage: ``uv run python scripts/dgiwg_colours.py [--out-dir examples/dgiwg]``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from pycartosym.converter import Converter

API = "https://portal.dgiwg.org/public_dgiwg/registry/api"
_PAGE = 500
_NAME_RE = re.compile(r"[^A-Za-z0-9_]")


def fetch_items(collection: str, api: str = API) -> list[dict[str, Any]]:
    """Return the valid items of a register, in register order.

    The API returns at most 500 items per page, so the pages are followed.
    """
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        url = f"{api}/collections/{collection}/items?limit={_PAGE}&offset={offset}"
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            page = json.load(response)["features"]
        features += page
        if len(page) < _PAGE:
            break
        offset += _PAGE
    return [f for f in features if f["properties"]["status"] == "valid"]


def fetch_colours(api: str = API) -> list[dict[str, Any]]:
    """Return the valid colours of the register, in register order."""
    return fetch_items("colour", api)


def variable_name(feature: dict[str, Any]) -> str:
    """Name a variable after the registry code, e.g. ``CC_2101``."""
    return _NAME_RE.sub("_", feature["id"])


def _comment(props: dict[str, Any]) -> str:
    parts = [props["title"]]
    for key in ("cmyk", "cielab"):
        if props.get(key):
            parts.append(f"{key.upper()} " + " ".join(str(v) for v in props[key]))
    if props.get("pantone"):
        parts.append(f"Pantone {props['pantone']}")
    return " | ".join(parts).replace("*/", "* /")


def to_cscss(features: list[dict[str, Any]], date: str = "") -> str:
    """Write the colours as CartoSym-CSS variables."""
    source = f"{API}/collections/colour" + (f", read on {date}" if date else "")
    lines = [
        "/* DGIWG Portrayal Registry - colour register (valid colours) */",
        f"/* Source: {source} */",
        "",
    ]
    for feature in features:
        props = feature["properties"]
        lines.append(f"/* {_comment(props)} - {props['externalId']} */")
        lines.append(f"@{variable_name(feature)} = {props['hex'].lower()};")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Write ``dgiwg-colours.cscss`` and ``dgiwg-colours.cs.json``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("examples/dgiwg"))
    args = parser.parse_args()
    cscss = to_cscss(fetch_colours(), datetime.date.today().isoformat())
    csjson = Converter().cscss_to_csjson(cscss)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "dgiwg-colours.cscss").write_text(cscss, encoding="utf-8")
    (args.out_dir / "dgiwg-colours.cs.json").write_text(
        json.dumps(csjson, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
