"""MapLibre GL layer ``filter`` ↔ CartoSym selector (CQL2-JSON dict).

MapLibre filters come in two spellings — the *legacy* form
(``["==", "key", value]``) and the *expression* form
(``["==", ["get", "key"], value]``) — plus the combinators ``all`` /
``any`` / ``none``. Both spellings map to the same CQL2-JSON selector
dict that ``StylingRule.selector`` carries
(``{"op": "=", "args": [{"property": "key"}, value]}``).

Special MapLibre key ``$id`` and data-driven operands have no CQL2
equivalent and raise :exc:`NotImplementedError`. A
``sysId dataLayer.id = <name>`` equality conjunct — the implicit
self-reference a CartoSym-CSS ``RuleName[...]`` rule always carries (its
parser-generated ``sysId`` twin of the rule's own name, unrelated to any
real per-feature filtering) — is dropped rather than raised on: this
codec has no data-source concept (see :mod:`.writer`'s module docstring)
for a real ``dataLayer.id`` to bind to, and the value is redundant with
the MapLibre layer's own ``id`` regardless (see
:func:`strip_datalayer_id`). Any other ``sysId``, or a ``dataLayer.id``
compared with anything but ``=``, still raises — real information this
codec has no target for.

``sysId dataLayer.featuresGeometryDimensions`` is the one exception: a
``=``/``!=`` comparison against ``0``/``1``/``2`` maps to (from) the
MapLibre ``["==``/``!=", ["geometry-type"], "Point"/"LineString"/
"Polygon"]`` filter expression — unlike ``dataLayer.id``/``dataLayer.type``
this is real per-feature information (not provably redundant with how a
rule was routed to layers, see :mod:`.writer`), and ``geometry-type``
happens to be MapLibre's own faithful equivalent (see
:func:`_geometry_dimensions_filter_conjunct`). ``$type`` and a bare
``geometry-type`` compared with anything else still raise — no mapping.

A selector ``between`` predicate (``{"op": "between", "args": [prop, lo,
hi]}``) has no single MapLibre filter primitive, so it decomposes into
``["all", [">=", …, lo], ["<=", …, hi]]`` — two ordinary comparisons a
reader already folds back into an equivalent (if differently-shaped)
``and``-of-two-comparisons selector, rather than reconstructing
``between`` itself. A ``like``/``ilike`` predicate always raises —
MapLibre filters (legacy or expression form) have no SQL
``LIKE``/wildcard string-matching operator, a permanent gap rather than
a missing wire-up. ``isNull`` op comparisons are matched
case-insensitively (see :func:`_is_op`): this codec's own selectors
spell it ``isNull``, but the SLD reader emits lowercase ``isnull`` for
``PropertyIsNull`` (`StylingRule.selector` has no fixed op casing to
enforce), and both must be accepted here.
"""

from __future__ import annotations

from typing import Any

from ._zoom import zoom_filter_conjunct

# MapLibre comparison op -> CQL2 op
_CMP: dict[str, str] = {
    "==": "=",
    "!=": "<>",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
}
_CMP_INV = {v: k for k, v in _CMP.items()}

_SPECIAL_KEYS = {"$type", "$id"}

# CartoSym dataLayer.featuresGeometryDimensions <-> MapLibre geometry-type.
# The MapLibre expression collapses Multi* onto their base type (documented
# in the vendored v8.json spec), matching the CartoSym dimension's own
# 0/1/2 = point/curve/surface convention (confirmed against the public
# examples corpus: point/line/polygon feature layers use exactly these).
_GEOMETRY_TYPE_BY_DIMENSION = {0: "Point", 1: "LineString", 2: "Polygon"}
_DIMENSION_BY_GEOMETRY_TYPE = {v: k for k, v in _GEOMETRY_TYPE_BY_DIMENSION.items()}
_FEATURES_GEOMETRY_DIMENSIONS_SYSID = "dataLayer.featuresGeometryDimensions"


def _is_op(op: Any, name: str) -> bool:
    """Compare a selector ``op`` to *name* case-insensitively.

    The CQL2 model's own convention capitalises ``isNull``, and this
    codec's own :func:`filter_to_selector` emits that spelling — but the
    SLD reader (``codecs/sld/_filter.py``) always emits lowercase
    ``isnull`` for ``PropertyIsNull`` (itself case-insensitive on the way
    back out to SLD/SE XML). ``StylingRule.selector`` has no fixed op
    casing to enforce (a plain ``dict[str, Any]``, see
    ``models/styles.py``), so consuming it here must tolerate either.
    """
    return isinstance(op, str) and op.lower() == name.lower()


# ── MapLibre filter → selector ────────────────────────────────────────────


def _operand_to_property(operand: Any) -> dict[str, str]:
    """Turn a filter operand naming a feature property into ``{"property": name}``."""
    if isinstance(operand, str):
        if operand in _SPECIAL_KEYS:
            raise NotImplementedError(
                f"MapLibre filter key {operand!r} has no CartoSym selector mapping"
            )
        return {"property": operand}
    if (
        isinstance(operand, list)
        and len(operand) == 2
        and operand[0] == "get"
        and isinstance(operand[1], str)
    ):
        return {"property": operand[1]}
    raise NotImplementedError(
        f"MapLibre filter operand {operand!r} is not a plain property reference"
    )


