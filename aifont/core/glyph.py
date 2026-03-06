"""aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities:
- Access contours/paths.
- Get/set advance width, left/right bearings, unicode mapping.
- Geometric transformations (scale, rotate, move, skew).
- Typographic operations (remove_overlap, correct_direction, auto_hint).
- Export to SVG / PNG.

All operations are delegated to the underlying ``fontforge.glyph`` object.
FontForge source code is never modified.
"""

from __future__ import annotations

import math
import os
import tempfile
from typing import Any

try:
    import fontforge  # type: ignore
    import psMat  # type: ignore  # noqa: N813 — tests patch aifont.core.glyph.psMat
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore
    psMat = None  # type: ignore  # noqa: N816


def _make_ps_mat() -> Any:
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

    def set_width(self, value: int) -> Glyph:
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
    def contours(self) -> Any:
        """Return the foreground layer (contour container) for this glyph."""
        fg = getattr(self._ff, "foreground", None)
        if fg is None:
            return []
        return fg

    @property
    def has_open_contours(self) -> bool:
        """``True`` if any contour in the foreground layer is open (not closed)."""
        fg = getattr(self._ff, "foreground", None)
        if fg is None:
            return False
        try:
            return any(not getattr(c, "closed", True) for c in fg)
        except Exception:  # noqa: BLE001
            return False

    def add_contour(self, points: list[tuple[float, float]], *, closed: bool = True) -> Glyph:
        """Add a new contour to the glyph's foreground layer.

        Args:
            points: Sequence of ``(x, y)`` tuples defining the contour.
            closed: Whether the contour should be closed (default ``True``).

        Returns:
            *self* for method chaining.
        """
        import fontforge as ff_mod  # type: ignore[import]

        contour = ff_mod.contour()
        for x, y in points:
            contour += ff_mod.point(x, y)
        contour.closed = closed
        self._ff.foreground += contour  # type: ignore[union-attr]
        return self

    # ------------------------------------------------------------------
    # Glyph operations
    # ------------------------------------------------------------------

    def copy_from(self, other: Glyph) -> Glyph:
        """Copy contours and metrics from *other* into this glyph.

        Uses the fontforge pen protocol: clears the destination, obtains
        a glyph pen, and draws the source glyph into it.
        """
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]
        if hasattr(self._ff, "glyphPen"):
            pen = self._ff.glyphPen()  # type: ignore[union-attr]
            if hasattr(other._ff, "draw"):
                other._ff.draw(pen)  # type: ignore[union-attr]
        elif hasattr(other._ff, "foreground") and hasattr(self._ff, "foreground"):
            self._ff.foreground = other._ff.foreground  # type: ignore[union-attr]
        self.width = other.width
        return self

    def remove_all_contours(self) -> Glyph:
        """Remove all contours from the glyph (alias for :meth:`clear`)."""
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]
        return self

    def clear(self) -> Glyph:
        """Remove all contours from the glyph."""
        if hasattr(self._ff, "clear"):
            self._ff.clear()  # type: ignore[union-attr]
        return self

    def auto_hint(self) -> Glyph:
        """Run fontforge's auto-hinting on this glyph."""
        if hasattr(self._ff, "autoHint"):
            self._ff.autoHint()  # type: ignore[union-attr]
        return self

    def remove_overlap(self) -> Glyph:
        """Remove overlapping contours."""
        if hasattr(self._ff, "removeOverlap"):
            self._ff.removeOverlap()  # type: ignore[union-attr]
        return self

    def simplify(self, error_bound: float = 1.0, flags: tuple = ()) -> Glyph:
        """Simplify the glyph's outlines.

        Args:
            error_bound: Maximum deviation allowed when simplifying.
            flags:       Tuple of flag strings passed to fontforge ``simplify()``.
        """
        if hasattr(self._ff, "simplify"):
            self._ff.simplify(error_bound, flags)  # type: ignore[union-attr]
        return self

    def correct_direction(self) -> Glyph:
        """Correct the winding direction of all contours."""
        if hasattr(self._ff, "correctDirection"):
            self._ff.correctDirection()  # type: ignore[union-attr]
        return self

    def round_to_int(self) -> Glyph:
        """Round all point coordinates to integer values."""
        if hasattr(self._ff, "round"):
            self._ff.round()  # type: ignore[union-attr]
        return self

    def stroke(self, width: float = 10.0, stroke_type: str = "circular") -> Glyph:
        """Stroke the glyph's outlines.

        Args:
            width:       Stroke width in font units.
            stroke_type: FontForge stroke type (default ``"circular"``).

        Returns:
            *self* for method chaining.
        """
        if hasattr(self._ff, "stroke"):
            self._ff.stroke(stroke_type, width)  # type: ignore[union-attr]
        return self

    def transform(self, matrix: tuple) -> Glyph:
        """Apply an affine transformation matrix directly.

        Args:
            matrix: A 6-element tuple ``(xx, xy, yx, yy, dx, dy)`` defining
                    the affine transformation.

        Returns:
            *self* for method chaining.
        """
        self._ff.transform(matrix)  # type: ignore[union-attr]
        return self

    def scale(self, factor: float, factor_y: float | None = None) -> Glyph:
        """Scale the glyph uniformly (or non-uniformly).

        Args:
            factor:   Horizontal scale factor (and vertical if *factor_y* is
                      omitted).
            factor_y: Optional separate vertical scale factor.

        Returns:
            *self* for method chaining.
        """
        mat = _make_ps_mat()
        fy = factor_y if factor_y is not None else factor
        self._ff.transform(mat.scale(factor, fy))  # type: ignore[union-attr]
        return self

    def rotate(self, degrees: float) -> Glyph:
        """Rotate the glyph counter-clockwise by *degrees*.

        Args:
            degrees: Rotation angle in degrees.

        Returns:
            *self* for method chaining.
        """
        mat = _make_ps_mat()
        self._ff.transform(mat.rotate(math.radians(degrees)))  # type: ignore[union-attr]
        return self

    def move(self, dx: float = 0.0, dy: float = 0.0) -> Glyph:
        """Translate the glyph by (*dx*, *dy*).

        Args:
            dx: Horizontal offset in font units.
            dy: Vertical offset in font units.

        Returns:
            *self* for method chaining.
        """
        mat = _make_ps_mat()
        self._ff.transform(mat.translate(dx, dy))  # type: ignore[union-attr]
        return self

    def skew(self, degrees: float) -> Glyph:
        """Skew (shear) the glyph horizontally by *degrees*.

        Args:
            degrees: Skew angle in degrees.

        Returns:
            *self* for method chaining.
        """
        mat = _make_ps_mat()
        self._ff.transform(mat.skew(math.radians(degrees)))  # type: ignore[union-attr]
        return self

    def to_svg(self) -> str:
        """Export this glyph as an SVG string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = os.path.join(tmpdir, f"{self.name or 'glyph'}.svg")
            self._ff.export(svg_path)  # type: ignore[union-attr]
            with open(svg_path, encoding="utf-8") as fh:
                return fh.read()

    def to_png(self, size: int = 256) -> bytes:
        """Export this glyph as a PNG image.

        Args:
            size: Pixel size of the output image (default ``256``).

        Returns:
            Raw PNG bytes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = os.path.join(tmpdir, f"{self.name or 'glyph'}.png")
            self._ff.export(png_path, size)  # type: ignore[union-attr]
            with open(png_path, "rb") as fh:
                return fh.read()

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        uni = self.unicode
        uni_str = f"0x{uni:04x}" if uni >= 0 else str(uni)
        return f"Glyph(name={self.name!r}, unicode={uni_str}, width={self.width})"
