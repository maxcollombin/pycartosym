"""Array arguments of a function survive CQL2-JSON -> CQL2-Text -> CQL2-JSON."""

import pytest

from pycartosym import cql2


@pytest.mark.parametrize(
    "expression",
    [
        {"op": "a_equals", "args": [[1, 2, 3], [1, 2, 3]]},
        {"op": "a_overlaps", "args": [{"property": "tags"}, ["water", "river"]]},
        {"op": "a_contains", "args": [{"property": "tags"}, ["x"]]},
        {"op": "a_contains", "args": [{"property": "tags"}, []]},
        {"op": "a_equals", "args": [[["a", "b"], ["c"]], [1]]},
    ],
)
def test_array_argument_round_trips(expression):
    text = cql2.to_cql2_text(expression)
    assert "'[" not in text  # not written as quoted text
    assert cql2.to_cql2_json(cql2.parse_text(text)) == expression


def test_bracketed_array_is_read_as_an_array():
    parsed = cql2.to_cql2_json(cql2.parse_text("a_equals([1, 2, 3], [1, 2])"))
    assert parsed == {"op": "a_equals", "args": [[1, 2, 3], [1, 2]]}
