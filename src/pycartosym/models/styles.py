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
    variables: dict[str, Any] | None = Field(
        None,
        alias="$variables",
        description="Style variables: name -> value (a literal or an expression)",
    )

    @field_validator("variables", mode="before")
    @classmethod
    def _variables_from_legacy_list(cls, value: Any) -> Any:
        """Accept the pre-0.5 ``[{"name": ..., "value": ...}]`` list form."""
        if isinstance(value, list):
            return {
                (v["name"] if isinstance(v, dict) else v.name): (
                    v["value"] if isinstance(v, dict) else v.value
                )
                for v in value
            }
        return value

    def resolve_variables(self) -> Style:
        """Return a copy with every ``$ref`` to a variable replaced by its value.

        For consumers (renderers, SLD, MapLibre) that have no notion of
        variables. The copy has no ``$variables``.
        """
        if not self.variables:
            return self
        variables = self.variables

        def _resolve(node: Any) -> Any:
            if isinstance(node, dict):
                ref = node.get("$ref")
                name = (
                    ref.removeprefix(_VARIABLES_POINTER) if isinstance(ref, str) else ""
                )
                if name in variables:  # others come from an included file
                    return _resolve(variables[name])
                return {k: _resolve(v) for k, v in node.items()}
            if isinstance(node, list):
                return [_resolve(v) for v in node]
            return node

        data = _resolve(self.model_dump(exclude_none=True))
        data.pop("$variables", None)
        return type(self).model_validate(data)


_VARIABLES_POINTER = "#/$variables/"

# Enable forward references
StylingRule.model_rebuild()
