"""CS-JSON ``$comment`` → CartoSym-CSS comments, at every level that has one."""

from __future__ import annotations

from pycartosym.converter import Converter

_STYLE = {
    "$comment": "style comment",
    "metadata": {"title": "T", "$comment": "metadata comment"},
    "stylingRules": [
        {
            "$comment": "rule comment",
            "selector": {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Roads"]},
            "symbolizer": {
                "$comment": "symbolizer comment",
                "marker": {
                    "elements": {
                        "index": 1,
                        "value": {
                            "type": "Text",
                            "$comment": "element comment",
                            "text": "x",
                        },
                    }
                },
            },
        }
    ],
}


def _to_cscss(style: dict) -> str:
    return Converter().style_to_cscss(Converter().csjson_to_style(style))


def test_every_level_comment_is_written():
    out = _to_cscss(_STYLE)
    for text in (
        "style comment",
        "metadata comment",
        "rule comment",
        "symbolizer comment",
        "element comment",
    ):
        assert f"/* {text} */" in out, text


def test_written_comments_parse_back():
    out = _to_cscss(_STYLE)
    back = Converter().cscss_to_csjson(out)
    assert back["stylingRules"][0]["selector"]["args"][1] == "Roads"


def test_multiline_or_unsafe_comment_uses_line_comments():
    style = {
        "stylingRules": [
            {"$comment": "first\nsecond */ third", "symbolizer": {"opacity": 1}}
        ]
    }
    out = _to_cscss(style)
    assert "// first" in out and "// second */ third" in out
    assert "/*" not in out
    Converter().cscss_to_csjson(out)
