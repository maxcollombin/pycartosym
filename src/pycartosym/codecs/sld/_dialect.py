"""SLD dialect object — everything that differs between SLD 1.0.0 and SE 1.1.0.

The two OGC dialects share their whole document model (``UserStyle >
FeatureTypeStyle > Rule > Symbolizer``, the symbolizer semantics, the
Filter Encoding grammar, scalar formatting, cascade flattening). Only the
XML surface differs:

* the namespace that wraps ``Rule`` / ``*Symbolizer`` / ``Stroke`` / ``Fill`` /
  ``Graphic`` / ... — ``se:`` (SE 1.1.0) vs. the unprefixed SLD namespace
  (SLD 1.0.0);
* the styling-parameter element — ``se:SvgParameter`` vs. ``CssParameter``;
* the raster colour-map form — ``se:Categorize`` vs. ``<ColorMapEntry>``;
* whether style ``Title``/``Abstract`` sit inside a ``se:Description``
  wrapper (SE 1.1.0) or directly under ``UserStyle`` (SLD 1.0.0);
* whether a raster group maps to ``se:CoverageStyle`` (SE 1.1.0 only) or
  stays a plain ``FeatureTypeStyle`` (SLD 1.0.0 has no ``CoverageStyle``);
* the root ``version`` attribute and the namespace map.

A :class:`SldDialect` captures those points of variation plus the
``lxml`` element factories bound to them, so :mod:`._symbolizer`,
:mod:`.reader` and :mod:`.writer` stay dialect-agnostic. It carries no
mutable state — the two module-level instances are frozen constants.

The Filter Encoding layer (:mod:`._filter`) needs no dialect: FE 1.0 and
FE 1.1 share the ``http://www.opengis.net/ogc`` namespace and are
identical for every operator this codec emits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from lxml import etree

from ._xml_helpers import NSMAP, OGC_NS, SE_NS, SLD_NS, XLINK_NS, element_text

# SE 1.1.0 shares the module-level NSMAP (also used for detached ogc:Filter
# roots). SLD 1.0.0 needs no ``se`` prefix.
_SE_NSMAP = NSMAP
_SLD10_NSMAP = {
    None: SLD_NS,
    "ogc": OGC_NS,
    "xlink": XLINK_NS,
}


@dataclass(frozen=True)
class SldDialect:
    """One OGC styling dialect: SLD 1.0.0 or SLD 1.1.0 / SE 1.1.0.

    Attributes:
        version: Value of the root ``version`` attribute (``"1.0.0"`` / ``"1.1.0"``).
        symbology_ns: Namespace URI wrapping ``Rule`` / ``*Symbolizer`` /
            ``Stroke`` / ``Fill`` / ``Graphic`` / ``Font`` / placement / ...
            and the ``ElseFilter`` marker. ``SE_NS`` for 1.1.0, ``SLD_NS``
            for 1.0.0.
        param_tag: Local name of the styling-parameter element —
            ``"SvgParameter"`` (SE 1.1.0) or ``"CssParameter"`` (SLD 1.0.0).
            It lives in ``symbology_ns`` in both dialects.
        raster_colormap: Which raster colour-map encoding this dialect uses
            — ``"categorize"`` (``se:ColorMap/se:Categorize``, SE 1.1.0) or
            ``"entry"`` (``ColorMap/ColorMapEntry``, SLD 1.0.0).
        description_element: ``True`` if style ``Title``/``Abstract`` are
            wrapped in a ``se:Description`` element (SE 1.1.0); ``False`` if
            they are direct ``UserStyle`` children (SLD 1.0.0).
        coverage_style: ``True`` if a raster group maps to
            ``se:CoverageStyle`` / ``se:CoverageName`` (SE 1.1.0); ``False``
            if raster stays in a plain ``FeatureTypeStyle`` (SLD 1.0.0 has
            no ``CoverageStyle``).
        graphic_placement: ``True`` if a point ``Graphic`` may carry an
            ``AnchorPoint`` / ``Displacement`` child (SE 1.1.0 ``GraphicType``);
            ``False`` for SLD 1.0.0, whose ``Graphic`` stops at ``Rotation``.
        vendor_options: ``True`` if the dialect reads/writes GeoServer
            ``<VendorOption name=...>`` children of a symbolizer, mapping
            them to ``vendor.geoserver.*`` symbolizer properties (the
            conceptual model's generic vendor-extension mechanism).
            ``False`` for the standard OGC dialects, which reject
            ``<VendorOption>`` as a non-standard extension.
        recode_function: ``True`` if the dialect has the native
            ``se:Recode``/``se:LookupValue``/``se:MapItem`` elements (SE
            1.1.0 additions, substitution group ``se:Function`` — see
            ``Symbolizer.xsd``); ``False`` for SLD 1.0.0, which predates
            them.
        interpolate_function: ``True`` if the dialect has the native
            ``se:Interpolate``/``se:InterpolationPoint`` elements (SE
            1.1.0 additions, substitution group ``se:Function``, same
            section of ``Symbolizer.xsd`` as ``se:Recode``); ``False``
            for SLD 1.0.0, which predates them.
        mark_font_glyph: ``True`` if ``se:Mark`` supports the
            ``OnlineResource``/``Format``/``MarkIndex`` font-glyph-library
            alternative to ``WellKnownName`` (SE 1.1.0's own
            ``MarkType``); ``False`` for SLD 1.0.0, whose ``Mark`` is
            only ``{WellKnownName?, Fill?, Stroke?}``.
        nsmap: Namespace map for the document root element.
    """

    version: str
    symbology_ns: str
    param_tag: str
    raster_colormap: Literal["categorize", "entry"]
    description_element: bool
    coverage_style: bool
    graphic_placement: bool
    vendor_options: bool
    recode_function: bool
    interpolate_function: bool
    mark_font_glyph: bool
    nsmap: dict[str | None, str]

    # -- element factories -------------------------------------------------

    def el(
        self,
        tag: str,
        parent: etree._Element | None = None,
        text: str | None = None,
    ) -> etree._Element:
        """Create a symbology element (``se:<tag>`` or SLD ``<tag>``)."""
        qname = f"{{{self.symbology_ns}}}{tag}"
        el = (
            etree.SubElement(parent, qname)
            if parent is not None
            else etree.Element(qname, nsmap=self.nsmap)
        )
        if text is not None:
            el.text = text
        return el

    def wrap(
        self,
        tag: str,
        parent: etree._Element | None = None,
        text: str | None = None,
    ) -> etree._Element:
        """Create an SLD wrapper element, always in the SLD namespace.

        Wrapper elements (``StyledLayerDescriptor``, ``NamedLayer``,
        ``UserStyle``) stay in the SLD namespace in both dialects.
        """
        qname = f"{{{SLD_NS}}}{tag}"
        el = (
            etree.SubElement(parent, qname)
            if parent is not None
            else etree.Element(qname, nsmap=self.nsmap)
        )
        if text is not None:
            el.text = text
        return el

    def param(self, parent: etree._Element, name: str, value: str) -> etree._Element:
        """Append a styling-parameter child (``SvgParameter`` / ``CssParameter``)."""
        el = self.el(self.param_tag, parent, text=value)
        el.set("name", name)
        return el

    def param_element(self, parent: etree._Element, name: str) -> etree._Element:
        """Append an empty ``<SvgParameter name=...>`` for the caller to fill in.

        For a value with no plain-text form — a property-driven
        expression, whose content is a child element (``ogc:PropertyName``/
        ``ogc:Function``), not text — unlike :meth:`param`.
        """
        el = self.el(self.param_tag, parent)
        el.set("name", name)
        return el

    # -- readers ---------------------------------------------------------

    def find(self, elem: etree._Element, tag: str) -> etree._Element | None:
        """Return the first direct symbology-namespace ``<tag>`` child of *elem*."""
        return elem.find(f"{{{self.symbology_ns}}}{tag}")

    def findall(self, elem: etree._Element, tag: str) -> list[etree._Element]:
        """Return all direct symbology-namespace ``<tag>`` children of *elem*."""
        return cast(
            "list[etree._Element]", elem.findall(f"{{{self.symbology_ns}}}{tag}")
        )

    def finddeep(self, elem: etree._Element, tag: str) -> etree._Element | None:
        """Return the first descendant symbology-namespace ``<tag>`` of *elem*."""
        return elem.find(f".//{{{self.symbology_ns}}}{tag}")

    def get_param(self, elem: etree._Element, name: str) -> str | None:
        """Return the value of the ``<SvgParameter name=...>`` child, if present.

        Unwraps a ``<ogc:Literal>``-wrapped constant (a common GeoServer
        SLD 1.0.0 spelling).
        """
        param = self.get_param_element(elem, name)
        return element_text(param) if param is not None else None

    def get_param_element(
        self, elem: etree._Element, name: str
    ) -> etree._Element | None:
        """Return the raw ``<SvgParameter name=...>`` child element, if present.

        Unlike :meth:`get_param`, does not read its text — for a caller
        that needs to inspect its children instead (a property-driven
        expression's ``ogc:PropertyName``/``ogc:Function``, not a literal).
        """
        for param in self.findall(elem, self.param_tag):
            if param.get("name") == name:
                return param
        return None


SE_1_1_0 = SldDialect(
    version="1.1.0",
    symbology_ns=SE_NS,
    param_tag="SvgParameter",
    raster_colormap="categorize",
    description_element=True,
    coverage_style=True,
    graphic_placement=True,
    vendor_options=False,
    recode_function=True,
    interpolate_function=True,
    mark_font_glyph=True,
    nsmap=_SE_NSMAP,
)

SLD_1_0_0 = SldDialect(
    version="1.0.0",
    symbology_ns=SLD_NS,
    param_tag="CssParameter",
    raster_colormap="entry",
    description_element=False,
    coverage_style=False,
    graphic_placement=False,
    vendor_options=False,
    recode_function=False,
    interpolate_function=False,
    mark_font_glyph=False,
    nsmap=_SLD10_NSMAP,
)

# SLD 1.0.0 as GeoServer emits it: the OGC 1.0.0 document model plus
# GeoServer's <VendorOption> symbolizer children. Everything else is
# identical to SLD_1_0_0.
SLD_1_0_0_GEOSERVER = SldDialect(
    version="1.0.0",
    symbology_ns=SLD_NS,
    param_tag="CssParameter",
    raster_colormap="entry",
    description_element=False,
    coverage_style=False,
    graphic_placement=False,
    vendor_options=True,
    recode_function=False,
    interpolate_function=False,
    mark_font_glyph=False,
    nsmap=_SLD10_NSMAP,
)

__all__ = ["SldDialect", "SE_1_1_0", "SLD_1_0_0", "SLD_1_0_0_GEOSERVER"]
