"""MapLibre / MapBox GL Style codec — ``.maplibre.json`` reader and writer."""

from __future__ import annotations

from ..base import Codec
from .reader import MaplibreReader
from .writer import MaplibreWriter

codec = Codec(
    format_name="maplibre",
    extensions=[".maplibre.json"],
    reader=MaplibreReader(),
    writer=MaplibreWriter(),
)

__all__ = ["codec", "MaplibreReader", "MaplibreWriter"]
