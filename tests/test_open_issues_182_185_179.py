"""Regressions: dashOffset, unit dashPattern, label priority, Dot colour, rule name."""

import logging

import pytest

from pycartosym.converter import Converter


def _symbolizer(css: str) -> dict:
    return Converter().cscss_to_csjson(css)["stylingRules"][0]["symbolizer"]


def _roundtrip(css: str) -> dict:
    converter = Converter()
    style = converter.cscss_to_csjson(css)
    return converter.cscss_to_csjson(converter.csjson_to_cscss(style))


def test_dash_offset_is_kept():
    stroke = _symbolizer("R { stroke: { width: 2 px; dashOffset: 4 px }; }")["stroke"]
    assert stroke["dashOffset"] == {"px": 4.0}


def test_dash_offset_without_unit_is_kept():
    stroke = _symbolizer("R { stroke: { dashPattern: [ 8, 4 ]; dashOffset: 4 }; }")
    assert stroke["stroke"]["dashOffset"] == 4


def test_dash_pattern_with_units(caplog):
    with caplog.at_level(logging.WARNING):
        stroke = _symbolizer(
            "R { stroke: { width: 2 px; dashPattern: [ 8 px, 4 mm ] }; }"
        )["stroke"]
    assert stroke["dashPattern"] == [{"px": 8}, {"mm": 4}]
    assert "cannot parse" not in caplog.text


def test_plain_dash_pattern_stays_integers():
    stroke = _symbolizer("R { stroke: { dashPattern: [ 8, 4 ] }; }")["stroke"]
    assert stroke["dashPattern"] == [8, 4]


def test_dash_pattern_and_offset_roundtrip():
    css = (
        "R { stroke: { width: 2 px; dashPattern: [ 8 px, 4 mm ]; dashOffset: 3 px }; }"
    )
    original = Converter().cscss_to_csjson(css)
    assert _roundtrip(css) == original


def test_label_priority_identifier_is_a_property():
    label = _symbolizer(
        "P { label: { elements: [ Text { text: name } ]; "
        "placement: { priority: elevation } }; }"
    )["label"]
    assert label["placement"]["priority"] == {"property": "elevation"}


def test_label_priority_number_stays_a_number():
    label = _symbolizer(
        "P { label: { elements: [ Text { text: name } ]; "
        "placement: { priority: 3 } }; }"
    )["label"]
    assert label["placement"]["priority"] == 3


def test_dot_color_is_rgb():
    marker = _symbolizer(
        "H { marker: { elements: [ Dot { size: 5 px, color: #b8322a } ] }; }"
    )["marker"]
    assert marker["elements"][0]["color"] == [184, 50, 42]


@pytest.mark.parametrize("written", ["It''s", "It\\'s"])
def test_rule_name_escaped_quote_is_unescaped(written):
    style = Converter().cscss_to_csjson(f"A {{\n  .name '{written}'\n}}\n")
    assert style["stylingRules"][0]["name"] == "It's"


def test_rule_name_is_written_back_escaped():
    css = "A {\n  .name 'It''s'\n}\n"
    assert _roundtrip(css)["stylingRules"][0]["name"] == "It's"
