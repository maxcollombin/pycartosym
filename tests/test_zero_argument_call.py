"""A call without argument, such as ``random()``, as the value of a property."""

import pytest

from pycartosym.converter import Converter

_SOURCE = "A { fill: { color: gray; opacity: random(); }; }"
_CALL = {"op": "random", "args": []}


def test_cscss_to_json_keeps_the_empty_call():
    rule = Converter().cscss_to_csjson(_SOURCE)["stylingRules"][0]
    assert rule["symbolizer"]["fill"]["opacity"] == _CALL


def test_the_empty_call_round_trips_through_cscss():
    converter = Converter()
    data = converter.cscss_to_csjson(_SOURCE)
    again = converter.cscss_to_csjson(converter.csjson_to_cscss(data))
    assert again == data


def test_the_empty_call_is_written_with_its_brackets():
    data = Converter().cscss_to_csjson(_SOURCE)
    assert "opacity: random()" in Converter().csjson_to_cscss(data)


@pytest.mark.parametrize("target", ["sld", "maplibre"])
def test_formats_without_an_equivalent_refuse_it_clearly(target):
    from pycartosym.codecs.maplibre import MaplibreWriter
    from pycartosym.codecs.sld.writer import SldWriter
    from pycartosym.models.styles import Style

    style = Style.from_dict(Converter().cscss_to_csjson(_SOURCE))
    writer = SldWriter() if target == "sld" else MaplibreWriter()
    with pytest.raises((NotImplementedError, ValueError), match="random"):
        writer.write(style)
