"""
aifont.core.contour — Bézier contour and path manipulation utilities.

Provides functions to transform, simplify, and reshape glyph contours.
All operations wrap ``fontforge`` glyph methods; none call fontforge
directly except through the passed ``Glyph`` wrapper objects.

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  Use ``glyph.raw`` to access the
underlying ``fontforge.glyph`` when fontforge-specific methods are needed.

Key functions
-------------
transform(glyph, matrix)
    Apply a 6-element affine transformation matrix.
remove_overlap(glyph)
    Remove overlapping path regions.
simplify(glyph, threshold)
    Reduce unnecessary control points.
apply_stroke(glyph, width, join_type)
    Expand contours by a stroke width (boldification).
apply_slant(glyph, angle_deg, x_origin)
    Shear the glyph horizontally to produce an italic effect.
"""Bézier curve and path manipulation utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence
from collections.abc import Sequence
"""
aifont.core.contour — Bézier curve and path manipulation utilities.

Wraps fontforge's contour / point APIs and exposes higher-level helpers for:
- Simplifying paths (reducing unnecessary points).
- Removing overlapping contours.
- Correcting contour winding direction.
- Applying affine transformations.
"""aifont.core.contour — Bézier curve and vector path manipulation.

This module wraps FontForge's contour/point Python APIs to provide a clean,
Pythonic interface for creating and manipulating Bézier curves and paths.

All operations delegate to ``fontforge`` objects internally. FontForge source
code is never modified.

Example::

    import fontforge
    from aifont.core.contour import Contour, simplify, to_svg_path

    font = fontforge.font()
    glyph = font.createChar(0x41, "A")

    # Build a simple triangle contour
    c = Contour.from_points([(0, 0), (500, 700), (1000, 0)], closed=True)
    c.apply_to_glyph(glyph)

    svg = to_svg_path(glyph)
    print(svg)

    font.close()
