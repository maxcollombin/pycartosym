"""Polymorphic expression wrappers and cross-domain type aliases.

``AnyExpressionType``/``IdOrFnExpression`` are convenience unions spanning
every expression domain — the reason this module imports from (almost)
every other ``_expr_*`` module in the package.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from ._expr_arithmetic import ArithmeticExpression, NumericExpression
from ._expr_base import Expression, ExpressionType
from ._expr_boolean import BoolExpression
from ._expr_character import (
    CharacterExpression,
    ConcatenateExpression,
    FormatExpression,
)
from ._expr_color import Color0to1, ColorExpression, HexNumber
from ._expr_comparison import ComparisonPredicate
from ._expr_generic import (
    ArrayExpression,
    BinaryOperationExpression,
    ConditionalExpression,
    ConstantExpression,
    FunctionCallExpression,
    IdentifierExpression,
    InstanceExpression,
    MemberAccessExpression,
    StringExpression,
    UnaryOperationExpression,
)
from ._expr_spatial import (
    BboxLiteral,
    GeometryExpression,
    GeometryLiteral,
    SpatialPredicate,
    SpatialRelatePredicate,
)
from ._expr_temporal import DateInstant, TemporalExpression, TemporalLiteral


class AnyExpressionWrapper(Expression):
    """Wrapper for AnyExpression with proper Pydantic handling.

    This allows storing any expression type polymorphically.
    """

    type: ExpressionType = ExpressionType.IDENTIFIER
    expression: Any = Field(..., description="Wrapped expression of any type")

    def get_expression_type(self) -> str:
        """Get the actual type of the wrapped expression."""
        return type(self.expression).__name__


# 1.3 TypedArray - Arrays typés avec validation


class TypedArray(Expression):
    """Typed array with validation constraints.

    Provides strict validation of array elements with type checking.
    """

    type: ExpressionType = ExpressionType.ARRAY
    element_type: str = Field(..., description="Expected type of array elements")
    elements: list[Any] = Field(default_factory=list, description="Array elements")
    min_length: int | None = Field(None, ge=0, description="Minimum array length")
    max_length: int | None = Field(None, ge=0, description="Maximum array length")

    def validate_elements(self) -> bool:
        """Validate that all elements match the expected type."""
        if not self.elements:
            return True

        for element in self.elements:
            if self.element_type and not isinstance(element, eval(self.element_type)):
                return False
        return True

    def add_element(self, element: Any) -> bool:
        """Add an element with type validation."""
        if self.max_length and len(self.elements) >= self.max_length:
            return False

        if self.element_type and not isinstance(element, eval(self.element_type)):
            return False

        self.elements.append(element)
        return True


# 1.4 IdOrFnExpression - Union identifier/fonction


class IdOrFnExpressionWrapper(Expression):
    """Wrapper for identifier or function call expressions.

    Provides flexible syntax for identifiants vs function calls.
    """

    type: ExpressionType = ExpressionType.IDENTIFIER
    expression: IdentifierExpression | FunctionCallExpression = Field(
        ..., description="Identifier or function call"
    )

    def is_function_call(self) -> bool:
        """Check if this is a function call rather than identifier."""
        return isinstance(self.expression, FunctionCallExpression)

    def get_name(self) -> str:
        """Get the name (identifier name or function name)."""
        if isinstance(self.expression, IdentifierExpression):
            return self.expression.name
        elif isinstance(self.expression, FunctionCallExpression):
            return self.expression.function_name
        return "unknown"


# Define type aliases at the end of the file for proper forward references
AnyExpressionType = (
    # Basic expressions
    IdentifierExpression
    | ConstantExpression
    | StringExpression
    | MemberAccessExpression
    # Function and operation expressions
    | FunctionCallExpression
    | BinaryOperationExpression
    | UnaryOperationExpression
    | ConditionalExpression
    # Collection expressions
    | ArrayExpression
    | InstanceExpression
    # JSON Schema expressions
    | BoolExpression
    | NumericExpression
    | ArithmeticExpression
    | ComparisonPredicate
    # Character expressions
    | CharacterExpression
    | ConcatenateExpression
    | FormatExpression
    # Spatial expressions
    | SpatialPredicate
    | SpatialRelatePredicate
    | GeometryExpression
    | GeometryLiteral
    | BboxLiteral
    # Temporal expressions
    | TemporalExpression
    | TemporalLiteral
    | DateInstant
    # Color expressions
    | ColorExpression
    | Color0to1
    | HexNumber
)

# Convenience type aliases
IdOrFnExpression = IdentifierExpression | FunctionCallExpression
