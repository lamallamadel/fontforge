"""
aifont.core.font — high-level Font wrapper around ``fontforge.open()``.

Responsibilities:
- Open and save font files.
- Iterate over glyphs.
- Read/write font-level metadata (name, family, weight, em size, etc.).

All heavy lifting is delegated to the underlying ``fontforge.font`` object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional

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
    def open(cls, path: str | Path) -> "Font":
        """Open a font file and return a :class:`Font` instance.

        Args:
            path: Path to the font file (.sfd, .otf, .ttf, …).

        Returns:
            A new :class:`Font` wrapping the loaded font.

        Raises:
            RuntimeError: If FontForge cannot open the file.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = fontforge.open(str(path))
        return cls(ff)

    @classmethod
    def new(cls) -> "Font":
        """Create a new, empty font.

        Returns:
            A new :class:`Font` wrapping a blank fontforge font.
        """
        if fontforge is None:
            raise RuntimeError("fontforge Python bindings are not available.")
        ff = fontforge.font()
        return cls(ff)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font.

        Args:
            path: Destination file path.
            fmt:  Optional format string passed to ``fontforge.font.save``
                  (e.g. ``"otf"``).  When *None* the format is inferred from
                  the file extension.
        """
        if fmt is not None:
            self._font.save(str(path), fmt)
        else:
            self._font.save(str(path))

    # ------------------------------------------------------------------
    # Glyph access
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> list:
        """Return a list of :class:`~aifont.core.glyph.Glyph` wrappers.

        Only glyphs that are present in the font (i.e. have an encoding slot
        assigned and contain actual outline data or metrics) are returned.
        """
        from aifont.core.glyph import Glyph  # local import avoids circular deps

        result = []
        for name in self._font:
            try:
                result.append(Glyph(self._font[name]))
            except Exception:
                pass
        return result

    def glyph(self, name_or_unicode: str | int) -> "Glyph":
        """Return a single :class:`~aifont.core.glyph.Glyph` by name or codepoint.

        Args:
            name_or_unicode: Glyph name (str) or Unicode code point (int).
        """
        from aifont.core.glyph import Glyph

        return Glyph(self._font[name_or_unicode])

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> dict:
        """Font-level metadata as a plain dictionary."""
        ff = self._font
        return {
            "fontname": getattr(ff, "fontname", ""),
            "familyname": getattr(ff, "familyname", ""),
            "fullname": getattr(ff, "fullname", ""),
            "weight": getattr(ff, "weight", ""),
            "copyright": getattr(ff, "copyright", ""),
            "version": getattr(ff, "version", ""),
            "em": getattr(ff, "em", 0),
            "ascent": getattr(ff, "ascent", 0),
            "descent": getattr(ff, "descent", 0),
            "upos": getattr(ff, "upos", 0),
            "uwidth": getattr(ff, "uwidth", 0),
        }

    def set_metadata(self, **kwargs: object) -> None:
        """Update font-level metadata fields.

        Keyword arguments correspond to fontforge font attributes such as
        ``fontname``, ``familyname``, ``weight``, etc.
        """
        for key, value in kwargs.items():
            setattr(self._font, key, value)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _ff(self):
        """Direct access to the underlying fontforge font object (internal use)."""
        return self._font

    def close(self) -> None:
        """Close the underlying fontforge font and release resources."""
        try:
            self._font.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        name = getattr(self._font, "fontname", "<unknown>")
        return f"<Font '{name}'>"
