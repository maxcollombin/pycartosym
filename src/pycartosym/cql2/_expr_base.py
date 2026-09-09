"""Foundation classes shared by every expression domain in :mod:`pycartosym.cql2`.

``BaseExpression``/``ExpressionType``/``BinaryOperator``/``UnaryOperator``/
``Expression`` have no domain of their own — every other ``_expr_*`` module
in this package builds on top of them.
"""

from __future__ import annotations

from abc import ABC
from enum import Enum

from pydantic import BaseModel, ConfigDict

from ..models.base import BaseCartoSymModel


class BaseExpression(BaseCartoSymModel):
    """Base class for all expressions with minimal required fields."""

    pass


class ExpressionType(str, Enum):
    """Types of expressions in CartoSym CSS."""

    IDENTIFIER = "identifier"
    CONSTANT = "constant"
    STRING = "string"
    MEMBER_ACCESS = "member_access"
    FUNCTION_CALL = "function_call"
    BINARY_OP = "binary_operation"
    UNARY_OP = "unary_operation"
    CONDITIONAL = "conditional"
    ARRAY = "array"
    INSTANCE = "instance"
    NULL = "null"
    # Additional expression-type discriminants
    NUMERIC = "numeric"
    OBJECT = "object"
    PREDICATE = "predicate"


class BinaryOperator(str, Enum):
    """Binary operators."""

    # Arithmetic
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    INTEGER_DIVIDE = "//"
    MODULO = "%"
    POWER = "**"

    # Relational
    EQUAL = "="
    NOT_EQUAL = "!="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    IN = "in"
    NOT_IN = "not in"
    IS = "is"
    IS_NOT = "is not"
    LIKE = "like"
    NOT_LIKE = "not like"

    # Logical
    AND = "and"
    OR = "or"

    # Special
    BETWEEN = "between"
    NOT_BETWEEN = "not between"


class UnaryOperator(str, Enum):
    """Unary operators."""

    PLUS = "+"
    MINUS = "-"
    NOT = "not"


class Expression(BaseModel, ABC):
    """Base class for all expressions."""

    model_config = ConfigDict(use_enum_values=True)

    type: ExpressionType
