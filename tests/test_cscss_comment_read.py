"""CartoSym-CSS comments on the lines before a rule / property → ``$comment``."""

from __future__ import annotations

from pycartosym.converter import Converter

_SRC = """\
// about the roads
Roads
{
   // hidden by default
   visibility: false;

   /* shown when zoomed in */
   [viz.sd < 10000]
   {
      // draw thick
      // and red
      stroke: {color: red; width: 4 px};
      opacity: 0.5; // trailing, belongs to the opacity line
      marker: {elements: [
         Text {
            // offset to the right
            position: 20 0;
            text: Name; // trailing too
         }
      ]};
   }
}
"""


def _json(src: str = _SRC) -> dict:
    return Converter().cscss_to_csjson(src)


def test_comment_before_a_rule_goes_to_the_rule():
    rule = _json()["stylingRules"][0]
    assert rule["$comment"] == "about the roads"
    assert rule["nestedRules"][0]["$comment"] == "shown when zoomed in"


def test_comments_before_properties_go_to_the_symbolizer():
    rule = _json()["stylingRules"][0]
    assert rule["symbolizer"]["$comment"] == "hidden by default"
    nested = rule["nestedRules"][0]
    assert nested["symbolizer"]["$comment"] == "draw thick\nand red"


def test_trailing_comment_is_not_attached_to_the_next_line():
    nested = _json()["stylingRules"][0]["nestedRules"][0]
    assert "trailing" not in nested["symbolizer"]["$comment"]


def test_comment_before_a_property_in_an_element_goes_to_the_element():
    nested = _json()["stylingRules"][0]["nestedRules"][0]
    element = nested["symbolizer"]["marker"]["elements"][0]
    assert element["$comment"] == "offset to the right"


def test_no_comment_means_no_key():
    d = _json("Roads\n{\n   opacity: 1;\n}\n")
    assert "$comment" not in d["stylingRules"][0]
    assert "$comment" not in d["stylingRules"][0]["symbolizer"]


def test_comments_survive_cscss_json_cscss():
    conv = Converter()
    back = conv.cscss_to_csjson(conv.style_to_cscss(conv.csjson_to_style(_json())))
    assert back["stylingRules"][0]["$comment"] == "about the roads"
    nested = back["stylingRules"][0]["nestedRules"][0]
    assert nested["symbolizer"]["$comment"] == "draw thick\nand red"
