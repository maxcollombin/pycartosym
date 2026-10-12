"""MapLibre / MapBox GL Style reader — style JSON → CartoSym Style models.

Scope: ``fill`` / ``line`` / ``circle`` / ``symbol`` / ``background``
layers, paint / layout values that are constants or mapped value
expressions, and layer ``filter`` (see ``_layers`` / ``_expressions`` /
``_filter``). Everything else (``raster`` layers, legacy ``{"stops": …}``
functions, unmapped operators) raises :exc:`NotImplementedError` rather
than being silently dropped, per this project's lossless-transcoding
requirement.

One MapLibre layer can produce more than one ``stylingRule`` — a
top-level ``["step", ["zoom"], …]`` paint/layout value (a discrete,
piecewise-constant function of zoom) explodes into one rule per zoom
segment, each ``viz.sd``-scoped; see
``._layers.layer_to_styling_rules``/``_expand_step_zoom_layers``. A
continuous ``["interpolate", …, ["zoom"], …]`` or legacy
``{"stops": …}`` zoom function has no such decomposition (CartoSym's only
zoom/scale concept is the same finite, rule-level ``viz.sd``) and stays
out of scope, raising as before.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from ...models.styles import Style
from ..base import CodecReader
from ._layers import layer_to_styling_rules


class MaplibreReader(CodecReader):
    """Read a MapLibre GL style (``.json`` file, path, string, or dict)."""

    def read(self, source: str | Path | dict[str, Any]) -> Style:
        """Parse *source* into a validated :class:`Style`.

        Args:
            source: a filesystem path, the raw JSON text, or an
                already-parsed style ``dict``.

        Returns:
            The validated CartoSym Style model.

        Raises:
            NotImplementedError: the style uses a construct this codec
                does not map yet (see the module docstring).
        """
        style = self._load(source)

        version = style.get("version")
        if version != 8:
            raise NotImplementedError(
                f"MapLibre style version {version!r} is not supported (expected 8)"
            )

        rules = [
            rule
            for layer in style.get("layers", [])
            for rule in layer_to_styling_rules(layer)
        ]
        return Style(styling_rules=rules)

    @staticmethod
    def _load(source: str | Path | dict[str, Any]) -> dict[str, Any]:
        if isinstance(source, dict):
            return source
        if isinstance(source, Path):
            text = source.read_text(encoding="utf-8")
        else:
            # A str is JSON text, or a path to a file.
            text = source
            if "\n" not in source and len(source) < 4096:
                candidate = Path(source)
                if candidate.is_file():
                    text = candidate.read_text(encoding="utf-8")
        return cast("dict[str, Any]", json.loads(text))
