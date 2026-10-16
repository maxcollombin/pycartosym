# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- CQL2-JSON: array literals are JSON arrays (`a_overlaps(tags, ('water', 'river'))` was mangled into one string), `c ? a : b` is the schema's `{"op": "?:"}` and `^` is `{"op": "^"}` (was `**`). A `[selector]` is now parsed from its original text with the CQL2-Text grammar.
- CQL2: a single-quoted string used as a function argument, or on the left of `like`, stays a string literal instead of becoming a property reference (`contains(name, 'sl')` now selects the text `sl`, not the property `sl`).

## [0.4.1] - 2026-10-14

### Added

- CartoSym-CSS → CS-JSON: a comment on the lines just before a styling rule becomes the rule's `$comment`; comments before a rule's properties become its symbolizer's `$comment` (joined with newlines), and before a property inside a graphic element, that element's. A comment that follows code on the same line (`a: 1; // note`) is not attached to anything.

### Fixed

- CS-JSON → CartoSym-CSS: `$comment` on the style, the metadata, a symbolizer and a marker element is written as a comment, not only a rule's (those four were silently dropped). A multi-line comment, or one containing `*/`, is written as `//` lines.

## [0.4.0] - 2026-10-14

### Changed

- **Breaking** (CS-JSON): a styling rule's name is now the single `name` key, as in the schema and Annex B (`name` ↔ `se:Name`). The non-standard `stylingRuleName` key is gone and is rejected on read. `name` only holds an explicit `.name 'x'` (CSCSS) or `se:Name`; it no longer repeats the layer id of a layer shorthand (`Roads[...]`), which lives in the `dataLayer.id` selector only. Old files that carried the layer id in `name` now round-trip it as `.name '…'`.
- SLD/SE: `se:Rule/se:Name` ↔ `name` (was `stylingRuleName`); `se:Title` is only the fallback `name` when there is no `se:Name`, and is written as a copy of `name`.
- MapLibre writer: a rule without `name` takes its layer id from its `dataLayer.id` selector.

## [0.3.9] - 2026-10-13

### Fixed

- CQL2 text fallback: `x NOT ILIKE 'a'` was read as `ILIKE` on a mangled identifier; it is now `NOT (x ILIKE 'a')`.
- CQL2 text fallback: `a = 1 AND|OR x BETWEEN 1 AND 2` was split on the `AND` that belongs to the `BETWEEN`.
- MapLibre codec: arithmetic on a system identifier other than `viz.sd` is no longer sampled as a scale denominator.
- MapLibre codec: a `dataLayer.id` comparison against another expression is no longer silently dropped from the filter (only `dataLayer.id = <literal>` is).
- MapLibre codec: `viz.sd <> N` now works with the operands in either order.
- MapLibre codec: a malformed value dict raises `NotImplementedError` instead of a raw pydantic `ValidationError`.
- Docstrings and comments that contradicted the code (model `extra` handling, SLD/MapLibre/CQL2 scope notes).

## [0.3.8] - 2026-10-07

### Added

- `Stroke.patternGap` and `Stroke.patternInitialGap` map to `se:Gap` and `se:InitialGap` of `se:GraphicStroke` (SE 1.1.0).
- `WELL_KNOWN_SHAPES` is part of the public API.

## [0.3.7] - 2026-10-06

### Added

- `viz.pass` maps to the order of `se:FeatureTypeStyle` elements in SLD/SE, on read and write.

## [0.3.6] - 2026-10-02

### Added

- `<>` (not equal) is accepted in CartoSym-CSS selectors; it was a syntax error before.

### Changed

- Not equal is now `<>` in CS-JSON and is written back as `<>` in CartoSym-CSS (it was `!=`). `!=` is still accepted on input and normalized to `<>`.
- CQL2 keywords are case-insensitive in CartoSym-CSS (`AND`, `OR`, `IN`, `IS NULL`, ...). Previously an upper-case keyword was silently mis-parsed as an identifier.

### Fixed

- Precedence of the unary `not` and `-` operators in CartoSym-CSS expressions: `not a = 1 and b = 2` was read as `not (a = 1 and b = 2)`; they now bind to their own operand.
- Exponent literals such as `2e3` are read as floats (they were split into `2` and an identifier `e3`).

## [0.3.5] - 2026-09-17

### Added

- SLD/SE: `se:Mark` with `wellKnownName` `triangle`, `star`, `cross` or `x` maps to a Part 2 `ClosedPath` shape.

### Fixed

- `pip install pycartosym[all]` no longer installs the development tooling.

## [0.3.4] - 2026-09-13

### Added

- SLD/SE (1.1.0): a single-character `Text` element inside a `Marker` maps to a font-glyph `se:Mark` (`ttf://` resource with `MarkIndex`).

## [0.3.3] - 2026-09-13

### Fixed

- SLD/SE: a color-map entry carrying a label raised a bare `ValueError` instead of `NotImplementedError` on `se:Categorize`.

## [0.3.2] - 2026-09-12

### Fixed

- `UnitPoint.x` and `.y` accept the `{unit: value}` shorthand (e.g. `ImageGraphic(hot_spot=[{"pc": 50}, {"pc": 50}])`).
- SLD/SE writer: `se:AnchorPoint` was silently not written for an `ImageGraphic` built through the typed API, because `hot_spot` is only reachable through its `hotSpot` alias.

## [0.3.1] - 2026-09-12

### Changed

- Documentation and package description now use the OGC name "Cartographic Symbology".

## [0.3.0] - 2026-09-12

### Added

- SLD/SE: `Fill.pattern` and `Stroke.pattern` map to `se:GraphicFill` and `se:GraphicStroke`, on read and write.

### Fixed

- `Font` accepts `color`, `opacity` and `outline`, as the CartoSym-JSON schema defines.

[Unreleased]: https://github.com/maxcollombin/pycartosym/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/maxcollombin/pycartosym/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/maxcollombin/pycartosym/compare/v0.3.9...v0.4.0
[0.3.9]: https://github.com/maxcollombin/pycartosym/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/maxcollombin/pycartosym/compare/v0.3.7...v0.3.8
[0.3.7]: https://github.com/maxcollombin/pycartosym/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/maxcollombin/pycartosym/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/maxcollombin/pycartosym/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/maxcollombin/pycartosym/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/maxcollombin/pycartosym/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/maxcollombin/pycartosym/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/maxcollombin/pycartosym/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/maxcollombin/pycartosym/compare/v0.2.2...v0.3.0
