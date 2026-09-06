"""MapLibre layer ``filter`` ↔ CartoSym selector mapping."""

from __future__ import annotations

import pytest

from pycartosym.codecs.maplibre._filter import (
    filter_to_selector,
    selector_to_filter,
    strip_datalayer_id,
)


@pytest.mark.parametrize(
    "mb_filter, selector",
    [
        (
            ["==", "position", "left"],
            {"op": "=", "args": [{"property": "position"}, "left"]},
        ),
        (
            ["==", ["get", "position"], "left"],
            {"op": "=", "args": [{"property": "position"}, "left"]},
        ),
        (
            ["!=", "cls", "water"],
            {"op": "<>", "args": [{"property": "cls"}, "water"]},
        ),
        (
            [">=", "rank", 3],
            {"op": ">=", "args": [{"property": "rank"}, 3]},
        ),
        (
            ["all", ["==", "a", 1], [">", "b", 2]],
            {
                "op": "and",
                "args": [
                    {"op": "=", "args": [{"property": "a"}, 1]},
                    {"op": ">", "args": [{"property": "b"}, 2]},
                ],
            },
        ),
        (
            ["any", ["==", "a", 1], ["==", "a", 2]],
            {
                "op": "or",
                "args": [
                    {"op": "=", "args": [{"property": "a"}, 1]},
                    {"op": "=", "args": [{"property": "a"}, 2]},
                ],
            },
        ),
        (
            ["in", "type", "road", "rail"],
            {"op": "in", "args": [{"property": "type"}, ["road", "rail"]]},
        ),
        (
            ["in", ["get", "type"], ["literal", ["road", "rail"]]],
            {"op": "in", "args": [{"property": "type"}, ["road", "rail"]]},
        ),
        (
            ["!in", "type", "road"],
            {
                "op": "not",
                "args": [{"op": "in", "args": [{"property": "type"}, ["road"]]}],
            },
        ),
        (
            ["has", "name"],
            {
                "op": "not",
                "args": [{"op": "isNull", "args": [{"property": "name"}]}],
            },
        ),
        (
            ["!has", "name"],
            {"op": "isNull", "args": [{"property": "name"}]},
        ),
        (
            ["!", ["==", "a", 1]],
            {"op": "not", "args": [{"op": "=", "args": [{"property": "a"}, 1]}]},
        ),
        (
            ["==", ["geometry-type"], "Point"],
            {
                "op": "=",
                "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 0],
            },
        ),
        (
            ["==", ["geometry-type"], "LineString"],
            {
                "op": "=",
                "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 1],
            },
        ),
        (
            ["!=", ["geometry-type"], "Polygon"],
            {
                "op": "<>",
                "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 2],
            },
        ),
    ],
)
def test_filter_to_selector(mb_filter, selector):
    assert filter_to_selector(mb_filter) == selector


CANONICAL_FILTERS = [
    ["==", ["get", "position"], "left"],
    ["!=", ["get", "cls"], "water"],
    [">", ["get", "b"], 2],
    ["all", ["==", ["get", "a"], 1], [">", ["get", "b"], 2]],
    ["any", ["==", ["get", "a"], 1], ["==", ["get", "a"], 2]],
    ["in", ["get", "type"], ["literal", ["road", "rail"]]],
    ["!in", ["get", "type"], ["literal", ["road"]]],
    ["has", "name"],
    ["!", ["has", "name"]],
    ["!", ["==", ["get", "a"], 1]],
    ["==", ["geometry-type"], "Point"],
    ["!=", ["geometry-type"], "Polygon"],
]


@pytest.mark.parametrize("mb_filter", CANONICAL_FILTERS)
def test_round_trip_is_a_fixed_point(mb_filter):
    assert selector_to_filter(filter_to_selector(mb_filter)) == mb_filter


@pytest.mark.parametrize(
    "mb_filter",
    [
        ["==", "$type", "Polygon"],
        ["==", "$id", 5],
        ["<", ["geometry-type"], "Point"],
        [">=", ["geometry-type"], "Point"],
        ["==", ["geometry-type"], "MultiPoint"],
        ["step", ["zoom"], 0, 10, 1],
        ["==", ["get", "a"], ["get", "b"]],
    ],
)
def test_unsupported_filters_raise(mb_filter):
    with pytest.raises(NotImplementedError):
        filter_to_selector(mb_filter)


def test_none_combinator():
    assert filter_to_selector(["none", ["==", "x", "y"]]) == {
        "op": "not",
        "args": [{"op": "or", "args": [{"op": "=", "args": [{"property": "x"}, "y"]}]}],
    }


