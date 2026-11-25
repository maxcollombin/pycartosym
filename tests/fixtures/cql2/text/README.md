# Vendored OGC CQL2-Text example corpus

The official CQL2-Text examples published alongside the OGC 21-065r2
(Common Query Language 2) standard. Used by
`tests/test_cql2text_treewalker.py` as a conformance corpus for the
standalone `CQL2Text.g4` grammar (`vendor/cartosymcss-grammar/CQL2Text.g4`)
— every file here must parse without a syntax error.

File contents are **unmodified**.

## Provenance

- Source: <https://github.com/opengeospatial/ogcapi-features>
- Path: `cql2/standard/schema/examples/text/`
- Commit: `29acfc5da22a173b9c74114e6313189c972a8340`
- Retrieved: 2026-08-31
- Licence: OGC document/IPR licence (see the upstream repository's
  `LICENSE` file) — the same OGC copyright terms already covering the
  vendored SLD/SE XSDs under `tests/schemas/ogc-sld-1.0.0/`.

`clauseN_XX.txt` files are the worked examples embedded in the standard's
own clause text (§6/§7); `exampleNN[-altNN].txt` are the standalone
examples appendix. Both sets are real, spec-authored CQL2-Text — not
hand-written test fixtures — which is exactly why they are useful as a
grammar conformance corpus independent of this project's own assumptions.
