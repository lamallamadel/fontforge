"""aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities:
- Access contours/paths.
- Get/set advance width, left/right bearings, unicode mapping.
- Geometric transformations (scale, rotate, move, skew).
- Typographic operations (remove_overlap, correct_direction, auto_hint).
- Export to SVG.

All operations are delegated to the underlying ``fontforge.glyph`` object.
FontForge source code is never modified.
"""

from __future__ import annotations

import math
import os
import tempfile
from typing import Any, List, Optional, Tuple

try:
    import fontforge  # type: ignore
    import psMat  # type: ignore
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore
    psMat = None  # type: ignore


def _make_psMat() -> Any:
    """Return psMat, raising a clear error if unavailable."""
    if psMat is None:  # pragma: no cover
        raise RuntimeError("psMat module is not available (requires compiled FontForge).")
    return psMat


class Glyph:
    """Pythonic wrapper around a :class:`fontforge.glyph` object.

    Example::

        font = Font.open("MyFont.otf")
        g = font["A"]
        print(g.name, g.width, g.unicode_value)
        g.set_width(600)
    """

    def __init__(self, _ff_glyph: Any) -> None:
        """Wrap an existing ``fontforge.glyph`` object.

        Args:
            _ff_glyph: A live ``fontforge.glyph`` instance.
        """
        self._ff = _ff_glyph

    # ------------------------------------------------------------------
    # Raw access
    # ------------------------------------------------------------------

    @property
    def raw(self) -> Any:
        """The underlying ``fontforge.glyph`` object."""
        return self._ff

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The PostScript glyph name (e.g. ``"A"``, ``"uni0041"``)."""
        return str(getattr(self._ff, "glyphname", "") or "")

    @name.setter
    def name(self, value: str) -> None:
        self._ff.glyphname = value  # type: ignore[union-attr]

    @property
    def unicode(self) -> int:
        """Unicode code point, or ``-1`` if not mapped."""
        return int(getattr(self._ff, "unicode", -1))

    @unicode.setter
    def unicode(self, value: int) -> None:
        self._ff.unicode = value  # type: ignore[union-attr]

    @property
    def unicode_value(self) -> int:
        """Alias for :attr:`unicode`."""
        return self.unicode

    @unicode_value.setter
    def unicode_value(self, value: int) -> None:
        self.unicode = value

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width of the glyph in font units."""
        return int(getattr(self._ff, "width", 0))

    @width.setter
    def width(self, value: int) -> None:
        value = int(value)
        if value < 0:
            raise ValueError(f"width must be non-negative, got {value}")
        self._ff.width = value  # type: ignore[union-attr]

    def set_width(self, value: int) -> "Glyph":
        """Set the advance width (chainable).

        Args:
            value: New advance width in font units.

        Returns:
            *self* for method chaining.
        """
        self.width = value
        return self

    @property
    def left_side_bearing(self) -> int:
        """Left side-bearing in font units."""
        return int(getattr(self._ff, "left_side_bearing", 0))

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._ff.left_side_bearing = int(value)  # type: ignore[union-attr]

    @property
    def right_side_bearing(self) -> int:
        """Right side-bearing in font units."""
        return int(getattr(self._ff, "right_side_bearing", 0))

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        self._ff.right_side_bearing = int(value)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Contours / paths
    # ------------------------------------------------------------------

    @property
    def contours(self) -> List[Any]:
        """Return the raw fontforge contour objects for this glyph."""
        fg = getattr(self._ff, "foreground", None)
        if fg is None:
            return []
        try:
            return list(fg)
        except TypeError:
            return []

    # ------------------------------------------------------------------
    # Glyph operations
    # ------------------------------------------------------------------

    def copy_from(self, other: "Glyph") -> "Glyph":
        """Copy contours and metrics from *other* into this glyph."""
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]
        if hasattr(other._ff, "foreground") and hasattr(self._ff, "foreground"):
            self._ff.foreground = other._ff.foreground  # type: ignore[union-attr]
        self.width = other.width
        return self

    def clear(self) -> "Glyph":
        """Remove all contours from the glyph."""
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]
        return self

    def auto_hint(self) -> "Glyph":
        """Run fontforge's auto-hinting on this glyph."""
        if hasattr(self._ff, "autoHint"):
            self._ff.autoHint()  # type: ignore[union-attr]
        return self

    def remove_overlap(self) -> "Glyph":
        """Remove overlapping contours."""
        if hasattr(self._ff, "removeOverlap"):
            self._ff.removeOverlap()  # type: ignore[union-attr]
        return self

    def simplify(self, error_bound: float = 1.0) -> "Glyph":
        """Simplify the glyph's outlines."""
        if hasattr(self._ff, "simplify"):
            self._ff.simplify(error_bound)  # type: ignore[union-attr]
        return self

    def correct_direction(self) -> "Glyph":
        """Correct the winding direction of all contours."""
        if hasattr(self._ff, "correctDirection"):
            self._ff.correctDirection()  # type: ignore[union-attr]
        return self

    def scale(self, factor: float, factor_y: Optional[float] = None) -> "Glyph":
        """Scale the glyph uniformly (or non-uniformly)."""
        mat = _make_psMat()
        fy = factor_y if factor_y is not None else factor
        self._ff.transform(mat.scale(factor, fy))  # type: ignore[union-attr]
        return self

    def rotate(self, degrees: float) -> "Glyph":
        """Rotate the glyph counter-clockwise by *degrees*."""
        mat = _make_psMat()
        self._ff.transform(mat.rotate(math.radians(degrees)))  # type: ignore[union-attr]
        return self

    def to_svg(self) -> str:
        """Export this glyph as an SVG string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = os.path.join(tmpdir, f"{self.name or 'glyph'}.svg")
            self._ff.export(svg_path)  # type: ignore[union-attr]
            with open(svg_path, "r", encoding="utf-8") as fh:
                return fh.read()

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Glyph(name={self.name!r}, unicode={self.unicode:#06x}, "
            f"width={self.width})"
        )
