"""Writer-direction tests for the SLD/SE codec (vector + Part-1 raster).

Builds small Style/Symbolizer objects in-code and asserts on the parsed-back
XML tree (not raw string matching, to avoid whitespace/attribute-order
brittleness).
"""

from pathlib import Path

import pytest
from lxml import etree

from pycartosym.codecs.sld._dialect import SE_1_1_0
from pycartosym.codecs.sld._symbolizer import symbolizer_to_elements
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style

from ._xsd import assert_sld_valid

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / "examples"

NS = {
    "sld": "http://www.opengis.net/sld",
    "se": "http://www.opengis.net/se",
    "ogc": "http://www.opengis.net/ogc",
    "gml": "http://www.opengis.net/gml",
    "xlink": "http://www.w3.org/1999/xlink",
}


def _write(style_dict) -> etree._Element:
    style = Style.from_dict(style_dict)
    xml = SldWriter().write(style)
    return etree.fromstring(xml.encode("utf-8"))


def _rule_style(symbolizer, selector=None, nested_rules=None):
    rule = {"stylingRuleName": "R", "symbolizer": symbolizer}
    if selector is not None:
        rule["selector"] = selector
    if nested_rules is not None:
        rule["nestedRules"] = nested_rules
    return {"stylingRules": [rule]}


class TestWriteBasicSymbolizers:
    def test_fill_and_stroke_produce_polygon_symbolizer(self):
        root = _write(
            _rule_style(
                {
                    "fill": {"color": "gray", "opacity": 0.5},
                    "stroke": {"color": "#202020", "width": {"px": 2.0}},
                }
            )
        )
        poly = root.find(".//se:PolygonSymbolizer", NS)
        assert poly is not None
        assert root.find(".//se:LineSymbolizer", NS) is None
        fill_params = {
            p.get("name"): p.text for p in poly.findall("se:Fill/se:SvgParameter", NS)
        }
        assert fill_params["fill"] == "#808080"
        assert fill_params["fill-opacity"] == "0.5"
        stroke_params = {
            p.get("name"): p.text for p in poly.findall("se:Stroke/se:SvgParameter", NS)
        }
        assert stroke_params["stroke"] == "#202020"
        assert stroke_params["stroke-width"] == "2"

    def test_stroke_only_produces_line_symbolizer(self):
        root = _write(_rule_style({"stroke": {"color": "red", "width": {"px": 3.0}}}))
        assert root.find(".//se:PolygonSymbolizer", NS) is None
        line = root.find(".//se:LineSymbolizer", NS)
        assert line is not None
        stroke_params = {
            p.get("name"): p.text for p in line.findall("se:Stroke/se:SvgParameter", NS)
        }
        assert stroke_params["stroke"] == "#ff0000"

    def test_stroke_width_as_raw_unit_string_is_parsed(self):
        """CscssReader bypasses Converter._fix_unit_values, so some
        UnitValue fields reach this codec as a raw 'N unit' string (e.g.
        examples/3-vector-line.cscss's alter-overridden width) rather than a
        {unit: value} dict — must still parse, not raise issue #11.
        """
        root = _write(_rule_style({"stroke": {"color": "red", "width": "8.0 m"}}))
        line = root.find(".//se:LineSymbolizer", NS)
        stroke_params = {
            p.get("name"): p.text for p in line.findall("se:Stroke/se:SvgParameter", NS)
        }
        assert stroke_params["stroke-width"] == "8"

    def test_stroke_cap_join_write_linecap_linejoin(self):
        root = _write(
            _rule_style({"stroke": {"color": "red", "cap": "round", "join": "bevel"}})
        )
        line = root.find(".//se:LineSymbolizer", NS)
        stroke_params = {
            p.get("name"): p.text for p in line.findall("se:Stroke/se:SvgParameter", NS)
        }
        assert stroke_params["stroke-linecap"] == "round"
        assert stroke_params["stroke-linejoin"] == "bevel"

    def test_marker_dot_produces_point_symbolizer(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Dot",
                                "size": {"px": 10},
                                "position": {"x": 0, "y": 0},
                                "color": "white",
                            }
                        ]
                    }
                }
            )
        )
        point = root.find(".//se:PointSymbolizer", NS)
        assert point is not None
        wkn = point.find("se:Graphic/se:Mark/se:WellKnownName", NS)
        assert wkn.text == "circle"
        size = point.find("se:Graphic/se:Size", NS)
        assert size.text == "10"

    def test_marker_circle_produces_mark_with_fill_stroke_and_size(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Circle",
                                "position": {"x": 0, "y": 0},
                                "fill": {"color": "white", "opacity": 0.5},
                                "outline": {
                                    "color": "blue",
                                    "thickness": {"px": 2},
                                    "opacity": 0.7,
                                },
                                "radius": {"px": 5},
                            }
                        ]
                    }
                }
            )
        )
        mark = root.find(".//se:PointSymbolizer/se:Graphic/se:Mark", NS)
        assert mark.find("se:WellKnownName", NS).text == "circle"
        fill = {
            p.get("name"): p.text for p in mark.findall("se:Fill/se:SvgParameter", NS)
        }
        assert fill == {"fill": "#ffffff", "fill-opacity": "0.5"}
        stroke = {
            p.get("name"): p.text for p in mark.findall("se:Stroke/se:SvgParameter", NS)
        }
        assert stroke == {
            "stroke": "#0000ff",
            "stroke-width": "2",
            "stroke-opacity": "0.7",
        }
        # se:Size is a diameter — twice the CartoSym radius.
        size = root.find(".//se:PointSymbolizer/se:Graphic/se:Size", NS)
        assert size.text == "10"

    def test_marker_circle_round_trips_through_reader(self):
        from pycartosym.codecs.sld.reader import SldReader

        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "position": {"x": 0, "y": 0},
                            "fill": {"color": [255, 165, 0]},
                            "outline": {"color": [0, 0, 255], "thickness": {"px": 1}},
                            "radius": {"px": 4},
                        }
                    ]
                }
            }
        )
        style1 = Style.from_dict(style_dict)
        xml = SldWriter().write(style1)
        style2 = SldReader().read(xml)
        assert (
            style2.styling_rules[0].symbolizer.marker.elements
            == style1.styling_rules[0].symbolizer.marker.elements
        )

    def test_marker_rectangle_produces_square_mark(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Rectangle",
                                "position": {"x": 0, "y": 0},
                                "fill": {"color": "red"},
                                "width": {"px": 6},
                                "height": {"px": 6},
                            }
                        ]
                    }
                }
            )
        )
        mark = root.find(".//se:PointSymbolizer/se:Graphic/se:Mark", NS)
        assert mark.find("se:WellKnownName", NS).text == "square"
        fill = {
            p.get("name"): p.text for p in mark.findall("se:Fill/se:SvgParameter", NS)
        }
        assert fill == {"fill": "#ff0000"}
        size = root.find(".//se:PointSymbolizer/se:Graphic/se:Size", NS)
        assert size.text == "6"

    def test_marker_rectangle_width_height_mismatch_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Rectangle",
                                    "position": {"x": 0, "y": 0},
                                    "fill": {"color": "red"},
                                    "width": {"px": 6},
                                    "height": {"px": 8},
                                }
                            ]
                        }
                    }
                )
            )

    def test_marker_rectangle_round_trips_through_reader(self):
        from pycartosym.codecs.sld.reader import SldReader

        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Rectangle",
                            "position": {"x": 0, "y": 0},
                            "fill": {"color": [255, 0, 0]},
                            "outline": {"color": [0, 0, 0], "thickness": {"px": 2}},
                            "width": {"px": 10},
                            "height": {"px": 10},
                        }
                    ]
                }
            }
        )
        style1 = Style.from_dict(style_dict)
        xml = SldWriter().write(style1)
        style2 = SldReader().read(xml)
        assert (
            style2.styling_rules[0].symbolizer.marker.elements
            == style1.styling_rules[0].symbolizer.marker.elements
        )

    def test_marker_circle_rotation_maps_to_se_rotation(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Circle",
                                "position": {"x": 0, "y": 0},
                                "fill": {"color": "red"},
                                "radius": {"px": 5},
                                "transform": {"orientation": 45},
                            }
                        ]
                    }
                }
            )
        )
        graphic = root.find(".//se:PointSymbolizer/se:Graphic", NS)
        assert graphic.find("se:Rotation", NS).text == "45"

    def test_marker_rotation_round_trips_through_reader(self):
        from pycartosym.codecs.sld.reader import SldReader

        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "position": {"x": 0, "y": 0},
                            "fill": {"color": [255, 0, 0]},
                            "radius": {"px": 5},
                            "transform": {"orientation": 30},
                        }
                    ]
                }
            }
        )
        style1 = Style.from_dict(style_dict)
        xml = SldWriter().write(style1)
        style2 = SldReader().read(xml)
        assert (
            style2.styling_rules[0].symbolizer.marker.elements
            == style1.styling_rules[0].symbolizer.marker.elements
        )

    def test_label_text_orientation_maps_to_point_placement_rotation(self):
        root = _write(
            _rule_style(
                {
                    "label": {
                        "elements": [
                            {
                                "type": "Text",
                                "text": "Name",
                                "position": {"x": 0, "y": 0},
                                "transform": {"orientation": 10},
                            }
                        ]
                    }
                }
            )
        )
        rotation = root.find(
            ".//se:TextSymbolizer/se:LabelPlacement/se:PointPlacement/se:Rotation",
            NS,
        )
        assert rotation is not None
        assert rotation.text == "10"

    def test_label_rotation_round_trips_through_reader(self):
        from pycartosym.codecs.sld.reader import SldReader

        style_dict = _rule_style(
            {
                "label": {
                    "elements": [
                        {
                            "type": "Text",
                            "text": {"property": "Name"},
                            "position": {"x": 0, "y": 0},
                            "transform": {"orientation": -45},
                        }
                    ]
                }
            }
        )
        style1 = Style.from_dict(style_dict)
        xml = SldWriter().write(style1)
        style2 = SldReader().read(xml)
        assert (
            style2.styling_rules[0].symbolizer.label.elements
            == style1.styling_rules[0].symbolizer.label.elements
        )

    def test_label_text_transform_scaling_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "Name",
                                    "position": {"x": 0, "y": 0},
                                    "transform": {"scaling": {"x": 2, "y": 2}},
                                }
                            ]
                        }
                    }
                )
            )

    def test_label_text_produces_text_symbolizer(self):
        root = _write(
            _rule_style(
                {
                    "label": {
                        "elements": [
                            {
                                "type": "Text",
                                "text": {"property": "Name"},
                                "position": {"x": 0, "y": 0},
                            }
                        ]
                    }
                }
            )
        )
        text_sym = root.find(".//se:TextSymbolizer", NS)
        assert text_sym is not None
        prop = text_sym.find("se:Label/ogc:PropertyName", NS)
        assert prop.text == "Name"

    def test_multiple_dots_produce_sibling_point_symbolizers(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Dot",
                                "size": {"px": 10},
                                "position": {"x": 0, "y": 0},
                                "color": "white",
                            },
                            {
                                "type": "Dot",
                                "size": {"px": 8},
                                "position": {"x": 0, "y": 0},
                                "color": "orange",
                            },
                        ]
                    }
                }
            )
        )
        points = root.findall(".//se:PointSymbolizer", NS)
        assert len(points) == 2


