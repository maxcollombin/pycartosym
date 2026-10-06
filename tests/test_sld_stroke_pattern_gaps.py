"""``Stroke.patternGap``/``patternInitialGap`` <-> ``se:Gap``/``se:InitialGap``."""

import pytest
from lxml import etree

from pycartosym.codecs.sld.reader import SldReader
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style

from ._xsd import assert_sld_valid

NS = {"se": "http://www.opengis.net/se"}


def _style(stroke: dict) -> Style:
    return Style.from_dict({"stylingRules": [{"symbolizer": {"stroke": stroke}}]})


_CROSSES = {
    "color": "blue",
    "width": {"px": 4},
    "pattern": {"type": "Dot", "color": "red", "size": {"px": 18}},
    "patternGap": 25,
    "patternInitialGap": 9,
}


def test_gaps_follow_the_graphic_in_se_order():
    root = etree.fromstring(SldWriter().write(_style(_CROSSES)).encode("utf-8"))
    assert_sld_valid(root)
    graphic_stroke = root.find(".//se:Stroke/se:GraphicStroke", NS)
    tags = [etree.QName(c).localname for c in graphic_stroke]
    assert tags == ["Graphic", "InitialGap", "Gap"]
    assert graphic_stroke.find("se:Gap", NS).text == "25"
    assert graphic_stroke.find("se:InitialGap", NS).text == "9"


def test_gaps_round_trip():
    style = SldReader().read(SldWriter().write(_style(_CROSSES)))
    stroke = style.styling_rules[0].symbolizer.stroke
    assert (stroke.pattern_gap, stroke.pattern_initial_gap) == (25, 9)


def test_csjson_aliases():
    stroke = _style(_CROSSES).styling_rules[0].symbolizer.stroke
    dumped = stroke.model_dump(by_alias=True, exclude_none=True)
    assert dumped["patternGap"] == 25 and dumped["patternInitialGap"] == 9


def test_a_gap_without_a_pattern_is_rejected():
    with pytest.raises(NotImplementedError, match="patternGap"):
        SldWriter().write(_style({"color": "blue", "patternGap": 25}))


def test_well_known_shapes_are_public_and_written_as_their_name():
    from pycartosym.codecs.sld import WELL_KNOWN_SHAPES

    nodes = [
        {"x": {"px": x * 10}, "y": {"px": y * 10}} for x, y in WELL_KNOWN_SHAPES["x"]
    ]
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "ClosedPath",
                                    "nodes": nodes,
                                    "fill": {"color": "red"},
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )
    root = etree.fromstring(SldWriter().write(style).encode("utf-8"))
    assert root.find(".//se:WellKnownName", NS).text == "x"
