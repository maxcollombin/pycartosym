"""A nested rule without a selector in CartoSym-CSS merges into its parent (#190)."""

from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.converter import Converter

CSCSS = (
    "[kind = 'road']\n"
    "{\n"
    "   { stroke: { color: black; width: 5 px; }; }\n"
    "   { stroke: { color: white; width: 3 px; }; }\n"
    "}\n"
)


def test_bare_nested_rules_keep_no_selector():
    rules = Converter().cscss_to_csjson(CSCSS)["stylingRules"]
    assert [("selector" in n) for n in rules[0]["nestedRules"]] == [False, False]


def test_bare_nested_rules_override_one_another_in_sld():
    converter = Converter()
    style = converter.cscss_to_csjson(CSCSS)
    from pycartosym.models.styles import Style

    xml = SldWriter().write(Style.from_dict(style))
    assert xml.count("<se:Rule>") == 1
    assert "#ffffff" in xml
    assert "#000000" not in xml
