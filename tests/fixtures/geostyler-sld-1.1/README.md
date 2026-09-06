# Vendored GeoStyler SLD 1.1 test corpus

A copy of the SLD 1.1 test data from
[`geostyler/geostyler-sld-parser`](https://github.com/geostyler/geostyler-sld-parser),
`data/slds/1.1/`, used by `tests/test_sld_se_geostyler.py` to exercise the
`pycartosym.codecs.sld_se` reader/writer against third-party SLD/SE
1.1.0 documents (not just this project's own hand-written fixtures in
`examples/sld/`).

## Provenance

- Source: <https://github.com/geostyler/geostyler-sld-parser>
- Path: `data/slds/1.1/`
- Commit: `48f761c812d5d04df44cfa09f3969b5c78778131`
- Retrieved: 2026-08-28
- Licence: BSD-2-Clause (see the upstream repository's `LICENSE`)

**File contents are unmodified.** The only local change is layout: the 52
`.sld` files are sorted into `in-scope/` and `out-of-scope/`
subdirectories (upstream keeps them flat).

They are SE 1.1.0 (`se:` namespace, `se:SvgParameter`).

## How the tests use them

`tests/test_sld_se_geostyler.py` reads the split straight from the
directory layout:

- **`in-scope/`** (26 files) — fully within this codec's vector +
  Part-1-raster scope. Each must `read` → `write` → validate against the
  vendored OGC XSD → `read` again to a Pydantic-model fixed point.
- **`out-of-scope/`** (26 files) — using constructs this codec
  deliberately does not map. Each must raise `NotImplementedError` (a
  *clean* rejection — never another exception type).

Moving a file between the two directories is a deliberate act: the wrong
behaviour then fails loudly, and `test_corpus_layout` asserts the split
sizes and that no `.sld` is left uncategorised in the corpus root.

## Out-of-scope breakdown (26 files)

The scope boundary, mapped against this corpus:

| SE/SLD construct rejected | files | assessment |
|---|---|---|
| `se:Mark/se:WellKnownName` other than `circle`/`square` (`triangle`, `star`, `cross`, `x`, `shape://slash`, `ttf://` glyph) | 7 | extensible — needs a generic polygon shape (`ClosedPath`), not yet modeled; `square` itself mapped to `RectangleGraphic`, pycartosym issue #88 |
| `se:GraphicFill` / `se:GraphicStroke` (hatch / pattern fills & strokes) | 6 | GeoServer vendor extension / CartoSym Part 2 |
| `se:LabelPlacement/se:LinePlacement` | 3 | unfinished design work |
| unmapped `se:SvgParameter` (`stroke-linecap`, `stroke-linejoin`, `stroke-dashoffset`) | 2 | CSS/SVG stroke hints with no CartoSym `Stroke` field |
| `ogc:Function` inside `ogc:Filter` | 2 | no Filter Encoding 1.1 mapping without `ogc:Function` support |
| `ogc:Function` inside `se:Label` (`round`, …) | 1 | property-driven label text, out of scope |
| `se:RasterSymbolizer/se:ContrastEnhancement` | 1 | "not supported by SLD/SE" per OGC Annex B |
| `se:ExternalGraphic/se:InlineContent` (base64) | 1 | no `se:OnlineResource` |
| bare `se:RasterSymbolizer` (only `se:Opacity`) | 1 | niche, no fix planned |
| colour = `se:Categorize` function result | 1 | property-driven colour, out of scope |

`se:TextSymbolizer/se:Halo` ↔ `font.outline` **is** now mapped (Part-1
"font outlines"), so the 4 files that used it (`point_styledlabel*`,
`zero_values`) are in-scope. `se:Min/MaxScaleDenominator` ↔ `viz.sd` is
mapped too. The non-`circle`-mark rows (~8 files) are still "could
reasonably be added"; the rest are deliberate Part-2 / vendor scope calls.

**Source validity**: 6 of the 52 files are not themselves valid against
the pure OGC SE 1.1.0 XSD (empty `<se:Filter/>`, `ogc:Function` where the
schema wants `ogc:PropertyName`, a disallowed `type` attribute). Two of
those (`empty_filter`, `function_nested`) are in-scope — the codec
normalises them into valid SLD on write.
