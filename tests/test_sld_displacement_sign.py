"""CartoSym's position y points down, se:DisplacementY points up."""

from lxml import etree

from pycartosym.codecs.sld.reader import SldReader
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style

NS = {"se": "http://www.opengis.net/se", "ogc": "http://www.opengis.net/ogc"}


def _style(position):
    return Style.from_dict(
        {
            "stylingRules": [
                {
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Circle",
                                    "position": position,
                                    "radius": {"px": 5},
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )


def _displacement(xml):
    root = etree.fromstring(xml.encode("utf-8"))
    return [root.find(f".//se:Displacement/se:Displacement{a}", NS) for a in ("X", "Y")]


def test_graphic_position_down_is_displacement_y_negated():
    xml = SldWriter().write(_style({"x": 4, "y": 6}))
    x, y = _displacement(xml)
    assert (x.text, y.text) == ("4", "-6")


def test_zero_y_is_not_written_as_negative_zero():
    xml = SldWriter().write(_style({"x": 4, "y": 0}))
    assert _displacement(xml)[1].text == "0"


def test_displacement_y_is_read_back_as_the_same_position():
    xml = SldWriter().write(_style({"x": 4, "y": 6}))
    back = SldReader().read(xml)
    position = back.styling_rules[0].symbolizer.marker.elements[0]["position"]
    assert position["x"] == 4 and position["y"] == 6


def test_property_driven_y_round_trips():
    xml = SldWriter().write(_style({"x": 0, "y": {"property": "dy"}}))
    assert "Mul" in xml
    back = SldReader().read(xml)
    position = back.styling_rules[0].symbolizer.marker.elements[0]["position"]
    assert position["y"] == {"property": "dy"}


def _label_style(position):
    return Style.from_dict(
        {
            "stylingRules": [
                {
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "abc",
                                    "position": position,
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )


def test_label_position_down_is_displacement_y_negated_and_read_back():
    xml = SldWriter().write(_label_style({"x": 2, "y": 5}))
    root = etree.fromstring(xml.encode("utf-8"))
    y = root.find(".//se:PointPlacement/se:Displacement/se:DisplacementY", NS)
    assert y is not None and y.text == "-5"
    back = SldReader().read(xml)
    position = back.styling_rules[0].symbolizer.label.elements[0].position
    assert position.y == 5
