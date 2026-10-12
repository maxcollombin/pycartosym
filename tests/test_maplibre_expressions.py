"""MapLibre value-expression arrays ↔ CartoSym value expressions.

Scope: the six operators ``codecs.maplibre._expressions`` targets — ``get``
/ ``case`` / ``match`` / ``interpolate`` / ``step`` / ``coalesce`` — plus
the 5 binary arithmetic operators (``+``/``-``/``*``/``/``/``^``). A
``SystemIdentifier`` (e.g. ``viz.sd``, OGC issue #115) is a confirmed
permanent wall for :func:`value_to_maplibre_expr` itself, not mapped by
this codec: the real MapLibre style spec only allows ``["zoom"]`` as the
sole, top-level input to ``step``/``interpolate``, never nested inside
arithmetic. Every other MapLibre expression operator (comparisons,
``all``/``any``/``!``, ``%``, a bare ``zoom``, ``let``/``var``, other
interpolation colour spaces, …) is a deliberate out-of-scope gap —
asserted here, not silently dropped.

One exception, handled one level up in ``writer.py``'s ``_literal`` before
it ever reaches this module's raise (see :func:`test_is_viz_sd_arithmetic`
/ :func:`test_step_lut_for_viz_sd_samples_zoom_6_to_18` below, and
``test_maplibre_writer.py::test_viz_sd_arithmetic_stroke_width_samples_a_step_lut``
for the end-to-end case): a whole top-level property value built only
from ``viz.sd`` and numeric literals is sampled into a ``step`` lookup
table instead of raising.
"""

from __future__ import annotations

import pytest

from pycartosym.codecs.maplibre._expressions import (
    is_viz_sd_arithmetic,
    maplibre_expr_to_value,
    step_lut_for_viz_sd,
    value_to_maplibre_expr,
)
from pycartosym.models.value_expressions import (
    ArithmeticExpression,
    PropertyRef,
    SystemIdentifier,
)

# Round-trip cases: (MapLibre expression array, CartoSym value dict).
# Fed through maplibre_expr_to_value / value_to_maplibre_expr directly, and
# through the full Style model (Fill.color) to prove Pydantic validates the
# dict into the matching typed pycartosym.models.value_expressions
# class and the writer reconstructs the exact same array back.
ROUND_TRIP = [
    (
        ["get", "colour"],
        {"property": "colour"},
    ),
    (
        ["case", ["get", "big"], "red", "blue"],
        {"op": "case", "args": [{"property": "big"}, "red", "blue"]},
    ),
    (
        ["case", True, "a", False, "b", "c"],
        {"op": "case", "args": [True, "a", False, "b", "c"]},
    ),
    (
        ["match", ["get", "class"], "park", "green", "water", "blue", "grey"],
        {
            "op": "match",
            "args": [{"property": "class"}, "park", "green", "water", "blue", "grey"],
        },
    ),
    (
        ["match", ["get", "class"], [1, 2, 3], "a", 4, "b", "c"],
        {"op": "match", "args": [{"property": "class"}, [1, 2, 3], "a", 4, "b", "c"]},
    ),
    (
        ["step", ["get", "rank"], "small", 3, "medium", 6, "large"],
        {
            "op": "step",
            "args": [{"property": "rank"}, "small", 3, "medium", 6, "large"],
        },
    ),
    (
        ["interpolate", ["linear"], ["get", "zoom"], 0, 1, 10, 5],
        {
            "op": "interpolate",
            "interpolation": "linear",
            "args": [{"property": "zoom"}, 0, 1, 10, 5],
        },
    ),
    (
        ["interpolate", ["exponential", 1.5], ["get", "zoom"], 0, 1, 10, 5],
        {
            "op": "interpolate",
            "interpolation": "exponential",
            "base": 1.5,
            "args": [{"property": "zoom"}, 0, 1, 10, 5],
        },
    ),
    (
        ["interpolate", ["cubic-bezier", 0.2, 0, 0.8, 1], ["get", "zoom"], 0, 1, 10, 5],
        {
            "op": "interpolate",
            "interpolation": "cubic-bezier",
            "controlPoints": [0.2, 0, 0.8, 1],
            "args": [{"property": "zoom"}, 0, 1, 10, 5],
        },
    ),
    (
        ["coalesce", ["get", "a"], ["get", "b"], "fallback"],
        {
            "op": "coalesce",
            "args": [{"property": "a"}, {"property": "b"}, "fallback"],
        },
    ),
    # Nesting: get inside case inside coalesce.
    (
        ["coalesce", ["case", ["get", "ok"], ["get", "a"], None], "fallback"],
        {
            "op": "coalesce",
            "args": [
                {
                    "op": "case",
                    "args": [{"property": "ok"}, {"property": "a"}, None],
                },
                "fallback",
            ],
        },
    ),
    # Binary arithmetic (OGC issue #115's stroke.width: <property> / 1000
    # shape — arithmetic over a PropertyRef, which this codec does map;
    # viz.sd itself is a confirmed permanent wall, see
    # test_system_identifier_raises below).
    (
        ["/", ["get", "a"], 1000],
        {"op": "/", "args": [{"property": "a"}, 1000]},
    ),
    (
        ["^", 2, ["get", "a"]],
        {"op": "^", "args": [2, {"property": "a"}]},
    ),
]