"""

from __future__ import annotations

import math
from typing import Tuple

from aifont.core.glyph import Glyph

# Affine matrix type: (xx, xy, yx, yy, dx, dy)
Matrix = Tuple[float, float, float, float, float, float]

# Default join type used when expanding stroke outlines.
_DEFAULT_JOIN = "miter"


def transform(glyph: Glyph, matrix: Matrix) -> None:
    """Apply a 6-element affine transformation matrix to *glyph*.

    The matrix is in PostScript / fontforge order:
    ``(xx, xy, yx, yy, dx, dy)`` where the transformation is::

        x' = xx*x + yx*y + dx
        y' = xy*x + yy*y + dy

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to transform in-place.
    matrix:
        A 6-tuple ``(xx, xy, yx, yy, dx, dy)``.

    Examples
    --------
    Scale glyph to 80 % of its original size::

        transform(glyph, (0.8, 0, 0, 0.8, 0, 0))
    """
    glyph.raw.transform(matrix)


def remove_overlap(glyph: Glyph) -> None:
    """Remove overlapping contour regions from *glyph*.

    This is equivalent to a boolean union of all subpaths and is required
    before generating final font files to avoid rendering artifacts.

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to process in-place.
    """
    glyph.raw.removeOverlap()


def simplify(glyph: Glyph, threshold: float = 1.0) -> None:
    """Reduce unnecessary control points in *glyph*.

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to process in-place.
    threshold:
        Maximum deviation allowed when collapsing points (in font units).
        Higher values produce simpler paths with less accuracy.
    """
    glyph.raw.simplify(threshold)


def apply_stroke(
    glyph: Glyph,
    width: float,
    join_type: str = _DEFAULT_JOIN,
) -> None:
    """Expand the glyph outline by *width* font units (boldification).

    This calls fontforge's ``changeWeight`` method which expands stroke
    weight without distorting letterform proportions.

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to process in-place.
    width:
        Stroke expansion amount in font units.  Positive values make the
        glyph heavier (bold); negative values make it lighter.
    join_type:
        Stroke join style.  One of ``"miter"``, ``"round"``, ``"bevel"``.
        Currently passed as a hint; fontforge may use its own default.

    Notes
    -----
    After calling this function the glyph's advance width is *not*
    automatically updated.  Call ``glyph.set_width(…)`` if needed.
    """
    try:
        glyph.raw.changeWeight(width, join_type)
    except TypeError:
        # Some fontforge versions only accept width
        glyph.raw.changeWeight(width)


def apply_slant(
    glyph: Glyph,
    angle_deg: float,
    x_origin: float = 0.0,
) -> None:
    """Shear *glyph* horizontally to simulate an italic effect.

    The glyph is slanted by *angle_deg* degrees around the vertical axis
    at *x_origin*.  A positive angle tilts the tops of strokes to the
    right (conventional italic direction).

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to process in-place.
    angle_deg:
        Slant angle in degrees.  Typical italic values are 10–14°.
    x_origin:
        Horizontal position (in font units) used as the pivot for the
        shear.  Defaults to 0.

    Notes
    -----
    The shear matrix for an italic slant is::

        | 1   tan(θ)  0 |
        | 0     1     0 |
        | dx    0     1 |

    In fontforge's ``(xx, xy, yx, yy, dx, dy)`` convention this becomes
    ``(1, 0, tan(θ), 1, 0, 0)`` (no translation when x_origin=0).
    """
    shear = math.tan(math.radians(angle_deg))
    # Translate so x_origin becomes the pivot, shear, translate back
    matrix: Matrix = (1.0, 0.0, shear, 1.0, -x_origin * shear, 0.0)
    transform(glyph, matrix)


def scale(glyph: Glyph, sx: float, sy: float) -> None:
    """Scale *glyph* by independent horizontal and vertical factors.

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to process in-place.
    sx:
        Horizontal scale factor (1.0 = no change).
    sy:
        Vertical scale factor (1.0 = no change).
    """
    transform(glyph, (sx, 0.0, 0.0, sy, 0.0, 0.0))


def translate(glyph: Glyph, dx: float, dy: float) -> None:
    """Translate *glyph* by *(dx, dy)* font units.

    Parameters
    ----------
    glyph:
        The :class:`~aifont.core.glyph.Glyph` to process in-place.
    dx:
        Horizontal offset in font units.
    dy:
        Vertical offset in font units.
    """
    transform(glyph, (1.0, 0.0, 0.0, 1.0, dx, dy))
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph


def simplify(glyph: "Glyph", threshold: float = 1.0) -> None:
    """Simplify a glyph's contours by removing redundant points.

    Args:
        glyph:     The glyph to simplify.
        threshold: Maximum distance for point removal (default 1.0).

    Raises:
        RuntimeError: If the glyph is not properly initialized.
    """
    if glyph._ff is None:
        raise RuntimeError("Glyph is not properly initialized.")
# 2-D transformation matrix type: ((xx, xy), (yx, yy)) or a flat 6-element tuple.
Matrix = Sequence[float]


def simplify(glyph: Glyph, threshold: float = 1.0) -> None:
    """Simplify the paths of *glyph* by removing redundant points.

    Delegates to :meth:`fontforge.glyph.simplify` with the given
    *threshold* (in font units).
    """
    glyph._raw.simplify(threshold)


def remove_overlap(glyph: Glyph) -> None:
    """Remove overlapping contours from *glyph*.

    Delegates to :meth:`fontforge.glyph.removeOverlap`.
    """
    glyph._raw.removeOverlap()


def transform(glyph: Glyph, matrix: Matrix) -> None:
    """Apply a 2-D affine *matrix* to all contours in *glyph*.

    *matrix* must be a 6-element sequence ``[xx, xy, yx, yy, dx, dy]``
    compatible with fontforge's :meth:`~fontforge.glyph.transform`.

    Example — scale uniformly by 50 %::

        from aifont.core.contour import transform
        transform(glyph, [0.5, 0, 0, 0.5, 0, 0])
    """
    if len(matrix) != 6:
        raise ValueError(f"transform matrix must have 6 elements, got {len(matrix)}")
    glyph._raw.transform(tuple(matrix))


def reverse_direction(glyph: Glyph) -> None:
    """Reverse the winding direction of all contours in *glyph*.

    Useful for converting between PostScript (counter-clockwise outer) and
    TrueType (clockwise outer) conventions.
    """
    glyph._raw.reverseDirection()

def simplify(glyph: "Glyph", threshold: float = 1.0) -> None:
    """Simplify the outlines of *glyph* by removing near-collinear points.

    Uses fontforge's built-in simplify operation.  The *threshold* controls
    how aggressively points are removed; higher values remove more points.

    Args:
        glyph:     Target glyph whose outlines will be simplified.
        threshold: Maximum distance (in font units) a point may move from
                   the original outline.  Defaults to ``1.0``.
    """
    glyph._ff.simplify(threshold, ("mergelines",))


def remove_overlap(glyph: "Glyph") -> None:
    """Remove overlapping paths in a glyph.

    Args:
        glyph: The glyph to process.

    Raises:
        RuntimeError: If the glyph is not properly initialized.
    """
    if glyph._ff is None:
        raise RuntimeError("Glyph is not properly initialized.")
    glyph._ff.removeOverlap()


def transform(glyph: "Glyph", matrix: Sequence[float]) -> None:
    """Apply an affine transformation matrix to a glyph.

    Args:
        glyph:  The glyph to transform.
        matrix: A 6-element affine matrix ``[xx, xy, yx, yy, dx, dy]``.

    Example:
        Scale by 50%::

            transform(glyph, [0.5, 0, 0, 0.5, 0, 0])
    """
    if len(matrix) != 6:
        raise ValueError("Matrix must have exactly 6 elements [xx, xy, yx, yy, dx, dy].")
    if glyph._ff is None:
        raise RuntimeError("Glyph is not properly initialized.")
    glyph._ff.transform(tuple(matrix))


def reverse_direction(glyph: "Glyph") -> None:
    """Reverse the winding direction of all contours in a glyph.

    Args:
        glyph: The glyph to process.

    Raises:
        RuntimeError: If the glyph is not properly initialized.
    """
    if glyph._ff is None:
        raise RuntimeError("Glyph is not properly initialized.")
    glyph._ff.reverseDirection()
    """Remove overlapping path regions from *glyph*.

    Applies fontforge's ``removeOverlap`` to merge intersecting contours into
    a single, non-self-intersecting outline.

    Args:
        glyph: Target glyph.
    """
    glyph._ff.removeOverlap()


def correct_directions(glyph: "Glyph") -> None:
    """Correct the winding direction of *glyph*'s contours.

    Outer contours should be counter-clockwise and inner (counter) contours
    clockwise (PostScript / OTF convention).  TrueType uses the opposite
    winding.  FontForge's ``correctDirection`` enforces the correct convention
    automatically based on the font's target format.

    Args:
        glyph: Target glyph.
    """
    glyph._ff.correctDirection()


def transform(glyph: "Glyph", matrix: tuple) -> None:
    """Apply an affine transformation matrix to *glyph*.

    Args:
        glyph:  Target glyph.
        matrix: A 6-element tuple ``(xx, xy, yx, yy, dx, dy)`` representing
                the 2-D affine transform, compatible with fontforge's
                ``transform()`` method.
    """
    if len(matrix) != 6:
        raise ValueError("matrix must be a 6-element tuple (xx, xy, yx, yy, dx, dy)")
    glyph._ff.transform(matrix)
import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

# FontForge is an optional runtime dependency so that the module can be
# imported for type-checking purposes even when FontForge is not installed.
try:
    import fontforge as _ff
except ImportError:  # pragma: no cover
    _ff = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ContourPoint:
    """A single point on a contour.

    Attributes:
        x: Horizontal coordinate.
        y: Vertical coordinate.
        on_curve: ``True`` if the point lies on the curve (anchor point),
            ``False`` if it is a Bézier control handle (off-curve).
        name: Optional point name (used for hinting or identification).
    """

    x: float
    y: float
    on_curve: bool = True
    name: Optional[str] = None

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_ff_point(cls, pt: object) -> "ContourPoint":
        """Create a :class:`ContourPoint` from a ``fontforge.point`` object."""
        return cls(
            x=float(pt.x),  # type: ignore[union-attr]
            y=float(pt.y),  # type: ignore[union-attr]
            on_curve=bool(pt.on_curve),  # type: ignore[union-attr]
            name=getattr(pt, "name", None) or None,
        )

    def to_ff_point(self) -> object:
        """Convert to a ``fontforge.point`` object."""
        if _ff is None:
            raise RuntimeError("fontforge is not installed")
        pt = _ff.point(self.x, self.y, self.on_curve)
        if self.name:
            pt.name = self.name
        return pt

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def distance_to(self, other: "ContourPoint") -> float:
        """Euclidean distance between *self* and *other*."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def __iter__(self):  # allow tuple-unpacking: x, y = point
        yield self.x
        yield self.y

    def __repr__(self) -> str:  # pragma: no cover
        kind = "on" if self.on_curve else "off"
        return f"ContourPoint({self.x}, {self.y}, {kind})"


