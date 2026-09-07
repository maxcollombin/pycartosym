"""MapLibre / MapBox GL Style writer — CartoSym Style models → style JSON.

The inverse of :mod:`.reader`, and with the same scope: a ``fill`` /
``line`` / ``marker`` / ``label`` symbolizer with constant values maps to
a MapLibre layer (``fill`` / ``line`` / ``circle`` / ``symbol``); a rule
selector maps to the layer ``filter``, except any ``viz.sd`` conjuncts
that match MapLibre's own zoom-range shape, which map to
``minzoom``/``maxzoom`` instead (see :mod:`._zoom`), and a
``sysId dataLayer.id`` equality conjunct, dropped rather than mapped (see
:func:`._filter.strip_datalayer_id` for why) — likewise a
``sysId dataLayer.type`` conjunct whose literal matches the kind of
layer(s) the rule was actually routed to (``vector`` for
fill/line/circle/symbol/background, ``coverage`` for raster; see
:func:`_strip_redundant_datalayer_type`), provably redundant once
routing has already happened. A fill-only symbolizer
carrying the ``vendor.maplibre.layer-type: "background"`` extension (see
:mod:`._layers`) maps to a ``background`` layer instead of ``fill``.
A coverage symbolizer maps separately (see below); graphic element types
other than ``Dot``/``Circle``/``Image``/``Text``, and non-literal values,
raise :exc:`NotImplementedError`.

Each element of ``marker.elements``/``label.elements`` maps to its own
point layer, dispatched by the element's own ``type`` — a ``Dot``/
``Circle`` to a ``circle`` layer, an ``Image`` to a ``symbol`` layer's
``icon-image``, a ``Text`` to a ``symbol`` layer's ``text-field`` — not
by which of ``marker``/``label`` it came from, which this codec treats
symmetrically (see :func:`_point_layer_specs`). A ``Dot`` — ``1-core``,
stroke-only by design — draws as a ``circle`` layer's fill (``color``)
and radius (``size / 2``, ``size`` being a diameter), matching the SLD/SE
codec's own ``Dot`` mapping; unlike a ``2-shapes`` ``Circle``, it has no
outline. The common case of exactly one ``Image`` marker element and
exactly one ``Text`` label element still merges into a single combined
``symbol`` layer (icon + text together), as before this generalisation.

A symbolizer combining more than one of {fill, a full stroke (width or
opacity, not just a plain outline colour), a marker/label point layer}
has no single-layer MapLibre equivalent, so it maps to *several* layers
instead (see :func:`_rule_to_layers`) — one CartoSym rule can expand to
several ``layers`` entries. They share the rule's ``filter``/``minzoom``/
``maxzoom``/``visibility`` and are ordered fill, then line, then the
point layers in ``marker.elements``-then-``label.elements`` order (so a
point layer draws on top of its area/line siblings, the conventional
order); their ``id`` is disambiguated with a ``-fill``/``-line``/
``-circle``/``-symbol`` suffix — several point layers of the *same* kind
get a further numeric suffix (``-circle-1``/``-circle-2``…) — a bare rule
name is kept only when a single layer is produced, unchanged from
before. A stroke with only a ``color`` (no ``width``/``opacity``) stays
inlined as the fill layer's ``fill-outline-color``, as before, rather
than spawning a separate line layer — so ``stroke.dashPattern`` (see
below), which needs a line layer of its own to attach ``line-dasharray``
to, always raises on that inlined path.

``stroke.dashPattern`` maps to ``line-dasharray`` on a ``line``
layer, each length divided by ``stroke.width`` in px — CartoSym/SLD dash
lengths are absolute px, MapLibre's are multiples of the line's own
width (see :func:`_dash_array`). An ``{index, value}`` cascade-override
fragment (``codecs/_cascade.py`` does not resolve indexed overrides for
``dashPattern``, unlike ``elements``) raises, as does a missing/
non-literal ``stroke.width`` to scale by.

``StylingRule.nestedRules`` (a cascading refinement, e.g.
``[attr = value] { ... }`` narrowing a parent rule) has no MapLibre
nesting equivalent — ``layers`` is a flat list — so it is flattened into
independent rules first (see :func:`_flatten_rules`, reusing
:mod:`..._cascade`); a flattened rule with no name of its own inherits
its nearest named ancestor's, disambiguated with a positional suffix. A
rule that draws nothing (visibility/opacity/zOrder only — typically a
cascade's base/gate rule) is dropped rather than raising (see
:func:`_is_empty_of_paint`); one that instead carries unsupported
(raster) content still raises.

A CartoSym style has no data-source concept, so the output declares one
synthetic empty GeoJSON source (``cartosym``) that every vector layer
references — enough to satisfy the MapLibre style specification. A
coverage symbolizer (``singleChannel``/``colorMap``/``hillShading``…)
routes to a *different* synthetic source instead — a placeholder
``raster-dem`` (``cartosym-dem``) — since none of these fields may combine
with ``fill``/``stroke``/``marker``/``label`` in one rule; see
:mod:`._raster` for the achievable subset (``color-relief``/``hillshade``)
and the honest gaps (band selection/arithmetic, per-channel alpha, an
opacity ramp, ``hillShading.factor``, a shading-intensity colour/opacity
ramp).
"""

from __future__ import annotations

import math
import re
from typing import Any

from ...models.styles import Style, StylingRule
from ...models.types import UnitType, UnitValue
from ...models.value_expressions import (
    ArithmeticExpression,
    PropertyRef,
    SystemIdentifier,
)
from .._cascade import flatten_cascade_rules
from ..base import CodecWriter
from . import _raster
from ._expressions import (
    coerce_numeric_expr,
    is_viz_sd_arithmetic,
    step_lut_for_viz_sd,
    value_to_maplibre_expr,
)
from ._filter import selector_to_filter, strip_datalayer_id
from ._layers import _ANCHOR_TO_ALIGNMENT, _ICON_ANCHOR_TO_FRACTION
from ._zoom import extract_zoom_range

_SOURCE = "cartosym"

# CartoSym (hAlignment, vAlignment) -> MapLibre text-anchor token.
_ALIGNMENT_TO_ANCHOR = {v: k for k, v in _ANCHOR_TO_ALIGNMENT.items()}

# Coverage/raster symbolizer parts (see `_raster` for what maps and what
# doesn't) — presence routes a rule to `_raster_layers` instead of the
# vector fill/line/circle/symbol path.
_RASTER_SYMBOLIZER_PARTS = (
    "color_channels",
    "alpha_channel",
    "single_channel",
    "color_map",
    "opacity_map",
    "hill_shading",
)


