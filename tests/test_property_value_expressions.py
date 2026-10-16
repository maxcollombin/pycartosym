"""Expressions used as property values are converted, not dropped or kept as text."""

import logging

from pycartosym.parser import CartoSymParser


def _symbolizer(cscss: str) -> dict:
    style = CartoSymParser().parse_string_to_pydantic(cscss)
    return style.to_dict()["stylingRules"][0]["symbolizer"]


def test_opacity_expression_is_kept():
    sym = _symbolizer("Areas { opacity: 2 ^ -1; }")
    assert sym["opacity"] == {"op": "^", "args": [2, -1]}


def test_text_function_call_is_an_expression_not_a_property_name():
    sym = _symbolizer(
        "Places { label: { elements: [ Text { text: upperCase(name) } ] }; }"
    )
    assert sym["label"]["elements"][0]["text"] == {
        "op": "upperCase",
        "args": [{"property": "name"}],
    }


def test_unparseable_opacity_warns(caplog):
    with caplog.at_level(logging.WARNING):
        CartoSymParser().parse_string_to_pydantic("Areas { opacity: red; }")
    assert any("opacity" in r.message for r in caplog.records)
