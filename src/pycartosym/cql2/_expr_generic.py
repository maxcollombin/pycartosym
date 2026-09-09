"""The original CartoSym-CSS expression AST: identifiers, operators, instances.

This is the node hierarchy the CSCSS parser builds directly (as opposed to
the JSON-Schema-derived expression types in the other ``_expr_*`` modules),
plus the CSCSS-side ``Selector``/``StylingRuleExpression`` container types.
"""

from __future__ import annotations

from pydantic import BaseModel

from ._expr_base import BinaryOperator, Expression, ExpressionType, UnaryOperator


class IdentifierExpression(Expression):
    """Simple identifier like 'dataLayer' or 'FunctionCode'."""

    type: ExpressionType = ExpressionType.IDENTIFIER
    name: str


class ConstantExpression(Expression):
    """Constant value (number, boolean, etc.)."""

    type: ExpressionType = ExpressionType.CONSTANT
    value: int | float | bool | str
    unit: str | None = None  # For values like "2.0 px"


class StringExpression(Expression):
    """String literal."""

    type: ExpressionType = ExpressionType.STRING
    value: str


class NullLiteral(Expression):
    """SQL ``NULL`` literal (CQL2 ``x IS NULL``).

    A distinct type so consumers test ``isinstance(expr, NullLiteral)`` rather
    than sniffing an identifier name. Serialises to JSON ``null``.
    """

    type: ExpressionType = ExpressionType.NULL

    def to_cql2_json(self) -> None:
        """Serialise to CQL2-JSON: SQL ``NULL`` becomes JSON ``null``."""
        return None


class MemberAccessExpression(Expression):
    """Member access like 'dataLayer.type' or 'viz.timeInterval.start.date'."""

    type: ExpressionType = ExpressionType.MEMBER_ACCESS
    object: Expression
    member: str


class FunctionCallExpression(Expression):
    """Function call like 'Text(...)' or 'Image(...)'."""

    type: ExpressionType = ExpressionType.FUNCTION_CALL
    function_name: str
    arguments: list[Expression]


class BinaryOperationExpression(Expression):
    """Binary operation like 'a + b' or 'x = y'."""

    type: ExpressionType = ExpressionType.BINARY_OP
    left: Expression
    operator: BinaryOperator
    right: Expression


class UnaryOperationExpression(Expression):
    """Unary operation like '-x' or 'not y'."""

    type: ExpressionType = ExpressionType.UNARY_OP
    operator: UnaryOperator
    operand: Expression


class ConditionalExpression(Expression):
    """Ternary conditional like 'condition ? true_value : false_value'."""

    type: ExpressionType = ExpressionType.CONDITIONAL
    condition: Expression
    true_value: Expression
    false_value: Expression


class ArrayExpression(Expression):
    """Array literal like '[a, b, c]'."""

    type: ExpressionType = ExpressionType.ARRAY
    elements: list[Expression]


class PropertyAssignment(BaseModel):
    """Property assignment within an instance."""

    property: str
    value: Expression


class InstanceExpression(Expression):
    """Instance creation like '{color: red; opacity: 0.5}' or 'Text(...)'."""

    type: ExpressionType = ExpressionType.INSTANCE
    class_name: str | None = None  # For Text(...) vs {...}
    properties: list[PropertyAssignment] = []


# Selector with expressions
class Selector(BaseModel):
    """Enhanced selector that can include expressions."""

    name: str | None = None  # Simple name like "Landuse"
    conditions: list[Expression] = []  # Conditions like [dataLayer.type = vector]

    def is_simple(self) -> bool:
        """Check if this is a simple selector (name only)."""
        return self.name is not None and len(self.conditions) == 0


# Enhanced styling rule
class StylingRuleExpression(BaseModel):
    """Styling rule that can contain expressions and nested rules."""

    selectors: list[Selector] = []
    properties: dict[str, Expression] = {}  # property_name -> expression
    nested_rules: list[StylingRuleExpression] = []
