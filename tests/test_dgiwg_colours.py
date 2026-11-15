"""DGIWG colour register: registry items to CartoSym variables (offline)."""

import importlib.util
from pathlib import Path

from pycartosym.converter import Converter

_SCRIPT = Path(__file__).parent.parent / "scripts" / "dgiwg_colours.py"
_spec = importlib.util.spec_from_file_location("dgiwg_colours", _SCRIPT)
dgiwg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dgiwg)

FEATURES = [
    {
        "id": "CC_2101",
        "properties": {
            "title": "Black",
            "status": "valid",
            "externalId": "https://def.dgiwg.org/portrayal/colour/CC_2101",
            "hex": "#4B4B4B",
            "cmyk": [0, 0, 0, 100],
            "cielab": [31.9, 1.6, 1.5],
            "pantone": "Process Black U",
        },
    },
    {
        "id": "CC_2102",
        "properties": {
            "title": "Grey */ odd",
            "status": "valid",
            "externalId": "https://def.dgiwg.org/portrayal/colour/CC_2102",
            "hex": "#E0E0E0",
            "cmyk": None,
            "cielab": None,
            "pantone": None,
        },
    },
]


def test_each_colour_becomes_a_variable():
    cscss = dgiwg.to_cscss(FEATURES)
    assert "@CC_2101 = #4b4b4b;" in cscss
    assert "@CC_2102 = #e0e0e0;" in cscss


def test_values_without_a_counterpart_are_kept_in_a_comment():
    cscss = dgiwg.to_cscss(FEATURES)
    assert "CMYK 0 0 0 100 | CIELAB 31.9 1.6 1.5 | Pantone Process Black U" in cscss
    assert "https://def.dgiwg.org/portrayal/colour/CC_2101" in cscss


def test_the_output_is_valid_cartosym_css():
    data = Converter().cscss_to_csjson(dgiwg.to_cscss(FEATURES))
    assert data["$variables"] == {
        "CC_2101": [75, 75, 75],
        "CC_2102": [224, 224, 224],
    }
