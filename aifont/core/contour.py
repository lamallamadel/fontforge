"""Bézier contour and path manipulation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, Tuple

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph

# A 2-D affine transformation matrix as a flat 6-tuple
Matrix = Tuple[float, float, float, float, float, float]


def simplify(glyph: "Glyph", threshold: float = 1.0) -> None:
    """Simplify the contours of *glyph* by removing redundant points.

    Delegates to ``fontforge.glyph.simplify()``.
    """
    ff = glyph._ff
    if hasattr(ff, "simplify"):
        try:
            ff.simplify(threshold, ("removeSingletonPoints",))  # type: ignore[union-attr]
        except (TypeError, Exception):
            try:
                ff.simplify()  # type: ignore[union-attr]
            except (AttributeError, Exception):
                pass


def remove_overlap(glyph: "Glyph") -> None:
    """Remove overlapping contour regions from *glyph*.

    Delegates to ``fontforge.glyph.removeOverlap()``.
    """
    ff = glyph._ff
    if hasattr(ff, "removeOverlap"):
        try:
            ff.removeOverlap()  # type: ignore[union-attr]
        except (AttributeError, Exception):
            pass


def transform(glyph: "Glyph", matrix: Matrix) -> None:
    """Apply an affine *matrix* to all contours of *glyph*.

    *matrix* must be a 6-element tuple ``(xx, xy, yx, yy, dx, dy)``
    compatible with fontforge's ``psMat`` format.
    """
    if len(matrix) != 6:
        raise ValueError(f"matrix must have 6 elements, got {len(matrix)}")
    ff = glyph._ff
    if hasattr(ff, "transform"):
        try:
            ff.transform(matrix)  # type: ignore[union-attr]
        except (AttributeError, Exception):
            pass
