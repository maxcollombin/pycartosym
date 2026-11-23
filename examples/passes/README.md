# Rendering passes, overriding and stacked strokes

CartoSym-CSS cases for the interactions of nested rules, `feature.pass`,
`viz.pass`, casing and `zOrder`, as discussed in
[opengeospatial/cartographic-symbology#197](https://github.com/opengeospatial/cartographic-symbology/issues/197)
and [#212](https://github.com/opengeospatial/cartographic-symbology/issues/212).
Each case has its CartoSym-CSS (`.cscss`) and CS-JSON (`.cs.json`), and the
SLD/SE (`.sld`) and MapLibre (`.maplibre.json`) that pycartosym writes from it,
when it can. They show what the two target formats do with each case; they are
not renders. MapLibre needs a layer id: the writer uses the name of the rule or its data layer (`Roads`), and numbers the rules that come from a nested rule (`Roads-1`...); a rule with neither, such as `[kind = 'road']`, is refused.

Each top-level rule has `marker: null;`: without it the default Dot is drawn on
every feature (`/req/core/default-values`, opengeospatial/cartographic-symbology#207).

Meaning, as settled in #197: a nested rule without a selector is the same as
removing its curly brackets, so several of them override one another, as do
top-level rules with the same selector. Stacked drawing layers are written with
`feature.pass` (one feature complete before the next), `viz.pass` (all features
per pass) or the built-in `casing`.

| Case | Meaning | SLD/SE | MapLibre |
|---|---|---|---|
| `01-nested-override` | Only the white stroke remains | One `se:Rule`, white stroke | Error: a rule with no name or data layer has no layer id |
| `02-toplevel-override` | The same as 01 | **Two `se:Rule`: both are drawn, black then white** | Error: a rule with no name or data layer has no layer id |
| `03-feature-pass` | Per feature: black stroke, then white | One `se:Rule` with two `se:LineSymbolizer`, in pass order | Error: `feature.pass` has no mapping (a layer draws all its features) |
| `04-viz-pass` | All black strokes, then all white strokes | Two `se:FeatureTypeStyle`, in pass order | Two layers on the same source, in pass order |
| `05-casing` | Built-in casing | Error: `Stroke.casing` has no mapping | Error: `stroke.casing` has no mapping |
| `06-rule-without-pass` | A background rule next to rules with a `viz.pass`: it applies in pass 0 only (#198) | The rule without a pass is in the first `se:FeatureTypeStyle` (pass 0), then one per `viz.pass` | Layers in pass order: the rule without a pass first (pass 0), then one per `viz.pass` |
| `07-feature-and-viz-pass` | Both identifiers | Two `se:FeatureTypeStyle`, the first with a `se:Rule` of two symbolizers | Error: `feature.pass` has no mapping |
| `08-zorder` | Rails drawn above roads | Two `se:FeatureTypeStyle` in document order; `zOrder` is not written | Two layers in document order; `zOrder` is not written |

Known gaps shown here: overlapping top-level rules that override one another
(02) are written as independent rules that all draw, which differs from the
CartoSym meaning; `zOrder` and casing have no mapping.
