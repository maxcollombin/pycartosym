"""Round-trip and forward-conversion tests for every example style.

Forward test:   examples/*.cscss  →  converter  →  compare with the golden
                tests/fixtures/expected/*.cs.json
Write-back:     golden  →  csjson_to_cscss  →  re-parse, must equal the
                forward result (nothing lost in two conversions)

Regenerate the goldens after an intentional output change:
``uv run python tests/fixtures/expected/regenerate.py``.
"""

import json
from pathlib import Path

import pytest
from jsonschema import validate as jsonschema_validate

from pycartosym.converter import Converter
from pycartosym.models.styles import Style

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / "examples"
EXPECTED_DIR = ROOT / "tests" / "fixtures" / "expected"
SCHEMA_PATH = ROOT / "src" / "pycartosym" / "schemas" / "CartoSym-JSON.schema.json"
_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

# Every example must have a committed golden (regenerate.py keeps them in sync).
_FORWARD_CASES = sorted(f.stem for f in EXAMPLES_DIR.glob("*.cscss"))


# ---------------------------------------------------------------------------
# Forward conversion:  .cscss → .cs.json  must match expected output
# ---------------------------------------------------------------------------


class TestForwardConversion:
    """Parse each input .cscss and compare JSON output with expected file."""

    def setup_method(self):
        self.converter = Converter()

    @pytest.mark.parametrize("stem", _FORWARD_CASES, ids=_FORWARD_CASES)
    def test_cscss_to_csjson_matches_expected(self, stem):
        """cscss_to_csjson(examples/<stem>.cscss) must equal the golden."""
        cscss_path = EXAMPLES_DIR / f"{stem}.cscss"
        expected_path = EXPECTED_DIR / f"{stem}.cs.json"

        result = self.converter.cscss_to_csjson(cscss_path)
        with open(expected_path, encoding="utf-8") as f:
            expected = json.load(f)

        assert result == expected, (
            f"Mismatch for {stem}.cscss vs its golden — if the output change "
            f"is intended, run tests/fixtures/expected/regenerate.py and review."
        )


# ---------------------------------------------------------------------------
# Structural round-trip:  .cs.json → .cscss → .cs.json  (re-parseable)
# ---------------------------------------------------------------------------


class TestRoundTripFidelity:
    """Full round-trip fidelity: CSCSS → JSON → CSCSS → JSON must match.

    For each input .cscss file:
    1. Forward-parse the original CSCSS to JSON (json1)
    2. Write-back the expected JSON to CSCSS
    3. Re-parse that CSCSS back to JSON (json2)
    4. Assert json1 == json2  (nothing lost in the two successive conversions)
    """

    def setup_method(self):
        self.converter = Converter()

    @pytest.mark.parametrize("stem", _FORWARD_CASES, ids=_FORWARD_CASES)
    def test_round_trip_semantic_equality(self, stem):
        """CSCSS → JSON vs CSCSS → JSON → CSCSS → JSON must be identical."""
        cscss_path = EXAMPLES_DIR / f"{stem}.cscss"
        expected_path = EXPECTED_DIR / f"{stem}.cs.json"

        # Step 1: Forward parse
        json1 = self.converter.cscss_to_csjson(cscss_path)

        # Step 2: Write-back
        cscss_wb = self.converter.csjson_to_cscss(expected_path)
        assert (
            isinstance(cscss_wb, str) and len(cscss_wb) > 0
        ), "write-back produced empty CSCSS"

        # Step 3: Re-parse
        json2 = self.converter.cscss_to_csjson(cscss_wb)

        # Step 4: Full semantic equality
        assert json1 == json2, (
            f"Round-trip mismatch for {stem}.cscss — "
            f"the write-back CSCSS re-parses differently from the original"
        )


# ---------------------------------------------------------------------------
# Targeted parsing tests — selectors, properties, expressions
# ---------------------------------------------------------------------------


class TestSelectorParsing:
    """Verify various selector patterns are parsed correctly."""

    def setup_method(self):
        self.converter = Converter()

    def test_equality_selector(self):
        cscss = "[dataLayer.id = Rivers]\n{ visibility: true; }"
        result = self.converter.cscss_to_csjson(cscss)
        sel = result["stylingRules"][0]["selector"]
        assert sel["op"] == "="
        assert sel["args"][1] == "Rivers"

    def test_not_equal_operator_is_not_valid_cscss(self):
        """CartoSym-CSS has no `!=` / `<>` operator — its grammar's
        `relationalOperator` is EQ | LT | LTEQ | GT | GTEQ | IN | NOT IN |
        IS | IS NOT | LIKE | NOT LIKE. `!=` must be a hard syntax error,
        not silently swallowed.
        """
        from pycartosym.exceptions import CartoSymSyntaxError

        with pytest.raises(CartoSymSyntaxError):
            self.converter.cscss_to_csjson("[population != 0]\n{ visibility: true; }")

    def test_less_than_selector(self):
        cscss = "[viz.sd < 50000]\n{ visibility: true; }"
        result = self.converter.cscss_to_csjson(cscss)
        sel = result["stylingRules"][0]["selector"]
        assert sel["op"] == "<"

    def test_compound_and_selector(self):
        cscss = "[a = 1 and b = 2]\n{ visibility: true; }"
        result = self.converter.cscss_to_csjson(cscss)
        sel = result["stylingRules"][0]["selector"]
        assert sel["op"] == "and"
        assert len(sel["args"]) == 2

    def test_compound_or_selector(self):
        cscss = "[a = 1 or b = 2]\n{ visibility: true; }"
        result = self.converter.cscss_to_csjson(cscss)
        sel = result["stylingRules"][0]["selector"]
        assert sel["op"] == "or"

    def test_sysid_in_selector(self):
        """dataLayer.id, viz.sd etc. should produce sysId references."""
        cscss = "[dataLayer.id = Foo]\n{ visibility: true; }"
        result = self.converter.cscss_to_csjson(cscss)
        sel = result["stylingRules"][0]["selector"]
        assert sel["args"][0] == {"sysId": "dataLayer.id"}

    def test_named_rule_selector(self):
        """A named rule like 'RuleName[selector]' should produce name + selector."""
        cscss = "Cities[dataLayer.id = Cities]\n{ visibility: true; }"
        result = self.converter.cscss_to_csjson(cscss)
        rule = result["stylingRules"][0]
        assert rule.get("name") == "Cities"
        # Named rules produce a compound selector
        assert "op" in rule["selector"]


