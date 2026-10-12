"""Tests for extended CQL2 expression parsing & write-back.

Covers:
 - Text operation predicates: CONTAINS, STARTSWITH, ENDSWITH
 - Character expression functions: CASEI, ACCENTI, LOWERCASE, UPPERCASE,
   CONCATENATE, SUBSTITUTE, FORMAT
 - Spatial predicates: S_COVERS, S_COVEREDBY
 - Geometry manipulation (binary): S_INTERSECTION, S_UNION,
   S_DIFFERENCE, S_SYMDIFFERENCE
 - Geometry manipulation (unary): S_CONVEXHULL, S_ENVELOPE
 - Geometry buffer: S_BUFFER
 - Hex number literals: 0xFF
 - Round-trip: parse → model → to_json → writeback
"""

import pytest

from pycartosym.converter import Converter
from pycartosym.cql2.from_cql2text import parse_cql2_text
from pycartosym.cql2.from_text import ExpressionParser
from pycartosym.cql2.model import (
    AccentiExpression,
    CaseiExpression,
    ConcatenateExpression,
    ConstantExpression,
    FormatExpression,
    GeometryBuffer,
    GeometryManipulationBinary,
    GeometryManipulationUnary,
    IdentifierExpression,
    LowerUpperCaseExpression,
    SpatialPredicate,
    StringExpression,
    SubstituteExpression,
    TextOpPredicate,
)

# ── Helpers ───────────────────────────────────────────────────────────────


def parse(text: str):
    """Parse *text* via the CQL2-Text tree-walker (from_cql2text.parse_cql2_text)."""
    return parse_cql2_text(text)


def parse_full_chain(text: str):
    """Parse *text* via ``cql2.parse_text``'s full fallback chain.

    For constructs that are not standard CQL2-Text (hex literals — see
    ``TestHexNumber``, verified absent from the OGC ABNF when
    ``CQL2Text.g4`` was written) but that the ``parse_expression`` text-scan
    fallback still accepts.
    """
    return ExpressionParser._parse_expression_text(text)


def writeback(expr_dict: dict) -> str:
    """Format a dict expression back to CQL2-Text via the converter."""
    c = Converter.__new__(Converter)
    return c._format_selector_expr(expr_dict)


# ── Text Operation Predicates ─────────────────────────────────────────────


class TestTextOpPredicates:

    def test_contains_parse(self):
        result = parse("CONTAINS(name, 'park')")
        assert isinstance(result, TextOpPredicate)
        assert result.op == "contains"
        assert len(result.args) == 2

    def test_startswith_parse(self):
        result = parse("STARTSWITH(name, 'pre')")
        assert isinstance(result, TextOpPredicate)
        assert result.op == "startsWith"

    def test_endswith_parse(self):
        result = parse("ENDSWITH(name, 'suffix')")
        assert isinstance(result, TextOpPredicate)
        assert result.op == "endsWith"

    def test_contains_case_insensitive(self):
        result = parse("contains(name, 'park')")
        assert isinstance(result, TextOpPredicate)
        assert result.op == "contains"

    def test_contains_preserves_args(self):
        result = parse("CONTAINS(title, 'hello')")
        assert isinstance(result.args[0], IdentifierExpression)
        assert result.args[0].name == "title"
        assert isinstance(result.args[1], StringExpression)
        assert result.args[1].value == "hello"

    def test_writeback_contains(self):
        d = {"op": "contains", "args": [{"property": "name"}, "park"]}
        assert writeback(d) == "CONTAINS(name, 'park')"

    def test_writeback_startswith(self):
        d = {"op": "startsWith", "args": [{"property": "name"}, "pre"]}
        assert writeback(d) == "STARTSWITH(name, 'pre')"

    def test_writeback_endswith(self):
        d = {"op": "endsWith", "args": [{"property": "name"}, "suf"]}
        assert writeback(d) == "ENDSWITH(name, 'suf')"


# ── CASEI / ACCENTI ──────────────────────────────────────────────────────


