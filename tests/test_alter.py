"""Tests for the 'alter' flag on dot-notation and indexed element overrides."""

from pathlib import Path

from pycartosym.models.types import UnitType, UnitValue
from pycartosym.parser import CartoSymParser

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


class TestAlterFlag:
    """Dot-notation properties should produce ``alter: true`` on the
    parent sub-object.
    """

    def setup_method(self):
        self.parser = CartoSymParser()

    # ── fill.color in a nested rule ────────────────────────────────

    def test_fill_dot_color_sets_alter(self):
        """fill.color: darkGray  →  fill: { alter: true, color: 'darkGray' }"""
        cscss = """\
[Base]
{
   fill: {color: gray; opacity: 0.5};

   [FunctionCode = 'parking']
   {
      fill.color: darkGray;
   }
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        # The nested rule's symbolizer should have fill.alter == True
        nested = style.styling_rules[0].nested_rules[0]
        sym = nested.symbolizer
        assert sym.fill is not None, "fill should be set"
        assert sym.fill.alter is True, "fill.color in nested rule must set alter=True"
        assert sym.fill.color == "darkGray"

    # ── stroke.color in a nested rule ──────────────────────────────

    def test_stroke_dot_color_sets_alter(self):
        """stroke.color: #202020  →  stroke: { alter: true, color: [32,32,32] }"""
        cscss = """\
[Base]
{
   stroke: {color: gray; width: 2.0 px; opacity: 1.0};

   [FunctionCode = 'parking']
   {
      stroke.color: #202020;
   }
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        nested = style.styling_rules[0].nested_rules[0]
        sym = nested.symbolizer
        assert sym.stroke is not None, "stroke should be set"
        assert (
            sym.stroke.alter is True
        ), "stroke.color in nested rule must set alter=True"

    # ── stroke.width in a nested rule ──────────────────────────────

    def test_stroke_dot_width_sets_alter(self):
        """stroke.width: 4.0 px  →  stroke: { alter: true, width: {px: 4.0} }"""
        cscss = """\
