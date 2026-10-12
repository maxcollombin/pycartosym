"""MapLibre zoom-range visibility <-> CartoSym scale-denominator selectors.

CartoSym has no zoom-level concept — the OGC conceptual model's selector
vocabulary only knows a scale denominator (``viz.sd``, the same sysId the
SLD/SE codec's ``se:Min/MaxScaleDenominator`` mapping uses, see
:mod:`..sld._filter`). A MapLibre zoom level is converted to/from a scale
denominator via the standard "spherical Web Mercator" convention: a 256px
tile, the OGC standard rendering pixel size of 0.28mm (WMS 1.3.0 / SE /
WMTS), and the WGS84 semi-major axis treated as a sphere —

    scaleDenominator(zoom) = (2 * pi * 6378137) / (256 * 0.00028 * 2**zoom)

These constants are fixed, not configurable by this codec — matching OGC
CartoSym's own reference implementation, ecere/libCartoSym, whose MapLibre
codec (``MapboxStyles/gggLevels.ec``) uses the same formula (expressed
there via that project's internal geodesic grid with a level offset, but
algebraically identical) with the same fixed 256px/0.28mm/WGS84-major
constants, never exposed as options either.

MapLibre's own zoom-range semantics are asymmetric — a layer is visible
when ``minzoom <= zoom < maxzoom`` — which, since scale denominator
decreases as zoom increases, translates to exactly two representable
``viz.sd`` bound shapes: ``viz.sd <= scaleDenominator(minzoom)`` and
``viz.sd > scaleDenominator(maxzoom)``. Only those two shapes round-trip
through ``minzoom``/``maxzoom`` — e.g. a selector inherited from the
SLD/SE codec's own ``>=``/``<`` scale-range shape does not carry over
this way. A ``viz.sd`` bound using the other strictness (``<``, ``>=``)
or compared with ``=``/``!=`` has no *minzoom/maxzoom* equivalent, full
stop: ``minzoom``'s ``zoom >= minzoom`` is a closed (inclusive) bound on
a continuous zoom, and a strict bound like ``zoom > z`` has no smallest
representable closed lower bound. Rather than approximate this away
(rounding to the nearest representable shape), :func:`.selector_to_filter`
falls back to a MapLibre ``filter`` conjunct on the ``["zoom"]``
expression instead (see :func:`zoom_filter_conjunct`) — exact, but,
per the MapLibre style spec's own ``filter`` documentation, evaluated
only at integer zoom levels rather than continuously like
``minzoom``/``maxzoom``.

Known limitations, both inherent to mapping a zoom level (a tile-pyramid
concept) onto a scale denominator (a cartographic-scale concept), not bugs
in the formula above:

- It is only exact at the equator — Web Mercator's scale factor grows
  with latitude, so a MapLibre style authored with a real-world scale in
  mind will read back a ``viz.sd`` that is only approximate away from the
  equator.
- Unlike ecere/libCartoSym, this codec keeps the scale denominator exactly
  as computed rather than rounding it to a "nice" round number
  (``verbalRound``/``verbalRound2`` there) — so a zoom-derived ``viz.sd``
  produced by this codec will not match the rounded value a real CS-JSON
  file produced by ecere/libCartoSym would carry for the same MapLibre
  style. This keeps the zoom -> ``viz.sd`` -> zoom round trip exact for
  integer zoom levels (this codec's usual fixed-point round-trip
  convention), trading away byte-for-byte parity with that other tool's
  output.
"""

from __future__ import annotations

import math
from typing import Any

_SCALE_SYSID = "viz.sd"

# 256px tile, WGS84 semi-major axis treated as a sphere (spherical Web
# Mercator), OGC's standard 0.28mm rendering pixel size — fixed, not
# configurable (see module docstring).
_TILE_PIXELS = 256.0
_EARTH_CIRCUMFERENCE_M = 2 * math.pi * 6378137.0
_PIXEL_SIZE_M = 0.00028

_FLIP_OP = {
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "=": "=",
    "!=": "!=",
    "<>": "<>",
}


