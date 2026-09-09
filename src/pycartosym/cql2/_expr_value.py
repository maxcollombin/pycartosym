"""Generic value/reference expressions shared across domains.

Property and system references, scalar literals, and the JSON-Schema
generic function-call/conditional containers — small building blocks that
don't belong to any one CQL2 sub-domain (arithmetic, spatial, ...) but are
used by several of them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._expr_base import Expression


# Property and System References
class PropertyRef(Expression):
    """Property reference: {"property": "propertyName"}."""

    property: str


class SystemIdentifier(Expression):
    """System identifier: {"sysId": "identifier"}."""

    sysId: str


# Scalar Expressions
class ScalarExpression(Expression):
    """Base class for scalar expressions."""

    pass


class ScalarLiteral(ScalarExpression):
    """Scalar literal value."""

    value: str | int | float | bool


# Enhanced Function Calls (JSON Schema format)
class FunctionCallJSON(Expression):
    """JSON Schema function call: {"op": "functionName", "args": [...]}."""

    op: str  # Function name
    args: list[Expression] = Field(default_factory=list)


# Enhanced Conditional Expressions (JSON Schema format)
class ConditionalExpressionJSON(Expression):
    """JSON Schema conditional.

    ``{"op": "if", "args": [condition, trueValue, falseValue]}``
    """

    op: Literal["if"] = "if"
    args: list[Expression] = Field(min_length=3, max_length=3)
