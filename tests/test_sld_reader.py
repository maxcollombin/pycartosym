"""Reader-direction tests for the SLD/SE codec (vector-only pass)."""

from pathlib import Path

import pytest

from pycartosym.codecs.sld.reader import SldReader

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "examples" / "sld"


def _read(name):
    return SldReader().read(FIXTURES / name)


class TestReadBasicSymbolizers:
    def test_polygon_fill_stroke(self):
        style = _read("1-polygon-fill-stroke.sld")
        rule = style.styling_rules[0]
        sym = rule.symbolizer
        assert sym.fill.color == [128, 128, 128]
        assert sym.fill.opacity == 0.5
        assert sym.stroke.color == [32, 32, 32]
        assert sym.stroke.opacity == 1.0

    def test_line_stroke_dash(self):
        style = _read("2-line-stroke-dash.sld")
        sym = style.styling_rules[0].symbolizer
        assert sym.fill is None
        assert sym.stroke.color == [169, 169, 169]
        assert sym.stroke.dash_pattern == [4, 2]

    def test_point_circle_mark(self):
        style = _read("3-point-dot-mark.sld")
        sym = style.styling_rules[0].symbolizer
        elements = sym.marker.elements
        assert len(elements) == 2
        # A filled se:Mark wellKnownName="circle" is a 2-shapes Circle,
        # not a 1-core Dot (which is stroke-only).
        assert elements[0]["type"] == "Circle"
        assert elements[0]["fill"]["color"] == [255, 255, 255]
        assert elements[0]["radius"] == {"px": 5}  # se:Size 10, halved
        assert elements[1]["fill"]["color"] == [255, 165, 0]
        assert elements[1]["radius"] == {"px": 4}  # se:Size 8, halved

    def test_circle_mark_stroke_maps_to_outline_not_dropped(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:PointSymbolizer><se:Graphic>"
            "<se:Mark><se:WellKnownName>circle</se:WellKnownName>"
            '<se:Fill><se:SvgParameter name="fill">#ff0000</se:SvgParameter>'
            "</se:Fill>"
            '<se:Stroke><se:SvgParameter name="stroke">#0000ff</se:SvgParameter>'
            '<se:SvgParameter name="stroke-width">2</se:SvgParameter></se:Stroke>'
            "</se:Mark><se:Size>8</se:Size>"
            "</se:Graphic></se:PointSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        el = SldReader().read(xml).styling_rules[0].symbolizer.marker.elements[0]
        assert el["type"] == "Circle"
        assert el["fill"] == {"color": [255, 0, 0]}
        assert el["outline"] == {"color": [0, 0, 255], "thickness": {"px": 2}}
        assert el["radius"] == {"px": 4}

    def test_circle_mark_non_numeric_size_raises_not_implemented(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:PointSymbolizer><se:Graphic>"
            "<se:Mark><se:WellKnownName>circle</se:WellKnownName>"
            '<se:Fill><se:SvgParameter name="fill">#ff0000</se:SvgParameter>'
            "</se:Fill></se:Mark><se:Size>notanumber</se:Size>"
            "</se:Graphic></se:PointSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        with pytest.raises(NotImplementedError):
            SldReader().read(xml)

    def test_circle_mark_stroke_unknown_param_is_rejected(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:PointSymbolizer><se:Graphic>"
            "<se:Mark><se:WellKnownName>circle</se:WellKnownName>"
            '<se:Stroke><se:SvgParameter name="stroke-linecap">round'
            "</se:SvgParameter></se:Stroke>"
            "</se:Mark></se:Graphic></se:PointSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        with pytest.raises(NotImplementedError):
            SldReader().read(xml)

    def test_square_mark_maps_to_rectangle(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:PointSymbolizer><se:Graphic>"
            "<se:Mark><se:WellKnownName>square</se:WellKnownName>"
            '<se:Fill><se:SvgParameter name="fill">#ff0000</se:SvgParameter>'
            "</se:Fill></se:Mark><se:Size>6</se:Size>"
            "</se:Graphic></se:PointSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        el = SldReader().read(xml).styling_rules[0].symbolizer.marker.elements[0]
        assert el["type"] == "Rectangle"
        assert el["fill"] == {"color": [255, 0, 0]}
        # se:Size is a single scalar — width == height, unlike a circle's
        # size (a diameter) which is halved into a radius.
        assert el["width"] == {"px": 6}
        assert el["height"] == {"px": 6}

    def test_non_circle_non_square_mark_raises_not_implemented(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:PointSymbolizer><se:Graphic>"
            "<se:Mark><se:WellKnownName>triangle</se:WellKnownName></se:Mark>"
            "</se:Graphic></se:PointSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        with pytest.raises(NotImplementedError):
            SldReader().read(xml)

    def test_graphic_rotation_maps_to_transform_orientation(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:PointSymbolizer><se:Graphic>"
            "<se:Mark><se:WellKnownName>circle</se:WellKnownName>"
            '<se:Fill><se:SvgParameter name="fill">#ff0000</se:SvgParameter>'
            "</se:Fill></se:Mark><se:Size>8</se:Size>"
            "<se:Rotation>45</se:Rotation>"
            "</se:Graphic></se:PointSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        el = SldReader().read(xml).styling_rules[0].symbolizer.marker.elements[0]
        assert el["transform"] == {"orientation": 45.0}

    def test_line_stroke_cap_join(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:LineSymbolizer><se:Stroke>"
            '<se:SvgParameter name="stroke">#000000</se:SvgParameter>'
            '<se:SvgParameter name="stroke-linecap">round</se:SvgParameter>'
            '<se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>'
            "</se:Stroke></se:LineSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        sym = SldReader().read(xml).styling_rules[0].symbolizer
        assert sym.stroke.cap == "round"
        assert sym.stroke.join == "bevel"

    def test_line_stroke_linejoin_non_standard_spelling_is_rejected(self):
        # "mitre" (British) is not the SVG/SE spec spelling ("miter") —
        # a real vendored-corpus fixture uses it; must raise, not guess.
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:LineSymbolizer><se:Stroke>"
            '<se:SvgParameter name="stroke-linejoin">mitre</se:SvgParameter>'
            "</se:Stroke></se:LineSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        with pytest.raises(NotImplementedError):
            SldReader().read(xml)

    def test_line_perpendicular_offset_zero_passes(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:LineSymbolizer>"
            '<se:Stroke><se:SvgParameter name="stroke">#000000</se:SvgParameter>'
            "</se:Stroke><se:PerpendicularOffset>0</se:PerpendicularOffset>"
            "</se:LineSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        sym = SldReader().read(xml).styling_rules[0].symbolizer
        assert sym.stroke.color == [0, 0, 0]

    def test_line_perpendicular_offset_non_zero_is_rejected(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:LineSymbolizer>"
            '<se:Stroke><se:SvgParameter name="stroke">#000000</se:SvgParameter>'
            "</se:Stroke><se:PerpendicularOffset>3</se:PerpendicularOffset>"
            "</se:LineSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        with pytest.raises(NotImplementedError):
            SldReader().read(xml)

    def test_text_label(self):
        style = _read("4-text-label.sld")
        sym = style.styling_rules[0].symbolizer
        el = sym.label.elements[0]
        assert el.text == {"property": "Name"}
        assert el.font["face"] == "Arial"
        assert el.alignment == ["left", "middle"]
        assert el.position.x == 20

    def test_label_ogc_literal_is_read_as_plain_text(self):
        """se:Label is mixed content; some producers wrap literal text in
        <ogc:Literal> rather than as a bare text node.
        """
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>x</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule><se:TextSymbolizer>"
            "<se:Label><ogc:Literal>myText</ogc:Literal></se:Label>"
            "</se:TextSymbolizer></se:Rule></se:FeatureTypeStyle>"
            "</UserStyle></NamedLayer></StyledLayerDescriptor>"
        )
        style = SldReader().read(xml)
        el = style.styling_rules[0].symbolizer.label.elements[0]
        assert el.text == "myText"


class TestReadFilter:
    def test_and_of_comparisons(self):
        style = _read("2-line-stroke-dash.sld")
        selector = style.styling_rules[0].selector
        assert selector["op"] == "and"
        # One conjunct is the dataLayer.id sugar, the other the RoadClass comparison.
        ops = {arg["op"] for arg in selector["args"]}
        assert ops == {"="}

    def test_filter_breadth(self):
        style = _read("8-comparisons.sld")
        selector = style.styling_rules[0].selector
        assert selector["op"] == "and"
        ops = [arg.get("op") for arg in selector["args"]]
        assert "between" in ops
        assert "like" in ops
        assert "not" in ops
        assert "or" in ops


class TestReadScaleDenominator:
    _RULE = """<?xml version="1.0"?>
<StyledLayerDescriptor version="1.1.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc">
  <NamedLayer><se:Name>L</se:Name><UserStyle><se:Name>S</se:Name>
    <se:FeatureTypeStyle>
      <se:Rule>
        <se:Name>R</se:Name>
        {filter}
        {min}
        {max}
        <se:PointSymbolizer><se:Graphic><se:Mark>
          <se:WellKnownName>circle</se:WellKnownName>
          <se:Fill><se:SvgParameter name="fill">#FF0000</se:SvgParameter></se:Fill>
        </se:Mark></se:Graphic></se:PointSymbolizer>
      </se:Rule>
    </se:FeatureTypeStyle>
  </UserStyle></NamedLayer>
</StyledLayerDescriptor>"""

    def _read(self, *, filter="", min="", max=""):
        xml = self._RULE.format(filter=filter, min=min, max=max)
        return SldReader().read(xml).styling_rules[0].selector

    def test_min_and_max_become_viz_sd_range(self):
        selector = self._read(
            min="<se:MinScaleDenominator>10000</se:MinScaleDenominator>",
            max="<se:MaxScaleDenominator>20000</se:MaxScaleDenominator>",
        )
        assert selector == {
            "op": "and",
            "args": [
                {"op": ">=", "args": [{"sysId": "viz.sd"}, 10000]},
                {"op": "<", "args": [{"sysId": "viz.sd"}, 20000]},
            ],
        }

    def test_max_only(self):
        selector = self._read(
            max="<se:MaxScaleDenominator>200000</se:MaxScaleDenominator>"
        )
        assert selector == {"op": "<", "args": [{"sysId": "viz.sd"}, 200000]}

    def test_zero_min_is_dropped(self):
        selector = self._read(
            min="<se:MinScaleDenominator>0</se:MinScaleDenominator>",
            max="<se:MaxScaleDenominator>500000</se:MaxScaleDenominator>",
        )
        assert selector == {"op": "<", "args": [{"sysId": "viz.sd"}, 500000]}

    def test_merged_ahead_of_ogc_filter(self):
        selector = self._read(
            filter=(
                "<ogc:Filter><ogc:PropertyIsEqualTo>"
                "<ogc:PropertyName>NAME</ogc:PropertyName>"
                "<ogc:Literal>NY</ogc:Literal>"
                "</ogc:PropertyIsEqualTo></ogc:Filter>"
            ),
            max="<se:MaxScaleDenominator>20000</se:MaxScaleDenominator>",
        )
        assert selector == {
            "op": "and",
            "args": [
                {"op": "<", "args": [{"sysId": "viz.sd"}, 20000]},
                {"op": "=", "args": [{"property": "NAME"}, "NY"]},
            ],
        }


class TestReadElseRule:
    def test_nested_rules_populated(self):
        style = _read("5-else-rule.sld")
        rule = style.styling_rules[0]
        assert rule.nested_rules is not None
        assert len(rule.nested_rules) == 1
        assert rule.nested_rules[0].symbolizer.stroke.color == [128, 128, 128]


class TestReadFeatureTypeName:
    def test_selector_contains_datalayer_id(self):
        style = _read("6-feature-type-name.sld")
        selector = style.styling_rules[0].selector
        assert selector == {
            "op": "=",
            "args": [{"sysId": "dataLayer.id"}, "Buildings"],
        }


class TestReadMultiSymbolizerRule:
    def test_single_symbolizer_has_fill_stroke_and_label(self):
        style = _read("7-multi-symbolizer-rule.sld")
        sym = style.styling_rules[0].symbolizer
        assert sym.fill is not None
        assert sym.stroke is not None
        assert sym.label is not None
        assert sym.marker is None


class TestReadMetadata:
    def test_title_and_abstract(self):
        style = _read("9-metadata.sld")
        assert style.metadata.title == "Metadata-only style"
        assert style.metadata.abstract == (
            "SLD/SE codec fixture: se:Description/Title/Abstract mapping"
        )


class TestReadRuleMetadata:
    def test_rule_title_and_abstract_map_to_name_and_comment(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>L</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule>"
            "<se:Name>rule1</se:Name>"
            "<se:Description><se:Title>Red areas</se:Title>"
            "<se:Abstract>Areas classified as red</se:Abstract></se:Description>"
            '<se:PolygonSymbolizer><se:Fill><se:SvgParameter name="fill">'
            "#ff0000</se:SvgParameter></se:Fill></se:PolygonSymbolizer>"
            "</se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        rule = SldReader().read(xml).styling_rules[0]
        assert rule.styling_rule_name == "rule1"
        assert rule.name == "Red areas"
        assert rule.comment == "Areas classified as red"

    def test_rule_without_title_abstract_leaves_name_and_comment_unset(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se">'
            "<NamedLayer><se:Name>L</se:Name><UserStyle>"
            "<se:FeatureTypeStyle><se:Rule>"
            '<se:PolygonSymbolizer><se:Fill><se:SvgParameter name="fill">'
            "#ff0000</se:SvgParameter></se:Fill></se:PolygonSymbolizer>"
            "</se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        rule = SldReader().read(xml).styling_rules[0]
        assert rule.name is None
        assert rule.comment is None


class TestReadSymbolizerGeometry:
    """se:Geometry (symbolizer geometry, 3-geometry) has no CartoSym
    conceptual-model representation yet — the reader must raise, not drop
    it silently.
    """

    def test_se_geometry_child_raises(self):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>L</se:Name><UserStyle><se:Name>S</se:Name>"
            "<se:FeatureTypeStyle><se:Rule><se:LineSymbolizer>"
            "<se:Geometry><ogc:PropertyName>centerline</ogc:PropertyName>"
            "</se:Geometry>"
            '<se:Stroke><se:SvgParameter name="stroke">#000000</se:SvgParameter>'
            "</se:Stroke></se:LineSymbolizer>"
            "</se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        with pytest.raises(NotImplementedError, match="symbolizer geometry"):
            SldReader().read(xml)


class TestReadOutOfScopeRaises:
    def test_raster_symbolizer_contrast_enhancement_raises(self):
        with pytest.raises(NotImplementedError):
            _read("10-out-of-scope-raster.sld")

    def _read_string(self, xml):
        return SldReader().read(xml)

    def test_graphic_fill_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:PolygonSymbolizer><se:Fill>
      <se:GraphicFill><se:Graphic/></se:GraphicFill>
    </se:Fill></se:PolygonSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_external_graphic_without_online_resource_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:PointSymbolizer><se:Graphic><se:ExternalGraphic>
      <se:Format>image/png</se:Format>
    </se:ExternalGraphic></se:Graphic></se:PointSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_incomplete_rgb_channel_triple_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:RasterSymbolizer><se:ChannelSelection>
      <se:RedChannel><se:SourceChannelName>B04</se:SourceChannelName></se:RedChannel>
      <se:GreenChannel><se:SourceChannelName>B03</se:SourceChannelName></se:GreenChannel>
    </se:ChannelSelection></se:RasterSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_selected_channel_contrast_enhancement_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:RasterSymbolizer><se:ChannelSelection>
      <se:GrayChannel>
        <se:SourceChannelName>elevation</se:SourceChannelName>
        <se:ContrastEnhancement><se:Normalize/></se:ContrastEnhancement>
      </se:GrayChannel>
    </se:ChannelSelection></se:RasterSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_colormap_interpolate_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:RasterSymbolizer><se:ColorMap>
      <se:Interpolate><se:LookupValue>Rasterdata</se:LookupValue></se:Interpolate>
    </se:ColorMap></se:RasterSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_shaded_relief_brightness_only_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:RasterSymbolizer><se:ShadedRelief>
      <se:BrightnessOnly/>
    </se:ShadedRelief></se:RasterSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)


class TestReadImage:
    def test_image_marker_uri_format_and_anchor_point(self):
        style = _read("15-image-marker.sld")
        sym = style.styling_rules[0].symbolizer
        el = sym.marker.elements[0]
        assert el["type"] == "Image"
        assert el["image"] == {
            "uri": "http://example.com/parkingIcon.png",
            "type": "image/png",
        }
        assert el["hotSpot"] == [{"pc": 50}, {"pc": 50}]


class TestReadRaster:
    def test_single_channel_colormap(self):
        style = _read("11-raster-single-channel-colormap.sld")
        sym = style.styling_rules[0].symbolizer
        assert sym.single_channel == {"property": "elevation"}
        assert sym.color_map[0] == [900, [96, 136, 73]]
        assert sym.color_map[-1] == [2500, [250, 250, 250]]

    def test_color_channels_rgb(self):
        style = _read("12-raster-color-channels-rgb.sld")
        sym = style.styling_rules[0].symbolizer
        assert sym.color_channels == [
            {"property": "B04"},
            {"property": "B03"},
            {"property": "B02"},
        ]
        assert sym.alpha_channel is None

    def test_colormap_named_colors(self):
        style = _read("13-raster-colormap-named-colors.sld")
        sym = style.styling_rules[0].symbolizer
        assert sym.color_map[1] == [0.15, [128, 128, 128]]

    def test_shaded_relief_factor(self):
        style = _read("14-raster-shaded-relief.sld")
        sym = style.styling_rules[0].symbolizer
        assert sym.hill_shading == {"factor": 56}


class TestReadPropertyDrivenColor:
    """``fill``/``stroke`` colour as ``ogc:PropertyName`` / ``se:Recode``."""

    def _read_string(self, xml):
        return SldReader().read(xml)

    _RECODE_XML = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:PolygonSymbolizer><se:Fill>
      <se:SvgParameter name="fill">
        <se:Recode fallbackValue="#000000">
          <se:LookupValue><ogc:PropertyName>weight</ogc:PropertyName></se:LookupValue>
          <se:MapItem><se:Data>15</se:Data><se:Value>#6495ED</se:Value></se:MapItem>
          <se:MapItem><se:Data>10</se:Data><se:Value>#B0C4DE</se:Value></se:MapItem>
        </se:Recode>
      </se:SvgParameter>
    </se:Fill></se:PolygonSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""

    def test_bare_property_name_fill_color(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:PolygonSymbolizer><se:Fill>
      <se:SvgParameter name="fill">
        <ogc:PropertyName>COLOR_FIELD</ogc:PropertyName>
      </se:SvgParameter>
    </se:Fill></se:PolygonSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        sym = self._read_string(xml).styling_rules[0].symbolizer
        assert sym.fill.color.to_dict() == {"property": "COLOR_FIELD"}

    def test_bare_property_name_stroke_color(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:LineSymbolizer><se:Stroke>
      <se:SvgParameter name="stroke">
        <ogc:PropertyName>COLOR_FIELD</ogc:PropertyName>
      </se:SvgParameter>
    </se:Stroke></se:LineSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        sym = self._read_string(xml).styling_rules[0].symbolizer
        assert sym.stroke.color.to_dict() == {"property": "COLOR_FIELD"}

    def test_recode_fill_color_maps_to_match_expression(self):
        sym = self._read_string(self._RECODE_XML).styling_rules[0].symbolizer
        assert sym.fill.color.to_dict() == {
            "op": "match",
            "args": [{"property": "weight"}, 15, "#6495ED", 10, "#B0C4DE", "#000000"],
        }

    def test_recode_without_fallback_value_raises(self):
        xml = self._RECODE_XML.replace(' fallbackValue="#000000"', "")
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_recode_with_non_property_name_lookup_raises(self):
        xml = self._RECODE_XML.replace(
            "<ogc:PropertyName>weight</ogc:PropertyName>",
            "<ogc:Literal>weight</ogc:Literal>",
        )
        with pytest.raises(NotImplementedError):
            self._read_string(xml)

    def test_recode_without_map_item_raises(self):
        import re

        xml = re.sub(r"<se:MapItem>.*?</se:MapItem>", "", self._RECODE_XML, flags=re.S)
        with pytest.raises(NotImplementedError):
            self._read_string(xml)


class TestReadPropertyDrivenWidth:
    """``stroke-width`` as ``ogc:PropertyName`` / ``ogc:Function`` arithmetic.

    Hand-written XML (not generated by our own writer), to catch a bug the
    writer and reader might otherwise agree on while both disagreeing with
    the real SLD/SE spec.
    """

    def _read_string(self, xml):
        return SldReader().read(xml)

    def test_bare_property_name_width(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:LineSymbolizer><se:Stroke>
      <se:SvgParameter name="stroke-width">
        <ogc:PropertyName>LINE_WIDTH</ogc:PropertyName>
      </se:SvgParameter>
    </se:Stroke></se:LineSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        sym = self._read_string(xml).styling_rules[0].symbolizer
        assert sym.stroke.width.to_dict() == {"property": "LINE_WIDTH"}

    def test_ogc_function_div_width(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:LineSymbolizer><se:Stroke>
      <se:SvgParameter name="stroke-width">
        <ogc:Function name="Div">
          <ogc:PropertyName>population</ogc:PropertyName>
          <ogc:Literal>1000</ogc:Literal>
        </ogc:Function>
      </se:SvgParameter>
    </se:Stroke></se:LineSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        sym = self._read_string(xml).styling_rules[0].symbolizer
        assert sym.stroke.width.to_dict() == {
            "op": "/",
            "args": [{"property": "population"}, 1000],
        }

    def test_unmapped_function_name_raises(self):
        xml = """<?xml version='1.0' encoding='UTF-8'?>
<StyledLayerDescriptor
    xmlns="http://www.opengis.net/sld"
    xmlns:se="http://www.opengis.net/se"
    xmlns:ogc="http://www.opengis.net/ogc"
    version="1.1.0">
  <NamedLayer><UserStyle><se:FeatureTypeStyle><se:Rule>
    <se:LineSymbolizer><se:Stroke>
      <se:SvgParameter name="stroke-width">
        <ogc:Function name="Sqrt">
          <ogc:PropertyName>population</ogc:PropertyName>
        </ogc:Function>
      </se:SvgParameter>
    </se:Stroke></se:LineSymbolizer>
  </se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>
</StyledLayerDescriptor>"""
        with pytest.raises(NotImplementedError):
            self._read_string(xml)


class TestReadPathVsStringHeuristic:
    def test_path_and_raw_string_give_identical_results(self):
        path = FIXTURES / "1-polygon-fill-stroke.sld"
        from_path = SldReader().read(path)
        from_string = SldReader().read(path.read_text(encoding="utf-8"))
        assert from_path == from_string
