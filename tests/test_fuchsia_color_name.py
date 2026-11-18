"""The colour name is `fuchsia`; the old schema's `fuschia` is still read."""

import pytest

from pycartosym.codecs.sld.writer import SldWriter
from pycartosym.models.styles import Style


def _style(name):
    return Style.from_dict(
        {"stylingRules": [{"symbolizer": {"fill": {"color": name}}}]}
    )


@pytest.mark.parametrize("name", ["fuchsia", "fuschia"])
def test_fuchsia_spellings_are_read_and_kept(name):
    style = _style(name)
    dumped = style.model_dump(by_alias=True, exclude_none=True)
    assert dumped["stylingRules"][0]["symbolizer"]["fill"]["color"] == name


@pytest.mark.parametrize("name", ["fuchsia", "fuschia"])
def test_fuchsia_spellings_are_magenta_in_sld(name):
    assert "#ff00ff" in SldWriter().write(_style(name))