class TestCaseiAccenti:

    def test_casei_parse(self):
        result = parse("CASEI(name)")
        assert isinstance(result, CaseiExpression)
        assert result.op == "casei"
        assert len(result.args) == 1

    def test_accenti_parse(self):
        result = parse("ACCENTI(name)")
        assert isinstance(result, AccentiExpression)
        assert result.op == "accenti"

    def test_casei_case_insensitive(self):
        result = parse("casei(title)")
        assert isinstance(result, CaseiExpression)

    def test_writeback_casei(self):
        d = {"op": "casei", "args": [{"property": "name"}]}
        assert writeback(d) == "CASEI(name)"

    def test_writeback_accenti(self):
        d = {"op": "accenti", "args": [{"property": "name"}]}
        assert writeback(d) == "ACCENTI(name)"


# ── LOWERCASE / UPPERCASE ────────────────────────────────────────────────


class TestLowerUpperCase:

    def test_lowercase_parse(self):
        result = parse("LOWERCASE(name)")
        assert isinstance(result, LowerUpperCaseExpression)
        assert result.op == "lowerCase"

    def test_uppercase_parse(self):
        result = parse("UPPERCASE(name)")
        assert isinstance(result, LowerUpperCaseExpression)
        assert result.op == "upperCase"

    def test_writeback_lowercase(self):
        d = {"op": "lowerCase", "args": [{"property": "name"}]}
        assert writeback(d) == "LOWERCASE(name)"

    def test_writeback_uppercase(self):
        d = {"op": "upperCase", "args": [{"property": "name"}]}
        assert writeback(d) == "UPPERCASE(name)"


# ── CONCATENATE ──────────────────────────────────────────────────────────


class TestConcatenate:

    def test_concatenate_parse(self):
        result = parse("CONCATENATE(first, ' ', last)")
        assert isinstance(result, ConcatenateExpression)
        assert result.op == "concatenate"
        assert len(result.args) == 3

    def test_concatenate_two_args(self):
        result = parse("CONCATENATE(a, b)")
        assert isinstance(result, ConcatenateExpression)
        assert len(result.args) == 2

    def test_writeback_concatenate(self):
        d = {
            "op": "concatenate",
            "args": [{"property": "first"}, " ", {"property": "last"}],
        }
        assert writeback(d) == "CONCATENATE(first, ' ', last)"


# ── SUBSTITUTE ───────────────────────────────────────────────────────────


class TestSubstitute:

    def test_substitute_parse(self):
        result = parse("SUBSTITUTE(name, 'old', 'new')")
        assert isinstance(result, SubstituteExpression)
        assert result.op == "substitute"
        assert len(result.args) == 3

    def test_writeback_substitute(self):
        d = {"op": "substitute", "args": [{"property": "name"}, "old", "new"]}
        assert writeback(d) == "SUBSTITUTE(name, 'old', 'new')"


# ── FORMAT ───────────────────────────────────────────────────────────────


class TestFormat:

    def test_format_parse(self):
        result = parse("FORMAT('%s (%d)', name, code)")
        assert isinstance(result, FormatExpression)
        assert result.op == "format"
        assert len(result.args) == 3

    def test_format_single_arg(self):
        result = parse("FORMAT(name)")
        assert isinstance(result, FormatExpression)
        assert len(result.args) == 1

    def test_writeback_format(self):
        d = {
            "op": "format",
            "args": ["%s (%d)", {"property": "name"}, {"property": "code"}],
        }
        assert writeback(d) == "FORMAT('%s (%d)', name, code)"


# ── S_COVERS / S_COVEREDBY ──────────────────────────────────────────────


class TestSpatialCovers:

    def test_s_covers_parse(self):
        result = parse("S_COVERS(geomA, geomB)")
        assert isinstance(result, SpatialPredicate)
        assert result.op == "s_covers"
        assert len(result.args) == 2

    def test_s_coveredby_parse(self):
        result = parse("S_COVEREDBY(geomA, geomB)")
        assert isinstance(result, SpatialPredicate)
        assert result.op == "s_coveredBy"

    def test_s_covers_case_insensitive(self):
        result = parse("s_covers(a, b)")
        assert isinstance(result, SpatialPredicate)

    def test_writeback_s_covers(self):
        d = {"op": "s_covers", "args": [{"property": "geomA"}, {"property": "geomB"}]}
        assert writeback(d) == "S_COVERS(geomA, geomB)"

    def test_writeback_s_coveredby(self):
        d = {
            "op": "s_coveredBy",
            "args": [{"property": "geomA"}, {"property": "geomB"}],
        }
        assert writeback(d) == "S_COVEREDBY(geomA, geomB)"

    def test_model_accepts_s_covers(self):
        sp = SpatialPredicate(op="s_covers", args=[])
        assert sp.normalised_op() == "s_covers"

    def test_model_accepts_s_coveredby(self):
        sp = SpatialPredicate(op="s_coveredBy", args=[])
        assert sp.normalised_op() == "s_coveredBy"


