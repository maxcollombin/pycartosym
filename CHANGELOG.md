# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- MapLibre: `viz.pass` orders the layers (a layer of a pass comes after those of the previous pass; a rule without a pass is in pass 0). `feature.pass` still raises, it has no MapLibre equivalent.
- `examples/passes/`: CartoSym-CSS cases for nested-rule overriding, `feature.pass`, `viz.pass`, casing and `zOrder`, with the SLD/SE and MapLibre that pycartosym writes from them.

### Changed

- SLD/SE writer: a rule that does not test `viz.pass` applies in pass 0 only, as settled in opengeospatial/cartographic-symbology#198, so it goes into the first `se:FeatureTypeStyle`; a style that mixed rules with and without `viz.pass` was refused.

### Fixed

- CartoSym-CSS and CS-JSON: a call without argument as the value of a property (`opacity: random()`) is read and written back; it was refused with a validation error. SLD/SE and MapLibre have no equivalent and still refuse it, with a clear error.
- CQL2-Text writer: a property named `null`, `true`, `false` or another keyword, or whose name is not a plain identifier, is written double-quoted; written bare, `"null"` read back as the `null` literal.
- CartoSym-CSS writer: `%` is written as an infix operator with the precedence of `*` and `/`; a right operand of the same precedence keeps its brackets (`a - (b - c)` was written `a - b - c`), and so does a nested `and` / `or` written as a later operand.
- CartoSym-CSS writer: the `tint` and `blackTint` of an Image are written as colors; the `[r, g, b]` array was read back as a string.
- CartoSym-CSS and CS-JSON: `fill: null` and `stroke: null` are kept (they were dropped when reading CartoSym-CSS and refused by the bundled schema). `null` means the entity is not drawn by that property, as for `marker` and `label`; SLD/SE and MapLibre write nothing for it.
- SLD/SE and MapLibre: a rule with refinements no longer draws the features its refinements select (they were drawn twice, the parent's stroke under the refinement's). The parent's selector now excludes its refinements' property selectors; refinements that test a system identifier (`viz.pass`, `feature.pass`, scale) still stack. Two refinements that select the same feature are both still drawn.
- CS-JSON: a `marker` given as an expression (`{"property": "m"}`, a variable reference) is read and kept, as the revised schema allows. It has no CartoSym-CSS or SLD/SE or MapLibre form and is refused with a clear error by the writers.
- CS-JSON: shapes that are valid in the revised schema and were rejected are read: a boolean `selector` (`true` selects everything, `false` nothing; written as `[true]` in CartoSym-CSS, no filter in SLD/SE and MapLibre), `stroke.center` (the name in the specification text, read as `centerLine`), the unit key `inch` (read as `in`), an RGB colour whose components are expressions or that only overrides some of them (`{"alter": true, "r": 100}`), and a variable reference into an included file (`"base.cs.json#/$variables/w"`, written as `@w`). The bundled schema accepts `inch` and the file-qualified reference. A colour with expression or partial components has no CartoSym-CSS or SLD/SE form and is refused with a clear error.
- CartoSym-CSS: a nested rule without a selector keeps none, instead of receiving a copy of its parent's selector, so it merges into its parent (the last of several siblings wins) in SLD/SE and MapLibre; it was written as a separate rule that was drawn too (#190).
- SLD/SE: the vertical offset of a graphic or label `position` is written as the opposite `se:DisplacementY` and read back the same way: a positive `y` points down in CartoSym and up in `se:DisplacementY`. Offsets were written with the wrong vertical direction.
- The colour name `fuchsia` (the spelling of the revised schema) is accepted next to the misspelled `fuschia`, in CS-JSON, CartoSym-CSS and SLD/SE; each is kept as given.

## [0.6.6] - 2026-11-18

### Added

