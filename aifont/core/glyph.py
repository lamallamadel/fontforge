"""Glyph wrapper around fontforge.glyph."""

from __future__ import annotations

from typing import Any, Optional


class Glyph:
    """High-level wrapper around a FontForge glyph object.

    Example:
        >>> font = Font.open("MyFont.otf")
        >>> g = font.glyphs[0]
        >>> g.set_width(600)
    """

    def __init__(self, _ff_glyph: Any) -> None:
        self._ff = _ff_glyph

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Glyph name (e.g. ``'A'``, ``'uni0041'``)."""
        return str(self._ff.glyphname)

    @property
    def unicode(self) -> int:
        """Unicode code point, or -1 if unmapped."""
        return int(self._ff.unicode)

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return int(self._ff.width)

    @property
    def left_side_bearing(self) -> int:
        """Left side bearing in font units."""
        return int(self._ff.left_side_bearing)

    @property
    def right_side_bearing(self) -> int:
        """Right side bearing in font units."""
        return int(self._ff.right_side_bearing)

    @property
    def contours(self) -> list:
        """Return the glyph's foreground layer contours."""
        return list(self._ff.foreground)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def set_width(self, width: int) -> None:
        """Set the advance width.

        Args:
            width: New advance width in font units.
        """
        self._ff.width = width

    def set_left_side_bearing(self, value: int) -> None:
        """Set the left side bearing."""
        self._ff.left_side_bearing = value

    def set_right_side_bearing(self, value: int) -> None:
        """Set the right side bearing."""
        self._ff.right_side_bearing = value

    def copy_from(self, other: "Glyph") -> None:
        """Copy contours and metrics from another glyph.

        Args:
            other: Source glyph to copy from.
        """
        self._ff.clear()
        self._ff.importOutlines(other._ff)

    def __repr__(self) -> str:
        return f"<Glyph name={self.name!r} unicode={self.unicode}>"
