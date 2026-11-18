"""The cases of examples/passes/ read as CartoSym-CSS and match their CS-JSON."""

import json
from pathlib import Path

import pytest

from pycartosym.converter import Converter

CASES = sorted((Path(__file__).parent.parent / "examples" / "passes").glob("*.cscss"))


def test_cases_exist():
    assert len(CASES) >= 8


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_case_matches_its_csjson(case):
    expected = json.loads(case.with_suffix(".cs.json").read_text(encoding="utf-8"))
    assert Converter().cscss_to_csjson(case.read_text(encoding="utf-8")) == expected
