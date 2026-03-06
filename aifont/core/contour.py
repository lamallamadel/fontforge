"""Bézier curve and path manipulation utilities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph

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
