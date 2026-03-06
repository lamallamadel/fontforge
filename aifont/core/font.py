"""
aifont.core.font — high-level Font wrapper around ``fontforge.open()``.

Responsibilities:
- Open and save font files.
- Iterate over glyphs.
- Read/write font-level metadata (name, family, weight, em size, etc.).

All heavy lifting is delegated to the underlying ``fontforge.font`` object.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterator, List, Optional, Union

try:
    import fontforge  # type: ignore
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore  # Allow import in environments without FontForge


class Font:
    """Pythonic wrapper around a :class:`fontforge.font` object."""

    def __init__(self, _ff_font: object) -> None:
        """Initialise from an existing fontforge font object."""
        self._font = _ff_font

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: Union[str, Path]) -> "Font":
        """Open an existing font file.

        Args:
            path: Path to the font file (.sfd, .otf, .ttf, …).

        Returns:
            A new :class:`Font` instance.

        Raises:
            RuntimeError: If the fontforge bindings are unavailable.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        return cls(fontforge.open(str(path)))

    @classmethod
    def new(cls) -> "Font":
        """Create a new, empty font.

        Returns:
            A new :class:`Font` instance.

        Raises:
            RuntimeError: If the fontforge bindings are unavailable.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        return cls(fontforge.font())

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Union[str, Path], fmt: Optional[str] = None) -> None:
        """Save the font.

        When *fmt* is ``None`` the font is saved in FontForge's native SFD
        format via ``font.save()``.  When *fmt* is provided (e.g. ``"otf"``,
        ``"ttf"``, ``"woff2"``) the font is exported via ``font.generate()``
        using *path*; if *path* does not already carry the right extension it
        is appended automatically so that FontForge infers the correct output
        format from the filename.

        Args:
            path: Destination file path.
            fmt:  Optional target format extension without a leading dot
                  (e.g. ``"otf"``, ``"ttf"``).  When *None* the font is saved
                  in SFD format.
        """
        p = Path(path)
        if fmt is None:
            self._font.save(str(p))
        else:
            # Ensure the file extension matches the requested format so that
            # FontForge can determine the output format from the filename.
            ext = fmt.lstrip(".")
            if p.suffix.lstrip(".").lower() != ext.lower():
                p = p.with_suffix(f".{ext}")
            self._font.generate(str(p))

    # ------------------------------------------------------------------
    # Glyph access
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> List["Glyph"]:
        """Return a list of :class:`~aifont.core.glyph.Glyph` wrappers.

        Only glyphs that are present in the font (i.e. have an encoding slot
        assigned and contain actual outline data or metrics) are returned.
        """
        from aifont.core.glyph import Glyph  # local import avoids circular deps

        result: List[Glyph] = []
        for name in self._font:
            try:
                result.append(Glyph(self._font[name]))
            except Exception:
                pass
        return result

    def glyph(self, name_or_unicode: Union[str, int]) -> "Glyph":
        """Return a single :class:`~aifont.core.glyph.Glyph` by name or codepoint.

        Args:
            name_or_unicode: Glyph name (str) or Unicode code point (int).

        Returns:
            :class:`~aifont.core.glyph.Glyph` wrapper.
        """
        from aifont.core.glyph import Glyph

        return Glyph(self._font[name_or_unicode])

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> dict:
        """Font-level metadata as a plain dictionary."""
        f = self._font
        return {
            "family_name": getattr(f, "familyname", ""),
            "full_name": getattr(f, "fullname", ""),
            "weight": getattr(f, "weight", ""),
            "version": getattr(f, "version", ""),
            "copyright": getattr(f, "copyright", ""),
            "em_size": getattr(f, "em", 1000),
            "ascent": getattr(f, "ascent", 800),
            "descent": getattr(f, "descent", 200),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> object:
        """Direct access to the underlying fontforge font object (internal use)."""
        return self._font

    def __repr__(self) -> str:
        name = getattr(self._font, "fontname", "?")
        return f"<Font '{name}'>"
