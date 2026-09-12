"""Exercise the SLD/SE codec against the vendored third-party GeoStyler
SLD 1.1 corpus (``tests/fixtures/geostyler-sld-1.1/``, see its README).

The corpus is split by **directory**:

* ``in-scope/`` — must ``read`` -> ``write`` -> XSD-validate -> ``read`` to a
  Pydantic-model fixed point.
* ``out-of-scope/`` — must raise ``NotImplementedError`` (a clean rejection,
  never another exception type) on ``read`` or ``write``.

Moving a file between the two directories is a deliberate act: the wrong
behaviour then fails loudly. ``test_corpus_layout`` guards the split sizes
and that no fixture is left uncategorised in the corpus root.
"""

from pathlib import Path

import pytest

from pycartosym.codecs.sld_se.reader import SldSeReader
from pycartosym.codecs.sld_se.writer import SldSeWriter

from ._xsd import assert_sld_valid

CORPUS = Path(__file__).resolve().parent / "fixtures" / "geostyler-sld-1.1"
IN_SCOPE_DIR = CORPUS / "in-scope"
OUT_OF_SCOPE_DIR = CORPUS / "out-of-scope"

IN_SCOPE = sorted(p.stem for p in IN_SCOPE_DIR.glob("*.sld"))
OUT_OF_SCOPE = sorted(p.stem for p in OUT_OF_SCOPE_DIR.glob("*.sld"))

# Upstream corpus is 52 files; this split is asserted so an accidental
# add/remove/miscategorisation is caught (see the fixtures README).
_EXPECTED_IN_SCOPE = 28
_EXPECTED_OUT_OF_SCOPE = 24


def test_corpus_layout():
    assert len(IN_SCOPE) == _EXPECTED_IN_SCOPE, IN_SCOPE
    assert len(OUT_OF_SCOPE) == _EXPECTED_OUT_OF_SCOPE, OUT_OF_SCOPE
    assert not (set(IN_SCOPE) & set(OUT_OF_SCOPE))
    # nothing left loose in the corpus root
    assert not list(CORPUS.glob("*.sld"))


@pytest.mark.parametrize("stem", IN_SCOPE)
def test_in_scope_round_trips_and_validates(stem):
    reader, writer = SldSeReader(), SldSeWriter()
    fixture = IN_SCOPE_DIR / f"{stem}.sld"

    style1 = reader.read(fixture)
    xml = writer.write(style1)
    assert_sld_valid(xml, label=stem)
    style2 = reader.read(xml)
    assert style1 == style2, f"{stem}: read->write->read is not a fixed point"


@pytest.mark.parametrize("stem", OUT_OF_SCOPE)
def test_out_of_scope_raises_not_implemented(stem):
    reader, writer = SldSeReader(), SldSeWriter()
    fixture = OUT_OF_SCOPE_DIR / f"{stem}.sld"
    with pytest.raises(NotImplementedError):
        style = reader.read(fixture)
        writer.write(style)
