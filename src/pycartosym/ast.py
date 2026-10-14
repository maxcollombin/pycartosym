"""Abstract Syntax Tree (AST) classes for CartoSym CSS.

This module contains the data structures representing parsed CartoSym CSS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Variable:
    """Variable definition in CartoSym CSS AST."""

    name: str
    value: Any
    type: str | None = None


@dataclass
class StyleSheet:
    """Root node of a CartoSym CSS stylesheet."""

    metadata: list[Metadata] = field(default_factory=list)
    styling_rules: StylingRuleList | None = None
    variables: list[Variable] = field(default_factory=list)


@dataclass
class Metadata:
    """Metadata entry in a stylesheet."""

    key: str
    value: str


@dataclass
class StylingRuleList:
    """Collection of styling rules."""

    rules: list[StylingRule]

    def __post_init__(self):
        """Default ``rules`` to an empty list when constructed with ``None``."""
        if self.rules is None:
            self.rules = []


@dataclass
class StylingRule:
    """Individual styling rule with selector and properties."""

    name: str | None = None
    styling_rule_name: str | None = None  # explicit stylingRuleName from grammar
    selector: Selector | None = None
    # all selectors (for nested rules)
    selectors: list = field(default_factory=list)
    symbolizer: Symbolizer | None = None
    nested_rules: list[StylingRule] = field(default_factory=list)
    # all property assignments, for post-processing
    property_assignments: list = field(default_factory=list)
    # comment on the lines just before the rule
    comment: str | None = None


@dataclass
class Selector:
    """Selector for filtering features."""

    expression: Expression | None = None


@dataclass
class Symbolizer:
    """Symbolizer defining how features are rendered."""

    # Basic properties
    visibility: bool | None = None
    opacity: float | None = None
    z_order: int | None = None

    # Vector symbolizers
    fill: Fill | None = None
    stroke: Stroke | None = None
    marker: Marker | None = None
    label: Label | None = None

    # Coverage/Raster properties
    single_channel: str | None = None  # e.g., "elevation"
    singleChannel: str | None = None  # camelCase alternative
    color_channels: Any | None = None  # RGB color channels
    colorChannels: Any | None = None  # camelCase alternative
    alpha_channel: Any | None = None  # Alpha channel
    alphaChannel: Any | None = None  # camelCase alternative
    color_map: Any | None = None  # Color mapping
    colorMap: Any | None = None  # camelCase alternative
    opacity_map: Any | None = None  # Opacity mapping
    opacityMap: Any | None = None  # camelCase alternative
    hill_shading: dict[str, Any] | None = None  # Hill shading config
    hillShading: dict[str, Any] | None = None  # camelCase alternative


@dataclass
class Expression:
    """Base class for expressions."""

    pass


@dataclass
class PropertyAssignment:
    """Assignment of a value to a property."""

    property_name: str
    value: Any


@dataclass
class PropertyAssignmentList:
    """Collection of property assignments."""

    assignments: list[PropertyAssignment]

    def __post_init__(self):
        """Default ``assignments`` to an empty list when constructed with ``None``."""
        if self.assignments is None:
            self.assignments = []


@dataclass
class Fill:
    """Fill styling properties."""

    color: str | None = None
    opacity: float | None = None


@dataclass
class Stroke:
    """Stroke styling properties."""

    color: str | None = None
    width: float | None = None
    opacity: float | None = None


@dataclass
class Marker:
    """Marker styling properties."""

    elements: list | None = None


@dataclass
class Label:
    """Label styling properties."""

    elements: list | None = None
    position: Any | None = None
    opacity: float | None = None
    placement: Any | None = None
