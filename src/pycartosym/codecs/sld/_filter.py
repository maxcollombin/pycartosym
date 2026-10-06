"""OGC Filter Encoding <-> CartoSym selector dict mapping, both directions.

Ground truth for the selector dict shapes handled here is
``converter.py::_format_selector_expr``/``_selector_to_cscss`` — CartoSym's
``StylingRule.selector`` is a raw CQL2-JSON-shaped ``dict``/``list``/``str``
at runtime, not the ``Expression`` Pydantic hierarchy in
``models/expressions.py`` (that hierarchy is not wired into selector
validation).

Selector constructs with no faithful Filter Encoding equivalent are noted
inline at each such site.
"""

from __future__ import annotations

from typing import Any

from lxml import etree

from ._xml_helpers import GML, ogc_el

_COMPARISON_OPS = {
    "=": "PropertyIsEqualTo",
    "<>": "PropertyIsNotEqualTo",
    "<": "PropertyIsLessThan",
    ">": "PropertyIsGreaterThan",
    "<=": "PropertyIsLessThanOrEqualTo",
    ">=": "PropertyIsGreaterThanOrEqualTo",
}
_COMPARISON_TAGS = {v: k for k, v in _COMPARISON_OPS.items()}
# Legacy CS-JSON spelling of CQL2 `<>`, still accepted on write.
_COMPARISON_OPS["!="] = _COMPARISON_OPS["<>"]

# CQL2 named spatial-relation predicate -> Filter 1.1.0 spatial operator
# element (all ogc:BinarySpatialOpType, substitutionGroup ogc:spatialOps).
# Annex B (3-geometry) maps these to <ogc:Function>, which is wrong: they
# are proper ogc:BinarySpatialOpType elements. s_covers/s_coveredBy have
# no Filter 1.1.0 element (FES 2.0 only) and stay unmapped.
_SPATIAL_OPS = {
    "s_intersects": "Intersects",
    "s_within": "Within",
    "s_contains": "Contains",
    "s_disjoint": "Disjoint",
    "s_touches": "Touches",
    "s_overlaps": "Overlaps",
    "s_crosses": "Crosses",
    "s_equals": "Equals",
}
_SPATIAL_TAGS = {v: k for k, v in _SPATIAL_OPS.items()}

_TEXT_OP_PATTERNS = {
    "contains": lambda pat: f"%{pat}%",
    "startswith": lambda pat: f"{pat}%",
    "endswith": lambda pat: f"%{pat}",
}


_DATALAYER_METADATA_SYSIDS = (
    "dataLayer.type",
    "dataLayer.featuresGeometryDimensions",
)

_SCALE_SYSID = "viz.sd"
_PASS_SYSID = "viz.pass"
_FLIP_OP = {
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "=": "=",
    "<>": "<>",
    "!=": "<>",
}


def _is_sysid_eq(expr: Any, sys_id: str) -> bool:
    return (
        isinstance(expr, dict)
        and expr.get("op") == "="
        and isinstance(expr.get("args"), list)
        and len(expr["args"]) == 2
        and isinstance(expr["args"][0], dict)
        and expr["args"][0].get("sysId") == sys_id
    )


def _is_datalayer_id_eq(expr: Any) -> bool:
    return _is_sysid_eq(expr, "dataLayer.id")


def _flatten_and_conjuncts(selector: Any) -> list[Any]:
    """Flatten a nested ``{"op": "and", ...}`` chain into a list of conjuncts.

    Handles left-nested, right-nested and flat n-ary ``and`` chains. Only
    ``and`` is descended into — ``or``/``not``/comparisons flatten to a
    single-element list containing themselves.
    """
    if (
        isinstance(selector, dict)
        and selector.get("op") == "and"
        and isinstance(selector.get("args"), list)
    ):
        out: list[Any] = []
        for arg in selector["args"]:
            out.extend(_flatten_and_conjuncts(arg))
        return out
    return [selector]


def _reassemble_and(conjuncts: list[Any]) -> Any | None:
    if not conjuncts:
        return None
    if len(conjuncts) == 1:
        return conjuncts[0]
    return {"op": "and", "args": conjuncts}


