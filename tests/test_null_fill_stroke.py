"""``fill`` / ``stroke`` set to ``null``: the entity is not drawn by that property.

An explicit ``null`` is not the same as an absent property (a rule that does not
mention ``fill`` leaves a fill inherited from a parent rule or an earlier pass
alone), so no conversion may lose it.
"""

import json
from pathlib import Path

import pytest
from jsonschema import validate as jsonschema_validate

import pycartosym
from pycartosym.converter import Converter

_SCHEMA_FILE = (
    Path(pycartosym.__file__).parent / "schemas" / "CartoSym-JSON.schema.json"
)
SCHEMA = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))


def _symbolizer(cscss: str) -> dict:
    rule = Converter().cscss_to_csjson(cscss)["stylingRules"][0]
    return rule.get("symbolizer", {})


@pytest.mark.parametrize("prop", ["fill", "stroke"])
def test_cscss_to_json_keeps_null(prop):
    assert _symbolizer(f"A {{ {prop}: null; }}") == {prop: None}


def test_cscss_to_json_keeps_the_base_rule_of_issue_207():
    symbolizer = _symbolizer("A { zOrder: 3; fill: null; stroke: null; marker: null; }")
    assert symbolizer == {"zOrder": 3, "fill": None, "stroke": None, "marker": None}


def test_cscss_to_json_keeps_a_fill_next_to_a_null_stroke():
    symbolizer = _symbolizer("A { fill: { color: #ff0000 }; stroke: null; }")
    assert symbolizer == {"fill": {"color": [255, 0, 0]}, "stroke": None}


@pytest.mark.parametrize("prop", ["fill", "stroke"])
def test_an_absent_property_stays_absent(prop):
    assert prop not in _symbolizer("A { opacity: 1; }")


@pytest.mark.parametrize("prop", ["fill", "stroke"])
def test_json_null_is_valid_and_written_back(prop):
    data = {"stylingRules": [{"symbolizer": {prop: None}}]}
    jsonschema_validate(data, SCHEMA)
    written = " ".join(Converter().csjson_to_cscss(data).split())
    assert f"{prop}: null;" in written


def test_cscss_roundtrip_keeps_null():
    converter = Converter()
    data = converter.cscss_to_csjson("A { fill: null; stroke: null; }")
    text = converter.csjson_to_cscss(data)
    assert converter.cscss_to_csjson(text) == data


@pytest.mark.parametrize("prop", ["fill", "stroke"])
def test_a_null_graphic_element_fill_or_stroke_is_still_rejected(prop):
    """Only the symbolizer's own ``fill`` / ``stroke`` take ``null``."""
    from jsonschema import ValidationError

    data = {
        "stylingRules": [
            {
                "symbolizer": {
                    "marker": {
                        "elements": [{"type": "Shape", "shape": "circle", prop: None}]
                    }
                }
            }
        ]
    }
    with pytest.raises(ValidationError):
        jsonschema_validate(data, SCHEMA)
