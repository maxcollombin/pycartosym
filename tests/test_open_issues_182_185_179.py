"""Regressions: dashOffset, unit dashPattern, label priority, Dot colour, rule name."""

import logging

import pytest

from pycartosym.converter import Converter


def _symbolizer(css: str) -> dict:
    return Converter().cscss_to_csjson(css)["stylingRules"][0]["symbolizer"]


def _roundtrip(css: str) -> dict:
    converter = Converter()
    style = converter.cscss_to_csjson(css)
    return converter.cscss_to_csjson(converter.csjson_to_cscss(style))


@pytest.mark.parametrize("written", ["It''s", "It\\'s"])
def test_rule_name_escaped_quote_is_unescaped(written):
    style = Converter().cscss_to_csjson(f"A {{\n  .name '{written}'\n}}\n")
    assert style["stylingRules"][0]["name"] == "It's"


def test_rule_name_is_written_back_escaped():
    css = "A {\n  .name 'It''s'\n}\n"
    assert _roundtrip(css)["stylingRules"][0]["name"] == "It's"
