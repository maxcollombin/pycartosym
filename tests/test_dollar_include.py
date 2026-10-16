"""`.include` is written as `$include` unless the files are inlined."""

import json
import subprocess
import sys

import pytest

from pycartosym.converter import Converter


def _cli(*argv: str) -> int:
    return subprocess.run(
        [sys.executable, "-m", "pycartosym.cli", *argv], capture_output=True
    ).returncode


@pytest.fixture
def project(tmp_path):
    (tmp_path / "base.cscss").write_text("@w = 3;\nWater { fill: { color: blue }; }\n")
    main_file = tmp_path / "main.cscss"
    main_file.write_text(
        ".include 'base.cscss'\n"
        "Roads { stroke: { width: @w * 2 px; color: red }; }\n"
    )
    return tmp_path


def test_include_is_kept_as_dollar_include(project):
    data = Converter().cscss_to_csjson(project / "main.cscss")
    assert data["$include"] == "base.cscss"
    assert [r["selector"]["args"][1] for r in data["stylingRules"]] == ["Roads"]


def test_several_includes_are_a_list(tmp_path):
    for name in ("a", "b"):
        (tmp_path / f"{name}.cscss").write_text("X { opacity: 1; }\n")
    (tmp_path / "m.cscss").write_text(".include 'a.cscss'\n.include 'b.cscss'\n")
    data = Converter().cscss_to_csjson(tmp_path / "m.cscss")
    assert data["$include"] == ["a.cscss", "b.cscss"]


def test_reference_to_an_included_variable_is_a_ref(project):
    data = Converter().cscss_to_csjson(project / "main.cscss")
    width = data["stylingRules"][0]["symbolizer"]["stroke"]["width"]
    assert width == {"px": {"op": "*", "args": [{"$ref": "#/$variables/w"}, 2]}}
    assert "$variables" not in data  # defined in the included file


def test_inline_includes_merges_the_files(project):
    data = Converter(inline_includes=True).cscss_to_csjson(project / "main.cscss")
    assert "$include" not in data
    assert data["$variables"] == {"w": 3}
    assert [r["selector"]["args"][1] for r in data["stylingRules"]] == [
        "Water",
        "Roads",
    ]


def test_include_round_trips_through_cscss(project):
    converter = Converter()
    first = converter.cscss_to_csjson(project / "main.cscss")
    text = converter.csjson_to_cscss(json.dumps(first))
    assert ".include 'base.cscss'" in text
    assert converter.cscss_to_csjson(text) == first


def test_cli_inlines_for_maplibre(project, tmp_path):
    out = tmp_path / "out.maplibre.json"
    code = _cli(str(project / "main.cscss"), "-o", str(out))
    assert code == 0
    assert len(json.loads(out.read_text())["layers"]) == 2
