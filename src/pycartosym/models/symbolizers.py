"""Symbolizer models for CartoSym.

Based on the JSON Schema definitions for symbolizer, fill, stroke, marker, label, etc.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from ..cql2.model import BoolExpression, NumericExpression
from .base import AlterMixin, BaseCartoSymModel, CommentMixin
from .types import (
    FlexibleAngle,
    FlexibleColor,
    FlexibleNumber,
    FlexibleOpacity,
    FlexibleSize,
    UnitType,
    UnitValue,
)
from .value_expressions import PropertyRef

# A vendor-extension property on a symbolizer, per the conceptual model's
# generic vendor-extension mechanism: a symbolizer property named
# ``vendor.<vendorName>.<propertyName>``, any datatype, that consumers
# ignore when they do not understand it. Used to carry e.g. GeoServer
# ``<VendorOption>`` values losslessly through CS-JSON.
_VENDOR_KEY_RE = re.compile(r"^vendor\.[A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+$")


_UNIT_NAMES = {u.value for u in UnitType}


def parse_flexible_unit_value(v):
    """Coerce a ``{unit: value}`` dict into a :class:`UnitValue`.

    Only for an actual unit key (``{"px": 2.0}``) — a one-key expression
    dict like ``{"sysId": "viz.sd"}`` or ``{"property": "x"}`` has the same
    shape and must be left alone, not misread as value=``"viz.sd"``,
    unit=``"sysId"``.
    """
    if isinstance(v, dict) and len(v) == 1:
        unit, value = next(iter(v.items()))
        if unit in _UNIT_NAMES:
            return UnitValue(value=value, unit=unit)
    return v


def _validate_flexible_unit(cls, v):
    """Coerce a ``{unit: value}`` dict on a unit-typed field before validation.

    Shared body for the several ``field_validator``s below that only ever
    delegated to :func:`parse_flexible_unit_value` — assigned per-class as
    ``field_validator(<field names>, mode="before")(_validate_flexible_unit)``
    since the field names differ per class but the logic doesn't.
    """
    return parse_flexible_unit_value(v)


def _coerce_numeric_str(v: str):
    """Convert a numeric string to int/float, leaving it as-is if it isn't one."""
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _coerce_axis_value(v: str):
    """Coerce one ``UnitPoint`` coordinate token: a number or a property ref.

    A bare property-name identifier (e.g. ``sd`` in ``position: sd 3``)
    becomes a ``PropertyRef`` dict — arithmetic/system-identifier
    coordinates are out of scope here (see
    ``models/value_expressions.py``'s ``PropertyRef``): the CSCSS grammar
    treats a ``UnitPoint``'s two coordinates as one opaque two-token text
    blob rather than two independent expression trees, so there is no
    per-axis ANTLR context to parse a full sub-expression from, unlike a
    scalar property like ``stroke.width``.
    """
    numeric = _coerce_numeric_str(v)
    if not isinstance(numeric, str):
        return numeric
    if _IDENTIFIER_RE.match(v):
        return {"property": v}
    return v


class Fill(BaseCartoSymModel, AlterMixin):
    """Fill symbolizer for polygons and areas.

    Based on the 'fill' definition in the JSON schema.
    Can be either an expression reference or a fill object.
    """

    color: FlexibleColor | None = Field(None, description="Fill color")
    opacity: FlexibleOpacity | None = Field(None, description="Fill opacity (0.0-1.0)")

    # Pattern fills
    pattern: Graphic | None = Field(None, description="Fill pattern graphic")
    hatch: Hatch | None = Field(None, description="Hatch pattern")
    dotpattern: DotPattern | None = Field(None, description="Dot pattern")
    stipple: Stipple | None = Field(None, description="Stipple pattern")


class Hatch(BaseCartoSymModel, AlterMixin):
    """Hatch pattern for fills."""

    # FlexibleSize (not plain UnitValue | str | float) so a numeric
    # expression can round-trip through CS-JSON's numericExpression, per
    # OGC issue #115 — same rationale as Stroke.width.
    width: FlexibleSize | None = Field(None, description="Hatch line width")
    angle: FlexibleAngle | None = Field(None, description="Hatch angle")
    distance: FlexibleSize | None = Field(
        None, description="Distance between hatch lines"
    )

    validate_unit_fields = field_validator("width", "distance", mode="before")(
        _validate_flexible_unit
    )


