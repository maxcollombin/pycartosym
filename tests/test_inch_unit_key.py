"""The CS-JSON unit key `inch` (revised schema) is read next to `in`."""

from pycartosym.converter import Converter
from pycartosym.models.styles import Style


def _width(key):
    return Style.from_dict(
        {"stylingRules": [{"symbolizer": {"stroke": {"width": {key: 0.1}}}}]}
    )


def test_inch_and_in_are_the_same_unit():
    for key in ("inch", "in"):
        stroke = _width(key).styling_rules[0].symbolizer.stroke
        assert stroke.width.unit.value == "in"


def test_inch_is_written_back_as_cscss_inch():
    assert "0.1 inch" in Converter().style_to_cscss(_width("inch"))
