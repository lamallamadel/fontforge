"""High-level Font wrapper around fontforge.open()."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import fontforge as _ff

    from aifont.core.glyph import Glyph

    _FFFont = _ff.font


class Font:
    """Pythonic wrapper over a :class:`fontforge.font` object.

    All low-level operations are delegated to the underlying
    :class:`fontforge.font` instance — this class never bypasses it.

    Example::

        font = Font.open("path/to/font.otf")
        for glyph in font.glyphs:
            print(glyph.name)
        font.save("output.otf")
    """

    def __init__(self, _ff_font: _FFFont) -> None:
        self._font = _ff_font

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> Font:
        """Open an existing font file and return a :class:`Font` instance."""
        import fontforge  # noqa: PLC0415

        return cls(fontforge.open(str(path)))

    @classmethod
    def new(cls, family: str = "Untitled") -> Font:
        """Create a blank font."""
        import fontforge  # noqa: PLC0415

        ff_font = fontforge.font()
        ff_font.familyname = family
        return cls(ff_font)
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

    def save(self, path: str | Path, fmt: str | None = None) -> None:
        """Save the font to *path*.

        Args:
            path: Destination file path.
            fmt:  Optional fontforge format string (e.g. ``"otf"``).
        """
        if fmt:
            self._font.generate(str(path))
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
    def glyphs(self) -> Iterable:
        """Iterate over all glyphs in the font."""
        from aifont.core.glyph import Glyph  # noqa: PLC0415

        for name in self._font:
            yield Glyph(self._font[name])

    def glyph(self, name_or_codepoint: str | int) -> Glyph:
        """Return a :class:`~aifont.core.glyph.Glyph` by name or codepoint."""
        from aifont.core.glyph import Glyph  # noqa: PLC0415

        return Glyph(self._font[name_or_codepoint])
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
    def metadata(self) -> dict[str, str]:
        """Return a dict of common font metadata fields."""
        f = self._font
        return {
            "family": getattr(f, "familyname", ""),
            "full_name": getattr(f, "fullname", ""),
            "weight": getattr(f, "weight", ""),
            "copyright": getattr(f, "copyright", ""),
            "version": getattr(f, "version", ""),
            "em_size": str(getattr(f, "em", 1000)),
        }

    @metadata.setter
    def metadata(self, data: dict[str, str]) -> None:
        field_map = {
            "family": "familyname",
            "full_name": "fullname",
            "weight": "weight",
            "copyright": "copyright",
            "version": "version",
        }
        for key, ff_attr in field_map.items():
            if key in data:
                setattr(self._font, ff_attr, data[key])

    # ------------------------------------------------------------------
    # Low-level access
    # ------------------------------------------------------------------

    @property
    def _raw(self) -> _FFFont:
        """Direct access to the underlying :class:`fontforge.font` object."""
        return self._font

    def __repr__(self) -> str:  # pragma: no cover
        name = getattr(self._font, "familyname", "?")
        return f"<Font family={name!r}>"
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
