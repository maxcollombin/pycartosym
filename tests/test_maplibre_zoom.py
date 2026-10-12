"""MapLibre ``minzoom``/``maxzoom`` ↔ CartoSym ``viz.sd`` selector mapping."""

from __future__ import annotations

import pytest

from pycartosym.codecs.maplibre._zoom import (
    extract_zoom_range,
    merge_zoom_range,
    scale_denominator_from_zoom,
    zoom_filter_conjunct,
    zoom_from_scale_denominator,
)


@pytest.mark.parametrize("zoom", [0, 1, 2, 8, 10, 11, 19, 24])
def test_zoom_scale_round_trip_is_exact_for_integers(zoom: int):
    sd = scale_denominator_from_zoom(zoom)
    assert zoom_from_scale_denominator(sd) == zoom
    assert isinstance(zoom_from_scale_denominator(sd), int)


def test_scale_denominator_decreases_as_zoom_increases():
    assert scale_denominator_from_zoom(10) > scale_denominator_from_zoom(11)


def test_merge_minzoom_maps_to_upper_bound():
    selector = merge_zoom_range(10, None, None)
    assert selector == {
        "op": "<=",
        "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(10)],
    }


def test_merge_maxzoom_maps_to_lower_bound():
    selector = merge_zoom_range(None, 12, None)
    assert selector == {
        "op": ">",
        "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(12)],
    }


def test_merge_minzoom_zero_is_dropped():
    assert merge_zoom_range(0, None, None) is None


def test_merge_zoom_range_ands_with_existing_selector():
    base = {"op": "=", "args": [{"property": "class"}, "water"]}
    selector = merge_zoom_range(10, 12, base)
    assert selector == {
        "op": "and",
        "args": [
            {
                "op": "<=",
                "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(10)],
            },
            {"op": ">", "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(12)]},
            base,
        ],
    }


def test_extract_zoom_range_is_the_inverse_of_merge():
    merged = merge_zoom_range(10, 12, None)
    minzoom, maxzoom, remaining = extract_zoom_range(merged)
    assert (minzoom, maxzoom, remaining) == (10, 12, None)


def test_extract_zoom_range_leaves_residual_selector():
    base = {"op": "=", "args": [{"property": "class"}, "water"]}
    merged = merge_zoom_range(10, None, base)
    minzoom, maxzoom, remaining = extract_zoom_range(merged)
    assert (minzoom, maxzoom, remaining) == (10, None, base)


def test_extract_zoom_range_none_selector():
    assert extract_zoom_range(None) == (None, None, None)


def test_extract_zoom_range_picks_tightest_bound():
    # Two minzoom-shaped conjuncts (cascade merge) -> the higher zoom
    # (smaller scale denominator) wins.
    selector = {
        "op": "and",
        "args": [
            {"op": "<=", "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(8)]},
            {
                "op": "<=",
                "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(10)],
            },
        ],
    }
    minzoom, maxzoom, remaining = extract_zoom_range(selector)
    assert (minzoom, maxzoom, remaining) == (10, None, None)


@pytest.mark.parametrize("op", ["<", ">=", "=", "!="])
def test_extract_zoom_range_leaves_non_minmax_operators_for_the_filter_fallback(
    op: str,
):
    """``<``/``>=``/``=``/``!=`` have no minzoom/maxzoom shape (only
    ``<=``/``>`` do) — left in ``remaining`` rather than raised, for
    :func:`.selector_to_filter` to turn into a ``["zoom"]`` filter
    conjunct via :func:`zoom_filter_conjunct` instead.
    """
    selector = {"op": op, "args": [{"sysId": "viz.sd"}, 100000]}
    assert extract_zoom_range(selector) == (None, None, selector)


@pytest.mark.parametrize(
    ("op", "filter_op"),
    [("<", ">"), (">=", "<="), ("=", "=="), ("!=", "!=")],
)
def test_zoom_filter_conjunct_covers_the_non_minmax_operators(op: str, filter_op: str):
    selector = {"op": op, "args": [{"sysId": "viz.sd"}, 100000]}
    assert zoom_filter_conjunct(selector) == [
        filter_op,
        ["zoom"],
        zoom_from_scale_denominator(100000),
    ]


def test_zoom_filter_conjunct_handles_flipped_operand_order():
    # `100000 > viz.sd` reads the same as `viz.sd < 100000`
    selector = {"op": ">", "args": [100000, {"sysId": "viz.sd"}]}
    assert zoom_filter_conjunct(selector) == [
        ">",
        ["zoom"],
        zoom_from_scale_denominator(100000),
    ]


def test_zoom_filter_conjunct_ignores_minmax_shapes():
    """The two shapes ``extract_zoom_range`` already maps to minzoom/maxzoom
    are not also offered as a filter conjunct.
    """
    assert (
        zoom_filter_conjunct({"op": "<=", "args": [{"sysId": "viz.sd"}, 100000]})
        is None
    )
    assert (
        zoom_filter_conjunct({"op": ">", "args": [{"sysId": "viz.sd"}, 100000]}) is None
    )


def test_zoom_filter_conjunct_ignores_non_viz_sd_comparisons():
    assert zoom_filter_conjunct({"op": "<", "args": [{"property": "class"}, 1]}) is None


def test_extract_zoom_range_ignores_non_viz_sd_conjuncts():
    selector = {"op": "=", "args": [{"property": "class"}, "water"]}
    assert extract_zoom_range(selector) == (None, None, selector)


@pytest.mark.parametrize(
    "args", [[{"sysId": "viz.sd"}, 100.0], [100.0, {"sysId": "viz.sd"}]]
)
def test_zoom_filter_conjunct_not_equal_accepts_either_operand_order(args):
    result = zoom_filter_conjunct({"op": "<>", "args": args})
    assert result is not None and result[:2] == ["!=", ["zoom"]]