class TestWriteFilter:
    def test_comparison_operators(self):
        for op, tag in [
            ("=", "PropertyIsEqualTo"),
            ("!=", "PropertyIsNotEqualTo"),
            ("<", "PropertyIsLessThan"),
            (">", "PropertyIsGreaterThan"),
            ("<=", "PropertyIsLessThanOrEqualTo"),
            (">=", "PropertyIsGreaterThanOrEqualTo"),
        ]:
            root = _write(
                _rule_style(
                    {"fill": {"color": "red"}},
                    selector={"op": op, "args": [{"property": "X"}, 1]},
                )
            )
            assert (
                root.find(f".//ogc:{tag}", NS) is not None
            ), f"missing {tag} for op {op}"

    def test_and_or_not(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "red"}},
                selector={
                    "op": "and",
                    "args": [
                        {"op": "=", "args": [{"property": "A"}, 1]},
                        {
                            "op": "or",
                            "args": [
                                {"op": "=", "args": [{"property": "B"}, 2]},
                                {
                                    "op": "not",
                                    "args": [
                                        {"op": "=", "args": [{"property": "C"}, 3]}
                                    ],
                                },
                            ],
                        },
                    ],
                },
            )
        )
        assert root.find(".//ogc:And", NS) is not None
        assert root.find(".//ogc:Or", NS) is not None
        assert root.find(".//ogc:Not", NS) is not None

    def test_between_like_isnull(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "red"}},
                selector={
                    "op": "and",
                    "args": [
                        {"op": "between", "args": [{"property": "P"}, 1, 5]},
                        {"op": "like", "args": [{"property": "N"}, "%x%"]},
                        {"op": "isnull", "args": [{"property": "Q"}]},
                    ],
                },
            )
        )
        assert root.find(".//ogc:PropertyIsBetween", NS) is not None
        assert root.find(".//ogc:PropertyIsLike", NS) is not None
        assert root.find(".//ogc:PropertyIsNull", NS) is not None

    def test_datalayer_id_consumed_not_emitted_as_filter(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "red"}},
                selector={"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]},
            )
        )
        assert root.find(".//se:FeatureTypeName", NS).text == "Landuse"
        assert root.find(".//ogc:Filter", NS) is None


