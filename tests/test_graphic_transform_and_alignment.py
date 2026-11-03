"""A graphic's transform.orientation and an alignment by expressions."""

import pytest

from pycartosym.converter import Converter
from pycartosym.parser import CartoSymParser


def _json(css: str) -> dict:
    return (
        CartoSymParser()
        .parse_string_to_pydantic(css)
        .to_dict()["stylingRules"][0]["symbolizer"]
    )


@pytest.mark.parametrize("where", ["label", "marker"])
def test_orientation_number_property_and_expression(where):
    for source, expected in (
        ("45", 45),
        ("45 deg", 45),
        ("Rot", {"property": "Rot"}),
        ("Rot * 0.9", {"op": "*", "args": [{"property": "Rot"}, 0.9]}),
    ):
        sym = _json(
            f"L {{ {where}: {{ elements: [ Text {{ text: N, "
            f"transform: {{ orientation: {source} }} }} ] }}; }}"
        )
        assert sym[where]["elements"][0]["transform"]["orientation"] == expected


def test_alignment_from_expressions():
    sym = _json(
        "L { label: { elements: [ Text { text: N, "
        "alignment: {lowerCase(h), v = 'Top' ? 'top' : 'bottom'} } ] }; }"
    )
    h, v = sym["label"]["elements"][0]["alignment"]
    assert h == {"op": "lowerCase", "args": [{"property": "h"}]} and v["op"] == "?:"


def test_round_trip_through_cartosym_css():
    style = {
        "stylingRules": [
            {
                "selector": {"op": "=", "args": [{"sysId": "dataLayer.id"}, "L"]},
                "symbolizer": {
                    "label": {
                        "elements": [
                            {
                                "type": "Text",
                                "text": {"property": "N"},
                                "alignment": [
                                    {"op": "lowerCase", "args": [{"property": "h"}]},
                                    "middle",
                                ],
                                "transform": {"orientation": {"property": "Rot"}},
                            }
                        ]
                    },
                    "marker": {
                        "elements": [
                            {
                                "type": "Image",
                                "image": {"path": "a.svg"},
                                "transform": {"orientation": 45},
                            }
                        ]
                    },
                },
            }
        ]
    }
    css = Converter().csjson_to_cscss(style)
    back = _json(css)
    assert back["label"]["elements"][0]["transform"] == {
        "orientation": {"property": "Rot"}
    }
    assert back["label"]["elements"][0]["alignment"][1] == "middle"
    assert back["marker"]["elements"][0]["transform"] == {"orientation": 45}


def test_sld_label_concatenation_of_properties_and_text():
    from pycartosym import get_codec

    css = (
        "L { label: { elements: [ Text { text: concatenate(Nummer, '.', Teil) } ] }; }"
    )
    style = CartoSymParser().parse_string_to_pydantic(css)
    sld = get_codec("sld").write(style)
    assert (
        "<ogc:PropertyName>Nummer</ogc:PropertyName>.<ogc:PropertyName>Teil</ogc:PropertyName>"
        in sld
    )
