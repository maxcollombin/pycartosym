"""viz.pass <-> order of se:FeatureTypeStyle elements in a se:UserStyle."""

import pytest
from lxml import etree

from pycartosym.codecs.sld.reader import SldReader
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style

from ._xsd import assert_sld_valid

NS = {"se": "http://www.opengis.net/se"}


def _pass(n):
    return {"op": "=", "args": [{"sysId": "viz.pass"}, n]}


def _layer(name):
    return {"op": "=", "args": [{"sysId": "dataLayer.id"}, name]}


def _and(*args):
    return {"op": "and", "args": list(args)}


def _stroke(color, width):
    return {"stroke": {"color": color, "width": {"px": width}}}


def _casing_style():
    # Listed inner line first: the pass, not the rule order, decides the drawing order.
    return Style.from_dict(
        {
            "stylingRules": [
                {
                    "selector": _and(_layer("Roads"), _pass(1)),
                    "symbolizer": _stroke("white", 4),
                },
                {
                    "selector": _and(_layer("Roads"), _pass(0)),
                    "symbolizer": _stroke("gray", 7),
                },
            ]
        }
    )


def _strokes(root):
    return [
        [p.text for p in fts.iterfind(".//se:SvgParameter[@name='stroke']", NS)]
        for fts in root.iterfind(".//se:FeatureTypeStyle", NS)
    ]


def test_each_pass_is_a_feature_type_style_in_pass_order():
    xml = SldWriter().write(_casing_style())
    root = etree.fromstring(xml.encode("utf-8"))
    assert_sld_valid(root)
    assert _strokes(root) == [["#808080"], ["#ffffff"]]
    names = [el.text for el in root.iterfind(".//se:FeatureTypeName", NS)]
    assert names == ["Roads", "Roads"]


def test_nested_pass_rules_under_a_symbolizer_less_layer_rule():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "selector": _layer("Roads"),
                    "nestedRules": [
                        {"selector": _pass(0), "symbolizer": _stroke("gray", 7)},
                        {"selector": _pass(1), "symbolizer": _stroke("white", 4)},
                    ],
                }
            ]
        }
    )
    root = etree.fromstring(SldWriter().write(style).encode("utf-8"))
    assert _strokes(root) == [["#808080"], ["#ffffff"]]


def test_rules_with_and_without_a_pass_are_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {"selector": _pass(1), "symbolizer": _stroke("white", 4)},
                {"symbolizer": _stroke("gray", 7)},
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="viz.pass"):
        SldWriter().write(style)


def test_attribute_driven_pass_is_rejected():
    selector = {
        "op": "=",
        "args": [
            {"sysId": "viz.pass"},
            {"op": "+", "args": [{"property": "z_order"}, 1]},
        ],
    }
    style = Style.from_dict(
        {"stylingRules": [{"selector": selector, "symbolizer": _stroke("gray", 7)}]}
    )
    with pytest.raises(NotImplementedError, match="viz.pass"):
        SldWriter().write(style)


def test_reader_numbers_several_feature_type_styles_as_passes():
    style = SldReader().read(SldWriter().write(_casing_style()))
    selectors = [rule.selector for rule in style.styling_rules]
    assert selectors == [
        _and(_layer("Roads"), _pass(0)),
        _and(_layer("Roads"), _pass(1)),
    ]


def test_reader_gives_a_single_feature_type_style_no_pass():
    style = Style.from_dict(
        {
            "stylingRules": [
                {"selector": _layer("Roads"), "symbolizer": _stroke("gray", 7)}
            ]
        }
    )
    read = SldReader().read(SldWriter().write(style))
    assert read.styling_rules[0].selector == _layer("Roads")


def test_casing_round_trips():
    xml = SldWriter().write(_casing_style())
    assert SldWriter().write(SldReader().read(xml)) == xml
