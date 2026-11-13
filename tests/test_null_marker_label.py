"""``marker`` / ``label`` set to ``null``, to ``{ }`` or to an empty element list.

An explicit ``null`` unsets the default Marker (or Label), ``{ }`` brings the
default back (replacing an inherited value), and ``{ elements: [] }`` has no
graphic. None of them is the same as an absent property, so none may be lost
by a conversion.
"""

import json
from pathlib import Path

import pytest
from jsonschema import validate as jsonschema_validate

import pycartosym
from pycartosym.converter import Converter
from pycartosym.models.styles import Style

_SCHEMA_FILE = (
    Path(pycartosym.__file__).parent / "schemas" / "CartoSym-JSON.schema.json"
)
SCHEMA = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))

# (CartoSym-CSS value, CS-JSON value)
FORMS = [
    ("null", None),
    ("{ }", {}),
    ("{ elements: []; }", {"elements": []}),
]


def _symbolizer(cscss: str) -> dict:
    rule = Converter().cscss_to_csjson(cscss)["stylingRules"][0]
    return rule.get("symbolizer", {})


@pytest.mark.parametrize("prop", ["marker", "label"])
@pytest.mark.parametrize(("text", "value"), FORMS)
def test_cscss_to_json_keeps_the_form(prop, text, value):
    assert _symbolizer(f"A {{ {prop}: {text}; }}") == {prop: value}


@pytest.mark.parametrize("prop", ["marker", "label"])
def test_cscss_to_json_keeps_other_properties_next_to_null(prop):
    symbolizer = _symbolizer(f"A {{ opacity: 1; {prop}: null; }}")
    assert symbolizer == {"opacity": 1.0, prop: None}


@pytest.mark.parametrize("prop", ["marker", "label"])
@pytest.mark.parametrize(("_text", "value"), FORMS)
def test_json_to_cscss_writes_the_form(prop, _text, value):
    data = {"stylingRules": [{"symbolizer": {prop: value}}]}
    written = " ".join(Converter().csjson_to_cscss(data).split())
    expected = {
        None: f"{prop}: null;",
        "{}": f"{prop}: {{ }};",
        '{"elements": []}': f"{prop}: {{elements: []}};",
    }[json.dumps(value) if value is not None else None]
    assert expected in written


@pytest.mark.parametrize("prop", ["marker", "label"])
@pytest.mark.parametrize(("text", "_value"), FORMS)
def test_cscss_round_trip_is_stable(prop, text, _value):
    converter = Converter()
    first = converter.cscss_to_csjson(f"A {{ opacity: 1; {prop}: {text}; }}")
    second = converter.cscss_to_csjson(converter.csjson_to_cscss(first))
    assert second == first


@pytest.mark.parametrize("prop", ["marker", "label"])
def test_an_absent_property_stays_absent(prop):
    converter = Converter()
    data = converter.cscss_to_csjson("A { opacity: 1; }")
    assert prop not in data["stylingRules"][0]["symbolizer"]
    assert prop not in converter.csjson_to_cscss(data)


def test_null_in_a_nested_rule_unsets_the_parent_marker():
    cscss = (
        "A { marker: { elements: [ Dot(size: 4 px; color: red) ] };"
        " [level < 4] { marker: null; } }"
    )
    rule = Converter().cscss_to_csjson(cscss)["stylingRules"][0]
    assert rule["symbolizer"]["marker"]["elements"]
    assert rule["nestedRules"][0]["symbolizer"] == {"marker": None}


@pytest.mark.parametrize("prop", ["marker", "label"])
@pytest.mark.parametrize(("_text", "value"), FORMS)
def test_style_model_keeps_the_form_when_dumped(prop, _text, value):
    style = Style.from_dict({"stylingRules": [{"symbolizer": {prop: value}}]})
    assert style.to_dict()["stylingRules"][0]["symbolizer"] == {prop: value}


@pytest.mark.parametrize("prop", ["marker", "label"])
@pytest.mark.parametrize(("_text", "value"), FORMS)
def test_bundled_schema_accepts_the_forms(prop, _text, value):
    jsonschema_validate(
        {"stylingRules": [{"symbolizer": {prop: value}}]}, schema=SCHEMA
    )
