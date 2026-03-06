"""
aifont.core.contour — Bézier curve and path manipulation.

Wraps fontforge's contour/point APIs to provide higher-level operations:
- simplify paths
- remove overlapping contours
- reverse/correct path directions
- scale/transform contours

FontForge source code is never modified.
"""

from __future__ import annotations

from typing import Sequence, Tuple


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# A 2×3 affine transformation matrix as a flat 6-tuple:
# [a, b, c, d, e, f]  =>  | a  b  0 |
#                          | c  d  0 |
#                          | e  f  1 |
Matrix = Tuple[float, float, float, float, float, float]


def _get_ff_glyph(glyph: object) -> object:
    """Return the raw fontforge glyph from a wrapper or raw object."""
    if hasattr(glyph, "_glyph"):
        return glyph._glyph  # type: ignore[attr-defined]
    return glyph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def simplify(glyph: object, threshold: float = 1.0) -> None:
    """Simplify the outline of *glyph* by removing redundant points.

    Args:
        glyph:     A :class:`~aifont.core.glyph.Glyph` wrapper or a raw
                   ``fontforge.glyph``.
        threshold: Simplification tolerance in font units.  Larger values
                   produce fewer points but less accurate curves.
    """
    ff_g = _get_ff_glyph(glyph)
    ff_g.simplify(threshold)


def remove_overlap(glyph: object) -> None:
    """Remove overlapping contours from *glyph*.

    Calls FontForge's ``removeOverlap()`` method which performs a Boolean
    union of all contours.

    Args:
        glyph: A :class:`~aifont.core.glyph.Glyph` wrapper or a raw
               ``fontforge.glyph``.
    """
    ff_g = _get_ff_glyph(glyph)
    ff_g.removeOverlap()


def correct_directions(glyph: object) -> None:
    """Correct contour winding directions.

    Outer contours will be set to counter-clockwise (PostScript convention)
    and inner contours (holes) to clockwise.

    Args:
        glyph: A :class:`~aifont.core.glyph.Glyph` wrapper or a raw
               ``fontforge.glyph``.
    """
    ff_g = _get_ff_glyph(glyph)
    ff_g.correctDirection()


def transform(glyph: object, matrix: Matrix) -> None:
    """Apply an affine transformation matrix to all contours in *glyph*.

    Args:
        glyph:  A :class:`~aifont.core.glyph.Glyph` wrapper or a raw
                ``fontforge.glyph``.
        matrix: A 6-tuple ``(xx, xy, yx, yy, dx, dy)`` representing the
                2-D affine transform (same convention as
                :mod:`psMat`).

    Example::

        from aifont.core.contour import transform
        # Scale the glyph to 80 % of its original size:
        transform(glyph, (0.8, 0, 0, 0.8, 0, 0))
    """
    ff_g = _get_ff_glyph(glyph)
    ff_g.transform(matrix)


def round_to_int(glyph: object) -> None:
    """Round all point coordinates to integer values.

    Args:
        glyph: A :class:`~aifont.core.glyph.Glyph` wrapper or a raw
               ``fontforge.glyph``.
    """
    ff_g = _get_ff_glyph(glyph)
    ff_g.round()


def add_extrema(glyph: object) -> None:
    """Add extremal points to curves (required for valid OTF outlines).

    Args:
        glyph: A :class:`~aifont.core.glyph.Glyph` wrapper or a raw
               ``fontforge.glyph``.
    """
    ff_g = _get_ff_glyph(glyph)
    ff_g.addExtrema()
