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
        """Unicode codepoint, or ``-1`` if not assigned."""
        return self._glyph.unicode

    @unicode.setter
    def unicode(self, codepoint: int) -> None:
        self._glyph.unicode = codepoint

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return self._glyph.width

    @width.setter
    def width(self, value: int) -> None:
        self._glyph.width = value

    def set_width(self, value: int) -> None:
        """Set advance width (fluent alternative to ``glyph.width = value``)."""
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
