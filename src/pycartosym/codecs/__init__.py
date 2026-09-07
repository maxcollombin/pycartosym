"""Codec registry — automatic format detection and routing.

Each sub-package (``cscss``, ``csjson``, ``sld``, ``maplibre``) registers
its codec here so the CLI and public API can route conversions transparently.
"""

from __future__ import annotations

from pathlib import Path

from .base import Codec, CodecReader, CodecWriter

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, Codec] = {}


def register(codec: Codec) -> Codec:
    """Register a *codec* for each of its declared extensions."""
    for ext in codec.extensions:
        _REGISTRY[ext.lower()] = codec
    # Also register by format name (lower-cased) for --from/--to flags
    _REGISTRY[codec.format_name.lower()] = codec
    return codec


def get_codec(key: str) -> Codec | None:
    """Look up a codec by extension (e.g. ``".cscss"``) or format name."""
    return _REGISTRY.get(key.lower())


def detect_codec(path: Path) -> Codec | None:
    """Auto-detect the codec for *path* from its file extension.

    Handles compound extensions like ``.cs.json`` by trying the longest
    match first.
    """
    name = path.name.lower()
    # Try compound extensions first (e.g. ".cs.json")
    for ext, codec in sorted(_REGISTRY.items(), key=lambda kv: -len(kv[0])):
        if ext.startswith(".") and name.endswith(ext):
            return codec
    # Fallback: simple suffix
    return _REGISTRY.get(path.suffix.lower())


def list_codecs() -> list:
    """Return the list of unique registered codecs."""
    seen = set()
    codecs = []
    for codec in _REGISTRY.values():
        if id(codec) not in seen:
            seen.add(id(codec))
            codecs.append(codec)
    return codecs


# ---------------------------------------------------------------------------
# Auto-register built-in codecs on import
# ---------------------------------------------------------------------------
from .cscss import codec as _cscss_codec  # noqa: E402, F401
from .csjson import codec as _csjson_codec  # noqa: E402, F401

register(_cscss_codec)
register(_csjson_codec)

from .maplibre import codec as _maplibre_codec  # noqa: E402, F401

register(_maplibre_codec)

# SLD/SE needs the optional `sld` extra (lxml) — registered only if it's
# actually importable, so a bare `pip install pycartosym` (core deps only)
# doesn't crash on import; the CLI/API report an unknown format instead.
try:
    from .sld import codec as _sld_codec  # noqa: E402, F401
    from .sld import codec_sld_1_0_0 as _sld10_codec  # noqa: E402
    from .sld import codec_sld_1_1_0 as _sld11_codec  # noqa: E402
    from .sld import codec_sld_geoserver as _sld_geoserver_codec  # noqa: E402
except ImportError:
    pass
else:
    register(_sld_codec)
    register(_sld11_codec)
    register(_sld10_codec)
    register(_sld_geoserver_codec)

__all__ = [
    "Codec",
    "CodecReader",
    "CodecWriter",
    "register",
    "get_codec",
    "detect_codec",
    "list_codecs",
]
