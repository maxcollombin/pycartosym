"""Spatial expressions and predicates (geometry, OGC 21-065r2 spatial clause)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from ._expr_arithmetic import NumericExpression
from ._expr_base import Expression, ExpressionType
from ._expr_boolean import BoolExpression


class SpatialPredicate(BoolExpression):
    """Spatial predicate for geometry-based comparisons.

    OGC CQL2-JSON format: {"op": "s_intersects", "args": [geomA, geomB]}
    Inspired by CQL2ExpCall in ecere/libCartoSym CQL2Expressions.ec.
    """

    op: Literal[
        "s_intersects",
        "s_contains",
        "s_within",
        "s_touches",
        "s_crosses",
        "s_disjoint",
        "s_overlaps",
        "s_equals",
        "s_covers",
        "s_coveredBy",
        # Legacy bare names (accepted on input, normalised to s_ prefix on output)
        "intersects",
        "contains",
        "within",
        "touches",
        "crosses",
        "disjoint",
        "overlaps",
        "equals",
        "covers",
        "coveredBy",
    ]
    args: list[Expression]

    def normalised_op(self) -> str:
        """Return the CQL2-standard s_ prefixed operator name."""
        if self.op.startswith("s_"):
            return self.op
        return f"s_{self.op}"


class SpatialRelatePredicate(BoolExpression):
    """DE-9IM relate predicate: {"op": "s_relate", "args": [geomA, geomB, pattern]}.

    The pattern is a 9-character DE-9IM matrix string (e.g. "T*F**FFF*").
    See models/de9im.py for predicate↔pattern mapping and README for
    a description of the DE-9IM model.
    """

    op: Literal["s_relate"] = "s_relate"
    args: list[Expression] = Field(min_length=2, max_length=2)
    pattern: str = Field(
        ...,
        min_length=9,
        max_length=9,
        description="DE-9IM intersection matrix pattern",
    )

    @field_validator("pattern")
    def _validate_de9im_pattern(cls, v: str) -> str:
        """Reject a ``pattern`` that is not a well-formed DE-9IM pattern.

        Delegates to :func:`pycartosym.models.de9im.is_valid_de9im_pattern`
        so the pattern alphabet (``0 1 2 T F *``) lives in one place.
        """
        from ..models.de9im import is_valid_de9im_pattern

        if not is_valid_de9im_pattern(v):
            raise ValueError(
                f"{v!r} is not a valid DE-9IM pattern "
                "(9 characters, each one of 0 1 2 T F *)"
            )
        return v


class GeometryExpression(Expression):
    """Base class for geometry expressions."""

    type: ExpressionType = (
        ExpressionType.INSTANCE
    )  # Default type for geometry instances


class GeometryBuffer(GeometryExpression):
    """Geometry buffer operation: {"op": "s_buffer", "args": [geometry, distance]}."""

    op: Literal["buffer", "s_buffer"] = "s_buffer"
    args: list[Expression] = Field(min_length=2, max_length=2)  # [geometry, distance]


class GeometryManipulationUnary(GeometryExpression):
    """Unary geometry operations.

    ``{"op": "s_convexHull|s_envelope|centroid|boundary", "args": [geometry]}``
    """

    op: Literal[
        "centroid", "envelope", "convexHull", "boundary", "s_convexHull", "s_envelope"
    ]
    args: list[Expression] = Field(min_length=1, max_length=1)


class GeometryManipulationBinary(GeometryExpression):
    """Binary geometry operations.

    ``{"op": "s_intersection|s_union|s_difference|s_symDifference",
    "args": [geom1, geom2]}``
    """

    op: Literal[
        "union",
        "intersection",
        "difference",
        "symDifference",
        "s_intersection",
        "s_union",
        "s_difference",
        "s_symDifference",
    ]
    args: list[Expression] = Field(min_length=2, max_length=2)


class SpatialInstance(GeometryExpression):
    """Spatial geometry instance with coordinates."""

    geometry_type: Literal[
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
    ]
    coordinates: list[Any]  # Coordinate arrays, structure depends on geometry type
    crs: str | None = Field(None, description="Coordinate Reference System")


class GeometryLiteral(GeometryExpression):
    """Inline geometry literal (WKT / GeoJSON).

    In CQL2-Text this is written as WKT: POINT(1 2), POLYGON((...)), etc.
    In CQL2-JSON this is serialised as a GeoJSON geometry object:
      {"type": "Point", "coordinates": [1, 2]}

    Inspired by CQL2ExpCall::readGeometryFromCQL2() and toCQL2JSON() in
    ecere/libCartoSym CQL2Expressions.ec.
    """

    geom_type: Literal[
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
        "GeometryCollection",
    ]
    coordinates: list[Any] | None = None
    geometries: list[GeometryLiteral] | None = None  # For GeometryCollection
    crs: str | None = None

    def to_geojson(self) -> dict[str, Any]:
        """Serialise as a GeoJSON geometry dict (for CQL2-JSON output)."""
        result: dict[str, Any] = {"type": self.geom_type}
        if self.geom_type == "GeometryCollection" and self.geometries:
            result["geometries"] = [g.to_geojson() for g in self.geometries]
        elif self.coordinates is not None:
            result["coordinates"] = self.coordinates
        return result

    @classmethod
    def from_geojson(cls, data: dict[str, Any]) -> GeometryLiteral:
        """Deserialise from a GeoJSON geometry dict."""
        geom_type = data["type"]
        if geom_type == "GeometryCollection":
            return cls(
                geom_type=geom_type,
                geometries=[cls.from_geojson(g) for g in data.get("geometries", [])],
            )
        return cls(geom_type=geom_type, coordinates=data.get("coordinates"))


class BboxLiteral(GeometryExpression):
    """Bounding box literal.

    CQL2-Text:  BBOX(geom, x1, y1, x2, y2)
    CQL2-JSON:  {"bbox": [x1, y1, x2, y2]}  (4 or 6 values)
    """

    bbox: list[float] = Field(min_length=4, max_length=6)

    def to_cql2_json(self) -> dict[str, Any]:
        """Serialise to a CQL2-JSON ``{"bbox": [...]}`` object."""
        return {"bbox": self.bbox}


class AzimuthElevation(Expression):
    """Azimuth and elevation for directional calculations."""

    azimuth: float | NumericExpression
    elevation: float | NumericExpression
