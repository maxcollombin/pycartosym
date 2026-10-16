"""Tests for the .include directive preprocessing."""

from pathlib import Path

import pytest

from pycartosym.parser import CartoSymParser

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _rule_selector_name(rule) -> str | None:
    """Extract the top-level identifier name from a rule's selector/selectors.

    In the AST, a simple ``[Landuse]`` selector is stored as
    ``rule.selectors[0].conditions[0].name`` (IdentifierExpression).
    """
    if getattr(rule, "selectors", None):
        sel = rule.selectors[0]
        if getattr(sel, "conditions", None):
            cond = sel.conditions[0]
            if hasattr(cond, "name"):
                return cond.name
    return rule.name


class TestIncludeDirective:
    """Tests for .include directive resolution in CSCSS files."""

    def setup_method(self):
        self.parser = CartoSymParser(inline_includes=True)

    # ── Detection & resolution ────────────────────────────────────

    def test_include_resolves_file_content(self, tmp_path):
        """An .include directive should inline the referenced file content."""
        child = tmp_path / "child.cscss"
        child.write_text("[Landuse]\n{\n   visibility: false;\n}\n")

        parent = tmp_path / "parent.cscss"
        parent.write_text(".include 'child.cscss'\n")

        result = self.parser.parse_file(parent)
        assert result.styling_rules is not None
        assert len(result.styling_rules.rules) >= 1
        assert _rule_selector_name(result.styling_rules.rules[0]) == "Landuse"

    def test_include_preserves_local_rules(self, tmp_path):
        """Rules after .include directives should be preserved."""
        child = tmp_path / "child.cscss"
        child.write_text("[Layer1]\n{\n   visibility: false;\n}\n")

        parent = tmp_path / "parent.cscss"
        parent.write_text(
            ".include 'child.cscss'\n\n" "[Layer2]\n{\n   opacity: 0.5;\n}\n"
        )

        result = self.parser.parse_file(parent)
        assert result.styling_rules is not None
        rule_names = [_rule_selector_name(r) for r in result.styling_rules.rules]
        assert "Layer1" in rule_names
        assert "Layer2" in rule_names

    def test_multiple_includes(self, tmp_path):
        """Multiple .include directives should all be resolved in order."""
        a = tmp_path / "a.cscss"
        a.write_text("[LayerA]\n{\n   visibility: true;\n}\n")

        b = tmp_path / "b.cscss"
        b.write_text("[LayerB]\n{\n   visibility: false;\n}\n")

        main = tmp_path / "main.cscss"
        main.write_text(".include 'a.cscss'\n" ".include 'b.cscss'\n")

        result = self.parser.parse_file(main)
        assert result.styling_rules is not None
        rule_names = [_rule_selector_name(r) for r in result.styling_rules.rules]
        assert rule_names == ["LayerA", "LayerB"]

    # ── Relative path resolution ──────────────────────────────────

    def test_include_relative_to_parent_file(self, tmp_path):
        """Paths in .include should resolve relative to the including file."""
        subdir = tmp_path / "styles"
        subdir.mkdir()

        child = subdir / "base.cscss"
        child.write_text("[Base]\n{\n   visibility: true;\n}\n")

        parent = tmp_path / "main.cscss"
        parent.write_text(".include 'styles/base.cscss'\n")

        result = self.parser.parse_file(parent)
        assert result.styling_rules is not None
        assert _rule_selector_name(result.styling_rules.rules[0]) == "Base"

    # ── Recursive includes ────────────────────────────────────────

    def test_recursive_include(self, tmp_path):
        """A file included by another include should be resolved recursively."""
        grandchild = tmp_path / "grandchild.cscss"
        grandchild.write_text("[Deep]\n{\n   visibility: true;\n}\n")

        child = tmp_path / "child.cscss"
        child.write_text(".include 'grandchild.cscss'\n")

        parent = tmp_path / "parent.cscss"
        parent.write_text(".include 'child.cscss'\n")

        result = self.parser.parse_file(parent)
        assert result.styling_rules is not None
        assert _rule_selector_name(result.styling_rules.rules[0]) == "Deep"

    # ── Error cases ───────────────────────────────────────────────

    def test_include_file_not_found(self, tmp_path):
        """Including a nonexistent file should raise FileNotFoundError."""
        parent = tmp_path / "main.cscss"
        parent.write_text(".include 'nonexistent.cscss'\n")

        with pytest.raises(FileNotFoundError, match="nonexistent.cscss"):
            self.parser.parse_file(parent)

    def test_circular_include_raises_error(self, tmp_path):
        """Circular includes should raise ValueError."""
        a = tmp_path / "a.cscss"
        b = tmp_path / "b.cscss"

        a.write_text(".include 'b.cscss'\n")
        b.write_text(".include 'a.cscss'\n")

        with pytest.raises(ValueError, match="[Cc]ircular"):
            self.parser.parse_file(a)

    # ── Metadata stripping ────────────────────────────────────────

    def test_include_strips_arbitrary_metadata_keys(self, tmp_path):
        """Any leading `.identifier 'x'` metadata (not just .title/.abstract)
        must be stripped from an included file, since the grammar only
        allows metadata at the very top of a stylesheet.
        """
        child = tmp_path / "child.cscss"
        child.write_text(
            ".description 'A child stylesheet'\n"
            ".keywords 'a, b, c'\n"
            "[Layer]\n{\n   visibility: true;\n}\n"
        )

        parent = tmp_path / "parent.cscss"
        parent.write_text(".include 'child.cscss'\n")

        # Would raise a parse error if .description/.keywords leaked
        # through into the middle of the flattened stylesheet.
        result = self.parser.parse_file(parent)
        assert result.styling_rules is not None
        assert _rule_selector_name(result.styling_rules.rules[0]) == "Layer"

    def test_include_preserves_styling_rule_name_in_body(self, tmp_path):
        """`.name 'x'` inside a rule body (stylingRuleName) has the exact
        same textual shape as a metadata directive but must NOT be
        stripped — it only looks like metadata before the first `{`.
        """
        child = tmp_path / "child.cscss"
        child.write_text("[Layer]\n{\n   .name 'CustomName'\n   visibility: true;\n}\n")

        parent = tmp_path / "parent.cscss"
        parent.write_text(".include 'child.cscss'\n")

        result = self.parser.parse_file(parent)
        assert result.styling_rules is not None
        rule = result.styling_rules.rules[0]
        assert rule.styling_rule_name == "CustomName"

    # ── Integration with real input files ─────────────────────────

    def test_include_example_file_parses(self):
        """The example examples/12-include.cscss should parse without errors."""
        include_file = EXAMPLES_DIR / "12-include.cscss"
        if not include_file.exists():
            pytest.skip("examples/12-include.cscss not found")

        result = self.parser.parse_file(include_file)
        assert result.styling_rules is not None
        # Should contain rules from both included files + the local rule
        assert len(result.styling_rules.rules) >= 2

    def test_parse_string_ignores_includes(self):
        """parse_string() should not resolve includes (no file context)."""
        content = ".include 'some.cscss'\n[Layer]\n{\n   visibility: true;\n}\n"
        # parse_string has no base_dir, so .include lines should be
        # treated as unknown directives (ignored or passed through)
        result = self.parser.parse_string(content)
        assert result.styling_rules is not None

    # ── Variables alongside includes ──────────────────────────────

    def test_include_with_own_variables_keeps_rules_and_variables(self, tmp_path):
        """A file with `.include`, its own variables and rules loses nothing."""
        (tmp_path / "base.cscss").write_text("Water { fill: { color: blue }; }\n")
        main = tmp_path / "main.cscss"
        main.write_text(
            ".include 'base.cscss'\n"
            "@roadWidth = 3;\n"
            "Roads { stroke: { width: @roadWidth * 2 px; color: red }; }\n"
        )

        result = self.parser.parse_file(main)

        names = [_rule_selector_name(r) for r in result.styling_rules.rules]
        assert names == ["Water", "Roads"]
        assert [v.name for v in result.variables] == ["roadWidth"]

    def test_included_variables_come_before_own_variables(self, tmp_path):
        (tmp_path / "base.cscss").write_text("@a = 1;\nWater { opacity: 1; }\n")
        main = tmp_path / "main.cscss"
        main.write_text(".include 'base.cscss'\n@b = 2;\nRoads { opacity: 1; }\n")

        result = self.parser.parse_file(main)

        assert [v.name for v in result.variables] == ["a", "b"]


def test_input_after_a_rule_that_cannot_continue_is_an_error():
    """A variable after a rule must raise, not silently drop what follows."""
    from pycartosym.exceptions import CartoSymSyntaxError

    with pytest.raises(CartoSymSyntaxError):
        CartoSymParser().parse_string(
            "Water { opacity: 1; }\n@w = 3;\nRoads { opacity: 1; }\n"
        )
