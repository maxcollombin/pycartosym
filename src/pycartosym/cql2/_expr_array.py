"""Array-based predicates."""

from __future__ import annotations

from typing import Literal

from ._expr_base import Expression
from ._expr_boolean import BoolExpression


class ArrayPredicate(BoolExpression):
    """Array-based predicates.

    OGC CQL2-JSON format: {"op": "a_contains", "args": [arrayA, arrayB]}
    """

    op: Literal[
        "a_equals",
        "a_contains",
        "a_containedby",
        "a_overlaps",
        # Legacy bare names
        "aequals",
        "acontains",
        "acontainedby",
        "aoverlaps",
    ]
    args: list[Expression]
