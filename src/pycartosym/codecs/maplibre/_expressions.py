"""MapLibre value-expression arrays <-> CartoSym value expressions.

Scope: the six MapLibre operators this pass originally targeted — ``get``,
``case``, ``match``, ``interpolate``, ``step``, ``coalesce`` — mapped onto
the typed models in :mod:`pycartosym.models.value_expressions`, plus the
``literal`` and the 5 binary arithmetic operators (``+``/``-``/``*``/``/``/``^``, the
CartoSym-JSON schema's own ``arithmeticExpression`` op set — see
:mod:`pycartosym.models.value_expressions`'s ``ArithmeticExpression``),
which MapLibre spells identically. Every other MapLibre expression
operator (comparisons, ``all``/``any``/``!``, a bare ``zoom``, the string
operators, ``interpolate-hcl``/``-lab``, ``let``/``var``, ...) still
raises :exc:`NotImplementedError` naming the operator — a deliberate
scope boundary, not an oversight.

A ``SystemIdentifier`` (OGC issue #115's ``viz.sd``, the current scale
denominator) is a **confirmed permanent wall in this codec** for the
general case, not a missing-wiring gap — same conclusion as the SLD/SE
codec, for a different reason: the real MapLibre style spec restricts a
``["zoom"]`` expression to being the *sole, top-level* input of a
``step``/``interpolate`` call — it cannot be nested inside arithmetic
(confirmed against the real ``gl-style-validate`` CLI, not just this
codec's own JSON-shape checks). An earlier version of this module built a
``["zoom"]``-driven arithmetic formula for ``viz.sd`` that validated as
the right JSON *shape* but was never actually valid MapLibre syntax —
caught only once a round-trip test was run through the real validator
instead of comparing JSON shapes.

**One special case is handled, not a wall**: when the value passed to
``writer.py``'s ``_literal`` (i.e. an entire top-level paint/layout
property, never a value nested inside another expression) is built only
from ``viz.sd`` and numeric literals — see :func:`is_viz_sd_arithmetic` —
the enclosing arithmetic's constant scaling is folded into a MapLibre
``step`` lookup table instead (:func:`step_lut_for_viz_sd`), sampling the
formula at each integer zoom level 6-18 and making the ``step`` itself the
top-level value, exactly like the technique OGC's own reference
implementation (``ecere/libCartoSym``'s ``mbglWriter.ec:381-403``) applies
to an analogous metres-to-pixels problem. This trades exactness for a
piecewise-constant approximation and an intentionally asymmetric
round-trip: reading a sampled ``step`` back does **not** attempt to
recover the original symbolic formula, it lands on
``_layers.py``'s existing ``step(["zoom"])`` -> N ``viz.sd``-bounded
rules machinery (already there for a hand-authored ``step``, added in
PR #70) — each rule getting that segment's *literal* sampled value. Any
other shape (``viz.sd`` combined with a ``PropertyRef``, or nested inside
``case``/``match``/``coalesce``/``interpolate`` rather than being the
property's entire value) still raises unconditionally — folding only
helps when the ``step`` can *be* the top-level value.

Legacy MapLibre "zoom functions" (``{"stops": [...]}``) are a separate,
unrelated value shape and stay out of scope here too (rejected in
``_layers.py`` before this module ever sees them).
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from ...models.value_expressions import (
    ArithmeticExpression,
    CaseExpression,
    CoalesceExpression,
    InterpolateExpression,
    MatchExpression,
    PropertyRef,
    StepExpression,
    SystemIdentifier,
)
from ._zoom import scale_denominator_from_zoom

# A MapLibre value that is already a plain JSON scalar, not an expression.
_SCALAR = (str, int, float, bool, type(None))

_INTERPOLATION_TYPES = frozenset({"linear", "exponential", "cubic-bezier"})

_ARITHMETIC_OPS = frozenset({"+", "-", "*", "/", "^"})

_ARITHMETIC_EVAL: dict[str, Callable[[float, float], float]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "^": operator.pow,
}

_VIZ_SD_SYSID = "viz.sd"

# Integer zoom levels sampled to build a viz.sd step lookup table (see
# step_lut_for_viz_sd) -- matches the range ecere/libCartoSym's own
# step-sampling technique for an analogous metres->pixels problem uses
# (mbglWriter.ec:381-403).
_VIZ_SD_STEP_ZOOM_LEVELS = range(6, 19)


def coerce_numeric_expr(value: Any) -> Any:
    """Best-effort coercion of a plain expression-shaped dict to its typed class.

    A value nested inside a graphic element (``Marker.elements`` is typed
    ``Any`` — see ``models/symbolizers.py`` — so Pydantic never validates
    anything under it, unlike a direct ``Symbolizer`` field like
    ``Stroke.width``) stays a raw dict rather than a real
    ``PropertyRef``/``ArithmeticExpression``/``SystemIdentifier`` instance,
    which :func:`value_to_maplibre_expr`'s ``isinstance`` checks need.
    Passes through unchanged if already typed or not one of these three
    shapes (e.g. a plain literal, or one of the other
    :mod:`.models.value_expressions` classes reachable only from a
    directly-typed field today). Public (no leading underscore) — also
    used by ``writer.py`` for ``Dot.size``, which needs to detect a
    property/arithmetic/system-identifier expression itself (to divide it
    by 2 symbolically) rather than just recognise one inside a call it
    delegates to.
    """
    if isinstance(value, (PropertyRef, ArithmeticExpression, SystemIdentifier)):
        return value
    if isinstance(value, dict):
        if "property" in value:
            return PropertyRef.model_validate(value)
        if "sysId" in value:
            return SystemIdentifier.model_validate(value)
        if "op" in value and value.get("op") in _ARITHMETIC_OPS and "args" in value:
            return ArithmeticExpression.model_validate(value)
    return value


def is_viz_sd_arithmetic(value: Any) -> bool:
    """True if *value* is built only from ``viz.sd`` and numeric literals.

    Recognises a bare ``SystemIdentifier("viz.sd")`` or an
    ``ArithmeticExpression`` combining only that and numeric literals —
    the one shape :func:`step_lut_for_viz_sd` can sample into a MapLibre
    ``step`` lookup table (see module docstring). A different ``sysId``,
    any ``PropertyRef`` operand, or a plain scalar on its own (nothing to
    sample) all return ``False``.
    """
    if isinstance(value, SystemIdentifier):
        return value.sysId == _VIZ_SD_SYSID
    if not isinstance(value, ArithmeticExpression):
        return False
    leaves = _flatten_arithmetic(value)
    return any(isinstance(leaf, SystemIdentifier) for leaf in leaves) and all(
        _is_number(leaf)
        or (isinstance(leaf, SystemIdentifier) and leaf.sysId == _VIZ_SD_SYSID)
        for leaf in leaves
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _flatten_arithmetic(value: Any) -> list[Any]:
    if isinstance(value, ArithmeticExpression):
        return [leaf for arg in value.args for leaf in _flatten_arithmetic(arg)]
    return [value]


def _eval_viz_sd_arithmetic(value: Any, sd: float) -> float:
    """Evaluate *value* (see :func:`is_viz_sd_arithmetic`) with ``viz.sd`` = *sd*."""
    if isinstance(value, SystemIdentifier):
        return sd
    if isinstance(value, ArithmeticExpression):
        a, b = (_eval_viz_sd_arithmetic(arg, sd) for arg in value.args)
        return _ARITHMETIC_EVAL[value.op](a, b)
    return float(value)


def step_lut_for_viz_sd(value: Any) -> list[Any]:
    """Sample a ``viz.sd``-only expression into a MapLibre ``step`` lookup table.

    *value* must satisfy :func:`is_viz_sd_arithmetic`. Evaluates it at each
    integer zoom level in :data:`_VIZ_SD_STEP_ZOOM_LEVELS`, converting zoom
    to a scale denominator via :func:`._zoom.scale_denominator_from_zoom`
    (the same Web-Mercator convention the ``viz.sd``/zoom selector mapping
    already uses), and returns
    ``["step", ["zoom"], v0, z1, v1, z2, v2, ..., zN, vN]`` — the sampled
    value below the lowest level, then a new value at each subsequent
    integer level (see ``_layers.py``'s ``_step_value_at`` for the exact
    piecewise-constant semantics this LUT is read back with on the
    round trip). An approximation, not an exact inverse — see the module
    docstring.
    """
    zooms = list(_VIZ_SD_STEP_ZOOM_LEVELS)
    samples = [
        _eval_viz_sd_arithmetic(value, scale_denominator_from_zoom(z)) for z in zooms
    ]
    step: list[Any] = ["step", ["zoom"], samples[0]]
    for z, v in zip(zooms[1:], samples[1:]):
        step.extend([z, v])
    return step


def maplibre_expr_to_value(value: Any, prop: str) -> Any:
    """Convert one MapLibre paint/layout value to its CartoSym equivalent.

    A literal (number / string / bool / ``None``) passes through unchanged.
    A MapLibre expression array becomes the matching dict shape
    (``{"property": ...}`` for ``get``, ``{"op": ..., "args": [...]}`` for
    the other operators, including binary arithmetic; ``literal`` yields
    its bare argument) for the Pydantic ``Style`` model to
    validate into a typed :mod:`.value_expressions` model downstream.

    Raises:
        NotImplementedError: *value* is a MapLibre expression using an
            operator this codec does not map.
    """
    if isinstance(value, _SCALAR):
        return value
    if not isinstance(value, list) or not value:
        raise NotImplementedError(
            f"{prop}: {value!r} is not a supported MapLibre value or expression"
        )

    op, args = value[0], value[1:]

    if op in _ARITHMETIC_OPS:
        if len(args) != 2:
            raise NotImplementedError(
                f"{prop}: only 2-argument [{op!r}, a, b] arithmetic maps in "
                "this codec"
            )
        return {
            "op": op,
            "args": [maplibre_expr_to_value(a, prop) for a in args],
        }
    if op == "literal":
        if len(args) != 1:
            raise NotImplementedError(f"{prop}: malformed ['literal', ...] expression")
        return args[0]
    if op == "get":
        if len(args) != 1 or not isinstance(args[0], str):
            raise NotImplementedError(
                f"{prop}: only single-argument ['get', 'property'] maps in this codec"
            )
        return {"property": args[0]}
    if op == "case":
        if len(args) < 3 or len(args) % 2 == 0:
            raise NotImplementedError(
                f"{prop}: malformed ['case', ...] expression (need "
                "cond, out, ..., fallback)"
            )
        return {"op": "case", "args": [maplibre_expr_to_value(a, prop) for a in args]}
    if op == "match":
        return _match_to_value(args, prop)
    if op == "step":
        if len(args) < 2 or len(args) % 2 != 0:
            raise NotImplementedError(
                f"{prop}: malformed ['step', ...] expression (need "
                "input, output0, stop1, output1, ...)"
            )
        return {"op": "step", "args": [maplibre_expr_to_value(a, prop) for a in args]}
    if op == "interpolate":
        return _interpolate_to_value(args, prop)
    if op == "coalesce":
        if not args:
            raise NotImplementedError(f"{prop}: malformed ['coalesce', ...] expression")
        return {
            "op": "coalesce",
            "args": [maplibre_expr_to_value(a, prop) for a in args],
        }
    raise NotImplementedError(
        f"{prop}: MapLibre expression operator {op!r} is not mapped by this codec"
    )


def _match_label(label: Any, prop: str) -> Any:
    """Return a ``match`` label: a literal, or a literal array of literals."""
    if isinstance(label, list):
        if not all(isinstance(item, _SCALAR) for item in label):
            raise NotImplementedError(
                f"{prop}: ['match', ...] label group {label!r} must be literal values"
            )
        return label
    if isinstance(label, _SCALAR):
        return label
    raise NotImplementedError(
        f"{prop}: ['match', ...] label {label!r} must be a literal"
    )


def _match_to_value(args: list[Any], prop: str) -> dict[str, Any]:
    if len(args) < 3:
        raise NotImplementedError(f"{prop}: malformed ['match', ...] expression")
    body, fallback = args[1:-1], args[-1]
    if len(body) % 2 != 0:
        raise NotImplementedError(f"{prop}: malformed ['match', ...] expression")
    out: list[Any] = [maplibre_expr_to_value(args[0], prop)]
    for i in range(0, len(body), 2):
        out.append(_match_label(body[i], prop))
        out.append(maplibre_expr_to_value(body[i + 1], prop))
    out.append(maplibre_expr_to_value(fallback, prop))
    return {"op": "match", "args": out}


def _interpolate_to_value(args: list[Any], prop: str) -> dict[str, Any]:
    if len(args) < 3:
        raise NotImplementedError(f"{prop}: malformed ['interpolate', ...] expression")
    interp_spec, input_expr, *rest = args
    if not isinstance(interp_spec, list) or not interp_spec:
        raise NotImplementedError(
            f"{prop}: ['interpolate', ...] needs an interpolation-type array"
        )
    interp_type = interp_spec[0]
    if interp_type not in _INTERPOLATION_TYPES:
        raise NotImplementedError(
            f"{prop}: interpolation type {interp_type!r} is not mapped by this codec"
        )

    out: dict[str, Any] = {
        "op": "interpolate",
        "interpolation": interp_type,
        "args": [maplibre_expr_to_value(input_expr, prop)]
        + [maplibre_expr_to_value(a, prop) for a in rest],
    }
    if interp_type == "exponential":
        if len(interp_spec) != 2 or not isinstance(interp_spec[1], (int, float)):
            raise NotImplementedError(
                f"{prop}: ['exponential', base] needs a numeric base"
            )
        out["base"] = interp_spec[1]
    elif interp_type == "cubic-bezier":
        if len(interp_spec) != 5 or not all(
            isinstance(v, (int, float)) for v in interp_spec[1:]
        ):
            raise NotImplementedError(
                f"{prop}: ['cubic-bezier', x1, y1, x2, y2] needs 4 numeric "
                "control points"
            )
        out["controlPoints"] = list(interp_spec[1:])
    return out


def value_to_maplibre_expr(value: Any, prop: str) -> Any:
    """Inverse of :func:`maplibre_expr_to_value`.

    Raises:
        NotImplementedError: *value* is not a literal or one of the
            typed :mod:`.value_expressions` models this codec maps.
    """
    try:
        value = coerce_numeric_expr(value)
    except ValidationError as exc:
        raise NotImplementedError(
            f"{prop}: {value!r} is not a valid CartoSym value expression"
        ) from exc
    if isinstance(value, PropertyRef):
        return ["get", value.property]
    if isinstance(value, ArithmeticExpression):
        return [value.op, *(value_to_maplibre_expr(a, prop) for a in value.args)]
    if isinstance(value, SystemIdentifier):
        # Confirmed permanent wall (see module docstring) — the real
        # MapLibre style spec only allows a ["zoom"] input as the sole,
        # top-level argument of step/interpolate, never nested inside
        # arithmetic, so there is no faithful, round-trippable mapping for
        # any SystemIdentifier here, viz.sd included.
        raise NotImplementedError(
            f"{prop}: system identifier {value.sysId!r} has no MapLibre "
            "expression mapping in this codec"
        )
    if isinstance(value, CaseExpression):
        return ["case", *(value_to_maplibre_expr(a, prop) for a in value.args)]
    if isinstance(value, MatchExpression):
        return _match_to_expr(value, prop)
    if isinstance(value, StepExpression):
        return ["step", *(value_to_maplibre_expr(a, prop) for a in value.args)]
    if isinstance(value, InterpolateExpression):
        return _interpolate_to_expr(value, prop)
    if isinstance(value, CoalesceExpression):
        return ["coalesce", *(value_to_maplibre_expr(a, prop) for a in value.args)]
    if isinstance(value, _SCALAR):
        return value
    raise NotImplementedError(
        f"{prop}: {value!r} has no MapLibre expression mapping in this codec"
    )


def _match_to_expr(value: MatchExpression, prop: str) -> list[Any]:
    args = value.args
    out: list[Any] = ["match", value_to_maplibre_expr(args[0], prop)]
    body, fallback = args[1:-1], args[-1]
    for i in range(0, len(body), 2):
        out.append(body[i])  # label(s): already a plain literal / literal list
        out.append(value_to_maplibre_expr(body[i + 1], prop))
    out.append(value_to_maplibre_expr(fallback, prop))
    return out


def _interpolate_to_expr(value: InterpolateExpression, prop: str) -> list[Any]:
    if value.interpolation == "exponential":
        base = value.base if value.base is not None else 1
        interp_spec: list[Any] = ["exponential", base]
    elif value.interpolation == "cubic-bezier":
        if not value.control_points or len(value.control_points) != 4:
            raise NotImplementedError(
                f"{prop}: cubic-bezier interpolation needs 4 control points"
            )
        interp_spec = ["cubic-bezier", *value.control_points]
    else:
        interp_spec = ["linear"]
    return [
        "interpolate",
        interp_spec,
        *(value_to_maplibre_expr(a, prop) for a in value.args),
    ]
