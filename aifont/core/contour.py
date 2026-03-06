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
