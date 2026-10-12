"""Base Pydantic models and utilities for CartoSym."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

_T = TypeVar("_T", bound="BaseCartoSymModel")


class BaseCartoSymModel(BaseModel):
    """Base class for all CartoSym models.

    Provides common configuration and utilities for validation,
    serialization, and documentation generation.
    """

    model_config = ConfigDict(
        # Reject unknown fields (typo protection). The one spec-sanctioned
        # extension point — ``vendor.<name>.<prop>`` keys on a Symbolizer —
        # is opened up in ``Symbolizer`` itself.
        extra="forbid",
        # Validate on assignment
        validate_assignment=True,
        # Use enum values in serialization
        use_enum_values=True,
        # Populate by name (for JSON Schema compatibility)
        populate_by_name=True,
        # Use aliases in serialization
        serialize_by_alias=True,
        # Strict validation by default
        strict=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary, excluding None values."""
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """Convert model to JSON string."""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_dict(cls: type[_T], data: dict[str, Any]) -> _T:
        """Create model instance from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls: type[_T], json_str: str) -> _T:
        """Create model instance from JSON string."""
        return cls.model_validate_json(json_str)


class CommentMixin(BaseModel):
    """Mixin for models that can have comments."""

    comment: str | None = Field(None, alias="$comment", description="Optional comment")


class AlterMixin(BaseModel):
    """Mixin for models that can have alter flag."""

    alter: bool | None = Field(
        None, description="Whether this overrides a previous definition"
    )