def extract_feature_type_name(
    selector: dict | None,
) -> tuple[str | None, dict | None]:
    """Split the ``dataLayer.*`` conjuncts out of *selector*.

    Pulls ``dataLayer.id`` / ``dataLayer.type`` /
    ``dataLayer.featuresGeometryDimensions`` from anywhere in an
    arbitrarily-nested ``and`` chain (real generated CS-JSON right-nests
    these three conjuncts, not a flat 3-ary ``and``).

    ``dataLayer.id`` is captured and returned for the caller to emit as
    ``<se:FeatureTypeName>``. ``dataLayer.type``/
    ``dataLayer.featuresGeometryDimensions`` are silently dropped — SLD/SE
    has no representation for either; this is a permanent, write-only lossy
    simplification. Mirrors the same detection logic as
    ``converter.py:217-244`` / ``ast_converter.py:1014,1038``.

    Returns:
    -------
    (feature_type_name, remaining_selector)
        ``remaining_selector`` is ``None`` if nothing is left, the bare
        leaf if exactly one conjunct remains, or a flat n-ary ``and`` of
        whatever remains otherwise.
    """
    if selector is None:
        return None, None
    conjuncts = _flatten_and_conjuncts(selector)
    id_val: str | None = None
    remaining: list[Any] = []
    for conjunct in conjuncts:
        if id_val is None and _is_sysid_eq(conjunct, "dataLayer.id"):
            id_val = _coerce_id_value(conjunct["args"][1])
        elif any(_is_sysid_eq(conjunct, s) for s in _DATALAYER_METADATA_SYSIDS):
            continue  # dropped, write-only (no SLD/SE representation)
        else:
            remaining.append(conjunct)
    return id_val, _reassemble_and(remaining)


def merge_feature_type_name(name: str | None, selector: dict | None) -> dict | None:
    """Reader-side inverse of :func:`extract_feature_type_name`.

    Only ``dataLayer.id`` is reconstructed — ``dataLayer.type``/
    ``dataLayer.featuresGeometryDimensions`` have no SLD/SE representation
    to reconstruct from, so a selector written with those conjuncts will
    not round-trip them back.
    """
    if name is None:
        return selector
    id_eq = {"op": "=", "args": [{"sysId": "dataLayer.id"}, name]}
    if selector is None:
        return id_eq
    return {"op": "and", "args": [id_eq, selector]}