class TestWriteScaleDenominator:
    def test_viz_sd_upper_bound_becomes_max_scale_denominator(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "red"}},
                selector={"op": "<", "args": [{"sysId": "viz.sd"}, 200000]},
            )
        )
        rule = root.find(".//se:Rule", NS)
        assert rule.find("se:MaxScaleDenominator", NS).text == "200000"
        assert rule.find("se:MinScaleDenominator", NS) is None
        assert root.find(".//ogc:Filter", NS) is None

    def test_viz_sd_range_and_residual_filter(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "red"}},
                selector={
                    "op": "and",
                    "args": [
                        {"op": ">=", "args": [{"sysId": "viz.sd"}, 1000]},
                        {"op": "<", "args": [{"sysId": "viz.sd"}, 50000]},
                        {"op": "=", "args": [{"property": "CLASS"}, "road"]},
                    ],
                },
            )
        )
        rule = root.find(".//se:Rule", NS)
        assert rule.find("se:MinScaleDenominator", NS).text == "1000"
        assert rule.find("se:MaxScaleDenominator", NS).text == "50000"
        filt = root.find(".//ogc:Filter", NS)
        assert filt is not None
        assert filt.find(".//ogc:PropertyName", NS).text == "CLASS"
        # SE RuleType order: Filter, then Min/MaxScaleDenominator, then Symbolizer.
        kids = [etree.QName(c).localname for c in rule]
        assert kids == [
            "Name",
            "Filter",
            "MinScaleDenominator",
            "MaxScaleDenominator",
            "PolygonSymbolizer",
        ]

    def test_viz_sd_equality_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {"fill": {"color": "red"}},
                    selector={"op": "=", "args": [{"sysId": "viz.sd"}, 5000]},
                )
            )

    def test_roundtrip_through_read(self):
        from pycartosym.codecs.sld.reader import SldReader

        selector = {
            "op": "and",
            "args": [
                {"op": "<", "args": [{"sysId": "viz.sd"}, 100000]},
                {"op": "=", "args": [{"property": "NAME"}, "NY"]},
            ],
        }
        style1 = Style.from_dict(_rule_style({"fill": {"color": "red"}}, selector))
        xml = SldWriter().write(style1)
        style2 = SldReader().read(xml)
        assert style2.styling_rules[0].selector == selector


class TestWriteElseRule:
    def test_else_filter_uses_se_namespace(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "red"}},
                nested_rules=[{"symbolizer": {"fill": {"color": "gray"}}}],
            )
        )
        rules = root.findall(".//se:Rule", NS)
        assert len(rules) == 2
        assert rules[0].find("se:ElseFilter", NS) is None
        assert rules[1].find("se:ElseFilter", NS) is not None
        # Regression guard: SE 1.1.0 se:ElseFilter, never SLD 1.0.0 ogc:ElseFilter.
        assert root.find(".//ogc:ElseFilter", NS) is None


class TestWriteRuleTitleAbstract:
    def test_rule_name_and_comment_map_to_title_and_abstract(self):
        root = _write(
            {
                "stylingRules": [
                    {
                        "name": "Red areas",
                        "$comment": "Areas classified as red",
                        "symbolizer": {"fill": {"color": "red"}},
                    }
                ]
            }
        )
        rule = root.find(".//se:Rule", NS)
        assert rule.find("se:Name", NS) is None
        title = rule.find("se:Description/se:Title", NS)
        abstract = rule.find("se:Description/se:Abstract", NS)
        assert title.text == "Red areas"
        assert abstract.text == "Areas classified as red"

    def test_rule_styling_rule_name_and_name_both_present(self):
        root = _write(
            {
                "stylingRules": [
                    {
                        "name": "Red areas",
                        "stylingRuleName": "rule1",
                        "symbolizer": {"fill": {"color": "red"}},
                    }
                ]
            }
        )
        rule = root.find(".//se:Rule", NS)
        assert rule.find("se:Name", NS).text == "rule1"
        assert rule.find("se:Description/se:Title", NS).text == "Red areas"

    def test_rule_title_abstract_round_trips_through_reader(self):
        from pycartosym.codecs.sld.reader import SldReader

        style_dict = {
            "stylingRules": [
                {
                    "name": "Red areas",
                    "$comment": "Areas classified as red",
                    "stylingRuleName": "rule1",
                    "symbolizer": {"fill": {"color": [255, 0, 0]}},
                }
            ]
        }
        style1 = Style.from_dict(style_dict)
        xml = SldWriter().write(style1)
        style2 = SldReader().read(xml)
        rule2 = style2.styling_rules[0]
        assert rule2.name == "Red areas"
        assert rule2.comment == "Areas classified as red"
        assert rule2.styling_rule_name == "rule1"


class TestWriteFeatureTypeName:
    def test_rules_with_different_ids_get_separate_feature_type_styles(self):
        style_dict = {
            "stylingRules": [
                {
                    "name": "A",
                    "selector": {
                        "op": "=",
                        "args": [{"sysId": "dataLayer.id"}, "Landuse"],
                    },
                    "symbolizer": {"fill": {"color": "red"}},
                },
                {
                    "name": "B",
                    "selector": {
                        "op": "=",
                        "args": [{"sysId": "dataLayer.id"}, "Roads"],
                    },
                    "symbolizer": {"stroke": {"color": "black", "width": {"px": 1.0}}},
                },
            ]
        }
        root = _write(style_dict)
        fts_list = root.findall(".//se:FeatureTypeStyle", NS)
        assert len(fts_list) == 2
        names = {fts.find("se:FeatureTypeName", NS).text for fts in fts_list}
        assert names == {"Landuse", "Roads"}

    def test_datalayer_type_and_dims_conjuncts_stripped_leaves_no_filter(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "gray"}},
                selector={
                    "op": "and",
                    "args": [
                        {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]},
                        {
                            "op": "and",
                            "args": [
                                {
                                    "op": "=",
                                    "args": [{"sysId": "dataLayer.type"}, "vector"],
                                },
                                {
                                    "op": "=",
                                    "args": [
                                        {
                                            "sysId": "dataLayer.featuresGeometryDimensions"  # noqa: E501
                                        },
                                        2,
                                    ],
                                },
                            ],
                        },
                    ],
                },
            )
        )
        assert root.find(".//se:FeatureTypeName", NS).text == "Landuse"
        assert root.find(".//ogc:Filter", NS) is None

    def test_datalayer_type_dims_stripped_leaves_other_conjunct_as_filter(self):
        root = _write(
            _rule_style(
                {"fill": {"color": "gray"}},
                selector={
                    "op": "and",
                    "args": [
                        {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Landuse"]},
                        {"op": "=", "args": [{"sysId": "dataLayer.type"}, "vector"]},
                        {
                            "op": "=",
                            "args": [
                                {"sysId": "dataLayer.featuresGeometryDimensions"},
                                2,
                            ],
                        },
                        {"op": "=", "args": [{"property": "FunctionCode"}, "parking"]},
                    ],
                },
            )
        )
        assert root.find(".//se:FeatureTypeName", NS).text == "Landuse"
        filt = root.find(".//ogc:Filter", NS)
        assert filt is not None
        assert filt.find(".//ogc:PropertyIsEqualTo", NS) is not None
        assert filt.find(".//ogc:PropertyName", NS).text == "FunctionCode"


class TestWriteAlwaysSvgParameter:
    def test_no_css_parameter_anywhere(self):
        root = _write(
            _rule_style(
                {
                    "fill": {"color": "gray", "opacity": 0.5},
                    "stroke": {"color": "black", "width": {"px": 1.0}},
                }
            )
        )
        assert root.findall(".//se:CssParameter", NS) == []
        assert root.findall(".//CssParameter") == []


class TestWriteOutOfScopeRaises:
    def test_raster_color_channels_raises(self):
        with pytest.raises(NotImplementedError):
            _write(_rule_style({"colorChannels": {"r": "R", "g": "G", "b": "B"}}))

    def test_fill_hatch_raises(self):
        with pytest.raises(NotImplementedError):
            _write(_rule_style({"fill": {"hatch": {"width": {"px": 1.0}}}}))

    def test_stroke_casing_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {"stroke": {"color": "black", "casing": {"color": "white"}}}
                )
            )

    def test_shape_graphic_raises(self):
        """Image is now supported (see TestWriteImage) — Shape/Circle/
        Rectangle remain the unsupported graphic types.
        """
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Shape",
                                    "size": {"px": 5},
                                    "position": {"x": 0, "y": 0},
                                }
                            ]
                        }
                    }
                )
            )

    def test_metadata_authors_raises(self):
        style_dict = _rule_style({"fill": {"color": "red"}})
        style_dict["metadata"] = {"title": "T", "authors": ["Alice"]}
        with pytest.raises(NotImplementedError):
            _write(style_dict)

    def test_label_placement_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "X",
                                    "position": {"x": 0, "y": 0},
                                }
                            ],
                            "placement": {"type": "line"},
                        }
                    }
                )
            )


