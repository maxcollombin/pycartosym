"""CartoSym-JSON schema test documents from cartosym-draft-check.

`tests/data/cartosym_schema_cases.json` holds the Part 1 test documents of
cartosym-draft-check (https://github.com/henrik716/cartosym-draft-check, MIT),
each with the outcome expected for the revised schema of
opengeospatial/cartographic-symbology#188. Change the cases in that repository
and export them again, not here.

What is tested: the models read every valid document, the bundled schema
accepts it, and the bundled schema rejects every invalid document. The models
are not tested on the invalid documents: they convert, they do not validate.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

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


def _validator() -> Any:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _id(case: dict[str, Any]) -> str:
    return f"{case['set']}: {case['name']}"


@pytest.mark.parametrize("case", _VALID, ids=_id)
def test_models_read_a_valid_document(case):
    Style.from_dict(case["document"])


@pytest.mark.parametrize("case", _VALID, ids=_id)
def test_bundled_schema_accepts_a_valid_document(case):
    assert _validator().is_valid(case["document"])


_INVALID: list[dict[str, Any]] = [
    c
    for c in json.loads(gzip.decompress(_DATA.read_bytes()))["cases"]
    if not c["valid"]
]


@pytest.mark.parametrize("case", _INVALID, ids=_id)
def test_bundled_schema_rejects_an_invalid_document(case):
    assert not _validator().is_valid(case["document"])
