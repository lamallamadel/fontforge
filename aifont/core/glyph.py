"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Provides a clean Python API for reading and writing individual glyph
properties (width, bearings, unicode mapping, contour access).

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  This module wraps fontforge glyph
objects; it does not subclass them.
"""Glyph wrapper around fontforge.glyph."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import fontforge as _ff

    _FFGlyph = _ff.glyph


class Glyph:
    """Wraps a :class:`fontforge.glyph` object with a clean Pythonic API.

    This class *wraps* — it does **not** subclass — :class:`fontforge.glyph`.
    All operations are delegated to the internal FontForge object.
    """

    def __init__(self, _ff_glyph: _FFGlyph) -> None:
"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities:
- Access contours / paths.
- Get and set advance width and side-bearings.
- Read / write Unicode mapping.

This module wraps fontforge glyph objects; it does **not** subclass them.
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
        """Glyph name (e.g. ``"A"``, ``"uni0041"``)."""
        """PostScript glyph name."""
        return self._glyph.glyphname

    @property
    def unicode(self) -> int:
        """Unicode codepoint, or ``-1`` if not assigned."""
        return self._glyph.unicode

    @unicode.setter
    def unicode(self, codepoint: int) -> None:
        self._glyph.unicode = codepoint

        """Unicode code point, or ``-1`` if unmapped."""
        return self._glyph.unicode

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

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
        return self._glyph.width

    @width.setter
    def width(self, value: int) -> None:
        self._glyph.width = value

    def set_width(self, value: int) -> None:
        """Set advance width (fluent alternative to ``glyph.width = value``)."""
    def set_width(self, value: int) -> None:
        """Set the advance width in font units.

        Args:
            value: New advance width.
        """
        self._glyph.width = value

    @property
    def left_side_bearing(self) -> int:
        return self._glyph.left_side_bearing

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._glyph.left_side_bearing = value

    @property
    def right_side_bearing(self) -> int:
        return self._glyph.right_side_bearing

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        self._glyph.right_side_bearing = value

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
    def contours(self) -> list:
        """Return the list of contours (fontforge layer contours)."""
        return list(self._glyph.foreground)

    # ------------------------------------------------------------------
    # Copying
    # ------------------------------------------------------------------

    def copy_from(self, other: Glyph) -> None:
        """Copy contours and metrics from *other* into this glyph."""
        self._glyph.clear()
        pen = self._glyph.glyphPen()
        other._glyph.draw(pen)
        self._glyph.width = other._glyph.width

    # ------------------------------------------------------------------
    # Low-level access
    # ------------------------------------------------------------------

    @property
    def _raw(self) -> _FFGlyph:
        """Direct access to the underlying :class:`fontforge.glyph` object."""
        return self._glyph

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Glyph name={self.name!r} unicode={self.unicode}>"
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

        Uses fontforge's built-in copy/paste mechanism to transfer all
        foreground layer outlines from *other* to this glyph.

        Parameters
        ----------
        other:
            The source glyph to copy from.
        """
        self._ff_glyph.clear()
        other._ff_glyph.copy()
        self._ff_glyph.paste()

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Glyph(name={self.name!r}, width={self.width})"
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