def test_selector_with_sysid_operand_raises():
    with pytest.raises(NotImplementedError):
        selector_to_filter({"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]})


def test_selector_with_sysid_comparison_value_raises():
    """A sysId on the *right*-hand side (e.g. viz.timeInterval.start.date)
    has no MapLibre filter equivalent — it must raise, not embed a bare
    object where the expression grammar requires a literal (regression:
    this used to pass the dict straight through, producing a filter
    ``gl-style-validate`` rejects as "Bare objects invalid").
    """
    selector = {
        "op": ">=",
        "args": [
            {"property": "validDate"},
            {"sysId": "viz.timeInterval.start.date"},
        ],
    }
    with pytest.raises(NotImplementedError, match="viz.timeInterval.start.date"):
        selector_to_filter(selector)


def test_selector_between_with_sysid_bound_raises():
    """Same guard for a ``between`` predicate's low/high bounds."""
    selector = {
        "op": "between",
        "args": [
            {"property": "validDate"},
            {"sysId": "viz.timeInterval.start.date"},
            {"sysId": "viz.timeInterval.end.date"},
        ],
    }
    with pytest.raises(NotImplementedError, match="viz.timeInterval"):
        selector_to_filter(selector)


def test_strip_datalayer_id_drops_a_lone_conjunct():
    selector = {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]}
    assert strip_datalayer_id(selector) is None


def test_strip_datalayer_id_handles_reversed_operand_order():
    selector = {"op": "=", "args": ["Landuse", {"sysId": "dataLayer.id"}]}
    assert strip_datalayer_id(selector) is None


def test_strip_datalayer_id_leaves_other_selectors_untouched():
    selector = {"op": "=", "args": [{"property": "k"}, "v"]}
    assert strip_datalayer_id(selector) == selector
    assert strip_datalayer_id(None) is None


def test_strip_datalayer_id_unwraps_single_surviving_sibling():
    selector = {
        "op": "and",
        "args": [
            {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]},
            {"op": "=", "args": [{"property": "k"}, "v"]},
        ],
    }
    assert strip_datalayer_id(selector) == {
        "op": "=",
        "args": [{"property": "k"}, "v"],
    }


def test_selector_to_filter_geometry_dimensions_equal():
    selector = {
        "op": "=",
        "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 2],
    }
    assert selector_to_filter(selector) == ["==", ["geometry-type"], "Polygon"]


def test_selector_to_filter_geometry_dimensions_not_equal():
    selector = {
        "op": "<>",
        "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 0],
    }
    assert selector_to_filter(selector) == ["!=", ["geometry-type"], "Point"]


def test_selector_to_filter_geometry_dimensions_reversed_operand_order():
    selector = {
        "op": "=",
        "args": [1, {"sysId": "dataLayer.featuresGeometryDimensions"}],
    }
    assert selector_to_filter(selector) == ["==", ["geometry-type"], "LineString"]


def test_selector_to_filter_geometry_dimensions_bad_comparator_raises():
    selector = {
        "op": "<",
        "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 2],
    }
    with pytest.raises(NotImplementedError):
        selector_to_filter(selector)


def test_selector_to_filter_geometry_dimensions_unknown_value_raises():
    selector = {
        "op": "=",
        "args": [{"sysId": "dataLayer.featuresGeometryDimensions"}, 3],
    }
    with pytest.raises(NotImplementedError):
        selector_to_filter(selector)


def test_strip_datalayer_id_keeps_and_with_several_survivors():
    selector = {
        "op": "and",
        "args": [
            {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]},
            {"op": "=", "args": [{"property": "k"}, "v"]},
            {"op": ">", "args": [{"property": "n"}, 1]},
        ],
    }
    assert strip_datalayer_id(selector) == {
        "op": "and",
        "args": [
            {"op": "=", "args": [{"property": "k"}, "v"]},
            {"op": ">", "args": [{"property": "n"}, 1]},
        ],
    }


def test_selector_to_filter_between():
    """No single MapLibre filter primitive for ``between`` — it decomposes
    into an ``all`` of the two boundary comparisons.
    """
    selector = {"op": "between", "args": [{"property": "Population"}, 1000, 5000]}
    assert selector_to_filter(selector) == [
        "all",
        [">=", ["get", "Population"], 1000],
        ["<=", ["get", "Population"], 5000],
    ]


def test_selector_to_filter_not_between():
    selector = {
        "op": "not",
        "args": [{"op": "between", "args": [{"property": "n"}, 1, 5]}],
    }
    assert selector_to_filter(selector) == [
        "!",
        ["all", [">=", ["get", "n"], 1], ["<=", ["get", "n"], 5]],
    ]


def test_selector_to_filter_between_round_trips_as_and_of_comparisons():
    """The decomposed ``all``/``>=``/``<=`` filter reads back as an
    equivalent ``and``-of-two-comparisons selector — not reconstructed as
    ``between`` (no MapLibre primitive marks it as one), which is fine:
    semantically equivalent, just a different (already-supported) shape.
    """
    mb_filter = selector_to_filter({"op": "between", "args": [{"property": "n"}, 1, 5]})
    assert filter_to_selector(mb_filter) == {
        "op": "and",
        "args": [
            {"op": ">=", "args": [{"property": "n"}, 1]},
            {"op": "<=", "args": [{"property": "n"}, 5]},
        ],
    }


def test_selector_to_filter_like_raises():
    selector = {"op": "like", "args": [{"property": "Name"}, "%park%"]}
    with pytest.raises(NotImplementedError):
        selector_to_filter(selector)


@pytest.mark.parametrize("spelling", ["isNull", "isnull", "ISNULL"])
def test_selector_to_filter_isnull_is_case_insensitive(spelling):
    """The SLD reader emits lowercase ``isnull`` for ``PropertyIsNull``
    (``codecs/sld/_filter.py``, itself case-insensitive on the way back
    to SLD/SE XML) while this codec's own selectors spell it ``isNull`` —
    ``StylingRule.selector`` has no fixed op casing to enforce, so both
    must be accepted.
    """
    selector = {"op": spelling, "args": [{"property": "name"}]}
    assert selector_to_filter(selector) == ["!", ["has", "name"]]


@pytest.mark.parametrize("spelling", ["isNull", "isnull"])
def test_selector_to_filter_not_isnull_is_case_insensitive(spelling):
    selector = {
        "op": "not",
        "args": [{"op": spelling, "args": [{"property": "name"}]}],
    }
    assert selector_to_filter(selector) == ["has", "name"]
