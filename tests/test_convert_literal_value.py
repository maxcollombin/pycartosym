"""``cql2.to_json.convert_literal_value`` — unit-suffixed literal parsing."""

from __future__ import annotations

import pytest

from pycartosym.cql2.to_json import convert_literal_value
from pycartosym.models.types import UnitType, UnitValue


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2.0px", UnitValue(value=2.0, unit=UnitType.PIXELS)),
        ("2.0mm", UnitValue(value=2.0, unit=UnitType.MILLIMETERS)),
        ("2.0cm", UnitValue(value=2.0, unit=UnitType.CENTIMETERS)),
        ("2.0in", UnitValue(value=2.0, unit=UnitType.INCHES)),
        ("2.0pt", UnitValue(value=2.0, unit=UnitType.POINTS)),
        ("2.0em", UnitValue(value=2.0, unit=UnitType.EM)),
        ("2.0pc", UnitValue(value=2.0, unit=UnitType.PERCENT)),
        ("2.0ft", UnitValue(value=2.0, unit=UnitType.FEET)),
        ("2.0m", UnitValue(value=2.0, unit=UnitType.METERS)),
    ],
)
def test_convert_literal_value_parses_every_unit_type(text, expected):
    assert convert_literal_value(text) == expected


def test_convert_literal_value_percent_stays_a_string():
    """Percent has no ``models.types.UnitType`` member.

    Pre-existing, separate gap, not touched here — falls back to the bare
    string, same as before this module's unit list was extended.
    """
    assert convert_literal_value("2.0%") == "2.0%"


def test_convert_literal_value_does_not_confuse_mm_with_bare_m():
    """A millimetre value must not be mis-sliced by the shorter "m" suffix.

    "8.0 mm" should parse as millimetres, not become the unparseable
    "8.0 m" (falling back to a bare string) that a wrong suffix-check
    order would produce.
    """
    assert convert_literal_value("8.0 mm") == UnitValue(
        value=8.0, unit=UnitType.MILLIMETERS
    )


def test_convert_literal_value_integer_meters():
    assert convert_literal_value("10m") == UnitValue(value=10, unit=UnitType.METERS)
