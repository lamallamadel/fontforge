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