class DotPattern(BaseCartoSymModel, AlterMixin):
    """Dot pattern for fills."""

    distance: FlexibleSize | None = Field(None, description="Distance between dots")

    validate_distance = field_validator("distance", mode="before")(
        _validate_flexible_unit
    )


class Stipple(BaseCartoSymModel, AlterMixin):
    """Stipple pattern for fills."""

    ratio: Any | None = Field(
        None, description="Stipple ratio (temporary - will be numericExpression)"
    )


class StrokeStyling(BaseCartoSymModel, AlterMixin):
    """Basic stroke styling properties."""

    color: FlexibleColor | None = Field(None, description="Stroke color")
    opacity: FlexibleOpacity | None = Field(
        None, description="Stroke opacity (0.0-1.0)"
    )
    width: UnitValue | str | float | None = Field(None, description="Stroke width")

    validate_width = field_validator("width", mode="before")(_validate_flexible_unit)


class Stroke(BaseCartoSymModel, AlterMixin):
    """Stroke symbolizer for lines and outlines.

    Based on the 'stroke' definition in the JSON schema.
    """

    # Basic stroke properties
    color: FlexibleColor | None = Field(None, description="Stroke color")
    opacity: FlexibleOpacity | None = Field(
        None, description="Stroke opacity (0.0-1.0)"
    )
    # FlexibleSize (not the plain UnitValue | str | float of StrokeStyling's
    # own width) so a numeric expression — e.g. {"op": "/", "args":
    # [{"sysId": "viz.sd"}, 1000]} for stroke.width: viz.sd / 1000 — can
    # round-trip through CS-JSON's numericExpression, per OGC issue #115.
    width: FlexibleSize | None = Field(None, description="Stroke width")

    # Extended stroke properties
    casing: StrokeStyling | None = Field(None, description="Stroke casing")
    center_line: StrokeStyling | None = Field(
        None, alias="centerLine", description="Center line styling"
    )
    dash_pattern: list[int] | dict[str, int] | None = Field(
        None,
        alias="dashPattern",
        description=(
            "Dash pattern: array of integers, or an indexed cascade "
            "override {index, value}"
        ),
    )
    pattern: dict[str, Any] | None = Field(
        None, description="Stroke pattern graphic (temporary)"
    )

    # Part 2 ("shapes") extension: line ends/corners — { butt, round,
    # square } / { miter, round, bevel } respectively.
    cap: str | None = Field(None, description="Stroke line cap")
    join: str | None = Field(None, description="Stroke line join")

    validate_width = field_validator("width", mode="before")(_validate_flexible_unit)


class Marker(BaseCartoSymModel):
    """Marker symbolizer for points.

    Based on the 'marker' definition (multiGraphic) in the JSON schema.
    """

    # Enhanced with proper structure
    alter: bool | None = Field(None, description="Alter behavior flag")
    position: UnitPoint | None = Field(None, description="Marker position")
    opacity: FlexibleOpacity | None = Field(None, description="Marker opacity")
    elements: Any | None = Field(
        None,
        description=(
            "Graphic elements in marker (list) or indexed override " "{index, value}"
        ),
    )

    @field_validator("elements", mode="before")
    def ensure_elements_list(cls, v):
        """Normalise ``elements`` to a list, preserving an indexed override dict."""
        # Preserve indexed override form {"index": N, "value": graphic} as-is
        if isinstance(v, dict) and "index" in v and "value" in v:
            return v
        # Accept dicts like {"value": ...} without index and convert to list
        if isinstance(v, dict) and "value" in v:
            return [v["value"]]
        if isinstance(v, dict):
            # If dict is a single graphic, wrap in list
            return [v]
        if not isinstance(v, list) and v is not None:
            return [v]
        return v


