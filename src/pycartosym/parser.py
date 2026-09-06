"""CartoSym CSS Parser module.

This module provides the main parsing functionality for CartoSym CSS files.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener

from pycartosym.exceptions import CartoSymSyntaxError
from pycartosym.models.symbolizers import Fill as ModelFill
from pycartosym.models.symbolizers import Label as ModelLabel
from pycartosym.models.symbolizers import Marker as ModelMarker
from pycartosym.models.symbolizers import Stroke as ModelStroke
from pycartosym.models.symbolizers import Symbolizer as ModelSymbolizer

from .ast import Metadata, StyleSheet, StylingRule, StylingRuleList
from .ast import PropertyAssignment as AstPropertyAssignment
from .ast_converter import (
    _coerce_unit_scalar,
    _normalize_graphic_element,
    convert_ast_to_pydantic,
)
from .cql2.from_text import ExpressionParser
from .cql2.model import (
    BinaryOperationExpression,
    ConstantExpression,
    Expression,
    IdentifierExpression,
    InstanceExpression,
    MemberAccessExpression,
    Selector,
    StringExpression,
)
from .cql2.to_json import convert_numeric_expression_value
from .grammar.generated import (
    CartoSymCSSGrammar,
    CartoSymCSSGrammarListener,
    CartoSymCSSLexer,
)
from .models import Style

logger = logging.getLogger(__name__)


class _CollectingErrorListener(ErrorListener):
    """ANTLR error listener that accumulates syntax errors.

    Errors are collected instead of printed to stderr, so
    :meth:`CartoSymParser.parse_string` can raise a single
    :class:`CartoSymSyntaxError`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []
        self.error_tuples: list[tuple[int, int, str]] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"line {line}:{column} {msg}")
        self.error_tuples.append((line, column, msg))


def _strip_inline_comment(s: str) -> str:
    """Strip a ``//`` line comment from *s*, outside quoted string literals.

    Quoted literals are skipped so URLs like ``'http://...'`` stay intact.
    """
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in ("'", '"'):
            # Consume the whole quoted literal without treating // as a comment.
            quote = ch
            result.append(ch)
            i += 1
            while i < len(s) and s[i] != quote:
                result.append(s[i])
                i += 1
            if i < len(s):
                result.append(s[i])  # closing quote
                i += 1
        elif ch == "/" and i + 1 < len(s) and s[i + 1] == "/":
            break  # everything from here onwards is a comment
        else:
            result.append(ch)
            i += 1
    return "".join(result).rstrip()