# ── Geometry Manipulation (Binary) ───────────────────────────────────────


class TestGeometryManipulationBinary:

    @pytest.mark.parametrize(
        "func,expected_op",
        [
            ("S_INTERSECTION", "s_intersection"),
            ("S_UNION", "s_union"),
            ("S_DIFFERENCE", "s_difference"),
            ("S_SYMDIFFERENCE", "s_symDifference"),
        ],
    )
    def test_parse(self, func, expected_op):
        result = parse(f"{func}(geomA, geomB)")
        assert isinstance(result, GeometryManipulationBinary)
        assert result.op == expected_op
        assert len(result.args) == 2

    def test_case_insensitive(self):
        result = parse("s_intersection(a, b)")
        assert isinstance(result, GeometryManipulationBinary)

    @pytest.mark.parametrize(
        "op",
        [
            "s_intersection",
            "s_union",
            "s_difference",
            "s_symDifference",
        ],
    )
    def test_writeback(self, op):
        d = {"op": op, "args": [{"property": "geomA"}, {"property": "geomB"}]}
        result = writeback(d)
        assert result == f"{op.upper()}(geomA, geomB)"


# ── Geometry Manipulation (Unary) ────────────────────────────────────────


class TestGeometryManipulationUnary:

    @pytest.mark.parametrize(
        "func,expected_op",
        [
            ("S_CONVEXHULL", "s_convexHull"),
            ("S_ENVELOPE", "s_envelope"),
        ],
    )
    def test_parse(self, func, expected_op):
        result = parse(f"{func}(geom)")
        assert isinstance(result, GeometryManipulationUnary)
        assert result.op == expected_op
        assert len(result.args) == 1

    @pytest.mark.parametrize("op", ["s_convexHull", "s_envelope"])
    def test_writeback(self, op):
        d = {"op": op, "args": [{"property": "geom"}]}
        result = writeback(d)
        assert result == f"{op.upper()}(geom)"


# ── Geometry Buffer ──────────────────────────────────────────────────────


class TestGeometryBuffer:

    def test_s_buffer_parse(self):
        result = parse("S_BUFFER(geom, 100)")
        assert isinstance(result, GeometryBuffer)
        assert result.op == "s_buffer"
        assert len(result.args) == 2

    def test_s_buffer_case_insensitive(self):
        result = parse("s_buffer(geom, 50)")
        assert isinstance(result, GeometryBuffer)

    def test_writeback_s_buffer(self):
        d = {"op": "s_buffer", "args": [{"property": "geom"}, 100]}
        assert writeback(d) == "S_BUFFER(geom, 100)"


# ── Hex Number Literals ──────────────────────────────────────────────────


class TestHexNumber:
    """0x-prefixed hex literals are not CQL2-Text (absent from the OGC ABNF,
    ``CQL2Text.g4`` deliberately omits them) and not the CartoSym-CSS
    grammar's own ``#RRGGBB``-style ``HEX_LITERAL`` token either — parsed
    via ``parse_full_chain``, which falls through to the
    ``parse_expression`` text-scan fallback.
    """

    def test_hex_lowercase(self):
        result = parse_full_chain("0xff")
        assert isinstance(result, ConstantExpression)
        assert result.value == 255

    def test_hex_uppercase(self):
        result = parse_full_chain("0xFF")
        assert isinstance(result, ConstantExpression)
        assert result.value == 255

    def test_hex_multi_digit(self):
        result = parse_full_chain("0xAB12")
        assert isinstance(result, ConstantExpression)
        assert result.value == 0xAB12

    def test_hex_zero(self):
        result = parse_full_chain("0x00")
        assert isinstance(result, ConstantExpression)
        assert result.value == 0


