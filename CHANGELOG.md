# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

- `<>` (not equal) is read and written; it is the canonical CS-JSON operator, and `!=` is still accepted on input.

### Changed

- CQL2 keywords are case-insensitive in CartoSym-CSS (`AND`, `OR`, `IN`, `IS NULL`, ...). Previously an upper-case `AND` was silently read as a property name.

### Fixed

- Precedence of the unary `not` and `-` operators in CartoSym-CSS expressions.
- Exponent literals such as `2e3` are read as floats.

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
- SLD/SE writer: fields reachable only through their JSON alias (e.g. `ImageGraphic.hot_spot`) were ignored on typed instances, so `se:AnchorPoint` was never written.

## [0.3.1] - 2026-09-12

### Changed

- Documentation and package description now use the OGC name "Cartographic Symbology".

## [0.3.0] - 2026-09-12

### Added

- SLD/SE: `Fill.pattern` and `Stroke.pattern` map to `se:GraphicFill` and `se:GraphicStroke`, on read and write.

### Fixed

- `Font` accepts `color`, `opacity` and `outline`, as the CartoSym-JSON schema defines.

[Unreleased]: https://github.com/maxcollombin/pycartosym/compare/v0.3.9...HEAD
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
