"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities
----------------
- Expose contours/paths.
- Get and set advance width and side-bearings.
- Read and write Unicode mapping.

This module wraps fontforge glyph objects; it does **not** subclass them.
"""

from __future__ import annotations

from typing import Any, List, Optional


class Glyph:
    """Pythonic wrapper around a ``fontforge.glyph`` object.

    Do **not** create instances directly — obtain them from
    :class:`~aifont.core.font.AIFont` methods such as
    :meth:`~aifont.core.font.AIFont.get_glyph` or
    :meth:`~aifont.core.font.AIFont.add_glyph`.
    """

    def __init__(self, _ff_glyph: Any) -> None:
        """Wrap an existing ``fontforge.glyph`` object.

        Args:
            _ff_glyph: A live ``fontforge.glyph`` instance.
        """
        self._glyph = _ff_glyph

    # ------------------------------------------------------------------
    # Basic identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The PostScript glyph name (e.g. ``'A'``)."""
        return str(getattr(self._glyph, "glyphname", "") or "")

    @property
    def unicode(self) -> int:
        """The Unicode code point assigned to this glyph, or ``-1``."""
        return int(getattr(self._glyph, "unicode", -1))

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return int(getattr(self._glyph, "width", 0))

    @width.setter
    def width(self, value: int) -> None:
        self._glyph.width = value

    def set_width(self, value: int) -> None:
        """Set the advance width.

        Args:
            value: New advance width in font units.
        """
        self._glyph.width = value

    @property
    def left_side_bearing(self) -> int:
        """Left side-bearing in font units."""
        return int(getattr(self._glyph, "left_side_bearing", 0))

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._glyph.left_side_bearing = value

    @property
    def right_side_bearing(self) -> int:
        """Right side-bearing in font units."""
        return int(getattr(self._glyph, "right_side_bearing", 0))

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        self._glyph.right_side_bearing = value

    # ------------------------------------------------------------------
    # Contours
    # ------------------------------------------------------------------

    @property
    def contours(self) -> List[Any]:
        """A list of ``fontforge.contour`` objects for this glyph's layers.

        Returns an empty list when the glyph has no outlines.
        """
        try:
            layer = self._glyph.foreground
            return list(layer)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Copy helper
    # ------------------------------------------------------------------

    def copy_from(self, other: "Glyph") -> None:
        """Copy the outline and metrics from *other* into this glyph.

        .. warning::
            This method uses FontForge's selection-based copy/paste mechanism
            which relies on mutable global clipboard state.  It is **not**
            thread-safe.  Do not call this method concurrently on the same
            font.

        Args:
            other: Source :class:`Glyph` to copy from.
        """
        self._glyph.clear()
        # fontforge's copy/paste operates via an internal clipboard.
        other._glyph.font.selection.select(other.name)
        other._glyph.font.copy()
        self._glyph.font.selection.select(self.name)
        self._glyph.font.paste()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _ff(self) -> Any:
        """Direct access to the underlying ``fontforge.glyph`` (internal use)."""
        return self._glyph

    def __repr__(self) -> str:
        return f"<Glyph name={self.name!r} unicode={self.unicode!r}>"
