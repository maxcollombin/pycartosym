"""AST to Pydantic converter for CartoSym CSS.

This module converts ANTLR-generated AST nodes to Pydantic models.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .ast import StyleSheet as AstStyleSheet
from .ast import StylingRule as AstStylingRule
from .cql2.to_json import (
    convert_literal_value,
    convert_numeric_expression_value,
    expression_to_json,
    post_process_selector,
)
from .models import (
    ArithmeticExpression,
    Fill,
    Label,
    Marker,
    Metadata,
    PropertyRef,
    Stroke,
    Style,
    StylingRule,
    Symbolizer,
    SystemIdentifier,
    UnitValue,
)

logger = logging.getLogger(__name__)


def _strip_inline_comment(s: str) -> str:
    """Strip a ``//`` line comment from *s*, outside quoted string literals.

    Quoted literals are skipped so URLs like ``'http://...'`` stay intact.
    """
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in ("'", '"'):
            quote = ch
            result.append(ch)
            i += 1
            while i < len(s) and s[i] != quote:
                result.append(s[i])
                i += 1
            if i < len(s):
                result.append(s[i])
                i += 1
        elif ch == "/" and i + 1 < len(s) and s[i + 1] == "/":
            break
        else:
            result.append(ch)
            i += 1
    return "".join(result).rstrip()


def _parse_resource_string(inner: str) -> dict:
    """Parse ``uri: 'val'; path: 'val'; ...`` content into a resource dict.

    Operates on the text inside ``{}`` and strips surrounding quotes from
    each value.
    """
    result = {}
    for part in inner.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, _, value = part.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key:
                result[key] = value
    return result


def _parse_hotspot_string(s: str) -> Any:
    """Convert ``'N unit N unit'`` (e.g. ``'50 pc 50 pc'``) to a unitPoint array.

    Produces ``[{unit: N}, {unit: N}]`` as expected by the CS-JSON schema.
    """
    parts = s.strip().split()
    if len(parts) == 4:
        try:
            x_val = float(parts[0]) if "." in parts[0] else int(parts[0])
            x_unit = parts[1]
            y_val = float(parts[2]) if "." in parts[2] else int(parts[2])
            y_unit = parts[3]
            return [{x_unit: x_val}, {y_unit: y_val}]
        except (ValueError, IndexError):
            pass
    elif len(parts) == 2:
        try:
            return [int(parts[0]), int(parts[1])]
        except ValueError:
            pass
    return s  # keep as-is if unparseable


def _parse_nested_props(props_str: str) -> dict:
    """Brace-aware CSS property parser (mirrors parser._parse_element_props)."""
    props = {}
    parts = []
    current = ""
    depth = 0
    for char in props_str:
        if char == "{":
            depth += 1
            current += char
        elif char == "}":
            if depth > 0:
                depth -= 1
                current += char
            else:
                break
        elif char in (";", ",") and depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    for part in parts:
        if "//" in part:
            part = _strip_inline_comment(part)
        if not part:
            continue
        if ":" in part:
            colon_idx = part.index(":")
            key = part[:colon_idx].strip()
            value = part[colon_idx + 1 :].strip()
            if key:
                props[key] = value
    return props


def _parse_color_value(v: str):
    """Convert a color string to schema-valid form.

    Hex ``#rrggbb`` or ``#rgb`` → ``[r, g, b]``; web colour names kept as-is.
    """
    if isinstance(v, str) and v.startswith("#") and len(v) in (4, 7):
        hex_str = v[1:]
        if len(hex_str) == 3:
            hex_str = "".join(c * 2 for c in hex_str)
        try:
            return list(bytes.fromhex(hex_str))
        except ValueError:
            pass
    return v


def _coerce_font_dict(font: dict) -> None:
    """Coerce font dict string values to proper Python types in-place.

    Handles size → int/float (or a numeric expression), bold/italic/
    underline → bool, opacity → float, color → parsed color, outline →
    parsed sub-dict.
    """
    ctx_map = font.pop("_expr_ctx", {})
    for k in list(font.keys()):
        v = font[k]
        if not isinstance(v, str):
            # Already coerced (or a sub-dict like outline that needs its own pass)
            if k == "outline" and isinstance(v, dict):
                _coerce_outline_dict(v)
            continue
        v = v.strip().strip("'\"")
        if k == "size":
            font[k] = _coerce_unit_scalar(v, ctx_map.get(k))
        elif k in ("bold", "italic", "underline"):
            font[k] = v.lower() == "true"
        elif k == "opacity":
            try:
                font[k] = float(v)
            except ValueError:
                font[k] = v
        elif k == "color":
            font[k] = _parse_color_value(v)
        elif k == "outline" and v.startswith("{") and v.endswith("}"):
            outline_raw = _parse_nested_props(v[1:-1])
            outline_dict = {
                ok: ov.strip().strip("'\"") for ok, ov in outline_raw.items()
            }
            _coerce_outline_dict(outline_dict)
            font[k] = outline_dict
        else:
            font[k] = v


def _coerce_outline_dict(outline: dict) -> None:
    """Coerce outline dict string values to proper Python types in-place."""
    outline.pop("_expr_ctx", None)
    for k in list(outline.keys()):
        v = outline[k]
        if not isinstance(v, str):
            continue
        v = v.strip().strip("'\"")
        if k == "size":
            try:
                outline[k] = int(v)
            except ValueError:
                try:
                    outline[k] = float(v)
                except ValueError:
                    outline[k] = v
        elif k == "opacity":
            try:
                outline[k] = float(v)
            except ValueError:
                outline[k] = v
        elif k == "color":
            outline[k] = _parse_color_value(v)
        else:
            outline[k] = v


def _coerce_unit_scalar(v: str, expr_ctx: Any = None):
    """Coerce a CSCSS scalar such as ``"5"``, ``"5 px"`` or ``"2.5 mm"``.

    Returns a bare number for a unit-less value, a ``{unit: value}`` dict
    when a unit suffix is present, or the original string if unparseable.

    When *expr_ctx* (the leaf's ANTLR expression context, threaded through
    by :meth:`parser.CartoSymStyleSheetListener._extract_element_from_instance`)
    is given and plain literal/unit parsing doesn't consume the whole
    value (e.g. ``"viz.sd / 1000"``), falls back to
    :func:`convert_numeric_expression_value` instead of leaving an opaque
    string — the same numeric-expression parsing already used for
    ``stroke.width`` (OGC issue #115).
    """
    if not isinstance(v, str):
        return v
    parts = v.strip().split()
    if len(parts) == 1:
        try:
            return int(parts[0])
        except ValueError:
            try:
                return float(parts[0])
            except ValueError:
                pass
    elif len(parts) == 2:
        try:
            num = float(parts[0])
        except ValueError:
            pass
        else:
            num = int(num) if num.is_integer() else num
            return {parts[1]: num}
    if expr_ctx is not None:
        return convert_numeric_expression_value(v, expr_ctx)
    return v


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _coerce_axis_value(p: str):
    """One coordinate token: a number, or a bare property-name identifier.

    E.g. ``sd`` in ``center: sd 3``, as a ``PropertyRef`` dict — see
    ``models/symbolizers.py``'s identically-named helper for why
    arithmetic/system-identifier coordinates are out of scope here.
    """
    try:
        return int(p)
    except ValueError:
        pass
    try:
        return float(p)
    except ValueError:
        pass
    if _IDENTIFIER_RE.match(p):
        return {"property": p}
    return None


def _parse_xy(v: str):
    """``"10 -4"`` / ``"{ 10, -4 }"`` → ``{"x": 10, "y": -4}``; ``None`` otherwise."""
    if not isinstance(v, str):
        return None
    raw = v.strip()
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1]
    parts = [p.strip() for p in raw.replace(",", " ").split() if p.strip()]
    if len(parts) != 2:
        return None
    coords: list = []
    for p in parts:
        coord = _coerce_axis_value(p)
        if coord is None:
            return None
        coords.append(coord)
    return {"x": coords[0], "y": coords[1]}


def _coerce_shape_style_dict(d: dict) -> None:
    """Coerce a ``2-shapes`` ``Circle``'s ``fill`` / ``outline`` sub-dict in-place.

    ``color`` → ``[r, g, b]`` / name, ``opacity`` → float,
    ``thickness`` / ``radius`` → unit scalar (or numeric expression),
    ``alter`` → bool.
    """
    ctx_map = d.pop("_expr_ctx", {})
    for k in list(d.keys()):
        v = d[k]
        if not isinstance(v, str):
            continue
        v = v.strip().strip("'\"")
        if k == "color":
            d[k] = _parse_color_value(v)
        elif k == "opacity":
            try:
                d[k] = float(v)
            except ValueError:
                d[k] = v
        elif k in ("thickness", "radius"):
            d[k] = _coerce_unit_scalar(v, ctx_map.get(k))
        elif k == "alter":
            d[k] = v.lower() == "true"
        else:
            d[k] = v


def _normalize_graphic_element(el: dict) -> None:
    """Normalise a graphic-element dict in-place to match the CartoSym JSON schema.

    Handles:
    * ``opacity`` / ``bold`` / ``italic`` strings → proper Python types
    * ``alignment: "left middle"`` → ``["left", "middle"]`` array
    * ``font: "{ face: 'Arial'; size: 12; ... }"`` string → proper dict
    """
    if not isinstance(el, dict):
        return

    ctx_map = el.pop("_expr_ctx", {})

    # Convert opacity string to float for any element type
    if "opacity" in el and isinstance(el["opacity"], str):
        try:
            el["opacity"] = float(el["opacity"])
        except ValueError:
            pass

    # Convert alter string to bool for any element type — every graphic
    # element inherits AlterMixin's alter: bool | None (models/symbolizers.py).
    if "alter" in el and isinstance(el["alter"], str):
        el["alter"] = el["alter"].strip().strip("'\"").lower() == "true"

    # Convert size string to a number, or a {unit: value} dict when a unit
    # suffix is present (e.g. a Dot's `size: 10 px`) — same coercion as
    # `radius` below, for any element type (shapes don't get the
    # font/outline-specific coercion below).
    if "size" in el and isinstance(el["size"], str):
        el["size"] = _coerce_unit_scalar(el["size"], ctx_map.get("size"))

    # position2D / position_2d (CSCSS syntax) → the schema's `position`
    # field (a UnitPoint): "{ 10, -4 }" → {x: 10, y: -4}
    for pos_key in ("position2D", "position_2d"):
        if pos_key in el and isinstance(el[pos_key], str):
            raw = el.pop(pos_key).strip()
            if raw.startswith("{") and raw.endswith("}"):
                raw = raw[1:-1]
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if len(parts) == 2:
                coords: list = []
                for p in parts:
                    try:
                        coords.append(int(p))
                    except ValueError:
                        try:
                            coords.append(float(p))
                        except ValueError:
                            coords.append(p)
                el["position"] = {"x": coords[0], "y": coords[1]}
        else:
            el.pop(pos_key, None)

    el_type = el.get("type", "")

    if el_type == "Text":
        # text: NAME (unquoted identifier) → {"property": "NAME"} property reference
        # text: 'literal' (quoted)         → strip quotes, keep as plain string
        if "text" in el and isinstance(el["text"], str):
            t = el["text"].strip()
            if (t.startswith("'") and t.endswith("'")) or (
                t.startswith('"') and t.endswith('"')
            ):
                el["text"] = t[1:-1]  # strip quotes → literal string
            else:
                # bare identifier → property reference
                el["text"] = {"property": t}

        # alignment: "left middle"  OR  { left, middle }  → ["left", "middle"]
        if "alignment" in el and isinstance(el["alignment"], str):
            a = el["alignment"].strip()
            if a.startswith("{") and a.endswith("}"):
                # { left, middle } block syntax
                parts = [p.strip() for p in a[1:-1].split(",") if p.strip()]
            else:
                parts = a.split()
            if len(parts) == 2:
                el["alignment"] = parts

        # font: "{ face: 'Arial'; ... }" → proper dict
        if "font" in el and isinstance(el["font"], str):
            font_str = el["font"].strip()
            # Strip outer braces if present
            if font_str.startswith("{") and font_str.endswith("}"):
                font_inner = font_str[1:-1]
            else:
                font_inner = font_str
            font_raw = _parse_nested_props(font_inner)
            font_dict: dict = {}
            for k, v in font_raw.items():
                v = v.strip().strip("'\"")
                font_dict[k] = v
            el["font"] = font_dict

        # Coerce font dict value types (size → int/float, bold/italic → bool, etc.)
        if "font" in el and isinstance(el["font"], dict):
            _coerce_font_dict(el["font"])

    elif el_type == "Image":
        # Convert image resource string "{uri: '...'; path: '...'; ...}" to a
        # proper resource dict as required by the schema.
        if "image" in el and isinstance(el["image"], str):
            img_str = el["image"].strip()
            if img_str.startswith("{") and img_str.endswith("}"):
                resource = _parse_resource_string(img_str[1:-1])
                if resource:
                    el["image"] = resource
        # Convert hotSpot string "N unit N unit" → [{unit: N}, {unit: N}]
        if "hotSpot" in el and isinstance(el["hotSpot"], str):
            el["hotSpot"] = _parse_hotspot_string(el["hotSpot"])
        # Convert alphaThreshold string → float
        if "alphaThreshold" in el and isinstance(el["alphaThreshold"], str):
            try:
                el["alphaThreshold"] = float(el["alphaThreshold"])
            except ValueError:
                pass

    # Shape graphics (2-shapes Circle, Arc/SectorArc/ChordArc, ...): fill /
    # outline are nested style objects, radius/startAngle/deltaAngle are
    # unit-bearing scalars, center is a point. These keys are
    # element-type-agnostic here — a Dot never carries them.
    if isinstance(el.get("fill"), dict):
        _coerce_shape_style_dict(el["fill"])
    if isinstance(el.get("outline"), dict):
        _coerce_shape_style_dict(el["outline"])
    if isinstance(el.get("radius"), str):
        el["radius"] = _coerce_unit_scalar(el["radius"], ctx_map.get("radius"))
    for angle_key in ("startAngle", "deltaAngle"):
        if isinstance(el.get(angle_key), str):
            el[angle_key] = _coerce_unit_scalar(el[angle_key], ctx_map.get(angle_key))
    # RectangleGraphic (Part 2 abstractShape): width/height, unit-bearing
    # scalars like radius above — previously left as an uncoerced raw
    # string ("5 px"), never valid against the schema's numericExpression/
    # unitValue shape.
    for size_key in ("width", "height"):
        if isinstance(el.get(size_key), str):
            el[size_key] = _coerce_unit_scalar(el[size_key], ctx_map.get(size_key))
    if isinstance(el.get("center"), str):
        pt = _parse_xy(el["center"])
        if pt is not None:
            el["center"] = pt

    # Strip empty dicts that carry no information (parser artifact for
    # brace-enclosed comma-separated values it cannot fully parse)
    if isinstance(el.get("alignment"), dict) and len(el["alignment"]) == 0:
        del el["alignment"]

    # Defensive cleanup: any nested-object sub-dict not otherwise consumed
    # above (e.g. `image`) still carries its own "_expr_ctx" companion map
    # from `_extract_element_from_instance` — strip it so it never leaks
    # into the final CS-JSON output. `font`/`fill`/`outline` already pop
    # their own above; re-popping here is a harmless no-op for those.
    for v in el.values():
        if isinstance(v, dict):
            v.pop("_expr_ctx", None)


class AstToPydanticConverter:
    """Converts ANTLR AST nodes to Pydantic models."""

    def convert_stylesheet(self, ast_stylesheet: AstStyleSheet) -> Style:
        """Convert AST StyleSheet to Pydantic Style model.

        Nested rules are preserved only as children.
        """
        try:
            # Convert metadata
            metadata = None
            if ast_stylesheet.metadata:
                metadata_dict: dict[str, Any] = {}
                _list_fields = {"keywords", "authors", "geoDataClasses"}
                _multiline_fields = {"abstract", "description", "title"}
                for meta in ast_stylesheet.metadata:
                    if not (hasattr(meta, "key") and hasattr(meta, "value")):
                        continue
                    key, value = meta.key, meta.value
                    if key in _list_fields:
                        if isinstance(value, str):
                            items = [v.strip() for v in value.split(",") if v.strip()]
                        elif isinstance(value, list):
                            items = value
                        else:
                            items = [str(value)]
                        existing = metadata_dict.get(key, [])
                        metadata_dict[key] = existing + items
                    elif key in _multiline_fields and key in metadata_dict:
                        metadata_dict[key] = metadata_dict[key] + "\n" + value
                    else:
                        metadata_dict[key] = value
                if metadata_dict:
                    metadata = Metadata(**metadata_dict)

            # Convert variables (if present)
            variables = None
            if hasattr(ast_stylesheet, "variables") and ast_stylesheet.variables:
                from .models.styles import Variable

                variables = [
                    Variable(name=v.name, value=v.value, type=getattr(v, "type", None))
                    for v in ast_stylesheet.variables
                ]

            # Build variable lookup and resolve references in the AST
            # before Pydantic model validation
            var_lookup = {}
            if hasattr(ast_stylesheet, "variables") and ast_stylesheet.variables:
                for v in ast_stylesheet.variables:
                    var_lookup[v.name] = v.value

            # Convert only top-level styling rules (do not flatten nested rules)
            styling_rules = []
            if ast_stylesheet.styling_rules and hasattr(
                ast_stylesheet.styling_rules, "rules"
            ):
                for ast_rule in ast_stylesheet.styling_rules.rules:
                    if var_lookup:
                        self._resolve_ast_variables(ast_rule, var_lookup)
                    pydantic_rule = self._convert_styling_rule(ast_rule)
                    if pydantic_rule:
                        styling_rules.append(pydantic_rule)

            style = Style(
                metadata=metadata, styling_rules=styling_rules, variables=variables
            )

            return style
        except Exception as e:
            raise ValueError(f"Failed to convert AST stylesheet: {e}") from e

    def _resolve_ast_variables(self, ast_node, var_lookup: dict):
        """Recursively resolve ``@variable`` references before model conversion.

        Walks all attributes of the AST node. String values like
        ``"@baseColor"`` are replaced with the variable's value.  The
        resolved value is coerced to int/float when appropriate.
        """
        if ast_node is None:
            return

        def _resolve_value(v):
            if isinstance(v, str) and v.startswith("@"):
                var_name = v[1:]
                if var_name in var_lookup:
                    return var_lookup[var_name]
            return v

        # Walk all attributes of the AST node
        for attr_name in list(vars(ast_node).keys()):
            val = getattr(ast_node, attr_name, None)
            if val is None:
                continue
            if isinstance(val, str):
                resolved = _resolve_value(val)
                if resolved is not val:
                    setattr(ast_node, attr_name, resolved)
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    if isinstance(item, str):
                        resolved = _resolve_value(item)
                        if resolved is not item:
                            val[i] = resolved
                    elif hasattr(item, "__dict__"):
                        self._resolve_ast_variables(item, var_lookup)
            elif isinstance(val, dict):
                for k in list(val.keys()):
                    v = val[k]
                    if isinstance(v, str):
                        resolved = _resolve_value(v)
                        if resolved is not v:
                            val[k] = resolved
                    elif hasattr(v, "__dict__"):
                        self._resolve_ast_variables(v, var_lookup)
            elif hasattr(val, "__dict__"):
                self._resolve_ast_variables(val, var_lookup)

    def _convert_styling_rule(self, ast_rule: AstStylingRule) -> StylingRule | None:
        """Convert AST StylingRule to Pydantic StylingRule.

        Includes nested selectors and ``stylingRuleName``.
        """
        try:
            selector: Any = None
            rule_name = None
            styling_rule_name = None
            # Support explicit stylingRuleName if present
            if hasattr(ast_rule, "styling_rule_name") and ast_rule.styling_rule_name:
                styling_rule_name = ast_rule.styling_rule_name
            # Always process selectors for any rule (top-level or nested)
            if hasattr(ast_rule, "selectors") and ast_rule.selectors:
                if len(ast_rule.selectors) > 1:
                    selector_args = []
                    for sel in ast_rule.selectors:
                        if hasattr(sel, "name") and sel.name:
                            selector_args.append(
                                {
                                    "op": "=",
                                    "args": [{"sysId": "dataLayer.id"}, sel.name],
                                }
                            )
                            if not rule_name:
                                rule_name = sel.name
                        elif hasattr(sel, "conditions") and sel.conditions:
                            for condition in sel.conditions:
                                json_condition = expression_to_json(condition)
                                if isinstance(json_condition, dict):
                                    selector_args.append(json_condition)
                        elif hasattr(sel, "expression") and sel.expression:
                            json_expr = expression_to_json(sel.expression)
                            if isinstance(json_expr, dict):
                                selector_args.append(json_expr)
                    if len(selector_args) > 1:
                        selector = {"op": "and", "args": selector_args}
                    elif len(selector_args) == 1:
                        selector = selector_args[0]
                    else:
                        selector = None
                    if selector:
                        selector = post_process_selector(selector)
                else:
                    sel = ast_rule.selectors[0]
                    if hasattr(sel, "name") and sel.name:
                        rule_name = sel.name
                        selector = {
                            "op": "=",
                            "args": [{"sysId": "dataLayer.id"}, sel.name],
                        }
                    elif hasattr(sel, "conditions") and sel.conditions:
                        if len(sel.conditions) > 1:
                            condition_args = []
                            for condition in sel.conditions:
                                json_condition = expression_to_json(condition)
                                if isinstance(json_condition, dict):
                                    condition_args.append(json_condition)
                            if condition_args:
                                selector = {"op": "and", "args": condition_args}
                        else:
                            selector = expression_to_json(sel.conditions[0])
                    else:
                        selector = None
                    if selector:
                        selector = post_process_selector(selector)
            elif hasattr(ast_rule, "name") and ast_rule.name:
                rule_name = ast_rule.name
                selector = [rule_name]
            elif hasattr(ast_rule, "selector") and ast_rule.selector:
                selector = ["Unknown"]

            # Convert symbolizer
            symbolizer = None
            if hasattr(ast_rule, "symbolizer") and ast_rule.symbolizer:
                symbolizer = self._convert_symbolizer(ast_rule.symbolizer)

            # Convert nested rules (ensure selectors are processed for each)
            nested_rules = None
            if hasattr(ast_rule, "nested_rules") and ast_rule.nested_rules:
                nested_rules = []
                for nested_ast_rule in ast_rule.nested_rules:
                    nested_pydantic_rule = self._convert_styling_rule(nested_ast_rule)
                    if nested_pydantic_rule:
                        nested_rules.append(nested_pydantic_rule)

            return StylingRule(
                name=rule_name,
                styling_rule_name=styling_rule_name,
                selector=selector,
                symbolizer=symbolizer,
                nested_rules=nested_rules,
            )

        except Exception as e:
            logger.warning("Failed to convert styling rule: %s", e)
            return None

    def _convert_symbolizer(self, ast_symbolizer) -> Symbolizer | None:
        """Convert AST Symbolizer to Pydantic Symbolizer."""
        try:
            symbolizer_data = {}

            # Basic properties
            if (
                hasattr(ast_symbolizer, "visibility")
                and ast_symbolizer.visibility is not None
            ):
                symbolizer_data["visibility"] = ast_symbolizer.visibility

            if (
                hasattr(ast_symbolizer, "opacity")
                and ast_symbolizer.opacity is not None
            ):
                symbolizer_data["opacity"] = ast_symbolizer.opacity

            if (
                hasattr(ast_symbolizer, "z_order")
                and ast_symbolizer.z_order is not None
            ):
                symbolizer_data["zOrder"] = ast_symbolizer.z_order

            # Complex properties
            if hasattr(ast_symbolizer, "fill") and ast_symbolizer.fill:
                fill = self._convert_fill(ast_symbolizer.fill)
                if fill:
                    symbolizer_data["fill"] = fill

            if hasattr(ast_symbolizer, "stroke") and ast_symbolizer.stroke:
                stroke = self._convert_stroke(ast_symbolizer.stroke)
                if stroke:
                    symbolizer_data["stroke"] = stroke

            if hasattr(ast_symbolizer, "marker") and ast_symbolizer.marker:
                marker = self._convert_marker(ast_symbolizer.marker)
                if marker:
                    symbolizer_data["marker"] = marker

            if hasattr(ast_symbolizer, "label") and ast_symbolizer.label:
                label = self._convert_label(ast_symbolizer.label)
                if label:
                    symbolizer_data["label"] = label

            # Coverage/Raster properties
            if (
                hasattr(ast_symbolizer, "single_channel")
                and ast_symbolizer.single_channel is not None
            ):
                symbolizer_data["single_channel"] = self._convert_channel_value(
                    ast_symbolizer.single_channel
                )
            elif (
                hasattr(ast_symbolizer, "singleChannel")
                and ast_symbolizer.singleChannel is not None
            ):
                symbolizer_data["single_channel"] = self._convert_channel_value(
                    ast_symbolizer.singleChannel
                )

            if (
                hasattr(ast_symbolizer, "color_channels")
                and ast_symbolizer.color_channels is not None
            ):
                symbolizer_data["color_channels"] = self._convert_channel_value(
                    ast_symbolizer.color_channels
                )
            elif (
                hasattr(ast_symbolizer, "colorChannels")
                and ast_symbolizer.colorChannels is not None
            ):
                symbolizer_data["color_channels"] = self._convert_channel_value(
                    ast_symbolizer.colorChannels
                )

            if (
                hasattr(ast_symbolizer, "alpha_channel")
                and ast_symbolizer.alpha_channel is not None
            ):
                symbolizer_data["alpha_channel"] = self._convert_channel_value(
                    ast_symbolizer.alpha_channel
                )
            elif (
                hasattr(ast_symbolizer, "alphaChannel")
                and ast_symbolizer.alphaChannel is not None
            ):
                symbolizer_data["alpha_channel"] = self._convert_channel_value(
                    ast_symbolizer.alphaChannel
                )

            if (
                hasattr(ast_symbolizer, "color_map")
                and ast_symbolizer.color_map is not None
            ):
                symbolizer_data["color_map"] = self._convert_color_map(
                    ast_symbolizer.color_map
                )
            elif (
                hasattr(ast_symbolizer, "colorMap")
                and ast_symbolizer.colorMap is not None
            ):
                symbolizer_data["color_map"] = self._convert_color_map(
                    ast_symbolizer.colorMap
                )

            if (
                hasattr(ast_symbolizer, "opacity_map")
                and ast_symbolizer.opacity_map is not None
            ):
                symbolizer_data["opacity_map"] = self._convert_opacity_map(
                    ast_symbolizer.opacity_map
                )
            elif (
                hasattr(ast_symbolizer, "opacityMap")
                and ast_symbolizer.opacityMap is not None
            ):
                symbolizer_data["opacity_map"] = self._convert_opacity_map(
                    ast_symbolizer.opacityMap
                )

            if (
                hasattr(ast_symbolizer, "hill_shading")
                and ast_symbolizer.hill_shading is not None
            ):
                symbolizer_data["hill_shading"] = self._convert_hill_shading(
                    ast_symbolizer.hill_shading
                )
            elif (
                hasattr(ast_symbolizer, "hillShading")
                and ast_symbolizer.hillShading is not None
            ):
                symbolizer_data["hill_shading"] = self._convert_hill_shading(
                    ast_symbolizer.hillShading
                )

            return Symbolizer(**symbolizer_data) if symbolizer_data else None

        except Exception as e:
            logger.warning("Failed to convert symbolizer: %s", e)
            return None

    def _convert_fill(self, ast_fill) -> Fill | None:
        """Convert AST Fill to Pydantic Fill with proper value conversion."""
        try:
            fill_data = {}

            if hasattr(ast_fill, "alter") and ast_fill.alter is not None:
                fill_data["alter"] = ast_fill.alter

            if hasattr(ast_fill, "color") and ast_fill.color is not None:
                # Use _convert_literal_value for proper hex/color conversion
                fill_data["color"] = convert_literal_value(str(ast_fill.color))

            if hasattr(ast_fill, "opacity") and ast_fill.opacity is not None:
                fill_data["opacity"] = float(ast_fill.opacity)

            # Pattern fields (hatch/dotpattern/stipple/pattern): only ever
            # arrive here already as typed Pydantic instances — built by
            # the parser's ANTLR-aware `fill: {...}` handler, which (unlike
            # this generic AST-shaped fallback) can see the nested
            # sub-block's expression tree. There is no legacy string form
            # to fall back to, unlike stroke.width below.
            for field in ("hatch", "dotpattern", "stipple", "pattern"):
                if hasattr(ast_fill, field) and getattr(ast_fill, field) is not None:
                    fill_data[field] = getattr(ast_fill, field)

            return Fill(**fill_data) if fill_data else None

        except Exception as e:
            logger.warning("Failed to convert fill: %s", e)
            return None

    def _convert_stroke(self, ast_stroke) -> Stroke | None:
        """Convert AST Stroke to Pydantic Stroke with proper value conversion."""
        try:
            stroke_data = {}

            if hasattr(ast_stroke, "alter") and ast_stroke.alter is not None:
                stroke_data["alter"] = ast_stroke.alter

            if hasattr(ast_stroke, "color") and ast_stroke.color is not None:
                # Use _convert_literal_value for proper hex/color conversion
                stroke_data["color"] = convert_literal_value(str(ast_stroke.color))

            if hasattr(ast_stroke, "width") and ast_stroke.width is not None:
                width = ast_stroke.width
                if isinstance(
                    width,
                    (UnitValue, ArithmeticExpression, SystemIdentifier, PropertyRef),
                ):
                    # Already a typed value (e.g. built directly by the
                    # parser's dot-notation handler, which — unlike this
                    # generic AST-shaped fallback — can see the ANTLR
                    # expression tree and resolve a numeric expression like
                    # ``viz.sd / 1000``). Stringifying and reparsing it via
                    # convert_literal_value would only be lossy here: a
                    # UnitValue's ``__str__`` happens to round-trip, but
                    # ArithmeticExpression/SystemIdentifier's Pydantic repr
                    # does not.
                    stroke_data["width"] = width
                else:
                    # Use _convert_literal_value for proper unit conversion
                    width_value = str(width)
                    stroke_data["width"] = convert_literal_value(width_value)

            if hasattr(ast_stroke, "opacity") and ast_stroke.opacity is not None:
                stroke_data["opacity"] = float(ast_stroke.opacity)

            return Stroke(**stroke_data) if stroke_data else None

        except Exception as e:
            logger.warning("Failed to convert stroke: %s", e)
            return None

    def _convert_marker(self, ast_marker) -> Marker | None:
        """Convert AST Marker to Pydantic Marker.

        Includes position and opacity if present, and preserves all element
        properties.
        """
        try:
            from .models.symbolizers import Marker as PydanticMarker

            marker_data = {}
            # Alter flag (set when marker.elements[N] syntax is used)
            if hasattr(ast_marker, "alter") and ast_marker.alter is not None:
                marker_data["alter"] = ast_marker.alter
            # Position and opacity at marker level
            if hasattr(ast_marker, "position") and ast_marker.position is not None:
                marker_data["position"] = ast_marker.position
            if hasattr(ast_marker, "opacity") and ast_marker.opacity is not None:
                marker_data["opacity"] = ast_marker.opacity
            # Elements — either a list of graphics or an indexed override {index, value}
            if hasattr(ast_marker, "elements") and ast_marker.elements is not None:
                elements = ast_marker.elements
                if (
                    isinstance(elements, dict)
                    and "index" in elements
                    and "value" in elements
                ):
                    # Indexed override: keep the {index, value} form
                    val = elements["value"]
                    if hasattr(val, "model_dump"):
                        el_dict = val.model_dump(exclude_none=True)
                    elif hasattr(val, "items"):
                        el_dict = dict(val)
                    else:
                        el_dict = val
                    # Marker.elements is typed Any (see models/symbolizers.py),
                    # so Pydantic never auto-validates `position` here — convert
                    # it to a real UnitPoint explicitly.
                    if isinstance(el_dict, dict) and isinstance(
                        el_dict.get("position"), (str, dict)
                    ):
                        from .models.symbolizers import UnitPoint as ModelUnitPoint

                        el_dict["position"] = ModelUnitPoint.model_validate(
                            el_dict["position"]
                        )
                    _normalize_graphic_element(el_dict)
                    marker_data["elements"] = {
                        "index": elements["index"],
                        "value": el_dict,
                    }
                else:
                    converted_elements = []
                    for el in (elements if isinstance(elements, list) else [elements]):
                        # Accept dicts (from marker.elements[N] patch) or
                        # Pydantic objects
                        if hasattr(el, "model_dump"):
                            el_dict = el.model_dump(exclude_none=True)
                        elif hasattr(el, "items"):
                            el_dict = dict(el)
                        else:
                            el_dict = el
                        # Ensure type is present (default to Dot if missing)
                        if isinstance(el_dict, dict) and "type" not in el_dict:
                            el_dict["type"] = "Dot"
                        # Marker.elements is typed Any (see models/symbolizers.py),
                        # so Pydantic never auto-validates `position` here —
                        # convert it to a real UnitPoint explicitly.
                        if isinstance(el_dict, dict) and isinstance(
                            el_dict.get("position"), (str, dict)
                        ):
                            from .models.symbolizers import UnitPoint as ModelUnitPoint

                            el_dict["position"] = ModelUnitPoint.model_validate(
                                el_dict["position"]
                            )
                        _normalize_graphic_element(el_dict)
                        converted_elements.append(el_dict)
                    marker_data["elements"] = converted_elements
            # If no data was collected the marker would serialize to {}, which
            # fails schema validation.  Return None so the symbolizer omits it.
            if not marker_data:
                return None
            return PydanticMarker(**marker_data)
        except Exception as e:
            logger.warning("Failed to convert marker: %s", e)
            return None

    def _convert_channel_value(self, value: Any) -> Any:
        """Convert a channel value to proper expression format.

        If value is a simple identifier string, convert to property reference.
        If value is multiple space-separated identifiers, convert to an array
        of property references.
        If value contains arithmetic operators, parse it as a mathematical
        expression.
        Otherwise return as-is for numeric values or complex expressions.
        """
        if isinstance(value, str):
            # Check if it contains arithmetic operators - if so, parse as expression
            if any(op in value for op in ["+", "-", "*", "/", "(", ")"]):
                try:
                    return self._parse_arithmetic_expression(value)
                except Exception as e:
                    logger.warning(
                        "Failed to parse arithmetic expression %r: %s", value, e
                    )
                    return value

            # Check for multiple space-separated identifiers (like "B04 B03 B02")
            parts = value.split()
            if len(parts) > 1:
                # Multiple identifiers - check if they're all simple identifiers
                if all(
                    p
                    and not any(
                        c in p
                        for c in [
                            "+",
                            "-",
                            "*",
                            "/",
                            "(",
                            ")",
                            "[",
                            "]",
                            "{",
                            "}",
                            ";",
                            ".",
                        ]
                    )
                    for p in parts
                ):
                    # Convert to array of property references
                    return [{"property": p} for p in parts]
            # Single identifier - check it's simple (no spaces, no operators)
            elif value and not any(
                c in value
                for c in [" ", "+", "-", "*", "/", "(", ")", "[", "]", "{", "}", ";"]
            ):
                # Check if it's a numeric literal
                try:
                    # Try to parse as number
                    if "." in value:
                        return float(value)
                    else:
                        return int(value)
                except ValueError:
                    # Not a number - convert to property reference
                    return {"property": value}
            # Otherwise return as-is
            return value
        elif isinstance(value, (int, float)):
            # Numeric value - return as-is
            return value
        elif isinstance(value, dict):
            # Already an expression object
            return value
        else:
            return value

    def _parse_arithmetic_expression(self, expr: str) -> Any:
        """Parse arithmetic expression string into JSON expression format.

        Handles basic arithmetic: +, -, *, / with parentheses.
        Example: "(B08 - B04)/(B08 + B04)" -> {"op": "/", "args": [...]}
        """
        expr = expr.strip()

        # Remove outer parentheses if they wrap the entire expression
        while expr.startswith("(") and expr.endswith(")"):
            # Check if these parentheses match
            depth = 0
            matches = True
            for i, c in enumerate(expr):
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                if depth == 0 and i < len(expr) - 1:
                    matches = False
                    break
            if matches:
                expr = expr[1:-1].strip()
            else:
                break

        # Parse operators with precedence: / and * before + and -
        # Find the last + or - that's not inside parentheses (lowest precedence)
        depth = 0
        last_add_sub = -1
        for i in range(len(expr) - 1, -1, -1):
            if expr[i] == ")":
                depth += 1
            elif expr[i] == "(":
                depth -= 1
            elif depth == 0 and expr[i] in ["+", "-"]:
                # Make sure it's not a unary operator at the start
                if i > 0:
                    last_add_sub = i
                    break

        if last_add_sub > 0:
            op = expr[last_add_sub]
            left = expr[:last_add_sub].strip()
            right = expr[last_add_sub + 1 :].strip()
            return {
                "op": op,
                "args": [
                    self._parse_arithmetic_expression(left),
                    self._parse_arithmetic_expression(right),
                ],
            }

        # Find the last * or / that's not inside parentheses (higher precedence)
        depth = 0
        last_mul_div = -1
        for i in range(len(expr) - 1, -1, -1):
            if expr[i] == ")":
                depth += 1
            elif expr[i] == "(":
                depth -= 1
            elif depth == 0 and expr[i] in ["*", "/"]:
                last_mul_div = i
                break

        if last_mul_div > 0:
            op = expr[last_mul_div]
            left = expr[:last_mul_div].strip()
            right = expr[last_mul_div + 1 :].strip()
            return {
                "op": op,
                "args": [
                    self._parse_arithmetic_expression(left),
                    self._parse_arithmetic_expression(right),
                ],
            }

        # No operators found - must be a terminal (identifier or number)
        # Check if it's a number
        try:
            if "." in expr:
                return float(expr)
            else:
                return int(expr)
        except ValueError:
            # It's an identifier - convert to property reference
            return {"property": expr}

    def _convert_label(self, ast_label) -> Label | None:
        """Convert AST Label to Pydantic Label, preserving all element properties."""
        try:
            from .models.symbolizers import Label as PydanticLabel

            label_data = {}
            # Position and opacity at label level
            if hasattr(ast_label, "position") and ast_label.position is not None:
                label_data["position"] = ast_label.position
            if hasattr(ast_label, "opacity") and ast_label.opacity is not None:
                label_data["opacity"] = ast_label.opacity
            if hasattr(ast_label, "placement") and ast_label.placement is not None:
                label_data["placement"] = ast_label.placement
            # Elements — list of graphics
            if hasattr(ast_label, "elements") and ast_label.elements is not None:
                elements = ast_label.elements
                converted_elements = []
                for el in (elements if isinstance(elements, list) else [elements]):
                    if hasattr(el, "model_dump"):
                        el_dict = el.model_dump(exclude_none=True)
                    elif hasattr(el, "items"):
                        el_dict = dict(el)
                    else:
                        el_dict = el
                    if isinstance(el_dict, dict) and "type" not in el_dict:
                        el_dict["type"] = "Dot"
                    # `position` (bare "x y" string or {x,y} dict) is
                    # accepted as-is — UnitPoint's own validator parses both.
                    _normalize_graphic_element(el_dict)
                    converted_elements.append(el_dict)
                label_data["elements"] = converted_elements
            if not label_data:
                return None
            return PydanticLabel(**label_data)
        except Exception as e:
            logger.warning("Failed to convert label: %s", e)
            return None

    def _convert_color_map(self, ast_color_map) -> Any | None:
        """Convert AST ColorMap to array format per JSON schema."""
        try:
            if isinstance(ast_color_map, (list, tuple)):
                # Return array directly per JSON schema
                return list(ast_color_map)
            elif isinstance(ast_color_map, dict):
                # Handle idOrFnExpression format
                return dict(ast_color_map)
            else:
                # Handle string or other formats - return as-is for validation to catch
                return str(ast_color_map)
        except Exception as e:
            logger.warning("Failed to convert color map: %s", e)
            return None

    def _convert_opacity_map(self, ast_opacity_map) -> Any | None:
        """Convert AST OpacityMap to array format per JSON schema."""
        try:
            if isinstance(ast_opacity_map, (list, tuple)):
                # Return array directly per JSON schema
                return list(ast_opacity_map)
            elif isinstance(ast_opacity_map, dict):
                # Handle idOrFnExpression format
                return dict(ast_opacity_map)
            else:
                # Handle string or other formats
                return str(ast_opacity_map)
        except Exception as e:
            logger.warning("Failed to convert opacity map: %s", e)
            return None

    def _convert_hill_shading(self, ast_hill_shading) -> dict[str, Any] | None:
        """Convert AST HillShading to dictionary per JSON schema."""
        try:
            if isinstance(ast_hill_shading, dict):
                # Handle object format, e.g.
                # {factor: 56; sun: {azimuth: 45.0; elevation: 60.0};
                #  colorMap: [...]; opacityMap: [...]}
                result: dict = {}
                for key, value in ast_hill_shading.items():
                    if key == "sun":
                        if isinstance(value, dict):
                            result["sun"] = dict(value)
                        elif (
                            isinstance(value, str)
                            and value.startswith("{")
                            and value.endswith("}")
                        ):
                            # Parse sun string, e.g.
                            # "{azimuth: 45.0; elevation: 60.0}" → object
                            sun_obj: dict = {}
                            content = value.strip("{}").strip()
                            for part in content.split(";"):
                                if ":" in part:
                                    k, v = part.split(":", 1)
                                    try:
                                        sun_obj[k.strip()] = float(v.strip())
                                    except ValueError:
                                        sun_obj[k.strip()] = v.strip()
                            result["sun"] = sun_obj
                        else:
                            result["sun"] = value
                    elif key == "colorMap":
                        # colorMap inside hillShading uses 0-1 values for first element
                        result["colorMap"] = (
                            value if isinstance(value, (list, dict)) else str(value)
                        )
                    elif key == "opacityMap":
                        # opacityMap inside hillShading
                        result["opacityMap"] = (
                            value if isinstance(value, (list, dict)) else str(value)
                        )
                    else:
                        result[key] = value
                return result
            else:
                return {"raw_value": str(ast_hill_shading)}
        except Exception as e:
            logger.warning("Failed to convert hill shading: %s", e)
            return {"raw_value": str(ast_hill_shading)}


def convert_ast_to_pydantic(ast_stylesheet: AstStyleSheet) -> Style:
    """Convert an AST StyleSheet to a Pydantic Style (convenience wrapper).

    Args:
        ast_stylesheet: ANTLR-generated AST stylesheet

    Returns:
        Pydantic Style model

    Raises:
        ValueError: If conversion fails
    """
    converter = AstToPydanticConverter()
    return converter.convert_stylesheet(ast_stylesheet)
