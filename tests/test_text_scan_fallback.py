"""Expressions that the CartoSym-CSS grammar reads but CQL2-Text does not.

A `?:` (or a unit) is not CQL2-Text, so the expression is read by the
CartoSym-CSS grammar, which hands the arguments of a known CQL2 call
(`s_intersects`, `concatenate`…) to the text scan of
`ExpressionParser._try_parse_cql2_function`. These cases go through that scan:
WKT geometries, a call to an unknown function and a property path as
arguments.
"""

import pytest

from pycartosym import Converter


def _width(geometry: str):
    style = Converter().cscss_to_csjson(
        f"R {{ stroke: {{ width: s_intersects(geom, {geometry}) ? 2 px : 1 px }}; }}"
    )
    width = style["stylingRules"][0]["symbolizer"]["stroke"]["width"]
    assert width["op"] == "?:"
    return width["args"][0]["args"][1]


@pytest.mark.parametrize(
    ("wkt", "expected"),
    [
        ("POINT(1 2)", {"type": "Point", "coordinates": [1.0, 2.0]}),
        (
            "LINESTRING(0 0, 1 1)",
            {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
        ),
        (
            "POLYGON((0 0, 1 0, 1 1, 0 0))",
            {
                "type": "Polygon",
                "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
            },
        ),
        (
            "MULTIPOINT((0 0), (1 1))",
            {"type": "MultiPoint", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
        ),
        (
            "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 0)), ((5 5, 6 5, 6 6, 5 5)))",
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
                    [[[5.0, 5.0], [6.0, 5.0], [6.0, 6.0], [5.0, 5.0]]],
                ],
            },
        ),
        (
            "GEOMETRYCOLLECTION(POINT(1 2), LINESTRING(0 0, 1 1))",
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "Point", "coordinates": [1.0, 2.0]},
                    {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                ],
            },
        ),
    ],
)
def test_wkt_argument_next_to_a_conditional(wkt, expected):
    assert _width(wkt) == expected


def test_unknown_call_and_property_path_as_arguments():
    style = Converter().cscss_to_csjson(
        "R { label: { elements: [ Text { text: "
        "concatenate(myFunc(a), x.y, b ? 'c' : 'd') } ] }; }"
    )
    text = style["stylingRules"][0]["symbolizer"]["label"]["elements"][0]["text"]
    assert text == {
        "op": "concatenate",
        "args": [
            {"op": "myFunc", "args": [{"property": "a"}]},
            {"property": "x.y"},
            {"op": "?:", "args": [{"property": "b"}, "c", "d"]},
        ],
    }
