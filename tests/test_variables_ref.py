"""Variables: a `$variables` object, referenced with `{"$ref": "#/$variables/x"}`."""

from pycartosym.converter import Converter
from pycartosym.models.styles import Style

SOURCE = (
    "@roadWidth = 3;\n"
    "@c = #336699;\n"
    "@alpha = 0.5;\n"
    "Roads { stroke: { width: @roadWidth * 2 px; color: red }; }\n"
    "Land { fill: { color: @c; opacity: @alpha }; }\n"
)


def _csjson(cscss: str = SOURCE) -> dict:
    return Converter().cscss_to_csjson(cscss)


def test_variables_are_an_object():
    assert _csjson()["$variables"] == {
        "roadWidth": 3,
        "c": [51, 102, 153],
        "alpha": 0.5,
    }


def test_reference_in_an_expression_is_a_ref():
    width = _csjson()["stylingRules"][0]["symbolizer"]["stroke"]["width"]
    assert width == {"px": {"op": "*", "args": [{"$ref": "#/$variables/roadWidth"}, 2]}}


def test_plain_reference_is_a_ref_not_inlined():
    fill = _csjson()["stylingRules"][1]["symbolizer"]["fill"]
    assert fill == {
        "color": {"$ref": "#/$variables/c"},
        "opacity": {"$ref": "#/$variables/alpha"},
    }


def test_round_trip_through_cscss():
    first = _csjson()
    text = Converter().style_to_cscss(Style.from_dict(first))
    assert "@roadWidth * 2 px" in text and "color: @c" in text
    assert _csjson(text) == first


def test_legacy_variable_list_is_still_read():
    style = Style.from_dict(
        {"stylingRules": [], "$variables": [{"name": "a", "value": 1}]}
    )
    assert style.variables == {"a": 1}


def test_resolve_variables_inlines_values():
    resolved = Style.from_dict(_csjson()).resolve_variables().to_dict()
    assert "$variables" not in resolved
    assert resolved["stylingRules"][1]["symbolizer"]["fill"]["color"] == [51, 102, 153]


def test_variables_reach_codecs_as_values():
    from pycartosym.codecs.maplibre.writer import MaplibreWriter

    style = Style.from_dict(_csjson())
    MaplibreWriter().write(style)  # no error, no leftover $ref


def test_sld_writes_variables_as_values():
    from pycartosym.codecs.sld.writer import SldWriter

    style = Style.from_dict(
        Converter().cscss_to_csjson("@c = #336699;\nLand { fill: { color: @c }; }\n")
    )
    xml = SldWriter().write(style)
    assert "#336699" in xml.lower()