# ---------------------------------------------------------------------------
# Contour
# ---------------------------------------------------------------------------


@dataclass
class Contour:
    """A sequence of :class:`ContourPoint` objects representing a single path.

    A :class:`Contour` can be open (a line/curve that does not close on
    itself) or closed (a filled shape).

    Attributes:
        points: Ordered list of points.
        closed: Whether the path is closed.
        is_quadratic: ``True`` for TrueType (quadratic) curves, ``False`` for
            PostScript (cubic) curves.
    """

    points: List[ContourPoint] = field(default_factory=list)
    closed: bool = False
    is_quadratic: bool = False

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_ff_contour(cls, ff_contour: object) -> "Contour":
        """Build a :class:`Contour` from a ``fontforge.contour`` object."""
        points = [ContourPoint.from_ff_point(p) for p in ff_contour]  # type: ignore[union-attr]
        return cls(
            points=points,
            closed=bool(ff_contour.closed),  # type: ignore[union-attr]
            is_quadratic=bool(ff_contour.is_quadratic),  # type: ignore[union-attr]
        )

    @classmethod
    def from_points(
        cls,
        coords: Iterable[Tuple[float, float]],
        *,
        closed: bool = False,
        is_quadratic: bool = False,
    ) -> "Contour":
        """Create a :class:`Contour` from an iterable of ``(x, y)`` tuples.

        All points are treated as on-curve anchor points.
        """
        points = [ContourPoint(x=x, y=y, on_curve=True) for x, y in coords]
        return cls(points=points, closed=closed, is_quadratic=is_quadratic)

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def to_ff_contour(self) -> object:
        """Convert to a ``fontforge.contour`` object."""
        if _ff is None:
            raise RuntimeError("fontforge is not installed")
        c = _ff.contour(self.is_quadratic)
        c.closed = self.closed
        for p in self.points:
            c += p.to_ff_point()
        return c

    def apply_to_glyph(self, glyph: object, layer: str = "Fore") -> None:
        """Append this contour to *glyph*'s foreground (or given) layer.

        Args:
            glyph: A ``fontforge.glyph`` object.
            layer: Layer name to write to (default ``"Fore"``).
        """
        pen = glyph.glyphPen(replace=False)  # type: ignore[union-attr]
        _write_contour_to_pen(self, pen)
        del pen

    # ------------------------------------------------------------------
    # Open / close helpers
    # ------------------------------------------------------------------

    def close(self) -> "Contour":
        """Return a closed copy of this contour."""
        return Contour(points=list(self.points), closed=True, is_quadratic=self.is_quadratic)

    def open(self) -> "Contour":
        """Return an open copy of this contour."""
        return Contour(points=list(self.points), closed=False, is_quadratic=self.is_quadratic)

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def reverse(self) -> "Contour":
        """Return a copy of this contour with point order reversed.

        Reversing a closed contour changes its winding direction (clockwise ↔
        counter-clockwise), which matters for fill rules in rendered fonts.
        """
        return Contour(
            points=list(reversed(self.points)),
            closed=self.closed,
            is_quadratic=self.is_quadratic,
        )

    def transform(self, matrix: Sequence[float]) -> "Contour":
        """Apply a 2-D affine transform and return the resulting contour.

        Args:
            matrix: A 6-element sequence ``[xx, xy, yx, yy, dx, dy]``
                representing a 2×3 affine matrix in the same order used by
                ``fontforge.glyph.transform()``.

        Returns:
            A new :class:`Contour` with transformed coordinates.
        """
        xx, xy, yx, yy, dx, dy = matrix
        new_points = []
        for p in self.points:
            nx = xx * p.x + yx * p.y + dx
            ny = xy * p.x + yy * p.y + dy
            new_points.append(ContourPoint(x=nx, y=ny, on_curve=p.on_curve, name=p.name))
        return Contour(points=new_points, closed=self.closed, is_quadratic=self.is_quadratic)

    def to_svg_path_data(self) -> str:
        """Return an SVG ``d`` attribute string for this contour.

        Only cubic (PostScript) contours are fully supported.  Quadratic
        contours are treated as cubic for SVG output purposes.

        Returns:
            A string suitable for use as the ``d`` attribute of an SVG
            ``<path>`` element.
        """
        return _contour_to_svg_d(self)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.points)

    def __getitem__(self, index):
        return self.points[index]

    def __iter__(self):
        return iter(self.points)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Contour(points={len(self.points)}, closed={self.closed}, "
            f"is_quadratic={self.is_quadratic})"
        )


