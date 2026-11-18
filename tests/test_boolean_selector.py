"""A boolean `selector`: `true` selects everything, `false` nothing."""

from pycartosym.codecs.maplibre.writer import MaplibreWriter
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style


def _style(selector):
    return Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "a",
                    "selector": selector,
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )


def test_csjson_boolean_selector_is_read_and_kept():
    dumped = _style(True).model_dump(by_alias=True, exclude_none=True)
    assert dumped["stylingRules"][0]["selector"] is True


def test_boolean_selector_round_trips_through_cscss():
    converter = Converter()
    cscss = converter.style_to_cscss(_style(True))
    assert "[true]" in cscss
    back = converter.cscss_to_csjson(cscss)
    assert back["stylingRules"][0]["selector"] is True


def test_true_selector_has_no_filter_in_sld_and_maplibre():
    assert "Filter" not in SldWriter().write(_style(True))
    layer = MaplibreWriter().write(_style(True))["layers"][0]
    assert "filter" not in layer


def test_false_selector_rule_is_not_written():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "never",
                    "selector": False,
                    "symbolizer": {"fill": {"color": "red"}},
                },
                {"name": "always", "symbolizer": {"fill": {"color": "blue"}}},
            ]
        }
    )
    sld = SldWriter().write(style)
    assert "#0000ff" in sld and "#ff0000" not in sld
    layers = MaplibreWriter().write(style)["layers"]
    assert [layer["id"] for layer in layers] == ["always"]
