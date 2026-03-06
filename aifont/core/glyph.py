"""
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Responsibilities:
- Access contours / paths.
- Get and set advance width, bearings, and Unicode mapping.
- Contour manipulation (add, remove, simplify).
- Geometric transformations (scale, rotate, move, skew).
- Typographic operations (stroke, remove_overlap, correct_direction).
- Export to SVG / PNG for previewing.

This module wraps fontforge glyph objects; it does **not** subclass them.
"""

from __future__ import annotations

import io
import math
import tempfile
import os
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

try:
    import fontforge  # type: ignore
    import psMat  # type: ignore
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore
    psMat = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _psMat_available() -> bool:
    return psMat is not None


def _make_psMat():
    """Import psMat lazily and raise a clear error if unavailable."""
    if psMat is None:  # pragma: no cover
        raise RuntimeError("psMat module is not available (requires compiled FontForge).")
    return psMat


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class Glyph:
    """Pythonic wrapper around a ``fontforge.glyph`` object.

    All mutation methods return ``self`` to allow method chaining::

        glyph.scale(1.2).rotate(15).round_to_int()
    """

    def __init__(self, _ff_glyph: object) -> None:
        """Initialise from an existing fontforge glyph object.

        Args:
            _ff_glyph: A ``fontforge.glyph`` instance.
        """
        self._glyph = _ff_glyph

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """PostScript glyph name."""
        return self._glyph.glyphname

    @property
    def unicode(self) -> int:
        """Unicode code point, or ``-1`` if unmapped."""
        return self._glyph.unicode

    @unicode.setter
    def unicode(self, value: int) -> None:
        """Set the Unicode code point.

        Args:
            value: Unicode code point (or -1 to unmap).
        """
        self._glyph.unicode = value

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Advance width in font units."""
        return self._glyph.width

    @width.setter
    def width(self, value: int) -> None:
        """Set the advance width in font units.

        Args:
            value: New advance width (non-negative integer).

        Raises:
            ValueError: If *value* is negative.
        """
        value = int(value)
        if value < 0:
            raise ValueError(f"width must be non-negative, got {value}")
        self._glyph.width = value

    def set_width(self, value: int) -> "Glyph":
        """Set the advance width in font units (chainable).

        Args:
            value: New advance width.

        Returns:
            *self* for method chaining.
        """
        self.width = value
        return self

    @property
    def left_side_bearing(self) -> int:
        """Left side-bearing in font units."""
        return self._glyph.left_side_bearing

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        """Set the left side-bearing.

        Args:
            value: New left side-bearing in font units.
        """
        self._glyph.left_side_bearing = int(value)

    @property
    def right_side_bearing(self) -> int:
        """Right side-bearing in font units."""
        return self._glyph.right_side_bearing

    @right_side_bearing.setter
    def right_side_bearing(self, value: int) -> None:
        """Set the right side-bearing.

        Args:
            value: New right side-bearing in font units.
        """
        self._glyph.right_side_bearing = int(value)

    # ------------------------------------------------------------------
    # Contours
    # ------------------------------------------------------------------

    @property
    def contours(self):
        """Return the foreground layer contour/path data (fontforge layer object)."""
        return self._glyph.foreground

    @property
    def has_open_contours(self) -> bool:
        """Return ``True`` if any foreground contour is open (not closed)."""
        layer = self._glyph.foreground
        for contour in layer:
            if not contour.closed:
                return True
        return False

    def add_contour(
        self,
        points: Sequence[Tuple[float, float]],
        closed: bool = True,
    ) -> "Glyph":
        """Add a contour defined by a sequence of on-curve points.

        Each element of *points* is a ``(x, y)`` tuple which becomes a
        ``fontforge.point`` with ``on_curve=True``.  For full control over
        curve types (cubic / quadratic Bézier off-curve nodes) build the
        ``fontforge.contour`` manually and use
        :py:meth:`add_fontforge_contour` instead.

        Args:
            points: Sequence of ``(x, y)`` tuples representing on-curve nodes.
            closed: Whether the contour should be closed.  Defaults to ``True``.

        Returns:
            *self* for method chaining.
        """
        if fontforge is None:  # pragma: no cover
            raise RuntimeError("fontforge Python bindings are not available.")

        contour = fontforge.contour()
        for x, y in points:
            pt = fontforge.point(x, y, True)
            contour += pt
        contour.closed = closed

        layer = self._glyph.foreground
        layer += contour
        self._glyph.foreground = layer
        return self

    def add_fontforge_contour(self, contour: object) -> "Glyph":
        """Add a pre-built ``fontforge.contour`` object to this glyph.

        Args:
            contour: A ``fontforge.contour`` instance.

        Returns:
            *self* for method chaining.
        """
        layer = self._glyph.foreground
        layer += contour
        self._glyph.foreground = layer
        return self

    def remove_all_contours(self) -> "Glyph":
        """Clear all foreground contours from this glyph.

        Returns:
            *self* for method chaining.
        """
        self._glyph.clear()
        return self

    # ------------------------------------------------------------------
    # Typographic operations
    # ------------------------------------------------------------------

    def simplify(
        self,
        error_bound: float = 1.0,
        *,
        flags: Tuple[str, ...] = ("setstarttoextremum", "removesingletonpoints"),
    ) -> "Glyph":
        """Simplify the glyph's outlines by removing redundant nodes.

        Args:
            error_bound:
                Maximum distance (in font units) that the simplified curve
                may deviate from the original.  Defaults to ``1.0``.
            flags:
                Tuple of FontForge simplify flags.

        Returns:
            *self* for method chaining.
        """
        self._glyph.simplify(error_bound, flags)
        return self

    def remove_overlap(self) -> "Glyph":
        """Remove overlapping contours and merge them into a single outline.

        Returns:
            *self* for method chaining.
        """
        self._glyph.removeOverlap()
        return self

    def correct_direction(self) -> "Glyph":
        """Correct the winding direction of all contours.

        Outer contours will be counter-clockwise; inner (counter) contours
        will be clockwise, following PostScript/OTF conventions.

        Returns:
            *self* for method chaining.
        """
        self._glyph.correctDirection()
        return self

    def auto_hint(self) -> "Glyph":
        """Auto-hint the glyph for PostScript (Type 1 / OTF CFF) output.

        Returns:
            *self* for method chaining.
        """
        self._glyph.autoHint()
        return self

    def round_to_int(self) -> "Glyph":
        """Round all point coordinates to the nearest integer.

        Returns:
            *self* for method chaining.
        """
        self._glyph.round()
        return self

    def stroke(
        self,
        width: float = 50,
        *,
        line_cap: str = "butt",
        line_join: str = "miter",
        stroke_type: str = "circular",
    ) -> "Glyph":
        """Expand stroke outlines by *width* (bold / stroke effect).

        This calls ``fontforge.glyph.stroke()`` which converts the glyph's
        contours into filled outlines expanded by the given pen width.

        Args:
            width:
                Pen width in font units.  Defaults to ``50``.
            line_cap:
                Line cap style: ``"butt"`` (default), ``"round"``, or
                ``"square"``.
            line_join:
                Line join style: ``"miter"`` (default), ``"round"``, or
                ``"bevel"``.
            stroke_type:
                Stroke shape: ``"circular"`` (default) or ``"caligraphic"``.

        Returns:
            *self* for method chaining.
        """
        self._glyph.stroke(stroke_type, width, line_cap, line_join)
        return self

    # ------------------------------------------------------------------
    # Geometric transformations
    # ------------------------------------------------------------------

    def scale(self, factor: float, *, factor_y: Optional[float] = None) -> "Glyph":
        """Scale the glyph uniformly (or non-uniformly).

        Args:
            factor:   Horizontal scale factor.
            factor_y: Vertical scale factor.  When omitted *factor* is used
                      for both axes (uniform scaling).

        Returns:
            *self* for method chaining.
        """
        mat = _make_psMat()
        fy = factor_y if factor_y is not None else factor
        self._glyph.transform(mat.scale(factor, fy))
        return self

    def rotate(self, degrees: float) -> "Glyph":
        """Rotate the glyph around the origin by *degrees* (counter-clockwise).

        Args:
            degrees: Rotation angle in degrees.

        Returns:
            *self* for method chaining.
        """
        mat = _make_psMat()
        radians = math.radians(degrees)
        self._glyph.transform(mat.rotate(radians))
        return self

    def move(self, dx: float = 0, dy: float = 0) -> "Glyph":
        """Translate the glyph by *(dx, dy)* font units.

        Args:
            dx: Horizontal displacement.
            dy: Vertical displacement.

        Returns:
            *self* for method chaining.
        """
        mat = _make_psMat()
        self._glyph.transform(mat.translate(dx, dy))
        return self

    def skew(self, degrees: float) -> "Glyph":
        """Apply a horizontal skew (shear) transformation.

        Args:
            degrees: Skew angle in degrees.

        Returns:
            *self* for method chaining.
        """
        mat = _make_psMat()
        radians = math.radians(degrees)
        self._glyph.transform(mat.skew(radians))
        return self

    def transform(self, matrix: Sequence[float]) -> "Glyph":
        """Apply an arbitrary 2×3 affine transformation matrix.

        The matrix is specified as a flat sequence of six values
        ``[xx, xy, yx, yy, dx, dy]`` representing the PostScript matrix
        ``[xx xy yx yy dx dy]``.

        Args:
            matrix: Six-element sequence of floats.

        Returns:
            *self* for method chaining.
        """
        self._glyph.transform(tuple(matrix))
        return self

    # ------------------------------------------------------------------
    # Export / Preview
    # ------------------------------------------------------------------

    def to_svg(self) -> str:
        """Export this glyph as an SVG string.

        FontForge writes an SVG file for the glyph and this method reads
        it back as a string.

        Returns:
            SVG markup as a UTF-8 string.

        Raises:
            RuntimeError: If the export fails.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = os.path.join(tmpdir, f"{self.name}.svg")
            self._glyph.export(svg_path)
            with open(svg_path, "r", encoding="utf-8") as fh:
                return fh.read()

    def to_png(self, size: int = 256) -> bytes:
        """Rasterise this glyph at *size*×*size* pixels and return PNG bytes.

        FontForge exports a PNG file for the glyph and this method reads
        it back as raw bytes.

        Args:
            size: Output image width and height in pixels.  Defaults to 256.

        Returns:
            Raw PNG bytes.

        Raises:
            RuntimeError: If the export fails.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = os.path.join(tmpdir, f"{self.name}.png")
            self._glyph.export(png_path, size)
            with open(png_path, "rb") as fh:
                return fh.read()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def copy_from(self, other: "Glyph") -> "Glyph":
        """Replace this glyph's contours with those copied from *other*.

        Args:
            other: Source :class:`Glyph` to copy from.

        Returns:
            *self* for method chaining.
        """
        self._glyph.clear()
        pen = self._glyph.glyphPen()
        other._glyph.draw(pen)
        return self

    @property
    def _ff(self) -> object:
        """Direct access to the underlying fontforge glyph object (internal use)."""
        return self._glyph

    def __repr__(self) -> str:
        if self.unicode >= 0:
            return f"<Glyph '{self.name}' U+{self.unicode:04X}>"
        return f"<Glyph '{self.name}'>"
