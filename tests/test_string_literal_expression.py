"""An expression that is only a string literal stays a string."""

import pytest

from pycartosym import cql2
from pycartosym.converter import Converter
from pycartosym.parser import CartoSymParser


def test_bare_string_literal_is_a_string():
    assert cql2.to_cql2_json(cql2.parse_text("'abc'")) == "abc"
    assert cql2.to_cql2_json(cql2.parse_text("abc")) == {"property": "abc"}


def _text(value: str):
    cscss = (
        "[dataLayer.id = 'p'] "
        f"{{ label: {{ elements: [ Text {{ text: {value} }} ] }}; }}"
    )
    rule = Converter().cscss_to_csjson(cscss)["stylingRules"][0]
    return rule["symbolizer"]["label"]["elements"][0]["text"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("'Oslo'", "Oslo"),
        ("name", {"property": "name"}),
        ('"name"', {"property": "name"}),
    ],
)
def test_text_literal_versus_property(value, expected):
    assert _text(value) == expected


def test_text_literal_round_trips_through_cartosym_css():
    style = CartoSymParser().parse_string_to_pydantic(
        "L { label: { elements: [ Text { text: 'Oslo' } ] }; }"
    )
    written = Converter().style_to_cscss(style)
    again = CartoSymParser().parse_string_to_pydantic(written)
    assert again.to_dict() == style.to_dict()
