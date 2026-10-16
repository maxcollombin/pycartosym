"""Core style and rule models for CartoSym.

Based on the JSON Schema definitions for style, stylingRule, and metadata.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from .base import BaseCartoSymModel, CommentMixin

# Import symbolizers
from .symbolizers import Symbolizer


class Metadata(BaseCartoSymModel, CommentMixin):
    """Metadata for a CartoSym style.

    Based on the 'metadata' definition in the JSON schema.
    """

    title: str | None = Field(None, description="Style title")
    abstract: str | None = Field(None, description="Style abstract/summary")
    description: str | None = Field(None, description="Style description")
    authors: list[str] | None = Field(None, description="List of authors")
    keywords: list[str] | None = Field(None, description="Keywords for the style")
    geo_data_classes: list[str] | None = Field(
        None, alias="geoDataClasses", description="Geographic data classes (URIs)"
    )

    @field_validator("keywords", mode="before")
    @classmethod
    def _split_keywords_string(cls, value: Any) -> Any:
        """Accept a comma-separated string, as CartoSym-CSS ``.keywords`` writes it."""
        if isinstance(value, str):
            return [kw.strip() for kw in value.split(",") if kw.strip()]
        return value


class Variable(BaseCartoSymModel):
    """Represents a variable definition in CartoSym CSS."""

    name: str = Field(..., description="Variable name")
    value: Any = Field(..., description="Variable value")
    type: str | None = Field(None, description="Variable type (optional)")


class StylingRule(BaseCartoSymModel, CommentMixin):
    """Individual styling rule with optional selector and symbolizer.

    Field order matters: Pydantic serializes in declaration order,
    so the JSON output follows: name → selector → symbolizer → nestedRules.
    """

    name: str | None = Field(
        None, description="Styling rule name (CSCSS ``.name``, ``se:Rule/se:Name``)"
    )
    selector: dict[str, Any] | list[str] | str | None = Field(
        None,
        description="Selector expression (flexible - can be dict, list, or string)",
    )
    symbolizer: Symbolizer | dict[str, Any] | None = Field(
        None, description="Symbolizer for this rule"
    )
    nested_rules: list[StylingRule] | None = Field(
        None, alias="nestedRules", description="Nested rules within this rule"
    )

    @field_validator("symbolizer", mode="before")
    def ensure_symbolizer_model(cls, v):
        """Coerce a plain ``dict`` symbolizer into a :class:`Symbolizer`."""
        if isinstance(v, dict):
            return Symbolizer.from_dict(v)
        return v

    @model_validator(mode="after")
    def recursively_validate_nested_rules(self):
        """Coerce nested-rule dicts into :class:`StylingRule` models, recursively."""
        if self.nested_rules:
            for i, rule in enumerate(self.nested_rules):
                if isinstance(rule, dict):
                    self.nested_rules[i] = StylingRule.model_validate(rule)
        return self


class Style(BaseCartoSymModel, CommentMixin):
    """Root CartoSym style definition."""

    include: str | list[str] | None = Field(
        None, alias="$include", description="Included style files"
    )
    metadata: Metadata | None = Field(None, description="Style metadata")
    styling_rules: list[StylingRule] = Field(
        ..., alias="stylingRules", description="List of styling rules"
    )
    variables: list[Variable] | None = Field(
        None, alias="$variables", description="Style variables (as objects)"
    )


# Enable forward references
StylingRule.model_rebuild()
