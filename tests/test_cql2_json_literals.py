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


_COND = {
    "op": "?:",
    "args": [{"op": "=", "args": [{"property": "class"}, "european"]}, "E", "F"],
}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "concatenate(class = 'european' ? 'E' : 'F', number)",
            {"op": "concatenate", "args": [_COND, {"property": "number"}]},
        ),
        (
            "concatenate(number, class = 'european' ? 'E' : 'F')",
            {"op": "concatenate", "args": [{"property": "number"}, _COND]},
        ),
        (
            "concatenate(x > 1 ? 1 : 2, 'F')",
            {
                "op": "concatenate",
                "args": [
                    {
                        "op": "?:",
                        "args": [{"op": ">", "args": [{"property": "x"}, 1]}, 1, 2],
                    },
                    "F",
                ],
            },
        ),
    ],
)
def test_conditional_argument_of_a_call_with_several_arguments(text, expected):
    """A `?:` argument is a conditional, not a comparison with a string (#242)."""
    style = CartoSymParser().parse_string_to_pydantic(
        f"R {{ label: {{ elements: [ Text {{ text: {text} }} ] }}; }}"
    )
    label = style.to_dict()["stylingRules"][0]["symbolizer"]["label"]
    assert label["elements"][0]["text"] == expected
