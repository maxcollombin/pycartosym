"""``import pycartosym`` works without the optional ``lxml`` (the ``sld`` extra)."""

import subprocess
import sys

_SCRIPT = """
import sys

class _NoLxml:
    def find_spec(self, name, path=None, target=None):
        if name == "lxml" or name.startswith("lxml."):
            raise ModuleNotFoundError("No module named 'lxml'")

sys.meta_path.insert(0, _NoLxml())
from pycartosym import cql2, codecs

names = {c.format_name for c in codecs.list_codecs()}
assert {"cscss", "csjson", "maplibre"} <= names and "sld" not in names, names
assert cql2.to_cql2_json(cql2.parse_text("a = 1"))["op"] == "="
"""


def test_core_import_and_codecs_without_lxml():
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
