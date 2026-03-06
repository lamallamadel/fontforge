"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities:
- Access contours/paths.
- Get/set advance width, left/right bearings, unicode mapping.
- Copy glyph outlines from another glyph.

All operations are delegated to the underlying ``fontforge.glyph`` object.
FontForge source code is never modified.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


class Glyph:
    """Pythonic wrapper around a :class:`fontforge.glyph` object.

    Example::

        font = Font.open("MyFont.otf")
        g = font.glyph("A")
        print(g.name, g.width)
    """

    def __init__(self, _ff_glyph: object) -> None:
        """Initialise from an existing fontforge glyph object.

        Args:
            _ff_glyph: A live :class:`fontforge.glyph` instance.
        """
        self._glyph = _ff_glyph

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Glyph name (e.g. ``"A"``, ``"uni0041"``)."""
        return self._glyph.glyphname

    @property
    def unicode(self) -> int:
        """Unicode code point, or ``-1`` if the glyph has no Unicode mapping."""
        return self._glyph.unicode

    @unicode.setter
    def unicode(self, codepoint: int) -> None:
        self._glyph.unicode = codepoint

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width of the glyph in font units."""
        return self._glyph.width

    @width.setter
    def width(self, value: int) -> None:
        self._glyph.width = value

    def set_width(self, value: int) -> None:
        """Set the advance width.  Equivalent to ``glyph.width = value``.

        Args:
            value: New advance width in font units.
        """
        self._glyph.width = value

    @property
    def left_side_bearing(self) -> int:
        """Left side-bearing in font units."""
        return self._glyph.left_side_bearing

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._glyph.left_side_bearing = value

    @property
    def right_side_bearing(self) -> int:
        """Right side-bearing in font units."""
        return self._glyph.right_side_bearing

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        self._glyph.right_side_bearing = value

    @property
    def bounding_box(self) -> Tuple[float, float, float, float]:
        """Return ``(xmin, ymin, xmax, ymax)`` of the glyph's bounding box."""
        return tuple(self._glyph.boundingBox())  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Contours
    # ------------------------------------------------------------------

    @property
    def contours(self) -> object:
        """Raw fontforge layer object containing contour data."""
        return self._glyph.foreground

    def copy_from(self, other: "Glyph") -> None:
        """Replace this glyph's outlines with those of *other*.

        Args:
            other: The source :class:`Glyph` whose outlines to copy.
        """
        self._glyph.clear()
        pen = self._glyph.glyphPen()
        other._glyph.draw(pen)
        pen = None  # flush

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove all outlines from this glyph."""
        self._glyph.clear()

    def auto_hint(self) -> None:
        """Run FontForge's auto-hinting on this glyph."""
        self._glyph.autoHint()

    def auto_instr(self) -> None:
        """Run FontForge's auto-instructing on this glyph (for TTF)."""
        self._glyph.autoInstr()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> object:
        """Direct access to the underlying fontforge glyph (internal use)."""
        return self._glyph

    def __repr__(self) -> str:
        return f"<Glyph: {self.name!r}>"
