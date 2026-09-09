"""Character/string expression types."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._expr_base import Expression, ExpressionType
from ._expr_boolean import BoolExpression


class CharacterExpression(Expression):
    """Base class for character/string expressions from JSON schema."""

    type: ExpressionType = (
        ExpressionType.FUNCTION_CALL
    )  # Default type for function-like expressions


class CaseiExpression(CharacterExpression):
    """Case-insensitive string expression: {"op": "casei", "args": [string]}."""

    op: Literal["casei"] = "casei"
    args: list[Expression] = Field(min_length=1, max_length=1)


class AccentiExpression(CharacterExpression):
    """Accent-insensitive string expression: {"op": "accenti", "args": [string]}."""

    op: Literal["accenti"] = "accenti"
    args: list[Expression] = Field(min_length=1, max_length=1)


class ConcatenateExpression(CharacterExpression):
    """String concatenation: {"op": "concatenate", "args": [str1, str2, ...]}."""

    op: Literal["concatenate"] = "concatenate"
    args: list[Expression] = Field(min_length=2)


class FormatExpression(CharacterExpression):
    """String formatting: {"op": "format", "args": [format_string, ...values]}."""

    op: Literal["format"] = "format"
    args: list[Expression] = Field(min_length=1)


class SubstituteExpression(CharacterExpression):
    """String substitution.

    ``{"op": "substitute", "args": [string, pattern, replacement]}``
    """

    op: Literal["substitute"] = "substitute"
    args: list[Expression] = Field(min_length=3, max_length=3)


class LowerUpperCaseExpression(CharacterExpression):
    """Case conversion: {"op": "lowerCase|upperCase|upper|lower", "args": [string]}."""

    op: Literal["upper", "lower", "upperCase", "lowerCase"]
    args: list[Expression] = Field(min_length=1, max_length=1)


class PatternExpression(CharacterExpression):
    """Pattern matching expression for advanced text operations."""

    type: ExpressionType = ExpressionType.STRING
    pattern: str
    flags: list[str] | None = None


class TextOpPredicate(BoolExpression):
    """Text operation predicates for string comparisons.

    OGC CQL2-JSON: {"op": "contains|startsWith|endsWith", "args": [charExpr, charExpr]}
    """

    op: Literal["contains", "startsWith", "endsWith"]
    args: list[Expression] = Field(min_length=2, max_length=2)