class Label(BaseCartoSymModel):
    """Label symbolizer for text labels.

    Based on the 'label' definition in the JSON schema.
    Extends multiGraphic with label placement.
    """

    # Enhanced with proper structure
    alter: bool | None = Field(None, description="Alter behavior flag")
    position: UnitPoint | None = Field(None, description="Label position")
    opacity: FlexibleOpacity | None = Field(None, description="Label opacity")
    elements: list[Graphic] | None = Field(
        None, description="Graphic elements in label"
    )
    placement: LabelPlacement | None = Field(
        None, description="Label placement configuration"
    )

    @field_validator("elements", mode="before")
    def ensure_elements_list(cls, v):
        """Normalise ``elements`` to a list of graphic dicts."""
        if isinstance(v, dict) and "value" in v:
            return [v["value"]]
        if isinstance(v, dict):
            return [v]
        if not isinstance(v, list) and v is not None:
            return [v]
        return v


# Graphic system classes
class UnitPoint(BaseCartoSymModel):
    """Point with unit values: [x, y], {x: value, y: value}, or "x y"."""

    x: UnitValue | str | float | PropertyRef
    y: UnitValue | str | float | PropertyRef

    @model_validator(mode="before")
    @classmethod
    def parse_unit_point(cls, v):
        """Accept a bare ``"x y"`` string or ``[x, y]`` list as well as ``{x, y}``."""
        # Accept a bare "x y" string (as written by the CSCSS writer, e.g.
        # for `position`) or a [x, y] list, in addition to the normal
        # {x: ..., y: ...} dict form.
        if isinstance(v, str):
            parts = v.strip().split()
            if len(parts) == 2:
                return {
                    "x": _coerce_axis_value(parts[0]),
                    "y": _coerce_axis_value(parts[1]),
                }
        elif isinstance(v, (list, tuple)) and len(v) == 2:
            return {"x": v[0], "y": v[1]}
        return v


class Resource(BaseCartoSymModel):
    """Resource reference (file, URL, etc.)."""

    uri: str | None = Field(None, description="Resource URI")
    path: str | None = Field(None, description="File path")
    id: str | None = Field(None, description="Resource ID")
    type: str | None = Field(None, description="MIME type")
    ext: str | None = Field(None, description="File extension")
    sprite: str | None = Field(None, description="Icon atlas sprite id")


class Font(BaseCartoSymModel):
    """Font specification."""

    face: str | None = Field(None, description="Font family name")
    size: FlexibleSize | None = Field(None, description="Font size")
    bold: bool | None = Field(None, description="Bold weight")
    italic: bool | None = Field(None, description="Italic style")
    underline: bool | None = Field(None, description="Underline decoration")


class FontOutline(BaseCartoSymModel):
    """Font outline styling."""

    color: FlexibleColor | None = Field(None, description="Outline color")
    width: UnitValue | str | float | None = Field(None, description="Outline width")


class TextAlignment(BaseCartoSymModel):
    """Text alignment configuration."""

    h_alignment: str | None = Field(
        None,
        alias="hAlignment",
        description="Horizontal alignment: left, center, right",
    )
    v_alignment: str | None = Field(
        None, alias="vAlignment", description="Vertical alignment: top, middle, bottom"
    )
    alter: bool | None = Field(None, description="Alter behavior flag")


class LabelPlacement(BaseCartoSymModel):
    """Label placement configuration."""

    placement_type: str | None = Field(
        None, alias="type", description="Placement algorithm type"
    )
    # Additional placement properties would go here
    priority: FlexibleNumber | None = Field(None, description="Label priority")
    min_spacing: FlexibleSize | None = Field(
        None, alias="minSpacing", description="Minimum spacing"
    )
    max_spacing: FlexibleSize | None = Field(
        None, alias="maxSpacing", description="Maximum spacing"
    )

    validate_spacing_fields = field_validator(
        "min_spacing", "max_spacing", mode="before"
    )(_validate_flexible_unit)


