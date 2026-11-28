"""Tests for CQL2 expression parsing & write-back.

Covers:
 - BETWEEN / NOT BETWEEN
 - IN / NOT IN
 - LIKE / NOT LIKE / ILIKE
 - IS NULL / IS NOT NULL
 - Spatial predicates: S_INTERSECTS, S_CONTAINS, … S_RELATE
 - Temporal predicates: T_BEFORE, T_AFTER, …
 - Array predicates: A_CONTAINS, A_OVERLAPS, …
 - WKT geometry literals: POINT, LINESTRING, POLYGON, MULTIPOINT, …
 - Temporal literals: DATE, TIMESTAMP, INTERVAL
 - BBOX literal
 - Write-back (converter._format_selector_expr) for all new types
"""

import pytest

from pycartosym.converter import Converter
from pycartosym.cql2.from_cql2text import parse_cql2_text
from pycartosym.cql2.model import (
    ArrayPredicate,
    BboxLiteral,
    ConstantExpression,
    GeometryLiteral,
    IdentifierExpression,
    IsBetweenPredicate,
    IsInListPredicate,
    IsLikePredicate,
    IsNullPredicate,
    NotExpression,
    SpatialPredicate,
    SpatialRelatePredicate,
    TemporalLiteral,
    TemporalPredicate,
)


# Helper: parse text as a standalone expression
def parse(text: str):
    """Parse *text* via the CQL2-Text tree-walker (from_cql2text.parse_cql2_text)."""
    return parse_cql2_text(text)


# Helper: format a dict expression back to CQL2-Text via the converter
def writeback(expr_dict: dict) -> str:
    c = Converter.__new__(Converter)
    return c._format_selector_expr(expr_dict)


# ── BETWEEN / NOT BETWEEN ─────────────────────────────────────────────────


class TestBetween:

    def test_between(self):
        result = parse("age between 10 and 20")
        assert isinstance(result, IsBetweenPredicate)
        assert result.op == "between"
        assert len(result.args) == 3

    def test_not_between(self):
        result = parse("age not between 10 and 20")
        assert isinstance(result, NotExpression)
        assert isinstance(result.args[0], IsBetweenPredicate)

    def test_between_preserves_operands(self):
        result = parse("score BETWEEN 0 AND 100")
        # args = [score, 0, 100]
        assert isinstance(result.args[0], IdentifierExpression)
        assert result.args[0].name == "score"
        assert isinstance(result.args[1], ConstantExpression)
        assert result.args[1].value == 0
        assert isinstance(result.args[2], ConstantExpression)
        assert result.args[2].value == 100

    def test_writeback_between(self):
        d = {"op": "between", "args": [{"property": "age"}, 10, 20]}
        assert writeback(d) == "age between 10 and 20"

    def test_writeback_not_between(self):
        d = {
            "op": "not",
            "args": [{"op": "between", "args": [{"property": "age"}, 10, 20]}],
        }
        assert writeback(d) == "age not between 10 and 20"


# ── IN / NOT IN ───────────────────────────────────────────────────────────


class TestIn:

    def test_in(self):
        result = parse("status in ('a', 'b', 'c')")
        assert isinstance(result, IsInListPredicate)

    def test_not_in(self):
        result = parse("status not in ('x', 'y')")
        assert isinstance(result, NotExpression)
        assert isinstance(result.args[0], IsInListPredicate)

    def test_in_preserves_values(self):
        result = parse("code IN (1, 2, 3)")
        assert isinstance(result, IsInListPredicate)
        # args[0] is the value, args[1] is the list
        assert isinstance(result.args[0], IdentifierExpression)
        assert result.args[0].name == "code"

    def test_writeback_in(self):
        d = {"op": "in", "args": [{"property": "status"}, ["a", "b", "c"]]}
        assert writeback(d) == "status in ('a', 'b', 'c')"

    def test_writeback_not_in(self):
        d = {
            "op": "not",
            "args": [{"op": "in", "args": [{"property": "status"}, ["x", "y"]]}],
        }
        assert writeback(d) == "status not in ('x', 'y')"


# ── LIKE / NOT LIKE / ILIKE ──────────────────────────────────────────────