# ---------------------------------------------------------------------------
# Targeted property tests
# ---------------------------------------------------------------------------


class TestPropertyParsing:
    """Verify symbolizer properties are parsed correctly."""

    def setup_method(self):
        self.converter = Converter()

    def test_visibility_false(self):
        result = self.converter.cscss_to_csjson("[Base]\n{ visibility: false; }")
        sym = result["stylingRules"][0]["symbolizer"]
        assert sym["visibility"] is False

    def test_visibility_true(self):
        result = self.converter.cscss_to_csjson("[Base]\n{ visibility: true; }")
        sym = result["stylingRules"][0]["symbolizer"]
        assert sym["visibility"] is True

    def test_opacity_float(self):
        result = self.converter.cscss_to_csjson("[Base]\n{ opacity: 0.5; }")
        sym = result["stylingRules"][0]["symbolizer"]
        assert sym["opacity"] == 0.5

    def test_zorder_int(self):
        result = self.converter.cscss_to_csjson("[Base]\n{ zOrder: 3; }")
        sym = result["stylingRules"][0]["symbolizer"]
        assert sym["zOrder"] == 3

    def test_fill_object(self):
        result = self.converter.cscss_to_csjson(
            "[Base]\n{ fill: {color: red; opacity: 0.8}; }"
        )
        fill = result["stylingRules"][0]["symbolizer"]["fill"]
        assert fill["color"] == "red"
        assert fill["opacity"] == 0.8

    def test_stroke_with_unit_width(self):
        result = self.converter.cscss_to_csjson(
            "[Base]\n{ stroke: {color: blue; width: 3.0 px}; }"
        )
        stroke = result["stylingRules"][0]["symbolizer"]["stroke"]
        assert stroke["color"] == "blue"
        assert stroke["width"] == {"px": 3.0}

    def test_marker_element_size_with_no_space_unit_suffix(self):
        """A graphic element's ``size: 4px`` (no space) must round-trip to
        {"px": 4.0} like the space-separated form, not leak a raw
        UnitType enum member into the dict key (regression: Marker.elements
        is typed Any, so a nested UnitValue's model_dump() override never
        actually ran — {"value": v, "unit": <enum>} reached _fix_unit_values
        with the enum instance itself, not its "px" string).
        """
        result = self.converter.cscss_to_csjson(
            "[Base]\n{ marker: { elements: [Dot {color: red; size: 4px}] }; }"
        )
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["size"] == {"px": 4.0}
        back = self.converter.style_to_cscss(Style.from_dict(result))
        assert "size: 4.0 px" in back

    def test_fill_color_hex(self):
        """Hex colors like #FF0000 should be parsed to RGB arrays."""
        result = self.converter.cscss_to_csjson("[Base]\n{ fill: {color: #FF0000}; }")
        fill = result["stylingRules"][0]["symbolizer"]["fill"]
        assert fill["color"] == [255, 0, 0]

    def test_stroke_width_system_identifier_expression(self):
        """stroke.width: viz.sd / 1000 becomes a structured arithmeticExpression.

        Not a literal string — OGC issue #115 confirmed this is spec-valid
        (RC "Symbolizer Parameter Value Expressions").
        """
        result = self.converter.cscss_to_csjson(
            "[Base]\n{ stroke.width: viz.sd / 1000; }"
        )
        stroke = result["stylingRules"][0]["symbolizer"]["stroke"]
        assert stroke["width"] == {
            "op": "/",
            "args": [{"sysId": "viz.sd"}, 1000],
        }
        jsonschema_validate(instance=result, schema=_SCHEMA)

    def test_stroke_width_nested_arithmetic_expression(self):
        result = self.converter.cscss_to_csjson(
            "[Base]\n{ stroke.width: viz.sd / 1000 + 2; }"
        )
        stroke = result["stylingRules"][0]["symbolizer"]["stroke"]
        assert stroke["width"] == {
            "op": "+",
            "args": [
                {"op": "/", "args": [{"sysId": "viz.sd"}, 1000]},
                2,
            ],
        }
        jsonschema_validate(instance=result, schema=_SCHEMA)

    def test_stroke_width_expression_round_trip(self):
        """CSCSS -> JSON -> CSCSS -> JSON must be identical for an expression width."""
        json1 = self.converter.cscss_to_csjson(
            "[Base]\n{ stroke.width: viz.sd / 1000; }"
        )
        cscss_wb = self.converter.csjson_to_cscss(json1)
        assert "viz.sd / 1000" in cscss_wb
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_nested_rules(self):
        """Nested selector blocks should produce nestedRules."""
        cscss = """\
[Base]
{
   visibility: false;
   [sub = 1]
   {
      visibility: true;
   }
}
"""
        result = self.converter.cscss_to_csjson(cscss)
        rule = result["stylingRules"][0]
        assert rule["symbolizer"]["visibility"] is False
        assert "nestedRules" in rule
        assert len(rule["nestedRules"]) == 1
        assert rule["nestedRules"][0]["symbolizer"]["visibility"] is True


