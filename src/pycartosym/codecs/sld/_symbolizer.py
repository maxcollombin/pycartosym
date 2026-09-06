"""CartoSym ``Symbolizer`` <-> SLD/SE symbolizer-element mapping, both ways.

Covers ``{Point,Line,Polygon,Text,Raster}Symbolizer``.

Scope: vector symbolizers plus basic Part-1 raster/coverage styling
(channels, color map, shaded relief). ``Fill.hatch/dotpattern/stipple``,
``Stroke.casing/centerLine``, ``Label.placement``,
``Symbolizer.alphaChannel``, ``Symbolizer.opacityMap``, and
``HillShading.sun``/``colorMap``/``opacityMap`` are all out of scope and
raise :exc:`NotImplementedError` naming the field — per this project's
lossless-transcoding requirement, out-of-scope content must fail loudly
rather than silently drop data. On read, an unmapped
``SvgParameter``/``CssParameter`` (``stroke-dashoffset`` / ...) likewise
raises. ``stroke-linecap``/``stroke-linejoin`` map to the Part 2
("shapes") ``Stroke.cap``/``Stroke.join`` extension, both ways, on the
``LineSymbolizer``/``PolygonSymbolizer`` outline ``Stroke`` only — a
point ``se:Mark``'s outline has no CartoSym ``cap``/``join`` field
(``ShapeOutline`` is thickness/opacity/color only) and still raises on
either parameter there.

``se:Halo`` maps to ``font.outline`` (``{size, opacity, color}``); a
point ``se:Graphic``'s ``se:Opacity`` and ``se:Displacement`` map to the
graphic's ``opacity`` / ``position`` (SE 1.1.0 only — SLD 1.0.0's
``Graphic`` has no ``Displacement`` child, so a non-zero offset raises
there). A point ``se:Graphic``'s ``se:Rotation`` (present in both
dialects — unlike ``Displacement``, it's not SE-only) maps to the
graphic's ``transform.orientation`` (Part 2 ``abstractGraphic``
extension, OGC issue tracked as pycartosym #89) for ``Mark``- and
``ExternalGraphic``-based graphics; a ``TextGraphic.transform`` has no
mapping (labels use ``se:LabelPlacement``, not ``se:Graphic``) and
raises rather than silently dropping it.

Every function here is dialect-agnostic: the caller passes a
:class:`~pycartosym.codecs.sld._dialect.SldDialect` (``d``) and all
XML element/parameter construction and lookup goes through it, so the same
code serialises SLD 1.0.0 (``CssParameter``, unprefixed) and SE 1.1.0
(``se:SvgParameter``).

``Symbolizer.opacity`` has no whole-symbolizer equivalent in SE 1.1.0 and
is folded multiplicatively into every leaf opacity produced
(``fill-opacity``, ``stroke-opacity``, ``se:Graphic/se:Opacity``,
``se:RasterSymbolizer/se:Opacity``) — round-trips cleanly only for raster.

``se:Fill``/``se:Stroke``'s ``fill``/``stroke`` (colour) parameters may
also be property-driven: a bare ``ogc:PropertyName`` maps to a CartoSym
``PropertyRef``, and ``se:Recode`` (native SE 1.1.0 element,
``se:LookupValue`` + one or more ``se:MapItem``/``se:Data``/``se:Value``,
substitution group ``se:Function`` — see ``Symbolizer.xsd``, *not* the
generic ``ogc:Function name="Recode"`` some Annex B examples show, which
has no ``fallbackValue`` and isn't SE-namespaced) maps to a
``MatchExpression`` (see :mod:`...models.value_expressions`) — the same
CartoSym-side shape MapLibre's own ``match`` expression uses, chosen
deliberately so a Recode read from SLD passes straight through the
MapLibre codec unchanged. ``Recode``'s ``fallbackValue`` (required on the
abstract ``se:FunctionType``) becomes ``match``'s trailing fallback arg;
a lookup value other than a bare ``ogc:PropertyName`` (a nested function,
say) is out of scope and raises. **``se:Data`` (a ``MapItem``'s label) is
``xsd:double`` in the schema — numeric only** (unlike ``se:Categorize``'s
``se:Value``, a free-text ``ParameterValueType``) — a non-numeric
``match`` label has no ``se:Recode`` mapping and raises on write; this is
presumably *why* the Annex B "Recoding Function" worked example (a
string-keyed region-name lookup) uses the generic ``ogc:Function
name="Recode"`` form instead of the native element it names — the
native ``se:Recode`` cannot represent it. SE 1.1.0 only — SLD 1.0.0
predates ``se:Recode`` and has no equivalent, so a match/Recode colour
raises there (``SldDialect.recode_function``). ``fill-opacity``/
``stroke-opacity`` read the same property-driven shapes, but the
opacity-folding above means they never write back as an expression —
only as a literal, or ``NotImplementedError``.

``stroke-width`` may likewise be property-driven: a bare
``ogc:PropertyName`` maps to ``PropertyRef``, and an ``ogc:Function
name="Add|Sub|Mul|Div"`` (OGC Filter Encoding's arithmetic functions,
unprefixed ``ogc:`` in both dialects — unlike ``se:Recode``, this isn't
an SE 1.1.0 addition) maps to an ``ArithmeticExpression`` — the CS-JSON
schema's own ``arithmeticExpression``/``systemIdentifier`` (see OGC issue
#115). A ``SystemIdentifier`` (e.g. ``viz.sd``, the current scale
denominator) has no mapping and raises: SLD/SE has no construct exposing
scale as a filter/expression *value*, only rule-level
``MinScaleDenominator``/``MaxScaleDenominator`` gating — a confirmed
permanent wall for this one system identifier, not a missing-wiring gap.
A ``2-shapes`` shape's outline ``thickness`` (``se:Mark/se:Stroke``'s own
``stroke-width``) is wired the same way, via the same
:func:`_write_numeric_param`/:func:`_parse_flexible_numeric_param`.

``Dot``, ``Circle``, ``Rectangle``, ``Image``, and ``Text`` graphic
elements (found in either ``Symbolizer.marker.elements`` or
``Symbolizer.label.elements`` — CartoSym allows Text under either) are
in scope (the other ``2-shapes`` shape graphics — arbitrary polygons for
``se:Mark wellKnownName`` values like ``triangle``/``star``/``cross``/
``x`` — are not, pycartosym issue #88); a filled
``se:Mark wellKnownName="circle"`` reads back as a ``2-shapes`` ``Circle``
(``fill`` + ``outline`` + ``radius``), ``wellKnownName="square"`` as a
``2-shapes`` ``Rectangle`` with equal ``width``/``height`` (``se:Size`` is
a single scalar — a non-square rectangle has no ``se:Mark`` mapping), and
a ``Dot`` element still writes (stroke-only mark) for CartoSym-CSS
sources. On read, an ``se:Mark``/
``se:ExternalGraphic`` always reconstructs into ``marker.elements`` and an
``se:TextSymbolizer`` always reconstructs into ``label.elements`` (SLD/SE
has no construct distinguishing CartoSym's separate marker-text vs
label-text concepts, so this read direction is inherently lossy).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lxml import etree

from ...models.base import BaseCartoSymModel
from ...models.value_expressions import (
    ArithmeticExpression,
    InterpolateExpression,
    MatchExpression,
    PropertyRef,
    SystemIdentifier,
)
from ._dialect import SldDialect
from ._types import (
    format_angle,
    format_color,
    format_number,
    format_opacity,
    format_unit_value,
    parse_angle,
    parse_color,
    parse_number,
    parse_opacity,
    parse_unit_value,
)
from ._xml_helpers import OGC, XLINK, element_text, local_name

_ANCHOR_X = {"left": "0", "center": "0.5", "right": "1"}
_ANCHOR_Y = {"top": "1", "middle": "0.5", "bottom": "0"}
_ANCHOR_X_TO_H = {"0": "left", "0.5": "center", "1": "right"}
_ANCHOR_Y_TO_V = {"1": "top", "0.5": "middle", "0": "bottom"}


def _g(obj: Any, key: str, default: Any = None) -> Any:
    """Get *key* from *obj*, whether it's a plain dict or a Pydantic model."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _number_of(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return float(value.value)
    if isinstance(value, dict) and len(value) == 1:
        return float(next(iter(value.values())))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _axis_value_of(value: Any) -> Any:
    """A plain float for a literal coordinate, or the typed value itself.

    Unlike :func:`_number_of` (used by e.g. ``Circle.radius``, which has
    no property-driven SLD/SE mapping and must stay float-only), a
    ``UnitPoint`` coordinate feeding :func:`_write_numeric_element` needs
    the typed value preserved rather than coerced to ``None``.
    """
    coerced = _coerce_numeric_expr(value)
    if isinstance(coerced, (PropertyRef, ArithmeticExpression, SystemIdentifier)):
        return coerced
    return _number_of(value)


def _unit_point_xy(position: Any):
    return _axis_value_of(_g(position, "x")), _axis_value_of(_g(position, "y"))


# ---------------------------------------------------------------------------
# GeoServer <VendorOption> <-> vendor.geoserver.* symbolizer properties
# ---------------------------------------------------------------------------


def _coerce_vendor_value(text: str) -> bool | int | float | str:
    """Best-effort scalar for a ``<VendorOption>`` text value.

    ``"true"``/``"false"`` become ``bool``; an integral / decimal string
    becomes ``int`` / ``float``; anything else stays a ``str``. Each of
    those round-trips back to the same text via :func:`_vendor_option_text`.
    """
    stripped = text.strip()
    low = stripped.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return stripped