@pytest.mark.parametrize("mb_expr, value", ROUND_TRIP)
def test_maplibre_expr_to_value(mb_expr, value):
    assert maplibre_expr_to_value(mb_expr, "prop") == value


def test_literal_scalars_pass_through():
    for scalar in ("red", 3, 1.5, True, None):
        assert maplibre_expr_to_value(scalar, "prop") == scalar
        assert value_to_maplibre_expr(scalar, "prop") == scalar


def test_literal_operator_unwraps_its_payload():
    # ['literal', x] marks x (often an array) as a constant, not a nested
    # expression — it unwraps one-way; a plain value never re-wraps into
    # ['literal', ...] on the way back (there is nothing to disambiguate).
    assert maplibre_expr_to_value(["literal", "red"], "prop") == "red"


@pytest.mark.parametrize(
    "mb_expr",
    [
        ["==", ["get", "a"], 1],
        ["all", ["==", "a", 1], [">", "b", 2]],
        ["%", ["get", "a"], 2],
        ["zoom"],
        ["to-string", ["get", "a"]],
        ["let", "x", 1, ["var", "x"]],
        ["interpolate-hcl", ["linear"], ["get", "zoom"], 0, "red", 10, "blue"],
    ],
)
def test_out_of_scope_operator_raises(mb_expr):
    with pytest.raises(NotImplementedError):
        maplibre_expr_to_value(mb_expr, "prop")


@pytest.mark.parametrize(
    "mb_expr",
    [
        ["get", "a", "b"],  # two-arg get (object indexing) not supported
        ["case", ["get", "a"]],  # missing fallback
        ["match", ["get", "a"], "x"],  # missing fallback
        ["step", ["get", "a"]],  # missing output0
        ["interpolate", ["linear"], ["get", "a"]],  # missing stop/output pair
        ["interpolate", ["unknown-type"], ["get", "a"], 0, 1],
        # non-literal label:
        ["match", ["get", "a"], [1, ["get", "b"]], "out", "fallback"],
        ["+", 1, 2, 3],  # only 2-argument arithmetic maps in this codec
    ],
)
def test_malformed_expression_raises(mb_expr):
    with pytest.raises(NotImplementedError):
        maplibre_expr_to_value(mb_expr, "prop")


@pytest.mark.parametrize("sys_id", ["viz.sd", "viz.other"])
def test_system_identifier_raises(sys_id):
    """No ``SystemIdentifier`` has a MapLibre expression mapping in
    :func:`value_to_maplibre_expr` itself — ``viz.sd`` (OGC issue #115)
    included: the real MapLibre style spec only allows a ``["zoom"]``
    input as the sole, top-level argument of ``step``/``interpolate``,
    never nested inside arithmetic, so there is no faithful,
    round-trippable encoding for it here in the general case (confirmed
    permanent wall, not a missing-wiring gap — same conclusion as SLD/SE).
    The one exception (a whole top-level property built only from
    ``viz.sd`` and numeric literals) is handled before this function is
    even called — see the module docstring and
    :func:`test_is_viz_sd_arithmetic`.
    """
    with pytest.raises(NotImplementedError):
        value_to_maplibre_expr(SystemIdentifier(sysId=sys_id), "prop")