def _literal(value: Any, prop: str) -> Any:
    """Return a plain string / number / bool, or a mapped MapLibre expression.

    A :mod:`...models.value_expressions` model (``PropertyRef``,
    ``CaseExpression``, …) round-trips back to its MapLibre array via
    :func:`._expressions.value_to_maplibre_expr`; a ``Color``'s
    ``list[int]`` RGB(A) 0-255 form (what a CSCSS ``#rrggbb`` hex literal
    actually parses into — a named colour or ``#``-string colour stays a
    plain string and needs none of this) becomes a hex string via
    :func:`_rgb_to_hex`; a ``viz.sd``-only expression (e.g.
    ``stroke-width: viz.sd / 1000``) becomes a sampled ``step`` lookup
    table via :func:`._expressions.step_lut_for_viz_sd` — only reachable
    here, at the top level of a whole property value, never from a value
    nested inside another expression (see that function's module
    docstring for why); anything else this codec does not map (a
    ``UnitValue`` in a non-``px`` unit, …) raises.
    """
    if isinstance(value, (str, int, float, bool)):
        return value
    if (
        isinstance(value, list)
        and len(value) in (3, 4)
        and all(isinstance(c, int) and not isinstance(c, bool) for c in value)
    ):
        return _rgb_to_hex(value)
    if is_viz_sd_arithmetic(value):
        return step_lut_for_viz_sd(value)
    return value_to_maplibre_expr(value, prop)


def _rgb_to_hex(rgb: list[int]) -> str:
    """Render a 0-255 RGB(A) triple/quad as a MapLibre-compatible hex colour string."""
    hex_str = "#" + "".join(f"{c:02x}" for c in rgb[:3])
    if len(rgb) == 4:
        hex_str += f"{rgb[3]:02x}"
    return hex_str


def _px_number(value: Any, ctx: str) -> Any:
    """Unwrap a plain-pixel unit value to a bare number.

    MapLibre has no unit system of its own — a numeric paint/layout
    property (``line-width``, ``circle-radius``, ``circle-stroke-width``)
    is always already in pixels — so a CartoSym px value round-trips 1:1.
    Two shapes reach here: a validated ``UnitValue`` (a top-level
    ``Stroke.width``, going through normal Pydantic field validation) or
    a bare ``{"px": …}`` dict (a graphic-element field inside
    ``Marker.elements``, which stays an untyped ``dict`` — see
    ``models/symbolizers.py``). Anything else (a non-``px`` unit, a bare
    number, a :mod:`...models.value_expressions` model) passes through
    unchanged for :func:`_literal` to handle — a non-``px`` unit has no
    pixel-space equivalent and raises there, same as before.
    """
    if isinstance(value, UnitValue) and value.unit == UnitType.PIXELS:
        return value.value
    if isinstance(value, dict) and set(value) == {"px"}:
        return value["px"]
    return value


def _orientation_degrees(value: Any, ctx: str) -> Any:
    """Unwrap a ``Transform2D.orientation`` angle to bare degrees.

    ``FlexibleAngle`` may validate to an ``Angle`` model (``value`` +
    ``unit``) or a ``{"deg": …}``/``{"rad": …}`` dict — MapLibre's
    ``icon-rotate``/``text-rotate`` have no unit system of their own
    (always degrees), so ``rad`` input is converted here, mirroring the
    SLD/SE codec's own ``format_angle``. A bare number or a
    value-expression model passes through unchanged for :func:`_literal`
    to handle.
    """
    if hasattr(value, "value") and hasattr(value, "unit"):
        unit = value.unit
        return (
            value.value
            if str(unit) in ("deg", "AngleUnit.DEGREES")
            else math.degrees(value.value)
        )
    if isinstance(value, dict) and set(value) in ({"deg"}, {"rad"}):
        unit, v = next(iter(value.items()))
        return v if unit == "deg" else math.degrees(v)
    return value


def _reject_stroke_extras(stroke: Any, ctx: str) -> None:
    for attr in ("casing", "center_line", "pattern"):
        if getattr(stroke, attr, None) is not None:
            raise NotImplementedError(
                f"{ctx}: stroke.{attr} has no MapLibre mapping in this codec"
            )


def _dash_array(stroke: Any, ctx: str) -> list[float] | None:
    """Turn a resolved ``stroke.dashPattern`` array into a ``line-dasharray``.

    CartoSym/SLD dash lengths are absolute (the same px convention as
    ``stroke.width``); MapLibre's ``line-dasharray`` is instead in
    multiples of the line's own width ("line widths" per the vendored
    spec — "the lengths are later scaled by the line width"). Each
    length is therefore divided by ``stroke.width`` in px so the pattern
    stays faithful whatever the line width is, rather than passed
    through literally (which would only be correct at ``width == 1px``).

    Raises if ``dashPattern`` carries no resolved ``pattern`` array — an
    ``{index, value}`` cascade-override fragment, say — since
    ``codecs/_cascade.py`` does not resolve indexed overrides for
    ``dashPattern`` (only for ``marker``/``label`` ``elements``), so one
    reaching here is unflattened, not a final value; or if there is no
    literal px ``stroke.width`` to scale by.
    """
    dash_pattern = getattr(stroke, "dash_pattern", None)
    if dash_pattern is None:
        return None
    if not isinstance(dash_pattern, list):
        raise NotImplementedError(
            f"{ctx}: stroke.dashPattern with no resolved array (an "
            "unflattened index/value cascade-override fragment?) has "
            "no MapLibre mapping in this codec"
        )
    pattern = dash_pattern
    width_px = (
        _px_number(stroke.width, "stroke.width") if stroke.width is not None else None
    )
    if (
        not isinstance(width_px, (int, float))
        or isinstance(width_px, bool)
        or width_px == 0
    ):
        raise NotImplementedError(
            f"{ctx}: stroke.dashPattern needs a literal px stroke.width to "
            "convert into MapLibre's line-width-relative line-dasharray, "
            "which is missing or non-literal here"
        )
    return [p / width_px for p in pattern]


def _fill_pattern_icon_id(pattern: Any, ctx: str) -> Any:
    """Return the sprite id/URI/path a ``fill.pattern`` Image graphic names.

    Only an ``Image`` graphic maps — MapLibre's ``fill-pattern`` is always
    a sprite reference, so a ``fill.pattern`` of another graphic type
    (``Shape``, ``Text``, …) has no equivalent.
    """
    graphic_type = _attr(pattern, "type")
    if graphic_type != "Image":
        raise NotImplementedError(
            f"{ctx} of type {graphic_type!r} has no MapLibre fill-pattern "
            "mapping in this codec (only an Image graphic maps)"
        )
    image = _attr(pattern, "image")
    icon_id = _attr(image, "id") or _attr(image, "uri") or _attr(image, "path")
    if icon_id is None:
        raise NotImplementedError(
            f"{ctx} Image without id/uri/path has no MapLibre fill-pattern mapping"
        )
    return icon_id


