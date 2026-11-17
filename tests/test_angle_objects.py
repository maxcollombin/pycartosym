"""The CS-JSON schema's ``{"deg": …}`` / ``{"rad": …}`` angle objects."""

import pytest
from pydantic import ValidationError

from pycartosym.converter import Converter
from pycartosym.models import Style

ROT = {"property": "rot"}


def _style(orientation) -> dict:
    graphic = {
        "type": "Image",
        "image": {"path": "a.svg"},
        "transform": {"orientation": orientation},
    }
    return {"stylingRules": [{"symbolizer": {"fill": {"pattern": graphic}}}]}


def _orientation(csjson: dict):
    symbolizer = csjson["stylingRules"][0]["symbolizer"]
    return symbolizer["fill"]["pattern"]["transform"]["orientation"]


@pytest.mark.parametrize("angle", [{"deg": 45}, {"rad": 1.5}, {"deg": ROT}])
def test_an_angle_object_is_accepted_and_kept(angle):
    assert _orientation(Style.model_validate(_style(angle)).to_dict()) == angle


@pytest.mark.parametrize("angle", [{"deg": 1, "rad": 2}, {"grad": 3}, {}])
def test_another_object_is_rejected(angle):
    with pytest.raises(ValidationError):
        Style.model_validate(_style(angle))


@pytest.mark.parametrize(
    ("angle", "css", "back"),
    [
        ({"deg": 45}, "orientation: 45 deg", 45),
        ({"deg": ROT}, "orientation: rot", ROT),
        (
            {"rad": ROT},
            "orientation: (rot) * 57.29577951308232",
            {"op": "*", "args": [ROT, 57.29577951308232]},
        ),
    ],
)
def test_an_angle_object_is_written_to_cartosym_css(angle, css, back):
    converter = Converter()
    text = converter.csjson_to_cscss(_style(angle))
    assert css in text
    assert _orientation(converter.cscss_to_csjson(text)) == back