# Abstract base for graphics
class Transform2D(BaseCartoSymModel, AlterMixin):
    """2D graphic transform (Part 2 ``transform2D``).

    Only ``orientation`` is wired into any codec today (SLD/SE
    ``se:Rotation``, issue #89). ``scaling`` is accepted for schema
    fidelity but left untyped: Part 2's own ``scale2D`` definition isn't
    even vendored in this project's schema subset, so there's nothing
    more precise to model yet.
    """

    orientation: FlexibleAngle | None = Field(None, description="Rotation angle")
    scaling: Any | None = Field(None, description="2D scale factor")
    translation: UnitPoint | None = Field(None, description="2D translation offset")


class AbstractGraphic(BaseCartoSymModel, AlterMixin):
    """Base class for all graphic elements."""

    position: UnitPoint | None = Field(None, description="Graphic position")
    opacity: FlexibleOpacity | None = Field(None, description="Graphic opacity")
    transform: Transform2D | None = Field(
        None, description="2D transform (Part 2 abstractGraphic extension)"
    )

    @field_validator("position", mode="before")
    def validate_position(cls, v):
        """Accept a two-item ``[x, y]`` list for ``position``."""
        if isinstance(v, list) and len(v) == 2:
            return UnitPoint(x=v[0], y=v[1])
        return v


class Graphic(AbstractGraphic):
    """Base graphic element - can be Image, Text, Shape, etc."""

    type: str | None = Field(None, description="Graphic type: Image, Text, Shape, etc.")
    model_config = ConfigDict(extra="allow")


class ImageGraphic(Graphic):
    """Image graphic element."""

    type: str = Field("Image", description="Graphic type")
    image: Resource = Field(..., description="Image resource")
    hot_spot: UnitPoint | None = Field(
        None, alias="hotSpot", description="Hot spot position"
    )
    tint: FlexibleColor | None = Field(None, description="Tint color")
    black_tint: FlexibleColor | None = Field(
        None, alias="blackTint", description="Black tint color"
    )
    alpha_threshold: FlexibleOpacity | None = Field(
        None, alias="alphaThreshold", description="Alpha threshold"
    )
    model_config = ConfigDict(extra="allow")


class TextGraphic(Graphic):
    """Text graphic element."""

    type: str = Field("Text", description="Graphic type")
    text: str | Any = Field(
        ..., description="Text content or expression"
    )  # Should be characterExpression
    font: Font | None = Field(None, description="Font specification")
    alignment: TextAlignment | None = Field(None, description="Text alignment")


# Shape classes — the Part 2 ("shapes") extension of the conceptual model.
class ShapeOutline(BaseCartoSymModel, AlterMixin):
    """Outline of a shape graphic (Part 2 ``shapeOutline``).

    Distinct from :class:`Stroke`: a shape outline carries only
    ``thickness`` / ``opacity`` / ``color`` — no casing, centre line,
    dash pattern or pattern graphic.
    """

    thickness: FlexibleSize | None = Field(None, description="Outline thickness")
    opacity: FlexibleOpacity | None = Field(
        None, description="Outline opacity (0.0-1.0)"
    )
    color: FlexibleColor | None = Field(None, description="Outline color")

    validate_thickness = field_validator("thickness", mode="before")(
        _validate_flexible_unit
    )


class ShapeGraphic(Graphic):
    """Base class for shape graphics (Part 2 ``abstractShape``)."""

    type: str = Field("Shape", description="Graphic type")
    outline: ShapeOutline | None = Field(None, description="Shape outline")


class ClosedShape(ShapeGraphic):
    """A shape graphic that encloses an area, hence can be filled.

    Part 2 ``closedShape`` — adds ``fill`` to :class:`ShapeGraphic`.
    """

    fill: Fill | None = Field(None, description="Shape fill")


class CircleGraphic(ClosedShape):
    """Circle shape graphic (Part 2 ``circle``).

    A filled, outlined, sized circle: ``fill`` (from ``ClosedShape``),
    ``outline`` (from ``ShapeGraphic``) and ``radius``.
    """

    center: UnitPoint | None = Field(None, description="Circle centre")
    radius: FlexibleSize | None = Field(None, description="Circle radius")


