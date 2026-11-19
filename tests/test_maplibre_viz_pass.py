"""MapLibre: ``viz.pass`` orders the layers, ``feature.pass`` has no mapping."""

import pytest

from pycartosym.codecs.maplibre import MaplibreWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style

_ROADS = """
Zones { fill: { color: lightGray; }; }
Roads
{
   [viz.pass = 1] { stroke: { color: white; width: 3 px; }; }
   [viz.pass = 0] { stroke: { color: black; width: 5 px; }; }
}
"""


def _layers(source):
    style = Style.from_dict(Converter().cscss_to_csjson(source))
    return MaplibreWriter().write(style)["layers"]


def test_layers_follow_the_pass_order():
    layers = _layers(_ROADS)
    colors = [layer.get("paint", {}).get("line-color") for layer in layers]
    assert colors == [None, "black", "white"]  # the fill rule is pass 0, first


def test_the_pass_test_is_not_left_in_the_filter():
    assert all("filter" not in layer for layer in _layers(_ROADS))


def test_rules_without_pass_keep_their_document_order():
    layers = _layers("A { fill: { color: red; }; }\nB { fill: { color: blue; }; }")
    assert [layer["id"] for layer in layers] == ["A", "B"]


def test_feature_pass_has_no_mapping():
    source = "Roads { [feature.pass = 0] { stroke: { color: black; }; } }"
    with pytest.raises(NotImplementedError):
        _layers(source)
