"""Glyph wrapper around fontforge.glyph."""

from __future__ import annotations

from typing import List, Optional, Tuple


class Glyph:
    """Pythonic wrapper around a fontforge.glyph object.

    Wraps (does not subclass) the underlying fontforge glyph so that
    all operations remain transparent and testable.
    """

    def __init__(self, _ff_glyph: object) -> None:
        self._ff = _ff_glyph

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Glyph name (e.g., ``"A"``, ``"uni0041"``)."""
        return getattr(self._ff, "glyphname", "")

    @property
    def unicode(self) -> int:
        """Unicode code point, or ``-1`` if not mapped."""
        return int(getattr(self._ff, "unicode", -1))

    @unicode.setter
    def unicode(self, value: int) -> None:
        self._ff.unicode = value  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return int(getattr(self._ff, "width", 0))

    @width.setter
    def width(self, value: int) -> None:
        self._ff.width = int(value)  # type: ignore[union-attr]

    def set_width(self, value: int) -> None:
        """Set the advance width (fluent helper)."""
        self.width = value

    @property
    def left_side_bearing(self) -> int:
        return int(getattr(self._ff, "left_side_bearing", 0))

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._ff.left_side_bearing = int(value)  # type: ignore[union-attr]

    @property
    def right_side_bearing(self) -> int:
        return int(getattr(self._ff, "right_side_bearing", 0))

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        self._ff.right_side_bearing = int(value)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Contours / paths
    # ------------------------------------------------------------------

    @property
    def contours(self) -> List[object]:
        """Return the raw fontforge contour objects for this glyph."""
        fg = getattr(self._ff, "foreground", None)
        if fg is None:
            return []
        try:
            return list(fg)
        except TypeError:
            return []

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def copy_from(self, other: "Glyph") -> None:
        """Copy contours and metrics from *other* into this glyph."""
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]
        if hasattr(other._ff, "foreground") and hasattr(self._ff, "foreground"):
            self._ff.foreground = other._ff.foreground  # type: ignore[union-attr]
        self.width = other.width

    def clear(self) -> None:
        """Remove all contours from the glyph."""
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]

    def auto_hint(self) -> None:
        """Run fontforge's auto-hinting on this glyph."""
        if hasattr(self._ff, "autoHint"):
            self._ff.autoHint()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Glyph(name={self.name!r}, unicode={self.unicode:#06x}, "
            f"width={self.width})"
        )
