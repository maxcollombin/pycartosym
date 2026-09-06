"""Converter module for transforming between different formats.

This module provides conversion capabilities between CartoSym CSS and other formats,
using Pydantic models for robust validation and serialization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Style
from .parser import CartoSymParser


class Converter:
    """Main converter class for format transformations using Pydantic models."""

    def __init__(self) -> None:
        """Create the converter with a fresh :class:`CartoSymParser`."""
        self.parser = CartoSymParser()

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve *path* relative to the project root (the ``pyproject.toml`` dir).

        Absolute or already-existing paths are returned unchanged.
        """
        p = Path(path)
        if p.is_absolute() or p.exists():
            return p
        # Cherche la racine du projet
        root = Path(__file__).resolve().parent.parent.parent
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            abs_path = root / p
            return abs_path
        return p

    def cscss_to_csjson(self, cscss_input: str | Path | Style) -> dict[str, Any]:
        """Convert CartoSym CSS (CSCSS) to CartoSym JSON (CSJSON) format.

        Args:
            cscss_input: CSCSS string, file path, or Style model

        Returns:
            Dictionary representation suitable for CSJSON serialization
        """
        if isinstance(cscss_input, Style):
            # Already a Style model
            style = cscss_input
        elif isinstance(cscss_input, (str, Path)):
            # Check if it's a path first (shorter strings, no newlines)
            if isinstance(cscss_input, Path):
                resolved = self._resolve_path(cscss_input)
                style = self.parser.parse_file_to_pydantic(resolved)
            elif (
                isinstance(cscss_input, str)
                and cscss_input.strip()
                and len(cscss_input) < 500
                and "\n" not in cscss_input
                and Path(cscss_input).is_file()
            ):
                resolved = self._resolve_path(cscss_input)
                style = self.parser.parse_file_to_pydantic(resolved)
            else:
                # Parse from string using ANTLR parser
                style = self.parser.parse_string_to_pydantic(cscss_input)
        else:
            raise ValueError("Invalid input type - expected str, Path, or Style model")

        result = style.to_dict()
        # Post-process the CS-JSON dict in one recursive pass: fix an
        # invalid/sysId-expression selector shape and unit-value
        # serialization (previously three separate full-tree traversals —
        # _fix_invalid_selectors, _fix_unit_values, _fix_sysid_expressions —
        # each walking the same structure on its own).
        self._postprocess_csjson(result)
        return result

    def _postprocess_csjson(self, data):
        """Recursively apply every CS-JSON node-level fix in a single pass."""
        if isinstance(data, dict):
            self._fix_selector(data)
            self._fix_unit_values(data)
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._postprocess_csjson(value)
        elif isinstance(data, list):
            for item in data:
                self._postprocess_csjson(item)

    def _fix_selector(self, data):
        """Fix this node's own ``selector`` key in place, if present.

        Combines what were two separate full-tree passes (both only ever
        inspected this one key, never anything else): an invalid bare
        ``{"property": X}`` selector (likely a parsing error where a member
        access like ``'viz.timeInterval.start.date'`` was incorrectly
        split) is dropped entirely; a ``sysId`` value containing a
        comparison operator (e.g. ``"viz.sd > 100"``) is split into a
        proper ``op``/``args`` selector.
        """
        selector = data.get("selector")
        if not isinstance(selector, dict):
            return
        if "property" in selector:
            # A len==1 bare property reference is the special case of "no
            # op/args either" (its only key is "property"), so one check
            # covers both — the original two-branch form only ever agreed.
            if "op" not in selector and "args" not in selector:
                del data["selector"]
            return
        sysid = selector.get("sysId")
        if not isinstance(sysid, str):
            return
        for op in [">=", "<=", "!=", "=", ">", "<"]:
            if op not in sysid:
                continue
            parts = sysid.split(op, 1)
            if len(parts) != 2:
                continue
            left_part = parts[0].strip()
            right_part = parts[1].strip()
            try:
                right_value = (
                    float(right_part) if "." in right_part else int(right_part)
                )
            except ValueError:
                right_value = right_part.strip("'\"")
            data["selector"] = {"op": op, "args": [{"sysId": left_part}, right_value]}
            break

    def csjson_to_style(self, csjson_input: str | dict[str, Any] | Path) -> Style:
        """Convert CSJSON to CartoSym Style model.

        Args:
            csjson_input: CSJSON string, dictionary, or file path

        Returns:
            Validated Style model
        """
        if isinstance(csjson_input, Style):
            return csjson_input
        elif isinstance(csjson_input, Path) or (
            isinstance(csjson_input, str) and Path(csjson_input).is_file()
        ):
            file_path = self._resolve_path(csjson_input)
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            return Style.from_json(content)
        elif isinstance(csjson_input, str):
            # Parse JSON string
            return Style.from_json(csjson_input)
        elif isinstance(csjson_input, dict):
            # Parse dictionary
            return Style.from_dict(csjson_input)
        else:
            raise ValueError(
                "Invalid input type - expected str, dict, Path, or Style model"
            )

    def csjson_to_cscss(self, csjson_input: str | dict[str, Any] | Path) -> str:
        """Convert CSJSON to CartoSym CSS (CSCSS) format.

        Args:
            csjson_input: CSJSON string, dictionary, or file path

        Returns:
            CSCSS string representation
        """
        # First convert to Style model for validation
        style = self.csjson_to_style(csjson_input)

        # Then convert Style to CSS
        return self.style_to_cscss(style)

    def style_to_cscss(self, style: Style) -> str:
        """Convert Style model to CSCSS string with pretty-print indentation."""
        lines = []
        # Add metadata + $include as CSCSS directives (same header block —
        # the grammar's own ``styleSheet: metadata* variableDef*
        # stylingRuleList?`` puts .include alongside .title/.abstract/etc.,
        # before any @variable declaration).
        header_lines = []
        if style.metadata:
            if getattr(style.metadata, "title", None):
                header_lines.append(f".title '{style.metadata.title}'")
            if getattr(style.metadata, "abstract", None):
                header_lines.append(f".abstract '{style.metadata.abstract}'")
            if getattr(style.metadata, "description", None):
                header_lines.append(f".description '{style.metadata.description}'")
            if style.metadata.authors:
                for author in style.metadata.authors:
                    header_lines.append(f'.author "{author}"')
            if style.metadata.keywords:
                kw = style.metadata.keywords
                kw_str = ", ".join(kw) if isinstance(kw, list) else kw
                header_lines.append(f".keywords '{kw_str}'")
            # Model field is ``geo_data_classes`` (alias ``geoDataClasses``);
            # the CSCSS directive keeps the camelCase spelling.
            if style.metadata.geo_data_classes:
                gc = style.metadata.geo_data_classes
                gc_str = ", ".join(gc) if isinstance(gc, list) else gc
                header_lines.append(f".geoDataClasses '{gc_str}'")
        if style.include:
            includes = (
                style.include if isinstance(style.include, list) else [style.include]
            )
            for path in includes:
                header_lines.append(f".include '{path}'")
        if header_lines:
            lines.extend(header_lines)
            lines.append("")  # Empty line after metadata/include

        # @variable declarations — usage sites (``@name`` references inside
        # rules) are already resolved to their literal value by the reader
        # (see parser.py's ``enterVariableDef``), so only the declaration
        # itself round-trips; re-emitting it is still strictly better than
        # dropping it, and lets a re-parse repopulate ``style.variables``.
        if style.variables:
            for var in style.variables:
                lines.append(f"@{var.name} = {self._format_variable_value(var.value)};")
            lines.append("")  # Empty line after variable declarations

        # Add only top-level rules; nested rules are emitted only within their parent
        for rule in style.styling_rules:
            lines.extend(self._rule_to_css(rule, emit_nested=True, indent=0))
            lines.append("")  # Empty line between rules

        return "\n".join(lines).strip()

    def _format_variable_value(self, value: Any) -> str:
        """Format a ``Variable.value`` for a ``@name = value;`` declaration.

        ``parser.py``'s ``enterVariableDef`` already reduces the RHS to a
        plain ``int``/``float``/``str`` (quotes stripped either way), so a
        quoted string round-trips to the same value as a bare one — quoting
        unconditionally here is the unambiguous, always-valid choice.
        """
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return f"'{value}'"

    def _rule_to_css(self, rule, emit_nested=True, indent=0) -> list:
        """Convert StylingRule model to CSS lines with pretty-print indentation."""
        lines = []
        pad = "    " * indent
        # Add rule comment if present
        if rule.comment:
            lines.append(f"{pad}/* {rule.comment} */")
        # Add selector
        if rule.selector:
            selector_str = self._selector_to_cscss(rule.selector)
            lines.append(f"{pad}{selector_str}")
        # Add symbolizer
        lines.append(f"{pad}{{")
        # Emit .name directive only when stylingRuleName is explicitly set
        if getattr(rule, "styling_rule_name", None):
            lines.append(f"{pad}    .name '{rule.styling_rule_name}'")
        if rule.symbolizer:
            for line in self._symbolizer_to_css(rule.symbolizer, indent=indent + 1):
                lines.append(f"{pad}    {line.lstrip()}")
        # Emit nested rules only within this block
        if emit_nested and getattr(rule, "nested_rules", None):
            for nested_rule in rule.nested_rules:
                lines.extend(
                    self._rule_to_css(nested_rule, emit_nested=True, indent=indent + 1)
                )
        lines.append(f"{pad}}}")
        return lines

    def _selector_to_cscss(self, selector) -> str:
        """Convert a selector (dict, list, or str) to a CSCSS selector string.

        Handles:
        - Landuse
        - Landuse[other filter]
        - [complex filter]
        """
        # Simple string selector
        if isinstance(selector, str):
            return selector
        # List of selectors (rare, but possible)
        if isinstance(selector, list):
            if len(selector) == 1 and isinstance(selector[0], dict):
                return self._selector_to_cscss(selector[0])
            return " ".join(self._selector_to_cscss(s) for s in selector)
        # Dict selector (expression)
        if isinstance(selector, dict):
            # Special case: simple dataLayer.id = value → emit bare identifier
            if (
                selector.get("op") == "="
                and isinstance(selector.get("args"), list)
                and len(selector["args"]) == 2
                and isinstance(selector["args"][0], dict)
                and selector["args"][0].get("sysId") == "dataLayer.id"
            ):
                id_val = selector["args"][1]
                if isinstance(id_val, dict) and "property" in id_val:
                    id_val = id_val["property"]
                id_str = str(id_val)
                if not id_str.replace("_", "").replace(".", "").isalnum():
                    id_str = f'"{id_str}"'
                return id_str
            # Special case: Landuse[filter] form (and-combined with dataLayer.id)
            if selector.get("op") == "and" and isinstance(selector.get("args"), list):
                args = selector["args"]
                id_arg = None
                other_args = []
                for arg in args:
                    if (
                        isinstance(arg, dict)
                        and arg.get("op") == "="
                        and isinstance(arg.get("args"), list)
                        and len(arg["args"]) == 2
                        and isinstance(arg["args"][0], dict)
                        and arg["args"][0].get("sysId") == "dataLayer.id"
                    ):
                        landuse_val = arg["args"][1]
                        if isinstance(landuse_val, dict) and "property" in landuse_val:
                            landuse_val = landuse_val["property"]
                        id_arg = landuse_val
                    else:
                        other_args.append(arg)
                if id_arg is not None:
                    # Quote the id if it contains special characters (e.g. hyphens)
                    id_str = str(id_arg)
                    if not id_str.replace("_", "").replace(".", "").isalnum():
                        id_str = f'"{id_str}"'
                    if other_args:
                        filter_str = (
                            self._format_selector_expr(other_args[0])
                            if len(other_args) == 1
                            else self._format_selector_expr(
                                {"op": "and", "args": other_args}
                            )
                        )
                        return f"{id_str}[{filter_str}]"
                    else:
                        return id_str
            # Otherwise, always reconstruct as a filter expression
            return f"[{self._format_selector_expr(selector)}]"
        # Fallback
        return str(selector)

    def _format_selector_expr(self, expr, _quote_bare_strings: bool = True) -> str:
        """Format a CQL2-JSON selector dict as a CSCSS filter string.

        Thin wrapper over :func:`pycartosym.cql2.to_text.expression_to_text`;
        the logic lives in the ``cql2`` package.
        """
        from .cql2.to_text import expression_to_text

        return expression_to_text(expr, _quote_bare_strings)

    def _geojson_to_wkt(self, geojson: dict) -> str:
        """Convert a GeoJSON geometry dict to WKT text (see ``cql2.to_text``)."""
        from .cql2.to_text import geojson_to_wkt

        return geojson_to_wkt(geojson)

    def _symbolizer_to_css(self, symbolizer, indent=1) -> list:
        """Convert Symbolizer model to CSS property lines."""
        lines = []
        # Core symbolizer properties
        if getattr(symbolizer, "visibility", None) is not None:
            lines.append(f"  visibility: {str(symbolizer.visibility).lower()};")
        if getattr(symbolizer, "opacity", None) is not None:
            lines.append(f"  opacity: {symbolizer.opacity};")
        # Support both z_order and zOrder
        zorder_val = getattr(symbolizer, "zOrder", None)
        if zorder_val is None:
            zorder_val = getattr(symbolizer, "z_order", None)
        if zorder_val is not None:
            lines.append(f"  zOrder: {zorder_val};")
        # Vector symbolizers
        if getattr(symbolizer, "fill", None):
            lines.extend(self._fill_to_css(symbolizer.fill))
        if getattr(symbolizer, "stroke", None):
            lines.extend(self._stroke_to_css(symbolizer.stroke))
        if getattr(symbolizer, "marker", None):
            lines.extend(self._marker_to_css(symbolizer.marker))
        if getattr(symbolizer, "label", None):
            lines.extend(self._label_to_css(symbolizer.label))
        # Coverage / raster symbolizer properties
        # Use explicit None-check (not `or`) to correctly handle 0 / 0.0 / False
        sc = getattr(symbolizer, "single_channel", None)
        if sc is None:
            sc = getattr(symbolizer, "singleChannel", None)
        if sc is not None:
            lines.append(f"  singleChannel: {self._channel_expr_to_css(sc)};")
        cc = getattr(symbolizer, "color_channels", None)
        if cc is None:
            cc = getattr(symbolizer, "colorChannels", None)
        if cc is not None:
            lines.append(f"  colorChannels: {self._channels_to_css(cc)};")
        ac = getattr(symbolizer, "alpha_channel", None)
        if ac is None:
            ac = getattr(symbolizer, "alphaChannel", None)
        if ac is not None:
            lines.append(f"  alphaChannel: {self._channel_expr_to_css(ac)};")
        cm = getattr(symbolizer, "color_map", None)
        if cm is None:
            cm = getattr(symbolizer, "colorMap", None)
        if cm is not None:
            lines.append(f"  colorMap: {self._color_map_to_css(cm)};")
        om = getattr(symbolizer, "opacity_map", None)
        if om is None:
            om = getattr(symbolizer, "opacityMap", None)
        if om is not None:
            lines.append(f"  opacityMap: {self._opacity_map_to_css(om)};")
        hs = getattr(symbolizer, "hill_shading", None)
        if hs is None:
            hs = getattr(symbolizer, "hillShading", None)
        if hs is not None:
            lines.extend(self._hill_shading_to_css(hs, sym_indent=indent))
        return lines

    def _channel_expr_to_css(self, expr) -> str:
        """Format a channel expression to CSCSS.

        The expression is a property-ref, an arithmetic expr, or a string.
        """
        if isinstance(expr, dict):
            if "property" in expr:
                return str(expr["property"])
            if "op" in expr:
                return self._arith_expr_to_css(expr)
        return str(expr)

    def _arith_expr_to_css(self, expr) -> str:
        """Recursively convert an arithmetic expression dict back to CSCSS string."""
        if isinstance(expr, dict):
            if "property" in expr:
                return str(expr["property"])
            if "op" in expr and "args" in expr:
                op = expr["op"]
                args = [self._arith_expr_to_css(a) for a in expr["args"]]
                if op in ("*", "/", "+", "-"):
                    left, right = args[0], args[1]
                    # Wrap sub-expressions in parens when needed to preserve precedence
                    return f"({left} {op} {right})"
                return " ".join([op] + args)
        if isinstance(expr, (int, float)):
            return str(expr)
        return str(expr)

    def _channels_to_css(self, channels) -> str:
        """Format colorChannels (list of property-refs or single expr) to CSCSS."""
        if isinstance(channels, list):
            return " ".join(self._channel_expr_to_css(c) for c in channels)
        return self._channel_expr_to_css(channels)

    def _color_entry_to_css(self, entry) -> str:
        """Format one colorMap entry [threshold, color] to CSCSS."""
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            threshold = entry[0]
            color = entry[1]
            if isinstance(color, (list, tuple)) and len(color) == 3:
                color_str = f"{int(color[0])} {int(color[1])} {int(color[2])}"
            elif isinstance(color, dict) and "r" in color:
                color_str = "{} {} {}".format(
                    int(color["r"]), int(color["g"]), int(color["b"])
                )
            else:
                color_str = self._format_color(color)
            return f"{threshold} {color_str}"
        return str(entry)

    def _color_map_to_css(self, color_map) -> str:
        """Format colorMap to CSCSS array syntax: [v1 r g b, v2 name, ...]."""
        if isinstance(color_map, list):
            entries = ", ".join(self._color_entry_to_css(e) for e in color_map)
            return f"[{entries}]"
        return str(color_map)

    def _opacity_map_to_css(self, opacity_map) -> str:
        """Format opacityMap to CSCSS array syntax: [v1 op1, v2 op2, ...]."""
        if isinstance(opacity_map, list):
            entries = []
            for e in opacity_map:
                if isinstance(e, (list, tuple)) and len(e) >= 2:
                    entries.append(f"{e[0]} {e[1]}")
                else:
                    entries.append(str(e))
            return "[" + ", ".join(entries) + "]"
        return str(opacity_map)

    def _hill_shading_to_css(self, hill_shading, sym_indent=1) -> list:
        """Format hillShading object to CSCSS property lines."""
        if not isinstance(hill_shading, dict):
            return []
        parts = []
        factor = hill_shading.get("factor")
        if factor is not None:
            parts.append(f"factor: {factor}")
        sun = hill_shading.get("sun")
        if sun and isinstance(sun, dict):
            sun_parts = "; ".join(f"{k}: {v}" for k, v in sun.items())
            parts.append(f"sun: {{{sun_parts}}}")
        cm = hill_shading.get("colorMap")
        if cm is not None:
            parts.append(f"colorMap: {self._color_map_to_css(cm)}")
        om = hill_shading.get("opacityMap")
        if om is not None:
            parts.append(f"opacityMap: {self._opacity_map_to_css(om)}")
        if not parts:
            return []
        # Multi-line block. The returned string has no leading whitespace on the
        # first line (caller does lstrip + re-indent). Continuation lines carry
        # absolute indentation: sym_indent levels for the closing }, and
        # sym_indent+1 levels for the inner properties.
        inner_pad = "    " * (sym_indent + 1)
        close_pad = "    " * sym_indent
        sep = ";\n" + inner_pad
        inner = sep.join(parts)
        return [f"hillShading: {{\n{inner_pad}{inner};\n{close_pad}}};"]

    def _marker_to_css(self, marker) -> list:
        """Convert Marker model to CSS lines.

        Two forms:
        * Normal list → ``marker: { elements: [ Type { ... }, ... ] };``
        * Indexed override → ``marker.elements[N]: Type { ... };``

        Raises:
            NotImplementedError: If ``position``/``opacity`` is set. The
                CartoSym-CSS grammar has no ``marker: { position: ...;
                opacity: ...; ... }`` syntax — only CS-JSON input can
                populate these two fields, and the AST's own ``Marker``
                dataclass doesn't even carry them, confirming there is no
                read-side counterpart to write back to.
        """
        lines: list[str] = []
        for field in ("position", "opacity"):
            if getattr(marker, field, None) is not None:
                raise NotImplementedError(
                    f"marker.{field}: not yet written back to CartoSym-CSS "
                    "(no grammar syntax for it)"
                )
        elements = getattr(marker, "elements", None)
        if not elements:
            return lines

        # ── Indexed override: marker.elements[N]: Type { ... } ────────────────
        if isinstance(elements, dict) and "index" in elements and "value" in elements:
            idx = elements["index"]
            el = elements["value"]
            lines.append(f"  marker.elements[{idx}]:")
            lines.append(f"     {self._graphic_element_to_css_block(el, indent=15)};")
            return lines

        # ── Normal list: marker: { elements: [ ... ] } ───────────────────────
        element_strs = []
        for el in (elements if isinstance(elements, list) else [elements]):
            element_strs.append(self._graphic_element_to_css_block(el, indent=15))
        elements_block = (
            "[\n                "
            + ",\n                ".join(element_strs)
            + "\n             ]"
        )
        lines.append(f"  marker: {{elements: {elements_block}}};")
        return lines

    def _label_to_css(self, label) -> list:
        """Convert Label model to CSS lines.

        Raises:
            NotImplementedError: If ``position``/``opacity`` is set —
                same reasoning as :meth:`_marker_to_css`'s own guard: no
                CartoSym-CSS grammar syntax reaches these two fields
                (confirmed empirically — parsing ``label: { position:
                ...; opacity: ...; elements: [...] }`` silently drops
                both rather than populating them).
        """
        lines: list[str] = []
        for field in ("position", "opacity"):
            if getattr(label, field, None) is not None:
                raise NotImplementedError(
                    f"label.{field}: not yet written back to CartoSym-CSS "
                    "(no grammar syntax for it)"
                )
        elements = getattr(label, "elements", None)
        placement = getattr(label, "placement", None)
        parts = []
        if elements:
            element_strs = [
                self._graphic_element_to_css_block(el, indent=15)
                for el in (elements if isinstance(elements, list) else [elements])
            ]
            elements_block = (
                "[\n                "
                + ",\n                ".join(element_strs)
                + "\n             ]"
            )
            parts.append(f"elements: {elements_block}")
        if placement is not None:
            placement_block = self._placement_to_css_block(placement)
            if placement_block is not None:
                parts.append(f"placement: {placement_block}")
        if not parts:
            return lines
        lines.append(f"  label: {{{'; '.join(parts)}}};")
        return lines

    def _placement_to_css_block(self, placement) -> str | None:
        """Render a ``LabelPlacement`` (``type``/``priority``/spacing) as CSCSS."""

        def _get(o, *keys):
            for k in keys:
                v = o.get(k) if isinstance(o, dict) else getattr(o, k, None)
                if v is not None:
                    return v
            return None

        parts = []
        placement_type = _get(placement, "placement_type", "type")
        if placement_type is not None:
            parts.append(f"type: {placement_type}")
        priority = _get(placement, "priority")
        if priority is not None:
            parts.append(f"priority: {self._format_unit_value(priority)}")
        min_spacing = _get(placement, "min_spacing", "minSpacing")
        if min_spacing is not None:
            parts.append(f"minSpacing: {self._format_unit_value(min_spacing)}")
        max_spacing = _get(placement, "max_spacing", "maxSpacing")
        if max_spacing is not None:
            parts.append(f"maxSpacing: {self._format_unit_value(max_spacing)}")
        if not parts:
            return None
        return "{" + "; ".join(parts) + "}"

    def _graphic_element_to_css_block(self, el, indent: int = 0) -> str:
        """Render a single graphic element as a CSS block, e.g. ``Dot { ... }``."""

        def _get(o, k):
            return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

        el_type = _get(el, "type") or "Graphic"
        pad = " " * indent
        inner_pad = " " * (indent + 3)

        prop_lines = []

        # alter (AlterMixin, every graphic element) — a bool from CS-JSON,
        # or the raw parsed string if _normalize_graphic_element's own
        # coercion was bypassed (e.g. a hand-built dict in a test).
        alter = _get(el, "alter")
        if alter is not None:
            alter_bool = alter if isinstance(alter, bool) else str(alter) == "true"
            prop_lines.append(f"alter: {str(alter_bool).lower()}")

        # position
        pos = _get(el, "position")
        if pos is not None:
            if hasattr(pos, "x") and hasattr(pos, "y"):
                prop_lines.append(
                    f"position: {self._format_axis_value(pos.x)} "
                    f"{self._format_axis_value(pos.y)}"
                )
            elif isinstance(pos, dict) and "x" in pos and "y" in pos:
                prop_lines.append(
                    f"position: {self._format_axis_value(pos['x'])} "
                    f"{self._format_axis_value(pos['y'])}"
                )

        # size (e.g. Dot.size)
        size = _get(el, "size")
        if size is not None:
            prop_lines.append(f"size: {self._format_unit_value(size)}")

        # color
        color = _get(el, "color")
        if color is not None:
            prop_lines.append(f"color: {self._format_color(color)}")

        # fill / outline (2-shapes Circle) — inline nested style objects
        for shape_key in ("fill", "outline"):
            sv = _get(el, shape_key)
            if isinstance(sv, dict) and sv:
                parts = []
                for k, v in sv.items():
                    if k == "color":
                        vf = self._format_color(v)
                    elif k == "thickness":
                        # unit value, or a numeric expression (e.g.
                        # viz.sd / 1000, OGC issue #115) — never a bare
                        # single-key-dict guess, which would misread an
                        # expression dict like {"sysId": "viz.sd"} as a
                        # {unit: value} shortcut.
                        vf = self._format_unit_value(v)
                    elif isinstance(v, dict) and len(v) == 1:
                        unit, val = next(iter(v.items()))
                        vf = f"{val} {unit}"
                    elif isinstance(v, bool):
                        vf = str(v).lower()
                    else:
                        vf = v
                    parts.append(f"{k}: {vf}")
                prop_lines.append(f"{shape_key}: {{{'; '.join(parts)}}}")

        # radius (2-shapes Circle, Arc/SectorArc/ChordArc)
        radius = _get(el, "radius")
        if radius is not None:
            prop_lines.append(f"radius: {self._format_unit_value(radius)}")

        # width / height (2-shapes RectangleGraphic)
        for size_key in ("width", "height"):
            size_val = _get(el, size_key)
            if size_val is not None:
                prop_lines.append(f"{size_key}: {self._format_unit_value(size_val)}")

        # startAngle / deltaAngle (2-shapes Arc/SectorArc/ChordArc)
        for angle_key in ("startAngle", "deltaAngle"):
            angle = _get(el, angle_key)
            if angle is not None:
                if isinstance(angle, dict) and len(angle) == 1:
                    unit, val = next(iter(angle.items()))
                    prop_lines.append(f"{angle_key}: {val} {unit}")
                else:
                    prop_lines.append(f"{angle_key}: {angle}")

        # center (2-shapes Circle, Arc/SectorArc/ChordArc)
        center = _get(el, "center")
        if center is not None:
            if hasattr(center, "x") and hasattr(center, "y"):
                prop_lines.append(
                    f"center: {self._format_axis_value(center.x)} "
                    f"{self._format_axis_value(center.y)}"
                )
            elif isinstance(center, dict) and "x" in center and "y" in center:
                prop_lines.append(
                    f"center: {self._format_axis_value(center['x'])} "
                    f"{self._format_axis_value(center['y'])}"
                )

        # text — property ref → bare identifier; plain string → quoted
        text = _get(el, "text")
        if text is not None:
            if isinstance(text, dict) and "property" in text:
                prop_lines.append(f"text: {text['property']}")
            elif isinstance(text, str):
                prop_lines.append(f"text: '{text}'")
            else:
                prop_lines.append(f"text: {text}")

        # alignment
        alignment = _get(el, "alignment")
        if alignment is not None:
            if isinstance(alignment, list) and len(alignment) == 2:
                prop_lines.append(f"alignment: {alignment[0]} {alignment[1]}")
            elif isinstance(alignment, dict) and alignment:
                vals = list(alignment.values())
                prop_lines.append(f"alignment: {' '.join(str(v) for v in vals)}")
            # empty dict — emit nothing (no information to preserve)

        # position2D
        pos2d = _get(el, "position2D") or _get(el, "position_2d")
        if pos2d is not None:
            if isinstance(pos2d, dict) and pos2d:
                vals = list(pos2d.values())
                prop_lines.append(f"position2D: {' '.join(str(v) for v in vals)}")
            elif isinstance(pos2d, list) and len(pos2d) == 2:
                prop_lines.append(f"position2D: {pos2d[0]} {pos2d[1]}")
            # empty dict — emit nothing (no information to preserve)

        # font
        font = _get(el, "font")
        if font is not None:
            if isinstance(font, dict):
                fp = []
                for k, v in font.items():
                    if k == "face" and isinstance(v, str):
                        fv = f"'{v}'"
                    elif k == "color":
                        fv = self._format_color(v)
                    elif k == "size":
                        # unit value, bare number, or a numeric expression
                        # (e.g. viz.sd / 1000, OGC issue #115).
                        fv = self._format_unit_value(v)
                    elif k == "outline" and isinstance(v, dict):
                        # Serialize outline as CSCSS inline object: {key: val; ...}
                        out_parts = []
                        for ok, ov in v.items():
                            if ok == "color":
                                ovf = self._format_color(ov)
                            elif isinstance(ov, bool):
                                ovf = str(ov).lower()
                            else:
                                ovf = ov
                            out_parts.append(f"{ok}: {ovf}")
                        fv = "{" + "; ".join(out_parts) + "}"
                    elif isinstance(v, bool):
                        fv = str(v).lower()
                    else:
                        fv = v
                    fp.append(f"{k}: {fv}")
                font_inner = (";\n" + inner_pad + "   ").join(fp)
                prop_lines.append(
                    f"font: {{\n{inner_pad}   {font_inner};\n{inner_pad}}}"
                )
            else:
                prop_lines.append(f"font: {font}")

        # image resource (Image type)
        image = _get(el, "image")
        if image is not None:
            res_parts = []
            for k in ("uri", "path", "id", "type", "ext", "sprite"):
                v = _get(image, k)
                if v is not None:
                    res_parts.append(f"{k}: '{v}'")
            if res_parts:
                prop_lines.append(f"image: {{{'; '.join(res_parts)}}}")

        # hotSpot — list of {unit: val} → "val unit val unit ..."
        hot_spot = _get(el, "hotSpot") or _get(el, "hot_spot")
        if hot_spot is not None:
            if isinstance(hot_spot, list):
                parts = []
                for item in hot_spot:
                    if isinstance(item, dict) and len(item) == 1:
                        unit, val = next(iter(item.items()))
                        parts.append(f"{val} {unit}")
                    elif hasattr(item, "value") and hasattr(item, "unit"):
                        parts.append(f"{item.value} {item.unit}")
                    else:
                        parts.append(str(item))
                prop_lines.append(f"hotSpot: {' '.join(parts)}")
            else:
                prop_lines.append(f"hotSpot: {hot_spot}")

        # tint / blackTint / alphaThreshold
        tint = _get(el, "tint")
        if tint is not None:
            prop_lines.append(f"tint: {tint}")

        black_tint = _get(el, "blackTint") or _get(el, "black_tint")
        if black_tint is not None:
            prop_lines.append(f"blackTint: {black_tint}")

        alpha_threshold = _get(el, "alphaThreshold") or _get(el, "alpha_threshold")
        if alpha_threshold is not None:
            prop_lines.append(f"alphaThreshold: {alpha_threshold}")

        # opacity — the element's own AbstractGraphic.opacity, independent
        # of any font block. Only suppressed if *font itself* already
        # carries its own "opacity" key (an actual duplicate to avoid, per
        # a font sub-block that has one) — not merely because a font block
        # was emitted at all, which used to drop a genuine, unrelated
        # element opacity whenever a font was also present.
        opacity = _get(el, "opacity")
        font_has_own_opacity = isinstance(font, dict) and "opacity" in font
        if opacity is not None and not font_has_own_opacity:
            prop_lines.append(f"opacity: {opacity}")

        body = (";\n" + inner_pad).join(prop_lines)
        if prop_lines:
            body += ";"
        return f"{el_type} {{\n{inner_pad}{body}\n{pad}}}"

    def _format_color(self, color) -> str:
        """Format a color value for CSCSS output.

        - [r, g, b] integer array → '#rrggbb' hex
        - {r, g, b} object → '#rrggbb' hex
        - named color string → as-is
        """
        if isinstance(color, list) and len(color) == 3:
            try:
                return f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}"
            except (TypeError, ValueError):
                pass
        if isinstance(color, dict) and all(k in color for k in ("r", "g", "b")):
            try:
                return "#{:02x}{:02x}{:02x}".format(
                    int(color["r"]), int(color["g"]), int(color["b"])
                )
            except (TypeError, ValueError):
                pass
        return str(color)

    def _format_numeric_expression(self, value) -> str | None:
        """Render a system identifier / arithmetic expression as CartoSym-CSS text.

        E.g. ``viz.sd / 1000``. Returns ``None`` if ``value`` isn't one of
        these (a plain unit value/number instead).
        """

        def _get(o, k):
            return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

        sys_id = _get(value, "sysId")
        if sys_id is not None:
            return str(sys_id)
        prop = _get(value, "property")
        if prop is not None:
            return str(prop)
        op = _get(value, "op")
        args = _get(value, "args")
        if op is not None and args is not None:
            parts = [self._format_numeric_expression(a) or str(a) for a in args]
            return f"{parts[0]} {op} {parts[1]}"
        return None

    def _format_axis_value(self, v) -> str:
        """Format one ``UnitPoint`` coordinate: a number, or a bare property.

        A property reference (``{"property": "sd"}`` / ``PropertyRef``)
        formats as its identifier, unquoted — mirrors
        ``models/symbolizers.py::UnitPoint``'s own coordinate parsing (see
        that module for why arithmetic/system-identifier coordinates are
        out of scope here).
        """
        if isinstance(v, dict) and "property" in v:
            return str(v["property"])
        if hasattr(v, "property"):
            return str(v.property)
        return str(v)

    def _format_unit_value(self, uv) -> str:
        """Format a UnitValue as CSCSS syntax, e.g. '2.0 px'.

        Also accepts a ``{unit: val}`` dict, or a numeric expression (e.g.
        ``viz.sd / 1000``).
        """
        expr = self._format_numeric_expression(uv)
        if expr is not None:
            return expr
        if hasattr(uv, "value") and hasattr(uv, "unit"):
            unit_str = uv.unit.value if hasattr(uv.unit, "value") else str(uv.unit)
            return f"{uv.value} {unit_str}"
        if isinstance(uv, dict) and len(uv) == 1:
            unit, val = next(iter(uv.items()))
            return f"{val} {unit}"
        return str(uv)

    def _format_angle_value(self, v) -> str:
        """Format an Angle/FlexibleAngle as a bare CartoSym-CSS number.

        The grammar's ``UNIT`` token has no angle unit (no ``deg``/``rad``)
        — an angle can only be written as a unitless number, which
        ``FlexibleAngle`` itself already treats as "assumed degrees". A
        radian ``Angle`` can't be represented without silently changing
        its unit tag, so that raises instead.

        Raises:
            NotImplementedError: If ``v`` is an ``Angle`` in radians.
        """
        expr = self._format_numeric_expression(v)
        if expr is not None:
            return expr
        if hasattr(v, "value") and hasattr(v, "unit"):
            unit = v.unit.value if hasattr(v.unit, "value") else str(v.unit)
            if unit not in ("deg", "degrees"):
                raise NotImplementedError(
                    f"angle unit {unit!r}: only degrees are representable "
                    "in CartoSym-CSS (no angle-unit grammar token)"
                )
            return str(v.value)
        return str(v)

    def _fill_pattern_block(self, obj, field_formatters: dict) -> str:
        """Render a Hatch/DotPattern/Stipple sub-object as a ``{...}`` block."""

        def _get(o, k):
            return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

        parts = []
        for field, formatter in field_formatters.items():
            v = _get(obj, field)
            if v is not None:
                parts.append(f"{field}: {formatter(v)}")
        return "{" + "; ".join(parts) + "}"

    def _fill_to_css(self, fill) -> list:
        """Convert Fill model to CSS lines, including pattern fills.

        Raises:
            NotImplementedError: If a pattern field (``hatch``/
                ``dotpattern``/``stipple``/``pattern``) is combined with
                ``alter`` — there is no ``fill.hatch: ...`` dot-notation
                grammar syntax, only the compound ``fill: {...}`` block
                form used below (same restriction color/opacity already
                have in alter mode).
        """

        def _get(o, k):
            return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

        color = getattr(fill, "color", None)
        opacity = getattr(fill, "opacity", None)
        is_alter = getattr(fill, "alter", None)
        hatch = _get(fill, "hatch")
        dotpattern = _get(fill, "dotpattern")
        stipple = _get(fill, "stipple")
        pattern = _get(fill, "pattern")

        if is_alter:
            for value, name in (
                (hatch, "hatch"),
                (dotpattern, "dotpattern"),
                (stipple, "stipple"),
                (pattern, "pattern"),
            ):
                if value is not None:
                    raise NotImplementedError(
                        f"fill.{name}: not yet written back to CartoSym-CSS "
                        "in alter mode (no dot-notation grammar syntax for it)"
                    )
            lines = []
            if color is not None:
                lines.append(f"  fill.color: {self._format_color(color)};")
            if opacity is not None:
                lines.append(f"  fill.opacity: {opacity};")
            return lines

        # Normal mode: always use a compound block to avoid injecting
        # alter on re-parse
        parts = []
        if color is not None:
            parts.append(f"color: {self._format_color(color)}")
        if opacity is not None:
            parts.append(f"opacity: {opacity}")
        if hatch is not None:
            block = self._fill_pattern_block(
                hatch,
                {
                    "width": self._format_unit_value,
                    "angle": self._format_angle_value,
                    "distance": self._format_unit_value,
                },
            )
            parts.append(f"hatch: {block}")
        if dotpattern is not None:
            block = self._fill_pattern_block(
                dotpattern, {"distance": self._format_unit_value}
            )
            parts.append(f"dotpattern: {block}")
        if stipple is not None:
            block = self._fill_pattern_block(
                stipple, {"ratio": self._format_unit_value}
            )
            parts.append(f"stipple: {block}")
        if pattern is not None:
            parts.append(f"pattern: {self._graphic_element_to_css_block(pattern)}")

        if not parts:
            return []
        return [f"  fill: {{{'; '.join(parts)}}};"]

    def _stroke_to_css(self, stroke) -> list:
        """Convert Stroke model to CSS lines.

        Raises:
            NotImplementedError: If the stroke carries casing, a center
                line, a dash pattern, a pattern graphic, or an explicit
                cap/join. The CartoSym-CSS grammar has no syntax for any
                of these yet (only CS-JSON/SLD input can populate them);
                dropping them silently would break the lossless guarantee
                (same reasoning as :meth:`_fill_to_css`'s pattern-graphic
                guard).
        """

        def _get(o, attr, alias):
            if isinstance(o, dict):
                return o.get(alias, o.get(attr))
            return getattr(o, attr, None)

        for attr, alias in (
            ("casing", "casing"),
            ("center_line", "centerLine"),
            ("dash_pattern", "dashPattern"),
            ("pattern", "pattern"),
            ("cap", "cap"),
            ("join", "join"),
        ):
            if _get(stroke, attr, alias) is not None:
                raise NotImplementedError(
                    f"stroke.{alias}: not yet written back to CartoSym-CSS "
                    "(no grammar syntax for it)"
                )

        color = getattr(stroke, "color", None)
        width = getattr(stroke, "width", None)
        opacity = getattr(stroke, "opacity", None)
        is_alter = getattr(stroke, "alter", None)

        if is_alter:
            # Alter mode: use dot-notation
            lines = []
            if color is not None:
                lines.append(f"  stroke.color: {self._format_color(color)};")
            if width is not None:
                lines.append(f"  stroke.width: {self._format_unit_value(width)};")
            if opacity is not None:
                lines.append(f"  stroke.opacity: {opacity};")
            return lines

        # Normal mode: always use compound block to avoid injecting alter on re-parse
        set_props = sum(1 for v in (color, width, opacity) if v is not None)
        if set_props > 0:
            parts = []
            if color is not None:
                parts.append(f"color: {self._format_color(color)}")
            if width is not None:
                parts.append(f"width: {self._format_unit_value(width)}")
            if opacity is not None:
                parts.append(f"opacity: {opacity}")
            return [f"  stroke: {{{'; '.join(parts)}}};"]

        return []

    def _fix_unit_values(self, data):
        """Fix this node's own unit-value shape in place, if any.

        Converts a ``{"value": v, "unit": u}`` dict to the schema's
        ``{u: v}`` form, or a raw ``"8.0 m"`` string on a known
        unit-bearing key to that same ``{unit: value}`` form. No longer
        recurses — :meth:`_postprocess_csjson` owns the tree traversal.
        """
        # Check if this looks like a unit value with value/unit structure
        if "value" in data and "unit" in data and len(data) == 2:
            # This is a unit value that should be converted to {unit: value} format
            value = data["value"]
            unit = data["unit"]
            # A UnitValue nested under an Any-typed field (e.g.
            # Marker.elements) reaches here as {"value": v, "unit": <enum>}
            # — Pydantic's own model_dump() doesn't invoke UnitValue's
            # model_dump() override (a plain Python method, not a
            # @model_serializer) for a nested-under-Any instance, so the
            # raw UnitType enum member leaks through instead of its "px"
            # string. Unwrap it before using it as the dict key.
            if hasattr(unit, "value"):
                unit = unit.value
            # Replace the dict contents with the correct format
            data.clear()
            data[unit] = value
            return

        # Check for string values that should be unit values
        # Common properties that should have unit values
        unit_properties = [
            "width",
            "height",
            "size",
            "radius",
            "thickness",
            "distance",
            "spacing",
            "startAngle",
            "deltaAngle",
        ]
        for key, value in list(data.items()):
            if key in unit_properties and isinstance(value, str):
                # Try to parse "value unit" format like "8.0 m"
                converted = self._parse_unit_string(value)
                if converted is not None:
                    data[key] = converted

    def _parse_unit_string(self, value_str: str):
        """Parse a string like '8.0 m' or '5 px' into {unit: value} format."""
        if not isinstance(value_str, str):
            return None

        parts = value_str.strip().split()
        if len(parts) == 2:
            try:
                # Parse the numeric value
                num_value = float(parts[0]) if "." in parts[0] else int(parts[0])
                unit = parts[1]
                # Valid units according to JSON schema
                valid_units = ["px", "mm", "cm", "in", "pt", "em", "pc", "m", "ft"]
                if unit in valid_units:
                    return {unit: num_value}
            except ValueError:
                pass
        return None
