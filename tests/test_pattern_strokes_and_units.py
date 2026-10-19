"""Pattern strokes, the pc and inch units, and unit points with units."""

import pytest

from pycartosym.converter import Converter
from pycartosym.models.types import UnitType, UnitValue
from pycartosym.parser import CartoSymParser


def _csjson(cscss: str) -> dict:
    return Converter().cscss_to_csjson(cscss)["stylingRules"][0]["symbolizer"]


def _round_trips(cscss: str) -> bool:
    style = CartoSymParser().parse_string_to_pydantic(cscss)
    written = Converter().style_to_cscss(style)
    return (
        CartoSymParser().parse_string_to_pydantic(written).to_dict() == style.to_dict()
    )


def test_pc_is_percent():
    assert UnitType.PERCENT.value == "pc"
    assert not hasattr(UnitType, "PICAS")
    assert UnitValue(value=50, unit="pc").unit is UnitType.PERCENT


def test_inch_abbreviation_of_the_specification():
    assert _csjson("L { stroke: { width: 2 inch; }; }")["stroke"]["width"] == {
        "in": 2.0
    }
    assert _round_trips("L { stroke: { width: 2 inch; }; }")


_PATTERN = (
    "L { stroke: { color: red; pattern: Image { image: {path: 'c.png'} };"
    " patternGap: 20 px; patternInitialGap: 5 }; }"
)


def test_pattern_stroke_is_read_with_unit_gaps():
    stroke = _csjson(_PATTERN)["stroke"]
    assert stroke["pattern"] == {"type": "Image", "image": {"path": "c.png"}}
    assert stroke["patternGap"] == {"px": 20.0}
    assert stroke["patternInitialGap"] == 5.0


def test_pattern_stroke_round_trips_through_cartosym_css():
    assert _round_trips(_PATTERN)


def test_pattern_gap_accepts_a_unit_value_in_csjson():
    from pycartosym.models import Style

    style = Style.from_dict(
        {"stylingRules": [{"symbolizer": {"stroke": {"patternGap": {"px": 40}}}}]}
    )
    assert style.styling_rules[0].symbolizer.stroke.pattern_gap.value == 40


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3 px 4 px", {"x": {"px": 3.0}, "y": {"px": 4.0}}),
        ("20 0", {"x": 20.0, "y": 0.0}),
    ],
)
def test_marker_position_with_or_without_units(text, expected):
    cscss = (
        f"L {{ marker: {{ elements: [ Dot {{ color: red; position: {text} }} ] }}; }}"
    )
    assert _csjson(cscss)["marker"]["elements"][0]["position"] == expected
    assert _round_trips(cscss)
