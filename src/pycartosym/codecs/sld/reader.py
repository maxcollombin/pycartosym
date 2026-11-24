"""SLD/SE reader — parse OGC SLD / Symbology Encoding XML into Style models.

Scope: vector symbolizers plus basic Part-1 raster/coverage styling; see
``writer.py``'s module docstring for the exact scope boundary. Out-of-scope
SLD/SE constructs (e.g. advanced raster, multi-element or text pattern
fills, ``ExternalGraphic`` without an ``OnlineResource``) raise
:exc:`NotImplementedError` rather than being silently skipped, per this
project's lossless-transcoding requirement.

:class:`SldReader` is parametrised by an
:class:`~pycartosym.codecs.sld._dialect.SldDialect`; the wiring in
:mod:`pycartosym.codecs.sld` binds it to SE 1.1.0.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from lxml import etree

from ...models.styles import Style
from ..base import CodecReader
from ._dialect import SE_1_1_0, SLD_1_0_0, SldDialect
from ._filter import (
    filter_xml_to_selector,
    merge_feature_pass,
    merge_feature_type_name,
    merge_scale_denominators,
    merge_visualization_pass,
)
from ._symbolizer import elements_to_symbolizer
from ._xml_helpers import OGC, SLD, local_name

_OVERRIDING_KINDS = frozenset({"LineSymbolizer", "PolygonSymbolizer"})

logger = logging.getLogger(__name__)


def _scale_denominator_value(
    el: etree._Element | None,
) -> int | float | None:
    """Parse an ``se:Min/MaxScaleDenominator`` element's text to a number.

    Integral values come back as ``int`` so a ``viz.sd`` selector conjunct
    round-trips to the same textual form GeoStyler and this codec's writer
    emit.
    """
    if el is None or el.text is None:
        return None
    text = el.text.strip()
    try:
        num = float(text)
    except ValueError as exc:
        raise NotImplementedError(
            f"non-numeric se:ScaleDenominator value {text!r}"
        ) from exc
    return int(num) if num.is_integer() else num


def _else_selector(
    others: list[dict | None], own: dict | None
) -> dict | None | Literal[False]:
    """Selector of an ``se:ElseFilter`` rule: no other rule of the group applies.

    ``others`` holds the selectors of the group's non-else rules (a scale
    range counts only where it is active, as SE discards the rules outside
    the nominal scale first) and ``own`` the rule's own scale range, if any.
    Returns ``False`` when another rule has no filter and no scale range, as
    it then always applies and the else rule never does.
    """
    if not others:
        return own
    if any(sel is None for sel in others):
        return False
    anyone = others[0] if len(others) == 1 else {"op": "or", "args": others}
    negated = {"op": "not", "args": [anyone]}
    return negated if own is None else {"op": "and", "args": [own, negated]}


class SldReader(CodecReader):
    """Read ``.sld`` / ``.se`` XML files (or raw XML strings) into a Style model."""

    def __init__(self, dialect: SldDialect | None = None) -> None:
        """Bind the reader to an SLD/SE dialect.

        Pass ``SE_1_1_0`` / ``SLD_1_0_0`` to pin one. The default
        (``None``) picks the dialect per document from the root
        ``version`` attribute — ``"1.0.0"`` selects SLD 1.0.0, anything
        else (including a missing attribute) selects SE 1.1.0.
        """
        self._pinned = dialect
        self.d = dialect or SE_1_1_0

    def _dialect_for(self, root: etree._Element) -> SldDialect:
        if self._pinned is not None:
            return self._pinned
        return SLD_1_0_0 if root.get("version") == "1.0.0" else SE_1_1_0

    def read(self, source: str | Path) -> Style:
        """Parse *source* and return a validated Style.

        Parameters
        ----------
        source : str | Path
            A filesystem path to a ``.sld``/``.se`` file, or the raw XML text.
        """
        if isinstance(source, Path):
            xml_bytes = source.read_bytes()
        elif (
            isinstance(source, str)
            and len(source) < 500
            and "\n" not in source
            and os.path.exists(source)  # False, not OSError, for a long name
        ):
            xml_bytes = Path(source).read_bytes()
        elif isinstance(source, str):
            xml_bytes = source.encode("utf-8")
        else:
            xml_bytes = source

        root = etree.fromstring(xml_bytes)
        return self._parse_sld(root)

    def _parse_sld(self, root: etree._Element) -> Style:
        self.d = self._dialect_for(root)
        vendor_options = root.findall(f".//{SLD}VendorOption")
        if vendor_options and not self.d.vendor_options:
            raise NotImplementedError(
                "GeoServer <VendorOption> is a vendor extension with no "
                "CartoSym mapping in this codec's scope"
            )
        for vo in vendor_options:
            parent = vo.getparent()
            if parent is None or not local_name(parent).endswith("Symbolizer"):
                where = local_name(parent) if parent is not None else "document root"
                raise NotImplementedError(
                    f"<VendorOption name={vo.get('name')!r}> under <{where}> — "
                    "only symbolizer-level vendor options map to a CartoSym "
                    "vendor.geoserver.* property"
                )
        named_layer = root.find(f"{SLD}NamedLayer")
        if named_layer is None:
            raise NotImplementedError(
                "SLD document without sld:NamedLayer is not supported"
            )
        user_style = named_layer.find(f"{SLD}UserStyle")
        if user_style is None:
            raise NotImplementedError(
                "sld:NamedLayer without sld:UserStyle is not supported"
            )
        return self._parse_user_style(user_style)

    def _parse_user_style(self, user_style: etree._Element) -> Style:
        metadata: dict = {}
        # SE 1.1.0 wraps Title/Abstract in se:Description; SLD 1.0.0 puts
        # them directly under UserStyle.
        if self.d.description_element:
            desc = self.d.find(user_style, "Description")
        else:
            desc = user_style
        if desc is not None:
            title_el = self.d.find(desc, "Title")
            abstract_el = self.d.find(desc, "Abstract")
            if title_el is not None and title_el.text:
                metadata["title"] = title_el.text
            if abstract_el is not None and abstract_el.text:
                metadata["description"] = abstract_el.text

        styles = [
            child
            for child in user_style
            if isinstance(child.tag, str)
            and local_name(child) in ("FeatureTypeStyle", "CoverageStyle")
        ]
        styling_rules: list[dict] = []
        for index, fts_el in enumerate(styles):
            # Several styles are drawn one after the other: their order is the
            # viz.pass of their rules (a single style needs none).
            pass_number = index if len(styles) > 1 else None
            styling_rules.extend(self._parse_feature_type_style(fts_el, pass_number))

        style_dict: dict = {"stylingRules": styling_rules}
        if metadata:
            style_dict["metadata"] = metadata
        style: Style = Style.from_dict(style_dict)
        return style

    def _parse_feature_type_style(
        self, fts_el: etree._Element, pass_number: int | None = None
    ) -> list[dict]:
        ftn_el = self.d.find(fts_el, "FeatureTypeName")
        if ftn_el is None:
            ftn_el = self.d.find(fts_el, "CoverageName")
        feature_type_name = ftn_el.text if ftn_el is not None else None

        rule_dicts: list[dict] = []
        parsed = [
            self._parse_rule(rule_el) for rule_el in self.d.findall(fts_el, "Rule")
        ]
        # Selectors (filter + scale range) of every non-else rule of the group:
        # an ElseFilter rule applies where none of them does, wherever they
        # sit relative to it (SE 1.1.0 10.3: the order is unimportant).
        others = [rd.get("selector") for rd, is_else in parsed if not is_else]

        for rule_dict, is_else in parsed:
            selector = rule_dict.get("selector")
            if is_else:
                selector = _else_selector(others, selector)
                if selector is False:
                    logger.warning(
                        "SLD reader: dropping se:ElseFilter rule %r, another "
                        "rule without a filter always applies so it never does",
                        rule_dict.get("name") or "<unnamed>",
                    )
                    continue
            selector = merge_visualization_pass(pass_number, selector)
            selector = merge_feature_type_name(feature_type_name, selector)
            if selector is not None:
                rule_dict["selector"] = selector
            extra = rule_dict.pop("_later_passes", [])
            if not extra:
                rule_dicts.append(rule_dict)
                continue
            # Symbolizers drawn one after the other for each feature: one rule
            # per feature.pass, in drawing order.
            for number, symbolizer in enumerate([rule_dict["symbolizer"], *extra]):
                rule_dicts.append(
                    {
                        **rule_dict,
                        "selector": merge_feature_pass(number, selector),
                        "symbolizer": symbolizer,
                    }
                )

        return rule_dicts

    def _parse_rule(self, rule_el: etree._Element) -> tuple[dict, bool]:
        rule_dict: dict = {}

        name_el = self.d.find(rule_el, "Name")
        if name_el is not None and name_el.text:
            rule_dict["name"] = name_el.text

        # se:Rule/se:Abstract maps to $comment (StylingRule has no abstract).
        # se:Rule/se:Title has no Annex B entry: it is only the fallback
        # for ``name`` when there is no se:Name. SE 1.1.0 wraps them in
        # se:Description;
        # SLD 1.0.0 puts them directly under Rule — same asymmetry as
        # _parse_user_style.
        desc = (
            self.d.find(rule_el, "Description")
            if self.d.description_element
            else rule_el
        )
        if desc is not None:
            title_el = self.d.find(desc, "Title")
            abstract_el = self.d.find(desc, "Abstract")
            if title_el is not None and title_el.text:
                rule_dict.setdefault("name", title_el.text)
            if abstract_el is not None and abstract_el.text:
                rule_dict["$comment"] = abstract_el.text

        min_sd = _scale_denominator_value(self.d.find(rule_el, "MinScaleDenominator"))
        max_sd = _scale_denominator_value(self.d.find(rule_el, "MaxScaleDenominator"))

        is_else = self.d.find(rule_el, "ElseFilter") is not None

        filter_selector = None
        if not is_else:
            filter_el = rule_el.find(f"{OGC}Filter")
            if filter_el is not None:
                filter_selector = filter_xml_to_selector(filter_el)
        selector = merge_scale_denominators(min_sd, max_sd, filter_selector)
        if selector is not None:
            rule_dict["selector"] = selector

        sym_children = [
            c
            for c in rule_el
            if isinstance(c.tag, str) and local_name(c).endswith("Symbolizer")
        ]
        if sym_children:
            # A line or polygon symbolizer met twice (casing, parallel strokes)
            # cannot be one CartoSym symbolizer, where the second would override
            # the first; each further layer is a feature.pass. Point and text
            # symbolizers pile up as marker / label elements instead.
            passes: list[list[etree._Element]] = [[]]
            for child in sym_children:
                if local_name(child) in _OVERRIDING_KINDS and any(
                    local_name(c) == local_name(child) for c in passes[-1]
                ):
                    passes.append([])
                passes[-1].append(child)
            rule_dict["symbolizer"] = elements_to_symbolizer(self.d, passes[0])
            if len(passes) > 1:
                rule_dict["_later_passes"] = [
                    elements_to_symbolizer(self.d, group) for group in passes[1:]
                ]

        return rule_dict, is_else