class TestWriteImage:
    def test_image_produces_external_graphic(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Image",
                                "image": {
                                    "uri": "http://example.com/x.png",
                                    "type": "image/png",
                                },
                            }
                        ]
                    }
                }
            )
        )
        point = root.find(".//se:PointSymbolizer", NS)
        assert point is not None
        online = point.find("se:Graphic/se:ExternalGraphic/se:OnlineResource", NS)
        assert online is not None
        assert online.get(f"{{{NS['xlink']}}}href") == "http://example.com/x.png"
        fmt = point.find("se:Graphic/se:ExternalGraphic/se:Format", NS)
        assert fmt is not None and fmt.text == "image/png"

    def test_image_hot_spot_produces_anchor_point(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Image",
                                "image": {"uri": "http://example.com/x.png"},
                                "hotSpot": [{"pc": 50}, {"pc": 50}],
                            }
                        ]
                    }
                }
            )
        )
        anchor = root.find(".//se:PointSymbolizer/se:Graphic/se:AnchorPoint", NS)
        assert anchor is not None
        assert anchor.find("se:AnchorPointX", NS).text == "0.5"
        assert anchor.find("se:AnchorPointY", NS).text == "0.5"

    def test_image_hot_spot_non_percent_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"uri": "http://example.com/x.png"},
                                    "hotSpot": [{"px": 5}, {"px": 5}],
                                }
                            ]
                        }
                    }
                )
            )

    def test_image_without_uri_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "marker": {
                            "elements": [{"type": "Image", "image": {"path": "x.png"}}]
                        }
                    }
                )
            )

    def test_image_tint_always_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"uri": "http://example.com/x.png"},
                                    "tint": "white",
                                }
                            ]
                        }
                    }
                )
            )

    def test_image_non_zero_position_emits_displacement(self):
        root = _write(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Image",
                                "image": {"uri": "http://example.com/x.png"},
                                "position": {"x": 10, "y": 0},
                            }
                        ]
                    }
                }
            )
        )
        disp = root.find(".//se:Graphic/se:Displacement", NS)
        assert disp is not None
        assert disp.find("se:DisplacementX", NS).text == "10"

    def test_image_non_zero_position_raises_for_sld_1_0_0(self):
        from pycartosym.codecs.sld._dialect import SLD_1_0_0

        style = Style.from_dict(
            _rule_style(
                {
                    "marker": {
                        "elements": [
                            {
                                "type": "Image",
                                "image": {"uri": "http://example.com/x.png"},
                                "position": {"x": 10, "y": 0},
                            }
                        ]
                    }
                }
            )
        )
        with pytest.raises(NotImplementedError):
            SldWriter(SLD_1_0_0).write(style)


class TestWriteRaster:
    def test_color_channels_produce_channel_selection_rgb(self):
        root = _write(
            _rule_style(
                {
                    "colorChannels": [
                        {"property": "B04"},
                        {"property": "B03"},
                        {"property": "B02"},
                    ]
                }
            )
        )
        raster = root.find(".//se:RasterSymbolizer", NS)
        assert raster is not None
        assert (
            raster.find(
                "se:ChannelSelection/se:RedChannel/se:SourceChannelName", NS
            ).text
            == "B04"
        )
        assert (
            raster.find(
                "se:ChannelSelection/se:GreenChannel/se:SourceChannelName", NS
            ).text
            == "B03"
        )
        assert (
            raster.find(
                "se:ChannelSelection/se:BlueChannel/se:SourceChannelName", NS
            ).text
            == "B02"
        )

    def test_single_channel_produces_gray_channel(self):
        root = _write(_rule_style({"singleChannel": {"property": "elevation"}}))
        raster = root.find(".//se:RasterSymbolizer", NS)
        assert (
            raster.find(
                "se:ChannelSelection/se:GrayChannel/se:SourceChannelName", NS
            ).text
            == "elevation"
        )

    def test_single_channel_arithmetic_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "singleChannel": {
                            "op": "/",
                            "args": [
                                {
                                    "op": "-",
                                    "args": [
                                        {"property": "B08"},
                                        {"property": "B04"},
                                    ],
                                },
                                {
                                    "op": "+",
                                    "args": [
                                        {"property": "B08"},
                                        {"property": "B04"},
                                    ],
                                },
                            ],
                        }
                    }
                )
            )

    def test_color_channels_and_single_channel_mutually_exclusive_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "colorChannels": [
                            {"property": "R"},
                            {"property": "G"},
                            {"property": "B"},
                        ],
                        "singleChannel": {"property": "elevation"},
                    }
                )
            )

    def test_alpha_channel_always_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "colorChannels": [
                            {"property": "R"},
                            {"property": "G"},
                            {"property": "B"},
                        ],
                        "alphaChannel": 1.0,
                    }
                )
            )

    def test_opacity_map_always_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "singleChannel": {"property": "elevation"},
                        "opacityMap": [[0.0, 1.0], [1.0, 0.5]],
                    }
                )
            )

    def test_color_map_categorize_structure_array_colors(self):
        root = _write(
            _rule_style(
                {
                    "singleChannel": {"property": "elevation"},
                    "colorMap": [
                        [0.0, [96, 136, 73]],
                        [900.0, [226, 219, 167]],
                    ],
                }
            )
        )
        categorize = root.find(".//se:ColorMap/se:Categorize", NS)
        assert categorize is not None
        lookup = categorize.find("se:LookupValue", NS)
        assert lookup is not None and lookup.text == "Rasterdata"
        children = [c for c in categorize if c.tag != f"{{{NS['se']}}}LookupValue"]
        tags = [etree.QName(c).localname for c in children]
        assert tags == ["Value", "Threshold", "Value"]
        values = [c.text for c in children if etree.QName(c).localname == "Value"]
        assert values == ["#608849", "#e2dba7"]
        threshold = [c for c in children if etree.QName(c).localname == "Threshold"][0]
        assert threshold.text == "900"

    def test_color_map_categorize_named_colors(self):
        root = _write(
            _rule_style(
                {
                    "singleChannel": {"property": "hillshade"},
                    "colorMap": [[0.0, "black"], [0.15, "gray"]],
                }
            )
        )
        values = [v.text for v in root.findall(".//se:Categorize/se:Value", NS)]
        assert values == ["#000000", "#808080"]

    def test_hill_shading_factor_produces_shaded_relief(self):
        root = _write(
            _rule_style(
                {
                    "singleChannel": {"property": "elevation"},
                    "hillShading": {"factor": 56},
                }
            )
        )
        relief = root.find(".//se:ShadedRelief/se:ReliefFactor", NS)
        assert relief is not None
        assert relief.text == "56"

    def test_hill_shading_sun_always_raises(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "singleChannel": {"property": "elevation"},
                        "hillShading": {
                            "factor": 56,
                            "sun": {"azimuth": 45.0, "elevation": 60.0},
                        },
                    }
                )
            )

    def test_hill_shading_nested_color_map_and_opacity_map_always_raise(self):
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "singleChannel": {"property": "hillshade"},
                        "hillShading": {
                            "colorMap": [[0.0, "black"], [0.15, "gray"]],
                        },
                    }
                )
            )
        with pytest.raises(NotImplementedError):
            _write(
                _rule_style(
                    {
                        "singleChannel": {"property": "hillshade"},
                        "hillShading": {
                            "opacityMap": [[0.0, 0.75], [0.15, 0.5]],
                        },
                    }
                )
            )

    def test_vector_and_raster_fields_coexist_as_sibling_symbolizers(self):
        root = _write(
            _rule_style(
                {
                    "fill": {"color": "gray"},
                    "singleChannel": {"property": "elevation"},
                }
            )
        )
        assert root.find(".//se:PolygonSymbolizer", NS) is not None
        assert root.find(".//se:RasterSymbolizer", NS) is not None


