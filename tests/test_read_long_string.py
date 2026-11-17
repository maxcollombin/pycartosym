"""A long one-line source string is read as content, not tried as a file path.

On Python 3.10-3.13 ``Path.exists()`` / ``Path.is_file()`` raise ``OSError``
(``ENAMETOOLONG``) for a name longer than the file system allows (255 bytes
on Linux) instead of returning ``False``.
"""

import json

import pytest

from pycartosym.codecs import get_codec

NAME = "r" * 300

SOURCES = {
    "csjson": json.dumps(
        {"stylingRules": [{"name": NAME, "symbolizer": {"stroke": {"width": 1}}}]}
    ),
    "cscss": f"L {{ .name '{NAME}' stroke: {{ width: 1 px }}; }}",
    "sld": (
        '<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld">'
        f"<NamedLayer><Name>L</Name><UserStyle><Name>{NAME}</Name>"
        "<FeatureTypeStyle><Rule><LineSymbolizer><Stroke/></LineSymbolizer></Rule>"
        "</FeatureTypeStyle></UserStyle></NamedLayer></StyledLayerDescriptor>"
    ),
}


@pytest.mark.parametrize("codec", sorted(SOURCES))
def test_a_long_one_line_string_is_read_as_content(codec):
    source = SOURCES[codec]
    assert len(source) > 255 and "\n" not in source
    assert get_codec(codec).read(source).styling_rules