class TestLike:

    def test_like(self):
        result = parse("name LIKE '%park%'")
        assert isinstance(result, IsLikePredicate)
        assert result.op == "like"

    def test_not_like(self):
        result = parse("name NOT LIKE '%test%'")
        assert isinstance(result, NotExpression)
        assert isinstance(result.args[0], IsLikePredicate)

    def test_casei_like(self):
        """OGC CQL2-Text has no ``ILIKE`` keyword — case-insensitive LIKE is
        ``CASEI(...) LIKE CASEI(...)`` (verified against the ABNF when
        ``CQL2Text.g4`` was written, see its header). ``op: "ilike"`` (a
        distinct, non-standard JSON-level op — see model.IsLikePredicate)
        stays supported for dict write-back below; it is not producible by
        parsing standard CQL2-Text.
        """
        result = parse("CASEI(name) LIKE CASEI('%Park%')")
        assert isinstance(result, IsLikePredicate)
        assert result.op == "like"

    def test_writeback_like(self):
        d = {"op": "like", "args": [{"property": "name"}, "'%park%'"]}
        assert "like" in writeback(d)

    def test_writeback_not_like(self):
        d = {
            "op": "not",
            "args": [{"op": "like", "args": [{"property": "name"}, "'%test%'"]}],
        }
        assert "not like" in writeback(d)


# ── IS NULL / IS NOT NULL ─────────────────────────────────────────────────


class TestIsNull:

    def test_is_null(self):
        result = parse("description is null")
        assert isinstance(result, IsNullPredicate)

    def test_is_not_null(self):
        result = parse("description is not null")
        assert isinstance(result, NotExpression)
        assert isinstance(result.args[0], IsNullPredicate)

    def test_writeback_is_null(self):
        d = {"op": "isNull", "args": [{"property": "description"}]}
        assert writeback(d) == "description is null"

    def test_writeback_is_not_null(self):
        d = {
            "op": "not",
            "args": [{"op": "isNull", "args": [{"property": "description"}]}],
        }
        assert writeback(d) == "description is not null"


# ── Spatial Predicates ────────────────────────────────────────────────────


class TestSpatialPredicateParsing:

    @pytest.mark.parametrize(
        "func",
        [
            "S_INTERSECTS",
            "S_CONTAINS",
            "S_WITHIN",
            "S_TOUCHES",
            "S_CROSSES",
            "S_DISJOINT",
            "S_OVERLAPS",
            "S_EQUALS",
        ],
    )
    def test_spatial_predicate(self, func):
        result = parse(f"{func}(geomA, geomB)")
        assert isinstance(result, SpatialPredicate)
        assert result.op == func.lower()
        assert len(result.args) == 2

    def test_spatial_case_insensitive(self):
        result = parse("s_intersects(a, b)")
        assert isinstance(result, SpatialPredicate)
        assert result.op == "s_intersects"

    def test_s_relate(self):
        result = parse("S_RELATE(geomA, geomB, 'T*F**FFF*')")
        assert isinstance(result, SpatialRelatePredicate)
        assert result.op == "s_relate"
        assert result.pattern == "T*F**FFF*"
        assert len(result.args) == 2

    def test_s_relate_rejects_malformed_de9im_pattern(self):
        # The DE-9IM pattern is validated (models/de9im.is_valid_de9im_pattern),
        # not passed through as an opaque string.
        with pytest.raises(Exception):
            parse("S_RELATE(geomA, geomB, 'ZZZZZZZZZ')")
        with pytest.raises(Exception):
            parse("S_RELATE(geomA, geomB, 'T*F')")

    def test_writeback_spatial(self):
        d = {
            "op": "s_intersects",
            "args": [{"property": "geomA"}, {"property": "geomB"}],
        }
        assert writeback(d) == "S_INTERSECTS(geomA, geomB)"

    def test_writeback_s_relate(self):
        d = {
            "op": "s_relate",
            "args": [{"property": "geomA"}, {"property": "geomB"}],
            "pattern": "T*F**FFF*",
        }
        assert writeback(d) == "S_RELATE(geomA, geomB, 'T*F**FFF*')"


# ── Temporal Predicates ───────────────────────────────────────────────────


