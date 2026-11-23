"""``capabilities.*`` System Identifiers are written as ``sysId``, not ``property``."""

from pycartosym import cql2
from pycartosym.converter import Converter


def test_capabilities_identifier_is_a_sysid_in_cql2_json() -> None:
    expr = cql2.to_cql2_json(cql2.parse_text("capabilities.hatches = true"))
    assert expr == {"op": "=", "args": [{"sysId": "capabilities.hatches"}, True]}


def test_capabilities_selector_is_a_sysid_in_cs_json() -> None:
    source = "Landcover[capabilities.hatches = true] { fill: { color: #5e8f52 }; }\n"
    result = Converter().cscss_to_csjson(source)
    selector = result["stylingRules"][0]["selector"]
    assert {"sysId": "capabilities.hatches"} in [
        a for e in selector["args"] for a in e["args"]
    ]
    assert (
        Converter()
        .csjson_to_cscss(result)
        .startswith("Landcover[capabilities.hatches = true]")
    )
