"""Flatten CartoSym nested-rule *cascades* into independent rules.

Shared by any codec whose target format has no cascade concept of its own
(SLD/SE's ``se:Rule``, MapLibre's flat ``layers`` list — a
``StylingRule`` here, unlike either, nests refinements). A
``StylingRule.nestedRules`` entry with a selector is a cascading refinement:
it applies only where its parent is selected, so its selector is AND-ed with
the parent's, and its symbolizer is a partial override merged onto the
parent's (CartoSym's ``alter`` mechanism, including indexed
``marker.elements[N]`` / ``label.elements[N]`` element overrides). A nested
rule **without** a selector is not a refinement at all: it is the same as
removing its curly brackets, so its symbolizer is merged into its parent's
(see :func:`_fold_selectorless`). Each subtree is pre-flattened here into
independent rules, each carrying the fully-merged selector and symbolizer,
parent before child (so a document-order-painting consumer — SE's
``se:Rule`` list — keeps the child on top).
"""

from __future__ import annotations

from typing import Any

_GRAPHIC_CONTAINER_KEYS = ("marker", "label")


def flatten_cascade_rules(rule_dicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten every cascade in *rule_dicts* (``StylingRule.to_dict()`` shape)."""
    out: list[dict[str, Any]] = []
    for rd in rule_dicts:
        out.extend(_flatten(rd, parent_selector=None, parent_sym={}))
    return out


def _and(a: Any | None, b: Any | None) -> Any | None:
    if a is None:
        return b
    if b is None:
        return a
    return {"op": "and", "args": [a, b]}


def _carry_name(rule: dict[str, Any]) -> dict[str, Any]:
    return {"name": rule["name"]} if "name" in rule else {}


def _fold_selectorless(
    rule: dict[str, Any], sym: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge *rule*'s selector-less nested rules into *sym*.

    A nested rule with an empty selector is the same as removing its curly
    brackets: it is not a true nested rule, its symbolizer simply overrides
    and merges with its parent's, and its own nested rules become the
    parent's. Returns the merged symbolizer and the nested rules left to
    flatten as refinements, in document order.
    """
    remaining: list[dict[str, Any]] = []
    for child in rule.get("nestedRules") or []:
        if child.get("selector") is None:
            sym, rest = _fold_selectorless(
                child, _deep_merge(sym, child.get("symbolizer") or {})
            )
            remaining.extend(rest)
        else:
            remaining.append(child)
    return sym, remaining


def _flatten(
    rule: dict[str, Any],
    parent_selector: Any | None,
    parent_sym: dict[str, Any],
) -> list[dict[str, Any]]:
    own_sym = rule.get("symbolizer") or {}
    merged_sym, refinements = _fold_selectorless(rule, _deep_merge(parent_sym, own_sym))
    merged_sel = _and(parent_selector, rule.get("selector"))

    node = _carry_name(rule)
    if merged_sel is not None:
        node["selector"] = merged_sel
    if merged_sym:
        node["symbolizer"] = merged_sym

    result = [node]
    for child in refinements:
        result.extend(_flatten(child, merged_sel, merged_sym))
    return result


# ---------------------------------------------------------------------------
# Symbolizer deep-merge
# ---------------------------------------------------------------------------


def _deep_merge(base: Any, override: Any) -> Any:
    """Deep-merge two symbolizer dicts; *override* wins on scalar clashes.

    ``marker``/``label`` containers are merged with element-list awareness
    so an indexed ``{"index": N, "value": ...}`` override replaces one
    element of the inherited list rather than clobbering the whole list.
    """
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for key, value in override.items():
        if (
            key in _GRAPHIC_CONTAINER_KEYS
            and isinstance(out.get(key), dict)
            and isinstance(value, dict)
        ):
            out[key] = _merge_graphic_container(out[key], value)
        elif isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _merge_graphic_container(base: dict[str, Any], override: dict[str, Any]) -> dict:
    """Merge two ``marker``/``label`` dicts, resolving element overrides."""
    out: dict[str, Any] = _deep_merge(
        {k: v for k, v in base.items() if k != "elements"},
        {k: v for k, v in override.items() if k not in ("elements", "alter")},
    )
    merged_elements = _merge_elements(base.get("elements"), override.get("elements"))
    if merged_elements is not None:
        out["elements"] = merged_elements
    return out


def _merge_elements(base_elements: Any, override_elements: Any) -> Any:
    """Apply *override_elements* onto *base_elements*.

    Supported override shapes:

    * ``None`` -> keep the inherited list unchanged
    * ``{"index": N, "value": G}`` (or a list of them) -> replace element N
      of the inherited list (padding with ``{}`` if the list is shorter)
    * anything else (a plain list of graphics) -> full replacement
    """
    if override_elements is None:
        return base_elements

    indexed = override_elements
    if isinstance(indexed, dict) and "index" in indexed and "value" in indexed:
        indexed = [indexed]
    if (
        isinstance(indexed, list)
        and indexed
        and all(isinstance(e, dict) and "index" in e and "value" in e for e in indexed)
    ):
        merged = list(base_elements) if isinstance(base_elements, list) else []
        for entry in indexed:
            idx = entry["index"]
            while len(merged) <= idx:
                merged.append({})
            merged[idx] = entry["value"]
        return merged

    return override_elements
