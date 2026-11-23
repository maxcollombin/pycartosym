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


def _convert(case: Path, to_format: str, monkeypatch, capsys) -> str:
    from pycartosym.cli import main

    monkeypatch.setattr(
        "sys.argv", ["cartosym", str(case), "--to-format", to_format, "--print"]
    )
    assert main() == 0
    return capsys.readouterr().out


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_case_matches_its_maplibre(case, monkeypatch, capsys):
    expected = case.with_suffix(".maplibre.json")
    if not expected.exists():
        pytest.skip("no MapLibre file: the writer refuses this case")
    out = _convert(case, "maplibre", monkeypatch, capsys)
    assert json.loads(out) == json.loads(expected.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_case_matches_its_sld(case, monkeypatch, capsys):
    expected = case.with_suffix(".sld")
    if not expected.exists():
        pytest.skip("no SLD/SE file: the writer refuses this case")
    out = _convert(case, "sld", monkeypatch, capsys)
    assert out.strip() == expected.read_text(encoding="utf-8").strip()
