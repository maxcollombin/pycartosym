"""CLI behaviour: exit codes, streams, quiet mode, diagnostics."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def run(*argv: str, **kw) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pycartosym.cli", *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        **kw,
    )


class TestExitCodes:
    def test_no_args_prints_help_and_exits_usage(self):
        r = run()
        assert r.returncode == 1

    def test_missing_input_file_is_not_found(self):
        r = run("does-not-exist.cscss", "--print")
        assert r.returncode == 2
        assert "file not found" in r.stderr

    def test_syntax_error_is_input_invalid(self, tmp_path: Path):
        bad = tmp_path / "bad.cscss"
        bad.write_text("Fill {\n  color: ;\n}\n", encoding="utf-8")
        r = run("validate", str(bad))
        assert r.returncode == 3
        assert "syntax error" in r.stderr
        # position + caret
        assert f"{bad}:2:" in r.stderr
        assert "^" in r.stderr

    def test_convert_syntax_error_is_input_invalid(self, tmp_path: Path):
        """Same formatted-error path as `validate`, via the default convert
        command (regression: convert used to pre-check syntax with its own
        separate lex+parse pass, ahead of the real parse inside the
        conversion itself — two full parses of the same file; now there is
        only the one, its CartoSymSyntaxError caught and reported here).
        """
        bad = tmp_path / "bad.cscss"
        bad.write_text("Fill {\n  color: ;\n}\n", encoding="utf-8")
        r = run(str(bad), "--print")
        assert r.returncode == 3
        assert "syntax error" in r.stderr
        assert f"{bad}:2:" in r.stderr
        assert "^" in r.stderr

    def test_unknown_conversion_is_unsupported(self, tmp_path: Path):
        src = tmp_path / "x.weird"
        src.write_text("{}", encoding="utf-8")
        r = run(str(src), "--print")
        assert r.returncode == 4

    def test_transcode_gap_is_its_own_code(self):
        # 0-basic.cscss used to hit this too (a symbolizer-less rule had no
        # MapLibre mapping); it now converts to an empty `layers: []`
        # (safe to drop, nothing lost — see MaplibreWriter._is_empty_of_paint).
        # 5-coverage-dem.cscss used to hit this too (raster/coverage was
        # entirely unmapped); a singleChannel+colorMap now maps to a
        # color-relief layer (see MaplibreWriter._raster). Band selection
        # (colorChannels) remains a genuine gap — no MapLibre layer draws
        # from anything but an already-rendered image.
        r = run(
            str(EXAMPLES / "6-coverage-sentinel2.cscss"),
            "--to-format",
            "maplibre",
            "--print",
        )
        assert r.returncode == 5


class TestStreamsAndQuiet:
    def test_success_note_on_stdout_by_default(self, tmp_path: Path):
        out = tmp_path / "out.cs.json"
        r = run(str(EXAMPLES / "0-basic.cscss"), "-o", str(out))
        assert r.returncode == 0
        assert out.exists()
        assert r.stdout.strip().startswith("ok:")

    def test_quiet_silences_success_note(self, tmp_path: Path):
        out = tmp_path / "out.cs.json"
        r = run(str(EXAMPLES / "0-basic.cscss"), "-o", str(out), "-q")
        assert r.returncode == 0
        assert r.stdout == ""

    def test_errors_go_to_stderr(self):
        r = run("nope.cscss", "--print")
        assert r.stdout == ""
        assert "error:" in r.stderr


class TestConversion:
    def test_cscss_source_is_lexed_only_once(self):
        """Regression: convert used to run a full throwaway lex+parse
        (its own raw ANTLR lexer/parser, bypassing CartoSymParser
        entirely) to check syntax, then a second full parse — via
        CartoSymParser — for the real conversion. Every successful cscss
        conversion paid for ANTLR twice. Spying on the lexer class itself
        (the one thing both the old pre-check and the real parse always
        construct, whichever path builds it) catches either form of the
        double-parse, not just a second CartoSymParser.parse_string call.
        """
        from unittest.mock import patch

        from pycartosym import cli
        from pycartosym.grammar.generated.CartoSymCSSLexer import CartoSymCSSLexer

        args = cli.create_argument_parser().parse_args(
            [str(EXAMPLES / "0-basic.cscss"), "--print"]
        )
        with patch(
            "pycartosym.parser.CartoSymCSSLexer",
            side_effect=CartoSymCSSLexer,
        ) as spy:
            with patch("sys.stdout"):
                rc = cli.convert_command(args)
        assert rc == 0
        assert spy.call_count == 1

    def test_print_defaults_to_the_other_text_encoding(self):
        r = run(str(EXAMPLES / "0-basic.cscss"), "--print")
        assert r.returncode == 0
        assert '"stylingRules"' in r.stdout

    def test_output_needs_force_to_overwrite(self, tmp_path: Path):
        out = tmp_path / "out.cs.json"
        out.write_text("x", encoding="utf-8")
        r = run(str(EXAMPLES / "0-basic.cscss"), "-o", str(out))
        assert r.returncode == 1
        assert "--force" in r.stderr

    @pytest.mark.parametrize("no_color", ["1", None])
    def test_no_color_env_strips_ansi(self, no_color: str | None):
        env = {"PATH": __import__("os").environ["PATH"]}
        if no_color is not None:
            env["NO_COLOR"] = no_color
        r = run("nope.cscss", "--print", env=env)
        assert "\033[" not in r.stderr


class TestVersion:
    def test_version_matches_package_metadata(self):
        from pycartosym import __version__

        r = run("--version")
        assert r.returncode == 0
        assert r.stdout.strip() == f"pycartosym {__version__}"


class TestValidateJson:
    def test_valid_cscss_reports_valid_true(self):
        import json

        r = run("validate", str(EXAMPLES / "0-basic.cscss"), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data == {
            "valid": True,
            "file": str(EXAMPLES / "0-basic.cscss"),
            "format": "cscss",
        }

    def test_invalid_cscss_reports_structured_errors(self, tmp_path: Path):
        import json

        bad = tmp_path / "bad.cscss"
        bad.write_text("Fill {\n  color: ;\n}\n", encoding="utf-8")
        r = run("validate", str(bad), "--json")
        assert r.returncode == 3
        data = json.loads(r.stdout)
        assert data["valid"] is False
        assert data["format"] == "cscss"
        assert data["errors"] and "line" in data["errors"][0]
        assert r.stderr == ""

    def test_missing_file_reports_valid_false(self):
        import json

        r = run("validate", "does-not-exist.cscss", "--json")
        assert r.returncode == 2
        data = json.loads(r.stdout)
        assert data == {
            "valid": False,
            "file": "does-not-exist.cscss",
            "error": "file not found",
        }


class TestLogLevel:
    def test_log_level_works_after_subcommand(self):
        r = run("parse", str(EXAMPLES / "0-basic.cscss"), "--log-level", "DEBUG")
        assert r.returncode == 0
        assert "DEBUG" in r.stderr or "INFO" in r.stderr

    def test_quiet_overrides_log_level(self):
        r = run("parse", str(EXAMPLES / "0-basic.cscss"), "--log-level", "DEBUG", "-q")
        assert r.returncode == 0
        assert r.stderr == ""
        assert r.stdout == ""
