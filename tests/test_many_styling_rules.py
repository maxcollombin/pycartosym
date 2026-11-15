"""A style with many styling rules converts without a recursion error."""

from pycartosym.converter import Converter

# More than the default recursion limit (1000): the grammar nests the styling
# rule list one level per rule.
COUNT = 1500


def _source() -> str:
    return "".join(f"A{i} [x = {i}] {{ .name 'r{i}' }}\n" for i in range(COUNT))


def test_cscss_to_json_keeps_every_rule_in_order():
    rules = Converter().cscss_to_csjson(_source())["stylingRules"]
    assert [rule["name"] for rule in rules] == [f"r{i}" for i in range(COUNT)]


def test_round_trip_keeps_every_rule():
    converter = Converter()
    first = converter.cscss_to_csjson(_source())
    second = converter.cscss_to_csjson(converter.csjson_to_cscss(first))
    assert second == first
