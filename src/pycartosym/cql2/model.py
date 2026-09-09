"""Expression system for CartoSym-CSS and the CartoSym-JSON schema.

Supports complex expressions, conditions, function calls, and JSON Schema
expression types.

This module is a thin re-export aggregator: the actual class definitions
live in the ``_expr_*`` submodules of this package, split by domain
(``_expr_generic`` for the original CSCSS AST, then one module per JSON
Schema expression domain — boolean, arithmetic, comparison, temporal,
spatial, color, alignment, array, character — plus ``_expr_value`` for
small cross-domain reference types and ``_expr_polymorphic`` for the
wrapper/union types spanning all of them). Every name in ``__all__`` below
kept working unchanged for existing ``from .model import X`` / ``from
..cql2.model import X`` importers — only the internal layout moved.
"""

from __future__ import annotations

from ._expr_alignment import Dot, HAlignment, Horizontal, VAlignment, Vertical
from ._expr_arithmetic import (
    ArithmeticExpression,
    ArithmeticOperands,
    BitwiseLogical,
    BitwiseNot,
    BitwiseShift,
    NumericExpression,
    ScalarOperands,
)
from ._expr_array import ArrayPredicate
from ._expr_base import BinaryOperator, Expression, ExpressionType, UnaryOperator
from ._expr_boolean import AndOrExpression, BoolExpression, NotExpression
from ._expr_character import (
    AccentiExpression,
    CaseiExpression,
    CharacterExpression,
    ConcatenateExpression,
    FormatExpression,
    LowerUpperCaseExpression,
    PatternExpression,
    SubstituteExpression,
    TextOpPredicate,
)
from ._expr_color import (
    Color0to1,
    ColorComponent0to255,
    ColorExpression,
    HexNumber,
    Shape,
    ZeroToOne,
)
from ._expr_comparison import (
    BinaryComparisonPredicate,
    ComparisonPredicate,
    IsBetweenPredicate,
    IsInListPredicate,
    IsLikePredicate,
    IsNullPredicate,
)
from ._expr_generic import (
    ArrayExpression,
    BinaryOperationExpression,
    ConditionalExpression,
    ConstantExpression,
    FunctionCallExpression,
    IdentifierExpression,
    InstanceExpression,
    MemberAccessExpression,
    NullLiteral,
    PropertyAssignment,
    Selector,
    StringExpression,
    StylingRuleExpression,
    UnaryOperationExpression,
)
from ._expr_polymorphic import (
    AnyExpressionType,
    AnyExpressionWrapper,
    IdOrFnExpression,
    TypedArray,
)
from ._expr_spatial import (
    AzimuthElevation,
    BboxLiteral,
    GeometryBuffer,
    GeometryExpression,
    GeometryLiteral,
    GeometryManipulationBinary,
    GeometryManipulationUnary,
    SpatialInstance,
    SpatialPredicate,
    SpatialRelatePredicate,
)
from ._expr_temporal import (
    DateInstant,
    DateString,
    InstantInstance,
    IntervalArray,
    IntervalInstance,
    TemporalExpression,
    TemporalInstantExpression,
    TemporalLiteral,
    TemporalOperands,
    TemporalPredicate,
    TimestampInstant,
    TimestampString,
)
from ._expr_value import (
    ConditionalExpressionJSON,
    FunctionCallJSON,
    PropertyRef,
    ScalarExpression,
    ScalarLiteral,
    SystemIdentifier,
)

__all__ = [
    # Original CSCSS expressions
    "Expression",
    "ExpressionType",
    "BinaryOperator",
    "UnaryOperator",
    "IdentifierExpression",
    "ConstantExpression",
    "StringExpression",
    "NullLiteral",
    "MemberAccessExpression",
    "FunctionCallExpression",
    "BinaryOperationExpression",
    "UnaryOperationExpression",
    "ConditionalExpression",
    "ArrayExpression",
    "PropertyAssignment",
    "InstanceExpression",
    "Selector",
    "StylingRuleExpression",
    # JSON Schema expressions
    "BoolExpression",
    "AndOrExpression",
    "NotExpression",
    "NumericExpression",
    "ArithmeticExpression",
    "BitwiseLogical",
    "BitwiseShift",
    "BitwiseNot",
    "ComparisonPredicate",
    "BinaryComparisonPredicate",
    "IsNullPredicate",
    "IsInListPredicate",
    "IsBetweenPredicate",
    "IsLikePredicate",
    "PropertyRef",
    "SystemIdentifier",
    "ScalarExpression",
    "ScalarLiteral",
    "FunctionCallJSON",
    "ConditionalExpressionJSON",
    # Character expressions
    "CharacterExpression",
    "CaseiExpression",
    "AccentiExpression",
    "ConcatenateExpression",
    "FormatExpression",
    "SubstituteExpression",
    "LowerUpperCaseExpression",
    "PatternExpression",
    "TextOpPredicate",
    # Spatial expressions
    "SpatialPredicate",
    "SpatialRelatePredicate",
    "GeometryExpression",
    "GeometryLiteral",
    "BboxLiteral",
    "GeometryBuffer",
    "GeometryManipulationUnary",
    "GeometryManipulationBinary",
    "SpatialInstance",
    "AzimuthElevation",
    # Temporal expressions
    "TemporalExpression",
    "TemporalPredicate",
    "TemporalLiteral",
    "DateInstant",
    "TimestampInstant",
    "DateString",
    "TimestampString",
    "InstantInstance",
    "IntervalInstance",
    "IntervalArray",
    "TemporalInstantExpression",
    "TemporalOperands",
    # Arithmetic expressions
    "ArithmeticOperands",
    "ScalarOperands",
    # Color and graphics expressions
    "ColorExpression",
    "Color0to1",
    "ColorComponent0to255",
    "HexNumber",
    "ZeroToOne",
    "Shape",
    # Alignment and layout expressions
    "HAlignment",
    "VAlignment",
    "Horizontal",
    "Vertical",
    "Dot",
    # Miscellaneous
    "ArrayPredicate",
    # Polymorphic expressions
    "AnyExpressionType",
    "AnyExpressionWrapper",
    "TypedArray",
    "IdOrFnExpression",
]


# Resolve forward references now that every domain submodule (and hence
# every class these models can reference) has been imported above. Mirrors
# the equivalent `model_rebuild()` sweep from before the module was split
# into `_expr_*` submodules — each call's own module already imports
# everything its fields reference, so no explicit `_types_namespace` is
# needed here.
MemberAccessExpression.model_rebuild()
FunctionCallExpression.model_rebuild()
BinaryOperationExpression.model_rebuild()
UnaryOperationExpression.model_rebuild()
ConditionalExpression.model_rebuild()
ArrayExpression.model_rebuild()
PropertyAssignment.model_rebuild()
StylingRuleExpression.model_rebuild()
BinaryComparisonPredicate.model_rebuild()
IsNullPredicate.model_rebuild()
IsInListPredicate.model_rebuild()
IsBetweenPredicate.model_rebuild()
IsLikePredicate.model_rebuild()
TemporalPredicate.model_rebuild()
SpatialPredicate.model_rebuild()
SpatialRelatePredicate.model_rebuild()
GeometryLiteral.model_rebuild()
BboxLiteral.model_rebuild()
TemporalLiteral.model_rebuild()
# Re-rebuild models with Expression operands now that all subtypes are defined
UnaryOperationExpression.model_rebuild()
BinaryOperationExpression.model_rebuild()
ConditionalExpression.model_rebuild()
