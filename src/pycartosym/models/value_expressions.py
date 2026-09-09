"""Property-driven value expressions for symbolizer properties.

MapLibre GL styles let paint/layout properties be driven by data through
expression arrays (``["get", "prop"]``, ``["case", ...]``, ``["match", ...]``,
``["interpolate", ...]``, ``["step", ...]``, ``["coalesce", ...]``). The
CartoSym-JSON schema has no native construct for most of these MapLibre
operators — only a generic function-call container
(``{"op": ..., "args": [...]}``) and a property reference
(``{"property": "..."}``, schema def ``propertyRef``).

This module gives each of those MapLibre operators its own typed Pydantic
model layered over that generic container — the same pattern already used
in :mod:`pycartosym.cql2.model` for e.g. ``ArithmeticExpression``
or ``BitwiseLogical`` (a fixed ``Literal`` ``op`` over a generic op/args
shape). ``PropertyRef`` maps 1:1 onto the schema's own ``propertyRef``; the
other five have no CartoSym-JSON equivalent and serialise as an ordinary
``functionCall`` — an honest, lossless pass-through, not an invented
mapping.

Deliberately **not** placed in :mod:`pycartosym.cql2.model`: that
module is scoped to CQL2 (OGC 21-065r2), a standalone standard, and
``case``/``match``/``step``/``interpolate``/``coalesce`` are MapLibre Style
Spec vocabulary, not CQL2 vocabulary.

``SystemIdentifier`` and ``ArithmeticExpression`` (added for symbolizer
*value* expressions such as ``stroke.width: viz.sd / 1000``, OGC issue
#115) map 1:1 onto the schema's own ``systemIdentifier``/
``arithmeticExpression``, and so — like ``PropertyRef`` — arguably *are*
CQL2 vocabulary already covered by same-named classes in
:mod:`pycartosym.cql2.model`. They are re-declared here anyway, following
``PropertyRef``'s own precedent: the ``cql2.model`` versions extend the
heavier ``Expression`` ABC (plain ``pydantic.BaseModel``, a required
``type`` discriminant), which doesn't match this module's/``symbolizers.py``'s
``BaseCartoSymModel`` conventions (alias-based serialisation, no
discriminant). This module's ``ArithmeticExpression.op`` is also
schema-exact (``+``/``-``/``*``/``/``/``^``) — the ``cql2.model`` version
additionally allows ``%``/``**``, which the schema's ``arithmeticExpression``
does not.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .base import BaseCartoSymModel


def _make_arg_parity_validator(*, want_odd: bool, msg: str):
    """Build an ``args``-length-parity ``field_validator`` for ``args``.

    Shared by the 4 MapLibre expression validators below (``CaseExpression``,
    ``MatchExpression``, ``StepExpression``, ``InterpolateExpression``) —
    real argument-count validation (MapLibre requires a specific parity per
    operator), not ponytail-scope duplication. They only differ in whether
    the required length is odd or even and in their own error message; this
    dedupes the repeated ``if len(v) % 2 == /!= 0: raise`` shape without
    changing any condition it enforces.
    """

    def _check(cls, v: list) -> list:
        if (len(v) % 2 != 0) != want_odd:
            raise ValueError(msg)
        return v

    return field_validator("args")(_check)


class PropertyRef(BaseCartoSymModel):
    """Property reference: ``{"property": "name"}`` (MapLibre ``["get", "name"]``).

    Maps 1:1 onto the CartoSym-JSON schema's ``propertyRef`` definition.
    """

    property: str


class SystemIdentifier(BaseCartoSymModel):
    """System identifier reference: ``{"sysId": "identifier"}``.

    Maps 1:1 onto the CartoSym-JSON schema's ``systemIdentifier``
    definition, e.g. ``{"sysId": "viz.sd"}`` (current scale denominator).
    """

    sysId: str


class ArithmeticExpression(BaseCartoSymModel):
    """Arithmetic expression: ``{"op": "+|-|*|/|^", "args": [a, b]}``.

    Maps 1:1 onto the CartoSym-JSON schema's ``arithmeticExpression``
    (schema ``op`` enum only — CartoSym-CSS's ``%``/``div`` operators have
    no ``arithmeticExpression`` mapping).
    """

    op: Literal["+", "-", "*", "/", "^"]
    args: list[ValueExpressionArg] = Field(min_length=2, max_length=2)


class CaseExpression(BaseCartoSymModel):
    """MapLibre ``["case", cond1, out1, cond2, out2, ..., fallback]``."""

    op: Literal["case"] = "case"
    args: list[ValueExpressionArg] = Field(
        min_length=3, description="cond1, out1, cond2, out2, ..., fallback"
    )

    _check_args_parity = _make_arg_parity_validator(
        want_odd=True,
        msg=(
            "case: args must have an odd length "
            "(cond, out, ..., fallback pairs plus a trailing fallback)"
        ),
    )


class MatchExpression(BaseCartoSymModel):
    """MapLibre ``["match", input, label1, out1, label2, out2, ..., fallback]``.

    A ``label`` may itself be a list of literals (several input values
    sharing one output) — MapLibre's own shorthand, kept as a plain
    ``list`` here rather than a nested expression.
    """

    op: Literal["match"] = "match"
    args: list[ValueExpressionArg | list[str | int | float | bool]] = Field(
        min_length=4, description="input, label, out, ..., fallback"
    )

    _check_args_parity = _make_arg_parity_validator(
        want_odd=False,
        msg="match: args must be [input, label, out, ..., fallback]",
    )


class StepExpression(BaseCartoSymModel):
    """MapLibre ``["step", input, output0, stop1, output1, ...]``."""

    op: Literal["step"] = "step"
    args: list[ValueExpressionArg] = Field(
        min_length=2, description="input, output0, stop1, output1, ..."
    )

    _check_args_parity = _make_arg_parity_validator(
        want_odd=False,
        msg=(
            "step: args must have an even length "
            "(input, output0, then stop/output pairs)"
        ),
    )


class InterpolateExpression(BaseCartoSymModel):
    """MapLibre ``["interpolate", [interpolation, ...], input, stop1, output1, ...]``.

    The interpolation-type sub-array is unpacked into ``interpolation`` /
    ``base`` / ``control_points``; ``args`` keeps the remaining
    ``input, stop1, output1, ...`` sequence.
    """

    op: Literal["interpolate"] = "interpolate"
    interpolation: Literal["linear", "exponential", "cubic-bezier"] = "linear"
    base: float | None = Field(None, description="Exponential interpolation base")
    control_points: list[float] | None = Field(
        None, alias="controlPoints", description="Cubic-bezier control points"
    )
    args: list[ValueExpressionArg] = Field(
        min_length=3, description="input, stop1, output1, ..."
    )

    _check_args_parity = _make_arg_parity_validator(
        want_odd=True,
        msg=(
            "interpolate: args must have an odd length "
            "(input, then stop/output pairs)"
        ),
    )


class CoalesceExpression(BaseCartoSymModel):
    """MapLibre ``["coalesce", e1, e2, ...]`` — first non-null value."""

    op: Literal["coalesce"] = "coalesce"
    args: list[ValueExpressionArg] = Field(min_length=1)


ValueExpression = (
    PropertyRef
    | SystemIdentifier
    | ArithmeticExpression
    | CaseExpression
    | MatchExpression
    | StepExpression
    | InterpolateExpression
    | CoalesceExpression
)
"""Any of the typed MapLibre-derived value expressions."""

ValueExpressionArg = ValueExpression | bool | int | float | str | None
"""An expression argument: a nested expression, or a JSON literal."""

for _cls in (
    ArithmeticExpression,
    CaseExpression,
    MatchExpression,
    StepExpression,
    InterpolateExpression,
    CoalesceExpression,
):
    _cls.model_rebuild()
del _cls
