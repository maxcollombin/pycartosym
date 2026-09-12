"""Exercise the SLD 1.0.0 dialect against the vendored GeoServer corpus.

``tests/fixtures/geoserver-sld/`` is 24 real GeoServer sample styles, all
SLD 1.0.0 (see its README). This test splits them into:

* **in-scope** — ``read`` (version auto-detected) -> ``write`` (SLD 1.0.0)
  -> XSD-validate -> ``read`` back to a Pydantic-model fixed point.
* **out-of-scope** — must raise ``NotImplementedError`` (a clean rejection,
  never another exception type) on ``read`` or ``write``.

The split is asserted, so an accidental behaviour change (a fixture that
starts or stops round-tripping) fails loudly. The corpus is vendored flat,
so the classification lives here rather than in directory layout; the
reason each file is out of scope is in the mapping below.
"""

import pytest

from pycartosym.codecs.sld._dialect import SLD_1_0_0
from pycartosym.codecs.sld.reader import SldReader
from pycartosym.codecs.sld.writer import SldWriter

from ._xsd import assert_sld10_valid
from .test_geoserver_sld_corpus import CORPUS, FILES

# Why each out-of-scope fixture is out of scope (all raise NotImplementedError).
OUT_OF_SCOPE = {
    "Lakes.sld": "unmapped CssParameter 'stroke-linecap' / '-linejoin' / '-dashoffset'",
    "default_generic.sld": "<ogc:Function> in filter + VendorOption (GeoServer)",
    "pattern_polygon.sld": (
        "VendorOption 'graphic-margin' (not Fill/GraphicFill — in scope now)"
    ),
    "poi.sld": "Graphic/Displacement on a point Mark (not in the SLD 1.0.0 schema)",
    "pophatch.sld": "Fill/GraphicFill (hatch) + WellKnownName 'shape://slash'",
    "poly_landmarks.sld": "VendorOption 'group' / 'autoWrap' (GeoServer)",
    "raster.sld": "RasterSymbolizer with only Opacity (no channels / colour map)",
    "tiger_roads.sld": "VendorOption 'group' + LabelPlacement/LinePlacement",
}
IN_SCOPE = sorted(set(FILES) - set(OUT_OF_SCOPE))

_EXPECTED_IN_SCOPE = 16
_EXPECTED_OUT_OF_SCOPE = 8


def test_corpus_split_is_exhaustive():
    assert len(IN_SCOPE) == _EXPECTED_IN_SCOPE, IN_SCOPE
    assert len(OUT_OF_SCOPE) == _EXPECTED_OUT_OF_SCOPE, sorted(OUT_OF_SCOPE)
    assert set(IN_SCOPE) | set(OUT_OF_SCOPE) == set(FILES)
    assert not (set(IN_SCOPE) & set(OUT_OF_SCOPE))


@pytest.mark.parametrize("name", IN_SCOPE)
def test_in_scope_round_trips_and_validates(name):
    reader, writer = SldReader(), SldWriter(SLD_1_0_0)
    fixture = CORPUS / name

    style1 = reader.read(fixture)
    xml = writer.write(style1)
    assert 'version="1.0.0"' in xml
    assert "SvgParameter" not in xml and "http://www.opengis.net/se" not in xml
    assert_sld10_valid(xml, label=name)

    style2 = reader.read(xml)
    assert style1 == style2, f"{name}: read->write->read is not a fixed point"


@pytest.mark.parametrize("name", sorted(OUT_OF_SCOPE))
def test_out_of_scope_raises_not_implemented(name):
    reader, writer = SldReader(), SldWriter(SLD_1_0_0)
    with pytest.raises(NotImplementedError):
        writer.write(reader.read(CORPUS / name))
