"""A conditional expression in a symbolizer is written as filtered rules."""

import pytest
from lxml import etree

from pycartosym.codecs.sld._conditional import MAX_VARIANTS
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style

from ._xsd import assert_sld_valid

NS = {
    "se": "http://www.opengis.net/se",
    "ogc": "http://www.opengis.net/ogc",
}


def _eq(prop, value):
    return {"op": "=", "args": [{"property": prop}, value]}


def _cond(cond, then, otherwise):
    return {"op": "?:", "args": [cond, then, otherwise]}


def _label(size):
    return {
        "label": {
            "elements": [
                {"type": "Text", "text": {"property": "n"}, "font": {"size": size}}
            ]
        }
    }


def _write(symbolizer, selector=None):
    rule = {"symbolizer": symbolizer}
    if selector is not None:
        rule["selector"] = selector
    xml = SldWriter().write(Style.from_dict({"stylingRules": [rule]}))
    assert_sld_valid(xml)
    return etree.fromstring(xml.encode("utf-8"))


def _sizes(root):
    return [
        r.find(".//se:SvgParameter[@name='font-size']", NS).text
        for r in root.findall(".//se:Rule", NS)
    ]


class TestSplit:
    def test_one_conditional_gives_a_rule_per_branch(self):
        root = _write(_label(_cond(_eq("k", "x"), 8, 10)))
        rules = root.findall(".//se:Rule", NS)
        assert _sizes(root) == ["8", "10"]
        first, second = (r.find("ogc:Filter", NS) for r in rules)
        assert first.find("ogc:PropertyIsEqualTo/ogc:Literal", NS).text == "x"
        assert second.find("ogc:Not/ogc:PropertyIsEqualTo", NS) is not None

    def test_the_selector_is_kept_in_every_rule(self):
        root = _write(_label(_cond(_eq("k", "x"), 8, 10)), _eq("t", "a"))
        for rule in root.findall(".//se:Rule", NS):
            names = [p.text for p in rule.findall(".//ogc:PropertyName", NS)]
            assert names[0] == "t"

    def test_no_conditional_is_one_unfiltered_rule(self):
        root = _write(_label(8))
        assert _sizes(root) == ["8"]
        assert root.find(".//ogc:Filter", NS) is None

    def test_a_condition_used_twice_splits_once(self):
        cond = _eq("k", "x")
        symbolizer = {
            "stroke": {"color": [0, 0, 0], "width": _cond(cond, 2, 3)},
            **_label(_cond(cond, 8, 10)),
        }
        root = _write(symbolizer)
        assert _sizes(root) == ["8", "10"]

    def test_a_chain_gives_one_rule_more_than_its_conditions(self):
        size = _cond(_eq("k", "a"), 1, _cond(_eq("k", "b"), 2, 3))
        root = _write(_label(size))
        assert _sizes(root) == ["1", "2", "3"]

    def test_independent_conditions_multiply(self):
        symbolizer = {
            "stroke": {"color": [0, 0, 0], "width": _cond(_eq("a", 1), 2, 3)},
            **_label(_cond(_eq("b", 1), 8, 10)),
        }
        assert len(_write(symbolizer).findall(".//se:Rule", NS)) == 4

    def test_equalities_on_one_property_never_meet(self):
        symbolizer = {
            "stroke": {"color": [0, 0, 0], "width": _cond(_eq("k", "a"), 2, 3)},
            **_label(_cond(_eq("k", "b"), 8, 10)),
        }
        # k='a' with k='b' is impossible: 3 rules, not 4
        assert len(_write(symbolizer).findall(".//se:Rule", NS)) == 3

    def test_too_many_rules_raise(self):
        symbolizer = {
            "stroke": {"color": [0, 0, 0], "width": _cond(_eq("p0", 1), 2, 3)},
            "fill": {"color": _cond(_eq("p1", 1), [1, 1, 1], [2, 2, 2])},
            **_label(_cond(_eq("p2", 1), 8, 10)),
            "marker": {
                "elements": [
                    {
                        "type": "Circle",
                        "radius": _cond(_eq("p3", 1), 1, 2),
                        "fill": {"color": _cond(_eq("p4", 1), [1, 1, 1], [2, 2, 2])},
                    }
                ]
            },
        }
        with pytest.raises(NotImplementedError, match=str(MAX_VARIANTS)):
            _write(symbolizer)

    def test_a_scale_condition_becomes_a_scale_range(self):
        scale = {"sysId": "viz.sd"}
        cond = {"op": "<", "args": [scale, 25000]}
        root = _write(_label(_cond(cond, 8, 10)))
        rules = root.findall(".//se:Rule", NS)
        assert [r.find("se:MaxScaleDenominator", NS) is not None for r in rules] == [
            True,
            False,
        ]
        assert rules[1].find("se:MinScaleDenominator", NS).text == "25000"
        assert root.find(".//ogc:Filter", NS) is None

    def test_the_source_style_is_not_modified(self):
        style = Style.from_dict(
            {"stylingRules": [{"symbolizer": _label(_cond(_eq("k", "x"), 8, 10))}]}
        )
        SldWriter().write(style)
        element = style.styling_rules[0].symbolizer.label.elements[0]
        assert element.font["size"]["op"] == "?:"
