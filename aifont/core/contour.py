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
