"""Selector helpers shared by the codecs (no XML dependency).

``extract_feature_type_name`` splits the ``dataLayer.*`` conjuncts out of a
selector; the SLD and MapLibre writers both use it, so it lives here and not in
the SLD codec, which needs the optional ``lxml``.
"""

from __future__ import annotations

from typing import Any

_DATALAYER_METADATA_SYSIDS = (
    "dataLayer.type",
    "dataLayer.featuresGeometryDimensions",
)


def _is_sysid_eq(expr: Any, sys_id: str) -> bool:
    return (
        isinstance(expr, dict)
        and expr.get("op") == "="
        and isinstance(expr.get("args"), list)
        and len(expr["args"]) == 2
        and isinstance(expr["args"][0], dict)
        and expr["args"][0].get("sysId") == sys_id
    )


def _coerce_id_value(value: Any) -> str:
    if isinstance(value, dict) and "property" in value:
        return str(value["property"])
    return str(value)


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


_VIZ_PASS_SYSID = "viz.pass"
_FEATURE_PASS_SYSID = "feature.pass"


def _extract_pass(selector: dict | None, sysid: str) -> tuple[int | None, dict | None]:
    """Split a literal ``<sysid> = N`` conjunct out of *selector*.

    Same flatten/reassemble pattern as :func:`extract_feature_type_name`.
    A pass compared otherwise (an attribute-driven expression, a range)
    stays in the remaining selector, where the filter encoder rejects it:
    a feature-dependent pass has no static SLD/SE structure.
    """
    if selector is None:
        return None, None
    pass_number: int | None = None
    remaining: list[Any] = []
    for conjunct in _flatten_and_conjuncts(selector):
        value = conjunct["args"][1] if _is_sysid_eq(conjunct, sysid) else None
        if (
            pass_number is None
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            pass_number = value
        else:
            remaining.append(conjunct)
    return pass_number, _reassemble_and(remaining)


def extract_visualization_pass(
    selector: dict | None,
) -> tuple[int | None, dict | None]:
    """Split a literal ``viz.pass = N`` conjunct out of *selector*.

    ``viz.pass`` (visualization rendering pass) maps to the order of
    ``se:FeatureTypeStyle`` elements in a ``se:UserStyle``: every feature
    is drawn with an earlier style before any is drawn with a later one.

    Returns:
    -------
    (pass_number, remaining_selector)
    """
    return _extract_pass(selector, _VIZ_PASS_SYSID)


def extract_feature_pass(
    selector: dict | None,
) -> tuple[int | None, dict | None]:
    """Split a literal ``feature.pass = N`` conjunct out of *selector*.

    ``feature.pass`` draws one feature completely (all its passes, in
    order) before the next, which is what several symbolizers of a single
    ``se:Rule`` do in SE.

    Returns:
    -------
    (pass_number, remaining_selector)
    """
    return _extract_pass(selector, _FEATURE_PASS_SYSID)