def scale_denominator_from_zoom(zoom: float) -> float:
    """Return the Web Mercator scale denominator for MapLibre zoom level *zoom*."""
    return _EARTH_CIRCUMFERENCE_M / (_TILE_PIXELS * _PIXEL_SIZE_M * 2**zoom)


def zoom_from_scale_denominator(sd: float) -> int | float:
    """Inverse of :func:`scale_denominator_from_zoom`.

    Integral results come back as ``int`` — a zoom that round-trips
    through :func:`scale_denominator_from_zoom` and back lands on the
    original integer value exactly (module docstring); this only clears
    floating-point noise around that value, it does not change it.
    """
    zoom = math.log2(_EARTH_CIRCUMFERENCE_M / (_TILE_PIXELS * _PIXEL_SIZE_M * sd))
    rounded = round(zoom, 9)
    return int(rounded) if rounded.is_integer() else rounded


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _flatten_and(selector: Any) -> list[Any]:
    """Flatten a nested ``{"op": "and", ...}`` chain into a list of conjuncts.

    Only ``and`` is descended into — ``or``/``not``/comparisons flatten to
    a single-element list containing themselves. Mirrors
    ``..sld._filter._flatten_and_conjuncts``.
    """
    if (
        isinstance(selector, dict)
        and selector.get("op") == "and"
        and isinstance(selector.get("args"), list)
    ):
        out: list[Any] = []
        for arg in selector["args"]:
            out.extend(_flatten_and(arg))
        return out
    return [selector]


def _reassemble_and(conjuncts: list[Any]) -> Any | None:
    if not conjuncts:
        return None
    if len(conjuncts) == 1:
        return conjuncts[0]
    return {"op": "and", "args": conjuncts}


def _viz_sd_operand(args: list[Any], op: str) -> tuple[str, Any] | None:
    """Detect a 2-arg comparison's ``viz.sd`` operand, either order.

    Returns ``(op, value)`` with *op* re-oriented so ``viz.sd`` reads as
    the left operand (``N >= viz.sd`` normalises to ``viz.sd <= N``), and
    *value* the other, numeric operand. ``None`` if *args* is not a
    ``viz.sd``-vs-number comparison at all.
    """
    if len(args) != 2:
        return None
    left, right = args
    if (
        isinstance(left, dict)
        and left.get("sysId") == _SCALE_SYSID
        and _is_number(right)
    ):
        return op, right
    if (
        isinstance(right, dict)
        and right.get("sysId") == _SCALE_SYSID
        and _is_number(left)
    ):
        return _FLIP_OP.get(op, ""), left
    return None


def _zoom_bound(expr: Any) -> tuple[str, Any] | None:
    """Classify *expr* as a MapLibre-representable ``viz.sd`` zoom bound.

    Returns ``("minzoom", value)`` for the ``viz.sd <= value`` shape (a
    ``minzoom``) or ``("maxzoom", value)`` for the ``viz.sd > value``
    shape (a ``maxzoom``) — see the module docstring for why only these
    two exact shapes round-trip through ``minzoom``/``maxzoom``. ``None``
    if *expr* is not a ``viz.sd`` comparison at all, **or** if it is one
    with no ``minzoom``/``maxzoom`` shape (``<``, ``>=``, ``=``, ``!=``) —
    the caller (:func:`.selector_to_filter`) falls back to
    :func:`zoom_filter_conjunct` for those instead of raising.
    """
    if not (isinstance(expr, dict) and isinstance(expr.get("args"), list)):
        return None
    raw_op = expr.get("op")
    detected = _viz_sd_operand(expr["args"], raw_op if isinstance(raw_op, str) else "")
    if detected is None:
        return None
    op, value = detected
    if op == "<=":
        return "minzoom", value
    if op == ">":
        return "maxzoom", value
    return None


# MapLibre filter-expression comparison op for a viz.sd bound with no
# minzoom/maxzoom shape (see the module docstring) — the equivalent
# ["zoom"] comparison, direction-flipped to match scale denominator
# decreasing as zoom increases.
_STRICT_TO_FILTER_OP = {"<": ">", ">=": "<=", "=": "==", "!=": "!=", "<>": "!="}