# ---------------------------------------------------------------------------
# Glyph-level operations
# ---------------------------------------------------------------------------


def simplify(glyph: object, threshold: float = 1.0) -> None:
    """Simplify the contours of *glyph* by reducing the number of nodes.

    Delegates to ``fontforge.glyph.simplify()``.

    Args:
        glyph: A ``fontforge.glyph`` object.
        threshold: The maximum distance by which simplified curves may deviate
            from the original path.  Larger values produce more aggressive
            simplification.  Defaults to ``1.0`` em unit.
    """
    glyph.simplify(threshold)  # type: ignore[union-attr]


def smooth_transitions(glyph: object) -> None:
    """Automatically smooth the curve transitions of *glyph*.

    Calls ``fontforge.glyph.addExtrema()`` followed by
    ``fontforge.glyph.roundToInt()`` to ensure extrema points are added and
    coordinates are snapped to integer values, producing smooth transitions
    between curve segments.

    Args:
        glyph: A ``fontforge.glyph`` object.
    """
    glyph.addExtrema()  # type: ignore[union-attr]
    glyph.roundToInt()  # type: ignore[union-attr]


def reverse_direction(glyph: object) -> None:
    """Reverse the winding direction of all contours in *glyph*.

    Delegates to ``fontforge.glyph.reverseDirection()``.

    Args:
        glyph: A ``fontforge.glyph`` object.
    """
    glyph.reverseDirection()  # type: ignore[union-attr]


