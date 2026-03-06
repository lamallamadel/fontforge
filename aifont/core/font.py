"""
aifont.core.font — high-level Font wrapper around ``fontforge.open()``.

Responsibilities:
- Open and save font files.
- Iterate over glyphs.
- Read/write font-level metadata (name, family, weight, em size, etc.).

All heavy lifting is delegated to the underlying ``fontforge.font`` object.
FontForge source code is never modified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator, Iterator, List, Optional

try:
    import fontforge  # type: ignore
    if not hasattr(fontforge, "font"):
        fontforge = None  # type: ignore  # namespace package stub, not the real extension
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore


class Font:
    """Pythonic wrapper around a :class:`fontforge.font` object.

    Example::

        font = Font.open("MyFont.otf")
        for glyph in font.glyphs:
            print(glyph.name)
        font.save("MyFont_modified.otf")
    """

    def __init__(self, _ff_font: object) -> None:
        """Initialise from an existing fontforge font object.

        Args:
            _ff_font: A live :class:`fontforge.font` instance.
        """
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
            RuntimeError: If the fontforge Python bindings are unavailable.
            IOError: If the file cannot be opened by FontForge.
        """
        if fontforge is None:
            raise RuntimeError(
                "fontforge Python bindings are not available. "
                "Install FontForge with Python support."
            )
        ff = fontforge.open(str(path))
        return cls(ff)

    @classmethod
    def new(cls) -> "Font":
        """Create a new, empty font.

        Returns:
            A new :class:`Font` wrapping a blank fontforge font.

        Raises:
            RuntimeError: If the fontforge Python bindings are unavailable.
        """
        if fontforge is None:
            raise RuntimeError(
                "fontforge Python bindings are not available. "
                "Install FontForge with Python support."
            )
        ff = fontforge.font()
        return cls(ff)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font to *path*.

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
    def glyphs(self) -> List["Glyph"]:
        """Return a list of :class:`~aifont.core.glyph.Glyph` wrappers.

        Only glyphs that are actually present in the font's encoding are
        returned.
        """
        from aifont.core.glyph import Glyph  # local import avoids circular deps

        result: List[Glyph] = []
        for name in self._font:
            try:
                result.append(Glyph(self._font[name]))
            except Exception:
                pass
        return result

    def __iter__(self) -> Iterator["Glyph"]:
        """Iterate over glyphs in the font."""
        return iter(self.glyphs)

    def glyph(self, name_or_unicode: str | int) -> "Glyph":
        """Return a single :class:`~aifont.core.glyph.Glyph` by name or codepoint.

        Args:
            name_or_unicode: Glyph name (str) or Unicode code point (int).

        Returns:
            A :class:`~aifont.core.glyph.Glyph` wrapper.
        """
        from aifont.core.glyph import Glyph

        return Glyph(self._font[name_or_unicode])

    def create_glyph(self, name: str, unicode_point: int = -1) -> "Glyph":
        """Create a new glyph in the font.

        Args:
            name: Glyph name.
            unicode_point: Unicode code point, or -1 for no mapping.

        Returns:
            A :class:`~aifont.core.glyph.Glyph` wrapper for the new glyph.
        """
        from aifont.core.glyph import Glyph

        ff_glyph = self._font.createChar(unicode_point, name)
        return Glyph(ff_glyph)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> dict:
        """Font-level metadata as a plain dictionary.

        Keys: ``fontname``, ``familyname``, ``fullname``, ``weight``,
        ``copyright``, ``em``, ``ascent``, ``descent``, ``upos``,
        ``uwidth``.
        """
        ff = self._font
        return {
            "fontname": getattr(ff, "fontname", ""),
            "familyname": getattr(ff, "familyname", ""),
            "fullname": getattr(ff, "fullname", ""),
            "weight": getattr(ff, "weight", ""),
            "copyright": getattr(ff, "copyright", ""),
            "em": getattr(ff, "em", 1000),
            "ascent": getattr(ff, "ascent", 800),
            "descent": getattr(ff, "descent", 200),
            "upos": getattr(ff, "upos", -100),
            "uwidth": getattr(ff, "uwidth", 50),
        }

    def set_metadata(self, **kwargs: object) -> None:
        """Set font-level metadata fields.

        Accepted keyword arguments match the keys returned by
        :attr:`metadata`.

        Example::

            font.set_metadata(fontname="MyFont", familyname="My Family")
        """
        _allowed = {
            "fontname", "familyname", "fullname", "weight",
            "copyright", "em", "ascent", "descent", "upos", "uwidth",
        }
        for key, value in kwargs.items():
            if key not in _allowed:
                raise ValueError(f"Unknown metadata field: {key!r}")
            setattr(self._font, key, value)

    # ------------------------------------------------------------------
    # Internals / helpers
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> object:
        """Direct access to the underlying fontforge font object (internal use)."""
        return self._font

    def close(self) -> None:
        """Close the underlying fontforge font and release resources."""
        self._font.close()

    def __repr__(self) -> str:
        name = getattr(self._font, "fontname", "<unknown>")
        return f"<Font: {name!r}>"
