"""Alignment and layout expressions."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._expr_arithmetic import NumericExpression
from ._expr_base import Expression


class HAlignment(Expression):
    """Horizontal alignment: left, center, right."""

    value: Literal["left", "center", "right"]


class VAlignment(Expression):
    """Vertical alignment: top, middle, bottom."""

    value: Literal["top", "middle", "bottom"]


class Horizontal(Expression):
    """Horizontal positioning/direction."""

    value: float | str | NumericExpression


class Vertical(Expression):
    """Vertical positioning/direction."""

    value: float | str | NumericExpression


class Dot(Expression):
    """Dot notation access for nested properties."""

    path: list[str] = Field(min_length=2)  # e.g., ['dataLayer', 'type']

    def to_string(self) -> str:
        """Render the member path as a dotted string (e.g. ``dataLayer.type``)."""
        return ".".join(self.path)
