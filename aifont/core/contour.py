"""
aifont.core.contour — Bézier curve and path manipulation utilities.

Wraps fontforge's contour / point APIs and exposes higher-level helpers for:
- Simplifying paths (reducing unnecessary points).
- Removing overlapping contours.
- Correcting contour winding direction.
- Applying affine transformations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph


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
