"""The ``Symbolizer`` model accepts vendor-extension keys and nothing else.

The conceptual model defines a generic vendor-extension mechanism: a
symbolizer property named ``vendor.<vendorName>.<propertyName>``, of any
datatype, which a consumer ignores when it does not understand it. The
model permits exactly those extra keys (so e.g. GeoServer ``<VendorOption>``
values survive a CS-JSON round-trip) and rejects any other unknown key as
a likely typo.
"""

import pytest
from pydantic import ValidationError

from pycartosym.models.symbolizers import Symbolizer


@pytest.mark.parametrize(
    "key",
    [
        "vendor.geoserver.autoWrap",
        "vendor.geoserver.group",
        "vendor.my-vendor.some_prop",
        "vendor.x.a.b.c",
    ],
)
def test_vendor_extension_keys_are_accepted_and_round_trip(key):
    sym = Symbolizer.from_dict({"fill": {"color": "#ffffff"}, key: 42})
    assert sym.to_dict()[key] == 42


def test_vendor_extension_value_keeps_its_datatype():
    sym = Symbolizer.from_dict(
        {
            "vendor.geoserver.group": True,
            "vendor.geoserver.autoWrap": 100,
            "vendor.geoserver.labelAllGroup": "true",
        }
    )
    dumped = sym.to_dict()
    assert dumped["vendor.geoserver.group"] is True
    assert dumped["vendor.geoserver.autoWrap"] == 100
    assert dumped["vendor.geoserver.labelAllGroup"] == "true"


@pytest.mark.parametrize(
    "key",
    [
        "bogus",
        "fil",  # typo of "fill"
        "vendor",
        "vendor.geoserver",  # no property part
        "vendor..autoWrap",  # empty vendor name
        "vendorX.geoserver.autoWrap",
    ],
)
def test_non_vendor_extra_keys_are_rejected(key):
    with pytest.raises(ValidationError):
        Symbolizer.from_dict({key: 1})


def test_known_fields_still_validated_normally():
    sym = Symbolizer.from_dict({"fill": {"color": "#abcabc"}})
    assert sym.fill is not None


def test_vendor_extension_round_trips_through_cartosym_css():
    from pycartosym.converter import Converter

    symbolizer = {
        "stroke": {"width": {"px": 1}},
        "vendor.example.offset": {"px": 2},
        "vendor.example.flag": True,
        "vendor.example.count": 3,
        "vendor.example.label": "it's",
        "vendor.example.size": {"op": "*", "args": [{"property": "h"}, 2]},
    }
    text = Converter().csjson_to_cscss({"stylingRules": [{"symbolizer": symbolizer}]})
    assert "vendor.example.offset: 2 px;" in text
    assert "vendor.example.label: 'it''s';" in text
    back = Converter().cscss_to_csjson(text)
    assert back["stylingRules"][0]["symbolizer"] == symbolizer


def test_vendor_extension_without_a_css_form_is_reported(caplog):
    from pycartosym.converter import Converter

    symbolizer = {"stroke": {"width": {"px": 1}}, "vendor.example.thing": {"x": 1}}
    text = Converter().csjson_to_cscss({"stylingRules": [{"symbolizer": symbolizer}]})
    assert "vendor.example.thing" not in text
    assert "vendor.example.thing" in caplog.text
