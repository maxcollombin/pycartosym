"""colorChannels set one channel at a time (colorChannels.r / .g / .b)."""

from pycartosym.converter import Converter

_CSCSS = """L
{
    colorChannels.r: B04 / 2500;
    colorChannels.g: B03 / 2500;
    colorChannels.b: B02;
}
"""
_EXPECTED = {
    "alter": True,
    "r": {"op": "/", "args": [{"property": "B04"}, 2500]},
    "g": {"op": "/", "args": [{"property": "B03"}, 2500]},
    "b": {"property": "B02"},
}


def _channels(csjson: dict):
    return csjson["stylingRules"][0]["symbolizer"]["colorChannels"]


def test_cscss_to_csjson():
    assert _channels(Converter().cscss_to_csjson(_CSCSS)) == _EXPECTED


def test_csjson_to_cscss_writes_one_line_per_channel():
    converter = Converter()
    cscss = converter.csjson_to_cscss(converter.cscss_to_csjson(_CSCSS))
    assert "{'" not in cscss
    assert "colorChannels.r:" in cscss
    assert _channels(converter.cscss_to_csjson(cscss)) == _EXPECTED