@pytest.mark.parametrize(
    "value, expected",
    [
        (SystemIdentifier(sysId="viz.sd"), True),
        (SystemIdentifier(sysId="viz.other"), False),
        (
            ArithmeticExpression(op="/", args=[SystemIdentifier(sysId="viz.sd"), 1000]),
            True,
        ),
        (
            ArithmeticExpression(
                op="+",
                args=[
                    ArithmeticExpression(
                        op="/", args=[SystemIdentifier(sysId="viz.sd"), 1000]
                    ),
                    1,
                ],
            ),
            True,
        ),
        # Pure literal arithmetic: nothing to sample, no viz.sd anywhere.
        (ArithmeticExpression(op="+", args=[1, 2]), False),
        # viz.sd mixed with a feature property: no LUT can fold a
        # per-feature operand away, stays the confirmed permanent wall.
        (
            ArithmeticExpression(
                op="*",
                args=[SystemIdentifier(sysId="viz.sd"), PropertyRef(property="a")],
            ),
            False,
        ),
        (PropertyRef(property="a"), False),
        (42, False),
    ],
)
def test_is_viz_sd_arithmetic(value, expected):
    assert is_viz_sd_arithmetic(value) is expected


def test_step_lut_for_viz_sd_samples_zoom_6_to_18():
    """The LUT samples 13 integer zoom levels (6-18 inclusive, matching
    ecere/libCartoSym's own step-sampling range for an analogous
    problem — see the module docstring), each value the formula
    evaluated with ``viz.sd`` substituted by that level's Web Mercator
    scale denominator.
    """
    from pycartosym.codecs.maplibre._zoom import scale_denominator_from_zoom

    expr = ArithmeticExpression(op="/", args=[SystemIdentifier(sysId="viz.sd"), 1000])
    lut = step_lut_for_viz_sd(expr)

    assert lut[0] == "step"
    assert lut[1] == ["zoom"]
    # "step" + ["zoom"] + out0, then (stop, out) pairs for zoom levels
    # 7..18 -> 2 + 1 + 2*12 = 27
    assert len(lut) == 27
    assert lut[2] == scale_denominator_from_zoom(6) / 1000
    stops = lut[3::2]
    outputs = lut[4::2]
    assert stops == list(range(7, 19))
    for zoom, out in zip(range(7, 19), outputs):
        assert out == scale_denominator_from_zoom(zoom) / 1000


def test_zoom_nested_in_arithmetic_raises():
    """A bare ``["zoom"]`` has no mapping of its own outside a top-level
    ``step``/``interpolate`` input — nested inside arithmetic (however it
    got there) it's an honest, undecomposable gap, not just unsupported
    when it happens to spell out the scale-denominator formula.
    """
    with pytest.raises(NotImplementedError):
        maplibre_expr_to_value(["/", 999, ["*", 100, ["^", 2, ["zoom"]]]], "prop")


@pytest.mark.parametrize("mb_expr, _value", ROUND_TRIP)
def test_expression_through_style_model(mb_expr, _value):
    """A value expression validates through Fill.color and writes back
    to the exact same MapLibre array — the Style model is the pivot, per
    this project's conversion pipeline.
    """
    from pycartosym.models.styles import Style

    color = maplibre_expr_to_value(mb_expr, "c")
    style = Style.model_validate(
        {
            "stylingRules": [
                {
                    "name": "r",
                    "symbolizer": {"fill": {"color": color}},
                }
            ]
        }
    )
    color = style.styling_rules[0].symbolizer.fill.color
    assert value_to_maplibre_expr(color, "fill.color") == mb_expr


def test_is_viz_sd_arithmetic_rejects_a_foreign_sysid_inside_arithmetic():
    """Only `viz.sd` may be sampled; another sysId in arithmetic is rejected."""
    value = ArithmeticExpression(op="*", args=[SystemIdentifier(sysId="viz.other"), 2])
    assert is_viz_sd_arithmetic(value) is False
