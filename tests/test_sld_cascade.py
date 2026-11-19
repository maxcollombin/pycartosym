"""Tests for CartoSym nested-rule cascade flattening in the SLD/SE writer.

See ``tests/test_cascade.py`` for the codec-agnostic
``flatten_cascade_rules`` unit tests (``codecs/_cascade.py``). SE 1.1.0
has no cascade, so the writer pre-flattens each subtree into independent
``se:Rule``s before emitting them.
"""

from lxml import etree

from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style

NS = {
    "sld": "http://www.opengis.net/sld",
    "se": "http://www.opengis.net/se",
    "ogc": "http://www.opengis.net/ogc",
}


class TestCascadeThroughWriter:
    def _write(self, style_dict):
        style = Style.from_dict(style_dict)
        return etree.fromstring(SldWriter().write(style).encode("utf-8"))

    def test_nested_scale_and_property_cascade_produces_independent_rules(self):
        root = self._write(
            {
                "stylingRules": [
                    {
                        "name": "Landuse",
                        "selector": {
                            "op": "=",
                            "args": [{"sysId": "dataLayer.id"}, "Landuse"],
                        },
                        "symbolizer": {"visibility": False},
                        "nestedRules": [
                            {
                                "selector": {
                                    "op": "<",
                                    "args": [{"sysId": "viz.sd"}, 200000],
                                },
                                "symbolizer": {
                                    "fill": {"color": "gray", "opacity": 0.5},
                                    "stroke": {"color": "gray", "width": {"px": 2}},
                                },
                                "nestedRules": [
                                    {
                                        "selector": {
                                            "op": "=",
                                            "args": [
                                                {"property": "FunctionCode"},
                                                "park",
                                            ],
                                        },
                                        "symbolizer": {"fill": {"color": "darkGreen"}},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )
        rules = root.findall(".//se:Rule", NS)
        # base visibility:false rule is dropped; two renderable rules remain
        assert len(rules) == 2
        # both under one FeatureTypeName
        assert [e.text for e in root.findall(".//se:FeatureTypeName", NS)] == [
            "Landuse"
        ]
        # both carry the inherited MaxScaleDenominator
        assert all(r.find("se:MaxScaleDenominator", NS).text == "200000" for r in rules)
        # the refined rule selects the park; the base rule excludes it
        filtered = [r for r in rules if r.find("ogc:Filter", NS) is not None]
        assert len(filtered) == 2
        assert [r.find(".//ogc:Not", NS) is not None for r in filtered] == [True, False]
        assert all(r.find(".//ogc:Literal", NS).text == "park" for r in filtered)
        # refined rule's fill is the override; parent rule's is gray
        fills = {
            r.find(".//se:PolygonSymbolizer/se:Fill/se:SvgParameter", NS).text
            for r in rules
        }
        assert fills == {"#808080", "#006400"}

    def test_selectorless_nested_rule_merges_into_its_parent_rule(self):
        root = self._write(
            {
                "stylingRules": [
                    {
                        "name": "Roads",
                        "selector": {
                            "op": "=",
                            "args": [{"property": "Class"}, "primary"],
                        },
                        "symbolizer": {"stroke": {"color": "red", "width": {"px": 3}}},
                        "nestedRules": [
                            {
                                "symbolizer": {
                                    "stroke": {"color": "gray", "width": {"px": 1}}
                                }
                            }
                        ],
                    }
                ]
            }
        )
        # not an else rule and not a second rule drawn over the parent: a
        # nested rule without selector is the parent with its brackets removed
        assert root.find(".//se:ElseFilter", NS) is None
        assert root.find(".//ogc:ElseFilter", NS) is None
        (rule,) = root.findall(".//se:Rule", NS)
        assert rule.findtext(".//ogc:PropertyName", namespaces=NS) == "Class"
        assert rule.find(".//se:SvgParameter[@name='stroke']", NS).text == "#808080"
        assert rule.find(".//se:SvgParameter[@name='stroke-width']", NS).text == "1"
