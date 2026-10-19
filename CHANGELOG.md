# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Breaking** (Python API): `UnitType.PICAS` is now `UnitType.PERCENT`. `pc` is percent in CartoSym-CSS (an Image's `hotSpot`, `50 pc 50 pc`), never picas; the value `"pc"` is unchanged.

### Fixed

- `import pycartosym` no longer needs `lxml` (the `sld` extra): the MapLibre writer imported a helper from the SLD codec. CartoSym-CSS, CS-JSON, MapLibre and the `cql2` API work with the core dependencies; SLD/SE is registered only when `lxml` is installed.
- CartoSym-CSS: a pattern stroke (`pattern`, `patternGap`, `patternInitialGap`) is read and written back instead of being dropped; the gaps accept units (`20 px`) in CartoSym-CSS and CS-JSON, and the SLD writer takes them in pixels.
- CartoSym-CSS: inches are `inch` as the specification writes them (`2 inch` is `{"in": 2}` in CS-JSON, and is written back as `inch`); `2 in` was written but could not be read back.
- CartoSym-CSS: a graphic's `position` with units (`3 px 4 px`) is read, instead of dropping the whole marker.
- Dot pattern `distance`: the `{horizontal, vertical}` object and the `[h, v]` array are read, kept in CS-JSON and written back to CartoSym-CSS, instead of becoming text (CartoSym-CSS) or a validation error (CS-JSON).
- CQL2: an expression that is only a string literal (`'abc'`) is the string `"abc"`, not a property reference; a label's `Text { text: 'Oslo' }` is the text Oslo, not the value of a property named Oslo.

## [0.5.1] - 2026-10-19

### Fixed

- CartoSym-CSS: a stroke's `cap`, `join`, `dashPattern` (tuple `5 5` or array `[2, 1]`), `casing` and `center` (or `centerLine`) are read, also in the `stroke.casing: {...}` form, instead of being dropped without a trace; an unreadable `dashPattern` logs a warning. The writer writes them back instead of raising `NotImplementedError`. A stroke `pattern` graphic still raises.
- CartoSym-CSS: a hexadecimal colour that is not 3, 6 or 8 digits (`#57510`) is a syntax error with its line and column, instead of passing through as an unreadable colour.
- CQL2: an identifier on the right of a comparison (`a = b`) is a property reference, not the text `b`; a double-quoted token (`"my col" = 1`) is an identifier, not a string. A bare word against a system identifier (`dataLayer.type = vector`) stays an enumeration value.

## [0.5.0] - 2026-10-16

### Changed

- **Breaking** (CS-JSON): CartoSym-CSS `.include 'x.cscss'` is written as `$include` (a string, or an array for several files) instead of merging the included rules and variables into the output, as the CartoSym 2.0 draft requires. The included files are still parsed, so `@name` in the including file references a variable they define. `Converter(inline_includes=True)` and `CartoSymParser(inline_includes=True)` keep the old merging; the CLI applies it automatically for SLD and MapLibre output, which have no include. The MapLibre writer raises `NotImplementedError` on `$include`, like the SLD writer.
- **Breaking** (CS-JSON): variables follow the CartoSym 2.0 draft. `$variables` is an object `{name: value}` (was a list of `{name, value}`), and every `@name` reference is written `{"$ref": "#/$variables/name"}`, in plain property values (`color: @c`) and inside expressions (`@w * 2 px` → `{"px": {"op": "*", "args": [{"$ref": ...}, 2]}}`). References are no longer replaced by the variable's value. The old list form is still read. A variable value may be an expression (`@a = 2 px`).
- SLD and MapLibre writers write a reference as its value. The SLD writer no longer refuses a style with `$variables`, but a width computed by an expression has no SLD form and raises `NotImplementedError`.
- Bundled schema: `variableRef` is accepted wherever `propertyRef` is, and the `{r, g, b}` colour object rejects other keys (a `{"property": …}` or `$ref` colour matched both branches of its `oneOf`).

### Fixed

- Expressions with units, as property values: `6 px` stays `{"px": 6}` inside `? :` and operations, and a unit shared by an arithmetic expression is written around it (`lanes * 2 px` ↔ `{"px": {"op": "*", ...}}`, the schema's `unitValue`). `stroke.width: lanes > 2 ? 6 px : 2 px` and any other operation are converted instead of kept as text. Mixed units in one operation are rejected. Written back to CartoSym-CSS as expressions (`? :`, `^`, parentheses), not Python reprs.
- CartoSym-CSS → CS-JSON: an operation used as a property value (`text: upperCase(name)`, `opacity: 2 ^ -1`) becomes CQL2-JSON instead of a property named `upperCase(name)` or a dropped value; an `opacity` that cannot be parsed logs a warning. `-1` is the number -1, not a unary operation.
- CQL2-JSON: array literals are JSON arrays (`a_overlaps(tags, ('water', 'river'))` was mangled into one string), `c ? a : b` is the schema's `{"op": "?:"}` and `^` is `{"op": "^"}` (was `**`). A `[selector]` is now parsed from its original text with the CQL2-Text grammar.
- CQL2: a single-quoted string used as a function argument, or on the left of `like`, stays a string literal instead of becoming a property reference (`contains(name, 'sl')` now selects the text `sl`, not the property `sl`).
- CartoSym-CSS → CS-JSON: a file with `.include` and its own variables no longer silently loses its own rules and variables. Included stylesheets are now parsed separately and merged (their variables and rules come before the file's own). Input left unparsed after a point where parsing cannot continue (such as a variable after a rule) is now a syntax error instead of being dropped.
- CS-JSON: `metadata.keywords` is also accepted as a comma-separated string (as CartoSym-CSS `.keywords 'a, b'` writes it), not only as an array.

## [0.4.1] - 2026-10-14

### Added

- CartoSym-CSS → CS-JSON: a comment on the lines just before a styling rule becomes the rule's `$comment`; comments before a rule's properties become its symbolizer's `$comment` (joined with newlines), and before a property inside a graphic element, that element's. A comment that follows code on the same line (`a: 1; // note`) is not attached to anything.

### Fixed

- CartoSym-CSS → CS-JSON: a file with `.include` and its own variables (or any input after a point where parsing cannot continue, such as a variable after a rule) no longer silently loses its own rules and variables. Included stylesheets are now parsed separately and merged (variables and rules before the file's own); input left unparsed is a syntax error.
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

[Unreleased]: https://github.com/maxcollombin/pycartosym/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/maxcollombin/pycartosym/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/maxcollombin/pycartosym/compare/v0.4.1...v0.5.0
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
