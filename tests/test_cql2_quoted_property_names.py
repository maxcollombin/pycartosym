"""A property named like a literal or a keyword is written double-quoted.

In CQL2-Text ``null`` is the literal and ``"null"`` a property (the same for
``true`` and ``false``), so a property written bare would read back as
something else.
"""

import pytest

from pycartosym import cql2


@pytest.mark.parametrize("name", ["null", "true", "false", "NULL", "and", "like"])
def test_a_property_named_like_a_keyword_is_quoted(name):
    assert cql2.to_cql2_text({"property": name}) == f'"{name}"'


@pytest.mark.parametrize("name", ["my prop", "a-b", "1x"])
def test_a_property_that_is_not_an_identifier_is_quoted(name):
    assert cql2.to_cql2_text({"property": name}) == f'"{name}"'


@pytest.mark.parametrize("name", ["height", "viz.date", "café", "a_1.b"])
def test_a_plain_property_stays_bare(name):
    assert cql2.to_cql2_text({"property": name}) == name


@pytest.mark.parametrize(
    "text",
    ['"null"', '"null" is null', '"null" > 1', '"true"', '"my prop" = 1'],
)
def test_the_property_survives_a_round_trip(text):
    expr = cql2.to_cql2_json(cql2.parse_text(text))
    again = cql2.to_cql2_json(cql2.parse_text(cql2.to_cql2_text(expr)))
    assert again == expr


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("null", None),
        ("null is null", {"op": "isNull", "args": [None]}),
        ("null > 1", {"op": ">", "args": [None, 1]}),
    ],
)
def test_the_null_literal_is_not_a_property(text, expected):
    assert cql2.to_cql2_json(cql2.parse_text(text)) == expected
