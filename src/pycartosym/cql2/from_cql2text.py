"""CQL2-Text -> ``cql2.model`` expression models via the standalone grammar.

Walks ``CQL2Text.g4`` (generated into ``pycartosym.grammar.generated.cql2text``).
This is a **tree-walker**, not a text scanner: every construct is read off
the parse tree the grammar already built (spatial/temporal/array predicates,
WKT geometry, DATE/TIMESTAMP/INTERVAL, CASEI/ACCENTI, BETWEEN/LIKE/IN/IS
NULL) rather than re-scanned from source-text slices. This is now the
primary path for :mod:`.from_text`'s ``_parse_expression_text`` (and thus
``cql2.parse_text``) — see that module's docstring for the fallback chain
kept as a safety net for constructs outside CQL2-Text proper (the
hand-rolled scanner this tree-walker used to fall back to has since been
removed).

Model choice mirrors :class:`.from_text.ExpressionParser`, except that
temporal and array operator names are canonicalised here (the fallback
scanner keeps the raw lower-cased name):

* AND / OR / arithmetic / comparison (``= != < <= > >=``) -> the generic
  :class:`~.model.BinaryOperationExpression` / :class:`~.model.UnaryOperationExpression`
  (a leading/standalone boolean NOT), matching the CartoSym-CSS ``expression``
  tree-walker (:meth:`.from_text.ExpressionParser.parse_expression_ctx`).
* BETWEEN / LIKE / IN / IS NULL -> the dedicated CQL2-JSON predicate models
  (:class:`~.model.IsBetweenPredicate` etc.), negation wrapped in
  :class:`~.model.NotExpression` — also matching that tree-walker.
* Spatial / temporal / array predicates, WKT geometry, DATE / TIMESTAMP /
  INTERVAL, CASEI / ACCENTI, and the geometry-manipulation / character
  functions -> the dedicated CQL2 models (:mod:`.model`), built directly
  from the grammar's own structured sub-rules (``pointText`` / ``point`` /
  ``linearRingText`` for WKT, ``instantParameter`` for INTERVAL bounds…)
  instead of :meth:`.from_text.ExpressionParser._try_parse_cql2_function`'s
  text re-scan.
* ``S_RELATE(a, b, pattern)`` -> :class:`~.model.SpatialRelatePredicate`,
  whose ``pattern`` field validator already delegates to
  :func:`pycartosym.models.de9im.is_valid_de9im_pattern` — real DE-9IM
  pattern validation falls out of using that model directly, not the
  previously-unvalidated opaque string the scanner produced.

Property/function-name dispatch (which identifiers are CQL2 predicates vs.
plain function calls) reuses :mod:`.vocab` — the single source of truth
derived from the Pydantic models, not a hand-written list.
"""

from __future__ import annotations

from typing import Any, cast

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from ..grammar.generated.cql2text import CQL2TextLexer, CQL2TextParser
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
    ConstantExpression,
    Expression,
    FormatExpression,
    FunctionCallExpression,
    GeometryBuffer,
    GeometryLiteral,
    GeometryManipulationBinary,
    GeometryManipulationUnary,
    IdentifierExpression,
    IsBetweenPredicate,
    IsInListPredicate,
    IsLikePredicate,
    IsNullPredicate,
    LowerUpperCaseExpression,
    NotExpression,
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

# See the module docstring on `_ExprNode` in `.from_text` — a walker
# method's return type is loose by necessity (many concrete node types,
# occasionally `None` or a bare `list`).
_ExprNode = Any


class Cql2TextSyntaxError(ValueError):
    """*text* is not valid CQL2-Text per the ``CQL2Text.g4`` grammar."""


class _CollectingErrorListener(ErrorListener):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(  # noqa: N802 - ANTLR's own method name
        self, recognizer, offending_symbol, line, column, msg, e
    ) -> None:
        self.errors.append(f"{line}:{column} {msg}")