def _vendor_option_text(value: Any) -> str:
    """Render a ``vendor.geoserver.*`` value back as ``<VendorOption>`` text."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _read_vendor_options(
    d: SldDialect, el: etree._Element
) -> list[tuple[str, bool | int | float | str]]:
    """Return ``(name, value)`` for each ``<VendorOption>`` child of *el*."""
    out: list[tuple[str, bool | int | float | str]] = []
    for opt in d.findall(el, "VendorOption"):
        name = opt.get("name")
        if not name:
            raise NotImplementedError("<VendorOption> without a name attribute")
        out.append((name, _coerce_vendor_value(element_text(opt) or "")))
    return out


def _vendor_extension_items(sym: Any) -> list[tuple[str, Any]]:
    """Return ``(key, value)`` for every ``vendor.<name>.<prop>`` property."""
    source: Any = (
        sym if isinstance(sym, dict) else getattr(sym, "__pydantic_extra__", None) or {}
    )
    return [(k, v) for k, v in source.items() if k.startswith("vendor.")]


def _apply_vendor_options(
    d: SldDialect, sym: Any, elements: list[etree._Element]
) -> None:
    """Append the symbolizer's ``vendor.geoserver.*`` props as ``<VendorOption>``.

    The conceptual model's vendor extensions are per-symbolizer, so they
    can only be written when the CartoSym symbolizer maps to exactly one
    SLD element — otherwise there is no unambiguous host.
    """
    items = _vendor_extension_items(sym)
    if not items:
        return
    if not d.vendor_options:
        raise NotImplementedError(
            "vendor.* symbolizer extensions have no mapping in the standard "
            "SLD/SE dialects — the 'sld:geoserver' codec is required"
        )
    if len(elements) != 1:
        raise NotImplementedError(
            "vendor.* symbolizer extensions on a symbolizer that expands to "
            f"{len(elements)} SLD elements — cannot attribute the "
            "<VendorOption> to a single symbolizer element"
        )
    for key, value in items:
        _, vendor_name, prop = key.split(".", 2)
        if vendor_name != "geoserver":
            raise NotImplementedError(
                f"vendor extension {key!r}: only 'geoserver' vendor extensions "
                "map to a GeoServer <VendorOption>"
            )
        opt = d.el("VendorOption", parent=elements[0], text=_vendor_option_text(value))
        opt.set("name", prop)


# ---------------------------------------------------------------------------
# Writer direction: Symbolizer -> SLD/SE symbolizer elements
# ---------------------------------------------------------------------------

_RASTER_FIELD_ATTRS = (
    "color_channels",
    "alpha_channel",
    "single_channel",
    "color_map",
    "opacity_map",
    "hill_shading",
)


def has_raster_fields(sym: Any) -> bool:
    return any(_g(sym, attr) is not None for attr in _RASTER_FIELD_ATTRS)


def _opacity_float(value: Any) -> float | None:
    """Numeric opacity (0..1) for *value*, or ``None`` if unset.

    ``format_opacity`` already raises ``NotImplementedError`` for
    expression/property-driven opacity, so any
    value that survives is numeric.
    """
    if value is None:
        return None
    return float(format_opacity(value))


def _combine_opacity(base: float | None, own: Any) -> str | None:
    """Format the product of a symbolizer-level *base* and an element's *own* opacity.

    SE 1.1.0 has no whole-symbolizer opacity — ``Symbolizer.opacity`` is
    folded into each leaf opacity the symbolizer emits (``fill-opacity``,
    ``stroke-opacity``, ``se:Graphic/se:Opacity``, ``se:RasterSymbolizer/
    se:Opacity``). Returns ``None`` when neither is set (emit nothing).
    """
    own_f = _opacity_float(own)
    if base is None and own_f is None:
        return None
    factor = (1.0 if base is None else base) * (1.0 if own_f is None else own_f)
    return format_opacity(factor)


def symbolizer_to_elements(d: SldDialect, sym: Any) -> list[etree._Element]:
    """Convert one CartoSym ``Symbolizer`` into 1..N sibling SLD/SE elements."""
    elements: list[etree._Element] = []
    fill = _g(sym, "fill")
    stroke = _g(sym, "stroke")
    marker = _g(sym, "marker")
    label = _g(sym, "label")
    # SE 1.1.0 has no whole-symbolizer opacity — fold Symbolizer.opacity
    # into every leaf opacity produced below.
    s_op = _opacity_float(_g(sym, "opacity"))

    if fill is not None:
        elements.append(_build_polygon_symbolizer(d, fill, stroke, s_op))
    elif stroke is not None:
        elements.append(_build_line_symbolizer(d, stroke, s_op))

    if has_raster_fields(sym):
        elements.append(_build_raster_symbolizer(d, sym, s_op))

    if marker is not None:
        elements.extend(
            _graphic_elements_to_symbolizers(d, _g(marker, "elements"), s_op)
        )

    if label is not None:
        if _g(label, "placement") is not None:
            raise NotImplementedError(
                "Label.placement (line placement / priority / spacing) has "
                "no SLD/SE mapping in this codec"
            )
        elements.extend(
            _graphic_elements_to_symbolizers(d, _g(label, "elements"), s_op)
        )

    _apply_vendor_options(d, sym, elements)

    # An empty result means the symbolizer carried no geometry-styling
    # intent (only visibility / opacity / zOrder, or nothing). SE 1.1.0
    # forbids a se:Rule without a se:Symbolizer, so the caller decides
    # whether such a rule can be dropped faithfully or must fail loudly
    # (see writer.SldWriter._build_rule).
    return elements


def _graphic_elements_to_symbolizers(
    d: SldDialect, elements: Any, base_opacity: float | None = None
) -> list[etree._Element]:
    if elements is None:
        return []
    if isinstance(elements, dict) and "index" in elements and "value" in elements:
        raise NotImplementedError(
            "Indexed marker/label element overrides ({index, value}) are "
            "not supported by this codec — the rule's element list must "
            "already be fully resolved before conversion to SLD/SE"
        )
    if not isinstance(elements, list):
        elements = [elements]
    result = []
    for el in elements:
        el_type = _g(el, "type")
        if el_type == "Dot":
            result.append(_build_point_symbolizer(d, el, base_opacity))
        elif el_type == "Circle":
            result.append(_build_circle_symbolizer(d, el, base_opacity))
        elif el_type == "Rectangle":
            result.append(_build_rectangle_symbolizer(d, el, base_opacity))
        elif el_type == "Image":
            result.append(_build_image_symbolizer(d, el, base_opacity))
        elif el_type == "Text":
            result.append(_build_text_symbolizer(d, el, base_opacity))
        else:
            raise NotImplementedError(
                f"Graphic element type {el_type!r} has no SLD/SE mapping in "
                "this codec's scope (only Dot/Circle/Rectangle/Image/Text "
                "are supported)"
            )
    return result


def _raise_if_fill_out_of_scope(fill: Any) -> None:
    for attr in ("hatch", "dotpattern", "stipple", "pattern"):
        if _g(fill, attr) is not None:
            raise NotImplementedError(
                f"Fill.{attr} has no SLD/SE mapping in this codec"
            )


def _coerce_color_expr(value: Any) -> Any:
    """Best-effort coercion of a plain expression-shaped dict to its typed class.

    Mirrors :func:`_coerce_numeric_expr`'s rationale (a value nested inside
    a graphic element — ``Marker.elements`` is typed ``Any`` — stays a raw
    dict rather than a real ``PropertyRef``/``MatchExpression``/
    ``InterpolateExpression`` instance, which :func:`_write_color_param`'s
    ``isinstance`` checks need), but recognises ``MatchExpression``
    (``{"op": "match", ...}``) and ``InterpolateExpression``
    (``{"op": "interpolate", ...}``) instead of ``ArithmeticExpression`` —
    a colour value is matched/recoded or interpolated by attribute, it
    doesn't do arithmetic. Passes through unchanged if already typed or
    not one of these shapes (e.g. a plain literal colour).
    """
    if isinstance(value, (PropertyRef, MatchExpression, InterpolateExpression)):
        return value
    if isinstance(value, dict):
        if "property" in value:
            return PropertyRef.model_validate(value)
        if value.get("op") == "match" and "args" in value:
            return MatchExpression.model_validate(value)
        if value.get("op") == "interpolate" and "args" in value:
            return InterpolateExpression.model_validate(value)
    return value


def _write_recode(
    d: SldDialect,
    parent: etree._Element,
    name: str,
    expr: MatchExpression,
    *,
    is_valid_output: Callable[[Any], bool],
    format_output: Callable[[Any], str],
) -> None:
    """Append *expr* as an ``se:Recode`` inside an ``SvgParameter`` named *name*.

    Shared by :func:`_write_color_param` (colour outputs — a literal
    string) and :func:`_write_numeric_param` (numeric outputs — a literal
    int/float): the ``se:Recode``/``se:LookupValue``/``se:MapItem`` shape
    and the ``se:Data`` (numeric label) constraint are identical, only the
    output validation/formatting differs, so it's injected rather than
    duplicated. SE 1.1.0 only (:attr:`SldDialect.recode_function`) —
    SLD 1.0.0 has no native ``Recode``/``LookupValue``/``MapItem``.
    """
    if not d.recode_function:
        raise NotImplementedError(
            f"{name}: a match/Recode value has no SLD 1.0.0 mapping in "
            "this codec (se:Recode/se:LookupValue/se:MapItem are SE "
            "1.1.0 additions)"
        )
    lookup, *rest = expr.args
    *pairs, fallback = rest
    if not isinstance(lookup, PropertyRef):
        raise NotImplementedError(
            f"{name}: match/Recode lookup value {lookup!r} is not "
            "supported in this codec (only a property reference maps)"
        )
    if not is_valid_output(fallback):
        raise NotImplementedError(
            f"{name}: match/Recode fallback {fallback!r} must be a "
            "literal — se:Recode's fallbackValue is an XML attribute, "
            "which can't hold a nested expression"
        )
    labels, outs = pairs[0::2], pairs[1::2]
    for label in labels:
        if isinstance(label, bool) or not isinstance(label, (int, float)):
            raise NotImplementedError(
                f"{name}: match/Recode label {label!r} must be numeric — "
                "se:Recode's se:Data is xsd:double per SE 1.1.0 "
                "(Symbolizer.xsd), unlike se:Categorize/se:Value"
            )
    for out in outs:
        if not is_valid_output(out):
            raise NotImplementedError(
                f"{name}: match/Recode value {out!r} must be a literal — "
                "se:Value can't hold a nested expression in this codec"
            )
    param = d.param_element(parent, name)
    recode = d.el("Recode", param)
    recode.set("fallbackValue", format_output(fallback))
    lookup_el = d.el("LookupValue", recode)
    etree.SubElement(lookup_el, f"{OGC}PropertyName").text = lookup.property
    for label, out in zip(labels, outs):
        item = d.el("MapItem", recode)
        d.el("Data", item, text=str(label))
        d.el("Value", item, text=format_output(out))


def _write_interpolate(
    d: SldDialect,
    parent: etree._Element,
    name: str,
    expr: InterpolateExpression,
    *,
    method: str,
    is_valid_output: Callable[[Any], bool],
    format_output: Callable[[Any], str],
) -> None:
    """Append *expr* as an ``se:Interpolate`` inside an ``SvgParameter`` named *name*.

    Shared by :func:`_write_color_param` (``method="color"``) and
    :func:`_write_numeric_param` (``method="numeric"``) — same
    ``is_valid_output``/``format_output`` injection as :func:`_write_recode`
    for the same reason (only the output type differs). Only
    ``interpolation == "linear"`` maps to SE's ``mode="linear"``:
    ``se:Interpolate``'s own ``mode`` enum is ``linear``/``cosine``/
    ``cubic``, with no base/control-point parameters at all (``Symbolizer.
    xsd``'s ``InterpolateType``), so MapLibre's ``exponential`` (a ``base``)
    and ``cubic-bezier`` (4 control points) have no faithful SE
    equivalent — raising rather than silently mismapping onto a
    same-named but differently-defined SE mode. SE 1.1.0 only
    (:attr:`SldDialect.interpolate_function`) — SLD 1.0.0 has no native
    ``Interpolate``/``LookupValue``/``InterpolationPoint``.
    ``fallbackValue`` is required on ``se:FunctionType`` (the abstract
    base both ``se:Recode`` and ``se:Interpolate`` extend, per
    ``Symbolizer.xsd``) even though ``InterpolateExpression`` carries no
    distinct fallback of its own — written as the last stop's output,
    matching the SE spec's own "beyond the last point" clamping semantics
    (the same value an out-of-domain lookup would resolve to); ignored on
    read, since it is redundant with the last ``se:InterpolationPoint``
    already captured in ``args``.
    """
    if not d.interpolate_function:
        raise NotImplementedError(
            f"{name}: an interpolate value has no SLD 1.0.0 mapping in "
            "this codec (se:Interpolate/se:LookupValue/"
            "se:InterpolationPoint are SE 1.1.0 additions)"
        )
    if expr.interpolation != "linear":
        raise NotImplementedError(
            f"{name}: interpolate type {expr.interpolation!r} has no SE "
            "1.1.0 mapping in this codec — se:Interpolate's mode enum "
            "(linear/cosine/cubic) has no base/control-point parameters, "
            "so only 'linear' has a faithful equivalent"
        )
    lookup, *rest = expr.args
    if not isinstance(lookup, PropertyRef):
        raise NotImplementedError(
            f"{name}: interpolate lookup value {lookup!r} is not "
            "supported in this codec (only a property reference maps)"
        )
    stops, outs = rest[0::2], rest[1::2]
    for stop in stops:
        if isinstance(stop, bool) or not isinstance(stop, (int, float)):
            raise NotImplementedError(
                f"{name}: interpolate stop {stop!r} must be numeric — "
                "se:InterpolationPoint/se:Data is xsd:double per SE 1.1.0 "
                "(Symbolizer.xsd)"
            )
    for out in outs:
        if not is_valid_output(out):
            raise NotImplementedError(
                f"{name}: interpolate value {out!r} is not supported in " "this codec"
            )
    param = d.param_element(parent, name)
    interp = d.el("Interpolate", param)
    interp.set("mode", "linear")
    interp.set("method", method)
    interp.set("fallbackValue", format_output(outs[-1]))
    lookup_el = d.el("LookupValue", interp)
    etree.SubElement(lookup_el, f"{OGC}PropertyName").text = lookup.property
    for stop, out in zip(stops, outs):
        point = d.el("InterpolationPoint", interp)
        d.el("Data", point, text=str(stop))
        d.el("Value", point, text=format_output(out))


def _write_color_param(
    d: SldDialect, parent: etree._Element, name: str, color: Any
) -> None:
    """Append *color* as a ``fill``/``stroke`` colour ``SvgParameter``.

    *color* is coerced first (:func:`_coerce_color_expr`) so a raw dict
    reaching here from an untyped nested field (``Marker.elements``) is
    recognised the same as an already-typed value. A literal (``Color``/
    hex/named string) goes through :func:`._types.format_color`. A
    ``PropertyRef``/``MatchExpression``/``InterpolateExpression`` (see the
    module docstring) instead builds a bare ``ogc:PropertyName``, an
    ``se:Recode`` or an ``se:Interpolate``; any other
    :mod:`...models.value_expressions` model (``CaseExpression``,
    ``StepExpression``, ``CoalesceExpression``) has no SLD/SE mapping in
    this codec yet and raises. SE 1.1.0 only — SLD 1.0.0 has no native
    ``Recode``/``Interpolate``/``LookupValue``/``MapItem``/
    ``InterpolationPoint`` (those are SE 1.1.0 additions), so this is not
    called for that dialect (see the caller).
    """
    color = _coerce_color_expr(color)
    if isinstance(color, PropertyRef):
        param = d.param_element(parent, name)
        etree.SubElement(param, f"{OGC}PropertyName").text = color.property
        return
    if isinstance(color, MatchExpression):
        _write_recode(
            d,
            parent,
            name,
            color,
            is_valid_output=lambda v: isinstance(v, (bool, int, float, str)),
            format_output=str,
        )
        return
    if isinstance(color, InterpolateExpression):
        _write_interpolate(
            d,
            parent,
            name,
            color,
            method="color",
            is_valid_output=lambda v: not isinstance(v, BaseCartoSymModel),
            format_output=format_color,
        )
        return
    d.param(parent, name, format_color(color))


# Arithmetic ↔ ogc:Function name mapping (OGC Filter Encoding's own
# well-known arithmetic function names, shared unprefixed ``ogc:`` by both
# SLD 1.0.0 and SE 1.1.0 — unlike se:Recode/se:MapItem, these aren't
# dialect-dependent). Only the CartoSym-JSON schema's own
# arithmeticExpression op set (``+``/``-``/``*``/``/`` — no ``^``, which
# has no standard ogc:Function name and so has no mapping here either).
_ARITHMETIC_FUNCTION_NAMES = {"+": "Add", "-": "Sub", "*": "Mul", "/": "Div"}
_ARITHMETIC_FUNCTION_OPS = {v: k for k, v in _ARITHMETIC_FUNCTION_NAMES.items()}

# ArithmeticExpression's own op set (models/value_expressions.py) — unlike
# _ARITHMETIC_FUNCTION_NAMES above, this includes "^" (it has no
# ogc:Function mapping, but is still a valid ArithmeticExpression to
# construct; _write_arithmetic_function raises NotImplementedError for it
# separately, at write time).
_ARITHMETIC_EXPRESSION_OPS = {"+", "-", "*", "/", "^"}


def _coerce_numeric_expr(value: Any) -> Any:
    """Best-effort coercion of a plain expression-shaped dict to its typed class.

    A value nested inside a graphic element (``Marker.elements`` is typed
    ``Any`` — see ``models/symbolizers.py`` — so Pydantic never validates
    anything under it, unlike a direct ``Symbolizer`` field like
    ``Stroke.width``) stays a raw dict rather than a real
    ``PropertyRef``/``ArithmeticExpression``/``MatchExpression``/
    ``InterpolateExpression``/``SystemIdentifier`` instance. The
    ``isinstance`` checks below need the typed class either way, so
    recognize the dict shape here first. The ``op`` value disambiguates
    ``MatchExpression`` (``"match"``) and ``InterpolateExpression``
    (``"interpolate"``) from ``ArithmeticExpression`` (only the schema's
    own ``+``/``-``/``*``/``/``/``^``) — checking ``"op" in value`` alone
    would wrongly try to validate e.g. a ``StepExpression``/``CaseExpression``
    (MapLibre-only shapes with no SLD/SE mapping) as arithmetic and raise a
    confusing ``pydantic.ValidationError`` instead of passing it through
    unchanged, like :func:`_coerce_color_expr` does for the same shapes, so
    it falls through to the caller's own clean ``NotImplementedError``. An
    already-typed value, or anything that matches no expression shape (a
    literal), also passes through unchanged.
    """
    if isinstance(
        value,
        (
            PropertyRef,
            ArithmeticExpression,
            MatchExpression,
            InterpolateExpression,
            SystemIdentifier,
        ),
    ):
        return value
    if isinstance(value, dict):
        if "property" in value:
            return PropertyRef.model_validate(value)
        if "sysId" in value:
            return SystemIdentifier.model_validate(value)
        if value.get("op") == "match" and "args" in value:
            return MatchExpression.model_validate(value)
        if value.get("op") == "interpolate" and "args" in value:
            return InterpolateExpression.model_validate(value)
        if value.get("op") in _ARITHMETIC_EXPRESSION_OPS and "args" in value:
            return ArithmeticExpression.model_validate(value)
    return value


def _write_numeric_param(
    d: SldDialect, parent: etree._Element, name: str, value: Any
) -> None:
    """Append *value* as a numeric (e.g. ``stroke-width``) ``SvgParameter``.

    A literal goes through :func:`._types.format_unit_value`. A
    ``PropertyRef`` builds a bare ``ogc:PropertyName``, mirroring
    :func:`_write_color_param`. An ``ArithmeticExpression`` builds an
    ``ogc:Function`` (``Add``/``Sub``/``Mul``/``Div``) over
    ``PropertyRef``/number operands. A ``MatchExpression`` builds an
    ``se:Recode`` (:func:`_write_recode`, shared with
    :func:`_write_color_param`) with numeric outputs, formatted like an
    arithmetic literal (:func:`_format_arithmetic_literal`) rather than
    ``str()`` — unlike a colour ``se:Value``, which is already the right
    string. An ``InterpolateExpression`` builds an ``se:Interpolate``
    (:func:`_write_interpolate`, shared the same way) with the same
    numeric output formatting. A ``SystemIdentifier`` (e.g. ``viz.sd``,
    the current scale denominator, per OGC issue #115) has no SLD/SE
    mapping in this codec and raises — SLD/SE has no construct exposing
    the current rendering scale as a filter/expression *value*, only
    ``MinScaleDenominator``/``MaxScaleDenominator`` rule-level gating (a
    coarse binary applicability test, not a continuous input).
    """
    value = _coerce_numeric_expr(value)
    if isinstance(value, PropertyRef):
        param = d.param_element(parent, name)
        etree.SubElement(param, f"{OGC}PropertyName").text = value.property
        return
    if isinstance(value, ArithmeticExpression):
        param = d.param_element(parent, name)
        _write_arithmetic_function(param, value)
        return
    if isinstance(value, MatchExpression):
        _write_recode(
            d,
            parent,
            name,
            value,
            is_valid_output=lambda v: isinstance(v, (int, float))
            and not isinstance(v, bool),
            format_output=_format_arithmetic_literal,
        )
        return
    if isinstance(value, InterpolateExpression):
        _write_interpolate(
            d,
            parent,
            name,
            value,
            method="numeric",
            is_valid_output=lambda v: isinstance(v, (int, float))
            and not isinstance(v, bool),
            format_output=_format_arithmetic_literal,
        )
        return
    if isinstance(value, SystemIdentifier):
        raise NotImplementedError(
            f"{name}: system identifier {value.sysId!r} has no SLD/SE "
            "mapping in this codec — SLD/SE has no construct exposing the "
            "current rendering scale as a filter/expression value (only "
            "MinScaleDenominator/MaxScaleDenominator rule-level gating)"
        )
    d.param(parent, name, format_unit_value(value))


def _write_arithmetic_function(
    parent: etree._Element, expr: ArithmeticExpression
) -> None:
    """Append *expr* as an ``ogc:Function name="Add|Sub|Mul|Div"`` under *parent*."""
    fn_name = _ARITHMETIC_FUNCTION_NAMES.get(expr.op)
    if fn_name is None:
        raise NotImplementedError(
            f"arithmetic operator {expr.op!r} has no ogc:Function mapping "
            "in this codec"
        )
    fn = etree.SubElement(parent, f"{OGC}Function")
    fn.set("name", fn_name)
    for arg in expr.args:
        _write_arithmetic_arg(fn, arg)


def _write_arithmetic_arg(parent: etree._Element, arg: Any) -> None:
    """Append one ``ArithmeticExpression`` operand under *parent*."""
    arg = _coerce_numeric_expr(arg)
    if isinstance(arg, PropertyRef):
        etree.SubElement(parent, f"{OGC}PropertyName").text = arg.property
        return
    if isinstance(arg, ArithmeticExpression):
        _write_arithmetic_function(parent, arg)
        return
    if isinstance(arg, SystemIdentifier):
        raise NotImplementedError(
            f"system identifier {arg.sysId!r} has no SLD/SE mapping in "
            "this codec (see _write_numeric_param)"
        )
    if isinstance(arg, (int, float)) and not isinstance(arg, bool):
        etree.SubElement(parent, f"{OGC}Literal").text = _format_arithmetic_literal(arg)
        return
    raise NotImplementedError(f"arithmetic operand {arg!r} has no SLD/SE mapping")


def _format_arithmetic_literal(value: int | float) -> str:
    """Format a numeric literal operand — an int stays bare, matching format_number."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _write_numeric_element(
    d: SldDialect, parent: etree._Element, tag: str, value: Any
) -> etree._Element:
    """Create ``<tag>`` under *parent* for a ``UnitPoint`` coordinate.

    Unlike ``stroke-width``/``thickness`` (an ``SvgParameter``, see
    :func:`_write_numeric_param`), ``se:DisplacementX/Y`` and
    ``se:AnchorPointX/Y`` are direct XML element children with no
    wrapping parameter container — a ``PropertyRef`` becomes a bare
    ``ogc:PropertyName`` as the element's sole child instead of its
    ``.text``. A ``SystemIdentifier`` still raises (no SLD/SE construct
    exposes it as a value, same reasoning as ``stroke-width``); CartoSym-CSS
    itself cannot author one here (``UnitPoint.x``/``.y`` only accepts a
    bare property-name identifier per coordinate, not a full expression —
    see ``models/symbolizers.py::_coerce_axis_value``), but a directly
    hand-authored CS-JSON file could still reach this via
    ``Marker.elements``'s untyped ``Any`` (:func:`_coerce_numeric_expr`).
    """
    value = _coerce_numeric_expr(value)
    el = d.el(tag, parent=parent)
    if isinstance(value, PropertyRef):
        etree.SubElement(el, f"{OGC}PropertyName").text = value.property
        return el
    if isinstance(value, ArithmeticExpression):
        _write_arithmetic_function(el, value)
        return el
    if isinstance(value, SystemIdentifier):
        raise NotImplementedError(
            f"{tag}: system identifier {value.sysId!r} has no SLD/SE "
            "mapping in this codec"
        )
    el.text = format_unit_value(value)
    return el


def _build_fill_element(
    d: SldDialect, fill: Any, base_opacity: float | None = None
) -> etree._Element:
    _raise_if_fill_out_of_scope(fill)
    el = d.el("Fill")
    color = _g(fill, "color")
    if color is not None:
        _write_color_param(d, el, "fill", color)
    combined = _combine_opacity(base_opacity, _g(fill, "opacity"))
    if combined is not None:
        d.param(el, "fill-opacity", combined)
    return el


def _raise_if_stroke_out_of_scope(stroke: Any) -> None:
    if _g(stroke, "casing") is not None:
        raise NotImplementedError("Stroke.casing has no SLD/SE mapping in this codec")
    if _g(stroke, "center_line") is not None:
        raise NotImplementedError(
            "Stroke.centerLine has no SLD/SE mapping in this codec"
        )
    if _g(stroke, "pattern") is not None:
        raise NotImplementedError(
            "Stroke.pattern (graphic stroke) has no SLD/SE mapping in this codec"
        )


def _build_stroke_element(
    d: SldDialect, stroke: Any, base_opacity: float | None = None
) -> etree._Element:
    _raise_if_stroke_out_of_scope(stroke)
    el = d.el("Stroke")
    color = _g(stroke, "color")
    width = _g(stroke, "width")
    dash_pattern = _g(stroke, "dash_pattern")
    if color is not None:
        _write_color_param(d, el, "stroke", color)
    if width is not None:
        _write_numeric_param(d, el, "stroke-width", width)
    combined = _combine_opacity(base_opacity, _g(stroke, "opacity"))
    if combined is not None:
        d.param(el, "stroke-opacity", combined)
    if dash_pattern is not None:
        if not isinstance(dash_pattern, list):
            raise NotImplementedError(
                "Stroke.dashPattern with no resolved array (an unflattened "
                "index/value cascade-override fragment?) has no SLD/SE "
                "mapping in this codec"
            )
        if dash_pattern:
            d.param(el, "stroke-dasharray", " ".join(str(int(p)) for p in dash_pattern))
    join = _g(stroke, "join")
    if join is not None:
        d.param(el, "stroke-linejoin", join)
    cap = _g(stroke, "cap")
    if cap is not None:
        d.param(el, "stroke-linecap", cap)
    return el


def _build_polygon_symbolizer(
    d: SldDialect, fill: Any, stroke: Any, base_opacity: float | None = None
) -> etree._Element:
    el = d.el("PolygonSymbolizer")
    if fill is not None:
        el.append(_build_fill_element(d, fill, base_opacity))
    if stroke is not None:
        el.append(_build_stroke_element(d, stroke, base_opacity))
    return el


def _build_line_symbolizer(
    d: SldDialect, stroke: Any, base_opacity: float | None = None
) -> etree._Element:
    el = d.el("LineSymbolizer")
    el.append(_build_stroke_element(d, stroke, base_opacity))
    return el


def _g2(obj: Any, snake: str, camel: str, default: Any = None) -> Any:
    """Like :func:`_g`, but for raster sub-dicts (``hillShading``, ...).

    Those are always raw ``Any``-typed dicts with camelCase JSON keys —
    never alias-normalised by Pydantic — so both spellings must be tried.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj[snake] if snake in obj else obj.get(camel, default)
    return getattr(obj, snake, default)


def _channel_source_name(channel_expr: Any, field_label: str) -> str:
    """Return the plain band/property name for one channel entry.

    Applies to ``colorChannels`` / ``singleChannel`` entries. Only a bare
    ``{"property": X}`` reference maps to ``se:SourceChannelName`` — a
    plain-string XSD type, unable to hold an arithmetic expression (e.g.
    an NDVI formula) at all.
    """
    if isinstance(channel_expr, dict) and set(channel_expr) == {"property"}:
        return str(channel_expr["property"])
    raise NotImplementedError(
        f"Symbolizer.{field_label} entries other than a bare property "
        f"reference ({{'property': X}}) have no se:SourceChannelName "
        f"mapping in this codec (got {channel_expr!r})"
    )


def _build_channel_selection_rgb(d: SldDialect, color_channels: Any) -> etree._Element:
    if not isinstance(color_channels, list) or len(color_channels) != 3:
        raise NotImplementedError(
            "Symbolizer.colorChannels must be a 3-element [R, G, B] list "
            f"(got {color_channels!r})"
        )
    cs = d.el("ChannelSelection")
    for tag, expr in zip(("RedChannel", "GreenChannel", "BlueChannel"), color_channels):
        name = _channel_source_name(expr, "colorChannels")
        channel_el = d.el(tag, parent=cs)
        d.el("SourceChannelName", parent=channel_el, text=name)
    return cs


def _build_channel_selection_gray(d: SldDialect, single_channel: Any) -> etree._Element:
    name = _channel_source_name(single_channel, "singleChannel")
    cs = d.el("ChannelSelection")
    gray_el = d.el("GrayChannel", parent=cs)
    d.el("SourceChannelName", parent=gray_el, text=name)
    return cs


def _validated_map_pairs(value: Any, field_label: str) -> list:
    if not isinstance(value, list) or not value:
        raise NotImplementedError(
            f"Symbolizer.{field_label} must be a non-empty list of "
            f"[threshold, value] pairs (got {value!r})"
        )
    for pair in value:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            raise NotImplementedError(
                f"Symbolizer.{field_label} entries must be [threshold, "
                f"value] pairs (got {pair!r})"
            )
    return value


def _build_categorize(d: SldDialect, pairs: list) -> etree._Element:
    """Build ``se:Categorize`` from ``[threshold, color]`` pairs.

    Per ``se:Categorize``'s own semantics, the first ``se:Value`` has no
    preceding ``se:Threshold`` (it's the below/at-first-value bucket) —
    ``pairs[0][0]`` is therefore never written.
    """
    categorize = d.el("Categorize")
    # fallbackValue is required on se:FunctionType (SE 1.1.0). It is the
    # value returned for an uncategorisable input; the below-first-
    # threshold colour is the natural choice. Ignored on read (regenerated
    # deterministically, so the round trip stays stable).
    categorize.set("fallbackValue", format_color(pairs[0][1]))
    d.el("LookupValue", parent=categorize, text="Rasterdata")
    d.el("Value", parent=categorize, text=format_color(pairs[0][1]))
    for threshold, value in pairs[1:]:
        d.el("Threshold", parent=categorize, text=format_number(threshold))
        d.el("Value", parent=categorize, text=format_color(value))
    return categorize


def _build_color_map_entries(d: SldDialect, pairs: list) -> etree._Element:
    """Build the SLD 1.0.0 ``<ColorMap><ColorMapEntry .../></ColorMap>`` form.

    Each ``[threshold, colour, label?]`` model entry becomes one
    ``<ColorMapEntry color quantity [label]/>`` — a clean 1:1 mapping, no
    synthesised first threshold (unlike ``se:Categorize``).
    """
    cm = d.el("ColorMap")
    for pair in pairs:
        entry = d.el("ColorMapEntry", parent=cm)
        entry.set("color", format_color(pair[1]))
        entry.set("quantity", format_number(pair[0]))
        if len(pair) > 2 and pair[2] is not None:
            entry.set("label", str(pair[2]))
    return cm


def _build_color_map(d: SldDialect, color_map: Any) -> etree._Element:
    pairs = _validated_map_pairs(color_map, "colorMap")
    if d.raster_colormap == "entry":
        return _build_color_map_entries(d, pairs)
    cm = d.el("ColorMap")
    cm.append(_build_categorize(d, pairs))
    return cm


def _build_shaded_relief(d: SldDialect, hill_shading: Any) -> etree._Element:
    if _g2(hill_shading, "sun", "sun") is not None:
        raise NotImplementedError(
            "HillShading.sun (azimuth/elevation) has no SE 1.1.0 "
            "se:ShadedRelief mapping — confirmed N/A by Annex B, a "
            "permanent gap"
        )
    if _g2(hill_shading, "color_map", "colorMap") is not None:
        raise NotImplementedError(
            "HillShading.colorMap has no documented SE 1.1.0 mapping — "
            "Annex B is silent"
        )
    if _g2(hill_shading, "opacity_map", "opacityMap") is not None:
        raise NotImplementedError(
            "HillShading.opacityMap has no documented SE 1.1.0 mapping — "
            "Annex B is silent"
        )
    sr = d.el("ShadedRelief")
    factor = _g2(hill_shading, "factor", "factor")
    if factor is not None:
        d.el("ReliefFactor", parent=sr, text=format_number(factor))
    return sr


def _build_raster_symbolizer(
    d: SldDialect, sym: Any, base_opacity: float | None = None
) -> etree._Element:
    rs = d.el("RasterSymbolizer")

    # se:RasterSymbolizerType order: Geometry?, Opacity?, ChannelSelection?, ...
    if base_opacity is not None:
        d.el("Opacity", parent=rs, text=format_opacity(base_opacity))

    color_channels = _g(sym, "color_channels")
    single_channel = _g(sym, "single_channel")
    if color_channels is not None and single_channel is not None:
        raise NotImplementedError(
            "Symbolizer.colorChannels and Symbolizer.singleChannel cannot "
            "both be set — se:ChannelSelection is RGB *or* Gray, not both"
        )
    if color_channels is not None:
        rs.append(_build_channel_selection_rgb(d, color_channels))
    elif single_channel is not None:
        rs.append(_build_channel_selection_gray(d, single_channel))

    if _g(sym, "alpha_channel") is not None:
        raise NotImplementedError(
            "Symbolizer.alphaChannel has no SE 1.1.0 RasterSymbolizer "
            "construct — confirmed N/A by Annex B, a permanent gap"
        )
    if _g(sym, "opacity_map") is not None:
        raise NotImplementedError(
            "Symbolizer.opacityMap has no clear SE 1.1.0 mapping — Annex "
            "B's own table is self-contradictory here"
        )

    color_map = _g(sym, "color_map")
    if color_map is not None:
        rs.append(_build_color_map(d, color_map))

    hill_shading = _g(sym, "hill_shading")
    if hill_shading is not None:
        rs.append(_build_shaded_relief(d, hill_shading))

    return rs


def _build_point_symbolizer(
    d: SldDialect, dot: Any, base_opacity: float | None = None
) -> etree._Element:
    ps = d.el("PointSymbolizer")
    graphic = d.el("Graphic", parent=ps)
    mark = d.el("Mark", parent=graphic)
    d.el("WellKnownName", parent=mark, text="circle")

    color = _g(dot, "color")
    if color is not None:
        fill_el = d.el("Fill", parent=mark)
        _write_color_param(d, fill_el, "fill", color)

    # se:GraphicType order: (Mark|ExternalGraphic)*, Opacity?, Size?, ...
    combined = _combine_opacity(base_opacity, _g(dot, "opacity"))
    if combined is not None:
        d.el("Opacity", parent=graphic, text=combined)

    size = _g(dot, "size")
    if size is not None:
        _write_numeric_element(d, graphic, "Size", size)

    _build_graphic_displacement(d, graphic, _g(dot, "position"), "Dot")
    return ps


def _build_shape_outline_element(
    d: SldDialect, outline: Any, base_opacity: float | None = None
) -> etree._Element:
    """Turn a ``2-shapes`` ``shapeOutline`` into ``se:Stroke`` (child of ``se:Mark``).

    ``shapeOutline`` is not a ``1-core`` ``Stroke``: it carries only
    ``color`` / ``thickness`` / ``opacity`` (no casing, centre line or
    dash pattern), matching Part 2 Annex B "Shape Outlines"
    (``thickness`` -> ``stroke-width``).
    """
    if _g(outline, "alter") is not None:
        raise NotImplementedError(
            "ShapeOutline.alter has no SLD/SE mapping in this codec"
        )
    el = d.el("Stroke")
    color = _g(outline, "color")
    if color is not None:
        _write_color_param(d, el, "stroke", color)
    thickness = _g(outline, "thickness")
    if thickness is not None:
        _write_numeric_param(d, el, "stroke-width", thickness)
    combined = _combine_opacity(base_opacity, _g(outline, "opacity"))
    if combined is not None:
        d.param(el, "stroke-opacity", combined)
    return el


def _write_rotation(d: SldDialect, graphic: etree._Element, transform: Any) -> None:
    """Emit ``se:Rotation`` for a non-``None`` ``transform.orientation``.

    Present in both dialects (unlike ``se:Displacement``/``se:AnchorPoint``,
    ``se:Rotation`` isn't SE 1.1.0-only), so no ``d.graphic_placement``
    gating is needed.
    """
    if transform is None:
        return
    orientation = _g(transform, "orientation")
    if orientation is None:
        return
    d.el("Rotation", parent=graphic, text=format_angle(orientation))


def _build_circle_symbolizer(
    d: SldDialect, circle: Any, base_opacity: float | None = None
) -> etree._Element:
    """Turn a ``2-shapes`` ``Circle`` element into ``se:PointSymbolizer`` / ``se:Mark``.

    ``fill`` -> ``se:Mark/se:Fill``; ``outline`` -> ``se:Mark/se:Stroke``;
    ``radius`` -> ``se:Graphic/se:Size`` **doubled** (``se:Size`` is a
    diameter, ``radius`` a radius); ``opacity`` -> ``se:Graphic/se:Opacity``;
    ``transform.orientation`` -> ``se:Graphic/se:Rotation``;
    ``position`` -> ``se:Graphic/se:Displacement``.
    """
    ps = d.el("PointSymbolizer")
    graphic = d.el("Graphic", parent=ps)
    mark = d.el("Mark", parent=graphic)
    d.el("WellKnownName", parent=mark, text="circle")

    fill = _g(circle, "fill")
    if fill is not None:
        mark.append(_build_fill_element(d, fill, base_opacity))

    outline = _g(circle, "outline")
    if outline is not None:
        mark.append(_build_shape_outline_element(d, outline, base_opacity))

    # se:GraphicType order: (Mark|ExternalGraphic)*, Opacity?, Size?,
    # Rotation?, AnchorPoint?, Displacement?
    combined = _combine_opacity(base_opacity, _g(circle, "opacity"))
    if combined is not None:
        d.el("Opacity", parent=graphic, text=combined)

    radius = _g(circle, "radius")
    if radius is not None:
        diameter = _number_of(radius)
        if diameter is None:
            raise NotImplementedError(
                f"Property-driven / expression Circle.radius {radius!r} has "
                "no SLD/SE mapping in this codec"
            )
        d.el("Size", parent=graphic, text=format_number(diameter * 2))

    _write_rotation(d, graphic, _g(circle, "transform"))
    _build_graphic_displacement(d, graphic, _g(circle, "position"), "Circle")
    return ps


def _build_rectangle_symbolizer(
    d: SldDialect, rectangle: Any, base_opacity: float | None = None
) -> etree._Element:
    """Turn a ``2-shapes`` ``Rectangle`` into ``se:PointSymbolizer``/``se:Mark``.

    ``se:Mark wellKnownName="square"`` only — ``se:Graphic/se:Size`` is a
    single scalar, so ``width`` and ``height`` must be equal (a non-square
    rectangle has no ``se:Mark`` mapping and raises). Otherwise the same
    shape as :func:`_build_circle_symbolizer`: ``fill``/``outline``/
    ``opacity``/``transform.orientation``/``position`` map the same way.
    """
    ps = d.el("PointSymbolizer")
    graphic = d.el("Graphic", parent=ps)
    mark = d.el("Mark", parent=graphic)
    d.el("WellKnownName", parent=mark, text="square")

    fill = _g(rectangle, "fill")
    if fill is not None:
        mark.append(_build_fill_element(d, fill, base_opacity))

    outline = _g(rectangle, "outline")
    if outline is not None:
        mark.append(_build_shape_outline_element(d, outline, base_opacity))

    combined = _combine_opacity(base_opacity, _g(rectangle, "opacity"))
    if combined is not None:
        d.el("Opacity", parent=graphic, text=combined)

    width = _number_of(_g(rectangle, "width"))
    height = _number_of(_g(rectangle, "height"))
    if width is not None or height is not None:
        if width is None or height is None:
            raise NotImplementedError(
                "Property-driven / expression RectangleGraphic width/height "
                "has no SLD/SE mapping in this codec"
            )
        if width != height:
            raise NotImplementedError(
                f"RectangleGraphic with width ({width!r}) != height "
                f"({height!r}) has no SLD/SE mapping in this codec — "
                'se:Mark wellKnownName="square" only represents a single '
                "uniform se:Size"
            )
        d.el("Size", parent=graphic, text=format_number(width))

    _write_rotation(d, graphic, _g(rectangle, "transform"))
    _build_graphic_displacement(d, graphic, _g(rectangle, "position"), "Rectangle")
    return ps


def _build_graphic_displacement(
    d: SldDialect, graphic: etree._Element, position: Any, ctx: str
) -> None:
    """Emit ``se:Displacement`` for a non-zero point-graphic offset.

    SLD 1.0.0's ``Graphic`` has no ``Displacement`` child (it stops at
    ``Rotation``), so a non-zero offset is out of scope there.
    """
    if position is None:
        return
    px, py = _unit_point_xy(position)
    if (px or 0) == 0 and (py or 0) == 0:
        return
    if not d.graphic_placement:
        raise NotImplementedError(
            f"Non-zero {ctx}.position (offset) has no SLD 1.0.0 Graphic "
            "mapping (Graphic has no Displacement child before Rotation)"
        )
    disp = d.el("Displacement", parent=graphic)
    _write_numeric_element(d, disp, "DisplacementX", px or 0)
    _write_numeric_element(d, disp, "DisplacementY", py or 0)


def _percent_to_fraction(value: Any) -> float:
    if isinstance(value, dict) and set(value) == {"pc"}:
        return float(value["pc"]) / 100
    raise NotImplementedError(
        f"ImageGraphic.hotSpot component {value!r} is not a percent (pc) "
        "unit value — only pc-unit hotSpot maps to se:AnchorPoint in this "
        "codec"
    )


def _hot_spot_to_anchor_fraction(hot_spot: Any):
    if isinstance(hot_spot, (list, tuple)) and len(hot_spot) == 2:
        x_raw, y_raw = hot_spot
    elif isinstance(hot_spot, dict) and "x" in hot_spot and "y" in hot_spot:
        x_raw, y_raw = hot_spot["x"], hot_spot["y"]
    else:
        raise NotImplementedError(
            f"Unsupported ImageGraphic.hotSpot shape: {hot_spot!r}"
        )
    return _percent_to_fraction(x_raw), _percent_to_fraction(y_raw)


def _raise_if_image_out_of_scope(image_graphic: Any) -> None:
    for attr in ("tint", "blackTint", "alphaThreshold"):
        if _g(image_graphic, attr) is not None:
            raise NotImplementedError(
                f"ImageGraphic.{attr} has no SLD/SE mapping in this codec "
                "— Annex B is silent on it entirely"
            )


def _build_image_symbolizer(
    d: SldDialect, image_graphic: Any, base_opacity: float | None = None
) -> etree._Element:
    _raise_if_image_out_of_scope(image_graphic)

    resource = _g(image_graphic, "image")
    if resource is None:
        raise NotImplementedError("ImageGraphic.image (Resource) is required")
    uri = _g(resource, "uri")
    if uri is None:
        raise NotImplementedError(
            "Resource.path-only images (no uri) have no SLD/SE mapping in "
            "this codec — no local-file resolution"
        )
    mime_type = _g(resource, "type")

    ps = d.el("PointSymbolizer")
    graphic = d.el("Graphic", parent=ps)
    ext_graphic = d.el("ExternalGraphic", parent=graphic)
    online_resource = d.el("OnlineResource", parent=ext_graphic)
    online_resource.set(f"{XLINK}type", "simple")
    online_resource.set(f"{XLINK}href", uri)
    if mime_type is not None:
        d.el("Format", parent=ext_graphic, text=mime_type)

    # se:GraphicType order: (Mark|ExternalGraphic)*, Opacity?, Size?,
    # Rotation?, AnchorPoint?, Displacement?
    combined = _combine_opacity(base_opacity, _g(image_graphic, "opacity"))
    if combined is not None:
        d.el("Opacity", parent=graphic, text=combined)

    _write_rotation(d, graphic, _g(image_graphic, "transform"))

    hot_spot = _g(image_graphic, "hotSpot")
    if hot_spot is not None:
        fx, fy = _hot_spot_to_anchor_fraction(hot_spot)
        if not d.graphic_placement:
            raise NotImplementedError(
                "ImageGraphic.hotSpot has no SLD 1.0.0 Graphic mapping "
                "(Graphic has no AnchorPoint child)"
            )
        # se:AnchorPoint belongs inside se:Graphic (after ExternalGraphic/
        # Mark, Opacity, Size, Rotation), not directly under the symbolizer.
        anchor_el = d.el("AnchorPoint", parent=graphic)
        d.el("AnchorPointX", parent=anchor_el, text=format_number(fx))
        d.el("AnchorPointY", parent=anchor_el, text=format_number(fy))

    _build_graphic_displacement(
        d, graphic, _g(image_graphic, "position"), "ImageGraphic"
    )
    return ps


def _alignment_hv(alignment: Any):
    if isinstance(alignment, (list, tuple)) and len(alignment) == 2:
        return alignment[0], alignment[1]
    if isinstance(alignment, dict):
        h = alignment.get("hAlignment") or alignment.get("h_alignment")
        v = alignment.get("vAlignment") or alignment.get("v_alignment")
        return h, v
    h = _g(alignment, "h_alignment")
    v = _g(alignment, "v_alignment")
    return h, v


def _build_halo(d: SldDialect, ts: etree._Element, outline: Any) -> None:
    """Emit ``se:Halo`` from a CartoSym ``font.outline`` (size / opacity / color)."""
    halo_el = d.el("Halo", parent=ts)
    size = _g(outline, "size")
    if size is not None:
        _write_numeric_element(d, halo_el, "Radius", size)
    color = _g(outline, "color")
    opacity = _g(outline, "opacity")
    if color is not None or opacity is not None:
        fill_el = d.el("Fill", parent=halo_el)
        if color is not None:
            _write_color_param(d, fill_el, "fill", color)
        if opacity is not None:
            d.param(fill_el, "fill-opacity", format_opacity(opacity))


def _build_text_symbolizer(
    d: SldDialect, text_graphic: Any, base_opacity: float | None = None
) -> etree._Element:
    if _g(text_graphic, "transform") is not None:
        raise NotImplementedError(
            "TextGraphic.transform has no SLD/SE mapping in this codec — "
            "text labels use se:LabelPlacement, not se:Graphic/se:Rotation"
        )
    ts = d.el("TextSymbolizer")

    text = _g(text_graphic, "text")
    label_el = d.el("Label", parent=ts)
    if isinstance(text, dict) and "property" in text:
        etree.SubElement(label_el, f"{OGC}PropertyName").text = text["property"]
    elif isinstance(text, str):
        label_el.text = text
    else:
        raise NotImplementedError(f"Unsupported Text.text shape: {text!r}")

    # Font color/opacity map to se:Fill, but SE's TextSymbolizerType fixes
    # the child order as Label, Font, LabelPlacement, Halo, Fill — so the
    # Fill element is built last, after the placement block below.
    font_color = None
    font_opacity = None
    font = _g(text_graphic, "font")
    if font is not None:
        if _g(font, "underline"):
            raise NotImplementedError(
                "Font.underline has no se:Font mapping in this codec"
            )
        font_el = d.el("Font", parent=ts)
        face = _g(font, "face")
        size = _g(font, "size")
        bold = _g(font, "bold")
        italic = _g(font, "italic")
        if face is not None:
            d.param(font_el, "font-family", str(face))
        if size is not None:
            _write_numeric_param(d, font_el, "font-size", size)
        if bold is not None:
            d.param(font_el, "font-weight", "bold" if bold else "normal")
        if italic is not None:
            d.param(font_el, "font-style", "italic" if italic else "normal")

        font_color = _g(font, "color")
        font_opacity = _g(font, "opacity")

    font_outline = _g(font, "outline") if font is not None else None

    alignment = _g(text_graphic, "alignment")
    position = _g(text_graphic, "position")
    px, py = _unit_point_xy(position) if position is not None else (None, None)
    has_displacement = (px or 0) != 0 or (py or 0) != 0

    if alignment is not None or has_displacement:
        placement_el = d.el("LabelPlacement", parent=ts)
        point_placement_el = d.el("PointPlacement", parent=placement_el)
        if alignment is not None:
            h, v = _alignment_hv(alignment)
            anchor_el = d.el("AnchorPoint", parent=point_placement_el)
            d.el("AnchorPointX", parent=anchor_el, text=_ANCHOR_X.get(h, "0.5"))
            d.el("AnchorPointY", parent=anchor_el, text=_ANCHOR_Y.get(v, "0.5"))
        if has_displacement:
            disp_el = d.el("Displacement", parent=point_placement_el)
            _write_numeric_element(d, disp_el, "DisplacementX", px or 0)
            _write_numeric_element(d, disp_el, "DisplacementY", py or 0)

    # se:TextSymbolizerType order: Label, Font, LabelPlacement, Halo, Fill.
    if font_outline is not None:
        _build_halo(d, ts, font_outline)

    combined_opacity = _combine_opacity(base_opacity, font_opacity)
    if font_color is not None or combined_opacity is not None:
        fill_el = d.el("Fill", parent=ts)
        if font_color is not None:
            _write_color_param(d, fill_el, "fill", font_color)
        if combined_opacity is not None:
            d.param(fill_el, "fill-opacity", combined_opacity)

    return ts


# ---------------------------------------------------------------------------
# Reader direction: SLD/SE symbolizer elements -> Symbolizer dict
# ---------------------------------------------------------------------------


def elements_to_symbolizer(d: SldDialect, sym_elements: list[etree._Element]) -> dict:
    """Convert one ``se:Rule``'s symbolizer elements into a CartoSym symbolizer.

    Returns a CS-JSON-shaped ``symbolizer`` dict, ready for
    ``Style.from_dict``.
    """
    result: dict = {}
    marker_elements: list[dict] = []
    label_elements: list[dict] = []

    for el in sym_elements:
        tag = local_name(el)
        if d.vendor_options:
            for name, value in _read_vendor_options(d, el):
                result[f"vendor.geoserver.{name}"] = value
        if d.find(el, "Geometry") is not None:
            # SE 1.1.0 "symbolizer geometry" — an optional <se:Geometry>
            # <ogc:PropertyName> selecting which geometry property to
            # render. CartoSym's 3-geometry "Symbolizer Geometry"
            # requirements class is not yet defined in the conceptual
            # model (empty rc-symbolizer-geometry.adoc, no `geometry`
            # field on the CS-JSON `symbolizer`), so there is nothing to
            # map it to — raise rather than silently drop it, per the
            # lossless-transcoding requirement.
            raise NotImplementedError(
                f"se:{tag}/se:Geometry (symbolizer geometry) has no CartoSym "
                "conceptual-model representation yet"
            )
        if tag == "PolygonSymbolizer":
            fill_el = d.find(el, "Fill")
            stroke_el = d.find(el, "Stroke")
            if fill_el is not None:
                result["fill"] = _parse_fill_element(d, fill_el)
            if stroke_el is not None:
                result["stroke"] = _parse_stroke_element(d, stroke_el)
        elif tag == "LineSymbolizer":
            offset_el = d.find(el, "PerpendicularOffset")
            if offset_el is not None and float(offset_el.text or 0) != 0:
                # A zero offset is a portrayal no-op (same as the element
                # being absent) and passes silently; any other value has
                # no CartoSym Stroke field to hold it.
                raise NotImplementedError(
                    "se:LineSymbolizer/se:PerpendicularOffset has no CartoSym "
                    "mapping in this codec"
                )
            stroke_el = d.find(el, "Stroke")
            if stroke_el is None:
                raise NotImplementedError(
                    "se:LineSymbolizer without se:Stroke is not supported"
                )
            result["stroke"] = _parse_stroke_element(d, stroke_el)
        elif tag == "PointSymbolizer":
            marker_elements.append(_parse_point_symbolizer(d, el))
        elif tag == "TextSymbolizer":
            label_elements.append(_parse_text_symbolizer(d, el))
        elif tag == "RasterSymbolizer":
            result.update(_parse_raster_symbolizer(d, el))
        else:
            raise NotImplementedError(f"Unsupported symbolizer element <{tag}>")

    if marker_elements:
        result["marker"] = {"elements": marker_elements}
    if label_elements:
        result["label"] = {"elements": label_elements}
    return result


def _reject_unknown_params(
    d: SldDialect, el: etree._Element, known: set[str], ctx: str
) -> None:
    """Fail loudly on a styling parameter this codec has no mapping for.

    Silently dropping e.g. ``stroke-dashoffset`` would break the
    lossless-transcoding guarantee, so an unrecognised ``CssParameter`` /
    ``SvgParameter`` name makes the whole document out of scope.
    """
    for param in d.findall(el, d.param_tag):
        name = param.get("name")
        if name not in known:
            raise NotImplementedError(
                f"{ctx} style parameter {name!r} has no CartoSym mapping in "
                "this codec's scope"
            )


def _validated_enum(value: str, name: str, allowed: set[str]) -> str:
    """Check a parameter value against the enum this codec maps.

    Used for ``stroke-linejoin``/``stroke-linecap``, whose CartoSym Part
    2 (``strokeJoin``/``strokeCap``) target is a closed enum matching the
    underlying SVG stroke-linejoin/-linecap spec — always ``miter``,
    never the British ``mitre`` some tools emit. A value this codec
    doesn't recognise raises rather than being passed through unchecked
    or silently normalised (that would be guessing at a mapping).
    """
    if value not in allowed:
        raise NotImplementedError(
            f"{name} {value!r} is not one of {sorted(allowed)} in this codec"
        )
    return value


def _coerce_recode_literal(text: str | None) -> Any:
    """Coerce an ``ogc:Literal``/``fallbackValue`` string to bool/int/float/str.

    Mirrors ``_filter.py``'s ``_coerce_literal`` (kept local rather than
    imported — this module doesn't otherwise depend on ``_filter.py``).
    """
    if text is None:
        return None
    if text in ("true", "false"):
        return text == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _property_ref_from_container(elem: etree._Element) -> dict | None:
    """Return ``{"property": ...}`` if *elem*'s single child is ``ogc:PropertyName``.

    ``None`` otherwise — the container (an ``SvgParameter``, or an
    ``se:LookupValue``, both ``se:ParameterValueType``-shaped mixed
    content) holds something else instead: a plain literal, or an
    unsupported shape for the caller to reject.
    """
    children = [c for c in elem if isinstance(c.tag, str)]
    if len(children) == 1 and local_name(children[0]) == "PropertyName":
        return {"property": children[0].text}
    return None


def _parse_recode(d: SldDialect, recode_el: etree._Element) -> dict:
    """Parse an ``se:Recode`` element into a CartoSym ``match`` expression.

    See the module docstring for the lookup-value scope and why
    ``op: "match"`` (MapLibre's own vocabulary, see
    :mod:`...models.value_expressions`) is reused rather than a
    CartoSym-specific ``"recode"`` name. ``fallbackValue`` (required on
    ``se:FunctionType``, SE 1.1.0) becomes ``match``'s trailing arg.
    """
    fallback = recode_el.get("fallbackValue")
    if fallback is None:
        raise NotImplementedError(
            "se:Recode without a fallbackValue attribute (required on "
            "se:FunctionType, SE 1.1.0) has no CartoSym mapping in this codec"
        )
    lookup_el = d.find(recode_el, "LookupValue")
    lookup = _property_ref_from_container(lookup_el) if lookup_el is not None else None
    if lookup is None:
        raise NotImplementedError(
            "se:Recode/se:LookupValue is missing, or is not a bare "
            "ogc:PropertyName — not supported in this codec"
        )
    map_items = d.findall(recode_el, "MapItem")
    if not map_items:
        raise NotImplementedError("se:Recode without any se:MapItem")
    args: list[Any] = [lookup]
    for item in map_items:
        data_el, value_el = d.find(item, "Data"), d.find(item, "Value")
        if data_el is None or value_el is None:
            raise NotImplementedError("se:MapItem without se:Data/se:Value")
        args.append(_coerce_recode_literal(element_text(data_el)))
        args.append(_coerce_recode_literal(element_text(value_el)))
    args.append(_coerce_recode_literal(fallback))
    return {"op": "match", "args": args}


def _parse_interpolate(d: SldDialect, interp_el: etree._Element) -> dict:
    """Parse an ``se:Interpolate`` element into a CartoSym ``interpolate`` expression.

    Inverse of :func:`_write_interpolate`. Only ``mode="linear"`` (or the
    attribute absent, treated the same as the writer's own default) is
    supported — ``cosine``/``cubic`` have no ``InterpolateExpression``
    equivalent (see that function's docstring). ``se:Data``/``se:Value``
    reuse :func:`_coerce_recode_literal` (already generic across numeric/
    colour text, same as :func:`_parse_recode`) — nothing method-specific
    needed to tell them apart on read.
    """
    mode = interp_el.get("mode")
    if mode is not None and mode != "linear":
        raise NotImplementedError(
            f"se:Interpolate mode={mode!r} has no CartoSym mapping in this "
            "codec (only 'linear' does)"
        )
    lookup_el = d.find(interp_el, "LookupValue")
    lookup = _property_ref_from_container(lookup_el) if lookup_el is not None else None
    if lookup is None:
        raise NotImplementedError(
            "se:Interpolate/se:LookupValue is missing, or is not a bare "
            "ogc:PropertyName — not supported in this codec"
        )
    points = d.findall(interp_el, "InterpolationPoint")
    if not points:
        raise NotImplementedError("se:Interpolate without any se:InterpolationPoint")
    args: list[Any] = [lookup]
    for point in points:
        data_el, value_el = d.find(point, "Data"), d.find(point, "Value")
        if data_el is None or value_el is None:
            raise NotImplementedError("se:InterpolationPoint without se:Data/se:Value")
        args.append(_coerce_recode_literal(element_text(data_el)))
        args.append(_coerce_recode_literal(element_text(value_el)))
    return {"op": "interpolate", "interpolation": "linear", "args": args}


def _parse_flexible_param(d: SldDialect, elem: etree._Element, name: str) -> Any:
    """Return an ``SvgParameter``'s value: text, an expression dict, or ``None``.

    A bare ``ogc:PropertyName``, an ``se:Recode`` or an ``se:Interpolate``
    child (SE 1.1.0 only) is a property-driven expression (see the module
    docstring); anything else falls back to
    :func:`._xml_helpers.element_text` (a plain literal, or the
    ``None``/``NotImplementedError`` — via ``parse_color``/
    ``parse_opacity`` — an unsupported shape already produces).
    """
    param = d.get_param_element(elem, name)
    if param is None:
        return None
    ref = _property_ref_from_container(param)
    if ref is not None:
        return ref
    if d.recode_function:
        recode_el = d.find(param, "Recode")
        if recode_el is not None:
            return _parse_recode(d, recode_el)
    if d.interpolate_function:
        interp_el = d.find(param, "Interpolate")
        if interp_el is not None:
            return _parse_interpolate(d, interp_el)
    return element_text(param)


def _parse_arithmetic_function(fn_el: etree._Element) -> dict:
    """Parse an ``ogc:Function`` (``Add``/``Sub``/``Mul``/``Div``) into an expression.

    Inverse of :func:`_write_arithmetic_function`.
    """
    fn_name = fn_el.get("name")
    op = _ARITHMETIC_FUNCTION_OPS.get(fn_name) if fn_name else None
    if op is None:
        raise NotImplementedError(
            f"ogc:Function name={fn_name!r} has no arithmeticExpression "
            "mapping in this codec"
        )
    children = [c for c in fn_el if isinstance(c.tag, str)]
    return {"op": op, "args": [_parse_arithmetic_arg(c) for c in children]}


def _parse_arithmetic_arg(el: etree._Element) -> Any:
    """Parse one ``ogc:PropertyName``/``ogc:Literal``/``ogc:Function`` operand."""
    tag = local_name(el)
    if tag == "PropertyName":
        return {"property": el.text}
    if tag == "Literal":
        return parse_number(element_text(el))
    if tag == "Function":
        return _parse_arithmetic_function(el)
    raise NotImplementedError(f"ogc:{tag} has no arithmetic-operand mapping")


def _parse_flexible_numeric_param(
    d: SldDialect, elem: etree._Element, name: str
) -> Any:
    """Return a numeric ``SvgParameter``'s value: text, a property-driven dict, or None.

    A bare ``ogc:PropertyName`` is a property reference; an ``ogc:Function``
    (``Add``/``Sub``/``Mul``/``Div``) is an arithmetic expression over such
    references/literals (see :func:`_write_numeric_param`); an ``se:Recode``
    or ``se:Interpolate`` child (SE 1.1.0 only, mirroring
    :func:`_parse_flexible_param`) is a match/interpolate expression,
    parsed by the same :func:`_parse_recode`/:func:`_parse_interpolate`
    used for colour — they already coerce ``se:Data``/``se:Value`` text to
    bool/int/float/str generically, nothing numeric-specific needed there.
    Anything else falls back to :func:`._xml_helpers.element_text` (a plain
    literal).
    """
    param = d.get_param_element(elem, name)
    if param is None:
        return None
    ref = _property_ref_from_container(param)
    if ref is not None:
        return ref
    if d.recode_function:
        recode_el = d.find(param, "Recode")
        if recode_el is not None:
            return _parse_recode(d, recode_el)
    if d.interpolate_function:
        interp_el = d.find(param, "Interpolate")
        if interp_el is not None:
            return _parse_interpolate(d, interp_el)
    children = [c for c in param if isinstance(c.tag, str)]
    if len(children) == 1 and local_name(children[0]) == "Function":
        return _parse_arithmetic_function(children[0])
    return element_text(param)


def _parse_fill_element(d: SldDialect, fill_el: etree._Element) -> dict:
    if d.find(fill_el, "GraphicFill") is not None:
        raise NotImplementedError(
            "se:Fill/se:GraphicFill (hatch/pattern fills) is out of scope "
            "for this codec"
        )
    _reject_unknown_params(d, fill_el, {"fill", "fill-opacity"}, "Fill")
    result: dict = {}
    color = _parse_flexible_param(d, fill_el, "fill")
    opacity = _parse_flexible_param(d, fill_el, "fill-opacity")
    if color is not None:
        result["color"] = color if isinstance(color, dict) else parse_color(color)
    if opacity is not None:
        result["opacity"] = (
            opacity if isinstance(opacity, dict) else parse_opacity(opacity)
        )
    return result


def _parse_stroke_element(d: SldDialect, stroke_el: etree._Element) -> dict:
    if (
        d.find(stroke_el, "GraphicStroke") is not None
        or d.find(stroke_el, "GraphicFill") is not None
    ):
        raise NotImplementedError(
            "se:Stroke graphic-fill/-stroke patterns are out of scope for this codec"
        )
    _reject_unknown_params(
        d,
        stroke_el,
        {
            "stroke",
            "stroke-width",
            "stroke-opacity",
            "stroke-dasharray",
            "stroke-linejoin",
            "stroke-linecap",
        },
        "Stroke",
    )
    result: dict = {}
    color = _parse_flexible_param(d, stroke_el, "stroke")
    width = _parse_flexible_numeric_param(d, stroke_el, "stroke-width")
    opacity = _parse_flexible_param(d, stroke_el, "stroke-opacity")
    dasharray = d.get_param(stroke_el, "stroke-dasharray")
    linejoin = d.get_param(stroke_el, "stroke-linejoin")
    linecap = d.get_param(stroke_el, "stroke-linecap")
    if color is not None:
        result["color"] = color if isinstance(color, dict) else parse_color(color)
    if width is not None:
        result["width"] = width if isinstance(width, dict) else parse_unit_value(width)
    if opacity is not None:
        result["opacity"] = (
            opacity if isinstance(opacity, dict) else parse_opacity(opacity)
        )
    if dasharray is not None:
        result["dashPattern"] = [int(float(p)) for p in dasharray.split()]
    if linejoin is not None:
        result["join"] = _validated_enum(
            linejoin, "stroke-linejoin", {"miter", "round", "bevel"}
        )
    if linecap is not None:
        result["cap"] = _validated_enum(
            linecap, "stroke-linecap", {"butt", "round", "square"}
        )
    return result


_UNSUPPORTED_RASTER_CHILDREN = (
    "OverlapBehavior",
    "ContrastEnhancement",
    "ImageOutline",
)


def _parse_selected_channel(d: SldDialect, channel_el: etree._Element) -> dict:
    if d.find(channel_el, "ContrastEnhancement") is not None:
        raise NotImplementedError(
            "se:SelectedChannelType/se:ContrastEnhancement has no "
            "CartoSym mapping in this codec's scope"
        )
    name_el = d.find(channel_el, "SourceChannelName")
    if name_el is None or not (name_el.text and name_el.text.strip()):
        raise NotImplementedError(
            "se:SourceChannelName is required and must have text content"
        )
    return {"property": name_el.text.strip()}


def _parse_channel_selection(d: SldDialect, cs_el: etree._Element) -> dict:
    red = d.find(cs_el, "RedChannel")
    green = d.find(cs_el, "GreenChannel")
    blue = d.find(cs_el, "BlueChannel")
    gray = d.find(cs_el, "GrayChannel")
    if red is not None and green is not None and blue is not None:
        return {
            "colorChannels": [
                _parse_selected_channel(d, red),
                _parse_selected_channel(d, green),
                _parse_selected_channel(d, blue),
            ]
        }
    if gray is not None:
        return {"singleChannel": _parse_selected_channel(d, gray)}
    raise NotImplementedError(
        "se:ChannelSelection without a full RGB triple or a GrayChannel is "
        "not supported"
    )


def _parse_color_map_entries(d: SldDialect, cm_el: etree._Element) -> list:
    """Parse the SLD 1.0.0 ``<ColorMap><ColorMapEntry/></ColorMap>`` form.

    ``<ColorMapEntry color quantity [label]/>`` maps 1:1 to a
    ``[threshold, colour, label?]`` model entry. A ``type`` other than the
    default ``ramp`` (``intervals`` / ``values``) or a per-entry
    ``opacity`` has no CartoSym ``colorMap`` representation and raises.
    """
    map_type = cm_el.get("type")
    if map_type is not None and map_type != "ramp":
        raise NotImplementedError(
            f"<ColorMap type={map_type!r}> has no CartoSym colorMap mapping "
            "(only the default 'ramp' form is supported)"
        )
    entries = d.findall(cm_el, "ColorMapEntry")
    if not entries:
        raise NotImplementedError("<ColorMap> without any <ColorMapEntry>")
    pairs: list = []
    for entry in entries:
        if entry.get("opacity") is not None:
            raise NotImplementedError(
                "<ColorMapEntry opacity=...> has no CartoSym colorMap mapping"
            )
        color = entry.get("color")
        quantity = entry.get("quantity")
        if color is None or quantity is None:
            raise NotImplementedError(
                "<ColorMapEntry> must carry both color and quantity"
            )
        pair: list = [parse_number(quantity), parse_color(color)]
        label = entry.get("label")
        if label is not None:
            pair.append(label)
        pairs.append(pair)
    return pairs


def _parse_color_map(d: SldDialect, cm_el: etree._Element) -> list:
    if d.raster_colormap == "entry":
        return _parse_color_map_entries(d, cm_el)
    categorize_el = d.find(cm_el, "Categorize")
    if categorize_el is None:
        raise NotImplementedError(
            "se:ColorMap without se:Categorize (se:Interpolate, or the "
            "SLD 1.0.0-only se:ColorMapEntry form) is out of scope for "
            "this codec"
        )
    children = [
        c
        for c in categorize_el
        if isinstance(c.tag, str) and local_name(c) != "LookupValue"
    ]
    if not children or local_name(children[0]) != "Value":
        raise NotImplementedError(
            "se:Categorize must start with a se:Value (the below-first-"
            "threshold color)"
        )
    values = [c.text for c in children if local_name(c) == "Value"]
    thresholds = [c.text for c in children if local_name(c) == "Threshold"]
    if len(thresholds) != len(values) - 1:
        raise NotImplementedError(
            "se:Categorize Value/Threshold count mismatch (expected "
            "exactly one more se:Value than se:Threshold)"
        )
    colors = [parse_color(v) for v in values]
    numeric_thresholds = [parse_number(t) for t in thresholds]

    # colorMap[0][0] has no XML representation
    # — synthesized as a duplicate of the first real threshold, a
    # deterministic, round-trip-stable, but explicitly arbitrary
    # convention.
    first_threshold = numeric_thresholds[0] if numeric_thresholds else 0
    pairs = [[first_threshold, colors[0]]]
    pairs.extend([t, c] for t, c in zip(numeric_thresholds, colors[1:]))
    return pairs


def _parse_shaded_relief(d: SldDialect, sr_el: etree._Element) -> dict:
    if d.find(sr_el, "BrightnessOnly") is not None:
        raise NotImplementedError(
            "se:ShadedRelief/se:BrightnessOnly has no CartoSym HillShading "
            "mapping in this codec's scope"
        )
    result: dict = {}
    factor_text = element_text(d.find(sr_el, "ReliefFactor"))
    if factor_text and factor_text.strip():
        result["factor"] = parse_number(factor_text)
    return result


def _parse_raster_symbolizer(d: SldDialect, el: etree._Element) -> dict:
    for tag in _UNSUPPORTED_RASTER_CHILDREN:
        if d.find(el, tag) is not None:
            raise NotImplementedError(
                f"se:RasterSymbolizer/se:{tag} has no CartoSym mapping in "
                "this codec's scope"
            )
    result: dict = {}
    opacity_text = element_text(d.find(el, "Opacity"))
    if opacity_text and opacity_text.strip():
        result["opacity"] = parse_opacity(opacity_text.strip())
    cs_el = d.find(el, "ChannelSelection")
    if cs_el is not None:
        result.update(_parse_channel_selection(d, cs_el))
    cm_el = d.find(el, "ColorMap")
    if cm_el is not None:
        result["colorMap"] = _parse_color_map(d, cm_el)
    sr_el = d.find(el, "ShadedRelief")
    if sr_el is not None:
        result["hillShading"] = _parse_shaded_relief(d, sr_el)
    return result


def _parse_point_symbolizer(d: SldDialect, ps_el: etree._Element) -> dict:
    graphic_el = d.find(ps_el, "Graphic")
    if graphic_el is None:
        raise NotImplementedError(
            "se:PointSymbolizer without se:Graphic is not supported"
        )
    mark_el = d.find(graphic_el, "Mark")
    if mark_el is not None:
        result = _parse_mark(d, mark_el, graphic_el)
    else:
        ext_el = d.find(graphic_el, "ExternalGraphic")
        if ext_el is None:
            raise NotImplementedError(
                "se:Graphic without se:Mark or se:ExternalGraphic is not " "supported"
            )
        result = _parse_external_graphic(d, ext_el, graphic_el)

    # se:Rotation is a direct se:Graphic child in both dialects (unlike
    # se:Displacement/se:AnchorPoint, it's not SE 1.1.0-only), so it's
    # parsed once here for both the Mark and ExternalGraphic branches.
    rotation_text = element_text(d.find(graphic_el, "Rotation"))
    if rotation_text is not None:
        result["transform"] = {"orientation": parse_angle(rotation_text)}
    return result


def _px(value: float) -> dict:
    """Format a plain pixel length as CartoSym's ``{"px": v}`` unit dict.

    ``parse_number`` (used for ``se:Size``) already returns a plain
    ``int`` for whole numbers despite its ``float`` type hint — handle
    that directly rather than calling ``.is_integer()`` on it, which
    only exists on ``int`` from Python 3.12 onward (this codebase
    supports 3.10+).
    """
    if isinstance(value, int):
        return {"px": value}
    return {"px": int(value) if value.is_integer() else value}


def _parse_mark(
    d: SldDialect, mark_el: etree._Element, graphic_el: etree._Element
) -> dict:
    wkn = element_text(d.find(mark_el, "WellKnownName"))
    if wkn not in ("circle", "square"):
        raise NotImplementedError(
            f"se:Mark/se:WellKnownName {wkn!r} is out of scope for this "
            "codec (only 'circle'/'square' are supported)"
        )

    # se:Mark wellKnownName="circle"/"square" — a filled, outlined mark —
    # is a 2-shapes Circle/Rectangle (ClosedShape.fill + abstractShape.
    # outline + radius, or width+height), not a 1-core Dot (which is
    # stroke-only by design and could not carry the fill and the
    # contrasting outline independently).
    result: dict = {
        "type": "Circle" if wkn == "circle" else "Rectangle",
        "position": _graphic_displacement(d, graphic_el),
    }

    fill_el = d.find(mark_el, "Fill")
    if fill_el is not None:
        fill: dict = {}
        color = d.get_param(fill_el, "fill")
        if color is not None:
            fill["color"] = parse_color(color)
        fill_opacity = d.get_param(fill_el, "fill-opacity")
        if fill_opacity is not None:
            fill["opacity"] = parse_opacity(fill_opacity)
        if fill:
            result["fill"] = fill

    stroke_el = d.find(mark_el, "Stroke")
    if stroke_el is not None:
        _reject_unknown_params(
            d,
            stroke_el,
            {"stroke", "stroke-width", "stroke-opacity"},
            "se:Mark/se:Stroke",
        )
        outline: dict = {}
        stroke_color = d.get_param(stroke_el, "stroke")
        if stroke_color is not None:
            outline["color"] = parse_color(stroke_color)
        stroke_width = _parse_flexible_numeric_param(d, stroke_el, "stroke-width")
        if stroke_width is not None:
            outline["thickness"] = (
                stroke_width
                if isinstance(stroke_width, dict)
                else parse_unit_value(stroke_width)
            )
        stroke_opacity = d.get_param(stroke_el, "stroke-opacity")
        if stroke_opacity is not None:
            outline["opacity"] = parse_opacity(stroke_opacity)
        if outline:
            result["outline"] = outline

    size_text = element_text(d.find(graphic_el, "Size"))
    if size_text is not None:
        size = parse_number(size_text)
        if size is not None:
            if wkn == "circle":
                # se:Size is a diameter; CartoSym radius is a radius.
                result["radius"] = _px(size / 2)
            else:
                # se:Size is the square's side length — width == height,
                # se:Mark has no separate width/height of its own.
                side = _px(size)
                result["width"] = side
                result["height"] = side

    opacity_text = element_text(d.find(graphic_el, "Opacity"))
    if opacity_text and opacity_text.strip():
        result["opacity"] = parse_opacity(opacity_text.strip())
    return result


def _graphic_displacement(d: SldDialect, graphic_el: etree._Element) -> dict:
    """Return the ``{x, y}`` offset from a point ``Graphic``'s ``se:Displacement``.

    Defaults to ``{x: 0, y: 0}`` (no offset). SLD 1.0.0 never has this
    child, so this is a no-op there.
    """
    disp_el = d.find(graphic_el, "Displacement")
    if disp_el is None:
        return {"x": 0, "y": 0}
    return {
        "x": _parsed_axis_or_zero(d.find(disp_el, "DisplacementX")),
        "y": _parsed_axis_or_zero(d.find(disp_el, "DisplacementY")),
    }


def _parse_external_graphic(
    d: SldDialect, ext_el: etree._Element, graphic_el: etree._Element
) -> dict:
    online_resource_el = d.find(ext_el, "OnlineResource")
    if online_resource_el is None:
        raise NotImplementedError(
            "se:ExternalGraphic without se:OnlineResource is not supported"
        )
    href = online_resource_el.get(f"{XLINK}href")
    if not href:
        raise NotImplementedError("se:OnlineResource must have a non-empty xlink:href")

    result: dict = {
        "type": "Image",
        "image": {"uri": href},
        "position": _graphic_displacement(d, graphic_el),
    }
    format_text = element_text(d.find(ext_el, "Format"))
    if format_text and format_text.strip():
        result["image"]["type"] = format_text.strip()

    anchor_el = d.find(graphic_el, "AnchorPoint")
    if anchor_el is not None:
        ax_el = d.find(anchor_el, "AnchorPointX")
        ay_el = d.find(anchor_el, "AnchorPointY")
        fx = _parsed_number_or(ax_el, 0.5)
        fy = _parsed_number_or(ay_el, 0.5)
        result["hotSpot"] = [
            {"pc": round(fx * 100)},
            {"pc": round(fy * 100)},
        ]
    return result


def _parsed_px_or_zero(el: etree._Element | None) -> float:
    text = element_text(el)
    if text is None:
        return 0
    parsed = parse_unit_value(text)
    return parsed["px"] if parsed is not None else 0


def _parsed_axis_or_zero(el: etree._Element | None) -> Any:
    """Parse one ``se:DisplacementX/Y`` (or ``AnchorPointX/Y``) element.

    A plain px-unit number (default ``0`` if absent, matching
    :func:`_parsed_px_or_zero`), or a ``PropertyRef``/``ArithmeticExpression``
    dict if its sole child is ``ogc:PropertyName``/``ogc:Function`` — the
    inverse of :func:`_write_numeric_element`.
    """
    if el is None:
        return 0
    children = [c for c in el if isinstance(c.tag, str)]
    if len(children) == 1:
        tag = local_name(children[0])
        if tag == "PropertyName":
            return {"property": element_text(children[0])}
        if tag == "Function":
            return _parse_arithmetic_function(children[0])
    return _parsed_px_or_zero(el)


def _parsed_number_or(el: etree._Element | None, default: float) -> float:
    text = element_text(el)
    if text is None:
        return default
    parsed = parse_number(text)
    return parsed if parsed is not None else default


def _parse_halo(d: SldDialect, halo_el: etree._Element | None) -> dict:
    """Map ``se:Halo`` (``Radius`` + ``Fill``) to a CartoSym ``font.outline`` dict.

    CartoSym Part-1 "font outlines": ``{size, opacity, color}``. An empty
    ``se:Halo`` yields an empty dict (the caller drops it).
    """
    if halo_el is None:
        return {}
    outline: dict = {}
    radius_text = element_text(d.find(halo_el, "Radius"))
    if radius_text and radius_text.strip():
        outline["size"] = parse_number(radius_text)
    fill_el = d.find(halo_el, "Fill")
    if fill_el is not None:
        opacity = d.get_param(fill_el, "fill-opacity")
        if opacity is not None:
            outline["opacity"] = parse_opacity(opacity)
        color = d.get_param(fill_el, "fill")
        if color is not None:
            outline["color"] = parse_color(color)
    return outline


def _parse_text_symbolizer(d: SldDialect, ts_el: etree._Element) -> dict:
    label_el = d.find(ts_el, "Label")
    if label_el is None:
        raise NotImplementedError("se:TextSymbolizer without se:Label is not supported")
    prop_el = label_el.find(f"{OGC}PropertyName")
    literal_el = label_el.find(f"{OGC}Literal")
    if prop_el is not None:
        text: Any = {"property": prop_el.text}
    elif literal_el is not None and literal_el.text is not None:
        # se:Label is mixed content; some producers wrap plain text in
        # <ogc:Literal> rather than as a bare text node.
        text = literal_el.text.strip()
    elif label_el.text and label_el.text.strip():
        text = label_el.text.strip()
    else:
        raise NotImplementedError(
            "se:Label with neither literal text, ogc:Literal, nor "
            "ogc:PropertyName is not supported"
        )

    result: dict = {"type": "Text", "text": text, "position": {"x": 0, "y": 0}}

    font_el = d.find(ts_el, "Font")
    font: dict = {}
    if font_el is not None:
        _reject_unknown_params(
            d,
            font_el,
            {"font-family", "font-size", "font-weight", "font-style"},
            "Font",
        )
        face = d.get_param(font_el, "font-family")
        size = d.get_param(font_el, "font-size")
        weight = d.get_param(font_el, "font-weight")
        style = d.get_param(font_el, "font-style")
        if face is not None:
            font["face"] = face
        if size is not None:
            # A bare number, per the schema's font.size (numericExpression,
            # not unitValue) — same as its outline["size"] sibling below,
            # not parse_unit_value's {"px": N} dict.
            font["size"] = parse_number(size)
        if weight is not None:
            font["bold"] = weight == "bold"
        if style is not None:
            font["italic"] = style == "italic"

    fill_el = d.find(ts_el, "Fill")
    if fill_el is not None:
        color = d.get_param(fill_el, "fill")
        opacity = d.get_param(fill_el, "fill-opacity")
        if color is not None:
            font["color"] = parse_color(color)
        if opacity is not None:
            font["opacity"] = parse_opacity(opacity)

    outline = _parse_halo(d, d.find(ts_el, "Halo"))
    if outline:
        font["outline"] = outline

    if font:
        result["font"] = font

    placement_el = d.find(ts_el, "LabelPlacement")
    if placement_el is not None:
        point_placement_el = d.find(placement_el, "PointPlacement")
        if point_placement_el is None:
            raise NotImplementedError(
                "se:LabelPlacement/se:LinePlacement is out of scope for this codec"
            )
        anchor_el = d.find(point_placement_el, "AnchorPoint")
        if anchor_el is not None:
            ax = d.find(anchor_el, "AnchorPointX")
            ay = d.find(anchor_el, "AnchorPointY")
            result["alignment"] = [
                _ANCHOR_X_TO_H.get(ax.text if ax is not None else "", "center"),
                _ANCHOR_Y_TO_V.get(ay.text if ay is not None else "", "middle"),
            ]
        disp_el = d.find(point_placement_el, "Displacement")
        if disp_el is not None:
            dx = d.find(disp_el, "DisplacementX")
            dy = d.find(disp_el, "DisplacementY")
            result["position"] = {
                "x": _parsed_axis_or_zero(dx),
                "y": _parsed_axis_or_zero(dy),
            }

    return result
