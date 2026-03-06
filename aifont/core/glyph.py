"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Provides a clean Python API for reading and writing individual glyph
properties (width, bearings, unicode mapping, contour access).

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  This module wraps fontforge glyph
objects; it does not subclass them.
"""

from __future__ import annotations

from typing import Optional, Tuple


class Glyph:
    """Wrapper around a ``fontforge.glyph`` object.

    Parameters
    ----------
    ff_glyph:
        A raw ``fontforge.glyph`` instance obtained from a
        :class:`~aifont.core.font.Font`.

    Examples
    --------
    >>> glyph = font.get_glyph("A")
    >>> print(glyph.name, glyph.width)
    >>> glyph.set_width(600)
    """

    def __init__(self, ff_glyph: object) -> None:
        self._ff_glyph = ff_glyph

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def raw(self) -> object:
        """The underlying ``fontforge.glyph`` object."""
        return self._ff_glyph

    @property
    def name(self) -> str:
        """PostScript glyph name."""
        return str(getattr(self._ff_glyph, "glyphname", ""))

    @property
    def unicode(self) -> int:
        """Unicode code point, or -1 if unencoded."""
        return int(getattr(self._ff_glyph, "unicode", -1))

    @unicode.setter
    def unicode(self, value: int) -> None:
        self._ff_glyph.unicode = value

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return int(getattr(self._ff_glyph, "width", 0))

    @property
    def lsb(self) -> int:
        """Left side-bearing in font units."""
        return int(getattr(self._ff_glyph, "left_side_bearing", 0))

    @property
    def rsb(self) -> int:
        """Right side-bearing in font units."""
        return int(getattr(self._ff_glyph, "right_side_bearing", 0))

    @property
    def bounding_box(self) -> Tuple[float, float, float, float]:
        """Bounding box as ``(xmin, ymin, xmax, ymax)``."""
        bb = getattr(self._ff_glyph, "boundingBox", None)
        if callable(bb):
            return tuple(bb())  # type: ignore[return-value]
        return (0.0, 0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def set_width(self, width: int) -> None:
        """Set the advance width to *width* font units."""
        self._ff_glyph.width = width

    def set_bearings(self, lsb: Optional[int] = None, rsb: Optional[int] = None) -> None:
        """Set left and/or right side bearings.

        Parameters
        ----------
        lsb:
            New left side-bearing value.  Unchanged if ``None``.
        rsb:
            New right side-bearing value.  Unchanged if ``None``.
        """
        if lsb is not None:
            self._ff_glyph.left_side_bearing = lsb
        if rsb is not None:
            self._ff_glyph.right_side_bearing = rsb

    def copy_from(self, other: "Glyph") -> None:
        """Copy contour data from *other* into this glyph.

        Parameters
        ----------
        other:
            The source glyph to copy from.
        """
        self._ff_glyph.clear()
        self._ff_glyph.addReference(other.name)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Glyph(name={self.name!r}, width={self.width})"