def _find_raster_symbolizer_dict(rules):
    """Recursively find the first nested-rule symbolizer dict carrying a
    raster field, in an output/*.cs.json-shaped stylingRules list.
    """
    raster_keys = (
        "colorChannels",
        "singleChannel",
        "alphaChannel",
        "colorMap",
        "hillShading",
    )
    for rule in rules:
        sym = rule.get("symbolizer")
        if isinstance(sym, dict) and any(k in sym for k in raster_keys):
            return sym
        nested = rule.get("nestedRules")
        if nested:
            found = _find_raster_symbolizer_dict(nested)
            if found is not None:
                return found
    return None


class TestRealRasterFixturesRegression:
    """Sanity-check the writer against real generated CS-JSON for the
    project's own raster fixtures (examples/5..9-coverage-*.cscss). Only
    fixture 5 is expected to fully succeed — 6/7/8/9 each hit a distinct,
    correctly-documented out-of-scope construct (alphaChannel, HillShading
    sun/colorMap/opacityMap, arithmetic raster channels).
    """

    def _symbolizer_for(self, stem):
        data = Converter().cscss_to_csjson(EXAMPLES_DIR / f"{stem}.cscss")
        raw = _find_raster_symbolizer_dict(data["stylingRules"])
        assert raw is not None, f"no raster symbolizer found in {stem}.cs.json"
        style = Style.from_dict({"stylingRules": [{"symbolizer": raw}]})
        return style.styling_rules[0].symbolizer

    def test_dem_succeeds(self):
        sym = self._symbolizer_for("5-coverage-dem")
        elements = symbolizer_to_elements(SE_1_1_0, sym)
        assert any(etree.QName(e).localname == "RasterSymbolizer" for e in elements)

    def test_sentinel2_raises_on_alpha_channel(self):
        sym = self._symbolizer_for("6-coverage-sentinel2")
        with pytest.raises(NotImplementedError, match="alphaChannel"):
            symbolizer_to_elements(SE_1_1_0, sym)

    def test_ndvi_raises_on_arithmetic_single_channel(self):
        sym = self._symbolizer_for("7-coverage-ndvi")
        with pytest.raises(NotImplementedError, match="singleChannel"):
            symbolizer_to_elements(SE_1_1_0, sym)

    def test_hillshading_raises_on_sun(self):
        sym = self._symbolizer_for("8-coverage-hillshading")
        with pytest.raises(NotImplementedError, match="sun"):
            symbolizer_to_elements(SE_1_1_0, sym)

    def test_hillshading_opacity_raises_on_sun(self):
        sym = self._symbolizer_for("9-coverage-hillshading-opacity")
        with pytest.raises(NotImplementedError, match="sun"):
            symbolizer_to_elements(SE_1_1_0, sym)