class TestGrammarPreferredOverScanner:
    """``parse_cql2_text`` (the standalone ``CQL2Text.g4`` tree-walker, now
    ``_parse_expression_text``'s primary path) gets both of these right;
    the old hand-rolled scanner (removed) had no arithmetic precedence and
    dropped a leading ``not``. Hex literals still fall back further, past
    this tree-walker, to the ``parse_expression`` text-scan (``TestHexNumber``).
    """

    def test_leading_not_is_not_dropped(self):
        from pycartosym.cql2.model import (
            NotExpression,
            UnaryOperationExpression,
        )

        result = parse("not (FunctionCode = 'park')")
        assert isinstance(result, (UnaryOperationExpression, NotExpression))

    def test_arithmetic_precedence_is_parsed(self):
        from pycartosym.cql2.model import BinaryOperationExpression

        result = parse("a + b * c")
        assert isinstance(result, BinaryOperationExpression)
        assert str(result.operator) in ("+", "BinaryOperator.ADD")
        # right operand is the higher-precedence multiplication
        assert isinstance(result.right, BinaryOperationExpression)
        assert str(result.right.operator) in ("*", "BinaryOperator.MULTIPLY")


# ── Round-trip integration ───────────────────────────────────────────────


class TestRoundTrip:

    def test_contains_roundtrip(self):
        result = parse("CONTAINS(name, 'park')")
        assert isinstance(result, TextOpPredicate)
        d = {
            "op": result.op,
            "args": [{"property": result.args[0].name}, result.args[1].value],
        }
        assert writeback(d) == "CONTAINS(name, 'park')"

    def test_casei_roundtrip(self):
        result = parse("CASEI(name)")
        assert isinstance(result, CaseiExpression)
        d = {"op": "casei", "args": [{"property": "name"}]}
        assert writeback(d) == "CASEI(name)"

    def test_s_covers_roundtrip(self):
        result = parse("S_COVERS(geomA, geomB)")
        assert isinstance(result, SpatialPredicate)
        d = {
            "op": result.op,
            "args": [
                {"property": result.args[0].name},
                {"property": result.args[1].name},
            ],
        }
        assert writeback(d) == "S_COVERS(geomA, geomB)"

    def test_s_buffer_roundtrip(self):
        result = parse("S_BUFFER(geom, 100)")
        assert isinstance(result, GeometryBuffer)
        d = {
            "op": result.op,
            "args": [
                {"property": result.args[0].name},
                result.args[1].value,
            ],
        }
        assert writeback(d) == "S_BUFFER(geom, 100)"

    def test_s_convexhull_roundtrip(self):
        result = parse("S_CONVEXHULL(geom)")
        assert isinstance(result, GeometryManipulationUnary)
        d = {"op": result.op, "args": [{"property": result.args[0].name}]}
        assert writeback(d) == "S_CONVEXHULL(geom)"

    def test_concatenate_roundtrip(self):
        result = parse("CONCATENATE(a, b)")
        assert isinstance(result, ConcatenateExpression)
        d = {"op": "concatenate", "args": [{"property": "a"}, {"property": "b"}]}
        assert writeback(d) == "CONCATENATE(a, b)"

    def test_substitute_roundtrip(self):
        result = parse("SUBSTITUTE(name, 'old', 'new')")
        assert isinstance(result, SubstituteExpression)
        d = {"op": "substitute", "args": [{"property": "name"}, "old", "new"]}
        assert writeback(d) == "SUBSTITUTE(name, 'old', 'new')"

    def test_lowercase_roundtrip(self):
        result = parse("LOWERCASE(name)")
        assert isinstance(result, LowerUpperCaseExpression)
        d = {"op": "lowerCase", "args": [{"property": "name"}]}
        assert writeback(d) == "LOWERCASE(name)"


# ── text-scan fallback: NOT ILIKE and mixed BETWEEN/and/or ────────────────


def test_not_ilike_is_negated_ilike_not_a_mangled_identifier():
    """`x NOT ILIKE 'a'` must negate an ILIKE on `x`, not ILIKE on `x NOT`."""
    result = ExpressionParser._parse_expression_text("x NOT ILIKE 'a'")
    assert result.op == "not"
    (inner,) = result.args
    assert inner.op == "ilike"
    assert inner.args[0].name == "x"


@pytest.mark.parametrize("conn", ["and", "or"])
def test_between_after_a_leading_connective_is_not_swallowed(conn):
    """A BETWEEN preceded by `and`/`or` stays one operand of the connective."""
    result = ExpressionParser.parse_expression(f"a = 1 {conn} x between 1 and 2")
    assert result.operator == conn
    assert result.right.op == "between"