def _literal(operand: Any) -> Any:
    if isinstance(operand, list):
        if len(operand) == 2 and operand[0] == "literal":
            return operand[1]
        raise NotImplementedError(
            f"MapLibre filter value {operand!r} is data-driven — not mapped"
        )
    return operand


def filter_to_selector(mb_filter: list[Any]) -> dict[str, Any]:
    """Convert a MapLibre layer ``filter`` to a CartoSym selector dict."""
    if not isinstance(mb_filter, list) or not mb_filter:
        raise NotImplementedError(f"unrecognised MapLibre filter {mb_filter!r}")

    op = mb_filter[0]
    args = mb_filter[1:]

    if op in ("all", "any"):
        return {
            "op": "and" if op == "all" else "or",
            "args": [filter_to_selector(f) for f in args],
        }
    if op == "none":
        return {
            "op": "not",
            "args": [{"op": "or", "args": [filter_to_selector(f) for f in args]}],
        }
    if op == "!":
        (inner,) = args
        return {"op": "not", "args": [filter_to_selector(inner)]}

    if op in _CMP:
        prop, value = args
        if prop == ["geometry-type"]:
            if op not in ("==", "!="):
                raise NotImplementedError(
                    f"MapLibre geometry-type filter operator {op!r} has no "
                    "CartoSym selector mapping (only ==/!= do)"
                )
            dimension = _DIMENSION_BY_GEOMETRY_TYPE.get(_literal(value))
            if dimension is None:
                raise NotImplementedError(
                    f"MapLibre geometry-type value {value!r} has no CartoSym "
                    "featuresGeometryDimensions mapping"
                )
            return {
                "op": _CMP[op],
                "args": [
                    {"sysId": _FEATURES_GEOMETRY_DIMENSIONS_SYSID},
                    dimension,
                ],
            }
        return {
            "op": _CMP[op],
            "args": [_operand_to_property(prop), _literal(value)],
        }

    if op in ("in", "!in"):
        prop, *rest = args
        # legacy: ["in", "k", v1, v2, …] — each remaining arg is a value.
        # expression: ["in", ["get","k"], ["literal", [...]]] — one list arg.
        if len(rest) == 1 and isinstance(rest[0], list):
            values = list(_literal(rest[0]))
        else:
            values = list(rest)
        pred = {"op": "in", "args": [_operand_to_property(prop), values]}
        return {"op": "not", "args": [pred]} if op == "!in" else pred

    if op in ("has", "!has"):
        (prop,) = args
        is_null = {"op": "isNull", "args": [_operand_to_property(prop)]}
        return is_null if op == "!has" else {"op": "not", "args": [is_null]}

    raise NotImplementedError(f"MapLibre filter operator {op!r} is not supported")


def strip_datalayer_id(selector: Any) -> Any:
    """Drop a ``sysId dataLayer.id = <literal>`` conjunct from *selector*.

    Walks the same ``and``-conjunction shape :func:`._zoom.extract_zoom_range`
    does, removing any ``dataLayer.id = <name>`` equality leaf wherever it
    appears (either operand order) and re-collapsing what remains — a
    single surviving conjunct is unwrapped, none leaves ``None``. See the
    module docstring for why this one sysId is dropped rather than raised
    on.
    """
    if not isinstance(selector, dict):
        return selector
    op = selector.get("op")
    if op == "and":
        kept = [
            stripped
            for a in selector.get("args", [])
            if (stripped := strip_datalayer_id(a)) is not None
        ]
        if not kept:
            return None
        if len(kept) == 1:
            return kept[0]
        return {"op": "and", "args": kept}
    if op == "=":
        args = selector.get("args", [])
        if len(args) == 2 and any(
            isinstance(a, dict) and a.get("sysId") == "dataLayer.id" for a in args
        ):
            return None
    return selector


# ── selector → MapLibre filter ───────────────────────────────────────────


def _property_name(arg: Any) -> str:
    if isinstance(arg, dict):
        name = arg.get("property")
        if isinstance(name, str):
            return name
    raise NotImplementedError(
        f"selector operand {arg!r} → MapLibre filter needs a plain property "
        "(sysId / expression operands are not mapped)"
    )


def _comparison_value(value: Any) -> Any:
    """Validate a comparison's right-hand operand is a plain JSON literal.

    A ``str``/``int``/``float``/``bool``/``list`` passes through
    unchanged — already valid MapLibre filter syntax. A dict here is a
    ``sysId``/``property``/expression operand (e.g.
    ``viz.timeInterval.start.date``, a per-request "current view" value
    with no MapLibre equivalent — unlike ``viz.sd``, which maps to
    ``["zoom"]``) — embedding it verbatim would produce a bare object
    where MapLibre's expression grammar requires a literal, which
    ``gl-style-validate`` rejects, so this raises instead.
    """
    if isinstance(value, dict):
        sys_id = value.get("sysId")
        if sys_id is not None:
            raise NotImplementedError(
                f"system identifier {sys_id!r} has no MapLibre filter "
                "mapping (comparison operand)"
            )
        raise NotImplementedError(
            f"selector comparison operand {value!r} → MapLibre filter is "
            "not a plain literal"
        )
    return value


