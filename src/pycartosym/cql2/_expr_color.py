"""Color and graphics expressions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from ._expr_arithmetic import NumericExpression
from ._expr_base import Expression, ExpressionType


class ColorExpression(Expression):
    """Base class for color expressions."""

    type: ExpressionType = ExpressionType.CONSTANT  # Default type for color constants


class Color0to1(ColorExpression):
    """Color with components in 0-1 range: {"r": 0.5, "g": 0.3, "b": 0.8, "a"?: 1.0}."""

    r: float | int = Field(ge=0.0, le=1.0)
    g: float | int = Field(ge=0.0, le=1.0)
    b: float | int = Field(ge=0.0, le=1.0)
    a: float | int | None = Field(None, ge=0.0, le=1.0)


class ColorComponent0to255(ColorExpression):
    """Color with 0-255 components: {"r": 128, "g": 76, "b": 204, "a"?: 255}."""

    r: int | NumericExpression = Field(ge=0, le=255)
    g: int | NumericExpression = Field(ge=0, le=255)
    b: int | NumericExpression = Field(ge=0, le=255)
    a: int | NumericExpression | None = Field(None, ge=0, le=255)


class HexNumber(ColorExpression):
    """Hexadecimal color: {"hex": "#FF5733"}."""

    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")


class ZeroToOne(NumericExpression):
    """Numeric value constrained to 0-1 range."""

    value: float | NumericExpression = Field(ge=0.0, le=1.0)


class Shape(Expression):
    """Shape definition for graphics."""

    shape_type: Literal["circle", "square", "triangle", "star", "cross", "diamond"]
    size: float | NumericExpression | None = None
    properties: dict[str, Any] | None = None
