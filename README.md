# pycartosym

[![CI](https://github.com/maxcollombin/pycartosym/actions/workflows/ci.yml/badge.svg)](https://github.com/maxcollombin/pycartosym/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pycartosym.svg)](https://pypi.org/project/pycartosym/)

A Python package for lossless transcoding between [CartoSym CSS](https://github.com/opengeospatial/styles-and-symbology) (`.cscss`) and other encodings of the OGC Style & Symbology conceptual model (CS-JSON, SLD/SE), plus MapLibre Style as a practical interoperability target.

## Supported Formats

CartoSym-CSS (`.cscss`) and CS-JSON (`.cs.json`) are the two OGC Style &
Symbology encodings this package reads and writes losslessly. SLD/SE
(`.sld`, 1.1.0 and 1.0.0, including SLD 1.0.0 with GeoServer
`<VendorOption>` pass-through) is also OGC. MapLibre Style (`.json`) is
the MapLibre/Mapbox de facto spec, not OGC, supported as a practical
interoperability target. All are read and written.

Each codec is covered for the constructs the target format actually
expresses (a symbolizer or property with no equivalent on the other side
raises rather than silently dropping data).

## Installation

### From PyPI

```bash
pip install pycartosym
```

### From Source

```bash
git clone https://github.com/maxcollombin/pycartosym.git
cd pycartosym
uv sync --all-extras
```

The generated ANTLR lexer/parser are already committed under
`src/pycartosym/grammar/generated/`, so no separate grammar build
step is needed. Prefix commands with `uv run`, or activate the
project's `.venv` with `source .venv/bin/activate`.

## Usage

```bash
# Format auto-detected from the file extensions where that's unambiguous
cartosym <input-file> -o <output-file>

# Explicit target format (needed for the SLD dialects and MapLibre,
# since a plain .sld/.json extension can't disambiguate those)
cartosym --to-format <sld|sld:1.0.0|sld:geoserver|maplibre|cscss|csjson> <input-file> -o <output-file>

# Display structure info for a CSCSS file, without converting it
cartosym parse <input-file>

# Validate a .cscss or .cs.json file against the grammar/JSON schema
cartosym validate <input-file>

# Full option and format reference
cartosym --help
```

A few concrete conversions, using the files under [`examples/`](examples/)
(`examples/sld/` for SLD/SE):

```bash
cartosym examples/0-basic.cscss -o out.cs.json
cartosym examples/13-vector-point-circle.cscss --to-format sld -o out.sld
cartosym examples/sld/1-polygon-fill-stroke.sld --to-format maplibre -o out.json
```

## Python API

Most users work through the `cartosym` CLI above. The `cql2` submodule also
exposes CQL2 (the OGC 21-065r2 query-expression sublanguage that
CartoSym-CSS embeds in `[ filter ]` selectors and CS-JSON encodes as
`{"op": …, "args": …}`) as a stable, importable API:

```python
from pycartosym import cql2

# CQL2-Text -> expression model
expr = cql2.parse_text("population > 1000")

# Expression model -> CQL2-JSON
cql2.to_cql2_json(expr)
# {'op': '>', 'args': [{'property': 'population'}, 1000]}

# CQL2-JSON selector dict -> CartoSym-CSS filter text
cql2.to_cql2_text({
    "op": "and",
    "args": [
        {"op": "=", "args": [{"property": "a"}, 1]},
        {"op": "like", "args": [{"property": "b"}, "x%"]},
    ],
})
# "a = 1 and b like 'x%'"

# Operator/function vocabulary, derived from the CQL2 Pydantic models
cql2.vocab.SPATIAL_RELATE                       # 's_relate'
"s_intersects" in cql2.vocab.KNOWN_CQL2_CALLS   # True
```

`cql2.parse_tree` is a lower-level entry point for converting an
already-parsed ANTLR `expression` context (as produced while walking the
CartoSym-CSS grammar) — most callers want `parse_text`.

## Development

```bash
uv sync --all-extras
uv run pytest
```

## License

See [LICENSE](LICENSE).