def remove_overlap(glyph: object) -> None:
    """Remove overlapping paths in *glyph*.

    Delegates to ``fontforge.glyph.removeOverlap()``.

    Args:
        glyph: A ``fontforge.glyph`` object.
    """
    glyph.removeOverlap()  # type: ignore[union-attr]


def transform(glyph: object, matrix: Sequence[float]) -> None:
    """Apply an affine transform to all contours in *glyph*.

    Args:
        glyph: A ``fontforge.glyph`` object.
        matrix: A 6-element sequence ``[xx, xy, yx, yy, dx, dy]`` — the same
            format accepted by ``fontforge.glyph.transform()``.
    """
    glyph.transform(tuple(matrix))  # type: ignore[union-attr]


def to_svg_path(glyph: object, layer: str = "Fore") -> str:
    """Convert all contours in *glyph* to an SVG ``<path d="…">`` string.

    Args:
        glyph: A ``fontforge.glyph`` object.
        layer: Layer to read contours from (default ``"Fore"``).

    Returns:
        A complete SVG path string combining all contours.
    """
    ff_layer = getattr(glyph, layer.lower(), None) or getattr(glyph, layer, None)
    if ff_layer is None:
        raise ValueError(f"Layer '{layer}' not found on glyph")
    parts: List[str] = []
    for ff_contour in ff_layer:
        c = Contour.from_ff_contour(ff_contour)
        parts.append(c.to_svg_path_data())
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_contour_to_pen(contour: Contour, pen: object) -> None:
    """Write *contour* to a FontForge glyph pen.

    This function converts a :class:`Contour` into a series of pen calls
    (``moveTo``, ``lineTo``, ``curveTo``, ``closePath`` / ``endPath``).

    Args:
        contour: The contour to write.
        pen: A ``fontforge.glyphPen`` (or any object implementing the
            same interface).
    """
    if not contour.points:
        return

    # Separate on-curve points from off-curve handles so that we can emit
    # the correct pen calls.
    points = contour.points

    # Find the first on-curve point and re-order the list so it comes first
    # (required by the pen protocol).
    start_idx = 0
    for i, p in enumerate(points):
        if p.on_curve:
            start_idx = i
            break

    if contour.closed:
        ordered = points[start_idx:] + points[:start_idx]
    else:
        ordered = list(points)

    # Emit moveTo for the starting on-curve point.
    first = ordered[0]
    pen.moveTo((first.x, first.y))  # type: ignore[union-attr]

    i = 1
    while i < len(ordered):
        p = ordered[i]
        if p.on_curve:
            pen.lineTo((p.x, p.y))  # type: ignore[union-attr]
            i += 1
        else:
            # Collect consecutive off-curve control points.
            handles: List[Tuple[float, float]] = []
            while i < len(ordered) and not ordered[i].on_curve:
                handles.append((ordered[i].x, ordered[i].y))
                i += 1
            # The next on-curve point (could wrap around for closed path).
            if i < len(ordered):
                end = (ordered[i].x, ordered[i].y)
                i += 1
            else:
                end = (first.x, first.y)
            if len(handles) == 1:
                # Quadratic / single handle — emit as cubicTo with implicit
                # conversion (duplicating the handle) for compatibility.
                hx, hy = handles[0]
                ex, ey = end
                pen.curveTo(  # type: ignore[union-attr]
                    (hx, hy),
                    (hx, hy),
                    (ex, ey),
                )
            else:
                pen.curveTo(*handles, end)  # type: ignore[union-attr]

    if contour.closed:
        pen.closePath()  # type: ignore[union-attr]
    else:
        pen.endPath()  # type: ignore[union-attr]


