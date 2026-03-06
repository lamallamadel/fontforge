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
aifont.core.glyph — Glyph wrapper around ``fontforge.glyph``.

Provides a clean Python API for reading and writing individual glyph
properties (width, bearings, unicode mapping, contour access).

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  This module wraps fontforge glyph
objects; it does not subclass them.
"""Glyph wrapper around fontforge.glyph."""

from __future__ import annotations

from typing import Any, Optional


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
    Example:
        >>> font = Font.open("MyFont.otf")
        >>> g = font.glyphs[0]
        >>> g.set_width(600)
    """

    def __init__(self, _ff_glyph: Any) -> None:
        self._ff = _ff_glyph
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
- Get and set advance width, bearings, and Unicode mapping.
- Contour manipulation (add, remove, simplify).
- Geometric transformations (scale, rotate, move, skew).
- Typographic operations (stroke, remove_overlap, correct_direction).
- Export to SVG / PNG for previewing.
- Get and set advance width and side-bearings.
- Read / write Unicode mapping.

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
        """Glyph name (e.g. ``'A'``, ``'uni0041'``)."""
        return str(self._ff.glyphname)

    @property
    def unicode(self) -> int:
        """Unicode code point, or -1 if unmapped."""
        return int(self._ff.unicode)
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
        """Unicode code point, or ``-1`` if unmapped."""
        return self._glyph.unicode

    @unicode.setter
    def unicode(self, value: int) -> None:
        """Set the Unicode code point.

        Args:
            value: Unicode code point (or -1 to unmap).
        """
        self._glyph.unicode = value
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
        return self._glyph.left_side_bearing

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        """Set the left side-bearing.

        Args:
            value: New left side-bearing in font units.
        """
        self._glyph.left_side_bearing = int(value)
        return int(self._ff.left_side_bearing)  # type: ignore[attr-defined]

    @left_side_bearing.setter
    def left_side_bearing(self, value: int) -> None:
        self._ff.left_side_bearing = value  # type: ignore[attr-defined]

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
        """Advance width in font units."""
        return int(self._ff.width)

    @property
    def left_side_bearing(self) -> int:
        """Left side bearing in font units."""
        return int(self._ff.left_side_bearing)

    @property
    def right_side_bearing(self) -> int:
        """Right side bearing in font units."""
        return int(self._ff.right_side_bearing)

    @property
    def contours(self) -> list:
        """Return the glyph's foreground layer contours."""
        return list(self._ff.foreground)
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
        """Set the advance width.

        Args:
            width: New advance width in font units.
        """
        self._ff.width = width

    def set_left_side_bearing(self, value: int) -> None:
        """Set the left side bearing."""
        self._ff.left_side_bearing = value

    def set_right_side_bearing(self, value: int) -> None:
        """Set the right side bearing."""
        self._ff.right_side_bearing = value

    def copy_from(self, other: "Glyph") -> None:
        """Copy contours and metrics from another glyph.

        Args:
            other: Source glyph to copy from.
        """
        self._ff.clear()
        self._ff.importOutlines(other._ff)

    def __repr__(self) -> str:
        return f"<Glyph name={self.name!r} unicode={self.unicode}>"
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
        return self

    @property
    def _ff(self) -> object:

    @property
    def _ff(self):
        """Direct access to the underlying fontforge glyph object (internal use)."""
        return self._glyph

    def __repr__(self) -> str:
        if self.unicode >= 0:
            return f"<Glyph '{self.name}' U+{self.unicode:04X}>"
        return f"<Glyph '{self.name}'>"
        return f"<Glyph '{self.name}' U+{self.unicode:04X}>" if self.unicode >= 0 else f"<Glyph '{self.name}'>"