def _fill_layer(layer_id: str, fill: Any, inline_stroke: Any) -> dict[str, Any]:
    """Build the ``fill`` layer.

    *inline_stroke* is only ever a plain-colour stroke — a stroke needing
    its own line layer is filtered out by the caller
    (:func:`_rule_to_layers`) before reaching here.
    """
    for attr in ("hatch", "dotpattern", "stipple"):
        if getattr(fill, attr, None) is not None:
            raise NotImplementedError(
                f"fill.{attr} has no MapLibre mapping in this codec"
            )

    paint: dict[str, Any] = {}
    if fill.pattern is not None:
        paint["fill-pattern"] = _literal(
            _fill_pattern_icon_id(fill.pattern, "fill.pattern"), "fill.pattern"
        )
    if fill.color is not None:
        paint["fill-color"] = _literal(fill.color, "fill.color")
    if fill.opacity is not None:
        paint["fill-opacity"] = _literal(fill.opacity, "fill.opacity")

    if inline_stroke is not None:
        _reject_stroke_extras(inline_stroke, "fill symbolizer")
        if inline_stroke.dash_pattern is not None:
            raise NotImplementedError(
                "fill symbolizer: stroke.dashPattern has no MapLibre mapping "
                "when the stroke stays inlined as fill-outline-color — no "
                "stroke.width to scale by, and fill has no dasharray paint "
                "property (give the stroke a width so it gets its own line "
                "layer instead)"
            )
        if inline_stroke.cap is not None or inline_stroke.join is not None:
            raise NotImplementedError(
                "fill symbolizer: stroke.cap/stroke.join have no MapLibre "
                "mapping when the stroke stays inlined as fill-outline-color "
                "— fill has no line-cap/line-join layout property (give the "
                "stroke a width so it gets its own line layer instead)"
            )
        if inline_stroke.color is not None:
            paint["fill-outline-color"] = _literal(inline_stroke.color, "stroke.color")

    return {"id": layer_id, "type": "fill", "source": _SOURCE, "paint": paint}


def _vendor_layer_type(sym: Any) -> str | None:
    """Return the symbolizer's ``vendor.maplibre.layer-type`` extra, if any.

    Raises on any other ``vendor.*`` extra (no other one is understood by
    this codec) or an unrecognised ``layer-type`` value — an unknown
    vendor extension must never be silently dropped.
    """
    extras = getattr(sym, "__pydantic_extra__", None) or {}
    layer_type = extras.get("vendor.maplibre.layer-type")
    unknown = [k for k in extras if k != "vendor.maplibre.layer-type"]
    if unknown:
        raise NotImplementedError(
            f"vendor extension {unknown[0]!r} has no MapLibre mapping in this codec"
        )
    if layer_type is not None and layer_type != "background":
        raise NotImplementedError(
            f"vendor.maplibre.layer-type {layer_type!r} is not a recognised value"
        )
    return layer_type


def _background_layer(layer_id: str, fill: Any, stroke: Any) -> dict[str, Any]:
    """Turn a tagged ``vendor.maplibre.layer-type: background`` ``Fill`` into a layer.

    See :func:`._layers._background_symbolizer` for why the tag exists: a
    ``background`` layer's paint is structurally identical to a ``fill``
    layer's, so this is the only way back to the right MapLibre layer
    type. Unlike ``fill``, a ``background`` layer has no ``source`` and
    no outline.
    """
    for attr in ("pattern", "hatch", "dotpattern", "stipple"):
        if getattr(fill, attr, None) is not None:
            raise NotImplementedError(
                f"fill.{attr} has no MapLibre mapping in this codec"
            )
    if stroke is not None:
        raise NotImplementedError(
            "a background layer has no outline — a stroke on a "
            "vendor.maplibre.layer-type=background symbolizer has no MapLibre "
            "mapping"
        )

    paint: dict[str, Any] = {}
    if fill.color is not None:
        paint["background-color"] = _literal(fill.color, "fill.color")
    if fill.opacity is not None:
        paint["background-opacity"] = _literal(fill.opacity, "fill.opacity")

    return {"id": layer_id, "type": "background", "paint": paint}


def _line_layer(layer_id: str, stroke: Any) -> dict[str, Any]:
    _reject_stroke_extras(stroke, "line symbolizer")
    paint: dict[str, Any] = {}
    if stroke.color is not None:
        paint["line-color"] = _literal(stroke.color, "stroke.color")
    if stroke.width is not None:
        paint["line-width"] = _literal(
            _px_number(stroke.width, "stroke.width"), "stroke.width"
        )
    if stroke.opacity is not None:
        paint["line-opacity"] = _literal(stroke.opacity, "stroke.opacity")
    dash_array = _dash_array(stroke, "line symbolizer")
    if dash_array is not None:
        paint["line-dasharray"] = dash_array
    layer: dict[str, Any] = {
        "id": layer_id,
        "type": "line",
        "source": _SOURCE,
        "paint": paint,
    }
    layout: dict[str, Any] = {}
    if stroke.cap is not None:
        layout["line-cap"] = _literal(stroke.cap, "stroke.cap")
    if stroke.join is not None:
        layout["line-join"] = _literal(stroke.join, "stroke.join")
    if layout:
        layer["layout"] = layout
    return layer


