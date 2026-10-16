"""Metadata.keywords accepts a comma-separated string as well as an array."""

from pycartosym.models.styles import Metadata


def test_keywords_comma_separated_string_becomes_list():
    assert Metadata(keywords="a, b,c").keywords == ["a", "b", "c"]


def test_keywords_list_unchanged():
    assert Metadata(keywords=["a", "b"]).keywords == ["a", "b"]
