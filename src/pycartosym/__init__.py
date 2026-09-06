"""Lossless transcoding between CartoSym-CSS, CS-JSON and other encodings.

This package provides tools for converting between CartoSym CSS, CartoSym
JSON format, and other cartographic symbology encodings like SLD (Styled
Layer Descriptor) and MapLibre GL Style.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: pyproject.toml's [project] version, read back
    # from the installed distribution's metadata — no hardcoded literal to
    # drift out of sync with it.
    __version__ = version("pycartosym")
except PackageNotFoundError:
    # Not installed (e.g. run from a source checkout without `uv sync`).
    __version__ = "0.0.0+unknown"

__author__ = "Maxime Collombin"
__email__ = "maxime.collombin@netplus.ch"

# Codec registry (lazy — sub-codecs register on first import of .codecs)
from .codecs import detect_codec, get_codec, list_codecs  # noqa: F401
from .converter import Converter
from .exceptions import CartoSymError, CartoSymSyntaxError
from .parser import CartoSymParser

__all__ = [
    "CartoSymParser",
    "Converter",
    "CartoSymError",
    "CartoSymSyntaxError",
    "get_codec",
    "detect_codec",
    "list_codecs",
]