def _attr(obj: Any, key: str) -> Any:
    """Read *key* from a graphic element, which may be a dict or a Pydantic model."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _circle_paint_from_circle(circle: Any) -> dict[str, Any]:
    """Turn a ``2-shapes`` ``Circle`` element into ``circle`` paint."""
    paint: dict[str, Any] = {}
    fill = _attr(circle, "fill")
    if fill is not None and _attr(fill, "color") is not None:
        paint["circle-color"] = _literal(_attr(fill, "color"), "Circle.fill.color")

    outline = _attr(circle, "outline")
    if outline is not None:
        for cs_key, mb_key in (
            ("color", "circle-stroke-color"),
            ("thickness", "circle-stroke-width"),
            ("opacity", "circle-stroke-opacity"),
        ):
            value = _attr(outline, cs_key)
            if value is not None:
                if cs_key == "thickness":
                    value = _px_number(value, "Circle.outline.thickness")
                paint[mb_key] = _literal(value, f"Circle.outline.{cs_key}")

    radius = _attr(circle, "radius")
    if radius is not None:
        paint["circle-radius"] = _literal(
            _px_number(radius, "Circle.radius"), "Circle.radius"
        )

    opacity = _attr(circle, "opacity")
    if opacity is not None:
        paint["circle-opacity"] = _literal(opacity, "Circle.opacity")
    return paint


def _circle_paint_from_dot(dot: Any) -> dict[str, Any]:
    """Turn a ``1-core`` ``Dot`` element (``color``+``size``) into ``circle`` paint.

    Matches the SLD/SE codec's own ``Dot`` mapping
    (``_build_point_symbolizer``): ``color`` is drawn as the mark's fill —
    a ``Dot`` has no separate outline concept in this codebase's flat
    ``{color, size, opacity, position}`` element representation, and
    ``size`` is a diameter (the OGC prose: "``stroke.color``/
    ``stroke.width`` carry the dot's colour and size"; same convention as
    SLD's ``se:Size``), so ``circle-radius`` is ``size / 2``. A literal
    divides in Python directly; a property/arithmetic/system-identifier
    expression (unlike ``Circle.radius``, which has no such halving and
    so maps straight through ``_literal``) divides symbolically instead
    — wrapped in an ``ArithmeticExpression`` before reaching
    :func:`_literal`, so it round-trips and, for a ``viz.sd``-only
    formula, still qualifies for the ``step``-LUT sampling in
    ``_expressions.py``.
    """
    paint: dict[str, Any] = {}
    color = _attr(dot, "color")
    if color is not None:
        paint["circle-color"] = _literal(color, "Dot.color")

    size = _attr(dot, "size")
    if size is not None:
        size_px = _px_number(size, "Dot.size")
        if isinstance(size_px, (int, float)) and not isinstance(size_px, bool):
            paint["circle-radius"] = size_px / 2
        else:
            coerced = coerce_numeric_expr(size_px)
            if isinstance(
                coerced, (PropertyRef, ArithmeticExpression, SystemIdentifier)
            ):
                paint["circle-radius"] = _literal(
                    ArithmeticExpression(op="/", args=[coerced, 2]), "Dot.size"
                )
            else:
                raise NotImplementedError(
                    "Dot.size: only a literal px value, or a property/"
                    "arithmetic/system-identifier expression, maps to "
                    "MapLibre circle-radius in this codec"
                )

    opacity = _attr(dot, "opacity")
    if opacity is not None:
        paint["circle-opacity"] = _literal(opacity, "Dot.opacity")

    position = _attr(dot, "position")
    if position is not None:
        px = _attr(position, "x") or 0
        py = _attr(position, "y") or 0
        if (px, py) != (0, 0):
            raise NotImplementedError(
                "Dot.position offset has no MapLibre mapping in this codec "
                "(circle-translate is not wired up)"
            )
    return paint


def _circle_layer_from_element(layer_id: str, el: Any) -> dict[str, Any]:
    """Turn a single ``Circle``/``Dot`` marker/label element into a ``circle`` layer."""
    el_type = _attr(el, "type")
    if _attr(el, "transform") is not None:
        # MapLibre's `circle` layer type has no rotation-capable property
        # at all (unlike `symbol`'s icon-rotate/text-rotate) — a plain
        # circle is radially symmetric in this codec's flat
        # color+radius+outline representation, so orientation/scaling/
        # translation all have nothing to map to.
        raise NotImplementedError(
            f"{el_type}.transform has no MapLibre mapping in this codec "
            "(the circle layer type has no rotation-capable property)"
        )
    if el_type == "Circle":
        paint = _circle_paint_from_circle(el)
    elif el_type == "Dot":
        paint = _circle_paint_from_dot(el)
    else:
        raise NotImplementedError(
            f"marker/label element {el_type!r} → MapLibre circle layer "
            "(only Dot/Circle map, to a circle layer)"
        )
    return {"id": layer_id, "type": "circle", "source": _SOURCE, "paint": paint}


def _position_axis_number(value: Any, ctx: str) -> float:
    """Return a ``Graphic.position`` axis as a bare number for ``text-offset``.

    ``UnitPoint.x``/``.y`` is ``UnitValue | str | float`` once validated;
    only a bare number round-trips (see the reader's matching comment —
    the CartoSym-JSON unit tag does not survive validation on this field).
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    raise NotImplementedError(
        f"{ctx}: only a unit-less Text.position axis maps to MapLibre "
        "text-offset (an em) in this codec"
    )


def _text_layer_layout_paint(text_el: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    layout: dict[str, Any] = {}
    paint: dict[str, Any] = {}

    text = _attr(text_el, "text")
    if isinstance(text, dict) and "property" in text:
        layout["text-field"] = "{" + text["property"] + "}"
    elif isinstance(text, str):
        layout["text-field"] = text
    else:
        raise NotImplementedError(
            f"Text.text {text!r}: only a literal string or a {{property: …}} "
            "reference maps to MapLibre text-field in this codec"
        )

    position = _attr(text_el, "position")
    if position is not None:
        px = _position_axis_number(_attr(position, "x"), "Text.position.x")
        py = _position_axis_number(_attr(position, "y"), "Text.position.y")
        if px != 0 or py != 0:
            layout["text-offset"] = [px, py]

    alignment = _attr(text_el, "alignment")
    if alignment is not None:
        if isinstance(alignment, (list, tuple)) and len(alignment) == 2:
            h, v = alignment[0], alignment[1]
        else:
            h = _attr(alignment, "h_alignment") or _attr(alignment, "hAlignment")
            v = _attr(alignment, "v_alignment") or _attr(alignment, "vAlignment")
        anchor = _ALIGNMENT_TO_ANCHOR.get((h, v))
        if anchor is None:
            raise NotImplementedError(f"Text.alignment {(h, v)!r} is not mapped")
        layout["text-anchor"] = anchor

    transform = _attr(text_el, "transform")
    if transform is not None:
        for attr in ("scaling", "translation"):
            if _attr(transform, attr) is not None:
                raise NotImplementedError(
                    f"TextGraphic.transform.{attr} has no MapLibre mapping "
                    "in this codec"
                )
        orientation = _attr(transform, "orientation")
        if orientation is not None:
            layout["text-rotate"] = _literal(
                _orientation_degrees(orientation, "TextGraphic.transform.orientation"),
                "TextGraphic.transform.orientation",
            )

    font = _attr(text_el, "font")
    if font is not None:
        for attr in ("bold", "italic", "underline"):
            # A literal `false` means no more than MapLibre's own default
            # (roman, non-underlined text) — nothing to map, so it passes
            # silently. Only `true` is the real, permanent gap: MapLibre
            # selects style through the `text-font` family name itself
            # (a font-server-specific naming convention), not a boolean
            # flag, and guessing a name suffix would be exactly the kind
            # of unfounded mapping this codec avoids.
            if _attr(font, attr):
                raise NotImplementedError(
                    f"Font.{attr} has no MapLibre mapping in this codec"
                )
        face = _attr(font, "face")
        if face is not None:
            layout["text-font"] = [_literal(face, "Font.face")]
        size = _attr(font, "size")
        if size is not None:
            layout["text-size"] = _literal(_px_number(size, "Font.size"), "Font.size")
        color = _attr(font, "color")
        if color is not None:
            paint["text-color"] = _literal(color, "Font.color")
        opacity = _attr(font, "opacity")
        if opacity is not None:
            paint["text-opacity"] = _literal(opacity, "Font.opacity")

        outline = _attr(font, "outline")
        if outline is not None:
            outline_color = _attr(outline, "color")
            if outline_color is not None:
                paint["text-halo-color"] = _literal(outline_color, "Font.outline.color")
            outline_size = _attr(outline, "size")
            if outline_size is not None:
                paint["text-halo-width"] = _literal(outline_size, "Font.outline.size")

    return layout, paint


# hotSpot fraction (fx, fy) -> MapLibre icon-anchor: the reader's own
# _ICON_ANCHOR_TO_FRACTION (._layers), inverted, so the two directions
# can't drift apart. See :func:`_hot_spot_to_icon_anchor` for the
# fraction's own (0,0)=lower-left/(1,1)=upper-right convention and why it
# lines up with icon-anchor unflipped.
_ANCHOR_BY_FRACTION: dict[tuple[float, float], str] = {
    v: k for k, v in _ICON_ANCHOR_TO_FRACTION.items()
}


def _hot_spot_fraction(component: Any) -> float | None:
    """Read one ``hotSpot`` ``[x, y]`` component as a 0..1 fraction.

    Only a ``pc`` value is understood as *percent* — the same
    restriction (and the same overload of ``pc``, formally "picas" in
    :class:`...models.types.UnitType`, as percent specifically for
    ``hotSpot``/``se:AnchorPoint``) the SLD codec's own mapping already
    applies (``codecs/sld/_symbolizer.py::_percent_to_fraction``).
    Anything else (a different unit, a bare number, an expression)
    returns ``None`` for the caller to reject — a graphic element inside
    ``Marker.elements``/``Label.elements`` stays untyped, so this is
    almost always a raw ``{"pc": N}`` dict rather than a validated
    ``UnitValue``, but both are accepted.
    """
    if isinstance(component, dict) and set(component) == {"pc"}:
        return float(component["pc"]) / 100
    if isinstance(component, UnitValue) and component.unit == UnitType.PICAS:
        return component.value / 100
    return None


def _hot_spot_to_icon_anchor(hot_spot: Any, ctx: str) -> str:
    """Turn a resolved ``Image.hotSpot`` into a MapLibre ``icon-anchor``.

    ``hotSpot`` is a fraction within the image — (0,0) is its lower-left
    corner, (1,1) its upper-right (the ``se:AnchorPoint`` convention this
    codebase's SLD reader already implements). That lines up, unflipped,
    with MapLibre's ``icon-anchor``: both describe *which part of the
    icon sits at the anchor point* (fy=0/"lower" edge of the image at
    the point ⇔ icon-anchor ``"bottom"``, not its opposite). Only the 9
    standard positions (0/50/100% on each axis) have an ``icon-anchor``
    keyword; anything else raises rather than approximating via
    ``icon-offset`` — that property scales by ``icon-size`` to get a
    *pixel* offset, and this codec only ever has a URI for the image,
    never its actual pixel dimensions to convert an arbitrary fraction
    against.
    """
    if isinstance(hot_spot, (list, tuple)) and len(hot_spot) == 2:
        fx, fy = _hot_spot_fraction(hot_spot[0]), _hot_spot_fraction(hot_spot[1])
    elif isinstance(hot_spot, dict) and "x" in hot_spot and "y" in hot_spot:
        fx, fy = _hot_spot_fraction(hot_spot["x"]), _hot_spot_fraction(hot_spot["y"])
    else:
        fx = fy = None
    if fx is None or fy is None:
        raise NotImplementedError(
            f"{ctx} {hot_spot!r} is not a pc (percent) UnitPoint — has no "
            "MapLibre mapping in this codec"
        )
    anchor = _ANCHOR_BY_FRACTION.get((fx, fy))
    if anchor is None:
        raise NotImplementedError(
            f"{ctx} ({fx * 100:g}%, {fy * 100:g}%) is not one of the 9 "
            "standard anchor positions (0/50/100% on each axis) — "
            "MapLibre's icon-anchor only has those, and icon-offset can't "
            "convert an arbitrary fraction without the image's actual "
            "pixel dimensions"
        )
    return anchor


def _icon_layer_layout_paint(image_el: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    for attr in ("blackTint", "black_tint", "alphaThreshold", "alpha_threshold"):
        if _attr(image_el, attr) is not None:
            raise NotImplementedError(
                f"Image.{attr} has no MapLibre mapping in this codec"
            )
    image = _attr(image_el, "image")
    icon_id = _attr(image, "id") or _attr(image, "uri") or _attr(image, "path")
    if icon_id is None:
        raise NotImplementedError(
            "Image.image without id/uri/path has no MapLibre icon-image mapping"
        )
    layout: dict[str, Any] = {"icon-image": _literal(icon_id, "Image.image")}
    paint: dict[str, Any] = {}
    opacity = _attr(image_el, "opacity")
    if opacity is not None:
        paint["icon-opacity"] = _literal(opacity, "Image.opacity")
    # icon-color only recolours an SDF (signed-distance-field) sprite in
    # MapLibre — a constraint this codec has no way to check (it only ever
    # carries a sprite id/URI, never the actual image data) — but tint is
    # otherwise the same "recolour the icon" concept, so it maps through.
    tint = _attr(image_el, "tint")
    if tint is not None:
        paint["icon-color"] = _literal(tint, "Image.tint")
    hot_spot = _attr(image_el, "hotSpot")
    if hot_spot is None:
        hot_spot = _attr(image_el, "hot_spot")
    if hot_spot is not None:
        layout["icon-anchor"] = _hot_spot_to_icon_anchor(hot_spot, "Image.hotSpot")
    transform = _attr(image_el, "transform")
    if transform is not None:
        for attr in ("scaling", "translation"):
            if _attr(transform, attr) is not None:
                raise NotImplementedError(
                    f"Image.transform.{attr} has no MapLibre mapping in this codec"
                )
        orientation = _attr(transform, "orientation")
        if orientation is not None:
            layout["icon-rotate"] = _literal(
                _orientation_degrees(orientation, "Image.transform.orientation"),
                "Image.transform.orientation",
            )
    return layout, paint


def _symbol_layer(layer_id: str, text_el: Any, image_el: Any) -> dict[str, Any]:
    """Turn a single ``Text`` and/or ``Image`` element into a ``symbol`` layer.

    *text_el*/*image_el* are individual marker/label graphic elements, not
    the ``Label``/``Marker`` container — either may be ``None``. The two
    are combined into one layer when both are given (the common
    "icon + label" idiom: one MapLibre ``symbol`` layer can carry both
    ``text-field`` and ``icon-image`` at once) — see the caller
    (:func:`_point_layer_specs`) for when that happens.
    """
    layout: dict[str, Any] = {}
    paint: dict[str, Any] = {}

    if text_el is not None:
        if _attr(text_el, "type") != "Text":
            raise NotImplementedError(
                f"marker/label element {_attr(text_el, 'type')!r} → MapLibre "
                "symbol layer (only Text maps to text-field)"
            )
        text_layout, text_paint = _text_layer_layout_paint(text_el)
        layout.update(text_layout)
        paint.update(text_paint)

    if image_el is not None:
        if _attr(image_el, "type") != "Image":
            raise NotImplementedError(
                f"marker/label element {_attr(image_el, 'type')!r} → MapLibre "
                "symbol layer (only Image maps to icon-image)"
            )
        icon_layout, icon_paint = _icon_layer_layout_paint(image_el)
        layout.update(icon_layout)
        paint.update(icon_paint)

    return {
        "id": layer_id,
        "type": "symbol",
        "source": _SOURCE,
        "layout": layout,
        "paint": paint,
    }


def _flatten_rules(styling_rules: list[StylingRule]) -> list[StylingRule]:
    """Flatten CartoSym nested-rule cascades into independent rules.

    MapLibre's ``layers`` is a flat list — unlike ``StylingRule``, it has
    no nesting concept — so a cascading refinement
    (``[attr = value] { ... }`` under a parent rule) must become its own
    top-level entry before :func:`_rule_to_layers` can see it. Reuses the
    codec-agnostic :func:`~pycartosym.codecs._cascade.flatten_cascade_rules`
    (selector AND + symbolizer merge), one top-level rule's subtree at a
    time so a name synthesized below never leaks across siblings.

    A flattened rule with no ``name``/``stylingRuleName`` of its own — the
    common case for a refinement, which usually only narrows the selector
    — inherits its nearest named ancestor's name, disambiguated with a
    positional suffix (a MapLibre layer id must be unique, unlike an SE
    rule which needs no name at all).
    """
    if not any(rule.nested_rules for rule in styling_rules):
        return list(styling_rules)

    out: list[StylingRule] = []
    for rule in styling_rules:
        current_name: str | None = None
        counter = 0
        for flat in flatten_cascade_rules([rule.to_dict()]):
            if flat.get("nestedRules"):
                raise NotImplementedError(
                    "a selector-less nestedRules entry (OGC 'else' rule) has "
                    "no MapLibre mapping in this codec"
                )
            name = flat.get("name") or flat.get("stylingRuleName")
            if name:
                current_name = name
                counter = 0
            elif current_name is not None:
                counter += 1
                flat["name"] = f"{current_name}-{counter}"
            out.append(StylingRule.from_dict(flat))
    return out


def _is_empty_of_paint(rule: Any) -> bool:
    """Return True if *rule* draws nothing and is safe to drop from ``layers``.

    Mirrors the SLD/SE writer's policy for a symbolizer-less rule (no
    symbolizer at all, or only ``visibility``/``opacity``/``zOrder`` —
    typically the base rule of a cascade, e.g. ``visibility: false`` gating
    scale-conditioned refinements): nothing is lost by omitting it. A rule
    that instead carries coverage/raster content (see
    :data:`_RASTER_SYMBOLIZER_PARTS`) is *not* empty — it still needs to
    reach :func:`_rule_to_layers`, which maps the achievable subset and
    raises on the rest (see :mod:`._raster`), not be silently dropped here.
    """
    sym = rule.symbolizer
    if sym is None:
        return True
    if any(getattr(sym, part, None) is not None for part in _RASTER_SYMBOLIZER_PARTS):
        return False
    return (
        sym.fill is None
        and sym.stroke is None
        and sym.marker is None
        and sym.label is None
    )


def _apply_shared_rule_props(
    layer: dict[str, Any],
    sym: Any,
    minzoom: int | float | None,
    maxzoom: int | float | None,
    remaining_selector: Any,
) -> None:
    """Apply the rule-level properties every layer from one rule shares.

    Namely ``minzoom``/``maxzoom``/``filter`` and ``visibility``.
    """
    if minzoom is not None or maxzoom is not None or remaining_selector is not None:
        # Re-key so `minzoom`/`maxzoom`/`filter` sit before `layout`/
        # `paint`, as styles are conventionally written.
        layout = layer.pop("layout", None)
        paint = layer.pop("paint")
        if minzoom is not None:
            layer["minzoom"] = minzoom
        if maxzoom is not None:
            layer["maxzoom"] = maxzoom
        if remaining_selector is not None:
            layer["filter"] = selector_to_filter(remaining_selector)
        if layout is not None:
            layer["layout"] = layout
        layer["paint"] = paint

    if sym.visibility is False:
        layer.setdefault("layout", {})["visibility"] = "none"
    elif sym.visibility is not True and sym.visibility is not None:
        raise NotImplementedError(
            "non-constant symbolizer.visibility → MapLibre is not mapped yet"
        )


def _elements_list(container: Any) -> list[Any]:
    """Return a ``Marker``/``Label``'s resolved element list, or ``[]`` if absent."""
    if container is None:
        return []
    elements = container.elements
    if not isinstance(elements, list):
        raise NotImplementedError(
            "an indexed marker/label element override ({index, value}) must "
            "already be fully resolved before conversion to MapLibre"
        )
    return elements


def _element_point_spec(el: Any) -> tuple[str, Any]:
    """Return a ``(kind, builder)`` pair for one marker/label graphic element.

    Dispatches on the element's own ``type`` — not on whether it came from
    ``marker.elements`` or ``label.elements``, which this codec treats
    symmetrically (both are a generic list of graphic elements in the
    conceptual model; a ``Dot``/``Text`` is equally valid in either — see
    e.g. a ``Text`` cascaded into ``marker.elements`` or a ``Dot`` inside
    ``label.elements`` in the public examples).
    """
    el_type = _attr(el, "type")
    if el_type in ("Dot", "Circle"):
        return ("circle", lambda lid: _circle_layer_from_element(lid, el))
    if el_type == "Image":
        return ("symbol", lambda lid: _symbol_layer(lid, None, el))
    if el_type == "Text":
        return ("symbol", lambda lid: _symbol_layer(lid, el, None))
    raise NotImplementedError(
        f"marker/label element {el_type!r} has no MapLibre mapping in this codec"
    )


def _point_layer_specs(sym: Any) -> list[tuple[str, Any]]:
    """Ordered ``(kind, builder)`` specs for the point layer(s) a symbolizer needs.

    One spec per marker/label graphic element, in ``marker.elements`` then
    ``label.elements`` order (bottom-to-top stacking, matching the
    MapLibre ``layers`` array) — except the common case of exactly one
    ``Image`` marker element and exactly one ``Text`` label element, which
    still merges into a single combined ``symbol`` layer (icon + text
    together), the same as before this generalisation.
    """
    marker_elements = _elements_list(getattr(sym, "marker", None))
    label_elements = _elements_list(getattr(sym, "label", None))

    if (
        len(marker_elements) == 1
        and _attr(marker_elements[0], "type") == "Image"
        and len(label_elements) == 1
        and _attr(label_elements[0], "type") == "Text"
    ):
        image_el, text_el = marker_elements[0], label_elements[0]
        return [("symbol", lambda lid: _symbol_layer(lid, text_el, image_el))]

    return [_element_point_spec(el) for el in (*marker_elements, *label_elements)]


def _strip_redundant_datalayer_type(selector: Any, expected_literal: str) -> Any:
    """Drop a ``sysId dataLayer.type = <expected_literal>`` conjunct from *selector*.

    Only called once a rule is already routed to layers of the matching
    kind (see :func:`_rule_to_layers`) — at that point the tag is provably
    redundant, nothing else could have produced those layers, the same
    reasoning :func:`._filter.strip_datalayer_id` applies to
    ``dataLayer.id``. A ``dataLayer.type`` whose *literal* doesn't match
    the layers actually produced (a contradiction that should never occur
    given a rule was successfully routed, but not this function's job to
    diagnose), a non-``=`` comparison, or any other ``sysId``, is left
    alone and still raises further down the pipeline.
    """
    if not isinstance(selector, dict):
        return selector
    op = selector.get("op")
    if op == "and":
        kept = [
            stripped
            for a in selector.get("args", [])
            if (stripped := _strip_redundant_datalayer_type(a, expected_literal))
            is not None
        ]
        if not kept:
            return None
        if len(kept) == 1:
            return kept[0]
        return {"op": "and", "args": kept}
    if op == "=":
        args = selector.get("args", [])
        if len(args) == 2:
            has_type_sysid = any(
                isinstance(a, dict) and a.get("sysId") == "dataLayer.type" for a in args
            )
            has_expected_literal = expected_literal in args
            if has_type_sysid and has_expected_literal:
                return None
    return selector


def _raster_layers(layer_id: str, sym: Any) -> list[dict[str, Any]]:
    """Return the ``color-relief``/``hillshade`` layer(s) a coverage symbolizer needs.

    See :mod:`._raster` for what maps and what is an honest gap.
    """
    if sym.color_channels is not None:
        raise NotImplementedError(
            "symbolizer.colorChannels has no MapLibre mapping in this "
            "codec — a raster/hillshade/color-relief layer draws from an "
            "already-rendered image, it cannot select source bands"
        )
    if sym.alpha_channel is not None:
        raise NotImplementedError(
            "symbolizer.alphaChannel has no MapLibre mapping in this codec"
        )
    if sym.opacity_map is not None:
        raise NotImplementedError(
            "symbolizer.opacityMap has no MapLibre mapping in this codec"
        )

    have_color = sym.single_channel is not None or sym.color_map is not None
    if have_color and (sym.single_channel is None or sym.color_map is None):
        raise NotImplementedError(
            "singleChannel and colorMap must both be present for the "
            "MapLibre color-relief mapping in this codec"
        )

    multi = have_color and sym.hill_shading is not None

    def _rid(kind: str) -> str:
        return f"{layer_id}-{kind}" if multi else str(layer_id)

    layers: list[dict[str, Any]] = []
    if have_color:
        layers.append(
            _raster.color_relief_layer(
                _rid("color-relief"), sym.single_channel, sym.color_map, _literal
            )
        )
    if sym.hill_shading is not None:
        layers.append(
            _raster.hillshade_layer(_rid("hillshade"), sym.hill_shading, _literal)
        )

    if not layers:
        raise NotImplementedError(
            "empty coverage symbolizer has no MapLibre mapping in this codec"
        )
    return layers


def _rule_to_layers(rule: Any) -> list[dict[str, Any]]:
    sym = rule.symbolizer
    if sym is None:
        raise NotImplementedError("styling rule without a symbolizer")

    layer_id = rule.name or rule.styling_rule_name
    if not layer_id:
        raise NotImplementedError("styling rule without a name → MapLibre layer id")

    minzoom, maxzoom, remaining_selector = extract_zoom_range(rule.selector)
    remaining_selector = strip_datalayer_id(remaining_selector)

    is_raster = any(
        getattr(sym, part, None) is not None for part in _RASTER_SYMBOLIZER_PARTS
    )
    if is_raster:
        if (
            sym.fill is not None
            or sym.stroke is not None
            or sym.marker is not None
            or sym.label is not None
        ):
            raise NotImplementedError(
                "a symbolizer cannot combine coverage/raster fields with "
                "fill/stroke/marker/label in this codec"
            )
        remaining_selector = _strip_redundant_datalayer_type(
            remaining_selector, "coverage"
        )
        layers = _raster_layers(layer_id, sym)
        for layer in layers:
            _apply_shared_rule_props(layer, sym, minzoom, maxzoom, remaining_selector)
        return layers

    remaining_selector = _strip_redundant_datalayer_type(remaining_selector, "vector")

    vendor_layer_type = _vendor_layer_type(sym)

    if vendor_layer_type == "background":
        if (
            sym.fill is None
            or sym.stroke is not None
            or sym.marker is not None
            or sym.label is not None
        ):
            raise NotImplementedError(
                "vendor.maplibre.layer-type=background requires a fill-only "
                "symbolizer (no stroke, marker, or label)"
            )
        if remaining_selector is not None:
            raise NotImplementedError(
                "a background layer has no filter — rule.selector must reduce "
                "to nothing but viz.sd zoom-range conjuncts on a "
                "vendor.maplibre.layer-type=background symbolizer"
            )
        layers = [_background_layer(layer_id, sym.fill, sym.stroke)]
    else:
        point_specs = _point_layer_specs(sym)

        # A plain-colour stroke (no width/opacity) stays inlined into the
        # fill layer as `fill-outline-color`, as before; a full stroke, or
        # one with no fill to attach to, gets its own `line` layer.
        needs_line = sym.stroke is not None and (
            sym.fill is None
            or sym.stroke.width is not None
            or sym.stroke.opacity is not None
        )
        inline_stroke = (
            sym.stroke if (sym.stroke is not None and not needs_line) else None
        )

        multi = sum((sym.fill is not None, needs_line, len(point_specs))) > 1

        def _id(kind: str, idx: int | None = None) -> str:
            if not multi:
                return str(layer_id)
            return f"{layer_id}-{kind}" if idx is None else f"{layer_id}-{kind}-{idx}"

        layers = []
        if sym.fill is not None:
            layers.append(_fill_layer(_id("fill"), sym.fill, inline_stroke))
        if needs_line:
            layers.append(_line_layer(_id("line"), sym.stroke))

        kind_counts: dict[str, int] = {}
        for kind, _ in point_specs:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        kind_seen: dict[str, int] = {}
        for kind, point_builder in point_specs:
            kind_seen[kind] = kind_seen.get(kind, 0) + 1
            idx = kind_seen[kind] if kind_counts[kind] > 1 else None
            layers.append(point_builder(_id(kind, idx)))

        if not layers:
            raise NotImplementedError(
                "symbolizer with no fill / stroke / marker has no MapLibre mapping"
            )

    for layer in layers:
        _apply_shared_rule_props(layer, sym, minzoom, maxzoom, remaining_selector)
    return layers


# `name` pattern the reader's own step(["zoom"]) explosion produces (PR
# #70, `_expand_step_zoom_layers`) — `{base}-{1-based index}`, sequential
# starting at 1. Recombination below only ever targets this exact shape;
# a hand-written CSCSS/CS-JSON rule set that happens to look similar but
# isn't named this way is never recombined — see :func:`_combine_stepped_rules`.
_STEP_NAME_RE = re.compile(r"^(.+)-(\d+)$")

_MISSING = object()


def _group_stepped_rules(rules: list[Any]) -> list[list[Any]]:
    """Group consecutive rules named ``base-1``/``base-2``/… for step recombination.

    A rule whose name doesn't fit the pattern, or that breaks the
    1..N sequence (wrong index, a different base, a gap in the rule
    list), starts its own singleton group instead.
    """
    groups: list[list[Any]] = []
    current: list[Any] = []
    current_base: str | None = None
    expected_index = 1
    for rule in rules:
        match = _STEP_NAME_RE.match(rule.name or "")
        if (
            match
            and match.group(1) == current_base
            and int(match.group(2)) == (expected_index)
        ):
            current.append(rule)
            expected_index += 1
            continue
        if current:
            groups.append(current)
            current = []
        if match and int(match.group(2)) == 1:
            current = [rule]
            current_base = match.group(1)
            expected_index = 2
        else:
            groups.append([rule])
            current_base = None
            expected_index = 1
    if current:
        groups.append(current)
    return groups


def _combine_stepped_rules(group: list[Any]) -> list[dict[str, Any]] | None:
    """Recombine a ``base-1``/``base-2``/… rule run into one ``step(["zoom"])`` layer.

    Inverse of the reader's :func:`._layers._expand_step_zoom_layers`
    (PR #70) — reuses :func:`_rule_to_layers` to resolve each rule
    independently first (so every existing per-property serialisation
    rule still applies unchanged), then merges the results. Returns
    ``None`` — meaning the caller falls back to writing each rule as its
    own independent layer(s), never a guessed/approximated merge — unless
    *every* one of these holds:

    - each rule resolves to exactly one layer (a rule that itself splits
      into several, e.g. combined fill+stroke, is never recombined);
    - all layers share the same ``type``/``source``/``source-layer``/
      ``filter`` — only ``minzoom``/``maxzoom`` and paint/layout *values*
      may differ;
    - the zoom ranges are contiguous with no gap (segment *i*'s
      ``maxzoom`` equals segment *i+1*'s ``minzoom``) and only the very
      first ``minzoom``/very last ``maxzoom`` may be absent (unbounded);
    - every differing paint/layout key is present in *all* segments (a
      key missing in only some has no ``step`` representation).
    """
    segment_layers = []
    for rule in group:
        if _is_empty_of_paint(rule):
            return None
        layers = _rule_to_layers(rule)
        if len(layers) != 1:
            return None
        segment_layers.append(layers[0])

    first = segment_layers[0]
    for layer in segment_layers[1:]:
        if any(
            layer.get(key) != first.get(key)
            for key in ("type", "source", "source-layer", "filter")
        ):
            return None

    for a, b in zip(segment_layers, segment_layers[1:]):
        if a.get("maxzoom") != b.get("minzoom"):
            return None
    if any("minzoom" not in layer for layer in segment_layers[1:]):
        return None
    if any("maxzoom" not in layer for layer in segment_layers[:-1]):
        return None
    zoom_stops = [layer["minzoom"] for layer in segment_layers[1:]]

    combined: dict[str, Any] = dict(first)
    combined["id"] = _STEP_NAME_RE.match(group[0].name).group(1)  # type: ignore[union-attr]
    if "maxzoom" in segment_layers[-1]:
        combined["maxzoom"] = segment_layers[-1]["maxzoom"]
    else:
        combined.pop("maxzoom", None)

    for prop_kind in ("paint", "layout"):
        per_segment = [layer.get(prop_kind, {}) for layer in segment_layers]
        keys = {key for values in per_segment for key in values}
        merged: dict[str, Any] = {}
        for key in keys:
            values = [v.get(key, _MISSING) for v in per_segment]
            if any(v is _MISSING for v in values):
                return None
            if all(v == values[0] for v in values):
                merged[key] = values[0]
            else:
                step_args: list[Any] = [values[0]]
                for stop, value in zip(zoom_stops, values[1:]):
                    step_args.extend([stop, value])
                merged[key] = ["step", ["zoom"], *step_args]
        if merged:
            combined[prop_kind] = merged
        else:
            combined.pop(prop_kind, None)
    return [combined]


class MaplibreWriter(CodecWriter):
    """Serialise a :class:`Style` as a MapLibre GL style ``dict``."""

    def write(self, style: Style) -> dict[str, Any]:
        """Return the MapLibre style JSON for *style*.

        Raises:
            NotImplementedError: the style uses a construct this codec
                does not map yet (see the module docstring).
        """
        rules = _flatten_rules(style.styling_rules)
        layers: list[dict[str, Any]] = []
        for group in _group_stepped_rules(rules):
            combined = _combine_stepped_rules(group) if len(group) > 1 else None
            if combined is not None:
                layers.extend(combined)
                continue
            for rule in group:
                if not _is_empty_of_paint(rule):
                    layers.extend(_rule_to_layers(rule))
        sources: dict[str, Any] = {}
        # A `background` layer has no `source` — only declare a synthetic
        # source when a layer actually references it.
        if any(layer.get("source") == _SOURCE for layer in layers):
            sources[_SOURCE] = {
                "type": "geojson",
                "data": {"type": "FeatureCollection", "features": []},
            }
        if any(layer.get("source") == _raster.DEM_SOURCE for layer in layers):
            sources[_raster.DEM_SOURCE] = _raster.dem_source()
        return {"version": 8, "sources": sources, "layers": layers}