class RectangleGraphic(ClosedShape):
    """Rectangle shape graphic."""

    width: FlexibleSize = Field(..., description="Rectangle width")
    height: FlexibleSize = Field(..., description="Rectangle height")

    validate_size_fields = field_validator("width", "height", mode="before")(
        _validate_flexible_unit
    )


class ArcGraphic(ShapeGraphic):
    """Open arc shape graphic (Part 2 ``arc``, from ``abstractArc``).

    Stroke-only (``outline`` from :class:`ShapeGraphic`, no fill) — an arc is
    an open curve, not an enclosed area.
    """

    type: str = Field("Arc", description="Graphic type")
    center: UnitPoint | None = Field(None, description="Arc centre")
    radius: FlexibleSize | None = Field(None, description="Arc radius")
    start_angle: FlexibleAngle | None = Field(
        None, alias="startAngle", description="Arc start angle"
    )
    delta_angle: FlexibleAngle | None = Field(
        None, alias="deltaAngle", description="Arc angular extent"
    )


class SectorArcGraphic(ClosedShape):
    """Pie-slice arc sector shape graphic (Part 2 ``sectorArc``).

    Same ``abstractArc`` geometry as :class:`ArcGraphic`, but a closed shape
    (``fill`` from :class:`ClosedShape`) — bounded by the two radii and the
    arc, unlike :class:`ChordArcGraphic`'s straight chord.
    """

    type: str = Field("SectorArc", description="Graphic type")
    center: UnitPoint | None = Field(None, description="Arc centre")
    radius: FlexibleSize | None = Field(None, description="Arc radius")
    start_angle: FlexibleAngle | None = Field(
        None, alias="startAngle", description="Arc start angle"
    )
    delta_angle: FlexibleAngle | None = Field(
        None, alias="deltaAngle", description="Arc angular extent"
    )


class ChordArcGraphic(ClosedShape):
    """Arc chord segment shape graphic (Part 2 ``chordArc``).

    Same ``abstractArc`` geometry as :class:`ArcGraphic`, but a closed shape
    (``fill`` from :class:`ClosedShape`) — bounded by the straight chord
    between the two endpoints, unlike :class:`SectorArcGraphic`'s two radii.
    """

    type: str = Field("ChordArc", description="Graphic type")
    center: UnitPoint | None = Field(None, description="Arc centre")
    radius: FlexibleSize | None = Field(None, description="Arc radius")
    start_angle: FlexibleAngle | None = Field(
        None, alias="startAngle", description="Arc start angle"
    )
    delta_angle: FlexibleAngle | None = Field(
        None, alias="deltaAngle", description="Arc angular extent"
    )


class ColorMap(BaseCartoSymModel):
    """Color mapping for raster/coverage data."""

    # Simplified for now - would contain color ramp definitions
    colors: list[FlexibleColor] | None = Field(None, description="Color ramp")
    values: list[NumericExpression] | None = Field(None, description="Value stops")


class OpacityMap(BaseCartoSymModel):
    """Opacity mapping for raster/coverage data."""

    # Simplified for now - would contain opacity ramp definitions
    opacities: list[FlexibleOpacity] | None = Field(None, description="Opacity ramp")
    values: list[NumericExpression] | None = Field(None, description="Value stops")


class HillShading(BaseCartoSymModel):
    """Hill shading configuration for elevation data."""

    azimuth: FlexibleAngle | None = Field(None, description="Light source azimuth")
    elevation: FlexibleAngle | None = Field(None, description="Light source elevation")
    factor: NumericExpression | None = Field(None, description="Shading factor")


