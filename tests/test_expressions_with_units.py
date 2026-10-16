"""Units inside expressions: {"px": expr} around the whole expression, round-trip."""

import pytest

from pycartosym.converter import Converter
from pycartosym.cql2.to_json import convert_property_expression
from pycartosym.parser import CartoSymParser


def _width(cscss: str):
    style = CartoSymParser().parse_string_to_pydantic(cscss)
    return style.to_dict()["stylingRules"][0]["symbolizer"]["stroke"]["width"]


def test_unit_literal_is_a_unit_value():
    assert convert_property_expression("6 px") == {"px": 6}


def test_shared_unit_is_moved_outside_the_operation():
    assert convert_property_expression("w * 2 px") == {
        "px": {"op": "*", "args": [{"property": "w"}, 2]}
    }


def test_mixed_units_are_rejected():
    assert convert_property_expression("1 mm + 2 px") is None


def test_conditional_width_wraps_each_branch():
    width = _width("Roads { stroke: { width: lanes > 2 ? 6 px : 2 px; color: red }; }")
    assert width == {
        "op": "?:",
        "args": [{"op": ">", "args": [{"property": "lanes"}, 2]}, {"px": 6}, {"px": 2}],
    }


@pytest.mark.parametrize(
    "cscss",
    [
        "Roads { stroke: { width: lanes > 2 ? 6 px : 2 px; color: red }; }",
        "Rivers { stroke: { width: lanes * 2 px; color: blue }; }",
        "Places { label: { elements: [ Text { text: upperCase(name) } ] }; }",
        "Areas { opacity: 2 ^ -1; }",
    ],
)
def test_expression_values_round_trip_through_cscss(cscss):
    parser = CartoSymParser()
    first = parser.parse_string_to_pydantic(cscss)
    text = Converter().style_to_cscss(first)
    second = parser.parse_string_to_pydantic(text)
    assert second.to_dict() == first.to_dict()