def _contour_to_svg_d(contour: Contour) -> str:
    """Return an SVG ``d`` string for a single :class:`Contour`.

    Implements a minimal subset of the SVG path command set:

    * ``M`` — move-to (start of contour)
    * ``L`` — line-to (on-curve to on-curve with no handles)
    * ``C`` — cubic Bézier curve (two control handles + end-point)
    * ``Q`` — quadratic Bézier curve (one control handle + end-point)
    * ``Z`` — close path
    """
    if not contour.points:
        return ""

    points = contour.points
    cmds: List[str] = []

    # Find first on-curve point.
    start_idx = 0
    for i, p in enumerate(points):
        if p.on_curve:
            start_idx = i
            break

    if contour.closed:
        ordered = points[start_idx:] + points[:start_idx]
    else:
        ordered = list(points)

    def _fmt(v: float) -> str:
        # Emit integers without decimals for tidiness.
        if v == int(v):
            return str(int(v))
        return f"{v:.4g}"

    def _coord(x: float, y: float) -> str:
        return f"{_fmt(x)},{_fmt(y)}"

    first = ordered[0]
    cmds.append(f"M {_coord(first.x, first.y)}")

    i = 1
    while i < len(ordered):
        p = ordered[i]
        if p.on_curve:
            cmds.append(f"L {_coord(p.x, p.y)}")
            i += 1
        else:
            handles: List[Tuple[float, float]] = []
            while i < len(ordered) and not ordered[i].on_curve:
                handles.append((ordered[i].x, ordered[i].y))
                i += 1
            if i < len(ordered):
                end_pt = ordered[i]
                i += 1
            else:
                end_pt = first
            if len(handles) == 1:
                hx, hy = handles[0]
                cmds.append(f"Q {_coord(hx, hy)} {_coord(end_pt.x, end_pt.y)}")
            else:
                # Emit as one or more cubic segments.
                h_coords = " ".join(_coord(hx, hy) for hx, hy in handles[-2:])
                cmds.append(f"C {h_coords} {_coord(end_pt.x, end_pt.y)}")

    if contour.closed:
        cmds.append("Z")

    return " ".join(cmds)