# Enhanced Symbolizer with all JSON schema properties
class SymbolizerEnhanced(BaseCartoSymModel, CommentMixin):
    """Enhanced symbolizer with all properties from JSON schema."""

    # Basic properties
    visibility: BoolExpression | None = Field(None, description="Visibility condition")
    opacity: FlexibleOpacity | None = Field(None, description="Overall opacity")
    z_order: NumericExpression | None = Field(
        None, alias="zOrder", description="Z-order for layering"
    )

    # Vector symbolizers
    fill: Fill | None = Field(None, description="Fill symbolizer")
    stroke: Stroke | None = Field(None, description="Stroke symbolizer")
    marker: Marker | None = Field(None, description="Marker symbolizer")
    label: Label | None = Field(None, description="Label symbolizer")

    # Raster/coverage symbolizers
    color_channels: FlexibleColor | None = Field(
        None, alias="colorChannels", description="RGB color channels"
    )
    alpha_channel: FlexibleOpacity | None = Field(
        None, alias="alphaChannel", description="Alpha channel"
    )
    single_channel: FlexibleOpacity | None = Field(
        None, alias="singleChannel", description="Single channel value"
    )
    color_map: ColorMap | None = Field(
        None, alias="colorMap", description="Color mapping"
    )
    opacity_map: OpacityMap | None = Field(
        None, alias="opacityMap", description="Opacity mapping"
    )

    # Elevation symbolizers
    hill_shading: HillShading | None = Field(
        None, alias="hillShading", description="Hill shading"
    )


class Symbolizer(BaseCartoSymModel, CommentMixin):
    """Main symbolizer containing all rendering properties.

    Based on the 'symbolizer' definition in the JSON schema.

    Extra keys are permitted only for vendor extensions — a property named
    ``vendor.<vendorName>.<propertyName>`` (see :data:`_VENDOR_KEY_RE`).
    Any other unknown key is rejected as a likely typo.
    """

    model_config = ConfigDict(extra="allow")

    # Core properties
    visibility: Any | None = Field(
        None, description="Visibility expression (temporary)"
    )
    opacity: Any | None = Field(
        None, description="Opacity value (temporary - will be zeroToOne)"
    )
    z_order: Any | None = Field(
        None,
        alias="zOrder",
        description="Z-order value (temporary - will be numericExpression)",
    )

    # Vector symbolizers
    fill: Fill | None = Field(None, description="Fill symbolizer")
    stroke: Stroke | None = Field(None, description="Stroke symbolizer")
    marker: Marker | None = Field(None, description="Marker symbolizer")
    label: Label | None = Field(None, description="Label symbolizer")

    # Raster symbolizers
    color_channels: Any | None = Field(
        None,
        alias="colorChannels",
        description="Color channels (temporary - will be color0to1)",
    )
    alpha_channel: Any | None = Field(
        None,
        alias="alphaChannel",
        description="Alpha channel (temporary - will be zeroToOne)",
    )
    single_channel: Any | None = Field(
        None,
        alias="singleChannel",
        description="Single channel (temporary - will be zeroToOne)",
    )
    color_map: Any | None = Field(
        None, alias="colorMap", description="Color map (temporary)"
    )
    opacity_map: Any | None = Field(
        None, alias="opacityMap", description="Opacity map (temporary)"
    )
    hill_shading: Any | None = Field(
        None, alias="hillShading", description="Hill shading (temporary)"
    )

    @model_validator(mode="after")
    def _reject_non_vendor_extras(self) -> Symbolizer:
        """Allow only ``vendor.<name>.<prop>`` extension keys as extras."""
        for key in self.__pydantic_extra__ or {}:
            if not _VENDOR_KEY_RE.match(key):
                raise ValueError(
                    f"unknown symbolizer property {key!r}: only vendor "
                    "extensions named 'vendor.<vendorName>.<propertyName>' "
                    "are accepted as extra keys"
                )
        return self


# Enable forward references for nested types
Fill.model_rebuild()
Stroke.model_rebuild()
StrokeStyling.model_rebuild()
Marker.model_rebuild()
Label.model_rebuild()
AbstractGraphic.model_rebuild()
ImageGraphic.model_rebuild()
TextGraphic.model_rebuild()
ShapeGraphic.model_rebuild()
ClosedShape.model_rebuild()
CircleGraphic.model_rebuild()
RectangleGraphic.model_rebuild()
ArcGraphic.model_rebuild()
SectorArcGraphic.model_rebuild()
ChordArcGraphic.model_rebuild()
