"""Serialise CQL2-JSON selector dicts back to CartoSym-CSS filter text.

This is the ``{"op": …, "args": …}`` → ``a = 'b' and c > 1`` half of the
CQL2 codec, lifted verbatim out of
:class:`pycartosym.converter.Converter` (the functions here never
touched ``self`` — they only called one another). Import the stable entry
points from :mod:`pycartosym.cql2` rather than from here directly.
"""

from __future__ import annotations

__all__ = ["expression_to_text", "geojson_to_wkt"]


def expression_to_text(expr, quote_bare_strings: bool = True) -> str:
    """Recursively format a selector expression dict as a CSCSS filter string.

    quote_bare_strings: when True (default) plain string values are
    single-quoted.  Set to False when the right-hand side of a sysId
    comparison is an unquoted identifier/enum (e.g. ``dataLayer.type = vector``).
    """
    if not isinstance(expr, dict):
        s = str(expr)
        if not quote_bare_strings:
            return s  # unquoted identifier/constant
        # Quote bare strings that are not numbers / booleans — they came from
        # CHARACTER_LITERALs like 'parking' and must be re-quoted on write-back.
        try:
            float(s)
            return s  # numeric literal – no quotes
        except ValueError:
            pass
        if s.lower() in ("true", "false", "null"):
            return s
        # Plain string value → single-quote it
        return f"'{s}'"
    # Handle bare property reference (e.g., {"property": "viz.date"})
    if "property" in expr and len(expr) == 1:
        return str(expr["property"])
    # Handle date literal (e.g., {"date": "2020-01-01"} → DATE('2020-01-01'))
    if "date" in expr and len(expr) == 1:
        return f"DATE('{expr['date']}')"
    # Handle timestamp literal
    if "timestamp" in expr and len(expr) == 1:
        return f"TIMESTAMP('{expr['timestamp']}')"
    # Handle interval literal
    if "interval" in expr and len(expr) == 1:
        parts = expr["interval"]
        args = ", ".join(f"'{p}'" for p in parts)
        return f"INTERVAL({args})"
    # Handle BBOX literal
    if "bbox" in expr and len(expr) == 1:
        vals = ", ".join(str(v) for v in expr["bbox"])
        return f"BBOX({vals})"
    # Handle GeoJSON geometry literal (has "type" + "coordinates" or "geometries")
    if "type" in expr and ("coordinates" in expr or "geometries" in expr):
        return geojson_to_wkt(expr)
    # Function call formatting (legacy "function" key, or "op" key for a
    # non-operator function)
    if "function" in expr and "args" in expr:
        func_name = expr["function"]
        args = expr["args"]

        def format_arg(a):
            if isinstance(a, str):
                if (a.startswith("'") and a.endswith("'")) or (
                    a.startswith('"') and a.endswith('"')
                ):
                    return a
                try:
                    float(a)
                    return a
                except Exception:
                    return f"'{a}'"
            return expression_to_text(a)

        args_str = ", ".join(format_arg(a) for a in args)
        return f"{func_name}({args_str})"
    op = expr.get("op")
    if op == "!=":  # legacy CS-JSON spelling; CartoSym-CSS only has `<>`
        op = "<>"
    args = expr.get("args", [])
    if op and isinstance(args, list):
        # Standard infix operators
        _INFIX_OPERATORS = {
            "and",
            "or",
            "=",
            "<>",
            "!=",
            "<",
            ">",
            "<=",
            ">=",
            "+",
            "-",
            "*",
            "/",
        }

        # --- CQL2 predicate function-call ops (S_INTERSECTS, T_BEFORE, etc.) ---
        op_lower = op.lower() if isinstance(op, str) else ""
        if (
            op_lower.startswith("s_")
            or op_lower.startswith("t_")
            or op_lower.startswith("a_")
        ):
            # Spatial/temporal/array predicates → FUNC(args)
            cql2_name = op.upper()

            def fmt_cql2_arg(a):
                return expression_to_text(a)

            if op_lower == "s_relate":
                # S_RELATE has a pattern as extra field
                pattern = expr.get("pattern", "")
                geom_args = ", ".join(fmt_cql2_arg(a) for a in args)
                return f"{cql2_name}({geom_args}, '{pattern}')"
            args_str = ", ".join(fmt_cql2_arg(a) for a in args)
            return f"{cql2_name}({args_str})"

        # --- Text operation predicates: contains, startsWith, endsWith ---
        if op_lower in ("contains", "startswith", "endswith"):
            _text_op_to_cql = {
                "contains": "CONTAINS",
                "startswith": "STARTSWITH",
                "endswith": "ENDSWITH",
            }
            cql_name = _text_op_to_cql[op_lower]
            args_str = ", ".join(expression_to_text(a) for a in args)
            return f"{cql_name}({args_str})"

        # --- Character expression functions: casei, accenti, lowerCase, upperCase,
        #     concatenate, substitute, format ---
        _char_func_ops = {
            "casei",
            "accenti",
            "lowercase",
            "uppercase",
            "concatenate",
            "substitute",
            "format",
        }
        if op_lower in _char_func_ops:
            cql_name = op.upper()
            args_str = ", ".join(expression_to_text(a) for a in args)
            return f"{cql_name}({args_str})"

        # --- BETWEEN: {"op": "between", "args": [val, lo, hi]} ---
        if op_lower == "between" and len(args) == 3:
            val = expression_to_text(args[0])
            lo = expression_to_text(args[1])
            hi = expression_to_text(args[2])
            return f"{val} between {lo} and {hi}"

        # --- IN: {"op": "in", "args": [val, [item1, item2, ...]]} ---
        if op_lower == "in" and len(args) >= 2:
            val = expression_to_text(args[0])
            if isinstance(args[1], list):
                items = ", ".join(expression_to_text(i) for i in args[1])
            else:
                items = ", ".join(expression_to_text(a) for a in args[1:])
            return f"{val} in ({items})"

        # --- LIKE / ILIKE: {"op": "like", "args": [val, pattern]} ---
        if op_lower in ("like", "ilike") and len(args) >= 2:
            val = expression_to_text(args[0])
            pat = expression_to_text(args[1])
            return f"{val} {op_lower} {pat}"

        # --- IS NULL: {"op": "isNull", "args": [val]} ---
        if op_lower == "isnull" and len(args) == 1:
            val = expression_to_text(args[0])
            return f"{val} is null"

        # --- NOT: {"op": "not", "args": [inner]} ---
        if op_lower == "not" and len(args) == 1:
            inner = args[0]
            # Detect NOT BETWEEN, NOT IN, NOT LIKE, IS NOT NULL
            if isinstance(inner, dict):
                inner_op = (inner.get("op") or "").lower()
                inner_args = inner.get("args", [])
                if inner_op == "between" and len(inner_args) == 3:
                    val = expression_to_text(inner_args[0])
                    lo = expression_to_text(inner_args[1])
                    hi = expression_to_text(inner_args[2])
                    return f"{val} not between {lo} and {hi}"
                if inner_op == "in" and len(inner_args) >= 2:
                    val = expression_to_text(inner_args[0])
                    if isinstance(inner_args[1], list):
                        items = ", ".join(expression_to_text(i) for i in inner_args[1])
                    else:
                        items = ", ".join(expression_to_text(a) for a in inner_args[1:])
                    return f"{val} not in ({items})"
                if inner_op in ("like", "ilike") and len(inner_args) >= 2:
                    val = expression_to_text(inner_args[0])
                    pat = expression_to_text(inner_args[1])
                    return f"{val} not {inner_op} {pat}"
                if inner_op == "isnull" and len(inner_args) == 1:
                    val = expression_to_text(inner_args[0])
                    return f"{val} is not null"
            return f"not {expression_to_text(inner)}"

        # Format n-ary ops (like 'and', 'or')
        if op in ("and", "or"):

            def needs_parens(arg):
                return (
                    isinstance(arg, dict)
                    and arg.get("op") in ("and", "or")
                    and arg.get("op") != op
                )

            joined = f" {op} ".join(
                (
                    f"({expression_to_text(a)})"
                    if needs_parens(a)
                    else expression_to_text(a)
                )
                for a in args
            )
            return joined
        # Non-operator "op" values are function calls
        # (e.g. {"op": "Text", "args": [...]})
        if op not in _INFIX_OPERATORS:

            def format_func_arg(a):
                if isinstance(a, str):
                    if (a.startswith("'") and a.endswith("'")) or (
                        a.startswith('"') and a.endswith('"')
                    ):
                        return a
                    try:
                        float(a)
                        return a
                    except Exception:
                        return f"'{a}'"
                return expression_to_text(a)

            args_str = ", ".join(format_func_arg(a) for a in args)
            return f"{op}({args_str})"
        # Format binary comparison ops
        if len(args) == 2:
            left_arg, right_arg = args[0], args[1]
            left = expression_to_text(left_arg)
            # If left side is a sysId, right side is an identifier/enum — don't quote
            right_quote = not (isinstance(left_arg, dict) and "sysId" in left_arg)
            right = expression_to_text(right_arg, quote_bare_strings=right_quote)
            return f"{left} {op} {right}"
    # Handle sysId
    if "sysId" in expr:
        return str(expr["sysId"])
    if "property" in expr:
        return str(expr["property"])
    return str(expr)