class TestTemporalPredicateParsing:

    @pytest.mark.parametrize(
        "func",
        [
            "T_BEFORE",
            "T_AFTER",
            "T_MEETS",
            "T_METBY",
            "T_OVERLAPS",
            "T_OVERLAPPEDBY",
            "T_STARTS",
            "T_STARTEDBY",
            "T_DURING",
            "T_CONTAINS",
            "T_FINISHES",
            "T_FINISHEDBY",
            "T_EQUALS",
            "T_INTERSECTS",
            "T_DISJOINT",
        ],
    )
    def test_temporal_predicate(self, func):
        result = parse(f"{func}(dateA, dateB)")
        assert isinstance(result, TemporalPredicate)
        assert result.op == func.lower()

    def test_writeback_temporal(self):
        d = {
            "op": "t_before",
            "args": [{"property": "startDate"}, {"date": "2020-01-01"}],
        }
        wb = writeback(d)
        assert wb == "T_BEFORE(startDate, DATE('2020-01-01'))"


# ── Array Predicates ──────────────────────────────────────────────────────


class TestArrayPredicateParsing:

    @pytest.mark.parametrize(
        "func",
        [
            "A_EQUALS",
            "A_CONTAINS",
            "A_CONTAINEDBY",
            "A_OVERLAPS",
        ],
    )
    def test_array_predicate(self, func):
        result = parse(f"{func}(arrA, arrB)")
        assert isinstance(result, ArrayPredicate)
        assert result.op == func.lower()

    def test_writeback_array(self):
        d = {"op": "a_contains", "args": [{"property": "tags"}, {"property": "search"}]}
        assert writeback(d) == "A_CONTAINS(tags, search)"


# ── Temporal Literals ─────────────────────────────────────────────────────


class TestTemporalLiteralParsing:

    def test_date(self):
        result = parse("DATE('2024-01-15')")
        assert isinstance(result, TemporalLiteral)
        assert result.temporal_type == "date"
        assert result.value == "2024-01-15"

    def test_timestamp(self):
        result = parse("TIMESTAMP('2024-01-15T08:30:00Z')")
        assert isinstance(result, TemporalLiteral)
        assert result.temporal_type == "timestamp"
        assert result.value == "2024-01-15T08:30:00Z"

    def test_interval(self):
        result = parse("INTERVAL('2024-01-01', '2024-12-31')")
        assert isinstance(result, TemporalLiteral)
        assert result.temporal_type == "interval"
        assert result.interval == ["2024-01-01", "2024-12-31"]

    def test_writeback_date(self):
        d = {"date": "2024-01-15"}
        assert writeback(d) == "DATE('2024-01-15')"

    def test_writeback_timestamp(self):
        d = {"timestamp": "2024-01-15T08:30:00Z"}
        assert writeback(d) == "TIMESTAMP('2024-01-15T08:30:00Z')"

    def test_writeback_interval(self):
        d = {"interval": ["2024-01-01", "2024-12-31"]}
        assert writeback(d) == "INTERVAL('2024-01-01', '2024-12-31')"


# ── BBOX Literal ──────────────────────────────────────────────────────────


class TestBboxParsing:

    def test_bbox_2d(self):
        result = parse("BBOX(0.0, 1.0, 2.0, 3.0)")
        assert isinstance(result, BboxLiteral)
        assert result.bbox == [0.0, 1.0, 2.0, 3.0]

    def test_bbox_3d(self):
        result = parse("BBOX(0, 0, -10, 1, 1, 10)")
        assert isinstance(result, BboxLiteral)
        assert len(result.bbox) == 6

    def test_writeback_bbox(self):
        d = {"bbox": [0.0, 1.0, 2.0, 3.0]}
        assert writeback(d) == "BBOX(0.0, 1.0, 2.0, 3.0)"


# ── WKT Geometry Literals ────────────────────────────────────────────────


