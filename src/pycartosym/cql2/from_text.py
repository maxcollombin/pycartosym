"""CQL2 / CartoSym-CSS expression parsing -> ``cql2.model`` expression models.

Public callers should use :mod:`pycartosym.cql2`
(``parse_text`` / ``parse_tree``); ``ExpressionParser`` here is the
implementation. Two entry points:

* :meth:`ExpressionParser.parse_expression_ctx` — **primary**, used for
  selector expressions. Walks the ANTLR ``ExpressionContext`` parse tree
  the grammar already built (``_atom_from_ctx`` / ``_flatten_binary`` /
  ``_build_precedence``). Chained binary operators are flattened and
  re-associated under a conventional precedence
  (``or < and < relational < + - < * / < ^``) rather than the grammar's
  own left-recursive alternative order.
* :meth:`ExpressionParser._parse_expression_text` (str) — the CQL2-Text
  entry point (``cql2.parse_text``), plus ``parse_expression`` and the
  repair sites in ``ast_converter``. It first tries the standalone
  ``CQL2Text.g4`` tree-walker (:func:`.from_cql2text.parse_cql2_text`);
  only on failure does it fall back to lexing+parsing the string as a
  CartoSym-CSS ``expression`` and walking that tree
  (:meth:`_text_to_expr_ctx`), then finally to the quote- and
  bracket-aware text-scan methods below (``parse_expression`` /
  ``_parse_logical_expression`` / ``_parse_single_expression`` and their
  helpers) — a safety net for constructs outside CQL2-Text proper (e.g.
  ``0x``-prefixed hex literals), not expected to trigger for actual
  CQL2-Text input. The hand-rolled scanner that used to be the sole
  parsing path here (``_parse_expression_text_legacy``) was removed once
  the tree-walker/grammar tiers above were proven to cover the test
  suite and official corpus without it.

Covers CQL2 spatial / temporal / array predicates, BETWEEN / IN / LIKE /
IS NULL, WKT and temporal literals, arithmetic, member access, function
calls, conditionals, and logical / relational operators.

Operators are read from the grammar-generated token accessors
(``op_ctx.AND()``, ``rel_ctx.IN()`` …), never their literal text. The CQL2
function/predicate vocabulary comes from :mod:`.vocab` (derived from
the Pydantic model ``Literal`` fields), not hand-written lists.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from ..grammar.generated import CartoSymCSSGrammar as _G
from . import vocab as _v
from .model import (
    AccentiExpression,
    ArrayExpression,
    ArrayPredicate,
    BboxLiteral,
    BinaryOperationExpression,
    BinaryOperator,
    CaseiExpression,
    ConcatenateExpression,
    ConditionalExpression,
    ConstantExpression,
    Expression,
    FormatExpression,
    FunctionCallExpression,
    GeometryBuffer,
    GeometryLiteral,
    GeometryManipulationBinary,
    GeometryManipulationUnary,
    IdentifierExpression,
    InstanceExpression,
    IsBetweenPredicate,
    IsInListPredicate,
    IsLikePredicate,
    IsNullPredicate,
    LowerUpperCaseExpression,
    MemberAccessExpression,
    NotExpression,
    NullLiteral,
    PropertyAssignment,
    SpatialPredicate,
    SpatialRelatePredicate,
    StringExpression,
    SubstituteExpression,
    TemporalLiteral,
    TemporalPredicate,
    TextOpPredicate,
    UnaryOperationExpression,
    UnaryOperator,
)

# ---------------------------------------------------------------------------
# CQL2 vocabulary — derived from the Pydantic models (see cql2.vocab), not
# hand-listed here.
# ---------------------------------------------------------------------------
_SPATIAL_PREDICATES = _v.SPATIAL_PREDICATES
_SPATIAL_RELATE = _v.SPATIAL_RELATE
_TEMPORAL_PREDICATES = _v.TEMPORAL_PREDICATES
_ARRAY_PREDICATES = _v.ARRAY_PREDICATES
_WKT_TYPES = _v.WKT_TYPES
_WKT_TO_GEOJSON = _v.WKT_TO_GEOJSON
_TEMPORAL_LITERAL_NAMES = _v.TEMPORAL_LITERAL_NAMES
_CHARACTER_FUNCTIONS = _v.CHARACTER_FUNCTIONS
_TEXT_OP_PREDICATES = _v.TEXT_OP_PREDICATES
_GEOM_MANIPULATION_BINARY = _v.GEOM_MANIPULATION_BINARY
_GEOM_MANIPULATION_UNARY = _v.GEOM_MANIPULATION_UNARY
_GEOM_BUFFER = _v.GEOM_BUFFER
_KNOWN_CQL2_CALLS = _v.KNOWN_CQL2_CALLS

# Parser helpers hand back nodes of many different concrete types — plain
# ``Expression`` subclasses, ``BoolExpression``/``ComparisonPredicate``
# predicates (also ``Expression`` subclasses, see ``model.BoolExpression``),
# occasionally ``None`` or a bare ``list`` — so the return type stays loose.
_ExprNode = Any


class ExpressionParser:
    """Parser for converting ANTLR expression contexts to Pydantic expressions."""

    # =================================================================
    # Parse-tree walk (primary path)
    #
    # The grammar's left-recursive ``expression`` rule is already an
    # operator-precedence tree; we walk it instead of re-scanning text.
    # Its alternatives are labelled (``LogicalExprContext`` …), so the
    # dispatch is a plain ``isinstance`` chain — see ``_atom_from_ctx`` /
    # ``_binary_op_info``.
    # =================================================================

    # Operator precedence, low → high. Relational operators all share one
    # level. This is the SQL / CQL2 convention, which the grammar's own
    # left-recursive alternative order also follows; re-climbing the
    # flattened chain keeps the result independent of that order.
    _PREC_OR = 1
    _PREC_AND = 2
    _PREC_REL = 3
    _PREC_ADD = 4
    _PREC_MUL = 5
    _PREC_POW = 6

    @staticmethod
    def parse_expression_ctx(ctx) -> _ExprNode | None:
        """Convert an ANTLR ``ExpressionContext`` to a Pydantic ``Expression``.

        Dispatches on the grammar's labelled ``expression`` alternatives
        (``PrimaryExprContext``, ``LogicalExprContext`` …). Chained binary
        operators are flattened and re-associated under conventional
        precedence (see :attr:`_PREC_*`) rather than trusting the grammar's
        own left-recursive alternative ordering.
        """
        if ctx is None:
            return None
        return ExpressionParser._expr_from_ctx(ctx)

    @staticmethod
    def _expr_from_ctx(ctx) -> _ExprNode:
        atom = ExpressionParser._atom_from_ctx(ctx)
        if atom is not None:
            return atom
        flat = ExpressionParser._flatten_binary(ctx)
        if flat and len(flat) >= 3:
            return ExpressionParser._build_precedence(flat)
        if flat and len(flat) == 1:
            return flat[0]
        return ExpressionParser._parse_expression_text(
            ExpressionParser._ctx_source_text(ctx)
        )

    @staticmethod
    def _atom_from_ctx(ctx) -> Any:
        """Non-binary forms: leaves, parens, unary, conditional, between, etc.

        Dispatches on the grammar's *labelled* alternative context types
        (``PrimaryExprContext``, ``ParenExprContext`` …). Returns ``None``
        when *ctx* is a chained binary-operator node (left to
        :meth:`_flatten_binary`).
        """
        if isinstance(ctx, _G.StringExprContext):
            return ExpressionParser._parse_string(ctx.expString())
        if isinstance(ctx, _G.CallExprContext):
            return ExpressionParser._dispatch_call_ctx(ctx.expCall())
        if isinstance(ctx, _G.InstanceExprContext):
            return ExpressionParser._parse_instance_from_text(
                ExpressionParser._ctx_source_text(ctx.expInstance())
            )
        if isinstance(ctx, _G.VariableExprContext):
            return IdentifierExpression(name=ctx.variable().getText())
        if isinstance(ctx, _G.TupleExprContext):
            return ExpressionParser._parse_tuple_ctx(ctx.tuple_())
        if isinstance(ctx, _G.ArrayExprContext):
            arr = ctx.expArray()
            elems = ExpressionParser._flatten_left_recursive(
                arr.arrayElements(), "arrayElements", "expression"
            )
            # `(x)` is grouping; `(a, b)` / `[a, b]` is a list.
            if arr.LPAR() is not None and len(elems) == 1:
                return ExpressionParser._expr_from_ctx(elems[0])
            return ArrayExpression(
                elements=[ExpressionParser._expr_from_ctx(e) for e in elems]
            )
        if isinstance(ctx, _G.PrimaryExprContext):
            return ExpressionParser._parse_id_or_constant_ctx(ctx.idOrConstant())
        if isinstance(ctx, _G.UnaryLogicalExprContext):
            return UnaryOperationExpression(
                operator=UnaryOperator.NOT,
                operand=ExpressionParser._expr_from_ctx(ctx.expression()),
            )
        if isinstance(ctx, _G.UnaryArithExprContext):
            minus = ctx.unaryArithmeticOperator().MINUS() is not None
            return UnaryOperationExpression(
                operator=UnaryOperator.MINUS if minus else UnaryOperator.PLUS,
                operand=ExpressionParser._expr_from_ctx(ctx.expression()),
            )
        if isinstance(ctx, _G.ParenExprContext):
            return ExpressionParser._expr_from_ctx(ctx.expression())
        if isinstance(ctx, _G.ConditionalExprContext):
            sub = ctx.expression()
            return ConditionalExpression(
                condition=ExpressionParser._expr_from_ctx(sub[0]),
                true_value=ExpressionParser._expr_from_ctx(sub[1]),
                false_value=ExpressionParser._expr_from_ctx(sub[2]),
            )
        if isinstance(ctx, _G.BetweenExprContext):
            sub = ctx.expression()
            pred: Any = IsBetweenPredicate(
                args=[ExpressionParser._expr_from_ctx(e) for e in sub[:3]]
            )
            if ctx.betweenOperator().NOT() is not None:
                return NotExpression(args=[pred])
            return pred
        if isinstance(ctx, _G.IndexExprContext):
            # No dedicated index model; preserve the historical flat text.
            return IdentifierExpression(name=ctx.getText())
        if isinstance(ctx, _G.MemberAccessExprContext):
            return MemberAccessExpression(
                object=ExpressionParser._expr_from_ctx(ctx.expression()),
                member=ctx.IDENTIFIER().getText(),
            )
        return None

    @staticmethod
    def _first_token_op(
        op_ctx, table: dict[str, BinaryOperator]
    ) -> BinaryOperator | None:
        """First ``BinaryOperator`` in *table* whose token accessor is set on *op_ctx*.

        *table* is keyed by grammar token name, e.g. ``"IDIV"``.
        """
        for token_name, operator in table.items():
            if getattr(op_ctx, token_name)() is not None:
                return operator
        return None

    @staticmethod
    def _binary_op_info(ctx):
        """Classify a labelled binary-operator alternative.

        Returns ``(BinaryOperator | None, precedence, relationalOperator
        ctx | None)`` for a labelled binary-operator alternative, else
        ``None``.

        Operators are identified via the generated token accessors
        (``op_ctx.AND()``, ``op_ctx.IDIV()`` …), never by their literal text.
        """
        if isinstance(ctx, _G.LogicalExprContext):
            if ctx.AND() is not None:
                return (BinaryOperator.AND, ExpressionParser._PREC_AND, None)
            return (BinaryOperator.OR, ExpressionParser._PREC_OR, None)
        if isinstance(ctx, _G.RelationalExprContext):
            return (None, ExpressionParser._PREC_REL, ctx.relationalOperator())
        if isinstance(ctx, _G.PowExprContext):
            return (BinaryOperator.POWER, ExpressionParser._PREC_POW, None)
        if isinstance(ctx, _G.MulExprContext):
            op = ExpressionParser._first_token_op(
                ctx.arithmeticOperatorMul(), _v.ARITH_MUL_BY_TOKEN
            )
            return (op or BinaryOperator.MULTIPLY, ExpressionParser._PREC_MUL, None)
        if isinstance(ctx, _G.AddExprContext):
            op = ExpressionParser._first_token_op(
                ctx.arithmeticOperatorAdd(), _v.ARITH_ADD_BY_TOKEN
            )
            return (op or BinaryOperator.ADD, ExpressionParser._PREC_ADD, None)
        return None

    @staticmethod
    def _flatten_binary(ctx):
        """Flatten a chain of binary operators into ``[expr, opinfo, expr, …]``."""
        info = ExpressionParser._binary_op_info(ctx)
        if info is None:
            atom = ExpressionParser._atom_from_ctx(ctx)
            return [atom] if atom is not None else None
        left_ctx, right_ctx = ctx.expression()[:2]
        left = ExpressionParser._flatten_binary(left_ctx) or [
            ExpressionParser._expr_from_ctx(left_ctx)
        ]
        right = ExpressionParser._flatten_binary(right_ctx) or [
            ExpressionParser._expr_from_ctx(right_ctx)
        ]
        return left + [info] + right

    @staticmethod
    def _build_precedence(flat) -> Any:
        """Precedence-climb ``[expr, (op, prec, relctx), expr, …]`` (left-assoc)."""

        def climb(pos: int, min_prec: int):
            result = flat[pos]
            pos += 1
            while pos < len(flat):
                op_enum, prec, rel_ctx = flat[pos]
                if prec < min_prec:
                    break
                pos += 1
                rhs, pos = climb(pos, prec + 1)
                result = ExpressionParser._make_binary(
                    rel_ctx, op_enum, prec, result, rhs
                )
            return result, pos

        node, _ = climb(0, 1)
        return node

    @staticmethod
    def _make_binary(rel_ctx, op_enum, prec: int, left, right) -> Any:
        if prec == ExpressionParser._PREC_REL:
            return ExpressionParser._build_relational(rel_ctx, left, right)
        return BinaryOperationExpression(left=left, operator=op_enum, right=right)

    # -- parse-tree helpers -----------------------------------------------------

    @staticmethod
    def _ctx_source_text(ctx) -> str:
        """Original source slice for *ctx* (with spacing), else ``getText()``."""
        try:
            start = ctx.start.start
            stop = ctx.stop.stop
            return str(ctx.start.getInputStream().getText(start, stop))
        except Exception:  # noqa: BLE001 - fall back to token-joined text
            return ctx.getText() if hasattr(ctx, "getText") else str(ctx)

    @staticmethod
    def _parse_id_or_constant_ctx(ctx) -> Any:
        """``IdOrConstantContext`` -> identifier / number / boolean / null."""
        if ctx.expConstant() is not None:
            return ExpressionParser._parse_constant(ctx.expConstant())
        if ctx.TRUE() is not None:
            return ConstantExpression(value=True)
        if ctx.FALSE() is not None:
            return ConstantExpression(value=False)
        if ctx.NULL() is not None:
            return NullLiteral()
        return IdentifierExpression(name=ctx.getText())

    @staticmethod
    def _flatten_left_recursive(ctx, self_accessor: str, item_accessor: str) -> list:
        """Flatten a left-recursive ``rule: items | rule ',' item`` list."""
        items: list = []
        while ctx is not None:
            inner = getattr(ctx, self_accessor)()
            got = getattr(ctx, item_accessor)()
            got = got if isinstance(got, list) else ([got] if got is not None else [])
            if inner is not None:
                items = got + items
                ctx = inner
            else:
                items = got + items
                ctx = None
        return items

    @staticmethod
    def _parse_tuple_ctx(ctx) -> ArrayExpression:
        """``TupleContext`` (space-separated values) -> ``ArrayExpression``."""
        elems = ExpressionParser._flatten_left_recursive(ctx, "tuple_", "idOrConstant")
        return ArrayExpression(
            elements=[ExpressionParser._parse_id_or_constant_ctx(e) for e in elems]
        )

    # relationalOperator token accessor -> comparison BinaryOperator
    _REL_COMPARISON = {
        "EQ": BinaryOperator.EQUAL,
        "NEQ": BinaryOperator.NOT_EQUAL,
        "LTEQ": BinaryOperator.LESS_EQUAL,
        "GTEQ": BinaryOperator.GREATER_EQUAL,
        "LT": BinaryOperator.LESS_THAN,
        "GT": BinaryOperator.GREATER_THAN,
    }

    @staticmethod
    def _build_relational(rel_ctx, left: Any, right: Any) -> Any:
        """Model for ``expression relationalOperator expression``.

        ``relationalOperator`` folds in ``IN / NOT IN / IS / IS NOT /
        LIKE / NOT LIKE``. The operator is read from *rel_ctx*'s
        grammar-generated token accessors (``.IN()``, ``.NOT()`` …); these
        cases become dedicated predicates rather than a plain
        :class:`BinaryOperationExpression`.
        """
        negated = rel_ctx.NOT() is not None

        if rel_ctx.LIKE() is not None:
            pred: Any = IsLikePredicate(op="like", args=[left, right])
            return NotExpression(args=[pred]) if negated else pred

        if rel_ctx.IN() is not None:
            if isinstance(right, ArrayExpression):
                items: list[Expression] = list(right.elements)
            elif isinstance(right, list):
                items = right
            else:
                items = [right]
            pred = IsInListPredicate(args=[left, items])
            return NotExpression(args=[pred]) if negated else pred

        if rel_ctx.IS() is not None:
            is_not = negated
            # The grammar attaches a bare `not` as a unary operator, so
            # `x is not null` parses as `x IS (not null)`.
            if isinstance(right, UnaryOperationExpression) and str(
                right.operator
            ).lower().endswith("not"):
                is_not = True
                right = right.operand
            if isinstance(right, NullLiteral):
                pred = IsNullPredicate(args=[left])
                return NotExpression(args=[pred]) if is_not else pred
            op = BinaryOperator.IS_NOT if is_not else BinaryOperator.IS
            return BinaryOperationExpression(left=left, operator=op, right=right)

        for token_name, operator in ExpressionParser._REL_COMPARISON.items():
            if getattr(rel_ctx, token_name)() is not None:
                return BinaryOperationExpression(
                    left=left, operator=operator, right=right
                )
        return BinaryOperationExpression(
            left=left, operator=BinaryOperator.EQUAL, right=right
        )

    @staticmethod
    def _dispatch_call_ctx(call_ctx) -> Any:
        """``ExpCallContext`` (``IDENTIFIER '(' arguments ')'``) -> model.

        Known CQL2 functions (spatial / temporal / array predicates, WKT and
        temporal literals, character/geometry functions) are handed to the
        text-based :meth:`_try_parse_cql2_function` on the call's source
        slice — its per-name model construction is already covered by
        ``test_cql2_*``. Everything else becomes a structural
        :class:`FunctionCallExpression` built from the argument sub-trees.
        """
        func_lower = call_ctx.IDENTIFIER().getText().lower()

        if func_lower in _KNOWN_CQL2_CALLS:
            model = ExpressionParser._try_parse_cql2_function(
                ExpressionParser._ctx_source_text(call_ctx)
            )
            if model is not None:
                return model

        func_name = call_ctx.IDENTIFIER().getText()
        arg_ctxs = ExpressionParser._flatten_left_recursive(
            call_ctx.arguments(), "arguments", "expression"
        )
        return FunctionCallExpression(
            function_name=func_name,
            arguments=[ExpressionParser.parse_expression_ctx(a) for a in arg_ctxs],
        )

    @staticmethod
    def parse_expression(ctx) -> _ExprNode | None:
        """Convert ANTLR expression context to Pydantic Expression."""
        if not ctx:
            return None

        # Always use the original text with spaces for parsing
        original_text = None
        if (
            hasattr(ctx, "start")
            and hasattr(ctx, "stop")
            and hasattr(ctx.start, "source")
        ):
            try:
                input_stream = ctx.start.source
                start_idx = ctx.start.start
                stop_idx = ctx.stop.stop
                original_text = input_stream.strdata[start_idx : stop_idx + 1]
            except Exception:
                pass
        if not original_text:
            original_text = ctx.getText() if hasattr(ctx, "getText") else str(ctx)

        # Strip a single pair of parentheses that wraps the *entire*
        # expression, e.g. `(a = 1 and b = 2)` — otherwise the
        # function-call branch below would mis-read it as a call.
        original_text = ExpressionParser._unwrap_parens(original_text.strip())

        # Check for top-level (depth 0, unquoted) logical operations.
        has_top_or = ExpressionParser._find_top_level(original_text, " or ") != -1
        has_top_and = ExpressionParser._find_top_level(original_text, " and ") != -1
        if has_top_or or has_top_and:
            # But not if ' and ' only appears inside a BETWEEN expression
            if not ExpressionParser._only_between_and(original_text):
                return ExpressionParser._parse_logical_expression(original_text)
        # Leading unary NOT (no top-level and/or to split on first)
        if original_text.strip()[:4].lower() == "not ":
            return ExpressionParser._parse_logical_expression(original_text)

        # --- CQL2 postfix operators (before relational so they take priority) ---
        cql2 = ExpressionParser._try_parse_cql2_operator(original_text)
        if cql2 is not None:
            return cql2

        # Check for relational operations (top-level, unquoted)
        for op in [">=", "<=", "<>", "!=", "=", ">", "<"]:
            if ExpressionParser._find_top_level(original_text, f" {op} ") != -1:
                return ExpressionParser._parse_relational_expression(original_text, op)

        # Handle member access (contains dots)
        if (
            "." in original_text
            and not original_text.startswith('"')
            and not original_text.startswith("'")
        ):
            return ExpressionParser._parse_member_access_from_text(original_text)

        # Handle string literals
        if (original_text.startswith('"') and original_text.endswith('"')) or (
            original_text.startswith("'") and original_text.endswith("'")
        ):
            return StringExpression(value=original_text[1:-1])

        # Handle 0x-prefixed hex literals: 0xFF, 0xAB12 etc. — not CQL2-Text
        # (absent from the OGC ABNF, CQL2Text.g4 deliberately omits them) and
        # not the CartoSym-CSS grammar's own `#RRGGBB`-style HEX_LITERAL
        # token, so this text-scan level is the only place that reads them.
        if original_text.startswith("0x") or original_text.startswith("0X"):
            try:
                return ConstantExpression(value=int(original_text, 16))
            except ValueError:
                pass

        # Handle numbers
        if original_text.replace(".", "").replace("-", "").isdigit():
            try:
                value = (
                    int(original_text)
                    if "." not in original_text
                    else float(original_text)
                )
                return ConstantExpression(value=value)
            except ValueError:
                pass

        # Handle boolean constants
        if original_text.lower() in ["true", "false"]:
            return ConstantExpression(value=original_text.lower() == "true")

        # Handle function calls — dispatch CQL2 predicates / literals first
        if "(" in original_text and ")" in original_text:
            cql2_func = ExpressionParser._try_parse_cql2_function(original_text)
            if cql2_func is not None:
                return cql2_func
            return ExpressionParser._parse_function_call_from_text(original_text)

        # Handle curly-brace temporal literals: DATE{...}, TIMESTAMP{...}, INTERVAL{...}
        temporal_brace = ExpressionParser._try_parse_temporal_braces(original_text)
        if temporal_brace is not None:
            return temporal_brace

        # Handle object literals {color: red; opacity: 0.5}
        if original_text.startswith("{") and original_text.endswith("}"):
            return ExpressionParser._parse_instance_from_text(original_text)

        # Default: treat as identifier
        return IdentifierExpression(name=original_text)

    @staticmethod
    def _parse_logical_expression(text: str) -> _ExprNode:
        """Parse logical expressions like 'a and b' or 'x or y'.

        Splits at the *last* top-level occurrence of the operator, not the
        first, so chains like 'a and b and c' parse left-associatively —
        matching the ANTLR grammar's own left-recursive `expression` rule
        (vendor/cartosymcss-grammar/CartoSymCSSGrammar.g4). Splitting at the
        first occurrence would instead build a right-associative tree.
        """
        # Split at the *last* top-level (depth 0, unquoted) ' or ', then
        # ' and ' — left-associative, matching the ANTLR grammar's own
        # left-recursive `expression` rule.
        for needle, op in ((" or ", BinaryOperator.OR), (" and ", BinaryOperator.AND)):
            pos = ExpressionParser._find_top_level(text, needle, last=True)
            if pos != -1:
                return BinaryOperationExpression(
                    left=ExpressionParser.parse_expression(text[:pos].strip()),
                    operator=op,
                    right=ExpressionParser.parse_expression(
                        text[pos + len(needle) :].strip()
                    ),
                )

        # Leading unary NOT: `not <expr>` / `not (<expr>)`
        stripped = text.strip()
        inner = stripped[4:].strip() if stripped[:4].lower() == "not " else ""
        if inner:
            return UnaryOperationExpression(
                operator=UnaryOperator.NOT,
                operand=ExpressionParser.parse_expression(inner),
            )

        # No logical op at top level, parse as relational or single
        return ExpressionParser._parse_single_expression(text)

    @staticmethod
    def _parse_relational_expression(text: str, operator_str: str) -> _ExprNode:
        """Parse relational expressions like 'a = b' or 'x < 5'."""
        # A top-level (depth 0, unquoted) logical operator outranks the
        # relational one — hand back to the logical parser. The guard is
        # quote-aware so `name = 'a or b'` is *not* treated as an OR.
        if (
            ExpressionParser._find_top_level(text, " or ") != -1
            or ExpressionParser._find_top_level(text, " and ") != -1
        ):
            return ExpressionParser._parse_logical_expression(text)

        # No logical op at this level, parse as relational
        op_pattern = f" {operator_str} "
        op_pos = ExpressionParser._find_top_level(text, op_pattern, last=False)
        if op_pos != -1:
            left_part = text[:op_pos].strip()
            right_part = text[op_pos + len(op_pattern) :].strip()
            left_expr = ExpressionParser._parse_single_expression(left_part)
            right_expr = ExpressionParser._parse_single_expression(right_part)
            operator = ExpressionParser._map_relational_operator(operator_str)
            return BinaryOperationExpression(
                left=left_expr, operator=operator, right=right_expr
            )
        # Fallback: try without spaces for cases like 'a=b'
        if operator_str in text:
            parts = text.split(operator_str, 1)
            if len(parts) == 2:
                left_expr = ExpressionParser._parse_single_expression(parts[0].strip())
                right_expr = ExpressionParser._parse_single_expression(parts[1].strip())
                operator = ExpressionParser._map_relational_operator(operator_str)
                return BinaryOperationExpression(
                    left=left_expr, operator=operator, right=right_expr
                )
        return IdentifierExpression(name=text)

    @staticmethod
    def _parse_member_access_from_text(text: str) -> _ExprNode:
        """Parse member access from text like 'dataLayer.type'."""
        parts = text.split(".")
        if len(parts) == 2:
            return MemberAccessExpression(
                object=IdentifierExpression(name=parts[0]), member=parts[1]
            )
        elif len(parts) > 2:
            # Chain of member accesses: a.b.c.d
            base: Any = IdentifierExpression(name=parts[0])
            for i in range(1, len(parts) - 1):
                base = MemberAccessExpression(object=base, member=parts[i])
            return MemberAccessExpression(object=base, member=parts[-1])

        return IdentifierExpression(name=text)

    @staticmethod
    def _parse_function_call_from_text(text: str) -> _ExprNode:
        """Parse function calls like 'Text(...)' from text."""
        if "(" not in text:
            return IdentifierExpression(name=text)

        func_name = text.split("(")[0].strip()
        args_part = text[text.find("(") + 1 : text.rfind(")")]

        # Simple argument parsing - can be enhanced
        arguments = []
        if args_part.strip():
            # For now, treat each comma-separated part as a separate argument
            for arg in args_part.split(","):
                arg = arg.strip()
                arguments.append(ExpressionParser._parse_single_expression(arg))

        return FunctionCallExpression(function_name=func_name, arguments=arguments)

    @staticmethod
    def _parse_instance_from_text(text: str) -> InstanceExpression:
        """Parse object instances like '{color: gray; opacity: 0.5}' from text."""
        # Remove braces
        content = text.strip("{}").strip()

        properties = []
        if content:
            # Split by semicolon for properties
            for prop_def in content.split(";"):
                prop_def = prop_def.strip()
                if ":" in prop_def:
                    key, value = prop_def.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    prop_expr = ExpressionParser._parse_single_expression(value)
                    properties.append(PropertyAssignment(property=key, value=prop_expr))

        return InstanceExpression(class_name=None, properties=properties)

    @staticmethod
    def _text_to_expr_ctx(text: str):
        """Lex+parse *text* as a CartoSym-CSS ``expression``; ``None`` on error.

        Returns the ANTLR ``ExpressionContext`` only when *text* parses
        cleanly and is fully consumed. Used to route the text-scan entry
        points through the grammar's own operator-precedence tree (see
        :meth:`parse_expression_ctx`) instead of the ``parse_expression``
        text-scan fallback below, which does not parse arithmetic.
        """
        from antlr4 import CommonTokenStream, InputStream, Token
        from antlr4.error.ErrorListener import ErrorListener

        from ..grammar.generated import CartoSymCSSGrammar, CartoSymCSSLexer

        class _Collect(ErrorListener):
            def __init__(self) -> None:
                super().__init__()
                self.hit = False

            def syntaxError(self, *_a, **_kw) -> None:
                self.hit = True

        listener = _Collect()
        lexer = CartoSymCSSLexer(InputStream(text))
        lexer.removeErrorListeners()
        lexer.addErrorListener(listener)
        parser = CartoSymCSSGrammar(CommonTokenStream(lexer))
        parser.removeErrorListeners()
        parser.addErrorListener(listener)
        try:
            tree = parser.expression()
        except Exception:  # noqa: BLE001 - any ANTLR failure -> caller falls back
            return None
        if listener.hit or parser.getCurrentToken().type != Token.EOF:
            return None
        return tree

    @staticmethod
    def _parse_expression_text(text: str) -> _ExprNode:
        """Parse a CQL2-Text / CartoSym-CSS expression string to a model.

        Prefers the standalone ``CQL2Text.g4`` grammar
        (:func:`.from_cql2text.parse_cql2_text`) — a real CQL2-Text
        tree-walker, case-insensitive keywords and all. Falls back to the
        CartoSym-CSS ``expression`` grammar
        (:meth:`_text_to_expr_ctx`/:meth:`parse_expression_ctx`), then to
        :meth:`parse_expression` (a quote- and bracket-aware text scan) for
        constructs neither grammar covers (e.g. ``0x``-prefixed hex
        literals, absent from both the CQL2-Text ABNF and the CartoSym-CSS
        grammar's own ``#RRGGBB``-style ``HEX_LITERAL``) — kept as a safety
        net, not expected to trigger for actual CQL2-Text input.
        """
        text = text.strip()
        try:
            from .from_cql2text import parse_cql2_text

            return parse_cql2_text(text)
        except Exception:  # noqa: BLE001 - fall back to the CartoSym-CSS grammar
            pass
        ctx = ExpressionParser._text_to_expr_ctx(text)
        if ctx is not None:
            try:
                walked = ExpressionParser.parse_expression_ctx(ctx)
            except Exception:  # noqa: BLE001 - fall back to the final parser below
                walked = None
            if walked is not None and not ExpressionParser._is_juxtaposition_artifact(
                walked, text
            ):
                return walked
        return ExpressionParser.parse_expression(text)

    @staticmethod
    def _is_juxtaposition_artifact(walked: Any, text: str) -> bool:
        """Return True if *walked* is a bare space-separated tuple, not a real array.

        The CartoSym-CSS grammar's ``tuple`` rule accepts any run of
        space-separated identifiers/numbers, so CQL2-Text the grammar
        cannot lex properly — upper-case keywords (``score BETWEEN 0 AND
        100``), hex literals (``0xFF`` → ``0 xFF``) — parses "cleanly" as
        an :class:`ArrayExpression`. A genuine array literal always has
        brackets or commas; a bare tuple here means the grammar path
        failed silently and the ``parse_expression`` text-scan fallback
        should take over instead.
        """
        return isinstance(walked, ArrayExpression) and not (set("[],") & set(text))

    @staticmethod
    def _parse_constant(ctx) -> ConstantExpression:
        """Parse constant value."""
        text = ctx.getText()
        unit = None

        # Check for unit
        if hasattr(ctx, "UNIT") and ctx.UNIT():
            unit = ctx.UNIT().getText()
            # Remove unit from text
            text = text.replace(unit, "").strip()

        # Parse value
        try:
            if "." in text or "e" in text.lower():
                value = float(text)
            else:
                value = int(text)
        except ValueError:
            value = text

        return ConstantExpression(value=value, unit=unit)

    @staticmethod
    def _parse_string(ctx) -> StringExpression:
        """Parse string literal."""
        text = ctx.getText()
        # Remove quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        return StringExpression(value=text)

    @staticmethod
    def _map_relational_operator(op_text: str) -> BinaryOperator:
        """Map operator text to BinaryOperator enum."""
        mapping = {
            "=": BinaryOperator.EQUAL,
            "<>": BinaryOperator.NOT_EQUAL,
            "!=": BinaryOperator.NOT_EQUAL,
            "<": BinaryOperator.LESS_THAN,
            "<=": BinaryOperator.LESS_EQUAL,
            ">": BinaryOperator.GREATER_THAN,
            ">=": BinaryOperator.GREATER_EQUAL,
            "in": BinaryOperator.IN,
            "not in": BinaryOperator.NOT_IN,
            "is": BinaryOperator.IS,
            "is not": BinaryOperator.IS_NOT,
            "like": BinaryOperator.LIKE,
            "not like": BinaryOperator.NOT_LIKE,
        }
        return mapping.get(op_text.lower(), BinaryOperator.EQUAL)

    @staticmethod
    def _parse_single_expression(text: str) -> _ExprNode:
        """Parse a single expression without logical operators."""
        text = text.strip()

        # Handle parentheses - remove the outer pair if it wraps the
        # entire expression
        if text.startswith("(") and text.endswith(")"):
            # Check if these parentheses actually wrap the whole expression
            paren_depth = 0
            for i, char in enumerate(text):
                if char == "(":
                    paren_depth += 1
                elif char == ")":
                    paren_depth -= 1
                    if paren_depth == 0 and i < len(text) - 1:
                        # Parentheses don't wrap the whole expression
                        break
            else:
                # Parentheses wrap the whole expression, remove them
                text = text[1:-1].strip()

        # --- CQL2 postfix operators ---
        cql2 = ExpressionParser._try_parse_cql2_operator(text)
        if cql2 is not None:
            return cql2

        # Check for relational operations (top-level, unquoted)
        for op in [">=", "<=", "<>", "!=", "=", ">", "<"]:
            if ExpressionParser._find_top_level(text, f" {op} ") != -1:
                return ExpressionParser._parse_relational_expression(text, op)

        # Handle string literals
        if (text.startswith('"') and text.endswith('"')) or (
            text.startswith("'") and text.endswith("'")
        ):
            result: Any = StringExpression(value=text[1:-1])
            return result

        # Handle function calls — CQL2 functions first
        if "(" in text and text.endswith(")"):
            cql2_func = ExpressionParser._try_parse_cql2_function(text)
            if cql2_func is not None:
                return cql2_func
            result = ExpressionParser._parse_function_call_from_text(text)
            return result

        # Handle curly-brace temporal literals: DATE{...}, TIMESTAMP{...}, INTERVAL{...}
        temporal_brace = ExpressionParser._try_parse_temporal_braces(text)
        if temporal_brace is not None:
            return temporal_brace

        # Handle hex number literals: 0xFF, 0xAB12 etc.
        if text.startswith("0x") or text.startswith("0X"):
            try:
                return ConstantExpression(value=int(text, 16))
            except ValueError:
                pass

        # Handle numbers
        try:
            if "." in text:
                result = ConstantExpression(value=float(text))
            else:
                result = ConstantExpression(value=int(text))
            return result
        except ValueError:
            pass

        # Handle boolean
        if text.lower() in ["true", "false"]:
            result = ConstantExpression(value=text.lower() == "true")
            return result

        # Handle member access
        if "." in text:
            result = ExpressionParser._parse_member_access_from_text(text)
            return result

        # Default: identifier
        result = IdentifierExpression(name=text)
        return result

    # =================================================================
    # CQL2 operator parsing helpers
    # =================================================================

    @staticmethod
    def _only_between_and(text: str) -> bool:
        """Return True if the only ' and ' in *text* is part of a BETWEEN."""
        tl = text.lower()
        m = re.search(r"\bbetween\b", tl)
        if not m:
            return False
        # Find the ' and ' after 'between'
        and_pos = tl.find(" and ", m.end())
        if and_pos == -1:
            return False
        # Check there's no other ' and ' or ' or ' outside the between
        rest = tl[and_pos + 5 :]
        return " and " not in rest and " or " not in rest

    @staticmethod
    def _try_parse_cql2_operator(text: str) -> _ExprNode | None:
        """Try to parse CQL2 postfix operators: BETWEEN, IN, LIKE, IS NULL.

        Returns the parsed Expression or None if no CQL2 operator was found.
        """
        tl = text.lower().strip()

        # --- IS NULL / IS NOT NULL (must precede other checks) ---
        m = re.match(r"^(.+?)\s+is\s+not\s+null\s*$", tl)
        if m:
            operand = ExpressionParser._parse_single_expression(text[: m.end(1)])
            return NotExpression(args=[IsNullPredicate(args=[operand])])
        m = re.match(r"^(.+?)\s+is\s+null\s*$", tl)
        if m:
            operand = ExpressionParser._parse_single_expression(text[: m.end(1)])
            return IsNullPredicate(args=[operand])

        # --- NOT BETWEEN x AND y ---
        m = re.match(r"^(.+?)\s+not\s+between\s+(.+?)\s+and\s+(.+)$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            lo = ExpressionParser._parse_single_expression(text[m.start(2) : m.end(2)])
            hi = ExpressionParser._parse_single_expression(text[m.start(3) :])
            return NotExpression(
                args=[IsBetweenPredicate(args=[val, lo, hi])],
            )

        # --- BETWEEN x AND y ---
        m = re.match(r"^(.+?)\s+between\s+(.+?)\s+and\s+(.+)$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            lo = ExpressionParser._parse_single_expression(text[m.start(2) : m.end(2)])
            hi = ExpressionParser._parse_single_expression(text[m.start(3) :])
            return IsBetweenPredicate(args=[val, lo, hi])

        # --- NOT IN (...) ---
        m = re.match(r"^(.+?)\s+not\s+in\s*\((.*)\)\s*$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            items = ExpressionParser._split_args(text[m.start(2) : m.end(2)])
            list_exprs = [ExpressionParser._parse_single_expression(i) for i in items]
            return NotExpression(
                args=[IsInListPredicate(args=[val, list_exprs])],
            )

        # --- IN (...) ---
        m = re.match(r"^(.+?)\s+in\s*\((.*)\)\s*$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            items = ExpressionParser._split_args(text[m.start(2) : m.end(2)])
            list_exprs = [ExpressionParser._parse_single_expression(i) for i in items]
            return IsInListPredicate(args=[val, list_exprs])

        # --- NOT LIKE 'pattern' ---
        m = re.match(r"^(.+?)\s+not\s+like\s+(.+)$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            pat = ExpressionParser._parse_single_expression(text[m.start(2) :])
            return NotExpression(
                args=[IsLikePredicate(op="like", args=[val, pat])],
            )

        # --- LIKE 'pattern' ---
        m = re.match(r"^(.+?)\s+like\s+(.+)$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            pat = ExpressionParser._parse_single_expression(text[m.start(2) :])
            return IsLikePredicate(op="like", args=[val, pat])

        # --- ILIKE 'pattern' ---
        m = re.match(r"^(.+?)\s+ilike\s+(.+)$", tl)
        if m:
            val = ExpressionParser._parse_single_expression(text[: m.end(1)])
            pat = ExpressionParser._parse_single_expression(text[m.start(2) :])
            return IsLikePredicate(op="ilike", args=[val, pat])

        return None

    @staticmethod
    def _try_parse_cql2_function(text: str) -> _ExprNode | None:
        """Try to parse CQL2 function-style expressions.

        Handles: spatial predicates, temporal predicates, array predicates,
        WKT geometry literals, BBOX, DATE, TIMESTAMP, INTERVAL.

        Returns the parsed Expression or None if not a CQL2 function.
        """
        paren_pos = text.index("(")
        func_name = text[:paren_pos].strip()
        func_lower = func_name.lower()

        # Extract the arguments substring (inside outermost parens)
        args_str = text[paren_pos + 1 : text.rfind(")")]

        # ── Spatial predicates: S_INTERSECTS(a, b) ──
        if func_lower in _SPATIAL_PREDICATES:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return SpatialPredicate(
                op=_v.SPATIAL_CANON.get(func_lower, func_lower), args=parsed_args
            )

        # ── S_RELATE(a, b, pattern) ──
        if func_lower == _SPATIAL_RELATE:
            args = ExpressionParser._split_args(args_str)
            if len(args) >= 3:
                parsed_a = ExpressionParser._parse_single_expression(args[0])
                parsed_b = ExpressionParser._parse_single_expression(args[1])
                pattern = args[2].strip().strip("'").strip('"')
                return SpatialRelatePredicate(
                    args=[parsed_a, parsed_b],
                    pattern=pattern,
                )

        # ── Temporal predicates: T_BEFORE(a, b) ──
        if func_lower in _TEMPORAL_PREDICATES:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return TemporalPredicate(op=func_lower, args=parsed_args)

        # ── Array predicates: A_CONTAINS(a, b) ──
        if func_lower in _ARRAY_PREDICATES:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return ArrayPredicate(op=func_lower, args=parsed_args)

        # ── DATE('...') ──
        if func_lower == "date":
            value = args_str.strip().strip("'").strip('"')
            return TemporalLiteral(temporal_type="date", value=value)

        # ── TIMESTAMP('...') ──
        if func_lower == "timestamp":
            value = args_str.strip().strip("'").strip('"')
            return TemporalLiteral(temporal_type="timestamp", value=value)

        # ── INTERVAL('start', 'end') ──
        if func_lower == "interval":
            parts = ExpressionParser._split_args(args_str)
            interval = [p.strip().strip("'").strip('"') for p in parts]
            return TemporalLiteral(temporal_type="interval", interval=interval)

        # ── BBOX(x1, y1, x2, y2[, x3, y3]) ──
        if func_lower == "bbox":
            parts = ExpressionParser._split_args(args_str)
            bbox_vals = [float(p.strip()) for p in parts]
            return BboxLiteral(bbox=bbox_vals)

        # ── WKT geometry literals: POINT(x y), POLYGON((...)), etc. ──
        if func_lower in _WKT_TYPES:
            geom_type = _WKT_TO_GEOJSON[func_lower]
            coords = ExpressionParser._parse_wkt_coordinates(func_lower, args_str)
            if geom_type == "GeometryCollection":
                # GeometryCollection contains sub-geometries
                return GeometryLiteral(geom_type=geom_type, geometries=coords)
            return GeometryLiteral(geom_type=geom_type, coordinates=coords)

        # ── Text operation predicates: CONTAINS(a, b), STARTSWITH, ENDSWITH ──
        if func_lower in _TEXT_OP_PREDICATES:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return TextOpPredicate(
                op=_v.TEXT_OP_CANON.get(func_lower, func_lower), args=parsed_args
            )

        # ── Character expression functions ──
        # CASEI(expr), ACCENTI(expr)
        if func_lower in ("casei", "accenti"):
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            if func_lower == "casei":
                return CaseiExpression(args=parsed_args)
            return AccentiExpression(args=parsed_args)

        # LOWERCASE(expr), UPPERCASE(expr)
        if func_lower in ("lowercase", "uppercase"):
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return LowerUpperCaseExpression(
                op=_v.LOWER_UPPER_CANON.get(func_lower, func_lower), args=parsed_args
            )

        # CONCATENATE(a, b, ...)
        if func_lower == "concatenate":
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return ConcatenateExpression(args=parsed_args)

        # SUBSTITUTE(string, pattern, replacement)
        if func_lower == "substitute":
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return SubstituteExpression(args=parsed_args)

        # FORMAT(format_string, ...)
        if func_lower == "format":
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return FormatExpression(args=parsed_args)

        # ── Geometry manipulation functions ──
        # S_BUFFER(geom, distance)
        if func_lower in _GEOM_BUFFER:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return GeometryBuffer(op="s_buffer", args=parsed_args)

        # S_CONVEXHULL(geom), S_ENVELOPE(geom)
        if func_lower in _GEOM_MANIPULATION_UNARY:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return GeometryManipulationUnary(
                op=_v.GEOM_UNARY_CANON.get(func_lower, func_lower), args=parsed_args
            )

        # S_INTERSECTION(a, b), S_UNION(a, b), S_DIFFERENCE(a, b), S_SYMDIFFERENCE(a, b)
        if func_lower in _GEOM_MANIPULATION_BINARY:
            args = ExpressionParser._split_args(args_str)
            parsed_args = [ExpressionParser._parse_single_expression(a) for a in args]
            return GeometryManipulationBinary(
                op=_v.GEOM_BINARY_CANON.get(func_lower, func_lower), args=parsed_args
            )

        return None

    # =================================================================
    # WKT coordinate parsing
    # =================================================================

    @staticmethod
    def _parse_wkt_coordinates(geom_lower: str, args_str: str):
        """Parse WKT coordinate content into GeoJSON-style coordinate arrays."""
        args_str = args_str.strip()

        if geom_lower == "point":
            # POINT(x y) or POINT(x y z)
            nums = args_str.split()
            return [float(n) for n in nums]

        if geom_lower == "linestring":
            # LINESTRING(x1 y1, x2 y2, ...)
            return ExpressionParser._parse_coord_list(args_str)

        if geom_lower == "polygon":
            # POLYGON((x1 y1, x2 y2, ...), (hole x1 y1, ...))
            return ExpressionParser._parse_ring_list(args_str)

        if geom_lower == "multipoint":
            # MULTIPOINT((x1 y1), (x2 y2)) or MULTIPOINT(x1 y1, x2 y2)
            if "(" in args_str:
                rings = ExpressionParser._extract_parens_groups(args_str)
                return [ExpressionParser._parse_coord_list(r)[0] for r in rings]
            return ExpressionParser._parse_coord_list(args_str)

        if geom_lower == "multilinestring":
            # MULTILINESTRING((x1 y1, x2 y2), (x3 y3, x4 y4))
            rings = ExpressionParser._extract_parens_groups(args_str)
            return [ExpressionParser._parse_coord_list(r) for r in rings]

        if geom_lower == "multipolygon":
            # MULTIPOLYGON(((x1 y1, ...)), ((x1 y1, ...)))
            # Each element is a polygon (list of rings)
            outer = ExpressionParser._extract_parens_groups(args_str)
            return [ExpressionParser._parse_ring_list(o) for o in outer]

        if geom_lower == "geometrycollection":
            # GEOMETRYCOLLECTION(POINT(...), LINESTRING(...))
            # Return list of GeometryLiteral sub-geometries
            sub_geoms = []
            # Use a simple state machine to split top-level sub-geometries
            depth = 0
            current = []
            for ch in args_str:
                if ch == "(":
                    depth += 1
                    current.append(ch)
                elif ch == ")":
                    depth -= 1
                    current.append(ch)
                elif ch == "," and depth == 0:
                    sub_text = "".join(current).strip()
                    if sub_text:
                        parsed = ExpressionParser._try_parse_cql2_function(
                            sub_text + ")"[0:0] if False else sub_text
                        )
                        # Re-parse as full expression — it's a WKT sub-geometry
                        parsed = ExpressionParser._try_parse_cql2_function(sub_text)
                        if parsed and isinstance(parsed, GeometryLiteral):
                            sub_geoms.append(parsed)
                    current = []
                else:
                    current.append(ch)
            last = "".join(current).strip()
            if last:
                parsed = ExpressionParser._try_parse_cql2_function(last)
                if parsed and isinstance(parsed, GeometryLiteral):
                    sub_geoms.append(parsed)
            return sub_geoms

        return []

    @staticmethod
    def _parse_coord_list(text: str) -> list:
        """Parse 'x1 y1, x2 y2, ...' into [[x1,y1], [x2,y2], ...]."""
        coords = []
        for pair in text.split(","):
            nums = pair.strip().split()
            if nums:
                coords.append([float(n) for n in nums])
        return coords

    @staticmethod
    def _parse_ring_list(text: str) -> list:
        """Parse '(x1 y1, x2 y2), (x3 y3, ...)' into rings."""
        groups = ExpressionParser._extract_parens_groups(text)
        return [ExpressionParser._parse_coord_list(g) for g in groups]

    @staticmethod
    def _extract_parens_groups(text: str) -> list:
        """Extract content of each top-level (...) group."""
        groups = []
        depth = 0
        current = []
        for ch in text:
            if ch == "(":
                if depth > 0:
                    current.append(ch)
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    groups.append("".join(current))
                    current = []
                elif depth > 0:
                    current.append(ch)
            elif depth > 0:
                current.append(ch)
        return groups

    @staticmethod
    def _unwrap_parens(text: str) -> str:
        """Strip one pair of parens iff it wraps the whole expression.

        ``(a and b)`` -> ``a and b`` ; ``f(x) = g(y)`` -> unchanged ;
        ``(a) or (b)`` -> unchanged.
        """
        while len(text) >= 2 and text[0] == "(" and text[-1] == ")":
            depth = 0
            wraps = True
            for i, ch in enumerate(text):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and i != len(text) - 1:
                        wraps = False
                        break
            if not wraps:
                return text
            text = text[1:-1].strip()
        return text

    @staticmethod
    def _iter_top_level(text: str) -> Iterator[tuple[int, str]]:
        """Yield ``(index, char)`` for top-level characters of *text*.

        "Top level" means bracket depth 0 and outside any
        single/double-quoted string literal.

        The hand-rolled scanners in this module historically tracked only
        ``()``/``{}`` nesting, so ``name = 'a and b'`` was mis-split on the
        ``and`` *inside the string literal*. Routing them through this
        helper makes them quote-aware.
        """
        depth = 0
        in_single = in_double = False
        for i, ch in enumerate(text):
            if ch == "'" and not in_double:
                in_single = not in_single
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                continue
            if in_single or in_double:
                continue
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif depth == 0:
                yield i, ch

    @staticmethod
    def _find_top_level(text: str, needle: str, *, last: bool = True) -> int:
        """Index of *needle* in *text* at bracket depth 0 and outside quotes, or -1.

        Case-insensitive. ``last=True`` returns the rightmost match (for
        left-associative operator splitting).
        """
        nl = needle.lower()
        n = len(needle)
        found = -1
        for i, _ in ExpressionParser._iter_top_level(text):
            if text[i : i + n].lower() == nl:
                if not last:
                    return i
                found = i
        return found

    @staticmethod
    def _split_args(text: str) -> list:
        """Split comma-separated arguments respecting parentheses, braces and quotes."""
        args = []
        depth = 0
        in_single = False
        in_double = False
        current = []
        for ch in text:
            if ch == "'" and not in_double:
                in_single = not in_single
                current.append(ch)
            elif ch == '"' and not in_single:
                in_double = not in_double
                current.append(ch)
            elif not in_single and not in_double:
                if ch in ("(", "{"):
                    depth += 1
                    current.append(ch)
                elif ch in (")", "}"):
                    depth -= 1
                    current.append(ch)
                elif ch == "," and depth == 0:
                    args.append("".join(current).strip())
                    current = []
                else:
                    current.append(ch)
            else:
                current.append(ch)
        last = "".join(current).strip()
        if last:
            args.append(last)
        return args

    @staticmethod
    def _try_parse_temporal_braces(text: str) -> _ExprNode | None:
        """Try to parse curly-brace temporal literals.

        DATE{...}, TIMESTAMP{...}, INTERVAL{...}.

        Returns the parsed TemporalLiteral, or None if the text is not a
        temporal literal.
        """
        text = text.strip()
        brace_pos = text.find("{")
        if brace_pos == -1 or not text.endswith("}"):
            return None
        func_name = text[:brace_pos].strip()
        func_lower = func_name.lower()
        if func_lower not in _TEMPORAL_LITERAL_NAMES:
            return None
        inner = text[brace_pos + 1 : -1]  # content inside { }
        if func_lower == "date":
            value = inner.strip().strip("'").strip('"')
            return TemporalLiteral(temporal_type="date", value=value)
        elif func_lower == "timestamp":
            value = inner.strip().strip("'").strip('"')
            return TemporalLiteral(temporal_type="timestamp", value=value)
        elif func_lower == "interval":
            parts = ExpressionParser._split_args(inner)
            interval = [p.strip().strip("'").strip('"') for p in parts]
            return TemporalLiteral(temporal_type="interval", interval=interval)
        return None
