"""
aifont.core.font — high-level Font wrapper around ``fontforge.font``.

This module provides a clean Pythonic API for opening, inspecting, and
saving fonts.  All low-level operations are delegated to the underlying
``fontforge.font`` object.

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  ``import fontforge`` is treated as
a black-box dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

try:
    import fontforge as _ff
except ImportError:  # pragma: no cover — fontforge may not be installed
    _ff = None  # type: ignore[assignment]


class Font:
    """High-level wrapper around a :class:`fontforge.font` object.

    Parameters
    ----------
    ff_font:
        A raw ``fontforge.font`` instance (returned by ``fontforge.open``
        or ``fontforge.font()``).

    Examples
    --------
    >>> font = Font.open("MyFont.otf")
    >>> for glyph in font.glyphs:
    ...     print(glyph.name)
    >>> font.save("/tmp/MyFont-modified.otf")
    """

    def __init__(self, ff_font: object) -> None:
        self._ff_font = ff_font

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> "Font":
        """Open a font file and return a :class:`Font` instance.

        Parameters
        ----------
        path:
            Absolute or relative path to a font file (.otf, .ttf, .sfd, …).

        Raises
        ------
        RuntimeError
            If FontForge is not installed.
        FileNotFoundError
            If *path* does not exist.
        """
        if _ff is None:
            raise RuntimeError(
                "fontforge Python bindings are not installed. "
                "Install FontForge to use Font.open()."
            )
        resolved = Path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Font file not found: {path!r}")
        return cls(_ff.open(str(resolved)))

    @classmethod
    def new(cls, family_name: str = "Untitled") -> "Font":
        """Create a new, empty :class:`Font`.

        Parameters
        ----------
        family_name:
            The font family name to assign to the new font.

        Raises
        ------
        RuntimeError
            If FontForge is not installed.
        """
        if _ff is None:
            raise RuntimeError(
                "fontforge Python bindings are not installed. "
                "Install FontForge to use Font.new()."
            )
        ff_font = _ff.font()
        ff_font.familyname = family_name
        ff_font.fontname = family_name.replace(" ", "-")
        return cls(ff_font)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def raw(self) -> object:
        """The underlying ``fontforge.font`` object."""
        return self._ff_font

    @property
    def family_name(self) -> str:
        """The font family name."""
        return str(getattr(self._ff_font, "familyname", ""))

    @family_name.setter
    def family_name(self, value: str) -> None:
        self._ff_font.familyname = value

    @property
    def font_name(self) -> str:
        """The PostScript font name."""
        return str(getattr(self._ff_font, "fontname", ""))

    @font_name.setter
    def font_name(self, value: str) -> None:
        self._ff_font.fontname = value

    @property
    def em_size(self) -> int:
        """Units per em (typically 1000 or 2048)."""
        return int(getattr(self._ff_font, "em", 1000))

    @property
    def italic_angle(self) -> float:
        """Italic angle in degrees (0 for upright fonts)."""
        return float(getattr(self._ff_font, "italicangle", 0.0))

    @italic_angle.setter
    def italic_angle(self, value: float) -> None:
        self._ff_font.italicangle = value

    @property
    def ascent(self) -> int:
        """Ascender value in font units."""
        return int(getattr(self._ff_font, "ascent", 800))

    @property
    def descent(self) -> int:
        """Descender value in font units (positive number)."""
        return int(getattr(self._ff_font, "descent", 200))

    @property
    def metadata(self) -> dict:
        """A dictionary of basic font metadata."""
        return {
            "family_name": self.family_name,
            "font_name": self.font_name,
            "em_size": self.em_size,
            "italic_angle": self.italic_angle,
            "ascent": self.ascent,
            "descent": self.descent,
        }

    # ------------------------------------------------------------------
    # Glyph iteration
    # ------------------------------------------------------------------

    @property
    def glyphs(self) -> Iterator["Glyph"]:
        """Iterate over all glyphs in the font.

        Yields
        ------
        Glyph
            Each glyph wrapped in :class:`~aifont.core.glyph.Glyph`.
        """
        from aifont.core.glyph import Glyph

        for name in self._ff_font:
            try:
                ff_glyph = self._ff_font[name]
                yield Glyph(ff_glyph)
            except (KeyError, TypeError):
                continue

    def get_glyph(self, name: str) -> Optional["Glyph"]:
        """Return the :class:`~aifont.core.glyph.Glyph` with the given name.

        Parameters
        ----------
        name:
            PostScript glyph name (e.g. ``"A"``).

        Returns
        -------
        Glyph or None
            ``None`` if the glyph does not exist.
        """
        from aifont.core.glyph import Glyph

        try:
            return Glyph(self._ff_font[name])
        except (KeyError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, fmt: Optional[str] = None) -> None:
        """Save the font to *path*.

        Parameters
        ----------
        path:
            Output file path.  The extension determines the format unless
            *fmt* is given.
        fmt:
            Optional explicit format string passed to
            ``fontforge.font.generate`` (e.g. ``"otf"``).
        """
        out = str(Path(path))
        if fmt is not None:
            self._ff_font.generate(out, flags=(), layer="Fore")
        else:
            self._ff_font.save(out)

    def close(self) -> None:
        """Close the font and free fontforge resources."""
        try:
            self._ff_font.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"Font(family_name={self.family_name!r}, em={self.em_size})"
