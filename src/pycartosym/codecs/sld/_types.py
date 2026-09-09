"""Scalar formatting conventions for the SLD/SE codec.

SLD/SE ``se:SvgParameter`` values and XML attributes are bare numeric/hex
strings — unlike CartoSym's ``{unit: value}`` dict convention for
:class:`~pycartosym.models.types.UnitValue`, SE 1.1.0 core has no
unit-of-measure attribute on these parameters, so unit information is lost
on write (a known, confirmed gap).
"""

from __future__ import annotations

import math
import re
from typing import Any

from ...models.types import RGBColor, RGBColorNormalized, WebColorName

# Full CSS/SVG named-color -> #rrggbb table, keyed by WebColorName's own
# enum values (camelCase, matching CartoSym-JSON's own spelling) so lookups
# don't need to normalize case.
_WEB_COLOR_HEX = {
    "black": "#000000",
    "dimGray": "#696969",
    "dimGrey": "#696969",
    "gray": "#808080",
    "grey": "#808080",
    "darkGray": "#a9a9a9",
    "darkGrey": "#a9a9a9",
    "silver": "#c0c0c0",
    "lightGray": "#d3d3d3",
    "lightGrey": "#d3d3d3",
    "gainsboro": "#dcdcdc",
    "whiteSmoke": "#f5f5f5",
    "white": "#ffffff",
    "rosyBrown": "#bc8f8f",
    "indianRed": "#cd5c5c",
    "brown": "#a52a2a",
    "fireBrick": "#b22222",
    "lightCoral": "#f08080",
    "maroon": "#800000",
    "darkRed": "#8b0000",
    "red": "#ff0000",
    "snow": "#fffafa",
    "mistyRose": "#ffe4e1",
    "salmon": "#fa8072",
    "tomato": "#ff6347",
    "darkSalmon": "#e9967a",
    "coral": "#ff7f50",
    "orangeRed": "#ff4500",
    "lightSalmon": "#ffa07a",
    "sienna": "#a0522d",
    "seaShell": "#fff5ee",
    "chocolate": "#d2691e",
    "saddleBrown": "#8b4513",
    "sandyBrown": "#f4a460",
    "peachPuff": "#ffdab9",
    "peru": "#cd853f",
    "linen": "#faf0e6",
    "bisque": "#ffe4c4",
    "darkOrange": "#ff8c00",
    "burlyWood": "#deb887",
    "tan": "#d2b48c",
    "antiqueWhite": "#faebd7",
    "navajoWhite": "#ffdead",
    "blanchedAlmond": "#ffebcd",
    "papayaWhip": "#ffefd5",
    "moccasin": "#ffe4b5",
    "orange": "#ffa500",
    "wheat": "#f5deb3",
    "oldLace": "#fdf5e6",
    "floralWhite": "#fffaf0",
    "darkGoldenrod": "#b8860b",
    "goldenrod": "#daa520",
    "cornsilk": "#fff8dc",
    "gold": "#ffd700",
    "khaki": "#f0e68c",
    "lemonChiffon": "#fffacd",
    "paleGoldenrod": "#eee8aa",
    "darkKhaki": "#bdb76b",
    "beige": "#f5f5dc",
    "lightGoldenRodYellow": "#fafad2",
    "olive": "#808000",
    "yellow": "#ffff00",
    "lightYellow": "#ffffe0",
    "ivory": "#fffff0",
    "oliveDrab": "#6b8e23",
    "yellowGreen": "#9acd32",
    "darkOliveGreen": "#556b2f",
    "greenYellow": "#adff2f",
    "chartreuse": "#7fff00",
    "lawnGreen": "#7cfc00",
    "darkSeaGreen": "#8fbc8f",
    "forestGreen": "#228b22",
    "limeGreen": "#32cd32",
    "lightGreen": "#90ee90",
    "paleGreen": "#98fb98",
    "darkGreen": "#006400",
    "green": "#008000",
    "lime": "#00ff00",
    "honeyDew": "#f0fff0",
    "seaGreen": "#2e8b57",
    "mediumSeaGreen": "#3cb371",
    "springGreen": "#00ff7f",
    "mintCream": "#f5fffa",
    "mediumSpringGreen": "#00fa9a",
    "mediumAquaMarine": "#66cdaa",
    "aquamarine": "#7fffd4",
    "turquoise": "#40e0d0",
    "lightSeaGreen": "#20b2aa",
    "mediumTurquoise": "#48d1cc",
    "darkSlateGray": "#2f4f4f",
    "darkSlateGrey": "#2f4f4f",
    "paleTurquoise": "#afeeee",
    "teal": "#008080",
    "darkCyan": "#008b8b",
    "aqua": "#00ffff",
    "cyan": "#00ffff",
    "lightCyan": "#e0ffff",
    "azure": "#f0ffff",
    "darkTurquoise": "#00ced1",
    "cadetBlue": "#5f9ea0",
    "powderBlue": "#b0e0e6",
    "lightBlue": "#add8e6",
    "deepSkyBlue": "#00bfff",
    "skyBlue": "#87ceeb",
    "lightSkyBlue": "#87cefa",
    "steelBlue": "#4682b4",
    "aliceBlue": "#f0f8ff",
    "dodgerBlue": "#1e90ff",
    "slateGray": "#708090",
    "slateGrey": "#708090",
    "lightSlateGray": "#778899",
    "lightSlateGrey": "#778899",
    "lightSteelBlue": "#b0c4de",
    "cornflowerBlue": "#6495ed",
    "royalBlue": "#4169e1",
    "midnightBlue": "#191970",
    "lavender": "#e6e6fa",
    "navy": "#000080",
    "darkBlue": "#00008b",
    "mediumBlue": "#0000cd",
    "blue": "#0000ff",
    "ghostWhite": "#f8f8ff",
    "slateBlue": "#6a5acd",
    "darkSlateBlue": "#483d8b",
    "mediumSlateBlue": "#7b68ee",
    "mediumPurple": "#9370db",
    "blueViolet": "#8a2be2",
    "indigo": "#4b0082",
    "darkOrchid": "#9932cc",
    "darkViolet": "#9400d3",
    "mediumOrchid": "#ba55d3",
    "thistle": "#d8bfd8",
    "plum": "#dda0dd",
    "violet": "#ee82ee",
    "purple": "#800080",
    "darkMagenta": "#8b008b",
    "magenta": "#ff00ff",
    "fuschia": "#ff00ff",
    "orchid": "#da70d6",
    "mediumVioletRed": "#c71585",
    "deepPink": "#ff1493",
    "hotPink": "#ff69b4",
    "lavenderBlush": "#fff0f5",
    "paleVioletRed": "#db7093",
    "crimson": "#dc143c",
    "pink": "#ffc0cb",
    "lightPink": "#ffb6c1",
}


