"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities:
- Access contours / paths.
- Get and set advance width and side-bearings.
- Read / write Unicode mapping.

This module wraps fontforge glyph objects; it does **not** subclass them.
"""

from __future__ import annotations

from typing import Optional


class Glyph:
    """Pythonic wrapper around a ``fontforge.glyph`` object."""

    def __init__(self, _ff_glyph: object) -> None:
        self._glyph = _ff_glyph

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """PostScript glyph name."""
        return self._glyph.glyphname

    @property
    def unicode(self) -> int:
        """Unicode code point, or ``-1`` if unmapped."""
        return self._glyph.unicode

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return self._glyph.width

    def set_width(self, value: int) -> None:
        """Set the advance width in font units.

        Args:
            value: New advance width.
        """
        self._glyph.width = value

    @property
    def left_side_bearing(self) -> int:
        """Left side-bearing in font units."""
        return self._glyph.left_side_bearing

    @property
    def right_side_bearing(self) -> int:
        """Right side-bearing in font units."""
        return self._glyph.right_side_bearing

    # ------------------------------------------------------------------
    # Contours
    # ------------------------------------------------------------------

    @property
    def contours(self):
        """Return the foreground layer contour/path data (fontforge layer object)."""
        return self._glyph.foreground

    @property
    def has_open_contours(self) -> bool:
        """Return True if any foreground contour is open (not closed)."""
        layer = self._glyph.foreground
        for contour in layer:
            if not contour.closed:
                return True
        return False

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def copy_from(self, other: "Glyph") -> None:
        """Copy contour data from *other* into this glyph.

        Args:
            other: Source :class:`Glyph` to copy from.
        """
        self._glyph.clear()
        pen = self._glyph.glyphPen()
        other._glyph.draw(pen)

    @property
    def _ff(self):
        """Direct access to the underlying fontforge glyph object (internal use)."""
        return self._glyph

    def __repr__(self) -> str:
        return f"<Glyph '{self.name}' U+{self.unicode:04X}>" if self.unicode >= 0 else f"<Glyph '{self.name}'>"
