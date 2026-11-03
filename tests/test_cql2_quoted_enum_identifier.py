"""A double-quoted word against a system identifier is a property, not an enum."""

import pytest

from pycartosym import cql2

SYS = {"sysId": "dataLayer.type"}


@pytest.mark.parametrize(
    ("text", "right"),
    [
        ("dataLayer.type = coverage", "coverage"),
        ("dataLayer.type = 'coverage'", "coverage"),
        ('dataLayer.type = "coverage"', {"property": "coverage"}),
    ],
)
def test_enum_string_and_quoted_identifier(text, right):
    assert cql2.to_cql2_json(cql2.parse_text(text)) == {
        "op": "=",
        "args": [SYS, right],
    }


def test_quoted_identifier_roundtrips_through_text():
    js = {"op": "=", "args": [SYS, {"property": "coverage"}]}
    text = cql2.to_cql2_text(js)
    assert text == 'dataLayer.type = "coverage"'
    assert cql2.to_cql2_json(cql2.parse_text(text)) == js
