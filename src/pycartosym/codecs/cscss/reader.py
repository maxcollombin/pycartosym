"""CSCSS reader — parse CartoSym-CSS files into Style models.

Delegates to the existing :class:`~pycartosym.parser.CartoSymParser`.
"""

from __future__ import annotations

from pathlib import Path

from ...models.styles import Style
from ...parser import CartoSymParser
from ..base import CodecReader


class CscssReader(CodecReader):
    """Read ``.cscss`` files (or raw CSCSS strings) into a Style model."""

    def __init__(self, inline_includes: bool = False) -> None:
        """Create the reader with a fresh :class:`CartoSymParser`."""
        self._parser = CartoSymParser(inline_includes=inline_includes)

    def read(self, source: str | Path) -> Style:
        """Parse *source* and return a validated Style.

        Parameters
        ----------
        source : str | Path
            A filesystem path to a ``.cscss`` file, or the raw CSCSS text.
        """
        if isinstance(source, Path):
            return self._parser.parse_file_to_pydantic(source)

        # Heuristic: short string without newlines that exists on disk → file path
        if (
            isinstance(source, str)
            and len(source) < 500
            and "\n" not in source
            and Path(source).exists()
        ):
            return self._parser.parse_file_to_pydantic(Path(source))

        # Otherwise treat it as raw CSCSS content
        return self._parser.parse_string_to_pydantic(source)