def _format_number(value: float) -> str:
    """Format a number as SLD/SE expects: ints bare, floats trimmed."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    return repr(float(value))


def format_number(value: Any) -> str:
    """Format a bare (unit-less) numeric value for SLD/SE output.

    Public wrapper around :func:`_format_number`, used by raster
    ``se:Threshold`` / ``se:ReliefFactor``.
    """
    return _format_number(value)


def parse_number(text: str | None) -> float | None:
    """Inverse of :func:`format_number`.

    Raises:
    ------
    NotImplementedError
        If *text* is not a valid number — mirrors
        ``reader._scale_denominator_value``'s own guard for the same
        non-numeric-text case, rather than letting a bare ``float()``
        raise ``ValueError``.
    """
    if text is None:
        return None
    try:
        num = float(text)
    except ValueError as exc:
        raise NotImplementedError(f"non-numeric SLD/SE value {text!r}") from exc
    return int(num) if num.is_integer() else num


_UNIT_STRING_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(px|mm|cm|in|pt|em|pc|m|ft)?\s*$"
)


def format_unit_value(value: Any) -> str:
    """Format a CartoSym unit-bearing value as a bare SLD number string.

    Accepts a :class:`UnitValue`, a raw ``{"px": 3.0}`` dict, a plain
    number, or a numeric string — either bare (``"3.0"``) or with a unit
    suffix (``"8.0 m"``, ``"10px"``, matching ``models/types.py``'s own
    ``validate_unit_string`` unit set). The latter shape reaches this
    codec because ``CscssReader``/``CartoSymParser`` produce a ``Style``
    directly, bypassing ``Converter.cscss_to_csjson``'s ``_fix_unit_values``
    post-processing (which only runs on the CS-JSON codec path) — some
    ``Stroke.width``/etc. values are therefore still a raw "N unit" string
    rather than a coerced ``UnitValue``/dict at this point. Non-pixel units
    are silently stripped and only the numeric magnitude is kept — a known,
    documented lossy conversion.

    Raises:
    ------
    NotImplementedError
        If *value* is a non-numeric expression string (property-driven
        sizing has no SLD/SE equivalent in this codec's scope).
    """
    if hasattr(value, "value") and hasattr(value, "unit"):
        return _format_number(value.value)
    if isinstance(value, dict) and len(value) == 1:
        ((_, v),) = value.items()
        return _format_number(v)
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        match = _UNIT_STRING_RE.match(value)
        if match:
            return _format_number(float(match.group(1)))
        raise NotImplementedError(
            f"Property-driven / expression unit value {value!r} has no "
            "SLD/SE mapping in this codec"
        )
    raise NotImplementedError(f"Unsupported unit value shape: {value!r}")


def parse_unit_value(text: str | None) -> dict | None:
    """Parse a bare SLD numeric string back into a CartoSym ``{"px": v}`` dict.

    SLD's implicit unit convention is pixels.
    """
    if text is None:
        return None
    num = float(text)
    if num.is_integer():
        num = int(num)
    return {"px": num}


def format_angle(value: Any) -> str:
    """Format a CartoSym angle as bare SLD/SE degrees.

    ``se:Rotation`` (and similar) are defined in degrees; ``rad``-unit
    input is converted on write.
    """
    if hasattr(value, "value") and hasattr(value, "unit"):
        unit = value.unit
        deg = (
            value.value
            if str(unit) in ("deg", "AngleUnit.DEGREES")
            else math.degrees(value.value)
        )
        return _format_number(deg)
    if isinstance(value, dict):
        unit, v = next(iter(value.items()))
        deg = v if unit == "deg" else math.degrees(v)
        return _format_number(deg)
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        try:
            return _format_number(float(value))
        except ValueError:
            raise NotImplementedError(
                f"Property-driven / expression angle value {value!r} has no "
                "SLD/SE mapping in this codec"
            )
    raise NotImplementedError(f"Unsupported angle value shape: {value!r}")


def parse_angle(text: str | None) -> float | None:
    """Parse a bare ``se:Rotation`` degrees string into a CartoSym float.

    ``FlexibleAngle`` accepts a plain float as degrees directly, so no
    ``Angle`` wrapper is needed here.
    """
    if text is None:
        return None
    return float(text)


def format_opacity(value: Any) -> str:
    """Format a CartoSym opacity (0-1) as a bare SLD/SE number string."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _format_number(value)
    if isinstance(value, str):
        try:
            return _format_number(float(value))
        except ValueError:
            raise NotImplementedError(
                f"Property-driven / expression opacity value {value!r} has "
                "no SLD/SE mapping in this codec"
            )
    raise NotImplementedError(f"Unsupported opacity value shape: {value!r}")


def parse_opacity(text: str | None) -> float | None:
    """Parse a bare SLD opacity string back into a CartoSym float."""
    if text is None:
        return None
    return float(text)


def format_color(value: Any) -> str:
    """Format a CartoSym color as ``#rrggbb`` hex.

    Accepts a :class:`WebColorName`, :class:`RGBColor`,
    :class:`RGBColorNormalized`, an ``[r, g, b]`` list, or a bare hex
    string. Any other string (a CQL2 expression) raises
    :exc:`NotImplementedError` — property-driven color has no mapping in
    this codec's scope.
    """
    if isinstance(value, WebColorName):
        return _WEB_COLOR_HEX[value.value]
    if isinstance(value, RGBColor):
        return f"#{value.r:02x}{value.g:02x}{value.b:02x}"
    if isinstance(value, RGBColorNormalized):
        r, g, b = round(value.r * 255), round(value.g * 255), round(value.b * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    if isinstance(value, dict):
        if {"r", "g", "b"} <= value.keys():
            r, g, b = value["r"], value["g"], value["b"]
            if isinstance(r, float) or isinstance(g, float) or isinstance(b, float):
                if r <= 1.0 and g <= 1.0 and b <= 1.0:
                    r, g, b = round(r * 255), round(g * 255), round(b * 255)
            return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
        raise NotImplementedError(f"Unsupported color dict shape: {value!r}")
    if isinstance(value, (list, tuple)) and len(value) == 3:
        r, g, b = value
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    if isinstance(value, str):
        if value.startswith("#"):
            hexpart = value[1:]
            if len(hexpart) == 3:
                hexpart = "".join(c * 2 for c in hexpart)
            return f"#{hexpart.lower()}"
        if value in _WEB_COLOR_HEX:
            return _WEB_COLOR_HEX[value]
        raise NotImplementedError(
            f"Property-driven / expression color value {value!r} has no "
            "SLD/SE mapping in this codec"
        )
    raise NotImplementedError(f"Unsupported color value shape: {value!r}")


def parse_color(text: str | None) -> list | None:
    """Parse an SLD hex color string or CSS color name into ``[r, g, b]``.

    This is the schema-valid form, matching the same hex-to-array
    convention used by ``ast_converter.py::_parse_color_value`` for CSCSS
    hex literals (the CartoSym-JSON schema's ``color`` definition does not
    accept a bare hex string, only named colors, RGB objects, or
    ``[r, g, b]`` arrays).

    A named color (e.g. ``se:Value`` text inside ``se:Categorize`` may
    legitimately be a plain CSS name — SE's ``ParameterValueType`` is just
    a string, nothing in the XSD forbids it) is looked up and converted
    the same way; names are not preserved as names on read (same
    precedent as hex).
    """
    if text is None:
        return None
    if text in _WEB_COLOR_HEX:
        text = _WEB_COLOR_HEX[text]
    hex_str = text.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) != 6:
        raise NotImplementedError(
            f"Unsupported SLD/SE color text {text!r} (not a #rrggbb/#rgb "
            "hex literal or a known CSS color name)"
        )
    return list(bytes.fromhex(hex_str))
