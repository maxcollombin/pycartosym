"""Exercise the ``sld:geoserver`` dialect (SLD 1.0.0 + ``<VendorOption>``).

``sld:geoserver`` reads/writes the SLD 1.0.0 GeoServer emits, and maps a
symbolizer-level ``<VendorOption name="X">V`` to a ``vendor.geoserver.X``
symbolizer property (the conceptual model's generic vendor-extension
mechanism). The standard ``sld`` / ``sld:1.0.0`` / ``sld:1.1.0`` codecs
still reject ``<VendorOption>``.

Split of the four vendored GeoServer files that carry a ``<VendorOption>``:

* **in scope** — the vendor option sits on a symbolizer and nothing else
  in the file is out of scope: ``read`` -> ``write`` -> XSD-validate (with
  the schema-undefined ``<VendorOption>`` elements stripped) -> ``read``
  back to a Pydantic-model fixed point.
* **out of scope** — still raises ``NotImplementedError``, for a reason
  unrelated to the vendor option itself.
"""

import re

import pytest

from pycartosym.codecs.sld._dialect import SLD_1_0_0_GEOSERVER
from pycartosym.codecs.sld.reader import SldReader
from pycartosym.codecs.sld.writer import SldWriter

from ._xsd import assert_sld10_valid
from .test_geoserver_sld_corpus import CORPUS

# file -> the vendor.geoserver.* keys its symbolizer-level VendorOptions map to
IN_SCOPE = {
    "poly_landmarks.sld": {
        "vendor.geoserver.group": True,
        "vendor.geoserver.autoWrap": 100,
    },
    "pattern_polygon.sld": {
        "vendor.geoserver.graphic-margin": "4 6 2 3",
    },
}

# <VendorOption> files still out of scope under sld:geoserver, each for a
# reason that has nothing to do with the vendor option.
OUT_OF_SCOPE = {
    "default_generic.sld": "<ogc:Function> in filter",
    "tiger_roads.sld": "LabelPlacement/LinePlacement",
}

_VENDOR_OPTION_RE = re.compile(r"[ \t]*<VendorOption\b[^>]*>[^<]*</VendorOption>\n?")


def _vendor_keys(style) -> dict:
    dumped = style.to_dict()
    return {
        k: v
        for rule in dumped["stylingRules"]
        for k, v in (rule.get("symbolizer") or {}).items()
        if k.startswith("vendor.")
    }


@pytest.mark.parametrize("name", sorted(IN_SCOPE))
def test_in_scope_round_trips_with_vendor_options(name):
    reader = SldReader(SLD_1_0_0_GEOSERVER)
    writer = SldWriter(SLD_1_0_0_GEOSERVER)
    fixture = CORPUS / name

    style1 = reader.read(fixture)
    assert _vendor_keys(style1) == IN_SCOPE[name]

    xml = writer.write(style1)
    assert 'version="1.0.0"' in xml
    for key, value in IN_SCOPE[name].items():
        opt = key.rsplit(".", 1)[1]
        expected = "true" if value is True else str(value)
        assert f'<VendorOption name="{opt}">{expected}</VendorOption>' in xml

    # The OGC SLD 1.0.0 XSD does not define <VendorOption>; the rest of the
    # document must still be schema-valid once they are stripped.
    assert_sld10_valid(_VENDOR_OPTION_RE.sub("", xml), label=name)

    style2 = reader.read(xml)
    assert style1 == style2, f"{name}: read->write->read is not a fixed point"


@pytest.mark.parametrize("name", sorted(OUT_OF_SCOPE))
def test_out_of_scope_still_raises(name):
    reader = SldReader(SLD_1_0_0_GEOSERVER)
    writer = SldWriter(SLD_1_0_0_GEOSERVER)
    with pytest.raises(NotImplementedError):
        writer.write(reader.read(CORPUS / name))


def test_standard_sld_codec_still_rejects_vendor_option():
    with pytest.raises(NotImplementedError):
        SldReader().read(CORPUS / "poly_landmarks.sld")  # auto -> pure SLD 1.0.0


def test_non_symbolizer_vendor_option_raises():
    """A <VendorOption> at FeatureTypeStyle/Rule level has no home."""
    xml = """<?xml version="1.0"?>
    <StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld"
        xmlns:ogc="http://www.opengis.net/ogc">
      <NamedLayer><Name>n</Name><UserStyle><FeatureTypeStyle>
        <VendorOption name="ruleEvaluation">first</VendorOption>
        <Rule><PolygonSymbolizer><Fill>
          <CssParameter name="fill">#000000</CssParameter>
        </Fill></PolygonSymbolizer></Rule>
      </FeatureTypeStyle></UserStyle></NamedLayer>
    </StyledLayerDescriptor>"""
    with pytest.raises(NotImplementedError, match="ruleEvaluation"):
        SldReader(SLD_1_0_0_GEOSERVER).read(xml)