def parse_cql2_text(text: str) -> _ExprNode:
    """Parse a CQL2-Text string into a ``cql2.model`` expression tree.

    Raises :class:`Cql2TextSyntaxError` if *text* is not valid CQL2-Text.
    """
    lexer = CQL2TextLexer(InputStream(text))
    lexer.removeErrorListeners()
    lexer_errors = _CollectingErrorListener()
    lexer.addErrorListener(lexer_errors)

    parser = CQL2TextParser(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser_errors = _CollectingErrorListener()
    parser.addErrorListener(parser_errors)

    tree = parser.cql2Text()
    errors = lexer_errors.errors + parser_errors.errors
    if errors:
        raise Cql2TextSyntaxError(f"{text!r} is not valid CQL2-Text: {errors}")
    return Cql2TextTreeWalker.boolean_expression(tree.booleanExpression())


class Cql2TextTreeWalker:
    """Walks a ``CQL2TextParser`` parse tree into ``cql2.model`` expressions."""

    # -- boolean layer (booleanExpression / booleanTerm / booleanFactor) ----

    @staticmethod
    def boolean_expression(ctx) -> _ExprNode:
        """``booleanTerm (OR booleanTerm)*`` -> left-associative OR chain."""
        return Cql2TextTreeWalker._left_fold(
            ctx.booleanTerm(), Cql2TextTreeWalker.boolean_term, BinaryOperator.OR
        )

    @staticmethod
    def boolean_term(ctx) -> _ExprNode:
        """``booleanFactor (AND booleanFactor)*`` -> left-associative AND chain."""
        return Cql2TextTreeWalker._left_fold(
            ctx.booleanFactor(), Cql2TextTreeWalker.boolean_factor, BinaryOperator.AND
        )

    @staticmethod
    def boolean_factor(ctx) -> _ExprNode:
        """``NOT* primary`` -> one ``UnaryOperationExpression`` per ``NOT``."""
        node = Cql2TextTreeWalker.primary(ctx.primary())
        for _ in ctx.NOT():
            node = UnaryOperationExpression(operator=UnaryOperator.NOT, operand=node)
        return node

    @staticmethod
    def _left_fold(items: list, walk, operator: BinaryOperator) -> _ExprNode:
        result = walk(items[0])
        for item in items[1:]:
            result = BinaryOperationExpression(
                left=result, operator=operator, right=walk(item)
            )
        return result

    # -- primary / predicateTail ---------------------------------------------

    @staticmethod
    def primary(ctx) -> _ExprNode:
        """Dispatch a ``primary`` alternative by which accessor is set."""
        if ctx.spatialPredicate() is not None:
            return Cql2TextTreeWalker.spatial_predicate(ctx.spatialPredicate())
        if ctx.temporalPredicate() is not None:
            return Cql2TextTreeWalker.temporal_predicate(ctx.temporalPredicate())
        if ctx.arrayPredicate() is not None:
            return Cql2TextTreeWalker.array_predicate(ctx.arrayPredicate())
        if ctx.booleanExpression() is not None:
            return Cql2TextTreeWalker.boolean_expression(ctx.booleanExpression())
        left = Cql2TextTreeWalker.operand(ctx.operand())
        tail = ctx.predicateTail()
        if tail is None:
            return left
        return Cql2TextTreeWalker.predicate_tail(tail, left)

    @staticmethod
    def predicate_tail(ctx, left: _ExprNode) -> _ExprNode:
        """Dispatch a ``predicateTail`` labelled alternative to its model."""
        from ..grammar.generated.cql2text.CQL2TextParser import CQL2TextParser as _P

        if isinstance(ctx, _P.ComparisonTailContext):
            op = Cql2TextTreeWalker._comparison_operator(ctx.comparisonOperator())
            right = Cql2TextTreeWalker.operand(ctx.operand())
            return BinaryOperationExpression(left=left, operator=op, right=right)

        if isinstance(ctx, _P.LikeTailContext):
            pattern = Cql2TextTreeWalker.character_clause(ctx.characterClause())
            pred: _ExprNode = IsLikePredicate(op="like", args=[left, pattern])
            return NotExpression(args=[pred]) if ctx.NOT() is not None else pred

        if isinstance(ctx, _P.BetweenTailContext):
            lo, hi = ctx.arithmeticExpr()
            pred = IsBetweenPredicate(
                args=[
                    left,
                    Cql2TextTreeWalker.arithmetic_expr(lo),
                    Cql2TextTreeWalker.arithmetic_expr(hi),
                ]
            )
            return NotExpression(args=[pred]) if ctx.NOT() is not None else pred

        if isinstance(ctx, _P.InTailContext):
            items = [Cql2TextTreeWalker.operand(o) for o in ctx.inList().operand()]
            pred = IsInListPredicate(args=[left, items])
            return NotExpression(args=[pred]) if ctx.NOT() is not None else pred

        if isinstance(ctx, _P.IsNullTailContext):
            pred = IsNullPredicate(args=[left])
            return NotExpression(args=[pred]) if ctx.NOT() is not None else pred

        raise Cql2TextSyntaxError(f"unhandled predicateTail alternative: {ctx!r}")

    _COMPARISON_OPS = {
        "EQ": BinaryOperator.EQUAL,
        "NEQ": BinaryOperator.NOT_EQUAL,
        "LTEQ": BinaryOperator.LESS_EQUAL,
        "GTEQ": BinaryOperator.GREATER_EQUAL,
        "LT": BinaryOperator.LESS_THAN,
        "GT": BinaryOperator.GREATER_THAN,
    }

    @staticmethod
    def _comparison_operator(ctx) -> BinaryOperator:
        for token_name, operator in Cql2TextTreeWalker._COMPARISON_OPS.items():
            if getattr(ctx, token_name)() is not None:
                return operator
        raise Cql2TextSyntaxError(f"unhandled comparisonOperator: {ctx.getText()!r}")

    # -- spatial / temporal / array predicates -------------------------------

    @staticmethod
    def spatial_predicate(ctx) -> SpatialPredicate:
        """``spatialFunction '(' operand ',' operand ')'`` -> ``SpatialPredicate``."""
        op = ctx.spatialFunction().getText().lower()
        args = [Cql2TextTreeWalker.operand(o) for o in ctx.operand()]
        return SpatialPredicate(op=_v.SPATIAL_CANON.get(op, op), args=args)

    @staticmethod
    def temporal_predicate(ctx) -> TemporalPredicate:
        """``temporalFunction '(' operand ',' operand ')'`` -> ``TemporalPredicate``."""
        op = ctx.temporalFunction().getText().lower()
        args = [Cql2TextTreeWalker.operand(o) for o in ctx.operand()]
        return TemporalPredicate(op=_v.TEMPORAL_CANON.get(op, op), args=args)

    @staticmethod
    def array_predicate(ctx) -> ArrayPredicate:
        """``arrayFunction '(' operand ',' operand ')'`` -> ``ArrayPredicate``."""
        op = ctx.arrayFunction().getText().lower()
        args = [Cql2TextTreeWalker.operand(o) for o in ctx.operand()]
        return ArrayPredicate(op=_v.ARRAY_CANON.get(op, op), args=args)

    # -- arithmetic layer (operand / arithmeticExpr / …/ arithmeticFactor) --

    @staticmethod
    def operand(ctx) -> _ExprNode:
        """``operand: arithmeticExpr`` -> the arithmetic-precedence chain."""
        return Cql2TextTreeWalker.arithmetic_expr(ctx.arithmeticExpr())

    _ADD_OPS = {"+": BinaryOperator.ADD, "-": BinaryOperator.SUBTRACT}
    _MUL_OPS = {
        "*": BinaryOperator.MULTIPLY,
        "/": BinaryOperator.DIVIDE,
        "div": BinaryOperator.INTEGER_DIVIDE,
        "%": BinaryOperator.MODULO,
    }

    @staticmethod
    def arithmetic_expr(ctx) -> _ExprNode:
        """``arithmeticTerm ((PLUS|MINUS) arithmeticTerm)*`` -> left-fold chain."""
        return Cql2TextTreeWalker._fold_children(
            ctx, Cql2TextTreeWalker.arithmetic_term, Cql2TextTreeWalker._ADD_OPS
        )

    @staticmethod
    def arithmetic_term(ctx) -> _ExprNode:
        """``powerTerm ((MUL|SLASH|IDIV|MOD) powerTerm)*`` -> left-fold chain."""
        return Cql2TextTreeWalker._fold_children(
            ctx, Cql2TextTreeWalker.power_term, Cql2TextTreeWalker._MUL_OPS
        )

    @staticmethod
    def power_term(ctx) -> _ExprNode:
        """``arithmeticFactor (POW arithmeticFactor)?`` -> at most one POW."""
        return Cql2TextTreeWalker._fold_children(
            ctx,
            Cql2TextTreeWalker.arithmetic_factor,
            {"^": BinaryOperator.POWER},
        )

    @staticmethod
    def _fold_children(ctx, walk_operand, op_table: dict[str, BinaryOperator]):
        """Left-fold a ``term (OP term)*``-shaped rule's children.

        The grammar keeps children in source order, alternating sub-rule /
        operator-terminal / sub-rule / …, so odd-indexed children are always
        the operator tokens — this avoids re-deriving interleaved order from
        per-token accessor lists (``ctx.PLUS()``/``ctx.MINUS()`` are each
        returned as a separate, non-interleaved list).
        """
        children = ctx.children
        result = walk_operand(children[0])
        i = 1
        while i < len(children):
            operator = op_table[children[i].getText().lower()]
            result = BinaryOperationExpression(
                left=result, operator=operator, right=walk_operand(children[i + 1])
            )
            i += 2
        return result

    @staticmethod
    def arithmetic_factor(ctx) -> _ExprNode:
        """``'(' arithmeticExpr ')' | MINUS? atom``."""
        if ctx.LPAR() is not None:
            return Cql2TextTreeWalker.arithmetic_expr(ctx.arithmeticExpr())
        node = Cql2TextTreeWalker.atom(ctx.atom())
        if ctx.MINUS() is not None:
            return UnaryOperationExpression(operator=UnaryOperator.MINUS, operand=node)
        return node

    # -- atom -----------------------------------------------------------------

    @staticmethod
    def atom(ctx) -> _ExprNode:
        """Dispatch an ``atom`` alternative by which accessor is set."""
        if ctx.geometryLiteral() is not None:
            return Cql2TextTreeWalker.geometry_literal(ctx.geometryLiteral())
        if ctx.temporalInstant() is not None:
            return Cql2TextTreeWalker.temporal_instant(ctx.temporalInstant())
        if ctx.characterClause() is not None:
            return Cql2TextTreeWalker.character_clause(ctx.characterClause())
        if ctx.NUMERIC_LITERAL() is not None:
            return Cql2TextTreeWalker._numeric_constant(ctx.NUMERIC_LITERAL().getText())
        if ctx.booleanLiteral() is not None:
            return ConstantExpression(value=ctx.booleanLiteral().TRUE() is not None)
        if ctx.propertyName() is not None:
            return IdentifierExpression(
                name=Cql2TextTreeWalker._property_name(ctx.propertyName())
            )
        if ctx.functionCall() is not None:
            return Cql2TextTreeWalker.function_call(ctx.functionCall())
        if ctx.arrayExpr() is not None:
            return Cql2TextTreeWalker.array_expr(ctx.arrayExpr())
        raise Cql2TextSyntaxError(f"unhandled atom alternative: {ctx.getText()!r}")

    @staticmethod
    def _numeric_constant(text: str) -> ConstantExpression:
        is_float = "." in text or "e" in text.lower()
        value: int | float = float(text) if is_float else int(text)
        return ConstantExpression(value=value)

    @staticmethod
    def _property_name(ctx) -> str:
        if ctx.QUOTED_IDENTIFIER() is not None:
            return str(ctx.QUOTED_IDENTIFIER().getText())[1:-1]
        return str(ctx.IDENTIFIER().getText())

    @staticmethod
    def _unescape_string(literal: str) -> str:
        r"""``'...'`` (with ``''``/``\'`` escapes) -> the unescaped Python string."""
        return literal[1:-1].replace("''", "'").replace("\\'", "'")

    @staticmethod
    def array_expr(ctx) -> ArrayExpression:
        """``'(' ')' | '(' operand (',' operand)+ ')'`` -> ``ArrayExpression``."""
        operands = ctx.operand()
        return ArrayExpression(
            elements=[Cql2TextTreeWalker.operand(o) for o in operands]
        )

    # -- character clause (CASEI / ACCENTI / STRING) -------------------------

    @staticmethod
    def character_clause(ctx) -> _ExprNode:
        """``CASEI(arg) | ACCENTI(arg) | STRING`` -> the matching model."""
        if ctx.CASEI() is not None:
            return CaseiExpression(
                args=[Cql2TextTreeWalker.character_clause_arg(ctx.characterClauseArg())]
            )
        if ctx.ACCENTI() is not None:
            return AccentiExpression(
                args=[Cql2TextTreeWalker.character_clause_arg(ctx.characterClauseArg())]
            )
        return StringExpression(
            value=Cql2TextTreeWalker._unescape_string(ctx.STRING().getText())
        )

    @staticmethod
    def character_clause_arg(ctx) -> _ExprNode:
        """``characterClause | propertyName | functionCall``."""
        if ctx.characterClause() is not None:
            return Cql2TextTreeWalker.character_clause(ctx.characterClause())
        if ctx.propertyName() is not None:
            return IdentifierExpression(
                name=Cql2TextTreeWalker._property_name(ctx.propertyName())
            )
        return Cql2TextTreeWalker.function_call(ctx.functionCall())

    # -- WKT geometry literals + BBOX -----------------------------------------

    @staticmethod
    def geometry_literal(ctx) -> GeometryLiteral | BboxLiteral:
        """Dispatch a ``geometryLiteral`` alternative by which accessor is set."""
        if ctx.pointTaggedText() is not None:
            point = ctx.pointTaggedText().pointText().point()
            return GeometryLiteral(
                geom_type="Point", coordinates=Cql2TextTreeWalker._point(point)
            )
        if ctx.linestringTaggedText() is not None:
            points = ctx.linestringTaggedText().lineStringText().point()
            return GeometryLiteral(
                geom_type="LineString",
                coordinates=[Cql2TextTreeWalker._point(p) for p in points],
            )
        if ctx.polygonTaggedText() is not None:
            rings = ctx.polygonTaggedText().polygonText().linearRingText()
            return GeometryLiteral(
                geom_type="Polygon",
                coordinates=[Cql2TextTreeWalker._linear_ring(r) for r in rings],
            )
        if ctx.multipointTaggedText() is not None:
            points = ctx.multipointTaggedText().multiPointText().pointText()
            return GeometryLiteral(
                geom_type="MultiPoint",
                coordinates=[Cql2TextTreeWalker._point(p.point()) for p in points],
            )
        if ctx.multilinestringTaggedText() is not None:
            mls = ctx.multilinestringTaggedText().multiLineStringText()
            lines = mls.lineStringText()
            return GeometryLiteral(
                geom_type="MultiLineString",
                coordinates=[
                    [Cql2TextTreeWalker._point(p) for p in line.point()]
                    for line in lines
                ],
            )
        if ctx.multipolygonTaggedText() is not None:
            polygons = ctx.multipolygonTaggedText().multiPolygonText().polygonText()
            return GeometryLiteral(
                geom_type="MultiPolygon",
                coordinates=[
                    [Cql2TextTreeWalker._linear_ring(r) for r in poly.linearRingText()]
                    for poly in polygons
                ],
            )
        if ctx.geometryCollectionTaggedText() is not None:
            geoms = (
                ctx.geometryCollectionTaggedText()
                .geometryCollectionText()
                .geometryLiteral()
            )
            return GeometryLiteral(
                geom_type="GeometryCollection",
                geometries=[Cql2TextTreeWalker.geometry_literal(g) for g in geoms],
            )
        if ctx.bboxTaggedText() is not None:
            numbers = ctx.bboxTaggedText().bboxText().signedNumber()
            return BboxLiteral(
                bbox=[Cql2TextTreeWalker._signed_number(n) for n in numbers]
            )
        raise Cql2TextSyntaxError(
            f"unhandled geometryLiteral alternative: {ctx.getText()!r}"
        )

    @staticmethod
    def _point(ctx) -> list[float]:
        return [Cql2TextTreeWalker._signed_number(n) for n in ctx.signedNumber()]

    @staticmethod
    def _linear_ring(ctx) -> list[list[float]]:
        return [Cql2TextTreeWalker._point(p) for p in ctx.point()]

    @staticmethod
    def _signed_number(ctx) -> float:
        value = float(ctx.NUMERIC_LITERAL().getText())
        return -value if ctx.MINUS() is not None else value

    # -- temporal instants (DATE / TIMESTAMP / INTERVAL) ---------------------

    @staticmethod
    def temporal_instant(ctx) -> TemporalLiteral:
        """``dateInstant | timestampInstant | intervalInstant`` -> literal model."""
        if ctx.dateInstant() is not None:
            return TemporalLiteral(
                temporal_type="date",
                value=Cql2TextTreeWalker._unescape_string(
                    ctx.dateInstant().STRING().getText()
                ),
            )
        if ctx.timestampInstant() is not None:
            return TemporalLiteral(
                temporal_type="timestamp",
                value=Cql2TextTreeWalker._unescape_string(
                    ctx.timestampInstant().STRING().getText()
                ),
            )
        interval_ctx = ctx.intervalInstant()
        bounds = [
            Cql2TextTreeWalker._instant_parameter(p)
            for p in interval_ctx.instantParameter()
        ]
        return TemporalLiteral(temporal_type="interval", interval=bounds)

    @staticmethod
    def _instant_parameter(ctx) -> str | Expression:
        if ctx.STRING() is not None:
            return Cql2TextTreeWalker._unescape_string(ctx.STRING().getText())
        if ctx.propertyName() is not None:
            return IdentifierExpression(
                name=Cql2TextTreeWalker._property_name(ctx.propertyName())
            )
        return cast(Expression, Cql2TextTreeWalker.function_call(ctx.functionCall()))

    # -- function calls: S_RELATE, geometry manipulation, character/text ----

    @staticmethod
    def function_call(ctx) -> _ExprNode:
        """Turn ``IDENTIFIER '(' argumentList? ')'`` into the matching CQL2 model.

        Only names that are *not* dedicated grammar keywords reach this
        rule (the spatial/temporal/array predicates the grammar lists, WKT
        tags, CASEI/ACCENTI, DATE/TIMESTAMP/INTERVAL all have their own
        grammar productions) — so this covers ``S_RELATE``, the two
        spatial predicates the model supports but ``spatialFunction``
        omits (``S_COVERS``/``S_COVEREDBY``; the temporal/array branches
        below are defensive, since their grammar lists match the model's),
        the geometry-manipulation functions
        (``S_BUFFER``, ``S_INTERSECTION``…), text-op predicates
        (``CONTAINS``/``STARTSWITH``/``ENDSWITH``), the remaining character
        functions (``LOWERCASE``/``CONCATENATE``/…), plus any other
        identifier — dispatch is by lower-cased name, from :mod:`.vocab`.
        """
        name = ctx.IDENTIFIER().getText()
        lname = name.lower()
        arg_list = ctx.argumentList()
        arg_ctxs = arg_list.operand() if arg_list is not None else []
        args = [Cql2TextTreeWalker.operand(a) for a in arg_ctxs]

        if lname == _v.SPATIAL_RELATE:
            if len(args) != 3:
                raise Cql2TextSyntaxError(
                    "S_RELATE requires 3 arguments (geomA, geomB, pattern), "
                    f"got {len(args)}"
                )
            pattern_arg = args[2]
            if not isinstance(pattern_arg, StringExpression):
                raise Cql2TextSyntaxError(
                    "S_RELATE's pattern argument must be a literal string, "
                    f"got {pattern_arg!r}"
                )
            return SpatialRelatePredicate(args=args[:2], pattern=pattern_arg.value)
        if lname in _v.SPATIAL_PREDICATES:
            return SpatialPredicate(op=_v.SPATIAL_CANON.get(lname, lname), args=args)
        if lname in _v.TEMPORAL_PREDICATES:
            return TemporalPredicate(op=_v.TEMPORAL_CANON.get(lname, lname), args=args)
        if lname in _v.ARRAY_PREDICATES:
            return ArrayPredicate(op=_v.ARRAY_CANON.get(lname, lname), args=args)
        if lname in _v.TEXT_OP_PREDICATES:
            return TextOpPredicate(op=_v.TEXT_OP_CANON.get(lname, lname), args=args)
        if lname == "concatenate":
            return ConcatenateExpression(args=args)
        if lname == "substitute":
            return SubstituteExpression(args=args)
        if lname == "format":
            return FormatExpression(args=args)
        if lname in ("lowercase", "uppercase"):
            return LowerUpperCaseExpression(
                op=_v.LOWER_UPPER_CANON.get(lname, lname), args=args
            )
        if lname in _v.GEOM_BUFFER:
            return GeometryBuffer(op="s_buffer", args=args)
        if lname in _v.GEOM_MANIPULATION_UNARY:
            return GeometryManipulationUnary(
                op=_v.GEOM_UNARY_CANON.get(lname, lname), args=args
            )
        if lname in _v.GEOM_MANIPULATION_BINARY:
            return GeometryManipulationBinary(
                op=_v.GEOM_BINARY_CANON.get(lname, lname), args=args
            )
        return FunctionCallExpression(function_name=name, arguments=args)