[Base]
{
   stroke: {color: gray; width: 2.0 px};

   [viz.sd < 10000]
   {
      stroke.width: 4.0 px;
   }
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        nested = style.styling_rules[0].nested_rules[0]
        sym = nested.symbolizer
        assert sym.stroke is not None, "stroke should be set"
        assert (
            sym.stroke.alter is True
        ), "stroke.width in nested rule must set alter=True"
        assert sym.stroke.width == UnitValue(value=4.0, unit=UnitType.PIXELS), (
            "stroke.width override must parse the unit suffix, not stay the "
            "bare string '4.0 px'"
        )

    def test_stroke_dot_width_non_px_unit_parses_too(self):
        """stroke.width: 8.0 m must parse to a UnitValue, same as any px override.

        Regression test: the dot-notation override path
        (``parser.py::enterPropertyAssignment``) used to assign the raw
        string straight to ``Stroke.width`` — invisible for ``px`` (still a
        plausible-looking string) but silently wrong for any other unit,
        since ``Stroke.width: UnitValue | str | float`` validates a bare
        string as its own ``str`` union member instead of raising.
        """
        cscss = """\
[Base]
{
   stroke: {color: gray; width: 5.0 px};

   [viz.sd < 10000]
   {
      stroke.width: 8.0 m;
   }
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        nested = style.styling_rules[0].nested_rules[0]
        assert nested.symbolizer.stroke.width == UnitValue(
            value=8.0, unit=UnitType.METERS
        )

    # ── fill.color + stroke.color combined ─────────────────────────

    def test_fill_and_stroke_dot_notation_both_alter(self):
        """fill.color and stroke.color should each set ``alter`` on their
        own object.
        """
        cscss = """\
[Base]
{
   fill: {color: gray; opacity: 0.5};
   stroke: {color: gray; width: 2.0 px; opacity: 1.0};

   [FunctionCode = 'park']
   {
      fill.color: darkGreen;
      stroke.color: green;
   }
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        nested = style.styling_rules[0].nested_rules[0]
        sym = nested.symbolizer
        assert sym.fill.alter is True
        assert sym.fill.color == "darkGreen"
        assert sym.stroke.alter is True
        assert sym.stroke.color == "green"

    # ── marker.elements[N] sets alter on marker ───────────────────

    def test_marker_elements_indexed_sets_alter(self):
        """marker.elements[1]: Image{...} →
        marker: { alter: true, elements: {index: 1, value: ...} }
        """
        cscss = """\
[Base]
{
   marker: {elements: [Dot(size: 10 px; color: red)]};

   [FunctionCode = 'parking']
   {
      marker.elements[1]:
         Image {
            image: {uri: 'http://example.com/icon'; path: 'icon.png';
                    id: 'parking'; type: 'image/png'; ext: 'png'};
            hotSpot: 50 pc 50 pc; tint: white; blackTint: blue; alphaThreshold: 0.1;
         };
   }
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        nested = style.styling_rules[0].nested_rules[0]
        sym = nested.symbolizer
        assert sym.marker is not None, "marker should be set"
        assert (
            sym.marker.alter is True
        ), "marker.elements[N] must set alter=True on marker"

    # ── No alter when property is set directly (not dot notation) ──

    def test_no_alter_on_direct_fill(self):
        """fill: {color: gray; opacity: 0.5} should NOT set alter."""
        cscss = """\
[Base]
{
   fill: {color: gray; opacity: 0.5};
}
"""
        style = self.parser.parse_string_to_pydantic(cscss)
        sym = style.styling_rules[0].symbolizer
        assert sym.fill is not None
        assert (
            sym.fill.alter is None or sym.fill.alter is False
        ), "Direct fill assignment should not set alter"

    # ── Real file: example 2 should have alter on nested fill/stroke

    def test_example2_alter_flags(self):
        """Example 2 (vector-polygon) nested rules should have alter on fill/stroke."""
        style = self.parser.parse_file_to_pydantic(
            EXAMPLES_DIR / "2-vector-polygon.cscss"
        )
        # Navigate: stylingRules[0] → nestedRules[0] (the zoom rule) →
        # nestedRules[0..2] (FunctionCode rules)
        base_rule = style.styling_rules[0]
        zoom_rule = base_rule.nested_rules[0]
        # The first 3 nested rules use fill.color / stroke.color
        for i in range(3):
            rule = zoom_rule.nested_rules[i]
            sym = rule.symbolizer
            assert sym.fill is not None, f"nestedRules[{i}] should have fill"
            assert (
                sym.fill.alter is True
            ), f"nestedRules[{i}].fill should have alter=True"
            assert sym.stroke is not None, f"nestedRules[{i}] should have stroke"
            assert (
                sym.stroke.alter is True
            ), f"nestedRules[{i}].stroke should have alter=True"


class TestArrayElementMember:
    """``marker.elements[N].member: value`` alters one member of one element."""

    _CSCSS = """\
R
{
   marker: { elements: [ Dot { size: 4 px; color: blue },
                         Image { image: { uri: 'a_N.svg' }; tint: green } ] };
   [a = 2] { marker.elements[1].tint: purple; }
   [a = 3] { marker.elements[0].color: red; marker.elements[0].opacity: 0.5; }
   [a = 4] { marker.elements[1].image.uri: 'a_NE.svg'; }
}
"""

    def _markers(self):
        style = CartoSymParser().parse_string_to_pydantic(self._CSCSS)
        rules = style.to_dict()["stylingRules"][0]["nestedRules"]
        return [rule["symbolizer"]["marker"] for rule in rules]

    def test_member_of_an_element(self):
        assert self._markers()[0] == {
            "alter": True,
            "elements": {
                "index": 1,
                "value": {"type": "Image", "alter": True, "tint": "purple"},
            },
        }

    def test_several_members_of_the_same_element(self):
        assert self._markers()[1]["elements"] == {
            "index": 0,
            "value": {"type": "Dot", "alter": True, "color": "red", "opacity": 0.5},
        }

    def test_member_of_a_member_of_an_element(self):
        value = self._markers()[2]["elements"]["value"]
        assert value["type"] == "Image"
        assert value["image"]["uri"] == "a_NE.svg"
        assert value["image"]["alter"] is True

    def test_element_that_is_not_a_graphic_warns(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            CartoSymParser().parse_string_to_pydantic(
                "R { [a = 1] { marker.elements[0]: 5; } }"
            )
        assert any("marker.elements[0]" in r.message for r in caplog.records)
