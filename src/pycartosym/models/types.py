"""Precise type definitions for CartoSym.

This module contains precise types based on the JSON Schema analysis,
including colors, units, ranges, and custom validators.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

from .value_expressions import ValueExpression

# =============================================================================
# Color Types
# =============================================================================


class WebColorName(str, Enum):
    """Web color names as defined in the CartoSym JSON Schema."""

    # Grays and whites
    BLACK = "black"
    DIM_GRAY = "dimGray"
    DIM_GREY = "dimGrey"
    GRAY = "gray"
    GREY = "grey"
    DARK_GRAY = "darkGray"
    DARK_GREY = "darkGrey"
    SILVER = "silver"
    LIGHT_GRAY = "lightGray"
    LIGHT_GREY = "lightGrey"
    GAINSBORO = "gainsboro"
    WHITE_SMOKE = "whiteSmoke"
    WHITE = "white"

    # Reds and pinks
    ROSY_BROWN = "rosyBrown"
    INDIAN_RED = "indianRed"
    BROWN = "brown"
    FIRE_BRICK = "fireBrick"
    LIGHT_CORAL = "lightCoral"
    MAROON = "maroon"
    DARK_RED = "darkRed"
    RED = "red"
    SNOW = "snow"
    MISTY_ROSE = "mistyRose"
    SALMON = "salmon"
    TOMATO = "tomato"
    DARK_SALMON = "darkSalmon"
    CORAL = "coral"
    ORANGE_RED = "orangeRed"
    LIGHT_SALMON = "lightSalmon"

    # Oranges and browns
    SIENNA = "sienna"
    SEA_SHELL = "seaShell"
    CHOCOLATE = "chocolate"
    SADDLE_BROWN = "saddleBrown"
    SANDY_BROWN = "sandyBrown"
    PEACH_PUFF = "peachPuff"
    PERU = "peru"
    LINEN = "linen"
    BISQUE = "bisque"
    DARK_ORANGE = "darkOrange"
    BURLY_WOOD = "burlyWood"
    TAN = "tan"
    ANTIQUE_WHITE = "antiqueWhite"
    NAVAJO_WHITE = "navajoWhite"
    BLANCHED_ALMOND = "blanchedAlmond"
    PAPAYA_WHIP = "papayaWhip"
    MOCCASIN = "moccasin"
    ORANGE = "orange"
    WHEAT = "wheat"
    OLD_LACE = "oldLace"
    FLORAL_WHITE = "floralWhite"

    # Yellows and golds
    DARK_GOLDENROD = "darkGoldenrod"
    GOLDENROD = "goldenrod"
    CORNSILK = "cornsilk"
    GOLD = "gold"
    KHAKI = "khaki"
    LEMON_CHIFFON = "lemonChiffon"
    PALE_GOLDENROD = "paleGoldenrod"
    DARK_KHAKI = "darkKhaki"
    BEIGE = "beige"
    LIGHT_GOLDENROD_YELLOW = "lightGoldenRodYellow"
    OLIVE = "olive"
    YELLOW = "yellow"
    LIGHT_YELLOW = "lightYellow"
    IVORY = "ivory"

    # Greens
    OLIVE_DRAB = "oliveDrab"
    YELLOW_GREEN = "yellowGreen"
    DARK_OLIVE_GREEN = "darkOliveGreen"
    GREEN_YELLOW = "greenYellow"
    CHARTREUSE = "chartreuse"
    LAWN_GREEN = "lawnGreen"
    DARK_SEA_GREEN = "darkSeaGreen"
    FOREST_GREEN = "forestGreen"
    LIME_GREEN = "limeGreen"
    LIGHT_GREEN = "lightGreen"
    PALE_GREEN = "paleGreen"
    DARK_GREEN = "darkGreen"
    GREEN = "green"
    LIME = "lime"
    HONEY_DEW = "honeyDew"
    SEA_GREEN = "seaGreen"
    MEDIUM_SEA_GREEN = "mediumSeaGreen"
    SPRING_GREEN = "springGreen"
    MINT_CREAM = "mintCream"
    MEDIUM_SPRING_GREEN = "mediumSpringGreen"
    MEDIUM_AQUA_MARINE = "mediumAquaMarine"
    AQUAMARINE = "aquamarine"
    TURQUOISE = "turquoise"
    LIGHT_SEA_GREEN = "lightSeaGreen"
    MEDIUM_TURQUOISE = "mediumTurquoise"

    # Cyans and teals
    DARK_SLATE_GRAY = "darkSlateGray"
    DARK_SLATE_GREY = "darkSlateGrey"
    PALE_TURQUOISE = "paleTurquoise"
    TEAL = "teal"
    DARK_CYAN = "darkCyan"
    AQUA = "aqua"
    CYAN = "cyan"
    LIGHT_CYAN = "lightCyan"
    AZURE = "azure"
    DARK_TURQUOISE = "darkTurquoise"
    CADET_BLUE = "cadetBlue"
    POWDER_BLUE = "powderBlue"
    LIGHT_BLUE = "lightBlue"
    DEEP_SKY_BLUE = "deepSkyBlue"
    SKY_BLUE = "skyBlue"
    LIGHT_SKY_BLUE = "lightSkyBlue"
    STEEL_BLUE = "steelBlue"
    ALICE_BLUE = "aliceBlue"

    # Blues
    DODGER_BLUE = "dodgerBlue"
    SLATE_GRAY = "slateGray"
    SLATE_GREY = "slateGrey"
    LIGHT_SLATE_GRAY = "lightSlateGray"
    LIGHT_SLATE_GREY = "lightSlateGrey"
    LIGHT_STEEL_BLUE = "lightSteelBlue"
    CORNFLOWER_BLUE = "cornflowerBlue"
    ROYAL_BLUE = "royalBlue"
    MIDNIGHT_BLUE = "midnightBlue"
    LAVENDER = "lavender"
    NAVY = "navy"
    DARK_BLUE = "darkBlue"
    MEDIUM_BLUE = "mediumBlue"
    BLUE = "blue"
    GHOST_WHITE = "ghostWhite"

    # Purples and violets
    SLATE_BLUE = "slateBlue"
    DARK_SLATE_BLUE = "darkSlateBlue"
    MEDIUM_SLATE_BLUE = "mediumSlateBlue"
    MEDIUM_PURPLE = "mediumPurple"
    BLUE_VIOLET = "blueViolet"
    INDIGO = "indigo"
    DARK_ORCHID = "darkOrchid"
    DARK_VIOLET = "darkViolet"
    MEDIUM_ORCHID = "mediumOrchid"
    THISTLE = "thistle"
    PLUM = "plum"
    VIOLET = "violet"
    PURPLE = "purple"
    DARK_MAGENTA = "darkMagenta"
    MAGENTA = "magenta"
    FUSCHIA = "fuschia"
    ORCHID = "orchid"
    MEDIUM_VIOLET_RED = "mediumVioletRed"
    DEEP_PINK = "deepPink"
    HOT_PINK = "hotPink"
    LAVENDER_BLUSH = "lavenderBlush"
    PALE_VIOLET_RED = "paleVioletRed"
    CRIMSON = "crimson"
    PINK = "pink"
    LIGHT_PINK = "lightPink"


class RGBColor(BaseModel):
    """RGB color with 0-255 components."""

    r: Annotated[int, Field(ge=0, le=255, description="Red component (0-255)")]
    g: Annotated[int, Field(ge=0, le=255, description="Green component (0-255)")]
    b: Annotated[int, Field(ge=0, le=255, description="Blue component (0-255)")]
    alter: bool = Field(False, description="Alter flag")


class RGBColorNormalized(BaseModel):
    """RGB color with 0-1 normalized components."""

    r: Annotated[float, Field(ge=0.0, le=1.0, description="Red component (0.0-1.0)")]
    g: Annotated[float, Field(ge=0.0, le=1.0, description="Green component (0.0-1.0)")]
    b: Annotated[float, Field(ge=0.0, le=1.0, description="Blue component (0.0-1.0)")]
    alter: bool = Field(False, description="Alter flag")


# Color type that accepts all forms
Color = (
    WebColorName  # Named colors
    | RGBColor  # RGB object with 0-255 values
    | RGBColorNormalized  # RGB object with 0-1 values
    | list[Annotated[int, Field(ge=0, le=255)]]  # RGB array [r, g, b]
    | str  # Hex colors like "#ff0000" or expressions
)

# Normalized color for coverage operations
ColorNormalized = (
    WebColorName
    | RGBColorNormalized
    | list[Annotated[float, Field(ge=0.0, le=1.0)]]
    | str
)


# =============================================================================
# Unit Types
# =============================================================================


class UnitType(str, Enum):
    """Supported unit types."""

    PIXELS = "px"
    MILLIMETERS = "mm"
    CENTIMETERS = "cm"
    INCHES = "in"
    POINTS = "pt"
    EM = "em"
    PICAS = "pc"
    METERS = "m"
    FEET = "ft"


class UnitValue(BaseModel):
    """Value with a specific unit.

    Splitting a raw ``{unit: value}`` dict (e.g. ``{"px": 2.0}``) into
    ``value``/``unit`` happens one level up, in
    :func:`~pycartosym.models.symbolizers.parse_flexible_unit_value` — a
    field-level ``@field_validator("value", "unit", mode="before")``
    on this class cannot do it: Pydantic only calls a field's
    before-validator on the value already extracted for that field, never
    on the whole raw input, so ``UnitValue.model_validate({"px": 2.0})``
    would still need ``value``/``unit`` keys present regardless (that
    validator was inert and has been removed).
    """

    value: float = Field(..., description="Numeric value")
    unit: UnitType = Field(..., description="Unit type")

    def __str__(self) -> str:
        """Return the string representation like '10px' or '2.5mm'."""
        return f"{self.value}{self.unit.value}"

    def to_dict(self) -> dict:
        """Convert to JSON schema format like {"px": 2.0}."""
        return {self.unit.value: self.value}

    def model_dump(self, **kwargs):
        """Override model_dump to use JSON schema format."""
        return self.to_dict()


# Flexible unit value that accepts expressions or objects
FlexibleUnitValue = UnitValue | str | float

# Flexible size that additionally accepts a typed data-driven value
# expression (MapLibre ["get"/"case"/"match"/"interpolate"/"step"/"coalesce"]).
FlexibleSize = UnitValue | str | float | ValueExpression


# =============================================================================
# Angle Types
# =============================================================================


class AngleUnit(str, Enum):
    """Supported angle units."""

    DEGREES = "deg"
    RADIANS = "rad"


class Angle(BaseModel):
    """Angle value with unit."""

    value: float = Field(..., description="Angle value")
    unit: AngleUnit = Field(AngleUnit.DEGREES, description="Angle unit")

    def __str__(self) -> str:
        """Return the string representation like '45deg' or '1.57rad'."""
        return f"{self.value}{self.unit.value}"


# =============================================================================
# Range Types
# =============================================================================

ZeroToOne = Annotated[float, Field(ge=0.0, le=1.0)]
"""Float value between 0 and 1 (inclusive)."""

Percent = Annotated[float, Field(ge=0.0, le=100.0)]
"""Percentage value between 0 and 100."""

ColorComponent255 = Annotated[int, Field(ge=0, le=255)]
"""Color component value between 0 and 255."""


# =============================================================================
# Flexible Types for Real-world Usage
# =============================================================================

# These are the types actually used in models - they accept both precise
# types and strings

FlexibleColor = Color | str | ValueExpression
"""Color that accepts precise Color types, string expressions, or a typed
data-driven value expression."""

# FlexibleUnitValue is defined once, above (line ~275).
# FlexibleSize is defined once, above (line ~283).

FlexibleAngle = Angle | str | float | ValueExpression
"""Angle that accepts Angle objects, strings, plain numbers (assumed
degrees), or a typed data-driven value expression."""

FlexibleOpacity = ZeroToOne | str | ValueExpression
"""Opacity that accepts a 0-1 float, string expressions, or a typed
data-driven value expression."""

FlexibleNumber = float | str | ValueExpression
"""Dimensionless number (e.g. a label priority) that accepts a plain float,
string expressions, or a typed data-driven value expression."""
