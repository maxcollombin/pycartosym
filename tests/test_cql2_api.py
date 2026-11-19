"""Smoke tests for the public :mod:`pycartosym.cql2` API."""

from __future__ import annotations

from pycartosym import cql2


def test_parse_text_returns_model():
    expr = cql2.parse_text("population > 1000")
    assert expr.operator == ">"
    assert expr.left.name == "population"


def test_to_cql2_text_roundtrips_a_selector_dict():
    d = {
        "op": "and",
        "args": [
            {"op": "=", "args": [{"property": "a"}, 1]},
            {"op": "like", "args": [{"property": "b"}, "x%"]},
        ],
    }
    assert cql2.to_cql2_text(d) == "a = 1 and b like 'x%'"


def test_to_cql2_json_passes_through_dicts():
    d = {"op": "=", "args": [{"property": "x"}, 1]}
    assert cql2.to_cql2_json(d) is d


def test_to_cql2_json_serialises_a_model():
    expr = cql2.parse_text("x = 1")
    assert cql2.to_cql2_json(expr) == {"op": "=", "args": [{"property": "x"}, 1]}


def test_vocab_is_exposed():
    assert cql2.vocab.SPATIAL_RELATE == "s_relate"
    assert "s_intersects" in cql2.vocab.KNOWN_CQL2_CALLS


def test_modulo_is_written_infix():
    d = {"op": "%", "args": [-7, 3]}
    assert cql2.to_cql2_text(d) == "-7 % 3"
    assert cql2.to_cql2_json(cql2.parse_text(cql2.to_cql2_text(d))) == d


def test_right_operand_of_the_same_precedence_keeps_its_brackets():
    for text in ("a - (b - c)", "a / (b * c)", "a % (b * c)", "a - b - c"):
        written = cql2.to_cql2_text(cql2.to_cql2_json(cql2.parse_text(text)))
        assert written == text


def test_nested_and_or_keep_the_structure_when_written():
    for text in (
        "x and (y and z)",
        "x or (y or z)",
        "x or (y and z)",
        "(x or y) and z",
    ):
        written = cql2.to_cql2_text(cql2.to_cql2_json(cql2.parse_text(text)))
        assert written == text
    left = cql2.to_cql2_json(cql2.parse_text("(x and y) and z"))
    assert cql2.to_cql2_text(left) == "x and y and z"
