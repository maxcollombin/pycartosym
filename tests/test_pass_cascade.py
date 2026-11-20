"""A later pass resolves its Symbolizer from every rule selecting the feature.

What a pass decides is only whether the feature is drawn: in pass 0 every
feature a rule selects is drawn, in a later pass only the features that a rule
testing ``viz.pass`` selects. A property set by a rule that does not test the
pass (here the stroke width) still applies in that later pass.
"""

from lxml import etree

from pycartosym.codecs.maplibre import MaplibreWriter
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style

_SOURCE = """
{ fill: null; stroke: null; marker: null; }
Roads
{
   stroke: { color: gray; width: 3 px; };
   [kind = 'a'] { [viz.pass = 1] { stroke: { color: red; }; } }
}
"""

_SE = {"se": "http://www.opengis.net/se", "ogc": "http://www.opengis.net/ogc"}


def _style() -> Style:
    return Style.from_dict(Converter().cscss_to_csjson(_SOURCE))


def test_maplibre_pass_one_inherits_the_width_and_selects_only_its_features():
    layers = MaplibreWriter().write(_style())["layers"]
    paint = [layer["paint"] for layer in layers]
    assert paint[-1] == {"line-color": "red", "line-width": 3.0}
    assert layers[-1]["filter"] == ["==", ["get", "kind"], "a"]


def test_sld_pass_one_inherits_the_width_and_selects_only_its_features():
    root = etree.fromstring(SldWriter().write(_style()).encode("utf-8"))
    pass_one = root.findall(".//se:FeatureTypeStyle", _SE)[-1]
    params = {
        p.get("name"): p.text for p in pass_one.findall(".//se:SvgParameter", _SE)
    }
    assert params == {"stroke": "#ff0000", "stroke-width": "3"}
    assert pass_one.findall(".//ogc:Literal", _SE)[0].text == "a"
