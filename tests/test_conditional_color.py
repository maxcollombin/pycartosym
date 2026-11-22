"""A conditional expression with colors is CQL2-JSON, and writes back as CSS."""

import pytest

from pycartosym.converter import Converter

CASES = [
    (
        "Roads { stroke: { color: class = 'european' ? #d0483a : #9a958b; }; }",
        "stroke",
        [[208, 72, 58], [154, 149, 139]],
        "class = 'european' ? #d0483a : #9a958b",
    ),
    (
        "Roads { stroke: { color: class = 'european' ? red : gray; }; }",
        "stroke",
        ["red", "gray"],
        "class = 'european' ? red : gray",
    ),
    (
        "Roads { fill: { color: a > 1 ? red : #ffffff; }; }",
        "fill",
        ["red", [255, 255, 255]],
        "a > 1 ? red : #ffffff",
    ),
]


@pytest.mark.parametrize(("source", "member", "branches", "text"), CASES)
def test_conditional_color_is_an_expression(source, member, branches, text) -> None:
    converter = Converter()
    result = converter.cscss_to_csjson(source)
    color = result["stylingRules"][0]["symbolizer"][member]["color"]
    assert color["op"] == "?:"
    assert color["args"][1:] == branches
    assert text in converter.csjson_to_cscss(result)


def test_conditional_color_of_a_dot() -> None:
    source = (
        "Pts { marker: { elements: [ "
        "Dot { color: elevation > 1800 ? #b8322a : #1f4e79; } ] }; }"
    )
    result = Converter().cscss_to_csjson(source)
    dot = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
    assert dot["color"]["args"][1:] == [[184, 50, 42], [31, 78, 121]]
