"""feature.pass <-> several symbolizers of one se:Rule (#203)."""

import json

from lxml import etree

from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style

from ._xsd import assert_sld_valid

NS = {"se": "http://www.opengis.net/se"}


def _kind_and_pass(n):
    return {
        "op": "and",
        "args": [
            {"op": "=", "args": [{"property": "kind"}, "road"]},
            {"op": "=", "args": [{"sysId": "feature.pass"}, n]},
        ],
    }


def _stroke(color, width):
    return {"stroke": {"color": color, "width": {"px": width}}}


def test_cscss_reads_feature_pass_as_system_identifier():
    text = (
        "[kind = 'road'] {\n"
        "  [feature.pass = 0] { stroke: { color: black; width: 5 px; }; }\n"
        "}\n"
    )
    out = json.dumps(Converter().cscss_to_csjson(text))
    assert '"sysId": "feature.pass"' in out
    assert '"property": "feature.pass"' not in out


def test_feature_passes_become_symbolizers_of_one_rule_in_pass_order():
    # Listed outer pass first: the pass, not the rule order, decides the order.
    style = Style.from_dict(
        {
            "stylingRules": [
                {"selector": _kind_and_pass(1), "symbolizer": _stroke("white", 3)},
                {"selector": _kind_and_pass(0), "symbolizer": _stroke("black", 5)},
            ]
        }
    )
    root = etree.fromstring(SldWriter().write(style).encode("utf-8"))
    assert_sld_valid(root)
    assert len(root.findall(".//se:Rule", NS)) == 1
    colors = [p.text for p in root.iterfind(".//se:SvgParameter[@name='stroke']", NS)]
    assert colors == ["#000000", "#ffffff"]


def _read_rule(symbolizers):
    from pycartosym.codecs.sld.reader import SldReader

    sld = (
        '<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" '
        'xmlns:se="http://www.opengis.net/se" version="1.1.0"><NamedLayer>'
        "<UserStyle><se:FeatureTypeStyle><se:Rule>"
        f"{symbolizers}"
        "</se:Rule></se:FeatureTypeStyle></UserStyle></NamedLayer>"
        "</StyledLayerDescriptor>"
    )
    return SldReader().read(sld)


def _line(color):
    return (
        "<se:LineSymbolizer><se:Stroke>"
        f'<se:SvgParameter name="stroke">{color}</se:SvgParameter>'
        "</se:Stroke></se:LineSymbolizer>"
    )


def test_sld_reader_reads_a_repeated_symbolizer_kind_as_feature_passes():
    style = _read_rule(_line("#000000") + _line("#ffffff"))
    rules = style.model_dump(by_alias=True, exclude_none=True)["stylingRules"]
    assert [r["selector"]["args"][1] for r in rules] == [0, 1]
    assert rules[0]["selector"]["args"][0] == {"sysId": "feature.pass"}
    assert [r["symbolizer"]["stroke"]["color"] for r in rules] == [
        [0, 0, 0],
        [255, 255, 255],
    ]


def test_sld_reader_keeps_different_symbolizer_kinds_in_one_rule():
    polygon = (
        "<se:PolygonSymbolizer><se:Fill>"
        '<se:SvgParameter name="fill">#ff0000</se:SvgParameter>'
        "</se:Fill></se:PolygonSymbolizer>"
    )
    style = _read_rule(polygon + _line("#000000"))
    assert len(style.styling_rules) == 1