def _geometry_dimensions_filter_conjunct(selector: Any) -> list[Any] | None:
    """Map a ``dataLayer.featuresGeometryDimensions`` comparison to a filter.

    A ``=``/``<>`` comparison maps to the equivalent MapLibre
    ``["=="/"!=", ["geometry-type"], …]`` filter expression. Unlike
    ``dataLayer.type``/``dataLayer.id``, this sysId is not provably
    redundant with how a rule was routed to layers (see :mod:`.writer`'s
    module docstring — a rule on line-dimensioned features can still add
    a point layer via a ``marker`` element, for instance), so it maps to
    a real filter conjunct rather than being dropped. Returns ``None``
    for any other sysId, comparison operator, or dimension value, leaving
    the selector to raise further down the pipeline (only ``=``/``<>``
    against a known ``0``/``1``/``2`` dimension is mapped — see module
    docstring).
    """
    if not isinstance(selector, dict):
        return None
    op = selector.get("op")
    if op not in ("=", "<>"):
        return None
    args = selector.get("args", [])
    if len(args) != 2:
        return None
    left, right = args
    if (
        isinstance(left, dict)
        and left.get("sysId") == _FEATURES_GEOMETRY_DIMENSIONS_SYSID
    ):
        dimension = right
    elif (
        isinstance(right, dict)
        and right.get("sysId") == _FEATURES_GEOMETRY_DIMENSIONS_SYSID
    ):
        dimension = left
    else:
        return None
    geometry_type = _GEOMETRY_TYPE_BY_DIMENSION.get(dimension)
    if geometry_type is None:
        return None
    return ["==" if op == "=" else "!=", ["geometry-type"], geometry_type]


def selector_to_filter(selector: Any) -> list[Any]:
    """Convert a CartoSym selector dict to a MapLibre (expression-form) filter."""
    if not isinstance(selector, dict) or "op" not in selector:
        raise NotImplementedError(
            f"selector {selector!r} → MapLibre filter is not supported"
        )

    # A viz.sd comparison with no minzoom/maxzoom shape (extract_zoom_range
    # already pulled out the two that do) still has an exact MapLibre
    # equivalent via the ["zoom"] filter expression — see
    # ``_zoom.zoom_filter_conjunct``. Checked ahead of the generic
    # property-comparison dispatch below since viz.sd is a sysId, not a
    # feature property.
    zoom_conjunct = zoom_filter_conjunct(selector)
    if zoom_conjunct is not None:
        return zoom_conjunct

    # Same reasoning: dataLayer.featuresGeometryDimensions is a sysId, not
    # a feature property, and has an exact MapLibre equivalent of its own
    # (see _geometry_dimensions_filter_conjunct) — checked ahead of the
    # generic property-comparison dispatch below.
    geometry_conjunct = _geometry_dimensions_filter_conjunct(selector)
    if geometry_conjunct is not None:
        return geometry_conjunct

    op = selector["op"]
    args = selector.get("args", [])

    if op == "and":
        return ["all", *[selector_to_filter(a) for a in args]]
    if op == "or":
        return ["any", *[selector_to_filter(a) for a in args]]
    if op == "not":
        (inner,) = args
        if isinstance(inner, dict) and _is_op(inner.get("op"), "isNull"):
            # ¬(k is null)  ==  "feature has k"
            return ["has", _property_name(inner["args"][0])]
        if isinstance(inner, dict) and inner.get("op") == "in":
            prop, values = inner["args"]
            return ["!in", ["get", _property_name(prop)], ["literal", list(values)]]
        return ["!", selector_to_filter(inner)]

    if op in _CMP_INV:
        left, right = args
        return [_CMP_INV[op], ["get", _property_name(left)], _comparison_value(right)]

    if op == "in":
        prop, values = args
        return ["in", ["get", _property_name(prop)], ["literal", list(values)]]
    if _is_op(op, "isNull"):
        return ["!", ["has", _property_name(args[0])]]
    if op == "between":
        prop, low, high = args
        target = ["get", _property_name(prop)]
        return [
            "all",
            [">=", target, _comparison_value(low)],
            ["<=", target, _comparison_value(high)],
        ]
    if _is_op(op, "like"):
        raise NotImplementedError(
            "selector operator 'like' → MapLibre filter is not supported — "
            "MapLibre filters have no SQL LIKE / wildcard string-matching "
            "operator (legacy or expression form)"
        )

    raise NotImplementedError(
        f"selector operator {op!r} → MapLibre filter is not supported"
    )
