"""Numeric/arithmetic/bitwise expressions (JSON Schema: ``numericExpression``)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._expr_base import BaseExpression, Expression
from ._expr_value import ScalarExpression


class NumericExpression(BaseExpression):
    """Base class for numeric expressions from JSON schema."""

    type: str | None = None


class ArithmeticExpression(NumericExpression):
    """Arithmetic expression: {"op": "+|-|*|/|%|**", "args": [...]}."""

    op: Literal["+", "-", "*", "/", "%", "**"]
    args: list[NumericExpression] = Field(min_length=2)


class ArithmeticOperands(NumericExpression):
    """Advanced arithmetic operands with multiple operations."""

    operations: list[ArithmeticExpression]

    @property
    def result_type(self) -> str:
        """Static result type of this expression (always ``"numeric"``)."""
        return "numeric"


class ScalarOperands(Expression):
    """Scalar operands for various operations on single values."""

    op: str
    args: list[NumericExpression | ScalarExpression] = Field(min_length=1)


class BitwiseLogical(NumericExpression):
    """Bitwise logical: {"op": "&|||^", "args": [...]}."""

    op: Literal["&", "|", "^"]
    args: list[NumericExpression] = Field(min_length=2)


class BitwiseShift(NumericExpression):
    """Bitwise shift: {"op": "<<|>>", "args": [...]}."""

    op: Literal["<<", ">>"]
    args: list[NumericExpression] = Field(min_length=2)


class BitwiseNot(NumericExpression):
    """Bitwise NOT: {"op": "~", "args": [...]}."""

    op: Literal["~"] = "~"
    args: list[NumericExpression] = Field(min_length=1, max_length=1)
