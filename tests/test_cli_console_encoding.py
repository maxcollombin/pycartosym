"""A console that cannot encode ``→`` (Windows cp1252) must not fail a conversion."""

import os
import subprocess
import sys


def test_conversion_succeeds_on_a_cp1252_console(tmp_path):
    source = tmp_path / "a.cscss"
    source.write_text("L { fill: { color: red }; }\n")
    out = tmp_path / "a.cs.json"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from pycartosym.cli import main; "
            "sys.argv = ['cartosym', *sys.argv[1:]]; raise SystemExit(main())",
            "--to-format",
            "csjson",
            str(source),
            "-o",
            str(out),
        ],
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("cp1252", "replace")
    assert out.exists()