def extract_visualization_pass(
    selector: dict | None,
) -> tuple[int | None, dict | None]:
    """Split a literal ``viz.pass = N`` conjunct out of *selector*.

    ``viz.pass`` (visualization rendering pass) maps to the order of
    ``se:FeatureTypeStyle`` elements in a ``se:UserStyle``: every feature
    is drawn with an earlier style before any is drawn with a later one.
    Same flatten/reassemble pattern as :func:`extract_feature_type_name`.
    A ``viz.pass`` compared otherwise (an attribute-driven expression, a
    range) stays in the remaining selector, where the filter encoder
    rejects it: a feature-dependent pass has no static FeatureTypeStyle.

    Returns:
    -------
    (pass_number, remaining_selector)
    """
    if selector is None:
        return None, None
    pass_number: int | None = None
    remaining: list[Any] = []
    for conjunct in _flatten_and_conjuncts(selector):
        value = conjunct["args"][1] if _is_sysid_eq(conjunct, _PASS_SYSID) else None
        if (
            pass_number is None
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            pass_number = value
        else:
            remaining.append(conjunct)
    return pass_number, _reassemble_and(remaining)


def merge_visualization_pass(
    pass_number: int | None, selector: dict | None
) -> dict | None:
    """Reader-side inverse of :func:`extract_visualization_pass`."""
    if pass_number is None:
        return selector
    pass_eq = {"op": "=", "args": [{"sysId": _PASS_SYSID}, pass_number]}
    if selector is None:
        return pass_eq
    return {"op": "and", "args": [pass_eq, selector]}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scale_bound(expr: Any) -> tuple[str, Any] | None:
    """Classify *expr* as a ``viz.sd`` scale-range bound.

    Returns ``("min", value)`` for a lower bound (``viz.sd > / >= N``),
    ``("max", value)`` for an upper bound (``viz.sd < / <= N``), or
    ``None`` if *expr* is not a ``viz.sd`` comparison at all. The operand
    order may be either way round (``viz.sd < N`` or ``N > viz.sd``).

    Raises:
    ------
    NotImplementedError
        If *expr* compares ``viz.sd`` with ``=``/``!=`` — neither can be
        expressed as an ``se:Min/MaxScaleDenominator`` range.
    """
    if not (
        isinstance(expr, dict)
        and isinstance(expr.get("args"), list)
        and len(expr["args"]) == 2
    ):
        return None
    left, right = expr["args"]
    raw_op = expr.get("op")
    op = raw_op if isinstance(raw_op, str) else ""
    if (
        isinstance(left, dict)
        and left.get("sysId") == _SCALE_SYSID
        and _is_number(right)
    ):
        value = right
    elif (
        isinstance(right, dict)
        and right.get("sysId") == _SCALE_SYSID
        and _is_number(left)
    ):
        op = _FLIP_OP.get(op, "")
        value = left
    else:
        return None
    if op in ("<", "<="):
        return "max", value
    if op in (">", ">="):
        return "min", value
    raise NotImplementedError(
        f"viz.sd {expr.get('op')!r} comparison has no se:ScaleDenominator "
        "mapping — only <, <=, >, >= define a scale range"
    )


def extract_scale_denominators(
    selector: dict | None,
) -> tuple[Any | None, Any | None, dict | None]:
    """Split ``viz.sd`` scale-range conjuncts out of *selector*.

    ``viz.sd`` (visualization scale denominator) maps 1:1 to SE's
    ``se:MinScaleDenominator`` / ``se:MaxScaleDenominator`` on
    ``se:RuleType``. This pulls the ``viz.sd`` comparison conjuncts out of
    an arbitrarily-nested ``and`` chain (same
    flatten/reassemble pattern as :func:`extract_feature_type_name`) for
    the caller to emit as those two elements; whatever is left stays for
    the ``ogc:Filter``.

    Returns ``(min_sd, max_sd, remaining_selector)``. When a cascade merge
    leaves several bounds on the same side (``viz.sd < 200000`` from an
    ancestor and ``viz.sd < 10000`` from the node), the tightest wins.

    Raises:
    ------
    NotImplementedError
        If ``viz.sd`` is compared with an operator that is not a range
        bound (``=``/``!=``).
    """
    if selector is None:
        return None, None, None
    min_sd: Any | None = None
    max_sd: Any | None = None
    remaining: list[Any] = []
    for conjunct in _flatten_and_conjuncts(selector):
        bound = _scale_bound(conjunct)
        if bound is None:
            remaining.append(conjunct)
            continue
        kind, value = bound
        if kind == "min":
            if min_sd is None or value > min_sd:
                min_sd = value
        else:
            if max_sd is None or value < max_sd:
                max_sd = value
    return min_sd, max_sd, _reassemble_and(remaining)


def merge_scale_denominators(
    min_sd: Any | None,
    max_sd: Any | None,
    selector: dict | None,
) -> dict | None:
    """Reader-side inverse of :func:`extract_scale_denominators`.

    ``se:MinScaleDenominator M`` -> ``viz.sd >= M`` and
    ``se:MaxScaleDenominator N`` -> ``viz.sd < N`` (SE's rule-applies
    range is ``M <= scale < N``), AND-merged ahead of any selector parsed
    from ``ogc:Filter``. A zero lower bound is SE's implicit default and
    is dropped rather than reconstructed as ``viz.sd >= 0``.
    """
    conjuncts: list[Any] = []
    if min_sd is not None and min_sd != 0:
        conjuncts.append({"op": ">=", "args": [{"sysId": _SCALE_SYSID}, min_sd]})
    if max_sd is not None:
        conjuncts.append({"op": "<", "args": [{"sysId": _SCALE_SYSID}, max_sd]})
    if selector is not None:
        conjuncts.append(selector)
    return _reassemble_and(conjuncts)


def _coerce_id_value(value: Any) -> str:
    if isinstance(value, dict) and "property" in value:
        return str(value["property"])
    return str(value)


def selector_to_filter_xml(selector: dict | None) -> etree._Element | None:
    """Convert a CartoSym selector dict into an ``<ogc:Filter>`` element.

    *selector* should already have any ``dataLayer.id`` conjunct removed
    (via :func:`extract_feature_type_name`) by the caller.
    """
    if selector is None:
        return None
    filt = ogc_el("Filter")
    filt.append(_expr_to_filter_xml(selector))
    return filt


def filter_xml_to_selector(filter_elem: etree._Element) -> dict:
    """Convert an ``<ogc:Filter>`` element back into a selector dict."""
    children = [c for c in filter_elem if isinstance(c.tag, str)]
    if len(children) != 1:
        raise NotImplementedError(
            f"ogc:Filter with {len(children)} top-level predicates is not "
            "supported (expected exactly 1)"
        )
    return _filter_xml_to_expr(children[0])


# ---------------------------------------------------------------------------
# Writer direction: selector dict -> ogc:Filter predicate element
# ---------------------------------------------------------------------------


def _operand_to_xml(operand: Any) -> etree._Element:
    """Build an ``ogc:PropertyName`` or ``ogc:Literal`` element for *operand*."""
    if isinstance(operand, dict):
        if "property" in operand and len(operand) == 1:
            return ogc_el("PropertyName", text=operand["property"])
        if "sysId" in operand:
            raise NotImplementedError(
                f"sysId {operand['sysId']!r} other than 'dataLayer.id' has no "
                "SLD/SE mapping in this codec"
            )
        if "date" in operand and len(operand) == 1:
            return ogc_el("Literal", text=str(operand["date"]))
        if "timestamp" in operand and len(operand) == 1:
            return ogc_el("Literal", text=str(operand["timestamp"]))
        raise NotImplementedError(
            f"Selector operand shape {operand!r} (interval / geometry literal "
            "/ other CQL2 construct) has no SLD/SE mapping in this codec"
        )
    if isinstance(operand, bool):
        return ogc_el("Literal", text="true" if operand else "false")
    return ogc_el("Literal", text=str(operand))


def _expr_to_filter_xml(expr: Any) -> etree._Element:
    """Recursively build the predicate subtree for one selector expression."""
    if not isinstance(expr, dict) or "op" not in expr:
        raise NotImplementedError(f"Unsupported selector expression: {expr!r}")

    op = expr["op"]
    op_lower = op.lower() if isinstance(op, str) else ""
    args = expr.get("args", [])

    if op_lower in ("and", "or"):
        tag = "And" if op_lower == "and" else "Or"
        el = ogc_el(tag)
        for a in args:
            el.append(_expr_to_filter_xml(a))
        return el

    if op_lower == "not" and len(args) == 1:
        el = ogc_el("Not")
        el.append(_expr_to_filter_xml(args[0]))
        return el

    if op in _COMPARISON_OPS and len(args) == 2:
        el = ogc_el(_COMPARISON_OPS[op])
        el.append(_operand_to_xml(args[0]))
        el.append(_operand_to_xml(args[1]))
        return el

    if op_lower == "between" and len(args) == 3:
        el = ogc_el("PropertyIsBetween")
        el.append(_operand_to_xml(args[0]))
        lower = ogc_el("LowerBoundary", parent=el)
        lower.append(_operand_to_xml(args[1]))
        upper = ogc_el("UpperBoundary", parent=el)
        upper.append(_operand_to_xml(args[2]))
        return el

    if op_lower in ("like", "ilike") and len(args) == 2:
        el = ogc_el("PropertyIsLike")
        el.set("wildCard", "%")
        el.set("singleChar", "_")
        el.set("escapeChar", "\\")
        el.append(_operand_to_xml(args[0]))
        el.append(_operand_to_xml(args[1]))
        return el

    if op_lower == "isnull" and len(args) == 1:
        el = ogc_el("PropertyIsNull")
        el.append(_operand_to_xml(args[0]))
        return el

    if op_lower in _TEXT_OP_PATTERNS and len(args) == 2:
        val, pattern = args
        if not isinstance(pattern, str):
            raise NotImplementedError(
                f"{op} with a non-literal pattern has no SLD/SE mapping"
            )
        el = ogc_el("PropertyIsLike")
        el.set("wildCard", "%")
        el.set("singleChar", "_")
        el.set("escapeChar", "\\")
        el.append(_operand_to_xml(val))
        el.append(ogc_el("Literal", text=_TEXT_OP_PATTERNS[op_lower](pattern)))
        return el

    if op_lower in _SPATIAL_OPS and len(args) == 2:
        el = ogc_el(_SPATIAL_OPS[op_lower])
        el.append(_operand_to_xml(args[0]))
        el.append(_operand_to_xml(args[1]))
        return el

    raise NotImplementedError(
        f"Selector operator {op!r} has no SLD/SE Filter Encoding mapping in "
        "this codec's scope"
    )


def bbox_to_filter_xml(bbox: list[float]) -> etree._Element:
    """Build an ``<ogc:BBOX>`` element from a ``[minx, miny, maxx, maxy]`` list."""
    el = ogc_el("BBOX")
    envelope = etree.SubElement(el, f"{GML}Envelope")
    minx, miny, maxx, maxy = bbox
    etree.SubElement(envelope, f"{GML}lowerCorner").text = f"{minx} {miny}"
    etree.SubElement(envelope, f"{GML}upperCorner").text = f"{maxx} {maxy}"
    return el


# ---------------------------------------------------------------------------
# Reader direction: ogc:Filter predicate element -> selector dict
# ---------------------------------------------------------------------------


def _local(elem: etree._Element) -> str:
    return str(etree.QName(elem).localname)


def _coerce_literal(text: str | None) -> Any:
    if text is None:
        return None
    if text in ("true", "false"):
        return text == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _operand_from_xml(elem: etree._Element) -> Any:
    tag = _local(elem)
    if tag == "PropertyName":
        return {"property": elem.text}
    if tag == "Literal":
        return _coerce_literal(elem.text)
    raise NotImplementedError(f"Unsupported Filter operand element <{tag}>")


def _children(elem: etree._Element) -> list[etree._Element]:
    return [c for c in elem if isinstance(c.tag, str)]


def _filter_xml_to_expr(elem: etree._Element) -> dict:
    tag = _local(elem)

    if tag in ("And", "Or"):
        return {
            "op": "and" if tag == "And" else "or",
            "args": [_filter_xml_to_expr(c) for c in _children(elem)],
        }

    if tag == "Not":
        return {"op": "not", "args": [_filter_xml_to_expr(_children(elem)[0])]}

    if tag in _COMPARISON_TAGS:
        left, right = _children(elem)
        return {
            "op": _COMPARISON_TAGS[tag],
            "args": [_operand_from_xml(left), _operand_from_xml(right)],
        }

    if tag == "PropertyIsBetween":
        value_el, lower_el, upper_el = _children(elem)
        return {
            "op": "between",
            "args": [
                _operand_from_xml(value_el),
                _operand_from_xml(_children(lower_el)[0]),
                _operand_from_xml(_children(upper_el)[0]),
            ],
        }

    if tag == "PropertyIsLike":
        left, right = _children(elem)
        return {
            "op": "like",
            "args": [_operand_from_xml(left), _operand_from_xml(right)],
        }

    if tag == "PropertyIsNull":
        return {"op": "isnull", "args": [_operand_from_xml(_children(elem)[0])]}

    if tag in _SPATIAL_TAGS:
        left, right = _children(elem)
        return {
            "op": _SPATIAL_TAGS[tag],
            "args": [_operand_from_xml(left), _operand_from_xml(right)],
        }

    if tag == "BBOX":
        children = _children(elem)
        envelope = children[-1]
        lower = envelope.find(f"{GML}lowerCorner")
        upper = envelope.find(f"{GML}upperCorner")
        minx, miny = (float(v) for v in lower.text.split())
        maxx, maxy = (float(v) for v in upper.text.split())
        return {"bbox": [minx, miny, maxx, maxy]}

    raise NotImplementedError(
        f"ogc:Filter construct <{tag}> has no CartoSym selector mapping in "
        "this codec's scope"
    )
