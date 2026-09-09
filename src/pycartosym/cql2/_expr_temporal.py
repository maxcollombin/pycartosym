"""Temporal expressions and predicates (date/time, OGC 21-065r2 temporal clause).

``TemporalLiteral`` lives here (rather than next to ``GeometryLiteral`` in
``_expr_spatial.py``, where the original single-file layout placed it) —
it's a temporal literal by definition, and grouping it with its own domain
is the more correct home now that a split makes that grouping explicit.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from ._expr_arithmetic import NumericExpression
from ._expr_base import Expression, ExpressionType
from ._expr_boolean import BoolExpression


class TemporalExpression(Expression):
    """Base class for temporal expressions."""

    type: ExpressionType = (
        ExpressionType.FUNCTION_CALL
    )  # Default type for temporal functions


class DateInstant(TemporalExpression):
    """Date instant: {"op": "date", "args": [year, month, day]}."""

    op: Literal["date"] = "date"
    args: list[int | float] = Field(
        min_length=3, max_length=3
    )  # [year, month, day] - use simple types


class TimestampInstant(TemporalExpression):
    """Timestamp instant.

    ``{"op": "timestamp", "args": [year, month, day, hour, minute, second]}``
    """

    op: Literal["timestamp"] = "timestamp"
    args: list[NumericExpression] = Field(
        min_length=6, max_length=7
    )  # [y,m,d,h,min,s,ms?]


class DateString(TemporalExpression):
    """Date from string: {"op": "dateString", "args": [dateString, format?]}."""

    op: Literal["dateString"] = "dateString"
    args: list[Expression] = Field(min_length=1, max_length=2)


class TimestampString(TemporalExpression):
    """Timestamp from string.

    ``{"op": "timestampString", "args": [timestampString, format?]}``
    """

    op: Literal["timestampString"] = "timestampString"
    args: list[Expression] = Field(min_length=1, max_length=2)


class InstantInstance(TemporalExpression):
    """Generic instant instance for temporal operations."""

    instant_type: Literal["date", "timestamp"]
    value: str | int | float


class IntervalInstance(TemporalExpression):
    """Time interval instance: {"start": instant, "end": instant}."""

    start: TemporalExpression
    end: TemporalExpression


class IntervalArray(TemporalExpression):
    """Array of time intervals."""

    intervals: list[IntervalInstance]


class TemporalInstantExpression(TemporalExpression):
    """Complex temporal instant with operations."""

    op: str
    args: list[TemporalExpression]


class TemporalOperands(Expression):
    """Temporal operands for arithmetic operations on time values."""

    op: Literal["add", "subtract", "duration"]
    args: list[TemporalExpression] = Field(min_length=2)


class TemporalPredicate(BoolExpression):
    """Temporal predicate for time-based comparisons.

    OGC CQL2-JSON format: {"op": "t_before", "args": [instantA, instantB]}
    Reference: ecere/libCartoSym CQL2Expressions.ec (DATE/TIMESTAMP/INTERVAL handling).
    """

    op: Literal[
        "t_before",
        "t_after",
        "t_meets",
        "t_metby",
        "t_overlaps",
        "t_overlappedby",
        # OGC 21-065r2's Allen-relation names are "starts"/"startedby" and
        # "finishes"/"finishedby" (matching `T_STARTS`/`T_STARTEDBY`/
        # `T_FINISHES`/`T_FINISHEDBY` in the CQL2-Text grammar) — this
        # Literal previously spelled them "begins"/"begunby"/"ends"/
        # "endedby", which no CQL2-Text/JSON producer ever emits.
        "t_starts",
        "t_startedby",
        "t_during",
        "t_contains",
        "t_finishes",
        "t_finishedby",
        "t_equals",
        "t_intersects",
        "t_disjoint",
        # Legacy bare names
        "before",
        "after",
        "during",
        "meets",
        "overlaps",
    ]
    args: list[Expression]

    def normalised_op(self) -> str:
        """Return the CQL2-standard t_ prefixed operator name."""
        if self.op.startswith("t_"):
            return self.op
        return f"t_{self.op}"


class TemporalLiteral(TemporalExpression):
    """Temporal literal for DATE / TIMESTAMP / INTERVAL.

    CQL2-JSON format (from ecere/libCartoSym CQL2Expressions.ec toCQL2JSON):
      DATE       → {"date": "2020-01-01"}
      TIMESTAMP  → {"timestamp": "2020-01-01T00:00:00Z"}
      INTERVAL   → {"interval": ["2020-01-01", "2020-12-31"]}
    """

    temporal_type: Literal["date", "timestamp", "interval"]
    value: str | None = None  # For date / timestamp
    # For interval (2 values: start, end). A bound is usually a literal
    # string, but per the CQL2-JSON schema's `intervalArray` (each item
    # `oneOf` instantString / ".." / propertyRef / systemIdentifier /
    # functionCall / conditionalExpression) it may also be a property
    # reference or function call, e.g. `INTERVAL(starts_at, ends_at)` —
    # common in the official CQL2-Text corpus (T_DURING, T_CONTAINS…).
    interval: list[str | Expression] | None = None

    def to_cql2_json(self) -> dict[str, Any]:
        """Serialise as CQL2-JSON temporal literal."""
        if self.temporal_type == "interval" and self.interval:
            from .to_json import expression_to_json

            return {
                "interval": [
                    v if isinstance(v, str) else expression_to_json(v)
                    for v in self.interval
                ]
            }
        elif self.value:
            return {self.temporal_type: self.value}
        return {}

    @classmethod
    def from_cql2_json(cls, data: dict[str, Any]) -> TemporalLiteral:
        """Deserialise from a CQL2-JSON temporal literal."""
        if "date" in data:
            return cls(temporal_type="date", value=data["date"])
        elif "timestamp" in data:
            return cls(temporal_type="timestamp", value=data["timestamp"])
        elif "interval" in data:
            return cls(temporal_type="interval", interval=data["interval"])
        raise ValueError(f"Unknown temporal literal format: {data}")