# ---------------------------------------------------------------------------
# Coverage-specific tests (DEM, NDVI, Sentinel-2, etc.)
# ---------------------------------------------------------------------------


class TestCoverageProperties:
    """Verify coverage-specific properties: colorMap, channels, etc."""

    def setup_method(self):
        self.converter = Converter()

    def _find_key_in_rules(self, rules, key):
        """Recursively search for a key in any symbolizer within rules."""
        for rule in rules:
            if key in rule.get("symbolizer", {}):
                return rule["symbolizer"][key]
            nested = rule.get("nestedRules", [])
            found = self._find_key_in_rules(nested, key)
            if found is not None:
                return found
        return None

    def test_dem_has_color_map(self):
        result = self.converter.cscss_to_csjson(EXAMPLES_DIR / "5-coverage-dem.cscss")
        cm = self._find_key_in_rules(result["stylingRules"], "colorMap")
        assert cm is not None, "DEM example should have a colorMap"
        assert isinstance(cm, list), "colorMap should be an array"

    def test_sentinel2_has_channels(self):
        result = self.converter.cscss_to_csjson(
            EXAMPLES_DIR / "6-coverage-sentinel2.cscss"
        )
        ch = self._find_key_in_rules(result["stylingRules"], "colorChannels")
        assert ch is not None, "Sentinel-2 should have colorChannels"

    def test_ndvi_has_color_map(self):
        result = self.converter.cscss_to_csjson(EXAMPLES_DIR / "7-coverage-ndvi.cscss")
        cm = self._find_key_in_rules(result["stylingRules"], "colorMap")
        assert cm is not None, "NDVI example should have a colorMap"

    def test_hillshading_has_hill_shading(self):
        result = self.converter.cscss_to_csjson(
            EXAMPLES_DIR / "8-coverage-hillshading.cscss"
        )
        hs = self._find_key_in_rules(result["stylingRules"], "hillShading")
        assert hs is not None, "Hillshading example should have hillShading"


# ---------------------------------------------------------------------------
# Metadata parsing
# ---------------------------------------------------------------------------


