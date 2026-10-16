"""CQL2-JSON serialisation of string literals, arrays, `? :` and `^`."""

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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a_overlaps((1, 2), (3, 4))", {"op": "a_overlaps", "args": [[1, 2], [3, 4]]}),
        (
            "pop > 5 ? 1 : 2",
            {
                "op": "?:",
                "args": [{"op": ">", "args": [{"property": "pop"}, 5]}, 1, 2],
            },
        ),
        ("2 ^ 10", {"op": "^", "args": [2, 10]}),
    ],
)
def test_array_conditional_and_power_in_cql2_json(text, expected):
    assert to_cql2_json(parse_text(text)) == expected


def test_array_literal_in_a_selector_is_a_json_array():
    style = CartoSymParser().parse_string_to_pydantic(
        "Rivers[a_overlaps(tags, ('water', 'river'))] { opacity: 1; }"
    )
    selector = style.to_dict()["stylingRules"][0]["selector"]
    assert {
        "op": "a_overlaps",
        "args": [{"property": "tags"}, ["water", "river"]],
    } in selector["args"]
