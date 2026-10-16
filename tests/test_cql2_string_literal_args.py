"""A single-quoted CQL2 string stays a literal when it is a function argument."""

import pytest

from pycartosym.cql2 import parse_text, to_cql2_json
from pycartosym.parser import CartoSymParser


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "contains(name, 'sl')",
            {"op": "contains", "args": [{"property": "name"}, "sl"]},
        ),
        ("upperCase('abc')", {"op": "upperCase", "args": ["abc"]}),
        ("'Oslo' like 'O%'", {"op": "like", "args": ["Oslo", "O%"]}),
        (
            "upperCase(kind) = 'CITY'",
            {
                "op": "=",
                "args": [{"op": "upperCase", "args": [{"property": "kind"}]}, "CITY"],
            },
        ),
    ],
)
def test_quoted_string_is_a_literal(text, expected):
    assert to_cql2_json(parse_text(text)) == expected


def test_quoted_string_argument_in_a_selector():
    style = CartoSymParser().parse_string_to_pydantic(
        "Places[contains(name, 'sl')] { opacity: 1; }"
    )
    selector = style.to_dict()["stylingRules"][0]["selector"]
    assert {"op": "contains", "args": [{"property": "name"}, "sl"]} in selector["args"]