def geojson_to_wkt(geojson: dict) -> str:
    """Convert a GeoJSON geometry dict to WKT text."""
    gtype = geojson.get("type", "")
    coords = geojson.get("coordinates")

    if gtype == "Point" and coords:
        return f"POINT({' '.join(str(c) for c in coords)})"
    if gtype == "LineString" and coords:
        pts = ", ".join(" ".join(str(c) for c in pt) for pt in coords)
        return f"LINESTRING({pts})"
    if gtype == "Polygon" and coords:
        rings = ", ".join(
            "(" + ", ".join(" ".join(str(c) for c in pt) for pt in ring) + ")"
            for ring in coords
        )
        return f"POLYGON({rings})"
    if gtype == "MultiPoint" and coords:
        pts = ", ".join("(" + " ".join(str(c) for c in pt) + ")" for pt in coords)
        return f"MULTIPOINT({pts})"
    if gtype == "MultiLineString" and coords:
        lines = ", ".join(
            "(" + ", ".join(" ".join(str(c) for c in pt) for pt in line) + ")"
            for line in coords
        )
        return f"MULTILINESTRING({lines})"
    if gtype == "MultiPolygon" and coords:
        polys = ", ".join(
            "("
            + ", ".join(
                "(" + ", ".join(" ".join(str(c) for c in pt) for pt in ring) + ")"
                for ring in poly
            )
            + ")"
            for poly in coords
        )
        return f"MULTIPOLYGON({polys})"
    if gtype == "GeometryCollection":
        geoms = geojson.get("geometries", [])
        parts = ", ".join(geojson_to_wkt(g) for g in geoms)
        return f"GEOMETRYCOLLECTION({parts})"
    return str(geojson)
