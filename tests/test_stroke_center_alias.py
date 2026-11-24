"""`center` is read and written; the older `centerLine` is still read."""

from pycartosym.models.styles import Style


def _stroke(key):
    return Style.from_dict(
        {
            "stylingRules": [
                {
                    "symbolizer": {
                        "stroke": {"width": 3, key: {"color": "white", "width": 1}}
                    }
                }
            ]
        }
    )


def test_center_and_centerline_are_the_same_property():
    for key in ("center", "centerLine"):
        stroke = _stroke(key).styling_rules[0].symbolizer.stroke
        assert stroke.center_line is not None


def test_center_line_is_written_as_center():
    dumped = _stroke("center").model_dump(by_alias=True, exclude_none=True)
    stroke = dumped["stylingRules"][0]["symbolizer"]["stroke"]
    assert "center" in stroke
    assert "centerLine" not in stroke
