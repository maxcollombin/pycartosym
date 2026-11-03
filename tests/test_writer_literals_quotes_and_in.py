"""CartoSym-CSS writer literals (boolean, quotes) and the SLD ``in`` operator."""

from lxml import etree

from pycartosym.codecs.sld._dialect import SE_1_1_0
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter

_OGC = "{http://www.opengis.net/ogc}"


def _roundtrip(cscss: str) -> tuple[dict, str]:
    converter = Converter()
    csjson = converter.cscss_to_csjson(cscss)
    return csjson, converter.csjson_to_cscss(csjson)


def test_boolean_literal_is_written_lower_case():
    csjson, text = _roundtrip(
        "L { [a = false and b <> 'x'] { stroke: {color: red}; } }"
    )
    assert "[a = false and" in text
    assert "False" not in text
    assert Converter().cscss_to_csjson(text) == csjson


def test_single_quote_is_doubled_in_selectors_and_metadata():
    csjson = {
        "metadata": {"title": "t", "abstract": "it's here"},
        "stylingRules": [
            {
                "selector": {"op": "=", "args": [{"property": "a"}, "it's"]},
                "symbolizer": {"stroke": {"color": [255, 0, 0]}},
            }
        ],
    }
    text = Converter().csjson_to_cscss(csjson)
    assert ".abstract 'it''s here'" in text
    assert "[a = 'it''s']" in text
    back = Converter().cscss_to_csjson(text)
    assert back["metadata"]["abstract"] == "it's here"
    assert back["stylingRules"][0]["selector"]["args"][1] == "it's"


def test_metadata_escaped_quotes_and_continuation():
    read = Converter().cscss_to_csjson
    rule = "L { stroke: {color: red}; }"
    assert read(f".abstract 'it\\'s'\n{rule}")["metadata"]["abstract"] == "it's"
    assert read(f".abstract 'it''s'\n{rule}")["metadata"]["abstract"] == "it's"
    assert read(f".abstract 'a'\n   'b'\n{rule}")["metadata"]["abstract"] == "a b"


def _filter(cscss: str) -> etree._Element:
    style = Converter().csjson_to_style(Converter().cscss_to_csjson(cscss))
    root = etree.fromstring(SldWriter(SE_1_1_0).write(style).encode())
    return root.find(f".//{_OGC}Filter")


def test_in_is_written_as_an_or_of_equalities():
    flt = _filter("Layer { [kind in ('a', 'b')] { stroke: {color: red}; } }")
    (or_el,) = list(flt)
    assert or_el.tag == f"{_OGC}Or"
    values = [eq.find(f"{_OGC}Literal").text for eq in or_el]
    assert values == ["a", "b"]
    assert all(eq.tag == f"{_OGC}PropertyIsEqualTo" for eq in or_el)


def test_in_with_one_value_is_a_plain_equality():
    flt = _filter("Layer { [kind in ('a')] { stroke: {color: red}; } }")
    (eq,) = list(flt)
    assert eq.tag == f"{_OGC}PropertyIsEqualTo"


def test_not_in_wraps_the_or_in_not():
    flt = _filter("Layer { [kind not in ('a', 'b')] { stroke: {color: red}; } }")
    (not_el,) = list(flt)
    assert not_el.tag == f"{_OGC}Not"
    assert list(not_el)[0].tag == f"{_OGC}Or"