class TestWktParsing:

    def test_point(self):
        result = parse("POINT(1 2)")
        assert isinstance(result, GeometryLiteral)
        assert result.geom_type == "Point"
        assert result.coordinates == [1.0, 2.0]

    def test_point_3d(self):
        result = parse("POINT(1 2 3)")
        assert isinstance(result, GeometryLiteral)
        assert result.coordinates == [1.0, 2.0, 3.0]

    def test_linestring(self):
        result = parse("LINESTRING(0 0, 1 1, 2 0)")
        assert isinstance(result, GeometryLiteral)
        assert result.geom_type == "LineString"
        assert result.coordinates == [[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]]

    def test_polygon(self):
        result = parse("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
        assert isinstance(result, GeometryLiteral)
        assert result.geom_type == "Polygon"
        assert len(result.coordinates) == 1  # one ring
        assert len(result.coordinates[0]) == 5  # 5 points

    def test_multipoint(self):
        result = parse("MULTIPOINT((0 0), (1 1))")
        assert isinstance(result, GeometryLiteral)
        assert result.geom_type == "MultiPoint"

    def test_writeback_point(self):
        d = {"type": "Point", "coordinates": [1.0, 2.0]}
        assert writeback(d) == "POINT(1.0 2.0)"

    def test_writeback_linestring(self):
        d = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
        assert writeback(d) == "LINESTRING(0 0, 1 1)"

    def test_writeback_polygon(self):
        d = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        }
        wkt = writeback(d)
        assert wkt.startswith("POLYGON(")
        assert "0 0" in wkt

    def test_writeback_geometrycollection(self):
        d = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Point", "coordinates": [0, 0]},
                {"type": "Point", "coordinates": [1, 1]},
            ],
        }
        wkt = writeback(d)
        assert wkt.startswith("GEOMETRYCOLLECTION(")
        assert "POINT(0 0)" in wkt


# ── Integration: parse → model → to_cql2_json → writeback ────────────────


class TestParseToJsonRoundTrip:

    def test_date_roundtrip(self):
        result = parse("DATE('2024-06-15')")
        assert isinstance(result, TemporalLiteral)
        json = result.to_cql2_json()
        assert json == {"date": "2024-06-15"}
        assert writeback(json) == "DATE('2024-06-15')"

    def test_timestamp_roundtrip(self):
        result = parse("TIMESTAMP('2024-06-15T12:00:00Z')")
        json = result.to_cql2_json()
        assert json == {"timestamp": "2024-06-15T12:00:00Z"}
        assert writeback(json) == "TIMESTAMP('2024-06-15T12:00:00Z')"

    def test_interval_roundtrip(self):
        result = parse("INTERVAL('2024-01-01', '2024-12-31')")
        json = result.to_cql2_json()
        assert json == {"interval": ["2024-01-01", "2024-12-31"]}
        assert writeback(json) == "INTERVAL('2024-01-01', '2024-12-31')"

    def test_bbox_roundtrip(self):
        result = parse("BBOX(0.0, 1.0, 2.0, 3.0)")
        json = result.to_cql2_json()
        assert json == {"bbox": [0.0, 1.0, 2.0, 3.0]}
        assert writeback(json) == "BBOX(0.0, 1.0, 2.0, 3.0)"

    def test_point_geojson_roundtrip(self):
        result = parse("POINT(3.5 48.8)")
        geojson = result.to_geojson()
        assert geojson == {"type": "Point", "coordinates": [3.5, 48.8]}
        assert writeback(geojson) == "POINT(3.5 48.8)"


class TestIntervalBoundsThatAreExpressions:
    """An unquoted bound of INTERVAL(...) is a property, not an instant string."""

    _SELECTOR = "t_intersects(INTERVAL(plannedStart, plannedEnd), viz.timeInterval)"
    _BOUNDS = [{"property": "plannedStart"}, {"property": "plannedEnd"}]

    def test_cscss_selector(self):
        csjson = Converter().cscss_to_csjson(f"[{self._SELECTOR}] {{ opacity: 0.5; }}")
        selector = csjson["stylingRules"][0]["selector"]
        assert selector["args"][0] == {"interval": self._BOUNDS}

    def test_quoted_bounds_stay_instants(self):
        csjson = Converter().cscss_to_csjson(
            "[t_intersects(INTERVAL('2026-01-01', '..'), viz.timeInterval)]"
            " { opacity: 0.5; }"
        )
        selector = csjson["stylingRules"][0]["selector"]
        assert selector["args"][0] == {"interval": ["2026-01-01", ".."]}

    def test_writeback(self):
        d = {"interval": [{"property": "plannedStart"}, ".."]}
        assert writeback(d) == "INTERVAL(plannedStart, '..')"
