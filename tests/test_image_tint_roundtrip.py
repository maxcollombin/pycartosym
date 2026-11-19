"""An Image's tint and blackTint, given as [r, g, b], survive JSON -> CSS -> JSON."""

from __future__ import annotations

from pycartosym import Converter


def test_image_tints_are_written_as_hex_and_read_back_as_colors():
    style = {
        "stylingRules": [
            {
                "symbolizer": {
                    "marker": {
                        "elements": [
                            {
                                "image": {"id": "bog"},
                                "tint": [255, 255, 255],
                                "blackTint": [107, 95, 42],
                            }
                        ]
                    }
                }
            }
        ]
    }
    converter = Converter()
    css = converter.csjson_to_cscss(style)
    assert "tint: #ffffff" in css
    assert "blackTint: #6b5f2a" in css
    element = converter.cscss_to_csjson(css)["stylingRules"][0]["symbolizer"]["marker"][
        "elements"
    ][0]
    assert element["tint"] == [255, 255, 255]
    assert element["blackTint"] == [107, 95, 42]