def zoom_filter_conjunct(expr: Any) -> list[Any] | None:
    """Match a ``viz.sd`` comparison with no ``minzoom``/``maxzoom`` shape.

    Returned as a MapLibre ``filter`` conjunct on the ``["zoom"]``
    expression instead. See the module docstring for why
    ``<``/``>=``/``=``/``!=``/``<>`` need this
    fallback rather than a (rounded, inexact) ``minzoom``/``maxzoom``.
    ``None`` if *expr* is not such a comparison — including a ``viz.sd``
    comparison :func:`_zoom_bound` already maps to minzoom/maxzoom, or one
    that is not a ``viz.sd`` comparison at all.
    """
    if not (isinstance(expr, dict) and isinstance(expr.get("args"), list)):
        return None
    raw_op = expr.get("op")
    detected = _viz_sd_operand(expr["args"], raw_op if isinstance(raw_op, str) else "")
    if detected is None:
        return None
    op, value = detected
    filter_op = _STRICT_TO_FILTER_OP.get(op)
    if filter_op is None:
        return None
    return [filter_op, ["zoom"], zoom_from_scale_denominator(value)]


def extract_zoom_range(
    selector: dict | None,
) -> tuple[int | float | None, int | float | None, dict | None]:
    """Split MapLibre-representable ``viz.sd`` conjuncts out of *selector*.

    Pulls the ``viz.sd <= N`` / ``viz.sd > N`` conjuncts out of an
    arbitrarily-nested ``and`` chain for the caller to emit as a layer's
    ``minzoom``/``maxzoom``; whatever is left stays for the MapLibre
    ``filter``.

    Returns ``(minzoom, maxzoom, remaining_selector)``. When several
    bounds land on the same side, the tightest (highest resulting
    ``minzoom``, or lowest resulting ``maxzoom``) wins.
    """
    if selector is None:
        return None, None, None
    upper_sd: Any = None  # tightest viz.sd <= N -> highest minzoom
    lower_sd: Any = None  # tightest viz.sd > N -> lowest maxzoom
    remaining: list[Any] = []
    for conjunct in _flatten_and(selector):
        bound = _zoom_bound(conjunct)
        if bound is None:
            remaining.append(conjunct)
            continue
        kind, value = bound
        if kind == "minzoom":
            if upper_sd is None or value < upper_sd:
                upper_sd = value
        else:
            if lower_sd is None or value > lower_sd:
                lower_sd = value
    minzoom = zoom_from_scale_denominator(upper_sd) if upper_sd is not None else None
    maxzoom = zoom_from_scale_denominator(lower_sd) if lower_sd is not None else None
    return minzoom, maxzoom, _reassemble_and(remaining)


def merge_zoom_range(
    minzoom: Any,
    maxzoom: Any,
    selector: dict | None,
) -> dict | None:
    """Reader-side inverse of :func:`extract_zoom_range`.

    ``minzoom M`` -> ``viz.sd <= scaleDenominator(M)`` and
    ``maxzoom N`` -> ``viz.sd > scaleDenominator(N)``, AND-merged ahead of
    any selector parsed from the layer ``filter``. MapLibre's implicit
    default ``minzoom: 0`` means "no restriction" and is dropped rather
    than reconstructed as an explicit (harmlessly enormous, but noisy)
    bound — mirrors the SLD/SE codec's identical treatment of a zero
    ``se:MinScaleDenominator``.
    """
    conjuncts: list[Any] = []
    if minzoom is not None and minzoom != 0:
        conjuncts.append(
            {
                "op": "<=",
                "args": [
                    {"sysId": _SCALE_SYSID},
                    scale_denominator_from_zoom(minzoom),
                ],
            }
        )
    if maxzoom is not None:
        conjuncts.append(
            {
                "op": ">",
                "args": [
                    {"sysId": _SCALE_SYSID},
                    scale_denominator_from_zoom(maxzoom),
                ],
            }
        )
    if selector is not None:
        conjuncts.append(selector)
    return _reassemble_and(conjuncts)
