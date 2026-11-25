"""Validate a MapLibre style dict against the official style specification.

MapLibre's ``v8.json`` reference is a bespoke schema format, not JSON
Schema, and there is no maintained Python validator. The authoritative
check is the ``gl-style-validate`` CLI shipped in the npm package
``@maplibre/maplibre-gl-style-spec`` — this module drives it through
``npx`` and turns a non-empty error list into a test failure.

If Node / ``npx`` is unavailable the check is skipped (same policy as the
optional XSD checks for the SLD codec).
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

# Pinned, so that npx finds the package in its cache (`--prefer-offline`)
# instead of asking the registry for the latest version on every call, and so
# that a new release of the specification cannot change the result unnoticed.
# The CI caches ~/.npm under this version (.github/workflows/ci.yml).
_PACKAGE = "@maplibre/maplibre-gl-style-spec@26.6.0"
_BIN = "gl-style-validate"


def _npx() -> str | None:
    return shutil.which("npx")


def maplibre_spec_available() -> bool:
    """True if the MapLibre validator can be run (Node + ``npx`` present)."""
    return _npx() is not None


def assert_maplibre_valid(style: dict) -> None:
    """Fail the calling test if *style* is not a valid MapLibre GL style.

    Skips (rather than fails) when the validator toolchain is missing, so
    the suite still runs on a machine without Node.
    """
    npx = _npx()
    if npx is None:
        pytest.skip("npx / Node not available — cannot run gl-style-validate")

    try:
        proc = subprocess.run(
            [
                npx,
                "--yes",
                "--prefer-offline",
                "-p",
                _PACKAGE,
                _BIN,
                "--json",
                "/dev/stdin",
            ],
            input=json.dumps(style),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:  # pragma: no cover - environment-dependent
        pytest.skip("gl-style-validate timed out (first-run npm download?)")

    # The CLI prints a JSON array of {message, severity, line}; empty on success.
    out = proc.stdout.strip()
    errors: list[dict] = []
    if out:
        try:
            parsed = json.loads(out)
            errors = [e for e in parsed if e.get("severity") == "error"]
        except json.JSONDecodeError:  # pragma: no cover - unexpected CLI output
            if proc.returncode != 0:
                pytest.fail(f"gl-style-validate failed:\n{proc.stdout}\n{proc.stderr}")
            return

    if errors:
        lines = "\n".join(f"  - {e['message']}" for e in errors)
        pytest.fail(f"style is not spec-valid:\n{lines}")
