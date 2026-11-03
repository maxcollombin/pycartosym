"""Split a symbolizer with conditional expressions into exclusive variants.

CartoSym's conditional expression (``condition ? thenExp : elseExp``, the
``"?:"`` operation) has no SE 1.1 / SLD 1.0 equivalent in a parameter value:
the only SE functions (``Recode``, ``Categorize``) look up a *number*, and
the Annex B mapping of the conditional is GeoServer's own ``if_then_else``.

What SE does have is the rule filter. A rule whose symbolizer holds
``cond ? a : b`` is written as two rules with the same selector, one
filtered by ``cond`` (carrying ``a``) and one by ``NOT cond`` (carrying
``b``). Each feature matches exactly one of them, so the rendering is
unchanged.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from ...models.base import BaseCartoSymModel

# More rules than this is almost certainly independent conditions multiplying
# (n distinct conditions make 2**n rules): refuse rather than emit them.
MAX_VARIANTS = 16

_INVERSE_COMPARISON = {"<": ">=", "<=": ">", ">": "<=", ">=": "<"}
_KEEP = object()


def _plain(node: Any) -> Any:
    """The plain-JSON form of an expression (a model or a dict)."""
    if isinstance(node, BaseCartoSymModel):
        return node.model_dump(by_alias=True, exclude_none=True)
    return node


def _cond_parts(node: Any) -> tuple[Any, Any, Any] | None:
    """``(condition, then, else)`` if *node* is a ``?:`` operation."""
    if isinstance(node, dict):
        op, args = node.get("op"), node.get("args")
    else:
        op, args = getattr(node, "op", None), getattr(node, "args", None)
    if op == "?:" and isinstance(args, list) and len(args) == 3:
        return args[0], args[1], args[2]
    return None


def _children(node: Any) -> list[tuple[Any, Any]]:
    """``(key, child)`` pairs of a container node, for walking and rewriting."""
    if isinstance(node, dict):
        return list(node.items())
    if isinstance(node, list):
        return list(enumerate(node))
    if isinstance(node, BaseCartoSymModel):
        pairs = [(name, getattr(node, name)) for name in type(node).model_fields]
        pairs += list((node.__pydantic_extra__ or {}).items())
        return pairs
    return []


def _set_child(node: Any, key: Any, value: Any) -> None:
    if isinstance(node, (dict, list)):
        node[key] = value
    elif key in type(node).model_fields:
        # bypass validate_assignment: the substituted value is a branch of
        # the original expression, not a new value to coerce
        node.__dict__[key] = value
    else:
        node.__pydantic_extra__[key] = value


def _first_conditional(node: Any) -> tuple[Any, Any, Any] | None:
    """The first ``?:`` in document order (outermost first)."""
    parts = _cond_parts(node)
    if parts is not None:
        return parts
    for _, child in _children(node):
        found = _first_conditional(child)
        if found is not None:
            return found
    return None


def _rewrite(node: Any, cond_key: str, truth: bool) -> Any:
    """Replace every ``?:`` whose condition is *cond_key* by the chosen branch."""
    parts = _cond_parts(node)
    if parts is not None and _key(parts[0]) == cond_key:
        return _rewrite(parts[1] if truth else parts[2], cond_key, truth)
    for key, child in _children(node):
        if parts is not None and key == "args":
            # a different conditional: its condition stays, its branches change
            for i in (1, 2):
                child[i] = _rewrite(child[i], cond_key, truth)
            continue
        new = _rewrite(child, cond_key, truth)
        if new is not child:
            _set_child(node, key, new)
    return node


def _key(expr: Any) -> str:
    return json.dumps(_plain(expr), sort_keys=True, default=str)


def negate(cond: Any) -> Any:
    """The negation of a CQL2-JSON condition, as simple as it can be written."""
    cond = _plain(cond)
    if isinstance(cond, dict):
        if cond.get("op") == "not" and len(cond.get("args", [])) == 1:
            return cond["args"][0]
        op = cond.get("op")
        inverse = _INVERSE_COMPARISON.get(op) if isinstance(op, str) else None
        args = cond.get("args", [])
        # a system identifier (the scale) is never null: invert the operator
        # so it stays a scale bound
        if inverse and any(isinstance(a, dict) and "sysId" in a for a in args):
            return {"op": inverse, "args": args}
    return {"op": "not", "args": [cond]}


def _equality(cond: Any) -> tuple[str, Any] | None:
    """``(property, literal)`` for a ``property = literal`` condition."""
    cond = _plain(cond)
    if isinstance(cond, dict) and cond.get("op") == "=" and len(cond["args"]) == 2:
        left, right = cond["args"]
        if (
            isinstance(left, dict)
            and "property" in left
            and not isinstance(right, (dict, list))
        ):
            return left["property"], right
    return None


def split_conditionals(symbolizer: Any) -> list[tuple[list[Any], Any]]:
    """Split *symbolizer* into ``(conditions, symbolizer)`` exclusive variants.

    Each variant carries the CQL2-JSON conditions to AND onto the rule's
    selector and a copy of the symbolizer with every conditional replaced by
    the branch those conditions select. A symbolizer without conditionals
    gives a single variant with no condition. The same condition used several
    times splits once; a chain ``a ? x : (b ? y : z)`` gives three variants,
    and two ``=`` tests of one property against different values never meet.

    Raises:
        NotImplementedError: more than :data:`MAX_VARIANTS` variants.
    """
    if symbolizer is None:
        return [([], symbolizer)]
    variants: list[tuple[list[Any], Any]] = []
    _split(symbolizer, [], {}, variants)
    if len(variants) > MAX_VARIANTS:
        raise NotImplementedError(
            f"The conditional expressions of a symbolizer need {len(variants)} "
            f"SLD/SE rules (more than {MAX_VARIANTS}): independent conditions "
            "multiply, and SE has no conditional inside a parameter value"
        )
    return variants


def _split(
    symbolizer: Any,
    conds: list[Any],
    equal_to: dict[str, Any],
    out: list[tuple[list[Any], Any]],
) -> None:
    found = _first_conditional(symbolizer)
    if found is None:
        out.append((conds, symbolizer))
        return
    cond = _plain(found[0])
    key = _key(cond)
    for truth in (True, False):
        known = dict(equal_to)
        if truth and (eq := _equality(cond)) is not None:
            prop, literal = eq
            if prop in known and known[prop] != literal:
                continue  # k = 'a' and k = 'b' never hold together
            known[prop] = literal
        branch = _rewrite(copy.deepcopy(symbolizer), key, truth)
        _split(branch, [*conds, cond if truth else negate(cond)], known, out)
