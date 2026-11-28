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
        CartoSymParser().parse_string_to_pydantic("Areas { opacity: 'x'; }")
    assert any("opacity" in r.message for r in caplog.records)


_CONFIDENCE_HALF = {"op": "*", "args": [{"property": "confidence"}, 0.5]}


def test_graphic_opacity_expression_is_kept():
    sym = _symbolizer(
        "P { marker: { elements: [ Dot { opacity: confidence * 0.5 },"
        " Dot { opacity: confidence } ] }; }"
    )
    elements = sym["marker"]["elements"]
    assert elements[0]["opacity"] == _CONFIDENCE_HALF
    assert elements[1]["opacity"] == {"property": "confidence"}


def test_font_and_outline_opacity_expressions_are_kept():
    sym = _symbolizer(
        "P { label: { elements: [ Text { text: name; font: { size: 12;"
        " opacity: confidence * 0.5; outline: { size: 1; opacity: confidence } }"
        " } ] }; }"
    )
    font = sym["label"]["elements"][0]["font"]
    assert font["opacity"] == _CONFIDENCE_HALF
    assert font["outline"]["opacity"] == {"property": "confidence"}


def test_font_opacity_expression_is_written_back_as_cscss():
    from pycartosym import Converter

    cscss = (
        "P { label: { elements: [ Text { text: name; font: { size: 12;"
        " opacity: confidence * 0.5; outline: { size: 1; opacity: confidence } }"
        " } ] }; }"
    )
    converter = Converter()
    written = converter.csjson_to_cscss(converter.cscss_to_csjson(cscss))
    assert "opacity: confidence * 0.5;" in written
    assert "opacity: confidence}" in written
