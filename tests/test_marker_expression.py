"""A marker can be given as an expression (a property, a variable...)."""

import pytest

from pycartosym.codecs.maplibre.writer import MaplibreWriter
from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style

MARKER = {"property": "m"}


def _style():
    return Style.from_dict(
        {"stylingRules": [{"name": "a", "symbolizer": {"marker": MARKER}}]}
    )


def test_marker_expression_is_read_and_kept():
    dumped = _style().model_dump(by_alias=True, exclude_none=True)
    assert dumped["stylingRules"][0]["symbolizer"]["marker"] == MARKER


def test_a_real_marker_is_still_a_marker():
    style = Style.from_dict(
        {"stylingRules": [{"symbolizer": {"marker": {"elements": [{"type": "Dot"}]}}}]}
    )
    assert hasattr(style.styling_rules[0].symbolizer.marker, "elements")


@pytest.mark.parametrize(
    "write",
    [
        lambda s: SldWriter().write(s),
        lambda s: MaplibreWriter().write(s),
        lambda s: Converter().style_to_cscss(s),
    ],
    ids=["sld", "maplibre", "cscss"],
)
def test_writers_refuse_a_marker_expression_clearly(write):
    with pytest.raises(NotImplementedError, match="marker"):
        write(_style())
