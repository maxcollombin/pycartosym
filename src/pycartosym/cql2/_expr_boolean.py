"""Boolean expressions (JSON Schema: ``boolExpression``)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._expr_base import BaseExpression, Expression, ExpressionType


class BoolExpression(BaseExpression, Expression):
    """Base class for boolean expressions from JSON schema.

    Also an :class:`~pycartosym.cql2._expr_base.Expression` (multiple
    inheritance, not a plain ``BaseExpression``) — predicates
    (``IsLikePredicate``, ``SpatialPredicate``, ``NotExpression``…) need to
    slot into the generic ``Expression`` tree wherever CQL2-Text combines
    them with AND/OR/NOT (``BinaryOperationExpression``/
    ``UnaryOperationExpression`` from :mod:`.from_cql2text`).
    ``BaseExpression`` is listed first so its (``BaseCartoSymModel``)
    stricter ``model_config`` — ``extra="forbid"`` in particular — wins over
    ``Expression``'s plainer one.
    """

    type: ExpressionType = ExpressionType.PREDICATE


class AndOrExpression(BoolExpression):
    """Logical AND/OR expression: {"op": "and|or", "args": [...]}."""

    op: Literal["and", "or"]
    args: list[BoolExpression] = Field(min_length=2)


class NotExpression(BoolExpression):
    """Logical NOT expression: {"op": "not", "args": [...]}."""

    op: Literal["not"] = "not"
    args: list[BoolExpression] = Field(min_length=1, max_length=1)
