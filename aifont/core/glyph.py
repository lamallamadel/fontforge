"""
aifont.core.glyph — High-level Glyph wrapper around FontForge glyphs.

This module provides the :class:`Glyph` class, which wraps a
``fontforge.glyph`` object and exposes a Pythonic interface for reading
and writing glyph geometry, metrics and metadata.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


class Glyph:
    """High-level wrapper around a FontForge glyph object.

    Wraps ``fontforge.glyph`` — do **not** subclass FontForge objects
    directly.

    Parameters
    ----------
    ff_glyph : fontforge.glyph
        The underlying FontForge glyph instance.

    Examples
    --------
    ::

        from aifont.core.font import Font

        font = Font.open("MyFont.otf")
        g = font["A"]
        print(g.name, g.width, g.unicode_value)
        g.set_width(600)
    """

    def __init__(self, ff_glyph: object) -> None:
        self._ff = ff_glyph

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The PostScript glyph name (e.g. ``"A"``, ``"uni0041"``)."""
        return str(self._ff.glyphname)  # type: ignore[attr-defined]

    @name.setter
    def name(self, value: str) -> None:
        self._ff.glyphname = value  # type: ignore[attr-defined]

    @property
    def unicode_value(self) -> int:
        """Unicode code-point, or ``-1`` if unassigned."""
        return int(self._ff.unicode)  # type: ignore[attr-defined]

    @unicode_value.setter
    def unicode_value(self, value: int) -> None:
        self._ff.unicode = value  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Advance width / bearings
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """The advance width of the glyph in font units."""
        return int(self._ff.width)  # type: ignore[attr-defined]

    @width.setter
    def width(self, value: int) -> None:
        self._ff.width = value  # type: ignore[attr-defined]

    def set_width(self, value: int) -> None:
        """Set the advance width.

        Parameters
        ----------
        value : int
            New advance width in font units.
        """
        self.width = value

    @property
    def left_side_bearing(self) -> int:
        """Left side-bearing in font units."""
        return int(self._ff.left_side_bearing)  # type: ignore[attr-defined]

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._ff.left_side_bearing = value  # type: ignore[attr-defined]

    @property
    def right_side_bearing(self) -> int:
        """Right side-bearing in font units."""
        return int(self._ff.right_side_bearing)  # type: ignore[attr-defined]

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        self._ff.right_side_bearing = value  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Vertical metrics
    # ------------------------------------------------------------------

    @property
    def vwidth(self) -> int:
        """Vertical advance width (for CJK fonts)."""
        return int(self._ff.vwidth)  # type: ignore[attr-defined]

    @vwidth.setter
    def vwidth(self, value: int) -> None:
        self._ff.vwidth = value  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Bounding box
    # ------------------------------------------------------------------

    @property
    def bounding_box(self) -> Tuple[float, float, float, float]:
        """Return ``(xmin, ymin, xmax, ymax)`` of the glyph outline.

        Returns
        -------
        tuple
            Four-element tuple ``(xmin, ymin, xmax, ymax)`` in font units.
            Returns ``(0, 0, 0, 0)`` for empty glyphs.
        """
        try:
            bb = self._ff.boundingBox()  # type: ignore[attr-defined]
            return (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))
        except Exception:  # noqa: BLE001
            return (0.0, 0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Contours / foreground layer
    # ------------------------------------------------------------------

    @property
    def contours(self) -> object:
        """The foreground contour layer (``fontforge.layer``).

        This is the raw FontForge layer object; use
        :mod:`aifont.core.contour` helpers for higher-level operations.
        """
        return self._ff.foreground  # type: ignore[attr-defined]

    @property
    def background(self) -> object:
        """The background contour layer (``fontforge.layer``)."""
        return self._ff.background  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Convenience operations
    # ------------------------------------------------------------------

    def copy_from(self, other: "Glyph") -> None:
        """Copy the outline of *other* into this glyph.

        Parameters
        ----------
        other : Glyph
            Source glyph whose foreground layer is copied.
        """
        self._ff.foreground = other._ff.foreground.dup()  # type: ignore[attr-defined]

    def clear(self) -> None:
        """Remove all contours from the foreground layer."""
        self._ff.clear()  # type: ignore[attr-defined]

    def add_reference(self, glyph_name: str) -> None:
        """Add a reference to another glyph.

        Parameters
        ----------
        glyph_name : str
            The name of the glyph to reference.
        """
        self._ff.addReference(glyph_name)  # type: ignore[attr-defined]

    def validate(self) -> int:
        """Run FontForge's built-in glyph validation.

        Returns
        -------
        int
            Bitmask of validation errors (0 = no errors).
        """
        try:
            return int(self._ff.validate(True))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return 0

    # ------------------------------------------------------------------
    # Low-level access
    # ------------------------------------------------------------------

    @property
    def ff_glyph(self) -> object:
        """The underlying ``fontforge.glyph`` object.

        Use this only when you need functionality not yet covered by
        the AIFont wrapper API.
        """
        return self._ff

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Glyph(name={self.name!r}, unicode={self.unicode_value}, "
            f"width={self.width})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Glyph):
            return NotImplemented
        return self._ff is other._ff

    def __hash__(self) -> int:
        return id(self._ff)
