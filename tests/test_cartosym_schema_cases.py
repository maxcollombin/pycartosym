"""CartoSym-JSON schema test documents from cartosym-draft-check.

`tests/data/cartosym_schema_cases.json` holds the Part 1 test documents of
cartosym-draft-check (https://github.com/henrik716/cartosym-draft-check, MIT),
each with the outcome expected for the revised schema of
opengeospatial/cartographic-symbology#188. Change the cases in that repository
and export them again, not here.

What is tested: the models read every valid document, and the bundled schema
accepts it. The documents the bundled schema rejects are the ones the revised
schema accepts; they are `xfail(strict=False)` until the bundled schema is
replaced by the revised one. The bundled schema must also reject the invalid
documents; the ones it accepts are `xfail(strict=False)` as well. The models are
not tested on the invalid documents: they convert, they do not validate.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft201909Validator, Draft202012Validator

from pycartosym.models.styles import Style

_DATA = Path(__file__).parent / "data" / "cartosym_schema_cases.json.gz"
_SCHEMA = (
    Path(__file__).parent.parent
    / "src"
    / "pycartosym"
    / "schemas"
    / "CartoSym-JSON.schema.json"
)
_VALID: list[dict[str, Any]] = [
    c for c in json.loads(gzip.decompress(_DATA.read_bytes()))["cases"] if c["valid"]
]

# Valid in the revised schema, rejected by the bundled one (until it is replaced).
_REVISED_SCHEMA_ONLY = {
    "not(true)",
    "a_containedBy(a, [1, 2])",
    "a_containedBy(['a'], a)",
    "a_contains(a, [1, 2])",
    "a_contains(['a'], a)",
    "a_equals(a, [1, 2])",
    "a_equals(['a'], a)",
    "a_overlaps(a, [1, 2])",
    "a_overlaps(['a'], a)",
    "myBool(x) as selector",
    "[myFn(x)]",
    "[[1, b]]",
    "color hex",
    "colorChannels {property}",
    "stroke dashOffset",
    "capabilities.dashes",
    "capabilities.vendor.acme.glow",
    "format with op",
    "pow as generic call",
    "notLike op (an unknown function, like any other name)",
    "LIKE upper case (an unknown function)",
    "mod",
    "intDiv",
    "graphic property and Text",
    "fill pattern property",
    "variable as selector",
}


def _validator() -> Any:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    dialect = (
        Draft202012Validator if "2020-12" in schema["$schema"] else Draft201909Validator
    )
    return dialect(schema)


def _id(case: dict[str, Any]) -> str:
    return f"{case['set']}: {case['name']}"


@pytest.mark.parametrize("case", _VALID, ids=_id)
def test_models_read_a_valid_document(case):
    Style.from_dict(case["document"])


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            c,
            marks=pytest.mark.xfail(
                c["name"] in _REVISED_SCHEMA_ONLY,
                reason="valid in the revised schema (#188), not in the bundled one",
                strict=False,
            ),
        )
        for c in _VALID
    ],
    ids=_id,
)
def test_bundled_schema_accepts_a_valid_document(case):
    assert _validator().is_valid(case["document"])


_INVALID: list[dict[str, Any]] = [
    c
    for c in json.loads(gzip.decompress(_DATA.read_bytes()))["cases"]
    if not c["valid"]
]
_BUNDLED_IS_REVISED = (
    "2020-12" in json.loads(_SCHEMA.read_text(encoding="utf-8"))["$schema"]
)


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            c,
            marks=pytest.mark.xfail(
                not _BUNDLED_IS_REVISED,
                reason="the bundled schema accepts what the revised one (#188) rejects",
                strict=False,
            ),
        )
        for c in _INVALID
    ],
    ids=_id,
)
def test_bundled_schema_rejects_an_invalid_document(case):
    assert not _validator().is_valid(case["document"])