class TestMetadataParsing:
    """Verify .title, .abstract and other directives."""

    def setup_method(self):
        self.converter = Converter()

    def test_title_and_abstract(self):
        cscss = (
            ".title 'My Style'\n.abstract 'A description'\n"
            "[Base]\n{ visibility: true; }"
        )
        result = self.converter.cscss_to_csjson(cscss)
        meta = result.get("metadata", {})
        assert meta.get("title") == "My Style"
        assert meta.get("abstract") == "A description"

    def test_metadata_from_example3(self):
        result = self.converter.cscss_to_csjson(EXAMPLES_DIR / "3-vector-line.cscss")
        meta = result.get("metadata", {})
        assert meta.get("title") == "Styling line vector features"
        assert "abstract" in meta

    def test_geo_data_classes_roundtrip(self):
        """.geoDataClasses must survive CSCSS → CS-JSON → CSCSS write-back
        (regression: the writer read a wrong attribute name and dropped it).
        """
        cscss = (
            ".title 'T'\n"
            ".geoDataClasses 'https://ex.org/a, https://ex.org/b'\n"
            "[Base]\n{ visibility: true; }"
        )
        result = self.converter.cscss_to_csjson(cscss)
        assert result["metadata"]["geoDataClasses"] == [
            "https://ex.org/a",
            "https://ex.org/b",
        ]
        back = self.converter.style_to_cscss(Style.from_dict(result))
        assert ".geoDataClasses 'https://ex.org/a, https://ex.org/b'" in back

    def test_include_directive_writeback(self):
        """A CS-JSON-authored $include must reach CSCSS write-back.

        ``.include`` is resolved (file content inlined) by the CSCSS
        *reader*'s own preprocessor, so it never round-trips through a
        CSCSS source — but a directly-authored CS-JSON document's
        ``$include`` is a real ``Style`` field regardless (regression:
        style_to_cscss never read it at all).
        """
        style = Style.from_dict(
            {
                "$include": "other.cscss",
                "stylingRules": [{"symbolizer": {"visibility": True}}],
            }
        )
        back = self.converter.style_to_cscss(style)
        assert ".include 'other.cscss'" in back

    def test_variable_declaration_roundtrip(self):
        """@var = value; must survive CSCSS -> CS-JSON -> CSCSS write-back
        (regression: style_to_cscss never read style.variables at all).
        """
        cscss = "@roadColor = gray;\n[Base]\n{ stroke: { color: @roadColor }; }"
        result = self.converter.cscss_to_csjson(cscss)
        assert result["$variables"] == [{"name": "roadColor", "value": "gray"}]
        back = self.converter.style_to_cscss(Style.from_dict(result))
        assert "@roadColor = 'gray';" in back
        # And it re-parses back to the same $variables.
        assert self.converter.cscss_to_csjson(back)["$variables"] == [
            {"name": "roadColor", "value": "gray"}
        ]

    def _fill_pattern_roundtrip(self, fill_dict):
        style = Style.from_dict({"stylingRules": [{"symbolizer": {"fill": fill_dict}}]})
        css = self.converter.style_to_cscss(style)
        back = self.converter.cscss_to_csjson(css)
        return css, back["stylingRules"][0]["symbolizer"]["fill"]

    def test_fill_hatch_writeback_roundtrips(self):
        """fill.hatch survives CS-JSON -> CartoSym-CSS -> CS-JSON."""
        css, fill = self._fill_pattern_roundtrip(
            {
                "color": [255, 0, 0],
                "hatch": {
                    "width": {"px": 2.0},
                    "angle": 45,
                    "distance": {"px": 5.0},
                },
            }
        )
        assert "hatch:" in css
        assert fill["hatch"] == {
            "width": {"px": 2.0},
            "angle": 45.0,
            "distance": {"px": 5.0},
        }

    def test_fill_dotpattern_writeback_roundtrips(self):
        """fill.dotpattern survives CS-JSON -> CartoSym-CSS -> CS-JSON."""
        css, fill = self._fill_pattern_roundtrip(
            {"dotpattern": {"distance": {"px": 3.0}}}
        )
        assert "dotpattern:" in css
        assert fill["dotpattern"] == {"distance": {"px": 3.0}}

    def test_fill_stipple_writeback_roundtrips(self):
        """fill.stipple survives CS-JSON -> CartoSym-CSS -> CS-JSON."""
        css, fill = self._fill_pattern_roundtrip({"stipple": {"ratio": 0.5}})
        assert "stipple:" in css
        assert fill["stipple"] == {"ratio": 0.5}

    def test_fill_pattern_graphic_writeback_roundtrips(self):
        """fill.pattern (a full graphic, e.g. Dot) survives the round trip."""
        css, fill = self._fill_pattern_roundtrip(
            {"pattern": {"type": "Dot", "size": {"px": 4.0}, "color": [1, 2, 3]}}
        )
        assert "pattern:" in css
        assert fill["pattern"] == {
            "type": "Dot",
            "size": {"px": 4.0},
            "color": "#010203",
        }

    def test_fill_pattern_alter_mode_still_raises(self):
        """A pattern field has no ``fill.hatch: ...`` dot-notation syntax —
        combined with ``alter`` the writer must still raise rather than
        drop it silently.
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "fill": {
                                "alter": True,
                                "color": [255, 0, 0],
                                "hatch": {"angle": 45},
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="fill.hatch"):
            self.converter.style_to_cscss(style)

    def test_plain_fill_still_writes_back(self):
        """Regression guard for the pattern check: a plain fill is unaffected."""
        style = Style.from_dict(
            {"stylingRules": [{"symbolizer": {"fill": {"color": [255, 0, 0]}}}]}
        )
        assert "fill:" in self.converter.style_to_cscss(style)

    def test_stroke_dash_pattern_writeback_raises(self):
        """A dash pattern has no CartoSym-CSS grammar syntax yet — the
        writer must raise (naming the field) rather than drop it silently.
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "stroke": {"color": [0, 0, 0], "dashPattern": [4, 2]}
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="stroke.dashPattern"):
            self.converter.style_to_cscss(style)

    def test_stroke_center_line_writeback_raises(self):
        """Same guard for centerLine — regression check that the alias
        (Python attr ``center_line``, JSON key ``centerLine``) is actually
        read, not silently always-None.
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "stroke": {
                                "color": [0, 0, 0],
                                "centerLine": {"color": [255, 255, 255]},
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="stroke.centerLine"):
            self.converter.style_to_cscss(style)

    def test_plain_stroke_still_writes_back(self):
        """Regression guard for the extended-field check: a plain stroke
        (color/width/opacity only) is unaffected.
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {"symbolizer": {"stroke": {"color": [0, 0, 0], "width": {"px": 2}}}}
                ]
            }
        )
        assert "stroke:" in self.converter.style_to_cscss(style)

    def _text_element_style(self, *, opacity, font):
        return Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "label": {
                                "elements": [
                                    {
                                        "type": "Text",
                                        "text": "Hello",
                                        "opacity": opacity,
                                        "font": font,
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        )

    def test_element_opacity_survives_alongside_font(self):
        """A Text element's own opacity must not be dropped just because a
        font block is also present (regression: the writer suppressed
        opacity whenever any font: line existed, not only when the font
        itself carried a conflicting opacity key).
        """
        style = self._text_element_style(
            opacity=0.5, font={"face": "Arial", "size": 12}
        )
        back = self.converter.style_to_cscss(style)
        assert "opacity: 0.5" in back
        assert "font:" in back

    def test_font_own_opacity_still_suppresses_element_opacity(self):
        """Regression guard: when the font block itself carries its own
        opacity key, the element-level opacity stays suppressed (as
        before) rather than emitting a confusing duplicate.
        """
        style = self._text_element_style(
            opacity=0.5, font={"face": "Arial", "size": 12, "opacity": 0.9}
        )
        back = self.converter.style_to_cscss(style)
        assert "opacity: 0.9" in back
        assert "opacity: 0.5" not in back

    def test_marker_position_writeback_raises(self):
        """marker.position has no CartoSym-CSS grammar syntax — regression
        guard against silently dropping it (the AST's own Marker dataclass
        doesn't even carry the field, confirmed no read-side counterpart).
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "marker": {
                                "position": {"x": 1, "y": 2},
                                "elements": [{"type": "Dot", "size": {"px": 4}}],
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="marker.position"):
            self.converter.style_to_cscss(style)

    def test_marker_opacity_writeback_raises(self):
        """Same guard for marker.opacity."""
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "marker": {
                                "opacity": 0.5,
                                "elements": [{"type": "Dot", "size": {"px": 4}}],
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="marker.opacity"):
            self.converter.style_to_cscss(style)

    def test_plain_marker_still_writes_back(self):
        """Regression guard: a plain marker (elements only) is unaffected."""
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "marker": {"elements": [{"type": "Dot", "size": {"px": 4}}]}
                        }
                    }
                ]
            }
        )
        assert "marker:" in self.converter.style_to_cscss(style)

    def test_label_position_writeback_raises(self):
        """label.position has no CartoSym-CSS grammar syntax — confirmed
        empirically (real CSCSS text with it silently drops both fields
        on read, rather than populating them).
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "label": {
                                "position": {"x": 1, "y": 2},
                                "elements": [{"type": "Text", "text": "hi"}],
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="label.position"):
            self.converter.style_to_cscss(style)

    def test_label_opacity_writeback_raises(self):
        """Same guard for label.opacity."""
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "label": {
                                "opacity": 0.5,
                                "elements": [{"type": "Text", "text": "hi"}],
                            }
                        }
                    }
                ]
            }
        )
        with pytest.raises(NotImplementedError, match="label.opacity"):
            self.converter.style_to_cscss(style)

    def test_placement_type_writes_back(self):
        """LabelPlacement.placement_type ("type") reaches real CartoSym-CSS
        syntax (confirmed empirically it round-trips) — regression: it was
        never written even though minSpacing/maxSpacing already were.
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "label": {
                                "elements": [{"type": "Text", "text": "hi"}],
                                "placement": {
                                    "type": "simple",
                                    "minSpacing": {"px": 2},
                                },
                            }
                        }
                    }
                ]
            }
        )
        back = self.converter.style_to_cscss(style)
        assert "type: simple" in back
        assert "minSpacing: 2.0 px" in back

    def test_graphic_element_alter_writes_back(self):
        """A graphic element's own ``alter`` (AlterMixin) must survive
        CS-JSON -> CartoSym-CSS write-back (regression:
        _graphic_element_to_css_block never read it at all).
        """
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "symbolizer": {
                            "marker": {
                                "elements": [
                                    {"type": "Dot", "alter": True, "color": "red"}
                                ]
                            }
                        }
                    }
                ]
            }
        )
        back = self.converter.style_to_cscss(style)
        assert "alter: true" in back

    def test_graphic_element_alter_roundtrips_through_cscss(self):
        """Full CSCSS -> JSON -> CSCSS -> JSON round trip for element alter."""
        cscss = (
            "[Base]\n{\n"
            "  marker: { elements: [Dot {alter: true; color: red; size: 4 px}] };\n"
            "}"
        )
        json1 = self.converter.cscss_to_csjson(cscss)
        back = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(back)
        assert json1 == json2
        el = json1["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["alter"] is True


# ---------------------------------------------------------------------------
# Font and graphic element normalization (ast_converter)
# ---------------------------------------------------------------------------


class TestFontNormalization:
    """Verify font dict values are coerced to proper types."""

    def setup_method(self):
        from pycartosym.ast_converter import _coerce_font_dict

        self.coerce = _coerce_font_dict

    def test_size_string_to_int(self):
        font = {"size": "12"}
        self.coerce(font)
        assert font["size"] == 12
        assert isinstance(font["size"], int)

    def test_size_float_string(self):
        font = {"size": "12.5"}
        self.coerce(font)
        assert font["size"] == 12.5
        assert isinstance(font["size"], float)

    def test_bold_string_to_bool(self):
        font = {"bold": "true", "italic": "false"}
        self.coerce(font)
        assert font["bold"] is True
        assert font["italic"] is False

    def test_opacity_string_to_float(self):
        font = {"opacity": "0.75"}
        self.coerce(font)
        assert font["opacity"] == 0.75

    def test_color_preserved(self):
        font = {"color": "darkGray"}
        self.coerce(font)
        assert font["color"] == "darkGray"

    def test_outline_string_coerced(self):
        font = {"outline": "{ size: 3; opacity: 0.75; color: white }"}
        self.coerce(font)
        outline = font["outline"]
        assert isinstance(outline, dict)
        assert outline["size"] == 3
        assert outline["opacity"] == 0.75
        assert outline["color"] == "white"

    def test_size_with_unit_suffix_becomes_unit_dict(self):
        """``size: 12 px`` — previously left as an uncoerced raw string."""
        font = {"size": "12 px"}
        self.coerce(font)
        assert font["size"] == {"px": 12}

    def test_already_coerced_values_untouched(self):
        """Values that are already the right type should not be altered."""
        font = {"size": 14, "bold": True, "opacity": 1.0}
        self.coerce(font)
        assert font["size"] == 14
        assert font["bold"] is True
        assert font["opacity"] == 1.0


class TestFontSizeExpression:
    """``Font.size`` accepts a numeric expression through the full CSCSS pipeline."""

    def setup_method(self):
        self.converter = Converter()

    def test_font_size_accepts_numeric_expression(self):
        css = (
            "Amenities {\n"
            "  label: { elements: [\n"
            "    Text { text: NAME; font: { size: viz.sd / 1000 } }\n"
            "  ]};\n"
            "}\n"
        )
        result = self.converter.cscss_to_csjson(css)
        el = result["stylingRules"][0]["symbolizer"]["label"]["elements"][0]
        assert el["font"]["size"] == {"op": "/", "args": [{"sysId": "viz.sd"}, 1000]}

    def test_font_size_expression_round_trips_through_csjson(self):
        css = (
            "Amenities {\n"
            "  label: { elements: [\n"
            "    Text { text: NAME; font: { size: viz.sd / 1000 } }\n"
            "  ]};\n"
            "}\n"
        )
        json1 = self.converter.cscss_to_csjson(css)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2


class TestAstConverterLoggingNotPrint:
    """AstToPydanticConverter's per-field except-blocks must use logging,
    not print() (CLAUDE.md: "Do not use print() for logging"). A failure
    converting one field (e.g. a malformed opacity) is swallowed and the
    field dropped either way — this only pins down *how* it's reported.
    """

    def test_fill_conversion_failure_logs_a_warning_not_a_print(self, caplog, capsys):
        from pycartosym.ast import Fill as AstFill
        from pycartosym.ast_converter import AstToPydanticConverter

        converter = AstToPydanticConverter()
        bad_fill = AstFill(opacity="not-a-number")

        with caplog.at_level("WARNING", logger="pycartosym.ast_converter"):
            result = converter._convert_fill(bad_fill)

        assert result is None
        assert any("Failed to convert fill" in rec.message for rec in caplog.records)
        assert capsys.readouterr().out == ""


class TestGraphicElementNormalization:
    """Verify _normalize_graphic_element handles text and alignment."""

    def setup_method(self):
        from pycartosym.ast_converter import _normalize_graphic_element

        self.normalize = _normalize_graphic_element

    def test_text_bare_identifier_becomes_property_ref(self):
        el = {"type": "Text", "text": "NAME"}
        self.normalize(el)
        assert el["text"] == {"property": "NAME"}

    def test_text_quoted_string_stays_literal(self):
        el = {"type": "Text", "text": "'Hello World'"}
        self.normalize(el)
        assert el["text"] == "Hello World"

    def test_alignment_space_separated(self):
        el = {"type": "Text", "text": "'X'", "alignment": "left middle"}
        self.normalize(el)
        assert el["alignment"] == ["left", "middle"]

    def test_alignment_braces_syntax(self):
        el = {"type": "Text", "text": "'X'", "alignment": "{ center, top }"}
        self.normalize(el)
        assert el["alignment"] == ["center", "top"]

    def test_opacity_string_to_float(self):
        el = {"type": "Dot", "opacity": "0.5"}
        self.normalize(el)
        assert el["opacity"] == 0.5

    def test_alter_string_to_bool(self):
        el = {"type": "Dot", "alter": "true"}
        self.normalize(el)
        assert el["alter"] is True

    def test_font_dict_coerced(self):
        el = {"type": "Text", "text": "'X'", "font": {"size": "10", "bold": "true"}}
        self.normalize(el)
        assert el["font"]["size"] == 10
        assert el["font"]["bold"] is True

    def test_circle_fill_outline_radius_coerced(self):
        el = {
            "type": "Circle",
            "fill": {"color": "#ffffff", "opacity": "0.5"},
            "outline": {"color": "#0000ff", "thickness": "2 px", "opacity": "0.7"},
            "radius": "5 px",
        }
        self.normalize(el)
        assert el["fill"] == {"color": [255, 255, 255], "opacity": 0.5}
        assert el["outline"] == {
            "color": [0, 0, 255],
            "thickness": {"px": 2},
            "opacity": 0.7,
        }
        assert el["radius"] == {"px": 5}

    def test_circle_unitless_radius_stays_bare_number(self):
        el = {"type": "Circle", "radius": "4"}
        self.normalize(el)
        assert el["radius"] == 4

    def test_rectangle_width_height_coerced(self):
        """Previously left as uncoerced raw strings ("5 px"), a schema-invalid shape."""
        el = {"type": "Rectangle", "width": "5 px", "height": "3"}
        self.normalize(el)
        assert el["width"] == {"px": 5}
        assert el["height"] == 3


class TestCircleGraphic:
    """CartoSym-CSS ``Circle { fill; outline; radius }`` (2-shapes shape graphic)."""

    def setup_method(self):
        self.converter = Converter()

    _CSCSS = (
        "Amenities {\n"
        "  marker: { elements: [\n"
        "    Circle {\n"
        "      fill: { color: #ffffff; opacity: 0.5 };\n"
        "      outline: { color: #0000ff; thickness: 2 px; opacity: 0.7 };\n"
        "      radius: 5 px;\n"
        "    }\n"
        "  ]};\n"
        "}\n"
    )

    def test_cscss_circle_parses_to_shapes_circle(self):
        result = self.converter.cscss_to_csjson(self._CSCSS)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["type"] == "Circle"
        assert el["fill"] == {"color": [255, 255, 255], "opacity": 0.5}
        assert el["outline"] == {
            "color": [0, 0, 255],
            "thickness": {"px": 2},
            "opacity": 0.7,
        }
        assert el["radius"] == {"px": 5}

    def test_cscss_circle_round_trips_through_csjson(self):
        json1 = self.converter.cscss_to_csjson(self._CSCSS)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_dot_is_not_promoted_to_circle(self):
        result = self.converter.cscss_to_csjson(
            "Base {\n  marker: { elements: [ Dot { size: 8 px; color: white } ] };\n}\n"
        )
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["type"] == "Dot"
        assert "fill" not in el and "outline" not in el and "radius" not in el

    def test_radius_and_outline_thickness_accept_numeric_expression(self):
        """``viz.sd / 1000`` — OGC issue #115, generalized beyond stroke.width."""
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Circle {\n"
            "      outline: { thickness: viz.sd / 2000 };\n"
            "      radius: viz.sd / 1000;\n"
            "    }\n"
            "  ]};\n"
            "}\n"
        )
        result = self.converter.cscss_to_csjson(css)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["radius"] == {
            "op": "/",
            "args": [{"sysId": "viz.sd"}, 1000],
        }
        assert el["outline"]["thickness"] == {
            "op": "/",
            "args": [{"sysId": "viz.sd"}, 2000],
        }

    def test_radius_expression_round_trips_through_csjson(self):
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Circle { radius: viz.sd / 1000 }\n"
            "  ]};\n"
            "}\n"
        )
        json1 = self.converter.cscss_to_csjson(css)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2