- `feature.pass` is a system identifier: CartoSym-CSS `[feature.pass = 0]` is read as `{"sysId": "feature.pass"}` instead of a property, and the SLD/SE writer turns rules that differ only by their `feature.pass` into the symbolizers of one `se:Rule`, in pass order; the SLD/SE reader reads a symbolizer kind repeated in one `se:Rule` (casing, parallel strokes, which the second used to override) as one rule per `feature.pass` (#203).

### Fixed

- Bundled schema: a stroke accepts `dashOffset` (a unit value), as the converters already read and write it (#182).
- SLD/SE and MapLibre writers: a nested rule without a selector refines its parent (its symbolizer is merged into the parent's, as if its curly brackets were removed) instead of becoming an `se:ElseFilter` rule that lost the parent's selector, or an error in MapLibre; the SLD reader reads an `se:ElseFilter` rule as the negation of the earlier rules' selectors (#190).
- CartoSym-CSS: a string literal that reads like a number, a boolean or `null` (`'1000'`, `'true'`, `'null'`) is written with its quotes, so it reads back as a string (#192).
- CartoSym-CSS: `not` over `and` / `or` is written with its brackets (`not (a = 1 or b = 2)`) instead of changing its meaning (#193).
- CartoSym-CSS: a graphic's `transform.scaling` is written (`transform: {orientation: 45; scaling: 2 3}`) and read back as `[x, y]` instead of being dropped (#195).
- CartoSym-CSS: symbolizer vendor properties (`vendor.<vendorName>.<propertyName>`) are written and read back instead of being dropped; a value without a CartoSym-CSS form is reported (#196).
- CartoSym-CSS: a property path with a numeric part (`purpose.0`, `purpose.0.general`) in a conditional is read as one property instead of a tuple or a garbled comparison (#194).
- CS-JSON: an angle given as the schema's `{"deg": …}` / `{"rad": …}` object (e.g. `transform.orientation` of a fill or stroke pattern) is accepted and kept as given instead of failing validation; CartoSym-CSS writes one holding an expression instead of failing (#191).
- A one-line source string longer than a file name may be (a CS-JSON or CartoSym-CSS style passed to `read`) is read as content instead of raising `OSError: File name too long` on Python 3.10-3.13 (#199).
- MapLibre: `isNull` is written as `["==", ["get", k], null]` and its negation as `["!=", ["get", k], null]`, which also hold for a property set to null, instead of `!has` / `has`; both are read back as `isNull` (#197).
- MapLibre: a symbolizer with only vendor properties raises the unknown-vendor-extension error instead of being dropped without a warning (#198).

## [0.6.5] - 2026-11-16

### Fixed

- CartoSym-CSS: `marker` and `label` set to `null`, to an empty `{ }` or to `{ elements: [] }` are kept in both directions instead of being merged into one form (#174).
- CartoSym-CSS: a style with many rules converts instead of failing on the depth of the parse tree, which is now walked iteratively (#178).
- CartoSym-CSS: `colorChannels` and `singleChannel` expressions are written back as infix CartoSym-CSS (#172), and `contains`, `startsWith` and `endsWith` as lower-camel-case function calls (#173).
- CartoSym-CSS: `stroke.dashOffset` is kept (it was dropped without a warning) and written back (#182). SLD/SE and MapLibre raise a clear error for it, as neither has a mapping.
- CartoSym-CSS: a `dashPattern` with units (`[ 8 px, 4 mm ]`) is read as unit values instead of being ignored (#183). SLD/SE writes lengths in pixels only; a length in another unit raises an error.
- CartoSym-CSS: a bare name in label placement (`priority: elevation`) is a property reference, not a string (#184).
- CartoSym-CSS: the hex colour of a `Dot`, and the `tint` and `blackTint` of an `Image`, are written as `[r, g, b]` like other colours (#185).
- CartoSym-CSS: `''` and `\'` in a styling rule name are read as a quote, and the name is written back escaped (#179).
- CartoSym-CSS: a call with several arguments in a property value (`stroke: { width: min(a, b) }`, `stroke.width: abs(a)`) is converted to an operation instead of being cut at the comma or turned into text; a quoted string or a `//` comment containing `,` or `;` no longer splits a block (#187).

## [0.6.4] - 2026-11-09

### Fixed

- CartoSym-CSS: `a ? b : c ? d : e` is read right to left, as `a ? b : (c ? d : e)` (#167).
- CartoSym-CSS: a function call or `^` in `colorChannels` / `singleChannel` is kept as an operation instead of becoming a property named after the text (#168).
- CartoSym-CSS: data layer names in a selector are combined with OR, and with the other selectors with AND (`Roads Railways[level < 4]`); the writer emits that form back (#169).

## [0.6.3] - 2026-11-03

### Fixed

- CartoSym-CSS: a graphic's `transform: {orientation: ...}` is read on a label's `Text` (it failed with a validation error) and on a marker (the value stayed text) as an angle or a CQL2 expression, and is written back instead of being dropped.
- CartoSym-CSS: a text alignment given by expressions is written as `alignment: {expr, expr}` instead of a Python dict, and read back.
- SLD/SE: a label whose text is a `concatenate` of properties and text is written as the mixed content of `se:Label`.
- CartoSym-CSS: a boolean literal in a selector is written `true` / `false`, not `True` / `False`.
- CartoSym-CSS: a single quote inside a string is doubled when writing (`'it''s'`) in selectors and metadata, and metadata strings read `''` and `\'` as a quote instead of a space or a backslash.
- SLD/SE: a selector with `in` is written as an `ogc:Or` of `ogc:PropertyIsEqualTo` (Filter Encoding 1.1 has no `IN`).
- SLD/SE: an image given by `path` is written as a relative `xlink:href` (as in the Annex B example) instead of failing; `se:Format` is taken from `type` or the file extension, and a scheme-less `xlink:href` is read back as `path` (#158).
- SLD/SE: sizes keep their unit. `mm`, `cm`, `in` and `pt` are converted to pixels at 0.28 mm per pixel (the CartoSym default) and `uom` is written as `pixel`; `m` and `ft` are written with `uom` `metre` / `foot`; a symbolizer that mixes ground and pixel sizes, or an `em` / `pc` size, raises a clear error. A symbolizer's `uom` is read back (#160).
- SLD/SE: a conditional expression (`cond ? a : b`) in a symbolizer is written as one rule per branch, filtered by the condition and its negation (SE has no conditional in a parameter value); a condition used twice splits once, a chain gives one rule more than its conditions, and a condition on the scale becomes a scale range. More than 16 rules raises an error (#159).

## [0.6.2] - 2026-11-03

### Fixed

- CQL2: a double-quoted word compared with a system identifier (`dataLayer.type = "coverage"`) is read as a property reference, not an enumeration value or a string, and is written back with its double quotes.

## [0.6.1] - 2026-10-21

### Fixed

- CartoSym-CSS: a coverage's colour channels set one at a time (`colorChannels.r: B04 / 2500;`, as in the specification's Sentinel-2 example) are read as the `{alter, r, g, b}` colour object instead of being dropped, and written back one line per channel instead of a Python dict.
- CQL2: an array that is a function argument is written as an array (`A_EQUALS([1, 2, 3], [1, 2])`), not as quoted text, and a bracketed array is read as an array; CQL2-JSON → CQL2-Text → CQL2-JSON no longer turns it into a string.

## [0.6.0] - 2026-10-19

### Changed

- **Breaking** (Python API): `UnitType.PICAS` is now `UnitType.PERCENT`. `pc` is percent in CartoSym-CSS (an Image's `hotSpot`, `50 pc 50 pc`), never picas; the value `"pc"` is unchanged.

### Fixed

- CLI: a console that cannot encode a character of a message (`→` on a Windows cp1252 console) prints `?` instead of ending a successful conversion with exit code 1.
- `import pycartosym` no longer needs `lxml` (the `sld` extra): the MapLibre writer imported a helper from the SLD codec. CartoSym-CSS, CS-JSON, MapLibre and the `cql2` API work with the core dependencies; SLD/SE is registered only when `lxml` is installed.
- CartoSym-CSS: a pattern stroke (`pattern`, `patternGap`, `patternInitialGap`) is read and written back instead of being dropped; the gaps accept units (`20 px`) in CartoSym-CSS and CS-JSON, and the SLD writer takes them in pixels.
- CartoSym-CSS: inches are `inch` as the specification writes them (`2 inch` is `{"in": 2}` in CS-JSON, and is written back as `inch`); `2 in` was written but could not be read back.
- CartoSym-CSS: a graphic's `position` with units (`3 px 4 px`) is read, instead of dropping the whole marker.
- Dot pattern `distance`: the `{horizontal, vertical}` object and the `[h, v]` array are read, kept in CS-JSON and written back to CartoSym-CSS, instead of becoming text (CartoSym-CSS) or a validation error (CS-JSON).
- CQL2: an expression that is only a string literal (`'abc'`) is the string `"abc"`, not a property reference; a label's `Text { text: 'Oslo' }` is the text Oslo, not the value of a property named Oslo.

## 0.5.1 - 2026-10-19 (never tagged or published; included in 0.6.0)

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

[Unreleased]: https://github.com/maxcollombin/pycartosym/compare/v0.6.6...HEAD
[0.6.6]: https://github.com/maxcollombin/pycartosym/compare/v0.6.5...v0.6.6
[0.6.5]: https://github.com/maxcollombin/pycartosym/compare/v0.6.4...v0.6.5
[0.6.4]: https://github.com/maxcollombin/pycartosym/compare/v0.6.3...v0.6.4
[0.6.3]: https://github.com/maxcollombin/pycartosym/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/maxcollombin/pycartosym/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/maxcollombin/pycartosym/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/maxcollombin/pycartosym/compare/v0.5.0...v0.6.0
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
