"""Comparison predicates (CQL2 ``=``/``!=``/``<``/isNull/in/between/like...)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._expr_arithmetic import NumericExpression
from ._expr_base import Expression
from ._expr_boolean import BoolExpression
from ._expr_value import ScalarExpression


class ComparisonPredicate(BoolExpression):
    """Base class for comparison predicates."""

    pass


class BinaryComparisonPredicate(ComparisonPredicate):
    """Binary comparison: {"op": "=|!=|<|<=|>|>=", "args": [...]}."""

    op: Literal["=", "!=", "<", "<=", ">", ">="]
    args: list[NumericExpression | ScalarExpression] = Field(min_length=2, max_length=2)


class IsNullPredicate(ComparisonPredicate):
    """Null check: {"op": "isNull", "args": [...]}."""

    op: Literal["isNull"] = "isNull"
    args: list[Expression] = Field(min_length=1, max_length=1)


class IsInListPredicate(ComparisonPredicate):
    """In list check: {"op": "in", "args": [...]}."""

    op: Literal["in"] = "in"
    args: list[Expression | list[Expression]] = Field(min_length=2)


class IsBetweenPredicate(ComparisonPredicate):
    """Between check: {"op": "between", "args": [...]}."""

    op: Literal["between"] = "between"
    args: list[Expression] = Field(min_length=3, max_length=3)  # [value, min, max]


class IsLikePredicate(ComparisonPredicate):
    """Pattern matching: {"op": "like|ilike", "args": [...]}."""

    op: Literal["like", "ilike"]
    args: list[Expression] = Field(
        min_length=2, max_length=3
    )  # [value, pattern, escape?]