class TestRectangleGraphic:
    """CartoSym-CSS ``Rectangle { width; height }`` (2-shapes shape graphic)."""

    def setup_method(self):
        self.converter = Converter()

    _CSCSS = (
        "Amenities {\n"
        "  marker: { elements: [\n"
        "    Rectangle { width: 5 px; height: 3 px }\n"
        "  ]};\n"
        "}\n"
    )

    def test_cscss_rectangle_width_height_coerced(self):
        """Regression: previously left as uncoerced raw strings ("5 px")."""
        result = self.converter.cscss_to_csjson(self._CSCSS)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["type"] == "Rectangle"
        assert el["width"] == {"px": 5}
        assert el["height"] == {"px": 3}

    def test_cscss_rectangle_round_trips_through_csjson(self):
        json1 = self.converter.cscss_to_csjson(self._CSCSS)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_rectangle_width_accepts_numeric_expression(self):
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Rectangle { width: viz.sd / 1000; height: 3 px }\n"
            "  ]};\n"
            "}\n"
        )
        result = self.converter.cscss_to_csjson(css)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["width"] == {"op": "/", "args": [{"sysId": "viz.sd"}, 1000]}


class TestUnitPointPropertyReference:
    """``UnitPoint.x``/``.y`` (``position``/``center``) accept a bare
    property-name identifier as one coordinate — e.g. ``position: sd 3``.

    No arithmetic/system-identifier support here: the CSCSS grammar treats
    a ``UnitPoint``'s two coordinates as one opaque two-token text blob,
    not two independent expression trees (see
    ``models/symbolizers.py::_coerce_axis_value``).
    """

    def setup_method(self):
        self.converter = Converter()

    def test_image_position_x_as_property_reference(self):
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Image { position: sd 3 }\n"
            "  ]};\n"
            "}\n"
        )
        result = self.converter.cscss_to_csjson(css)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["position"] == {"x": {"property": "sd"}, "y": 3.0}

    def test_image_position_round_trips_through_csjson(self):
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Image { position: sd 3 }\n"
            "  ]};\n"
            "}\n"
        )
        json1 = self.converter.cscss_to_csjson(css)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_circle_center_y_as_property_reference(self):
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Circle { center: 5 sd; radius: 2 px }\n"
            "  ]};\n"
            "}\n"
        )
        result = self.converter.cscss_to_csjson(css)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["center"] == {"x": 5, "y": {"property": "sd"}}

    def test_circle_center_round_trips_through_csjson(self):
        css = (
            "Amenities {\n"
            "  marker: { elements: [\n"
            "    Circle { center: 5 sd; radius: 2 px }\n"
            "  ]};\n"
            "}\n"
        )
        json1 = self.converter.cscss_to_csjson(css)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2


