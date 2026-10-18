"""Stroke cap, join, dashPattern, casing and center in CartoSym-CSS."""

import pytest

from pycartosym.converter import Converter
from pycartosym.parser import CartoSymParser


def _parse(text: str) -> dict:
    return (
        CartoSymParser()
        .parse_string_to_pydantic(text)
        .to_dict()["stylingRules"][0]["symbolizer"]["stroke"]
    )


def test_block_form_reads_every_property():
    stroke = _parse(
        "L { stroke: { color: #ffffff; width: 6; cap: round; join: miter;"
        " dashPattern: [2, 1]; casing: { color: #333333; width: 1; };"
        " center: { color: red; width: 1 px }; }; }"
    )
    assert stroke["cap"] == "round" and stroke["join"] == "miter"
    assert stroke["dashPattern"] == [2, 1]
    assert stroke["casing"] == {"color": [51, 51, 51], "width": 1.0}
    assert stroke["centerLine"] == {
        "color": "red",
        "width": {"value": 1.0, "unit": "px"},
    }


@pytest.mark.parametrize("text", ["5 5", "[5, 5]"])
def test_dash_pattern_tuple_and_array_forms(text):
    stroke = _parse(f"L {{ stroke: {{ dashPattern: {text}; }}; }}")
    assert stroke["dashPattern"] == [5, 5]


def test_center_line_alias_is_accepted():
    assert "centerLine" in _parse("L { stroke: { centerLine: { width: 1 } }; }")


def test_dot_form():
    stroke = _parse(
        "L { stroke.cap: round; stroke.dashPattern: [3, 1];"
        " stroke.casing: { color: red; width: 2 px }; }"
    )
    assert stroke["alter"] is True and stroke["cap"] == "round"
    assert stroke["dashPattern"] == [3, 1]
    assert stroke["casing"]["width"] == {"value": 2.0, "unit": "px"}


def test_unreadable_dash_pattern_is_warned_not_dropped_silently(caplog):
    stroke = _parse("L { stroke: { color: gray; dashPattern: 2.5 1 }; }")
    assert "dashPattern" not in stroke
    assert "stroke.dashPattern" in caplog.text


@pytest.mark.parametrize(
    "source",
    [
        "L { stroke: { color: #ffffff; width: 6 px; cap: round; join: bevel;"
        " dashPattern: [2, 1]; casing: { color: #333333; width: 1 px };"
        " center: { color: red; width: 1 px } }; }",
        "L { stroke.cap: square; stroke.dashPattern: [3, 1];"
        " stroke.casing: { color: red; width: 2 px }; }",
    ],
)
def test_round_trip_through_cartosym_css(source):
    style = CartoSymParser().parse_string_to_pydantic(source)
    written = Converter().style_to_cscss(style)
    again = CartoSymParser().parse_string_to_pydantic(written)
    assert again.to_dict() == style.to_dict()
