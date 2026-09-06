"""SLD/SE writer — serialise Style models to OGC SLD / Symbology Encoding XML.

Scope: vector symbolizers (Point/Line/Polygon/Text) plus basic Part-1
raster/coverage styling. GeoServer vendor extensions and advanced/Part-4
raster are out of scope. Out-of-scope content raises
:exc:`NotImplementedError` naming the unsupported field rather than being
silently dropped, per this project's lossless-transcoding requirement.

:class:`SldWriter` is parametrised by an
:class:`~pycartosym.codecs.sld._dialect.SldDialect`; the wiring in
:mod:`pycartosym.codecs.sld` binds it to SE 1.1.0.
"""

from __future__ import annotations

import logging
from collections import OrderedDict

from lxml import etree

from ...models.styles import Style, StylingRule
from .._cascade import flatten_cascade_rules
from ..base import CodecWriter
from ._dialect import SE_1_1_0, SldDialect
from ._filter import (
    extract_feature_type_name,
    extract_scale_denominators,
    selector_to_filter_xml,
)
from ._symbolizer import has_raster_fields, symbolizer_to_elements

logger = logging.getLogger(__name__)


def _scale_text(value: int | float) -> str:
    """Render a scale denominator, dropping a redundant ``.0`` on whole numbers."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class SldWriter(CodecWriter):
    """Write a Style model as SLD/SE XML."""

    def __init__(self, dialect: SldDialect = SE_1_1_0) -> None:
        """Bind the writer to an SLD/SE dialect (SE 1.1.0 by default)."""
        self.d = dialect

    def write(self, style: Style) -> str:
        """Serialise a Style model to an SLD/SE XML string."""
        root = self._build_sld(style)
        xml: bytes = etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
        return xml.decode("utf-8")

    def _build_sld(self, style: Style) -> etree._Element:
        root = self.d.wrap("StyledLayerDescriptor")
        root.set("version", self.d.version)
        named_layer = self.d.wrap("NamedLayer", parent=root)
        # SLD 1.1.0 requires se:Name as the first child of NamedLayer
        # (minOccurs=1). CartoSym has no layer-name concept, so this is
        # synthesised from the style title (write-only; the reader ignores it).
        title = getattr(style.metadata, "title", None) if style.metadata else None
        self.d.el("Name", parent=named_layer, text=title or "CartoSym Style")
        named_layer.append(self._build_user_style(style))
        return root

    def _build_user_style(self, style: Style) -> etree._Element:
        user_style = self.d.wrap("UserStyle")

        metadata = style.metadata
        if metadata is not None:
            for field in ("authors", "keywords", "geo_data_classes"):
                if getattr(metadata, field, None):
                    raise NotImplementedError(
                        f"Style.metadata.{field} has no SLD/SE mapping in this codec"
                    )
            if metadata.title or metadata.abstract:
                # SE 1.1.0 wraps Title/Abstract in se:Description; SLD 1.0.0
                # puts them directly under UserStyle.
                desc = (
                    self.d.el("Description", parent=user_style)
                    if self.d.description_element
                    else user_style
                )
                if metadata.title:
                    self.d.el("Title", parent=desc, text=metadata.title)
                if metadata.abstract:
                    self.d.el("Abstract", parent=desc, text=metadata.abstract)
        if style.variables:
            raise NotImplementedError(
                "Style.$variables has no SLD/SE mapping in this codec"
            )
        if style.include:
            raise NotImplementedError(
                "Style.$include has no SLD/SE mapping in this codec"
            )

        # Resolve CartoSym nested-rule cascades (selector AND-ing +
        # symbolizer partial-override merge) into a flat list of
        # independent rules before grouping — SE 1.1.0 has no cascade.
        # Selector-less nestedRules stay nested and keep their OGC "else"
        # meaning.
        if any(r.nested_rules for r in style.styling_rules):
            flat_rules = [
                StylingRule.from_dict(d)
                for d in flatten_cascade_rules(
                    [r.to_dict() for r in style.styling_rules]
                )
            ]
        else:
            flat_rules = list(style.styling_rules)
        groups = self._group_rules_by_feature_type(flat_rules)
        emitted = 0
        for feature_type_name, rules in groups.items():
            fts = self._build_feature_type_style(feature_type_name, rules)
            if fts is not None:
                user_style.append(fts)
                emitted += 1
        if emitted == 0:
            raise NotImplementedError(
                "Style has no SLD/SE-renderable content — every styling rule "
                "is symbolizer-less (visibility / opacity / zOrder only). SE "
                "1.1.0 forbids a se:Rule without a symbolizer"
            )
        return user_style

    def _group_rules_by_feature_type(
        self, rules: list[StylingRule]
    ) -> OrderedDict[str | None, list[tuple[StylingRule, dict | None]]]:
        """Group top-level rules by their ``dataLayer.id`` conjunct.

        Rules with no ``dataLayer.id`` conjunct are grouped under the key
        ``None`` and go into a ``se:FeatureTypeStyle`` with no
        ``se:FeatureTypeName`` child. Also strips (without re-emitting)
        any ``dataLayer.type``/``dataLayer.featuresGeometryDimensions``
        conjuncts found alongside it — see
        ``_filter.py::extract_feature_type_name``. SLD/SE has no
        representation for either, so this is a write-only lossy strip.
        """
        groups: OrderedDict[str | None, list[tuple[StylingRule, dict | None]]] = (
            OrderedDict()
        )
        for rule in rules:
            selector = rule.selector
            if selector is not None and not isinstance(selector, dict):
                raise NotImplementedError(
                    f"StylingRule.selector of type {type(selector).__name__} "
                    "(bare string/list selector, not a CQL2-JSON dict) has "
                    "no SLD/SE mapping in this codec"
                )
            feature_type_name, remaining = extract_feature_type_name(selector)
            groups.setdefault(feature_type_name, []).append((rule, remaining))
        return groups

    def _build_feature_type_style(
        self,
        feature_type_name: str | None,
        rules_and_selectors: list[tuple[StylingRule, dict | None]],
    ) -> etree._Element | None:
        # A group styling a coverage (any rule carries raster fields) maps
        # to se:CoverageStyle/se:CoverageName in SE 1.1.0; SLD 1.0.0 has no
        # CoverageStyle, so raster stays in a plain FeatureTypeStyle.
        is_coverage = any(
            self._rule_has_raster(rule) for rule, _ in rules_and_selectors
        )
        if is_coverage and self.d.coverage_style:
            fts = self.d.el("CoverageStyle")
            if feature_type_name is not None:
                self.d.el("CoverageName", parent=fts, text=str(feature_type_name))
        else:
            fts = self.d.el("FeatureTypeStyle")
            if feature_type_name is not None:
                self.d.el("FeatureTypeName", parent=fts, text=str(feature_type_name))
        n_rules = 0
        for rule, remaining_selector in rules_and_selectors:
            rule_el = self._build_rule(rule, remaining_selector)
            if rule_el is not None:
                fts.append(rule_el)
                n_rules += 1
            for else_rule in self._flatten_nested_rules(rule):
                fts.append(else_rule)
                n_rules += 1
        if n_rules == 0:
            # Every rule in this group was symbolizer-less and faithfully
            # dropped — se:FeatureTypeStyle/se:CoverageStyle both require
            # >=1 se:Rule, so emit nothing for this group.
            return None
        return fts

    def _rule_has_raster(self, rule: StylingRule) -> bool:
        """Return True if *rule* or any of its nested rules carries raster fields."""
        if rule.symbolizer is not None and has_raster_fields(rule.symbolizer):
            return True
        return any(self._rule_has_raster(n) for n in rule.nested_rules or [])

    def _flatten_nested_rules(self, rule: StylingRule) -> list[etree._Element]:
        """Emit the selector-less ``nested_rules`` as sibling ``se:Rule`` elements.

        Each carries an ``ElseFilter`` marker in the dialect's symbology
        namespace (``se:ElseFilter`` for SE 1.1.0).

        By the time this runs, ``flatten_cascade_rules`` has already
        pulled every *selector-bearing* nested rule out into an
        independent top-level rule; what is left here is genuine OGC
        else-rule fallback (no selector), symbolizer already merged onto
        its ancestors'.
        """
        out = []
        for nested in rule.nested_rules or []:
            nested_el = self._build_rule(nested, None, is_else=True)
            if nested_el is not None:
                out.append(nested_el)
            out.extend(self._flatten_nested_rules(nested))
        return out

    def _build_rule(
        self,
        rule: StylingRule,
        remaining_selector: dict | None,
        is_else: bool = False,
    ) -> etree._Element | None:
        sym_elements = (
            symbolizer_to_elements(self.d, rule.symbolizer)
            if rule.symbolizer is not None
            else []
        )
        if not sym_elements:
            # SE 1.1.0 forbids a se:Rule without a se:Symbolizer. A
            # symbolizer-less CartoSym rule (visibility / opacity / zOrder
            # only, or a cascade base case) is dropped; whatever intent it
            # carried is warned about, not silently lost, and the whole
            # style raises upstream if nothing renders at all.
            sym = rule.symbolizer
            carried = [
                f
                for f in ("visibility", "opacity", "z_order")
                if sym is not None and getattr(sym, f, None) is not None
            ]
            if carried and not is_else:
                logger.warning(
                    "SLD/SE writer: dropping symbolizer-less rule %r "
                    "(carried %s) — not representable in SE 1.1.0",
                    rule.styling_rule_name or rule.name or "<unnamed>",
                    ", ".join(carried),
                )
            return None

        rule_el = self.d.el("Rule")
        if rule.styling_rule_name:
            self.d.el("Name", parent=rule_el, text=rule.styling_rule_name)

        # rule.name/.comment map to se:Rule/se:Title/se:Abstract, distinct
        # from stylingRuleName -> se:Name above. rule.name previously
        # fell back into se:Name when stylingRuleName was absent, but that
        # would collide with this new Title mapping on round-trip (an
        # SLD Title-only rule would gain a spurious se:Name after one
        # write, see issue #90) — se:Name is now stylingRuleName-only.
        if rule.name or rule.comment:
            desc = (
                self.d.el("Description", parent=rule_el)
                if self.d.description_element
                else rule_el
            )
            if rule.name:
                self.d.el("Title", parent=desc, text=rule.name)
            if rule.comment:
                self.d.el("Abstract", parent=desc, text=rule.comment)

        if is_else:
            self.d.el("ElseFilter", parent=rule_el)
        else:
            min_sd, max_sd, filter_selector = extract_scale_denominators(
                remaining_selector
            )
            filt = selector_to_filter_xml(filter_selector)
            if filt is not None:
                rule_el.append(filt)
            # SE 1.1.0 RuleType order: (Filter|ElseFilter)?, then
            # MinScaleDenominator?, MaxScaleDenominator?, then Symbolizer*.
            if min_sd is not None:
                self.d.el(
                    "MinScaleDenominator", parent=rule_el, text=_scale_text(min_sd)
                )
            if max_sd is not None:
                self.d.el(
                    "MaxScaleDenominator", parent=rule_el, text=_scale_text(max_sd)
                )

        for sym_el in sym_elements:
            rule_el.append(sym_el)

        return rule_el
