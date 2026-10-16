"""Serialise parsed expressions to CQL2-JSON selector dicts.

This is the expression → ``{"op": …, "args": …}`` half of the CQL2 codec,
lifted verbatim out of :class:`pycartosym.ast_converter.AstToPydanticConverter`
(the functions here never touched ``self`` — they only called one another).
Import the stable entry points from :mod:`pycartosym.cql2` rather
than from here directly.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "post_process_selector",
    "expression_to_json",
    "convert_identifier",
    "convert_literal_value",
    "convert_numeric_expression_value",
    "convert_property_expression",
    "split_on_comparison_operator",
]

# Tried longest-first so e.g. ">=" matches before its "=" substring.
_COMPARISON_OPERATORS = [">=", "<=", "<>", "!=", "=", ">", "<"]


class _StringLiteral(str):
    """A CQL2 character literal (``'sl'``), as opposed to an identifier.

    Both reach :func:`post_process_selector` as plain ``str``, which then
    turns a bare word into a property reference. This marker keeps a quoted
    literal a literal.
    """

    __slots__ = ()


def split_on_comparison_operator(
    text: str, *, quoted_guard: bool = True
) -> tuple[str, str, str] | None:
    """Find a comparison operator embedded in *text* and split around it.

    Returns ``(op, left_part, right_part)`` for the first operator in
    ``_COMPARISON_OPERATORS`` that appears in *text* and splits it into
    exactly two pieces, both stripped of surrounding whitespace. Returns
    ``None`` if no operator matches.

    When *quoted_guard* is true (the default), a *text* starting with a
    quote character is never split — it's a string literal, not an
    embedded expression. ``converter.py``'s ``_fix_selector`` passes
    ``quoted_guard=False``: it runs on a ``sysId`` value that is never
    itself quoted, so the earlier duplicated copy of this logic there
    never carried the guard either.
    """
    if quoted_guard and (text.startswith('"') or text.startswith("'")):
        return None
    for op in _COMPARISON_OPERATORS:
        if op in text:
            parts = text.split(op, 1)
            if len(parts) == 2:
                return op, parts[0].strip(), parts[1].strip()
    return None


def post_process_selector(selector: Any) -> Any:
    """Post-process a selector: fix parsing issues, ensure proper JSON structure.

    Returns a dict for well-formed selectors. ``None`` and lists pass
    through unchanged; a string is parsed into a selector dict.
    """
    left_arg: Any
    right_arg: Any
    if isinstance(selector, dict):
        unit = _unit_of(selector)
        if unit is not None and isinstance(unit[1], dict):
            return {unit[0]: post_process_selector(unit[1])}
        if "op" in selector and "args" in selector:
            # Post-process arguments recursively
            processed_args: list = []
            op = selector.get("op", "")
            # Ops whose args after index 0 are value literals, not
            # property references (comparisons + CQL2 value predicates).
            is_comparison = op in [
                "=",
                "<",
                "<=",
                ">",
                ">=",
                "<>",
                "!=",
                "like",
                "ilike",
                "between",
                "in",
            ]
            for i, arg in enumerate(selector["args"]):
                # Convert string arguments to property references in comparisons
                if isinstance(arg, _StringLiteral):
                    processed_args.append(str(arg))
                elif isinstance(arg, str):
                    # In a comparison, right-hand args (index > 0) are VALUE
                    # literals (from CHARACTER_LITERALs like 'parking') – keep
                    # them as plain strings.
                    if is_comparison and i > 0:
                        processed_args.append(arg)
                    # Convert a simple identifier to a property reference, but
                    # not if it has quotes, spaces, dots, or is purely numeric.
                    elif (
                        arg
                        and not any(c in arg for c in ['"', "'", " ", "."])
                        and not arg.replace("-", "").replace("_", "").isdigit()
                    ):
                        # Simple identifier on left side - convert to property reference
                        processed_args.append({"property": arg})
                    else:
                        # Keep as-is (string literal or numeric string)
                        processed_args.append(arg)
                else:
                    # Recursively process non-string arguments
                    processed_args.append(post_process_selector(arg))
            selector["args"] = processed_args
            return selector
        elif "sysId" in selector:
            sysid = selector["sysId"]
            # Check if sysId contains an embedded expression
            split = split_on_comparison_operator(sysid)
            if split is not None:
                op, left_part, right_part = split
                # Convert right part
                if right_part.isdigit():
                    right_arg = int(right_part)
                elif right_part.replace(".", "").isdigit():
                    right_arg = float(right_part)
                else:
                    right_arg = right_part.strip("'\"")

                return {"op": op, "args": [{"sysId": left_part}, right_arg]}
        elif "property" in selector:
            prop = selector["property"]
            # Check if property is actually an unparsed CQL2 expression
            # (e.g. T_DURING(...))
            if ("(" in prop and prop.endswith(")")) or (
                "{" in prop and prop.endswith("}")
            ):
                try:
                    from .from_text import ExpressionParser

                    parsed = ExpressionParser._parse_expression_text(prop)
                    converted = expression_to_json(parsed)
                    if (
                        converted
                        and converted != prop
                        and converted != {"property": prop}
                    ):
                        return post_process_selector(converted)
                except Exception:
                    pass
            # Check if property contains an embedded expression
            split = split_on_comparison_operator(prop)
            if split is not None:
                op, left_part, right_part = split
                # Determine if left part is system property or regular property
                if "." in left_part and any(
                    left_part.startswith(prefix)
                    for prefix in ["viz", "dataLayer", "feature"]
                ):
                    left_arg = {"sysId": left_part}
                # Special case: certain properties are known system identifiers
                elif left_part in [
                    "featuresGeometryDimensions",
                    "featuresGeometry",
                    "geometryDimensions",
                ]:
                    left_arg = {"sysId": f"dataLayer.{left_part}"}
                else:
                    left_arg = {"property": left_part}

                # Convert right part
                if right_part.isdigit():
                    right_arg = int(right_part)
                elif right_part.replace(".", "").replace("-", "").isdigit():
                    right_arg = float(right_part)
                else:
                    right_arg = right_part.strip("'\"")

                return {"op": op, "args": [left_arg, right_arg]}
        return selector
    elif isinstance(selector, str):
        # Handle string selectors that should be expressions
        return convert_string_to_json_selector(selector)
    else:
        return selector


def convert_string_to_json_selector(selector_str: str) -> dict[str, Any]:
    """Convert string selector to proper JSON structure."""
    left_arg: Any
    right_arg: Any
    # Handle expressions embedded in strings
    split = split_on_comparison_operator(selector_str)
    if split is not None:
        op, left_part, right_part = split
        right_part = right_part.strip("'\"")
        # Determine if left part is system property or regular property
        if "." in left_part and any(
            left_part.startswith(prefix) for prefix in ["viz", "dataLayer"]
        ):
            left_arg = {"sysId": left_part}
        elif left_part in ["validDate", "FunctionCode", "FunctionTitle"]:
            left_arg = {"property": left_part}
        else:
            left_arg = left_part
        # Convert right part (handle sysId for dot notation)
        if right_part.isdigit():
            right_arg = int(right_part)
        elif right_part.replace(".", "").isdigit():
            right_arg = float(right_part)
        elif "." in right_part and any(
            right_part.startswith(prefix) for prefix in ["viz", "dataLayer"]
        ):
            right_arg = {"sysId": right_part}
        elif right_part in ["validDate", "FunctionCode", "FunctionTitle"]:
            right_arg = {"property": right_part}
        else:
            right_arg = right_part
        return {"op": op, "args": [left_arg, right_arg]}
    # If no operator found, treat as property
    return {"property": selector_str}


def _unit_of(arg: Any) -> tuple[str, Any] | None:
    """``{"px": 6}`` -> ``("px", 6)``; ``None`` for anything else."""
    if isinstance(arg, dict) and len(arg) == 1:
        ((key, inner),) = arg.items()
        if key in _UNITS:
            return key, inner
    return None


def _hoist_common_unit(op: str, args: list[Any]) -> dict[str, Any]:
    """Build an arithmetic operation, moving a shared unit outside of it.

    The schema puts the unit around the whole numeric expression
    (``{"px": {"op": "*", "args": [w, 2]}}``), not on each operand.

    Raises:
        ValueError: If operands use different units, which the schema
            cannot express.
    """
    units = {u[0] for a in args if (u := _unit_of(a))}
    if not units:
        return {"op": op, "args": args}
    if len(units) > 1:
        raise ValueError(f"cannot mix units {sorted(units)} in one expression ({op!r})")
    (unit,) = units
    bare = [u[1] if (u := _unit_of(a)) else a for a in args]
    return {unit: {"op": op, "args": bare}}


def expression_to_json(expression: Any) -> Any:
    """Convert an ANTLR expression to CS-JSON selector format."""
    if expression is None:
        return {}

    # NULL literal -> JSON null (checked before the falsy guard below).
    from .model import (
        ArrayExpression,
        ConditionalExpression,
        NullLiteral,
        StringExpression,
    )

    if isinstance(expression, NullLiteral):
        return None

    if not expression:
        return {}

    # Nested operand lists (e.g. the value list of an `in` predicate:
    # inListOperands = [scalarExpression, [scalarExpression, ...]]).
    if isinstance(expression, list):
        return [expression_to_json(item) for item in expression]

    # Handle ANTLR context objects (from grammar)
    if hasattr(expression, "getRuleIndex"):
        from ..grammar.generated.CartoSymCSSGrammar import CartoSymCSSGrammar

        rule_name = CartoSymCSSGrammar.ruleNames[expression.getRuleIndex()]
        return convert_antlr_expression(expression, rule_name)

    # Array literal -> JSON array; `c ? a : b` -> the schema's "?:" operator.
    if isinstance(expression, ArrayExpression):
        return [expression_to_json(item) for item in expression.elements]
    if isinstance(expression, ConditionalExpression):
        return {
            "op": "?:",
            "args": [
                expression_to_json(expression.condition),
                expression_to_json(expression.true_value),
                expression_to_json(expression.false_value),
            ],
        }

    # Handle UnaryOperationExpression (`not <expr>`) — check before the
    # binary branch (unary has `operator` + `operand`, no left/right).
    if (
        hasattr(expression, "operand")
        and hasattr(expression, "operator")
        and not hasattr(expression, "left")
    ):
        op_str = str(expression.operator).lower()
        op = "not" if "not" in op_str else op_str.rsplit(".", 1)[-1]
        operand = expression_to_json(expression.operand)
        if op == "-" and isinstance(operand, (int, float)):
            return -operand  # `-1` is the number -1, not a unary operation
        return {"op": op, "args": [operand]}

    # Handle BinaryOperationExpression (AST objects)
    if (
        hasattr(expression, "left")
        and hasattr(expression, "right")
        and hasattr(expression, "operator")
    ):
        left_arg = expression_to_json(expression.left)
        right_arg = expression_to_json(expression.right)

        # Map operator enum to string
        op_str = str(expression.operator)
        if getattr(expression.operator, "value", expression.operator) == "**":
            op = "^"  # CQL2-JSON / schema power operator
        elif "AND" in op_str:
            op = "and"
        elif "OR" in op_str:
            op = "or"
        elif "EQ" in op_str or "EQUAL" in op_str:
            op = "="
        elif "LT" in op_str and "LESS_THAN" in op_str:
            op = "<"
        elif "GT" in op_str and "GREATER_THAN" in op_str:
            op = ">"
        elif "LTE" in op_str or "LESS_EQUAL" in op_str:
            op = "<="
        elif "GTE" in op_str or "GREATER_EQUAL" in op_str:
            op = ">="
        elif "NEQ" in op_str or "NOT_EQUAL" in op_str:
            op = "<>"
        else:
            # Extract operator from string representation
            if "." in op_str:
                op_name = op_str.split(".")[-1].lower()
                op = op_name
            else:
                op = str(expression.operator)

        if op in _ARITHMETIC_OPS:
            return _hoist_common_unit(op, [left_arg, right_arg])
        return {"op": op, "args": [left_arg, right_arg]}

    # Handle MemberAccessExpression (system properties, recursive for deep access)
    if hasattr(expression, "object") and hasattr(expression, "member"):

        def get_full_property(expr):
            if hasattr(expr, "object") and hasattr(expr, "member"):
                return get_full_property(expr.object) + "." + str(expr.member)
            elif hasattr(expr, "name"):
                return str(expr.name)
            else:
                return str(expr)

        full_property = get_full_property(expression)
        # Top-level prefix check for sysId
        top_level = full_property.split(".", 1)[0]
        if top_level in ["viz", "vis", "dataLayer"]:
            return {"sysId": full_property}
        else:
            return {"property": full_property}

    # Handle CQL2 TemporalLiteral (DATE/TIMESTAMP/INTERVAL from expression parser)
    if hasattr(expression, "temporal_type"):
        if expression.temporal_type == "date":
            return {"date": expression.value}
        elif expression.temporal_type == "timestamp":
            return {"timestamp": expression.value}
        elif expression.temporal_type == "interval":
            return {
                "interval": [
                    v if isinstance(v, str) else expression_to_json(v)
                    for v in expression.interval
                ]
            }

    # Handle CQL2 BboxLiteral
    if hasattr(expression, "bbox") and isinstance(
        getattr(expression, "bbox", None), list
    ):
        return {"bbox": expression.bbox}

    # Handle CQL2 GeometryLiteral
    if hasattr(expression, "geom_type") and hasattr(expression, "coordinates"):
        result = {"type": expression.geom_type}
        if expression.coordinates is not None:
            result["coordinates"] = expression.coordinates
        if hasattr(expression, "geometries") and expression.geometries:
            result["geometries"] = [
                expression_to_json(g) for g in expression.geometries
            ]
        return result

    # Handle CQL2 spatial/temporal/array predicates + character/geometry functions
    if (
        hasattr(expression, "op")
        and hasattr(expression, "args")
        and not hasattr(expression, "function_name")
    ):
        result = {
            "op": expression.op,
            "args": [expression_to_json(arg) for arg in expression.args],
        }
        # Preserve extra fields (e.g. SpatialRelatePredicate.pattern)
        if hasattr(expression, "pattern"):
            result["pattern"] = expression.pattern
        return result

    # Handle FunctionCallExpression
    if hasattr(expression, "function_name") and hasattr(expression, "arguments"):
        func_name = expression.function_name
        # DATE('...') → { "date": "..." } (OGC scalar-data-types)
        if func_name.upper() == "DATE" and len(expression.arguments) == 1:
            arg = expression.arguments[0]
            date_val = arg.value if hasattr(arg, "value") else str(arg)
            # Strip surrounding quotes if present
            if isinstance(date_val, str):
                date_val = date_val.strip("'\"")
            return {"date": date_val}
        # Other function calls use "op" (not "function")
        return {
            "op": func_name,
            "args": [expression_to_json(arg) for arg in expression.arguments],
        }

    if isinstance(expression, StringExpression):
        return _StringLiteral(expression.value)

    # Handle IdentifierExpression (simple properties)
    if hasattr(expression, "name"):
        return convert_identifier(expression.name)

    # A constant with a unit (`6 px`) is the schema's unitValue: {"px": 6}.
    if getattr(expression, "unit", None) and hasattr(expression, "value"):
        return {
            str(getattr(expression.unit, "value", expression.unit)): expression.value
        }

    # Handle LiteralExpression/ConstantExpression
    if hasattr(expression, "value"):
        return convert_literal_value(expression.value)

    # Handle string representation (fallback)
    if isinstance(expression, str):
        return convert_identifier(expression)

    # Final fallback - convert to string
    return str(expression)


def convert_antlr_expression(expr_ctx: Any, rule_name: str) -> Any:
    """Convert an ANTLR expression context, following the parse-tree structure.

    Binary expressions appear as ``expression -> expression operator
    expression``.
    """
    if rule_name == "expression":
        if hasattr(expr_ctx, "getChildCount"):
            child_count = expr_ctx.getChildCount()

            # Binary expression pattern: expression + operator + expression (count = 3)
            if child_count == 3:
                left_child = expr_ctx.getChild(0)
                op_child = expr_ctx.getChild(1)
                right_child = expr_ctx.getChild(2)

                # Check if middle child is an operator
                if hasattr(op_child, "getRuleIndex"):
                    from ..grammar.generated.CartoSymCSSGrammar import (
                        CartoSymCSSGrammar,
                    )

                    op_rule = CartoSymCSSGrammar.ruleNames[op_child.getRuleIndex()]

                    if op_rule in [
                        "relationalOperator",
                        "arithmeticOperatorAdd",
                        "arithmeticOperatorMul",
                        "arithmeticOperatorExp",
                    ]:
                        # This is a binary operation
                        left_arg = convert_antlr_expression(left_child, "expression")
                        operator = op_child.getText().lower()
                        right_arg = convert_antlr_expression(right_child, "expression")

                        return {"op": operator, "args": [left_arg, right_arg]}

                # `and` / `or` are bare tokens in the `expression` rule
                elif not hasattr(op_child, "getRuleIndex") and (
                    op_child.getText().lower() in ("and", "or")
                ):
                    return {
                        "op": op_child.getText().lower(),
                        "args": [
                            convert_antlr_expression(left_child, "expression"),
                            convert_antlr_expression(right_child, "expression"),
                        ],
                    }

                # Property access pattern: expression + '.' + terminal
                elif (
                    hasattr(left_child, "getRuleIndex")
                    and not hasattr(op_child, "getRuleIndex")
                    and op_child.getText() == "."
                    and not hasattr(right_child, "getRuleIndex")
                ):

                    # Build property path: obj.member
                    left_part = convert_antlr_expression(left_child, "expression")
                    right_part = right_child.getText()

                    if isinstance(left_part, str):
                        full_path = f"{left_part}.{right_part}"
                    elif isinstance(left_part, dict) and "sysId" in left_part:
                        full_path = f"{left_part['sysId']}.{right_part}"
                    elif isinstance(left_part, dict) and "property" in left_part:
                        full_path = f"{left_part['property']}.{right_part}"
                    else:
                        full_path = f"{left_part}.{right_part}"

                    return convert_identifier(full_path)

            # Single child expression
            elif child_count == 1:
                child = expr_ctx.getChild(0)
                if hasattr(child, "getRuleIndex"):
                    from ..grammar.generated.CartoSymCSSGrammar import (
                        CartoSymCSSGrammar,
                    )

                    child_rule = CartoSymCSSGrammar.ruleNames[child.getRuleIndex()]
                    return convert_antlr_expression(child, child_rule)
                else:
                    # Terminal
                    return convert_identifier(child.getText())

    elif rule_name == "idOrConstant":
        # Check for expConstant child (numeric literal)
        if hasattr(expr_ctx, "getChildCount") and expr_ctx.getChildCount() == 1:
            child = expr_ctx.getChild(0)
            if hasattr(child, "getRuleIndex"):
                from ..grammar.generated.CartoSymCSSGrammar import CartoSymCSSGrammar

                child_rule = CartoSymCSSGrammar.ruleNames[child.getRuleIndex()]
                if child_rule == "expConstant":
                    return convert_literal_value(child.getText())

        # Otherwise treat as identifier
        return convert_identifier(expr_ctx.getText())

    elif rule_name == "expString":
        # String literal - remove quotes
        text = expr_ctx.getText()
        if (text.startswith("'") and text.endswith("'")) or (
            text.startswith('"') and text.endswith('"')
        ):
            return text[1:-1]
        return text

    # Default: get text and convert as identifier
    return convert_identifier(expr_ctx.getText())


def convert_identifier(name: str) -> Any:
    """Convert an identifier to a JSON selector part, mapping system properties."""
    left_arg: Any
    right_arg: Any
    # Handle embedded operators first
    split = split_on_comparison_operator(name)
    if split is not None:
        op, left_part, right_part = split
        # Convert left part (property)
        if "." in left_part:
            if any(
                left_part.startswith(prefix) for prefix in ["viz", "vis", "dataLayer"]
            ):
                # Map system properties correctly
                mapped_prop = _map_system_property(left_part)
                left_arg = {"sysId": mapped_prop}
            else:
                left_arg = {"property": left_part}
        else:
            if left_part in ["validDate", "FunctionCode", "FunctionTitle"]:
                left_arg = {"property": left_part}
            elif any(
                left_part.startswith(prefix) for prefix in ["viz", "vis", "dataLayer"]
            ):
                mapped_prop = _map_system_property(left_part)
                left_arg = {"sysId": mapped_prop}
            else:
                left_arg = left_part

        # Convert right part (value)
        right_arg = convert_literal_value(right_part)

        return {"op": op, "args": [left_arg, right_arg]}

    # No operator - determine property type
    if "." in name:
        if any(name.startswith(prefix) for prefix in ["viz", "vis", "dataLayer"]):
            mapped_prop = _map_system_property(name)
            return {"sysId": mapped_prop}
        else:
            return {"property": name}
    else:
        if name in ["validDate", "FunctionCode", "FunctionTitle"]:
            return {"property": name}
        elif any(name.startswith(prefix) for prefix in ["viz", "vis", "dataLayer"]):
            mapped_prop = _map_system_property(name)
            return {"sysId": mapped_prop}
        else:
            return convert_literal_value(name)


def _map_system_property(prop: str) -> str:
    """Retourne la propriété système telle quelle (mapping identique)."""
    return prop


def convert_literal_value(value: str | int | float) -> Any:
    """Convert literal value to appropriate JSON type with proper CS.JSON formatting."""
    if isinstance(value, (int, float)):
        return value

    if not isinstance(value, str):
        value = str(value)

    # Handle quoted strings
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]  # Remove quotes

    # Handle hex colors - convert to [r, g, b] array (CS.JSON color schema only accepts
    # arrays, {r,g,b} objects, or web color names – not hex strings)
    if value.startswith("#") and len(value) == 7:
        try:
            return list(bytes.fromhex(value[1:]))
        except ValueError:
            return value  # Keep as string if not valid hex

    # Handle numbers with units (e.g., "2.0px") -> UnitValue format for CS.JSON.
    # Every models.types.UnitType suffix, not just the screen-unit subset —
    # a ground-unit width like "8.0 m" silently stayed a bare string here
    # otherwise (only caught downstream, if at all, by whichever codec
    # consumes it — see the MapLibre writer's ``Stroke.width`` handling).
    # Multi-character suffixes are checked before the single-character "m"
    # so e.g. "8.0 mm" isn't mis-sliced as a 1-char "m" match first.
    # "%" excluded: CartoSym-CSS lexes it only as the modulo operator (MOD),
    # never as a unit suffix (vendor/cartosymcss-grammar/CartoSymCSSLexer.g4's
    # UNIT token has no "%" member) - and UnitType has no PERCENT either, so
    # keeping it here only produced a silent UnitValue(unit="%") -> ValueError
    # -> bare-string fallback, never a real unit.
    units = ["px", "mm", "cm", "in", "pt", "em", "pc", "ft", "m"]
    if value.endswith(tuple(units)):
        for unit in units:
            if value.endswith(unit):
                number_part = value[: -len(unit)]
                try:
                    if "." in number_part:
                        # Return as CS.JSON UnitValue format for Pydantic compatibility
                        from ..models.types import UnitType, UnitValue

                        return UnitValue(
                            value=float(number_part),
                            unit=getattr(UnitType, unit.upper(), unit),
                        )
                    else:
                        # Return as CS.JSON UnitValue format for Pydantic compatibility
                        from ..models.types import UnitType, UnitValue

                        return UnitValue(
                            value=int(number_part),
                            unit=getattr(UnitType, unit.upper(), unit),
                        )
                except (ValueError, ImportError):
                    # Fallback to string if UnitValue creation fails
                    return value

    # Handle pure numbers
    if value.isdigit():
        return int(value)

    try:
        if "." in value:
            return float(value)
    except ValueError:
        pass

    # Handle boolean values
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False

    # Keep known color names as strings (CS.JSON supports named colors)
    color_names = [
        "red",
        "green",
        "blue",
        "yellow",
        "black",
        "white",
        "gray",
        "grey",
        "darkGray",
        "lightGray",
        "darkGreen",
        "lightGreen",
        "darkBlue",
        "lightBlue",
        "darkRed",
        "lightRed",
        "orange",
        "purple",
        "brown",
        "pink",
        "cyan",
        "magenta",
    ]
    if value in color_names:
        return value

    # Keep known identifiers as strings
    return value


_ARITHMETIC_OPS = {"+", "-", "*", "/", "^"}
_UNITS = {"px", "mm", "cm", "in", "pt", "em", "pc", "m", "ft"}


def _is_supported_numeric_expr(value: Any) -> bool:
    """Whether ``value`` is a JSON shape this codec's numeric expressions can carry.

    A plain number, a ``sysId``/``property`` reference, or a schema-valid
    (``+``/``-``/``*``/``/``/``^``) arithmetic combination of those.
    """
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, dict):
        if "sysId" in value or "property" in value:
            return True
        if "op" in value and "args" in value:
            return value["op"] in _ARITHMETIC_OPS and all(
                _is_supported_numeric_expr(arg) for arg in value["args"]
            )
    return False


def convert_numeric_expression_value(prop_value: str, expr_ctx: Any = None) -> Any:
    """Convert a numeric symbolizer property value.

    Falls back to :func:`convert_literal_value` for a plain number/unit
    value — unchanged behavior for every case it already handled. When
    that only produces an unresolved opaque string *and* a parsed ANTLR
    expression tree is available, parses it as a numeric expression
    instead — e.g. ``viz.sd / 1000`` becomes ``{"op": "/", "args":
    [{"sysId": "viz.sd"}, 1000]}`` rather than round-tripping as the
    literal text ``"viz.sd / 1000"`` (OGC issue #115).
    """
    literal = convert_literal_value(prop_value)
    if isinstance(literal, str) and expr_ctx is not None:
        parsed = convert_property_expression(prop_value)
        if parsed is not None:
            return parsed
        parsed = convert_antlr_expression(expr_ctx, "expression")
        if _is_supported_numeric_expr(parsed):
            return parsed
    return literal


def convert_property_expression(text: str) -> dict[str, Any] | int | float | None:
    """Parse a property value such as ``upperCase(name)`` to CQL2-JSON.

    Returns the JSON operation (or number) the expression parses to, or
    ``None`` when *text* is not an operation (a bare word is a property name,
    handled by the caller), so callers can warn instead of
    dropping the value silently.
    """
    from .from_text import ExpressionParser

    try:
        result = post_process_selector(
            expression_to_json(ExpressionParser._parse_expression_text(text))
        )
    except Exception:  # noqa: BLE001 - not an expression the parser understands
        return None
    if isinstance(result, (int, float)):
        return result
    # Only a real operation: a bare word or opaque text parses to a "property".
    if (
        isinstance(result, dict)
        and ("op" in result or _unit_of(result))
        and "ExpressionType" not in str(result)
    ):
        return result
    return None