class CartoSymParser:
    """Main parser class for CartoSym CSS files."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize the parser with the specified log level."""
        self.logger = self._configure_logging(log_level)

    def _configure_logging(self, log_level: str) -> logging.Logger:
        """Configure logging based on the provided log level."""
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), "INFO"),
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return logging.getLogger(__name__)

    # Regex matching  .include 'path'  or  .include "path"
    _INCLUDE_RE = re.compile(r"^\s*\.include\s+['\"](.+?)['\"]\s*$", re.MULTILINE)

    def parse_file(self, file_path: str | Path) -> StyleSheet:
        """Parse a CartoSym CSS file and return an AST.

        Resolves `.include` directives before parsing: each directive is
        replaced by the content of the referenced file (resolved relative
        to the including file).  Includes are recursive; circular includes
        raise ``ValueError``.
        """
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.logger.info(f"Parsing file: {file_path}")

        with open(file_path, encoding="utf-8") as file:
            content = file.read()

        # Resolve .include directives (textual preprocessor)
        content = self._resolve_includes(content, file_path.parent, {file_path})

        return self.parse_string(content)

    # Regex matching a metadata directive (`.title 'x'`, `.abstract 'x'`,
    # `.keywords 'x'`, ... — the grammar's `metadata` rule accepts any
    # identifier, not a fixed set: `'.' IDENTIFIER CHARACTER_LITERAL`).
    # Excludes `.include`, which is resolved separately, before this runs.
    _METADATA_RE = re.compile(
        r"^\s*\.(?!include\b)\w+\s+['\"].*?['\"]\s*$", re.MULTILINE
    )

    def _resolve_includes(
        self,
        content: str,
        base_dir: Path,
        seen: set[Path],
    ) -> str:
        """Recursively resolve `.include` directives by textual substitution.

        Args:
            content: Raw CSCSS text (may contain `.include` lines).
            base_dir: Directory used to resolve relative include paths.
            seen: Set of already-included absolute paths (cycle detection).

        Returns:
            The fully-resolved CSCSS text with all includes inlined.

        Raises:
            FileNotFoundError: If an included file does not exist.
            ValueError: If a circular include is detected.
        """

        def _replacer(match: re.Match) -> str:
            rel_path = match.group(1)
            abs_path = (base_dir / rel_path).resolve()

            if not abs_path.exists():
                raise FileNotFoundError(
                    f"Included file not found: '{rel_path}' "
                    f"(resolved to {abs_path})"
                )

            if abs_path in seen:
                raise ValueError(
                    f"Circular include detected: '{rel_path}' "
                    f"(resolved to {abs_path})"
                )

            seen.add(abs_path)
            with open(abs_path, encoding="utf-8") as f:
                included = f.read()

            # Strip metadata directives from included files — the ANTLR
            # grammar only supports metadata at the top of the stylesheet
            # (`styleSheet: metadata* variableDef* stylingRuleList?`), not
            # between styling rules. Only strip within the leading portion
            # before the first `{`: `.identifier 'literal'` has the exact
            # same shape as `stylingRuleName` (`.name 'x'`, grammar rule
            # `stylingRuleName`), which legitimately appears just inside a
            # rule body — e.g. `Landuse { .name 'x'; ... }` — and must not
            # be stripped.
            brace_idx = included.find("{")
            head, tail = (
                (included, "")
                if brace_idx == -1
                else (included[:brace_idx], included[brace_idx:])
            )
            included = self._METADATA_RE.sub("", head) + tail

            # Recurse: the included file may itself contain .include
            return self._resolve_includes(included, abs_path.parent, seen)

        return self._INCLUDE_RE.sub(_replacer, content)

    def parse_file_to_pydantic(self, file_path: str | Path) -> Style:
        """Parse a CartoSym CSS file and return a Pydantic Style model."""
        ast_stylesheet = self.parse_file(file_path)
        return convert_ast_to_pydantic(ast_stylesheet)

    def parse_string_to_pydantic(self, content: str) -> Style:
        """Parse a CartoSym CSS string and return a Pydantic Style model."""
        ast_stylesheet = self.parse_string(content)
        return convert_ast_to_pydantic(ast_stylesheet)

    def parse_string(self, content: str) -> StyleSheet:
        """Parse a CartoSym CSS string and return an AST.

        Raises:
            CartoSymSyntaxError: if the lexer or parser reports any syntax
                error (rather than returning a partially-built tree).
        """
        error_listener = _CollectingErrorListener()

        input_stream = InputStream(content)
        lexer = CartoSymCSSLexer(input_stream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(error_listener)

        stream = CommonTokenStream(lexer)
        parser = CartoSymCSSGrammar(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(error_listener)

        tree = parser.styleSheet()

        if error_listener.errors:
            raise CartoSymSyntaxError(
                error_listener.errors, error_tuples=error_listener.error_tuples
            )

        # Create listener and walk the tree
        listener = CartoSymStyleSheetListener()
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        # enterStyleSheet always assigns listener.stylesheet during the walk.
        assert listener.stylesheet is not None
        # Post-process AST to merge orphaned marker.elements[N] assignments
        self._merge_marker_elements(listener.stylesheet)
        return listener.stylesheet

    def _merge_marker_elements(self, stylesheet):
        """No-op hook for ``marker.elements[N]`` overrides.

        Such overrides are now kept in their own rule as indexed Markers
        and written back as ``marker.elements[N]: Type { ... }`` by the
        CSCSS writer.
        """
        return


class CartoSymStyleSheetListener(CartoSymCSSGrammarListener):
    """ANTLR listener that builds a :class:`~pycartosym.ast.StyleSheet`.

    Walks the ``CartoSymCSSGrammar`` parse tree and accumulates rules,
    selectors, symbolizers and metadata onto :attr:`stylesheet`.
    """

    def _handle_object_property(
        self, prop_name: str, prop_value: str, symbolizer, expr_ctx=None
    ):
        """Handle object literal property assignments.

        E.g. ``fill: {color: gray; opacity: 0.5}``.

        *expr_ctx* (the assignment's ANTLR expression context, when
        available) lets the ``fill`` branch extract ``hatch``/``dotpattern``/
        ``stipple``/``pattern`` sub-blocks structurally instead of only the
        flat ``properties`` dict built below.
        """
        # Remove outer braces and strip whitespace
        content = prop_value.strip()
        if content.startswith("{") and content.endswith("}"):
            content = content[1:-1].strip()
        else:
            content = content.strip()
        properties: dict = {}
        if content:
            # Split by semicolon, but be careful with nested structures
            parts = []
            current_part = ""
            brace_count = 0
            bracket_count = 0
            for char in content:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                elif char in (";", ",") and brace_count == 0 and bracket_count == 0:
                    if current_part.strip():
                        parts.append(current_part.strip())
                    current_part = ""
                    continue
                current_part += char
            if current_part.strip():
                parts.append(current_part.strip())
            for part in parts:
                # A part may start with a comment line when the previous ; was
                # followed by an inline comment and the actual property is on the
                # next line.
                lines_in_part = part.split("\n")
                start_idx = None
                for i, line in enumerate(lines_in_part):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("//"):
                        start_idx = i
                        break
                if start_idx is None:
                    continue
                effective = "\n".join(lines_in_part[start_idx:]).strip()
                first_nl = effective.find("\n")
                if first_nl == -1:
                    first_line, rest = effective, ""
                else:
                    first_line, rest = effective[:first_nl], effective[first_nl:]
                if "//" in first_line:
                    first_line = first_line.split("//")[0].strip()
                part = (first_line + rest).strip()
                if not part:
                    continue
                if ":" in part:
                    key, value = part.split(":", 1)
                    key_stripped = key.strip()
                    if key_stripped:
                        v = value.strip()
                        # Special handling for position: 0 0;
                        if key_stripped == "position" and isinstance(v, str):
                            parts_v = v.split()
                            if len(parts_v) == 2:
                                try:
                                    x = (
                                        float(parts_v[0])
                                        if "." in parts_v[0]
                                        else int(parts_v[0])
                                    )
                                    y = (
                                        float(parts_v[1])
                                        if "." in parts_v[1]
                                        else int(parts_v[1])
                                    )
                                    properties[key_stripped] = {"x": x, "y": y}
                                except Exception:
                                    properties[key_stripped] = v
                            else:
                                properties[key_stripped] = v
                        else:
                            properties[key_stripped] = v
        # Assign properties to the appropriate symbolizer attribute
        prop_name_lower = prop_name.lower()
        if prop_name_lower == "fill":
            if not symbolizer.fill:
                symbolizer.fill = ModelFill()
            for k, v in properties.items():
                if k == "color":
                    symbolizer.fill.color = v
                elif k == "opacity":
                    try:
                        symbolizer.fill.opacity = float(v)
                    except ValueError:
                        pass
                elif k in ("hatch", "dotpattern", "stipple") and expr_ctx is not None:
                    inner = self._extract_top_level_dict_value(expr_ctx, k)
                    if inner is not None:
                        ctx_map = inner.pop("_expr_ctx", {})
                        for field, field_v in inner.items():
                            inner[field] = _coerce_unit_scalar(
                                field_v, ctx_map.get(field)
                            )
                        setattr(symbolizer.fill, k, inner)
                elif k == "pattern" and expr_ctx is not None:
                    el = self._extract_top_level_named_instance(expr_ctx, "pattern")
                    if el is not None:
                        _normalize_graphic_element(el)
                        symbolizer.fill.pattern = el
        elif prop_name_lower == "stroke":
            if not symbolizer.stroke:
                symbolizer.stroke = ModelStroke()
            for k, v in properties.items():
                if k == "color":
                    symbolizer.stroke.color = v
                elif k == "width":
                    symbolizer.stroke.width = v
                elif k == "opacity":
                    try:
                        symbolizer.stroke.opacity = float(v)
                    except ValueError:
                        pass
        elif prop_name_lower == "zorder" or prop_name_lower == "z_order":
            try:
                symbolizer.z_order = int(
                    properties.get("zOrder", properties.get("z_order", 0))
                )
            except Exception:
                symbolizer.z_order = properties.get(
                    "zOrder", properties.get("z_order", 0)
                )
        elif prop_name_lower == "hillshading" or prop_name_lower == "hill_shading":
            symbolizer.hill_shading = self._parse_hill_shading_object(properties)
        else:
            # For unknown object properties, try to attach the dict.
            # Silently skip if the Pydantic model rejects the attribute
            # (e.g. 'image' from a nested Image{…} class block).
            try:
                setattr(symbolizer, prop_name, properties)
            except Exception:
                pass

    def _handle_marker_element_property(self, element_dict, key, value):
        v = value.strip()
        if key == "position" and isinstance(v, str):
            parts_v = v.split()
            if len(parts_v) == 2:
                try:
                    x = float(parts_v[0]) if "." in parts_v[0] else int(parts_v[0])
                    y = float(parts_v[1]) if "." in parts_v[1] else int(parts_v[1])
                    element_dict[key] = {"x": x, "y": y}
                    return
                except Exception:
                    pass
        element_dict[key] = v

    def __init__(self) -> None:
        """Initialise the listener with empty stylesheet and rule state."""
        self.stylesheet: StyleSheet | None = None
        self.current_rule: StylingRule | None = None
        self.current_assignments: list = []
        self.rule_stack: list = []  # Stack for nested rules
        self.current_selectors: list = []  # Current selectors being processed
        self._in_object_assignment_stack: list = []

    # -- ANTLR tree traversal helpers for structured extraction --

    @staticmethod
    def _collect_inferred_assignments(pai_list_ctx):
        """Flatten a left-recursive ``PropertyAssignmentInferredListContext``.

        Returns the ``PropertyAssignmentInferredContext`` nodes in source
        order.
        """
        if pai_list_ctx is None:
            return []
        items = []
        node = pai_list_ctx
        while node is not None:
            pai = node.propertyAssignmentInferred()
            if pai:
                items.append(pai)
            node = node.propertyAssignmentInferredList()
        items.reverse()
        return items

    @staticmethod
    def _collect_array_elements(array_elements_ctx):
        """Flatten a left-recursive ``ArrayElementsContext``.

        Returns the ``ExpressionContext`` nodes in source order.
        """
        if array_elements_ctx is None:
            return []
        items = []
        node = array_elements_ctx
        while node is not None:
            expr = node.expression()
            if expr:
                items.append(expr)
            node = node.arrayElements()
        items.reverse()
        return items

    @staticmethod
    def _find_exp_instance(expr_ctx):
        """Find the ExpInstanceContext under a (labelled) expression alternative."""
        if expr_ctx is None:
            return None
        if isinstance(expr_ctx, CartoSymCSSGrammar.InstanceExprContext):
            return expr_ctx.expInstance()
        # Parenthesised wrapper: `( <instance> )`
        if isinstance(expr_ctx, CartoSymCSSGrammar.ParenExprContext):
            return CartoSymStyleSheetListener._find_exp_instance(expr_ctx.expression())
        return None

    @staticmethod
    def _expression_source_text(expr_ctx):
        """Get the original source text for an expression, preserving spaces.

        Surrounding quotes from CSCSS string literals (``'...'`` / ``"..."``)
        are stripped so that the value contains only the payload.
        """
        if expr_ctx is None:
            return ""
        start = expr_ctx.start.start
        stop = expr_ctx.stop.stop
        input_stream = expr_ctx.start.getInputStream()
        text = input_stream.getText(start, stop)
        # Strip CSCSS string-literal quotes (single or double)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            text = text[1:-1]
        return text

    @classmethod
    def _extract_element_from_instance(cls, exp_instance_ctx) -> dict:
        """Extract a single element dict from an ``ExpInstanceContext``.

        For example ``Dot { size: 10 px; color: white }``.

        Each leaf key's raw source text is stored as usual, but its ANTLR
        expression context is *also* kept, under a private ``"_expr_ctx"``
        key (one level per nesting, e.g. ``outline: {...}``'s own
        ``"_expr_ctx"``) — otherwise lost once only the text survives. This
        lets downstream numeric coercion
        (``ast_converter.py::_coerce_unit_scalar``/``_coerce_shape_style_dict``)
        fall back to parsing a numeric expression (e.g. ``viz.sd / 1000``,
        OGC issue #115) instead of leaving an opaque string, the same way
        the single dotted-override ``stroke.width: <expr>;`` already does.
        ``ast_converter.py`` pops ``"_expr_ctx"`` back out before the dict
        reaches the final Pydantic model — it must never leak into output.
        """
        ident = exp_instance_ctx.IDENTIFIER()
        result = {"type": ident.getText()} if ident else {}
        pai_list = exp_instance_ctx.propertyAssignmentInferredList()
        if pai_list is None:
            return result
        ctx_map: dict = {}
        for pai in cls._collect_inferred_assignments(pai_list):
            pa = pai.propertyAssignment()
            if pa is None:
                continue
            key = pa.lhValue().getText()
            expr = pa.expression()
            # Nested object? (e.g. font: { ... } or image: { ... })
            nested_ei = cls._find_exp_instance(expr) if expr else None
            if nested_ei is not None and nested_ei.IDENTIFIER() is None:
                # Anonymous nested object → recurse into its properties
                inner = {}
                inner_ctx_map: dict = {}
                inner_list = nested_ei.propertyAssignmentInferredList()
                if inner_list is not None:
                    for inner_pai in cls._collect_inferred_assignments(inner_list):
                        inner_pa = inner_pai.propertyAssignment()
                        if inner_pa:
                            inner_key = inner_pa.lhValue().getText()
                            inner_expr = inner_pa.expression()
                            inner[inner_key] = cls._expression_source_text(inner_expr)
                            inner_ctx_map[inner_key] = inner_expr
                if inner:
                    if inner_ctx_map:
                        inner["_expr_ctx"] = inner_ctx_map
                    result[key] = inner
                else:
                    # Braced but with no `key: value` pairs at all — e.g. a
                    # bare comma-separated list like "{ center, middle }"
                    # for `alignment`, where each entry is an "inferred"
                    # (keyless) assignment. Keep the raw source text instead
                    # of an empty dict, so downstream string-based coercion
                    # (see _normalize_graphic_element in ast_converter.py)
                    # can still parse it.
                    result[key] = cls._expression_source_text(expr)
            elif nested_ei is not None and nested_ei.IDENTIFIER() is not None:
                # Named nested instance (rare) → recurse
                result[key] = cls._extract_element_from_instance(nested_ei)
            else:
                result[key] = cls._expression_source_text(expr)
                ctx_map[key] = expr
        if ctx_map:
            result["_expr_ctx"] = ctx_map
        return result

    @classmethod
    def _extract_elements_from_antlr(cls, expr_ctx) -> list:
        """Extract marker/label elements from an ANTLR ExpressionContext.

        Handles two patterns:
        1. ``{ elements: [ Dot{...}, Image{...} ] }`` — anonymous instance with
           an ``elements`` property containing an array of named instances.
        2. ``Dot { size: 10 px; color: white }`` — single named instance
           (used for ``marker.elements[N]: ...`` overrides).

        Returns a list of dicts with ``type`` and property keys.
        """
        ei = cls._find_exp_instance(expr_ctx)
        if ei is None:
            return []

        ident = ei.IDENTIFIER()

        if ident is not None:
            # Named instance (e.g. Dot{...}, Text{...}, Image{...})
            return [cls._extract_element_from_instance(ei)]

        # Anonymous instance { elements: [...] } — find the elements property
        pai_list = ei.propertyAssignmentInferredList()
        if pai_list is None:
            return []

        for pai in cls._collect_inferred_assignments(pai_list):
            pa = pai.propertyAssignment()
            if pa is None:
                continue
            if pa.lhValue().getText() == "elements":
                # Get the array expression
                arr_expr = pa.expression()
                if not isinstance(arr_expr, CartoSymCSSGrammar.ArrayExprContext):
                    continue
                exp_arr = arr_expr.expArray()
                if exp_arr is None:
                    continue
                arr_elems = exp_arr.arrayElements()
                elements = []
                for elem_expr in cls._collect_array_elements(arr_elems):
                    elem_ei = cls._find_exp_instance(elem_expr)
                    if elem_ei is not None:
                        elements.append(cls._extract_element_from_instance(elem_ei))
                return elements
        return []

    @classmethod
    def _extract_top_level_dict_value(cls, expr_ctx, key: str) -> dict | None:
        """Find ``key: {...}`` at the top level of an anonymous ``{...}`` block.

        E.g. ``label: { elements: [...]; placement: {...} }`` — returns
        ``placement``'s properties as a flat dict (each leaf value paired
        with its ANTLR expression context under ``"_expr_ctx"``, same
        convention as :meth:`_extract_element_from_instance`), or ``None``
        if *key* is absent or isn't an anonymous-object value.
        """
        ei = cls._find_exp_instance(expr_ctx)
        if ei is None:
            return None
        pai_list = ei.propertyAssignmentInferredList()
        if pai_list is None:
            return None
        for pai in cls._collect_inferred_assignments(pai_list):
            pa = pai.propertyAssignment()
            if pa is None or pa.lhValue().getText() != key:
                continue
            value_expr = pa.expression()
            nested_ei = cls._find_exp_instance(value_expr) if value_expr else None
            if nested_ei is None or nested_ei.IDENTIFIER() is not None:
                return None
            inner: dict = {}
            inner_ctx_map: dict = {}
            inner_list = nested_ei.propertyAssignmentInferredList()
            if inner_list is not None:
                for inner_pai in cls._collect_inferred_assignments(inner_list):
                    inner_pa = inner_pai.propertyAssignment()
                    if inner_pa:
                        inner_key = inner_pa.lhValue().getText()
                        inner_expr = inner_pa.expression()
                        inner[inner_key] = cls._expression_source_text(inner_expr)
                        inner_ctx_map[inner_key] = inner_expr
            if inner_ctx_map:
                inner["_expr_ctx"] = inner_ctx_map
            return inner
        return None

    @classmethod
    def _extract_top_level_named_instance(cls, expr_ctx, key: str) -> dict | None:
        """Find ``key: Type {...}`` at the top level of an anonymous ``{...}`` block.

        E.g. ``fill: { pattern: Dot { size: 4 px } }`` — returns the
        extracted element dict (``type`` + properties, same shape as
        :meth:`_extract_element_from_instance`), or ``None`` if *key* is
        absent or isn't a named-instance value.
        """
        ei = cls._find_exp_instance(expr_ctx)
        if ei is None:
            return None
        pai_list = ei.propertyAssignmentInferredList()
        if pai_list is None:
            return None
        for pai in cls._collect_inferred_assignments(pai_list):
            pa = pai.propertyAssignment()
            if pa is None or pa.lhValue().getText() != key:
                continue
            value_expr = pa.expression()
            nested_ei = cls._find_exp_instance(value_expr) if value_expr else None
            if nested_ei is None or nested_ei.IDENTIFIER() is None:
                return None
            return cls._extract_element_from_instance(nested_ei)
        return None

    def enterStyleSheet(self, ctx):
        """Handle entering a stylesheet rule."""
        self.stylesheet = StyleSheet()

    def enterMetadata(self, ctx):
        """Handle entering metadata."""
        if ctx.IDENTIFIER() and ctx.CHARACTER_LITERAL():
            key = ctx.IDENTIFIER().getText()
            # Remove outer quotes from character literal
            value = ctx.CHARACTER_LITERAL().getText().strip("\"'")
            # Handle multiline string continuation: '...\n'\n          '...' pattern
            # ANTLR captures adjacent string literals as one token; remove the
            # internal closing/opening quote pair (apostrophe + whitespace + apostrophe)
            import re as _re_meta

            value = _re_meta.sub(r"'\s*'", " ", value)
            # Decode \n and \t escape sequences into real newline/tab chars
            value = value.replace("\\n", "\n").replace("\\t", "\t")
            # Collapse multiple spaces (but not the newlines/tabs above) and strip
            value = _re_meta.sub(r"  +", " ", value).strip()
            metadata = Metadata(key=key, value=value)
            if not self.stylesheet.metadata:
                self.stylesheet.metadata = []
            self.stylesheet.metadata.append(metadata)

    def enterVariableDef(self, ctx):
        """Handle entering a variable definition (@var = expr;)."""
        from .ast import Variable as AstVariable

        name = None
        value = None
        var_ctx = ctx.variable()
        if var_ctx and var_ctx.IDENTIFIER():
            name = var_ctx.IDENTIFIER().getText()
        expr_ctx = ctx.expression()
        if expr_ctx:
            text = expr_ctx.getText()
            if text.startswith("'") and text.endswith("'"):
                value = text.strip("'")
            else:
                try:
                    value = int(text)
                except ValueError:
                    try:
                        value = float(text)
                    except ValueError:
                        value = text
        var = AstVariable(name=name, value=value)
        if self.stylesheet.variables is None:
            self.stylesheet.variables = []
        self.stylesheet.variables.append(var)

    def enterStylingRuleName(self, ctx):
        """Handle entering a ``stylingRuleName`` (``.name 'value'``).

        Fires after ``enterStylingRule``, so ``self.current_rule`` already
        exists.
        """
        if ctx.CHARACTER_LITERAL() and self.current_rule:
            self.current_rule.styling_rule_name = (
                ctx.CHARACTER_LITERAL().getText().strip("'\"")
            )

    def enterStylingRule(self, ctx):
        """Handle entering a styling rule."""
        if self.current_rule:
            self.rule_stack.append(
                {
                    "rule": self.current_rule,
                    "assignments": self.current_assignments.copy(),
                    "selectors": self.current_selectors.copy(),
                    "_pending_marker_element_assignments": (
                        getattr(self, "_pending_marker_element_assignments", {}).copy()
                        if hasattr(self, "_pending_marker_element_assignments")
                        else {}
                    ),
                }
            )
        self.current_rule = StylingRule()
        self.current_assignments = []
        self.current_selectors = []
        # Inherit any pending marker element assignments from the parent
        # stack (propagate down)
        if (
            self.rule_stack
            and "_pending_marker_element_assignments" in self.rule_stack[-1]
        ):
            self._pending_marker_element_assignments = self.rule_stack[-1][
                "_pending_marker_element_assignments"
            ].copy()
        else:
            self._pending_marker_element_assignments = {}

    def exitStylingRule(self, ctx):
        """Finalise the current styling rule when its ``stylingRule`` subtree closes."""
        # Always create a new symbolizer for each rule, even if nested
        symbolizer_obj = ModelSymbolizer()
        explicit_symbolizer = None
        # Always collect all property assignments for this rule (for post-processing)
        if self.current_assignments:
            self.current_rule.property_assignments.extend(self.current_assignments)
        # Continue with normal property assignment handling for this rule
        # (import supprimé, on utilise les alias globaux)
        symbolizer_set = False
        if self.current_assignments:
            for assignment in self.current_assignments:
                # Traitement spécial pour symbolizer: Fill { ... }
                if assignment.property_name.strip().lower() == "symbolizer":
                    value = assignment.value.strip()
                    if value.lower().startswith("fill"):
                        # Extraction du bloc Fill { ... }
                        import re

                        m = re.match(r"Fill\s*\{(.*)\}", value, re.DOTALL)
                        if m:
                            props_str = m.group(1)
                            # Parse les propriétés du bloc
                            props = {}
                            for part in props_str.split(";"):
                                if ":" in part:
                                    k, v = part.split(":", 1)
                                    props[k.strip()] = v.strip()
                            fill = ModelFill()
                            if "color" in props:
                                fill.color = props["color"]
                            if "opacity" in props:
                                try:
                                    fill.opacity = float(props["opacity"])
                                except Exception:
                                    pass
                            explicit_symbolizer = ModelSymbolizer(fill=fill)
                            self.current_rule.symbolizer = explicit_symbolizer
                            symbolizer_set = True
                            continue
                    # Autres types de symbolizer à ajouter ici si besoin
                self._handle_property_assignment_enhanced(
                    assignment.property_name,
                    assignment.value,
                    symbolizer_obj,
                    assignment,
                )
        # Si aucune propriété symbolizer explicite, mais symbolizer a été
        # rempli, on l'affecte
        if not symbolizer_set and (
            symbolizer_obj.fill
            or symbolizer_obj.stroke
            or symbolizer_obj.hill_shading
            or symbolizer_obj.z_order
        ):
            self.current_rule.symbolizer = symbolizer_obj
        pending = getattr(self, "_pending_marker_element_assignments", {})
        effective_sym = (
            explicit_symbolizer if explicit_symbolizer is not None else symbolizer_obj
        )
        if pending and effective_sym.marker is None:
            # Use the first (and typically only) indexed override
            for idx, el_props in sorted(pending.items()):
                from .models.symbolizers import Marker as PydanticMarker

                effective_sym.marker = PydanticMarker(
                    alter=True, elements={"index": idx, "value": el_props}
                )
                break
            self._pending_marker_element_assignments = {}
        # Attach symbolizer to rule
        self.current_rule.symbolizer = effective_sym
        # Always set selectors, even if only one selector or only conditions
        if self.current_selectors:
            self.current_rule.selectors = self.current_selectors.copy()
            for selector in self.current_selectors:
                if hasattr(selector, "name") and selector.name:
                    self.current_rule.name = selector.name
                    break
        else:
            if self.rule_stack and "selectors" in self.rule_stack[-1]:
                self.current_rule.selectors = self.rule_stack[-1]["selectors"].copy()
        # Handle nesting: if we're in a nested rule, add to parent
        if self.rule_stack:
            parent_state = self.rule_stack.pop()
            parent_rule = parent_state["rule"]
            if not hasattr(parent_rule, "nested_rules"):
                parent_rule.nested_rules = []
            parent_rule.nested_rules.append(self.current_rule)
            self.current_rule = parent_rule
            self.current_assignments = parent_state["assignments"]
            self.current_selectors = parent_state["selectors"]
        else:
            if not self.stylesheet.styling_rules:
                self.stylesheet.styling_rules = StylingRuleList(rules=[])
            self.stylesheet.styling_rules.rules.append(self.current_rule)
            self.current_rule = None
            self.current_assignments = []
            self.current_selectors = []

    def enterSelector(self, ctx):
        """Handle entering a selector."""
        # Create a new selector
        selector = Selector()

        # Handle simple name selector
        if ctx.IDENTIFIER():
            raw_name = ctx.IDENTIFIER().getText()
            # Strip surrounding quotes (double or single) from quoted identifiers
            # e.g. "sentinel2-l2a" → sentinel2-l2a
            selector.name = raw_name.strip("\"'")

        # Handle conditional selector [expression]
        # This can be either in the same context or separate
        conditions_found = False

        # Check if this selector context has an expression (for [expr] selectors)
        if (
            hasattr(ctx, "LSBR")
            and ctx.LSBR()
            and hasattr(ctx, "expression")
            and ctx.expression()
        ):
            try:
                # Walk the ANTLR ExpressionContext parse tree directly
                # instead of re-scanning the selector text.
                expr_ctx = ctx.expression()
                expr = ExpressionParser.parse_expression_ctx(expr_ctx)
                if expr is None:
                    raise ValueError("empty selector expression")
                selector.conditions = [expr]
                conditions_found = True
            except Exception:  # noqa: BLE001 - degrade to a plain text identifier
                expr_text = ctx.expression().getText() if ctx.expression() else ""
                logger.warning("selector expression parse failed: %r", expr_text)
                selector.conditions = [IdentifierExpression(name=expr_text)]
                conditions_found = True

        # If no conditions found and we have an identifier, it's a simple selector
        if not conditions_found and selector.name:
            # This is a simple selector like "Landuse"
            pass
        self.current_selectors.append(selector)

    def enterPropertyAssignment(self, ctx):
        """Handle entering a property assignment."""
        if ctx.lhValue() and ctx.expression():
            prop_name = ctx.lhValue().getText()
            expr_ctx = ctx.expression()
            start = expr_ctx.start.start
            stop = expr_ctx.stop.stop
            input_stream = expr_ctx.start.getInputStream()
            prop_value = input_stream.getText(start, stop)

            # Detect nested object patterns: plain {…}, ClassName{…}, ClassName(…)
            # This prevents inner properties (e.g. image: inside Image{…}) from
            # being collected as separate top-level assignments.
            stripped = prop_value.strip()
            is_object = (stripped.startswith("{") and stripped.endswith("}")) or bool(
                re.match(r"[A-Za-z_]\w*\s*[{(]", stripped)
            )
            self._in_object_assignment_stack.append(is_object)

            # Only collect assignment if not inside an object property
            if not any(self._in_object_assignment_stack[:-1]):
                assignment = AstPropertyAssignment(
                    property_name=prop_name, value=prop_value
                )
                # Attach the ANTLR expression context for structured extraction
                # (used by marker/label handlers instead of regex).
                assignment._antlr_expr_ctx = ctx.expression()
                self.current_assignments.append(assignment)

    def exitPropertyAssignment(self, ctx):
        """Record a property assignment when its subtree closes."""
        if (
            hasattr(self, "_in_object_assignment_stack")
            and self._in_object_assignment_stack
        ):
            self._in_object_assignment_stack.pop()

    def _expression_to_string(self, expr: Expression) -> str:
        """Convert expression back to string representation for compatibility."""
        if isinstance(expr, IdentifierExpression):
            return expr.name
        elif isinstance(expr, ConstantExpression):
            result = str(expr.value)
            if expr.unit:
                result += f" {expr.unit}"
            return result
        elif isinstance(expr, StringExpression):
            return f'"{expr.value}"'
        elif isinstance(expr, MemberAccessExpression):
            obj_str = self._expression_to_string(expr.object)
            return f"{obj_str}.{expr.member}"
        elif isinstance(expr, BinaryOperationExpression):
            left_str = self._expression_to_string(expr.left)
            right_str = self._expression_to_string(expr.right)
            return f"{left_str} {expr.operator.value} {right_str}"
        elif isinstance(expr, InstanceExpression):
            # Handle instance expressions like {color: red; opacity: 0.5}
            if expr.class_name:
                return f"{expr.class_name}(...)"  # Simplified
            else:
                props = []
                for prop in expr.properties:
                    prop_val = self._expression_to_string(prop.value)
                    props.append(f"{prop.property}: {prop_val}")
                return "{" + "; ".join(props) + "}"
        else:
            # Fallback
            return str(expr)

    def _handle_property_assignment_enhanced(
        self, prop_name: str, prop_value: str, symbolizer, assignment=None
    ):
        """Enhanced property assignment handler with expression support."""
        # Resolve @variable references before processing
        if isinstance(prop_value, str) and prop_value.startswith("@"):
            var_name = prop_value[1:]
            if self.stylesheet is not None and self.stylesheet.variables:
                for v in self.stylesheet.variables:
                    if v.name == var_name:
                        prop_value = (
                            str(v.value) if not isinstance(v.value, str) else v.value
                        )
                        break

        # Retrieve the ANTLR expression context stored during enterPropertyAssignment
        expr_ctx = getattr(assignment, "_antlr_expr_ctx", None) if assignment else None

        # Special handler for marker property (must be first, not nested)
        if prop_name == "marker":
            elements = []
            if expr_ctx is not None:
                elements = self._extract_elements_from_antlr(expr_ctx)
            # Use the Pydantic Marker model (not the AST dataclass) so that
            # assignment to the Pydantic Symbolizer passes validation.
            symbolizer.marker = ModelMarker(elements=elements if elements else None)
            return

        if prop_name == "label":
            elements = []
            placement = None
            if expr_ctx is not None:
                elements = self._extract_elements_from_antlr(expr_ctx)
                placement = self._extract_top_level_dict_value(expr_ctx, "placement")
            if placement is not None:
                ctx_map = placement.pop("_expr_ctx", {})
                for numeric_key in ("minSpacing", "maxSpacing", "priority"):
                    if numeric_key in placement:
                        placement[numeric_key] = convert_numeric_expression_value(
                            placement[numeric_key], ctx_map.get(numeric_key)
                        )
            # Use the Pydantic Label model so it passes Symbolizer validation.
            symbolizer.label = ModelLabel(
                elements=elements if elements else None, placement=placement
            )
            return

        # Handle marker.elements[N]: ... assignments
        import re

        m = re.match(r"marker\.elements\[(\d+)\]", prop_name)
        if m:
            idx = int(m.group(1))
            props = None
            if expr_ctx is not None:
                extracted = self._extract_elements_from_antlr(expr_ctx)
                if extracted:
                    props = extracted[0]  # Single element from marker.elements[N]
            if props:
                if (
                    not hasattr(self, "_pending_marker_element_assignments")
                    or self._pending_marker_element_assignments is None
                ):
                    self._pending_marker_element_assignments = {}
                self._pending_marker_element_assignments[idx] = props
            return
        # Handle dot notation properties like fill.color, stroke.width
        if "." in prop_name:
            parts = prop_name.split(".")
            if len(parts) == 2:
                obj_name, attr_name = parts
                if obj_name.lower() == "fill":
                    if not symbolizer.fill:
                        symbolizer.fill = ModelFill()
                    symbolizer.fill.alter = True
                    if attr_name.lower() == "color":
                        symbolizer.fill.color = prop_value
                    elif attr_name.lower() == "opacity":
                        try:
                            symbolizer.fill.opacity = float(prop_value)
                        except ValueError:
                            pass
                elif obj_name.lower() == "stroke":
                    if not symbolizer.stroke:
                        symbolizer.stroke = ModelStroke()
                    symbolizer.stroke.alter = True
                    if attr_name.lower() == "color":
                        symbolizer.stroke.color = prop_value
                    elif attr_name.lower() == "width":
                        # Same unit-string parsing as the full-block form
                        # (_convert_stroke) — a bare assignment here would
                        # let a non-px value like "8.0 m" validate as the
                        # Stroke.width union's plain-``str`` member instead
                        # of a proper UnitValue, silently wrong downstream.
                        # Also recognizes a numeric expression over a system
                        # identifier (e.g. "viz.sd / 1000") when the ANTLR
                        # tree is available, instead of round-tripping it as
                        # opaque text (OGC issue #115).
                        symbolizer.stroke.width = convert_numeric_expression_value(
                            prop_value, expr_ctx
                        )
                    elif attr_name.lower() == "opacity":
                        try:
                            symbolizer.stroke.opacity = float(prop_value)
                        except ValueError:
                            pass
        else:
            # Handle direct properties
            prop_name_lower = prop_name.lower()
            # Handle special property value parsing for complex objects
            if prop_value.startswith("{") and prop_value.endswith("}"):
                # This is an object literal like {color: gray; opacity: 0.5}
                self._handle_object_property(
                    prop_name_lower, prop_value, symbolizer, expr_ctx
                )
            else:
                # Simple property
                if prop_name_lower == "visibility":
                    if prop_value.lower() == "false":
                        symbolizer.visibility = False
                    elif prop_value.lower() == "true":
                        symbolizer.visibility = True
                elif prop_name_lower == "opacity":
                    try:
                        symbolizer.opacity = float(prop_value)
                    except ValueError:
                        pass
                elif prop_name_lower in ("zorder", "z_order"):
                    try:
                        symbolizer.z_order = int(prop_value)
                    except Exception:
                        symbolizer.z_order = prop_value
                elif prop_name_lower in ("singlechannel", "single_channel"):
                    symbolizer.single_channel = prop_value.strip()
                elif prop_name_lower in ("colorchannels", "color_channels"):
                    symbolizer.color_channels = prop_value.strip()
                elif prop_name_lower in ("alphachannel", "alpha_channel"):
                    symbolizer.alpha_channel = prop_value.strip()
                elif prop_name_lower in ("colormap", "color_map"):
                    symbolizer.color_map = self._parse_color_map(prop_value.strip())
                elif prop_name_lower in ("opacitymap", "opacity_map"):
                    symbolizer.opacity_map = self._parse_opacity_map(prop_value.strip())
        # Remove outer braces only (not all braces at start/end)
        content = prop_value
        if content.startswith("{") and content.endswith("}"):
            content = content[1:-1].strip()
        else:
            content = content.strip()
        properties: dict = {}
        if content:
            # Split by semicolon, but be careful with nested structures
            parts = []
            current_part = ""
            brace_count = 0
            bracket_count = 0

            for char in content:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                elif char in (";", ",") and brace_count == 0 and bracket_count == 0:
                    if current_part.strip():
                        parts.append(current_part.strip())
                    current_part = ""
                    continue
                current_part += char

            # Add the last part
            if current_part.strip():
                parts.append(current_part.strip())

            # Parse each part as key: value, filtering out comments
            for part in parts:
                # Split multi-line parts (e.g., comment + actual property on next line)
                lines = part.split("\n")
                for line in lines:
                    line = line.strip()

                    # Skip comment-only lines
                    if line.startswith("//"):
                        continue

                    # Remove inline comments from lines
                    if "//" in line:
                        line = line.split("//")[0].strip()

                    # Skip empty lines after comment removal
                    if not line:
                        continue

                    if ":" in line:
                        key, value = line.split(":", 1)
                        key_stripped = key.strip()
                        if key_stripped:  # Make sure key is not empty
                            properties[key_stripped] = value.strip()

        # Apply properties to symbolizer
        # Coverage/Raster object properties
        if prop_name in ["hillshading", "hill_shading"]:
            # Handle hillShading: {factor: 56; sun: {azimuth: 45.0; elevation: 60.0}}
            symbolizer.hill_shading = self._parse_hill_shading_object(properties)

    def _parse_color_map(self, prop_value: str):
        """Parse color map from string format."""
        try:
            # Handle array format: [0 96 136 73, 900 226 219 167, ...]
            # or [0 black, 0.15 gray, ...]
            if prop_value.startswith("[") and prop_value.endswith("]"):
                content = prop_value.strip("[]").strip()
                if content:
                    # Split by commas first
                    segments = [seg.strip() for seg in content.split(",")]
                    parsed_segments: list = []
                    for seg in segments:
                        # Each segment is "value r g b" or "value colorName"
                        parts = seg.strip().split()
                        if len(parts) >= 4:
                            try:
                                value = float(parts[0])
                                r, g, b = int(parts[1]), int(parts[2]), int(parts[3])
                                parsed_segments.append([value, [r, g, b]])
                            except (ValueError, IndexError):
                                parsed_segments.append({"raw": seg})
                        elif len(parts) == 2:
                            # Format: "value colorName" (e.g., "0 black")
                            try:
                                value = float(parts[0])
                                color_name = parts[1]
                                parsed_segments.append([value, color_name])
                            except ValueError:
                                parsed_segments.append({"raw": seg})
                        else:
                            parsed_segments.append({"raw": seg})
                    return parsed_segments
            return {"raw_value": prop_value}
        except Exception:
            return {"raw_value": prop_value}

    def _parse_opacity_map(self, prop_value: str):
        """Parse opacity map from string format."""
        try:
            # Handle array format: [0 0.75, 0.15 0.50, ...]
            if prop_value.startswith("[") and prop_value.endswith("]"):
                content = prop_value.strip("[]").strip()
                if content:
                    # Split by commas first
                    segments = [seg.strip() for seg in content.split(",")]
                    parsed_segments: list = []
                    for seg in segments:
                        # Each segment is "value opacity"
                        parts = seg.strip().split()
                        if len(parts) >= 2:
                            try:
                                value = float(parts[0])
                                opacity = float(parts[1])
                                parsed_segments.append([value, opacity])
                            except (ValueError, IndexError):
                                parsed_segments.append({"raw": seg})
                        else:
                            parsed_segments.append({"raw": seg})
                    return parsed_segments
            return {"raw_value": prop_value}
        except Exception:
            return {"raw_value": prop_value}

    def _parse_hill_shading_object(self, properties: dict):
        """Parse hill shading object from properties."""
        result: dict = {}
        for key, value in properties.items():
            if key == "sun":
                # Handle nested sun object: {azimuth: 45.0; elevation: 60.0}
                if (
                    isinstance(value, str)
                    and value.startswith("{")
                    and value.endswith("}")
                ):
                    sun_content = value.strip("{}").strip()
                    sun_props: dict = {}
                    if sun_content:
                        for part in sun_content.split(";"):
                            if ":" in part:
                                k, v = part.split(":", 1)
                                try:
                                    sun_props[k.strip()] = float(v.strip())
                                except ValueError:
                                    sun_props[k.strip()] = v.strip()
                    result["sun"] = sun_props
                else:
                    result["sun"] = value
            elif key in ["colorMap", "color_map"]:
                # Handle colorMap inside hillShading
                result["colorMap"] = (
                    self._parse_color_map(value) if isinstance(value, str) else value
                )
            elif key in ["opacityMap", "opacity_map"]:
                # Handle opacityMap inside hillShading
                result["opacityMap"] = (
                    self._parse_opacity_map(value) if isinstance(value, str) else value
                )
            else:
                # Handle other properties like factor
                if isinstance(value, str):
                    try:
                        result[key] = float(value) if "." in value else int(value)
                    except ValueError:
                        result[key] = value
                else:
                    result[key] = value
        return result