class TestLabelPlacementSpacing:
    """``label: { placement: { minSpacing; maxSpacing; priority } }`` —
    previously unwired in CSCSS at all (``ast.py``'s dead ``hasattr(ast_label,
    "placement")`` check in ``ast_converter.py`` had nothing to read),
    not merely narrowly typed. Also accepts a numeric expression, unlike
    ``UnitPoint`` — ``placement``'s properties each keep their own ANTLR
    expression context, the same way a shape element's do.
    """

    def setup_method(self):
        self.converter = Converter()

    def test_min_max_spacing_coerced_to_unit_values(self):
        css = (
            "Amenities {\n"
            "  label: { elements: [ Text{ text: NAME } ];\n"
            "    placement: { minSpacing: 5 px; maxSpacing: 20 px } };\n"
            "}\n"
        )
        result = self.converter.cscss_to_csjson(css)
        placement = result["stylingRules"][0]["symbolizer"]["label"]["placement"]
        assert placement == {"minSpacing": {"px": 5}, "maxSpacing": {"px": 20}}

    def test_placement_alone_without_elements_is_preserved(self):
        """Regression: the writer used to drop the whole ``label`` block
        when it had no ``elements`` (checked emptiness before placement
        existed).
        """
        css = "Amenities {\n  label: { placement: { minSpacing: 5 px } };\n}\n"
        json1 = self.converter.cscss_to_csjson(css)
        placement = json1["stylingRules"][0]["symbolizer"]["label"]["placement"]
        assert placement == {"minSpacing": {"px": 5}}
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_min_spacing_accepts_numeric_expression(self):
        css = "Amenities {\n  label: { placement: { minSpacing: viz.sd / 1000 } };\n}\n"
        result = self.converter.cscss_to_csjson(css)
        placement = result["stylingRules"][0]["symbolizer"]["label"]["placement"]
        assert placement["minSpacing"] == {
            "op": "/",
            "args": [{"sysId": "viz.sd"}, 1000],
        }

    def test_min_spacing_expression_round_trips_through_csjson(self):
        css = "Amenities {\n  label: { placement: { minSpacing: viz.sd / 1000 } };\n}\n"
        json1 = self.converter.cscss_to_csjson(css)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_priority_literal_round_trips(self):
        """``priority`` used to be typed ``cql2.model.NumericExpression``, an
        abstract base with no bare-literal variant — a plain ``priority: 5``
        raised ``pydantic.ValidationError`` before it ever reached the
        writer. Now ``FlexibleNumber`` (like ``minSpacing``/``maxSpacing``'s
        ``FlexibleSize``), so a literal round-trips like any other field.
        """
        css = "Amenities {\n  label: { placement: { priority: 5 } };\n}\n"
        json1 = self.converter.cscss_to_csjson(css)
        placement = json1["stylingRules"][0]["symbolizer"]["label"]["placement"]
        assert placement == {"priority": 5.0}
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2

    def test_priority_accepts_numeric_expression(self):
        css = "Amenities {\n  label: { placement: { priority: viz.sd / 1000 } };\n}\n"
        result = self.converter.cscss_to_csjson(css)
        placement = result["stylingRules"][0]["symbolizer"]["label"]["placement"]
        assert placement["priority"] == {
            "op": "/",
            "args": [{"sysId": "viz.sd"}, 1000],
        }

    def test_priority_expression_round_trips_through_csjson(self):
        css = "Amenities {\n  label: { placement: { priority: viz.sd / 1000 } };\n}\n"
        json1 = self.converter.cscss_to_csjson(css)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2


