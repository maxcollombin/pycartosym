"""Dot pattern distance: one value, an object or an array."""

import pytest

from pycartosym.converter import Converter

_CSCSS = "L {{ fill: {{ dotpattern: {{ distance: {distance} }} }}; }}"
_CASES = [
    ("4 px", {"px": 4.0}),
    (
        "{ horizontal: 10 px; vertical: 8 px }",
        {"horizontal": {"px": 10.0}, "vertical": {"px": 8.0}},
    ),
    ("{ horizontal: 10; vertical: 8 }", {"horizontal": 10.0, "vertical": 8.0}),
    ("[4, 8]", [4.0, 8.0]),
]


def _distance(csjson: dict):
    return csjson["stylingRules"][0]["symbolizer"]["fill"]["dotpattern"]["distance"]


@pytest.mark.parametrize(("source", "expected"), _CASES)
def test_cscss_to_csjson(source, expected):
    csjson = Converter().cscss_to_csjson(_CSCSS.format(distance=source))
    assert _distance(csjson) == expected


@pytest.mark.parametrize(("source", "expected"), _CASES)
def test_csjson_round_trip_through_cartosym_css(source, expected):
    converter = Converter()
    csjson = {
        "stylingRules": [
            {"symbolizer": {"fill": {"dotpattern": {"distance": expected}}}}
        ]
    }
    cscss = converter.csjson_to_cscss(csjson)
    assert _distance(converter.cscss_to_csjson(cscss)) == expected
