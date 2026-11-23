"""``zOrder`` and ``opacity`` expressions are CQL2-JSON, not text or dropped."""

import pytest

from pycartosym.converter import Converter

CASES = [
    ("zOrder: z_order;", "zOrder", {"property": "z_order"}),
    (
        "zOrder: 0 - z_order;",
        "zOrder",
        {"op": "-", "args": [0, {"property": "z_order"}]},
    ),
    ("opacity: z_order;", "opacity", {"property": "z_order"}),
    ("zOrder: 3;", "zOrder", 3),
]


@pytest.mark.parametrize(("prop", "member", "expected"), CASES)
def test_expression_is_json_and_round_trips(prop, member, expected) -> None:
    converter = Converter()
    result = converter.cscss_to_csjson(f"Transport {{ {prop} }}")
    assert result["stylingRules"][0]["symbolizer"][member] == expected
    written = converter.csjson_to_cscss(result)
    assert prop.rstrip(";") in written
