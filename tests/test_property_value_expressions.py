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


def test_resource_uri_expression_is_kept():
    sym = _symbolizer(
        "P { marker: { elements: [ Image { image: {"
        " uri: concatenate('symbols/', kind, '.svg'); type: 'image/svg+xml' } },"
        " Image { image: { uri: kind } }, Image { image: { uri: 'kind' } } ] }; }"
    )
    images = [el["image"] for el in sym["marker"]["elements"]]
    assert images[0] == {
        "uri": {
            "op": "concatenate",
            "args": ["symbols/", {"property": "kind"}, ".svg"],
        },
        "type": "image/svg+xml",
    }
    assert images[1] == {"uri": {"property": "kind"}}
    assert images[2] == {"uri": "kind"}


def test_resource_uri_expression_is_written_back_as_cscss():
    from pycartosym import Converter

    converter = Converter()
    cscss = "P { marker: { elements: [ Image { image: { uri: kind } } ] }; }"
    written = converter.csjson_to_cscss(converter.cscss_to_csjson(cscss))
    assert "image: {uri: kind}" in written


def test_sld_writer_refuses_a_resource_uri_expression():
    import pytest

    from pycartosym import get_codec

    cscss = "P { marker: { elements: [ Image { image: { uri: kind } } ] }; }"
    style = CartoSymParser().parse_string_to_pydantic(cscss)
    with pytest.raises(NotImplementedError, match="expression"):
        get_codec("sld").write(style)
