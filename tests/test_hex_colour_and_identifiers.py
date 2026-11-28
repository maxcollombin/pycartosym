"""Hex colour length is validated; CQL2 identifiers stay properties on the right."""

import pytest

from pycartosym.cql2 import parse_text, to_cql2_json
from pycartosym.exceptions import CartoSymSyntaxError
from pycartosym.parser import CartoSymParser


def _parse(text: str):
    return CartoSymParser().parse_string_to_pydantic(text)


@pytest.mark.parametrize("color", ["#57510", "#5751", "#5751000", "#12"])
def test_hex_colour_with_a_wrong_digit_count_is_a_syntax_error(color):
    with pytest.raises(CartoSymSyntaxError, match="invalid hexadecimal colour"):
        _parse(f"L {{ fill: {{ color: {color} }}; }}")


@pytest.mark.parametrize("color", ["#575", "#575100", "#57510080"])
def test_hex_colour_with_3_6_or_8_digits_is_accepted(color):
    _parse(f"L {{ fill: {{ color: {color} }}; }}")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a = b", {"op": "=", "args": [{"property": "a"}, {"property": "b"}]}),
        ('a = "b"', {"op": "=", "args": [{"property": "a"}, {"property": "b"}]}),
        ('"my col" = 1', {"op": "=", "args": [{"property": "my col"}, 1]}),
        ("a = 'b'", {"op": "=", "args": [{"property": "a"}, "b"]}),
        ("a = true", {"op": "=", "args": [{"property": "a"}, True]}),
        # a bare word against a system identifier is an enumeration value
        (
            "dataLayer.type = vector",
            {"op": "=", "args": [{"sysId": "dataLayer.type"}, "vector"]},
        ),
    ],
)
def test_identifier_versus_literal(text, expected):
    assert to_cql2_json(parse_text(text)) == expected


def _first_rule(cscss: str) -> dict:
    from pycartosym import Converter

    return Converter().cscss_to_csjson(cscss)["stylingRules"][0]


@pytest.mark.parametrize("op", ["/", "-", "*"])
def test_property_after_arithmetic_on_a_system_identifier(op):
    rule = _first_rule(f"L {{ opacity: viz.sd {op} scale; }}")
    assert rule["symbolizer"]["opacity"] == {
        "op": op,
        "args": [{"sysId": "viz.sd"}, {"property": "scale"}],
    }


def test_property_compared_with_a_numeric_system_identifier():
    rule = _first_rule("[viz.sd > scale] { opacity: 0.5; }")
    assert rule["selector"]["args"] == [{"sysId": "viz.sd"}, {"property": "scale"}]


@pytest.mark.parametrize(
    ("selector", "value"),
    [("dataLayer.type = vector", "vector"), ("viz.date.month = may", "may")],
)
def test_bare_word_compared_with_an_enumerated_system_identifier(selector, value):
    rule = _first_rule(f"[{selector}] {{ opacity: 0.5; }}")
    assert rule["selector"]["args"][1] == value
