"""An unknown symbolizer property is ignored on its own, with a warning."""

import logging

import pytest

from pycartosym.parser import CartoSymParser


@pytest.mark.parametrize(
    ("assignment", "name"),
    [
        ("foo: 1", "foo"),
        ("geometry: centroid", "geometry"),
        ("extrusion: { height: 3 }", "extrusion"),
    ],
)
def test_unknown_property_is_ignored_with_a_warning(caplog, assignment, name):
    with caplog.at_level(logging.WARNING):
        style = CartoSymParser().parse_string_to_pydantic(
            f"P {{ fill: {{ color: red }}; {assignment}; }}"
        )
    symbolizer = style.to_dict()["stylingRules"][0]["symbolizer"]
    assert symbolizer == {"fill": {"color": "red"}}
    assert any(
        "unknown symbolizer property" in r.message and name in r.message
        for r in caplog.records
    )


def test_vendor_property_is_kept():
    style = CartoSymParser().parse_string_to_pydantic(
        "P { fill: { color: red }; vendor.acme.glow: 2; }"
    )
    symbolizer = style.to_dict()["stylingRules"][0]["symbolizer"]
    assert "vendor.acme.glow" in symbolizer
    assert symbolizer["fill"] == {"color": "red"}
