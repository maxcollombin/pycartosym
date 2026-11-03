"""Sizes in the SLD/SE codec: screen units converted, ground units in ``uom``."""

import pytest
from lxml import etree

from pycartosym.codecs.sld._dialect import SLD_1_0_0
from pycartosym.codecs.sld.reader import SldReader
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style

from ._xsd import assert_sld_valid

NS = {"se": "http://www.opengis.net/se"}
UOM = "http://www.opengeospatial.org/se/units/"


def _style(stroke_width, extra=None):
    symbolizer = {"stroke": {"color": [0, 0, 0], "width": stroke_width}}
    symbolizer.update(extra or {})
    return Style.from_dict({"stylingRules": [{"symbolizer": symbolizer}]})


def _line(style, writer=None):
    xml = (writer or SldWriter()).write(style)
    root = etree.fromstring(xml.encode("utf-8"))
    return root.find(".//se:LineSymbolizer", NS), root


def _width(line):
    return line.find("se:Stroke/se:SvgParameter[@name='stroke-width']", NS).text


class TestWriteUnits:
    def test_pixels_need_no_uom(self):
        line, _ = _line(_style({"px": 2}))
        assert line.get("uom") is None
        assert _width(line) == "2"

    def test_millimetres_become_pixels_at_0_28_mm(self):
        line, _ = _line(_style({"mm": 0.28}))
        assert _width(line) == "1"
        assert line.get("uom") == UOM + "pixel"

    def test_other_screen_units_use_the_same_pixel_size(self):
        line, _ = _line(_style({"cm": 0.28}))
        assert _width(line) == "10"
        line, _ = _line(_style({"in": 1}))
        assert _width(line) == "90.7143"
        line, _ = _line(_style({"pt": 72}))
        assert _width(line) == "90.7143"

    def test_metres_set_uom(self):
        line, _ = _line(_style({"m": 5}))
        assert _width(line) == "5"
        assert line.get("uom") == UOM + "metre"

    def test_feet_set_uom(self):
        line, _ = _line(_style({"ft": 3}))
        assert line.get("uom") == UOM + "foot"

    def test_uom_is_per_symbolizer_element(self):
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "stroke": {"color": [0, 0, 0], "width": {"m": 2}},
                            "marker": {
                                "elements": [
                                    {
                                        "type": "Circle",
                                        "radius": {"px": 4},
                                        "fill": {"color": [0, 0, 0]},
                                    }
                                ]
                            },
                        }
                    }
                ]
            }
        )
        xml = SldWriter().write(style)
        root = etree.fromstring(xml.encode("utf-8"))
        line = root.find(".//se:LineSymbolizer", NS)
        point = root.find(".//se:PointSymbolizer", NS)
        assert line.get("uom") == UOM + "metre"
        assert point.get("uom") is None

    def test_ground_and_pixel_sizes_in_one_symbolizer_raise(self):
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "marker": {
                                "elements": [
                                    {
                                        "type": "Circle",
                                        "radius": {"m": 2},
                                        "fill": {"color": [0, 0, 0]},
                                        "outline": {
                                            "color": [0, 0, 0],
                                            "thickness": {"px": 1},
                                        },
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="mixes units"):
            SldWriter().write(style)

    def test_em_cannot_be_converted(self):
        with pytest.raises(NotImplementedError, match="em"):
            _line(_style({"em": 2}))

    def test_plain_sld_converts_screen_units_without_uom(self):
        xml = SldWriter(SLD_1_0_0).write(_style({"mm": 0.28}))
        root = etree.fromstring(xml.encode("utf-8"))
        assert not root.xpath("//@uom")
        param = root.xpath("//*[local-name()='CssParameter'][@name='stroke-width']")
        assert param[0].text == "1"

    def test_output_with_uom_is_schema_valid(self):
        assert_sld_valid(SldWriter().write(_style({"m": 5})))

    def test_plain_sld_rejects_ground_units(self):
        with pytest.raises(NotImplementedError, match="uom"):
            SldWriter(SLD_1_0_0).write(_style({"m": 2}))


class TestReadUom:
    @staticmethod
    def _read(uom_attr):
        xml = (
            '<StyledLayerDescriptor version="1.1.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:se="http://www.opengis.net/se" '
            'xmlns:ogc="http://www.opengis.net/ogc">'
            "<NamedLayer><se:Name>l</se:Name><UserStyle><se:FeatureTypeStyle>"
            f"<se:Rule><se:LineSymbolizer{uom_attr}><se:Stroke>"
            '<se:SvgParameter name="stroke">#000000</se:SvgParameter>'
            '<se:SvgParameter name="stroke-width">4</se:SvgParameter>'
            "</se:Stroke></se:LineSymbolizer></se:Rule>"
            "</se:FeatureTypeStyle></UserStyle></NamedLayer>"
            "</StyledLayerDescriptor>"
        )
        return SldReader().read(xml)

    def test_no_uom_is_pixels(self):
        width = self._read("").styling_rules[0].symbolizer.stroke.width
        assert str(width.unit.value) == "px" and width.value == 4

    def test_metre_uom_is_read_as_metres(self):
        style = self._read(f' uom="{UOM}metre"')
        width = style.styling_rules[0].symbolizer.stroke.width
        assert str(width.unit.value) == "m" and width.value == 4

    def test_unknown_uom_raises(self):
        with pytest.raises(NotImplementedError, match="uom"):
            self._read(' uom="http://example.com/units/furlong"')

    def test_round_trip_of_metres(self):
        line, _ = _line(_style({"m": 5}))
        xml = etree.tostring(line.getroottree(), encoding="unicode")
        back = SldReader().read(xml)
        width = back.styling_rules[0].symbolizer.stroke.width
        assert str(width.unit.value) == "m" and width.value == 5