class TestResourceSprite:
    """``resource.sprite`` (icon atlas id) round-trips alongside uri/path/etc."""

    def setup_method(self):
        self.converter = Converter()

    _CSCSS = (
        "Amenities {\n"
        "  marker: { elements: [\n"
        "    Image { image: { uri: 'icons.png'; sprite: 'pin-15' } }\n"
        "  ]};\n"
        "}\n"
    )

    def test_sprite_parses(self):
        result = self.converter.cscss_to_csjson(self._CSCSS)
        el = result["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
        assert el["image"] == {"uri": "icons.png", "sprite": "pin-15"}

    def test_sprite_round_trips_through_csjson(self):
        json1 = self.converter.cscss_to_csjson(self._CSCSS)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2


class TestArcGraphics:
    """CartoSym-CSS ``Arc``/``SectorArc``/``ChordArc`` (2-shapes ``abstractArc``)."""

    def setup_method(self):
        self.converter = Converter()

    _CSCSS = (
        "Amenities {\n"
        "  marker: { elements: [\n"
        "    Arc {\n"
        "      outline: { color: #000000; thickness: 2 px; opacity: 1.0 };\n"
        "      radius: 5 px;\n"
        "      center: 0 0;\n"
        "      startAngle: 45;\n"
        "      deltaAngle: 90;\n"
        "    },\n"
        "    SectorArc {\n"
        "      fill: { color: #ff0000; opacity: 0.6 };\n"
        "      radius: 8 px;\n"
        "      startAngle: 0;\n"
        "      deltaAngle: 180;\n"
        "    },\n"
        "    ChordArc {\n"
        "      fill: { color: #00ff00; opacity: 0.4 };\n"
        "      radius: 6 px;\n"
        "      startAngle: 30 deg;\n"
        "      deltaAngle: 60 deg;\n"
        "    }\n"
        "  ]};\n"
        "}\n"
    )

    def test_arc_family_parses(self):
        result = self.converter.cscss_to_csjson(self._CSCSS)
        elements = result["stylingRules"][0]["symbolizer"]["marker"]["elements"]
        arc, sector, chord = elements
        assert arc["type"] == "Arc"
        assert arc["startAngle"] == 45
        assert arc["deltaAngle"] == 90
        assert "fill" not in arc  # an open arc has no fill
        assert sector["type"] == "SectorArc"
        assert sector["fill"] == {"color": [255, 0, 0], "opacity": 0.6}
        assert chord["type"] == "ChordArc"
        assert chord["startAngle"] == {"deg": 30}
        assert chord["deltaAngle"] == {"deg": 60}

    def test_arc_family_validates_against_schema(self):
        result = self.converter.cscss_to_csjson(self._CSCSS)
        jsonschema_validate(instance=result, schema=_SCHEMA)

    def test_arc_family_round_trips_through_csjson(self):
        json1 = self.converter.cscss_to_csjson(self._CSCSS)
        cscss_wb = self.converter.csjson_to_cscss(json1)
        json2 = self.converter.cscss_to_csjson(cscss_wb)
        assert json1 == json2


# ---------------------------------------------------------------------------
# Color parsing (ast_converter)
# ---------------------------------------------------------------------------


class TestColorParsing:
    """Verify _parse_color_value handles various formats."""

    def setup_method(self):
        from pycartosym.ast_converter import _parse_color_value

        self.parse = _parse_color_value

    def test_named_color(self):
        assert self.parse("red") == "red"

    def test_hex_color_6_digits(self):
        assert self.parse("#FF0000") == [255, 0, 0]

    def test_hex_color_lowercase(self):
        assert self.parse("#00ff00") == [0, 255, 0]

    def test_hex_color_8_digits_passthrough(self):
        """8-digit hex colors are not yet parsed — returned as-is."""
        result = self.parse("#FF000080")
        assert result == "#FF000080"

    def test_hex_color_3_digits(self):
        result = self.parse("#F00")
        assert result == [255, 0, 0]


# ---------------------------------------------------------------------------
# Variable resolution
# ---------------------------------------------------------------------------


class TestVariableResolution:
    """Verify that @variable references are resolved during parsing."""

    def setup_method(self):
        self.converter = Converter()

    def test_variable_substitution_in_fill(self, tmp_path):
        """Variables are resolved during file pre-processing."""
        f = tmp_path / "vars.cscss"
        f.write_text(
            "@baseColor = #336699;\n\nLanduse\n{\n   fill: {color: @baseColor};\n}\n"
        )
        result = self.converter.cscss_to_csjson(f)
        fill = result["stylingRules"][0]["symbolizer"]["fill"]
        # Variable should be resolved to the hex color
        assert fill["color"] == [51, 102, 153]

    def test_variable_substitution_numeric(self, tmp_path):
        f = tmp_path / "vars.cscss"
        f.write_text(
            "@baseOpacity = 0.7;\n\nLanduse\n{\n   opacity: @baseOpacity;\n}\n"
        )
        result = self.converter.cscss_to_csjson(f)
        sym = result["stylingRules"][0]["symbolizer"]
        assert sym["opacity"] == 0.7
