"""``cql2.from_cql2text`` — the CQL2-Text tree-walker built on ``CQL2Text.g4``.

Structural unit tests per construct, plus a full run over the official
120-example corpus (``tests/fixtures/cql2/text/``, see
``test_cql2text_grammar_corpus.py`` for provenance) already used to
grammar-conformance-test ``CQL2Text.g4`` itself.

This module is also exercised indirectly via ``pycartosym.cql2.parse_text``
(``cql2/from_text.py``), which now tries this tree-walker first — see
``test_cql2_parser.py``/``test_cql2_extended.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pycartosym.cql2.from_cql2text import Cql2TextSyntaxError, parse_cql2_text
from pycartosym.cql2.model import (
    AccentiExpression,
    ArrayExpression,
    ArrayPredicate,
    BboxLiteral,
    BinaryOperationExpression,
    BinaryOperator,
    CaseiExpression,
    ConstantExpression,
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
    NotExpression,
    SpatialPredicate,
    SpatialRelatePredicate,
    StringExpression,
    TemporalLiteral,
    TemporalPredicate,
    TextOpPredicate,
    UnaryOperationExpression,
    UnaryOperator,
)

_CORPUS = Path(__file__).parent / "fixtures" / "cql2" / "text"
_FIXTURES = sorted(_CORPUS.glob("*.txt"))


@pytest.mark.parametrize("path", _FIXTURES, ids=[p.name for p in _FIXTURES])
def test_official_corpus(path: Path):
    text = path.read_text(encoding="utf-8")
    model = parse_cql2_text(text)
    assert model is not None


def test_invalid_syntax_raises():
    with pytest.raises(Cql2TextSyntaxError):
        parse_cql2_text("a = b =")


# ── boolean layer: AND / OR / NOT precedence ────────────────────────────────


def test_and_binds_tighter_than_or():
    # a OR (b AND c)
    model = parse_cql2_text("a = 1 or b = 2 and c = 3")
    assert isinstance(model, BinaryOperationExpression)
    assert model.operator == BinaryOperator.OR
    assert isinstance(model.right, BinaryOperationExpression)
    assert model.right.operator == BinaryOperator.AND


def test_and_chain_is_left_associative():
    # (a = 1 and b = 2) and c = 3
    model = parse_cql2_text("a = 1 and b = 2 and c = 3")
    assert isinstance(model, BinaryOperationExpression)
    assert isinstance(model.left, BinaryOperationExpression)
    assert model.left.operator == BinaryOperator.AND
    assert model.left.left.left.name == "a"


def test_leading_not_wraps_unary():
    model = parse_cql2_text("not a = 1")
    assert isinstance(model, UnaryOperationExpression)
    assert model.operator == UnaryOperator.NOT


def test_double_not():
    model = parse_cql2_text("not not a = 1")
    assert isinstance(model, UnaryOperationExpression)
    assert isinstance(model.operand, UnaryOperationExpression)


# ── comparisons + arithmetic precedence ─────────────────────────────────────


@pytest.mark.parametrize("op, expected", [("=", "="), ("!=", "<>"), ("<>", "<>")])
def test_comparison_operators(op, expected):
    model = parse_cql2_text(f"a {op} 1")
    assert model.operator == expected


def test_arithmetic_precedence():
    # 1 + (2 * 3)
    model = parse_cql2_text("a = 1 + 2 * 3")
    rhs = model.right
    assert rhs.operator == BinaryOperator.ADD
    assert rhs.right.operator == BinaryOperator.MULTIPLY


def test_unary_minus_and_power():
    # `powerTerm: arithmeticFactor (POW arithmeticFactor)?` and
    # `arithmeticFactor: MINUS? atom` — the minus binds to the base *before*
    # POW is applied, i.e. `-2^3` is `(-2)^3`, not `-(2^3)`.
    model = parse_cql2_text("a = -2^3")
    rhs = model.right
    assert rhs.operator == BinaryOperator.POWER
    assert isinstance(rhs.left, UnaryOperationExpression)
    assert rhs.left.operator == UnaryOperator.MINUS


def test_idiv_and_mod():
    idiv = parse_cql2_text("a = 7 div 2").right
    assert idiv.operator == BinaryOperator.INTEGER_DIVIDE
    assert parse_cql2_text("a = 7 % 2").right.operator == BinaryOperator.MODULO


def test_parenthesised_arithmetic():
    model = parse_cql2_text("a = (1 + 2) * 3")
    assert model.right.operator == BinaryOperator.MULTIPLY
    assert model.right.left.operator == BinaryOperator.ADD


def test_quoted_identifier():
    # A quoted identifier escapes a reserved word / forces case-sensitivity —
    # it does not admit arbitrary characters like spaces (`QUOTED_IDENTIFIER`
    # uses the same `ID_START`/`ID_CONTINUE` charset as a bare `IDENTIFIER`).
    model = parse_cql2_text('"name" = 1')
    assert model.left.name == "name"


# ── BETWEEN / LIKE / IN / IS NULL (standalone, no hierarchy-split) ─────────


def test_between():
    model = parse_cql2_text("a between 1 and 10")
    assert isinstance(model, IsBetweenPredicate)
    assert model.op == "between"
    assert len(model.args) == 3


def test_not_between():
    model = parse_cql2_text("a not between 1 and 10")
    assert isinstance(model, NotExpression)
    assert isinstance(model.args[0], IsBetweenPredicate)


def test_like():
    model = parse_cql2_text("a like 'foo%'")
    assert isinstance(model, IsLikePredicate)
    assert model.args[1] == StringExpression(value="foo%")


def test_like_with_casei_pattern():
    model = parse_cql2_text("a like CASEI('FOO%')")
    assert isinstance(model, IsLikePredicate)
    assert isinstance(model.args[1], CaseiExpression)


def test_not_like():
    model = parse_cql2_text("a not like 'foo%'")
    assert isinstance(model, NotExpression)
    assert isinstance(model.args[0], IsLikePredicate)


def test_in_list():
    model = parse_cql2_text("a in (1, 2, 3)")
    assert isinstance(model, IsInListPredicate)
    items = model.args[1]
    assert isinstance(items, list)
    assert [i.value for i in items] == [1, 2, 3]


def test_not_in_list():
    model = parse_cql2_text("a not in (1, 2, 3)")
    assert isinstance(model, NotExpression)
    assert isinstance(model.args[0], IsInListPredicate)


def test_is_null():
    model = parse_cql2_text("a is null")
    assert isinstance(model, IsNullPredicate)


def test_is_not_null():
    model = parse_cql2_text("a is not null")
    assert isinstance(model, NotExpression)
    assert isinstance(model.args[0], IsNullPredicate)


# ── spatial / temporal / array predicates ───────────────────────────────────


def test_spatial_predicate():
    model = parse_cql2_text("S_INTERSECTS(a, b)")
    assert isinstance(model, SpatialPredicate)
    assert model.op == "s_intersects"
    assert [type(a) for a in model.args] == [IdentifierExpression, IdentifierExpression]


def test_spatial_relate_valid_pattern():
    model = parse_cql2_text("S_RELATE(a, b, 'T*F**FFF*')")
    assert isinstance(model, SpatialRelatePredicate)
    assert model.pattern == "T*F**FFF*"


def test_spatial_relate_invalid_pattern_rejected():
    with pytest.raises(ValidationError):
        parse_cql2_text("S_RELATE(a, b, 'not-a-pattern')")


def test_spatial_relate_wrong_arity_rejected():
    with pytest.raises(Cql2TextSyntaxError):
        parse_cql2_text("S_RELATE(a, b)")


@pytest.mark.parametrize(
    "keyword, op",
    [
        ("T_BEFORE", "t_before"),
        ("T_STARTS", "t_starts"),
        ("T_STARTEDBY", "t_startedby"),
        ("T_FINISHES", "t_finishes"),
        ("T_FINISHEDBY", "t_finishedby"),
    ],
)
def test_temporal_predicate(keyword, op):
    model = parse_cql2_text(f"{keyword}(a, b)")
    assert isinstance(model, TemporalPredicate)
    assert model.op == op


def test_array_predicate():
    model = parse_cql2_text("A_CONTAINS(a, b)")
    assert isinstance(model, ArrayPredicate)
    assert model.op == "a_contains"


# ── WKT geometry + BBOX ──────────────────────────────────────────────────────


def test_point():
    model = parse_cql2_text("a = POINT(1 2)")
    geom = model.right
    assert isinstance(geom, GeometryLiteral)
    assert geom.geom_type == "Point"
    assert geom.coordinates == [1.0, 2.0]


def test_point_z():
    geom = parse_cql2_text("a = POINT Z (1 2 3)").right
    assert geom.coordinates == [1.0, 2.0, 3.0]


def test_linestring():
    geom = parse_cql2_text("a = LINESTRING(1 2, 3 4)").right
    assert geom.geom_type == "LineString"
    assert geom.coordinates == [[1.0, 2.0], [3.0, 4.0]]


def test_polygon_with_hole():
    text = "a = POLYGON((0 0, 4 0, 4 4, 0 4, 0 0), (1 1, 2 1, 2 2, 1 2, 1 1))"
    geom = parse_cql2_text(text).right
    assert geom.geom_type == "Polygon"
    assert len(geom.coordinates) == 2
    assert geom.coordinates[0][0] == [0.0, 0.0]
    assert geom.coordinates[1][0] == [1.0, 1.0]


def test_multipoint():
    geom = parse_cql2_text("a = MULTIPOINT((1 2), (3 4))").right
    assert geom.geom_type == "MultiPoint"
    assert geom.coordinates == [[1.0, 2.0], [3.0, 4.0]]


def test_multilinestring():
    geom = parse_cql2_text("a = MULTILINESTRING((1 2, 3 4), (5 6, 7 8))").right
    assert geom.geom_type == "MultiLineString"
    assert geom.coordinates == [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]]


def test_multipolygon():
    text = "a = MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)), ((2 2, 3 2, 3 3, 2 3, 2 2)))"
    geom = parse_cql2_text(text).right
    assert geom.geom_type == "MultiPolygon"
    assert len(geom.coordinates) == 2


def test_geometry_collection():
    text = "a = GEOMETRYCOLLECTION(POINT(1 2), LINESTRING(3 4, 5 6))"
    geom = parse_cql2_text(text).right
    assert geom.geom_type == "GeometryCollection"
    assert [g.geom_type for g in geom.geometries] == ["Point", "LineString"]


def test_negative_coordinates():
    geom = parse_cql2_text("a = POINT(-1.5 -2.5)").right
    assert geom.coordinates == [-1.5, -2.5]


def test_bbox():
    model = parse_cql2_text("S_WITHIN(geometry, BBOX(-118, 33.8, -117.9, 34))")
    bbox = model.args[1]
    assert isinstance(bbox, BboxLiteral)
    assert bbox.bbox == [-118.0, 33.8, -117.9, 34.0]


# ── temporal instants ────────────────────────────────────────────────────────


def test_date_and_timestamp():
    date = parse_cql2_text("T_BEFORE(built, DATE('2015-01-01'))").args[1]
    assert isinstance(date, TemporalLiteral)
    assert date.temporal_type == "date"
    assert date.value == "2015-01-01"

    ts = parse_cql2_text("T_BEFORE(built, TIMESTAMP('2015-01-01T00:00:00Z'))").args[1]
    assert ts.temporal_type == "timestamp"
    assert ts.value == "2015-01-01T00:00:00Z"


def test_interval_with_string_bounds():
    interval = parse_cql2_text(
        "T_DURING(a, INTERVAL('1969-07-16T13:32:00Z', '1969-07-24T16:50:35Z'))"
    ).args[1]
    assert isinstance(interval, TemporalLiteral)
    assert interval.temporal_type == "interval"
    assert interval.interval == ["1969-07-16T13:32:00Z", "1969-07-24T16:50:35Z"]


def test_interval_with_open_bound():
    text = "T_STARTS(a, INTERVAL('1991-10-07T08:21:06Z', '..'))"
    interval = parse_cql2_text(text).args[1]
    assert interval.interval[1] == ".."


def test_interval_with_property_bounds():
    """``INTERVAL(starts_at, ends_at)`` — common in the official corpus."""
    interval = parse_cql2_text("T_DURING(INTERVAL(starts_at, ends_at), a)").args[0]
    assert isinstance(interval, TemporalLiteral)
    assert [type(b) for b in interval.interval] == [
        IdentifierExpression,
        IdentifierExpression,
    ]
    assert interval.interval[0].name == "starts_at"


# ── CASEI / ACCENTI ──────────────────────────────────────────────────────────


def test_casei_on_property():
    model = parse_cql2_text("CASEI(a) = CASEI('foo')")
    assert isinstance(model.left, CaseiExpression)
    assert isinstance(model.left.args[0], IdentifierExpression)
    assert isinstance(model.right, CaseiExpression)
    assert model.right.args[0] == StringExpression(value="foo")


def test_accenti():
    model = parse_cql2_text("ACCENTI(a) = ACCENTI('foo')")
    assert isinstance(model.left, AccentiExpression)


# ── array literal / functions / geometry manipulation ──────────────────────


def test_array_literal():
    model = parse_cql2_text("a in (1, 2, 3)")
    # via arithmetic operand path (not IN-list): a bare array atom
    arr = parse_cql2_text("a = (1, 2)").right
    assert isinstance(arr, ArrayExpression)
    assert [e.value for e in arr.elements] == [1, 2]
    assert isinstance(model, IsInListPredicate)


def test_geometry_buffer():
    model = parse_cql2_text("a = S_BUFFER(geom, 10)")
    assert isinstance(model.right, GeometryBuffer)
    assert model.right.op == "s_buffer"


def test_geometry_manipulation_unary():
    # Only the `s_`-prefixed canonical names dispatch to a dedicated model
    # (`vocab.GEOM_MANIPULATION_UNARY`'s own scope, matching `from_text.py`'s
    # scanner) — bare `CENTROID(geom)` is a plain function call, see below.
    model = parse_cql2_text("a = S_CONVEXHULL(geom)")
    assert isinstance(model.right, GeometryManipulationUnary)
    assert model.right.op == "s_convexHull"


def test_bare_geometry_function_name_is_generic():
    model = parse_cql2_text("a = CENTROID(geom)")
    assert isinstance(model.right, FunctionCallExpression)
    assert model.right.function_name == "CENTROID"


def test_geometry_manipulation_binary():
    model = parse_cql2_text("a = S_INTERSECTION(geom1, geom2)")
    assert isinstance(model.right, GeometryManipulationBinary)
    assert model.right.op == "s_intersection"


def test_text_op_predicate():
    model = parse_cql2_text("CONTAINS(a, b)")
    assert isinstance(model, TextOpPredicate)
    assert model.op == "contains"


def test_generic_function_call():
    model = parse_cql2_text("a = MYFUNC(1, 2)")
    assert isinstance(model.right, FunctionCallExpression)
    assert model.right.function_name == "MYFUNC"


def test_numeric_and_boolean_literals():
    assert parse_cql2_text("a = 1").right == ConstantExpression(value=1)
    assert parse_cql2_text("a = 1.5").right == ConstantExpression(value=1.5)
    assert parse_cql2_text("a = TRUE").right == ConstantExpression(value=True)
    assert parse_cql2_text("a = FALSE").right == ConstantExpression(value=False)
