"""Valid CS-JSON shapes that used to be rejected (from the schema test documents)."""

import pytest

from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter
from pycartosym.models.styles import Style


def _fill(color):
    return Style.from_dict(
        {"stylingRules": [{"symbolizer": {"fill": {"color": color}}}]}
    )


def test_color_component_can_be_an_expression_and_is_kept():
    color = [{"op": "*", "args": [{"property": "a"}, 2]}, 0, 0]
    dumped = _fill(color).model_dump(by_alias=True, exclude_none=True)
    assert dumped["stylingRules"][0]["symbolizer"]["fill"]["color"] == color


def test_altering_color_object_gives_only_some_components():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "symbolizer": {
                        "fill": {"alter": True, "color": {"alter": True, "r": 100}}
                    }
                }
            ]
        }
    )
    color = style.model_dump(by_alias=True, exclude_none=True)["stylingRules"][0][
        "symbolizer"
    ]["fill"]["color"]
    assert color == {"r": 100, "alter": True}


def test_color_object_without_alter_still_needs_all_components():
    with pytest.raises(ValueError):
        _fill({"r": 100})


@pytest.mark.parametrize("color", [[{"op": "*", "args": [{"property": "a"}, 2]}, 0, 0]])
def test_such_colors_are_refused_clearly_by_the_writers(color):
    with pytest.raises(NotImplementedError):
        Converter().style_to_cscss(_fill(color))
    with pytest.raises(NotImplementedError):
        SldWriter().write(_fill(color))


def test_variable_reference_into_an_included_file():
    ref = {"$ref": "base.cs.json#/$variables/w"}
    style = Style.from_dict(
        {"stylingRules": [{"symbolizer": {"stroke": {"width": ref}}}]}
    )
    assert (
        style.model_dump(by_alias=True, exclude_none=True)["stylingRules"][0][
            "symbolizer"
        ]["stroke"]["width"]
        == ref
    )
    assert "width: @w" in Converter().style_to_cscss(style)
