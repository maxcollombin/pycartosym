"""DGIWG portrayal rules: registry items to CartoSym selectors (offline)."""

import importlib.util
import sys
from pathlib import Path

from pycartosym.converter import Converter

_SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location(
    "dgiwg_rules", _SCRIPTS / "dgiwg_rules.py"
)
dgiwg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dgiwg)


def _rule(code, condition, feature_type="AerialFarm", title="A rule"):
    return {
        "id": code,
        "properties": {
            "title": title,
            "status": "valid",
            "externalId": f"https://def.dgiwg.org/portrayal/rule/{code}",
            "geometryType": "surface",
            "conditionExpr": condition,
            "featureType": {"alphaName": feature_type} if feature_type else None,
        },
    }


def _selector(feature):
    data = Converter().cscss_to_csjson(dgiwg.rule_to_cscss(feature))
    return data["stylingRules"][0]["selector"]


def test_enumeration_values_become_strings():
    assert (
        dgiwg.quote_enumerations("( a = noInformation )") == "( a = 'noInformation' )"
    )
    assert dgiwg.quote_enumerations("( a <> b ) AND ( c IS NULL )") == (
        "( a <> 'b' ) AND ( c IS NULL )"
    )
    assert dgiwg.quote_enumerations("( a = true )") == "( a = true )"


def test_the_condition_becomes_a_cql2_selector_on_the_feature_type():
    selector = _selector(_rule("PO_1", "( h >= 46 ) AND ( t = other )"))
    assert selector["args"][0] == {
        "op": "=",
        "args": [{"sysId": "dataLayer.id"}, "AerialFarm"],
    }
    assert selector["args"][1]["args"][1] == {
        "op": "=",
        "args": [{"property": "t"}, "other"],
    }


def test_no_condition_leaves_the_feature_type_only():
    for condition in (None, "", "{ feature }"):
        selector = _selector(_rule("PO_2", condition))
        assert selector == {
            "op": "=",
            "args": [{"sysId": "dataLayer.id"}, "AerialFarm"],
        }


def test_the_title_is_the_rule_name_and_the_code_a_comment():
    data = Converter().cscss_to_csjson(
        dgiwg.rule_to_cscss(_rule("PO_3", None, title="Aerial Farm"))
    )
    rule = data["stylingRules"][0]
    assert rule["name"] == "Aerial Farm"
    assert rule["$comment"].startswith("PO_3 | surface")


def test_a_quote_in_the_title_is_doubled():
    assert ".name 'It''s'" in dgiwg.rule_to_cscss(_rule("PO_3", None, title="It's"))


def test_conditions_with_prose_are_left_out():
    prose = _rule("PO_4", "( a < 46 ) { AND ( The feature is on land ) }")
    malformed = _rule("PO_5", "(( a = b ) OROR ( a = c )")
    good = _rule("PO_6", "( a = b )")
    kept, skipped = dgiwg.split_valid([prose, malformed, good])
    assert [f["id"] for f in kept] == ["PO_6"]
    assert skipped == ["PO_4", "PO_5"]
