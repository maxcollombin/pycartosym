"""A function call with several arguments in a symbolizer property value."""

import pytest

from pycartosym.converter import Converter

MIN_AB = {"op": "min", "args": [{"property": "a"}, {"property": "b"}]}


def _symbolizer(css: str) -> dict:
    return Converter().cscss_to_csjson(css)["stylingRules"][0]["symbolizer"]


def test_two_arguments_in_a_block():
    stroke = _symbolizer("R { stroke: { width: min(a, b); color: red }; }")["stroke"]
    assert stroke == {"color": "red", "width": MIN_AB}


def test_three_arguments_in_a_block():
    stroke = _symbolizer("R { stroke: { width: min(a, b, c) }; }")["stroke"]
    assert [a["property"] for a in stroke["width"]["args"]] == ["a", "b", "c"]


def test_arguments_in_a_marker_element():
    element = _symbolizer(
        "R { marker: { elements: [ Text { text: concat(a, b), size: max(x, 3) } ] }; }"
    )["marker"]["elements"][0]
    assert element["text"]["args"] == [{"property": "a"}, {"property": "b"}]
    assert element["size"] == {"op": "max", "args": [{"property": "x"}, 3]}


@pytest.mark.parametrize("call", ["abs(a)", "min(a, b)"])
def test_call_in_a_dotted_property(call):
    width = _symbolizer(f"R {{ stroke.width: {call}; }}")["stroke"]["width"]
    assert width["op"] == call.split("(")[0]


def test_call_roundtrips_through_cscss():
    converter = Converter()
    style = converter.cscss_to_csjson("R { stroke: { width: min(a, b) }; }")
    again = converter.cscss_to_csjson(converter.csjson_to_cscss(style))
    assert again == style


def test_string_with_separators_stays_whole():
    element = _symbolizer(
        "R { marker: { elements: [ Text { text: 'a, b; c', size: 8 } ] }; }"
    )["marker"]["elements"][0]
    assert element["text"] == "a, b; c"
    assert element["size"] == 8


def test_comment_with_apostrophe_and_separators():
    css = (
        "R { stroke: { color: red; // it's a; comment, really\n"
        "  width: min(a, b); }; }"
    )
    stroke = _symbolizer(css)["stroke"]
    assert stroke["color"] == "red"
    assert stroke["width"] == MIN_AB