class TestSymbolizerOpacity:
    """Symbolizer.opacity has no whole-symbolizer equivalent in SE 1.1.0 —
    it is folded (multiplicatively) into every leaf opacity produced.
    """

    def test_folds_into_fill_and_stroke_opacity(self):
        root = _write(
            _rule_style(
                {
                    "opacity": 0.5,
                    "fill": {"color": "gray", "opacity": 0.8},
                    "stroke": {"color": "#202020", "width": {"px": 2.0}},
                }
            )
        )
        poly = root.find(".//se:PolygonSymbolizer", NS)
        fill_params = {
            p.get("name"): p.text for p in poly.findall("se:Fill/se:SvgParameter", NS)
        }
        stroke_params = {
            p.get("name"): p.text for p in poly.findall("se:Stroke/se:SvgParameter", NS)
        }
        assert fill_params["fill-opacity"] == "0.4"  # 0.5 * 0.8
        assert stroke_params["stroke-opacity"] == "0.5"  # 0.5 * (implicit 1)

    def test_folds_into_raster_opacity_and_round_trips(self):
        style_dict = _rule_style(
            {"opacity": 0.5, "singleChannel": {"property": "elevation"}}
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        root = etree.fromstring(xml.encode("utf-8"))
        op = root.find(".//se:RasterSymbolizer/se:Opacity", NS)
        assert op is not None and op.text == "0.5"

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert back.styling_rules[0].symbolizer.opacity == 0.5

    def test_folds_into_point_graphic_opacity(self):
        root = _write(
            _rule_style(
                {
                    "opacity": 0.25,
                    "marker": {"elements": [{"type": "Dot", "color": "red"}]},
                }
            )
        )
        op = root.find(".//se:PointSymbolizer/se:Graphic/se:Opacity", NS)
        assert op is not None and op.text == "0.25"

    def test_output_stays_xsd_valid(self):
        from ._xsd import assert_sld_valid

        xml = SldWriter().write(
            Style.from_dict(
                _rule_style(
                    {
                        "opacity": 0.5,
                        "fill": {"color": "gray"},
                        "stroke": {"color": "black", "width": {"px": 1.0}},
                    }
                )
            )
        )
        assert_sld_valid(xml, label="symbolizer opacity")


class TestWritePropertyDrivenColor:
    """``fill``/``stroke`` colour as ``ogc:PropertyName`` / ``se:Recode``."""

    def test_property_ref_color_writes_bare_property_name(self):
        root = _write(_rule_style({"fill": {"color": {"property": "COLOR_FIELD"}}}))
        prop = root.find(".//se:Fill/se:SvgParameter/ogc:PropertyName", NS)
        assert prop is not None and prop.text == "COLOR_FIELD"

    def test_match_expression_color_writes_recode(self):
        from ._xsd import assert_sld_valid

        style_dict = _rule_style(
            {
                "fill": {
                    "color": {
                        "op": "match",
                        "args": [
                            {"property": "weight"},
                            15,
                            "#6495ED",
                            10,
                            "#B0C4DE",
                            "#000000",
                        ],
                    }
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="match/Recode fill color")
        root = etree.fromstring(xml.encode("utf-8"))
        recode = root.find(".//se:Fill/se:SvgParameter/se:Recode", NS)
        assert recode.get("fallbackValue") == "#000000"
        lookup = recode.find("se:LookupValue/ogc:PropertyName", NS)
        assert lookup.text == "weight"
        items = recode.findall("se:MapItem", NS)
        assert [i.find("se:Data", NS).text for i in items] == ["15", "10"]
        assert [i.find("se:Value", NS).text for i in items] == ["#6495ED", "#B0C4DE"]

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert (
            back.styling_rules[0].symbolizer.fill.color.to_dict()
            == style_dict["stylingRules"][0]["symbolizer"]["fill"]["color"]
        )

    def test_match_non_property_lookup_raises(self):
        style_dict = _rule_style(
            {
                "fill": {
                    "color": {
                        "op": "match",
                        "args": ["literal-not-a-property", "a", "#fff", "#000"],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_match_non_numeric_label_raises(self):
        style_dict = _rule_style(
            {
                "fill": {
                    "color": {
                        "op": "match",
                        "args": [
                            {"property": "class"},
                            "residential",
                            "#fff",
                            "#000",
                        ],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_match_color_raises_for_sld_1_0_0(self):
        from pycartosym.codecs.sld._dialect import SLD_1_0_0

        style_dict = _rule_style(
            {
                "fill": {
                    "color": {
                        "op": "match",
                        "args": [{"property": "weight"}, 15, "#fff", "#000"],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter(SLD_1_0_0).write(Style.from_dict(style_dict))


class TestWritePropertyDrivenWidth:
    """``stroke-width`` as ``ogc:PropertyName`` / ``ogc:Function`` arithmetic.

    OGC issue #115 confirmed a numeric symbolizer parameter may be a
    "Symbolizer Parameter Value Expressions" arithmetic expression; here
    it's over a ``PropertyRef`` (a feature attribute), which SLD/SE's own
    ``ogc:Function`` mechanism (OGC Filter Encoding) can express — unlike
    ``viz.sd`` (see :class:`TestWriteSystemIdentifierWidthRaises`).
    """

    def test_property_ref_width_writes_bare_property_name(self):
        root = _write(_rule_style({"stroke": {"width": {"property": "LINE_WIDTH"}}}))
        prop = root.find(".//se:Stroke/se:SvgParameter/ogc:PropertyName", NS)
        assert prop is not None and prop.text == "LINE_WIDTH"

    def test_arithmetic_width_writes_ogc_function(self):
        from ._xsd import assert_sld_valid

        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "/",
                        "args": [{"property": "population"}, 1000],
                    }
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="arithmetic stroke-width")
        root = etree.fromstring(xml.encode("utf-8"))
        fn = root.find(".//se:Stroke/se:SvgParameter/ogc:Function", NS)
        assert fn is not None and fn.get("name") == "Div"
        prop = fn.find("ogc:PropertyName", NS)
        lit = fn.find("ogc:Literal", NS)
        assert prop is not None and prop.text == "population"
        assert lit is not None and lit.text == "1000"

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert (
            back.styling_rules[0].symbolizer.stroke.width.to_dict()
            == style_dict["stylingRules"][0]["symbolizer"]["stroke"]["width"]
        )

    def test_nested_arithmetic_width_round_trips(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "+",
                        "args": [
                            {"op": "/", "args": [{"property": "population"}, 1000]},
                            2,
                        ],
                    }
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert (
            back.styling_rules[0].symbolizer.stroke.width.to_dict()
            == style_dict["stylingRules"][0]["symbolizer"]["stroke"]["width"]
        )

    def test_unsupported_arithmetic_operator_raises(self):
        style_dict = _rule_style(
            {"stroke": {"width": {"op": "^", "args": [{"property": "x"}, 2]}}}
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))


class TestWriteMatchExpressionWidth:
    """``stroke-width`` as ``se:Recode`` — the same mechanism
    :class:`TestWritePropertyDrivenColor` already uses for colour,
    generalised to a numeric ``SvgParameter`` (shared
    :func:`..._symbolizer._write_recode`, only output validation/
    formatting differs: numeric outputs must be int/float, formatted
    like an arithmetic literal, not a colour string).
    """

    def test_match_expression_width_writes_recode(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "match",
                        "args": [{"property": "weight"}, 15, 5.0, 10, 2.0, 1.0],
                    }
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="match/Recode stroke-width")
        root = etree.fromstring(xml.encode("utf-8"))
        recode = root.find(".//se:Stroke/se:SvgParameter/se:Recode", NS)
        assert recode.get("fallbackValue") == "1"
        lookup = recode.find("se:LookupValue/ogc:PropertyName", NS)
        assert lookup.text == "weight"
        items = recode.findall("se:MapItem", NS)
        assert [i.find("se:Data", NS).text for i in items] == ["15", "10"]
        assert [i.find("se:Value", NS).text for i in items] == ["5", "2"]

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert back.styling_rules[0].symbolizer.stroke.width.to_dict() == {
            "op": "match",
            "args": [{"property": "weight"}, 15, 5, 10, 2, 1],
        }

    def test_match_non_numeric_output_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "match",
                        "args": [{"property": "weight"}, 15, "thick", "thin"],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_match_non_property_lookup_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "match",
                        "args": ["literal-not-a-property", 1, 5.0, 1.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_match_width_raises_for_sld_1_0_0(self):
        from pycartosym.codecs.sld._dialect import SLD_1_0_0

        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "match",
                        "args": [{"property": "weight"}, 15, 5.0, 1.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter(SLD_1_0_0).write(Style.from_dict(style_dict))


class TestWriteInterpolateExpression:
    """``se:Interpolate`` — never wired at all before this, for either a
    numeric ``SvgParameter`` (``stroke-width``, ``method="numeric"``) or
    a colour one (``fill``, ``method="color"``) — same
    ``se:Interpolate``/``se:LookupValue``/``se:InterpolationPoint`` shape
    as ``se:Recode`` (:class:`TestWriteMatchExpressionWidth`), shared via
    ``_write_interpolate``, only the output validation/formatting and the
    ``method`` attribute differ.
    """

    def test_interpolate_width_writes_se_interpolate(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "linear",
                        "args": [
                            {"property": "population"},
                            0,
                            1.0,
                            1000,
                            5.0,
                            10000,
                            20.0,
                        ],
                    }
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="interpolate stroke-width")
        root = etree.fromstring(xml.encode("utf-8"))
        interp = root.find(".//se:Stroke/se:SvgParameter/se:Interpolate", NS)
        assert interp.get("mode") == "linear"
        assert interp.get("method") == "numeric"
        assert interp.get("fallbackValue") == "20"
        lookup = interp.find("se:LookupValue/ogc:PropertyName", NS)
        assert lookup.text == "population"
        points = interp.findall("se:InterpolationPoint", NS)
        assert [p.find("se:Data", NS).text for p in points] == ["0", "1000", "10000"]
        assert [p.find("se:Value", NS).text for p in points] == ["1", "5", "20"]

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert back.styling_rules[0].symbolizer.stroke.width.to_dict() == {
            "op": "interpolate",
            "interpolation": "linear",
            "args": [{"property": "population"}, 0, 1, 1000, 5, 10000, 20],
        }

    def test_interpolate_fill_color_writes_se_interpolate(self):
        style_dict = _rule_style(
            {
                "fill": {
                    "color": {
                        "op": "interpolate",
                        "interpolation": "linear",
                        "args": [
                            {"property": "temp"},
                            0,
                            "#0000ff",
                            50,
                            "#ffffff",
                            100,
                            "#ff0000",
                        ],
                    }
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="interpolate fill color")
        root = etree.fromstring(xml.encode("utf-8"))
        interp = root.find(".//se:Fill/se:SvgParameter/se:Interpolate", NS)
        assert interp.get("method") == "color"
        assert interp.get("fallbackValue") == "#ff0000"
        points = interp.findall("se:InterpolationPoint", NS)
        assert [p.find("se:Value", NS).text for p in points] == [
            "#0000ff",
            "#ffffff",
            "#ff0000",
        ]

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        assert back.styling_rules[0].symbolizer.fill.color.to_dict() == {
            "op": "interpolate",
            "interpolation": "linear",
            "args": [
                {"property": "temp"},
                0,
                "#0000ff",
                50,
                "#ffffff",
                100,
                "#ff0000",
            ],
        }

    def test_interpolate_exponential_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "exponential",
                        "base": 2,
                        "args": [{"property": "population"}, 0, 1.0, 1000, 5.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_interpolate_cubic_bezier_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "cubic-bezier",
                        "controlPoints": [0.25, 0.1, 0.25, 1.0],
                        "args": [{"property": "population"}, 0, 1.0, 1000, 5.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_interpolate_non_property_lookup_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "linear",
                        "args": ["literal-not-a-property", 0, 1.0, 1000, 5.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_interpolate_non_numeric_stop_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "linear",
                        "args": [{"property": "population"}, "low", 1.0, "high", 5.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_interpolate_non_numeric_width_output_raises(self):
        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "linear",
                        "args": [{"property": "population"}, 0, "thin", 1000, "thick"],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_interpolate_width_raises_for_sld_1_0_0(self):
        from pycartosym.codecs.sld._dialect import SLD_1_0_0

        style_dict = _rule_style(
            {
                "stroke": {
                    "width": {
                        "op": "interpolate",
                        "interpolation": "linear",
                        "args": [{"property": "population"}, 0, 1.0, 1000, 5.0],
                    }
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter(SLD_1_0_0).write(Style.from_dict(style_dict))


class TestWriteSystemIdentifierWidthRaises:
    """``viz.sd`` (current scale denominator) has no SLD/SE value mapping.

    SLD/SE only exposes scale as a rule-level ``MinScaleDenominator``/
    ``MaxScaleDenominator`` gate — never as a value usable inside a
    parameter/filter expression — so this is a confirmed permanent wall,
    not a missing-wiring gap (unlike MapLibre, which has ``["zoom"]``).
    """

    def test_bare_system_identifier_width_raises(self):
        style_dict = _rule_style({"stroke": {"width": {"sysId": "viz.sd"}}})
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_system_identifier_in_arithmetic_width_raises(self):
        style_dict = _rule_style(
            {"stroke": {"width": {"op": "/", "args": [{"sysId": "viz.sd"}, 1000]}}}
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))


class TestWriteMapLibreOnlyNumericExprRaises:
    """``StepExpression``/``CaseExpression`` (MapLibre-only shapes) have no
    SLD/SE mapping — a nested numeric field (``Marker.elements`` is typed
    ``Any``) reaches ``_coerce_numeric_expr`` as a raw ``{"op": ..., "args":
    [...]}`` dict, which must fall through to the same clean
    ``NotImplementedError`` a top-level ``Symbolizer`` field would raise,
    not be force-validated as ``ArithmeticExpression``.
    """

    def test_step_shaped_dot_size_raises_not_implemented(self):
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Dot",
                            "size": {
                                "op": "step",
                                "args": [{"property": "pop"}, 2, 10, 5],
                            },
                        }
                    ]
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_case_shaped_dot_size_raises_not_implemented(self):
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Dot",
                            "size": {
                                "op": "case",
                                "args": [{"property": "big"}, 10, 2],
                            },
                        }
                    ]
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))


class TestWritePropertyDrivenShapeOutlineThickness:
    """A ``2-shapes`` Circle's ``outline.thickness`` gets the same treatment
    as ``stroke-width`` (:class:`TestWritePropertyDrivenWidth`) — same
    ``se:Mark/se:Stroke`` ``stroke-width`` SvgParameter, same writer/reader
    helpers.
    """

    def _circle_style(self, thickness):
        return _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "outline": {"thickness": thickness},
                            "radius": {"px": 5},
                        }
                    ]
                }
            }
        )

    def test_arithmetic_thickness_writes_ogc_function(self):
        from ._xsd import assert_sld_valid

        style_dict = self._circle_style(
            {"op": "/", "args": [{"property": "population"}, 1000]}
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="arithmetic shape-outline thickness")
        root = etree.fromstring(xml.encode("utf-8"))
        fn = root.find(".//se:Mark/se:Stroke/se:SvgParameter/ogc:Function", NS)
        assert fn is not None and fn.get("name") == "Div"

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        el = back.styling_rules[0].symbolizer.marker.elements[0]
        assert (
            el["outline"]["thickness"]
            == style_dict["stylingRules"][0]["symbolizer"]["marker"]["elements"][0][
                "outline"
            ]["thickness"]
        )

    def test_system_identifier_thickness_raises(self):
        style_dict = self._circle_style({"sysId": "viz.sd"})
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))


class TestWritePropertyDrivenPosition:
    """``UnitPoint.x``/``.y`` (``Circle.position``) as a bare property
    reference — ``se:DisplacementX``/``Y`` are direct XML children (no
    ``SvgParameter`` wrapper, unlike ``stroke-width``/``thickness``), so
    a ``PropertyRef`` becomes a bare ``ogc:PropertyName`` as the element's
    sole child instead of its text (:func:`_write_numeric_element`).
    """

    def test_property_ref_x_writes_bare_property_name(self):
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "position": {"x": {"property": "dx"}, "y": 3},
                            "radius": {"px": 5},
                        }
                    ]
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        root = etree.fromstring(xml.encode("utf-8"))
        disp_x = root.find(".//se:Graphic/se:Displacement/se:DisplacementX", NS)
        disp_y = root.find(".//se:Graphic/se:Displacement/se:DisplacementY", NS)
        prop = disp_x.find("ogc:PropertyName", NS)
        assert prop is not None and prop.text == "dx"
        assert disp_y.text == "3"

        from pycartosym.codecs.sld.reader import SldReader

        back = SldReader().read(xml)
        el = back.styling_rules[0].symbolizer.marker.elements[0]
        assert el["position"] == {"x": {"property": "dx"}, "y": 3.0}

    def test_system_identifier_position_raises(self):
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "position": {"x": {"sysId": "viz.sd"}, "y": 3},
                            "radius": {"px": 5},
                        }
                    ]
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))


class TestWritePropertyDrivenNestedElementFields:
    """Fields nested under ``Marker.elements``/``Text.font`` that used to
    call ``format_unit_value``/``format_number``/``format_color`` directly
    instead of going through the coercing writers
    (``_write_numeric_param``/``_write_numeric_element``/
    ``_write_color_param``) — so a ``PropertyRef``/etc. reaching them (a
    raw dict, since ``Marker.elements`` is typed ``Any`` and never
    validated by Pydantic) either crashed with an unhandled exception
    (``Dot.size``/``Font.size``/``Halo.size``, via ``format_unit_value``'s
    single-key-dict branch mis-firing on ``{"sysId": ...}``/
    ``{"property": ...}``, or ``Halo.size`` via ``format_number`` calling
    ``float()`` on a dict) or raised with a misleading message
    (``Dot.color``/``ShapeOutline.color``/``Font.color``/``Halo.color``,
    and ``Circle.fill.color`` nested the same way despite
    ``_write_color_param`` already existing for the top-level-field case,
    PR #68). Fixed by routing each through the same coercing writer its
    direct-field sibling already uses.
    """

    def test_dot_color_and_size_write_property_name(self):
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Dot",
                            "color": {"property": "colourAttr"},
                            "size": {"property": "sizeAttr"},
                        }
                    ]
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="property-driven Dot color/size")
        root = etree.fromstring(xml.encode("utf-8"))
        color_prop = root.find(
            ".//se:Mark/se:Fill/se:SvgParameter/ogc:PropertyName", NS
        )
        size_prop = root.find(".//se:Graphic/se:Size/ogc:PropertyName", NS)
        assert color_prop is not None and color_prop.text == "colourAttr"
        assert size_prop is not None and size_prop.text == "sizeAttr"

    def test_dot_size_system_identifier_raises_cleanly(self):
        """Regression: used to crash (``_format_number("viz.sd")``) rather
        than raise ``NotImplementedError`` like every other confirmed wall.
        """
        style_dict = _rule_style(
            {"marker": {"elements": [{"type": "Dot", "size": {"sysId": "viz.sd"}}]}}
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_shape_outline_color_writes_property_name(self):
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "outline": {"color": {"property": "outlineColourAttr"}},
                            "radius": {"px": 5},
                        }
                    ]
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="property-driven ShapeOutline color")
        root = etree.fromstring(xml.encode("utf-8"))
        prop = root.find(".//se:Mark/se:Stroke/se:SvgParameter/ogc:PropertyName", NS)
        assert prop is not None and prop.text == "outlineColourAttr"

    def test_nested_circle_fill_color_writes_property_name(self):
        """``Circle.fill.color`` (nested under ``Marker.elements``) gets
        the same ``PropertyRef``/``MatchExpression`` support as the
        top-level ``Symbolizer.fill.color`` (PR #68,
        :class:`TestWritePropertyDrivenColor`) — previously
        ``_write_color_param`` only recognised already-typed instances,
        never a raw dict.
        """
        style_dict = _rule_style(
            {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "fill": {"color": {"property": "fillColourAttr"}},
                            "radius": {"px": 5},
                        }
                    ]
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="property-driven nested Circle fill color")
        root = etree.fromstring(xml.encode("utf-8"))
        prop = root.find(".//se:Mark/se:Fill/se:SvgParameter/ogc:PropertyName", NS)
        assert prop is not None and prop.text == "fillColourAttr"

    def test_font_and_halo_color_and_size_write_property_name(self):
        style_dict = _rule_style(
            {
                "label": {
                    "elements": [
                        {
                            "type": "Text",
                            "text": "hello",
                            "font": {
                                "color": {"property": "fontColourAttr"},
                                "size": {"property": "fontSizeAttr"},
                                "outline": {
                                    "color": {"property": "haloColourAttr"},
                                    "size": {"property": "haloSizeAttr"},
                                },
                            },
                        }
                    ]
                }
            }
        )
        xml = SldWriter().write(Style.from_dict(style_dict))
        assert_sld_valid(xml, label="property-driven Font/Halo color/size")
        root = etree.fromstring(xml.encode("utf-8"))
        font_size = root.find(".//se:Font/se:SvgParameter/ogc:PropertyName", NS)
        font_color = root.find(
            ".//se:TextSymbolizer/se:Fill/se:SvgParameter/ogc:PropertyName", NS
        )
        halo_size = root.find(".//se:Halo/se:Radius/ogc:PropertyName", NS)
        halo_color = root.find(
            ".//se:Halo/se:Fill/se:SvgParameter/ogc:PropertyName", NS
        )
        assert font_size is not None and font_size.text == "fontSizeAttr"
        assert font_color is not None and font_color.text == "fontColourAttr"
        assert halo_size is not None and halo_size.text == "haloSizeAttr"
        assert halo_color is not None and halo_color.text == "haloColourAttr"

    def test_font_size_system_identifier_raises_cleanly(self):
        """Regression: used to crash the same way as ``Dot.size`` above."""
        style_dict = _rule_style(
            {
                "label": {
                    "elements": [
                        {
                            "type": "Text",
                            "text": "hello",
                            "font": {"size": {"sysId": "viz.sd"}},
                        }
                    ]
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))

    def test_halo_size_non_expression_dict_raises_cleanly(self):
        """Regression: ``format_number(size)`` used to call ``float()`` on
        any non-numeric *value*, crashing on a dict shape it didn't
        recognise at all (unlike ``format_unit_value``'s narrower
        single-key-dict bug) — now a clean wall via
        ``_write_numeric_element``.
        """
        style_dict = _rule_style(
            {
                "label": {
                    "elements": [
                        {
                            "type": "Text",
                            "text": "hello",
                            "font": {"outline": {"size": {"sysId": "viz.sd"}}},
                        }
                    ]
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))


class TestLabelPlacementSpacingRaises:
    """``Label.placement.minSpacing``/``.maxSpacing`` — now reachable via
    CSCSS (previously only via direct CS-JSON authoring) — confirms the
    already-existing wall: SLD/SE's ``se:LabelPlacement`` has no
    line-placement/priority/spacing equivalent at all, so any
    ``Label.placement`` raises regardless of which of its fields is set.
    """

    def test_min_spacing_raises(self):
        style_dict = _rule_style(
            {
                "label": {
                    "elements": [{"type": "Text", "text": {"property": "NAME"}}],
                    "placement": {"minSpacing": {"px": 5}},
                }
            }
        )
        with pytest.raises(NotImplementedError):
            SldWriter().write(Style.from_dict(style_dict))
