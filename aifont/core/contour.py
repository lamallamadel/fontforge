"""Bézier curve and path manipulation utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph


def simplify(glyph: "Glyph", threshold: float = 1.0) -> None:
    """Simplify a glyph's contours by removing redundant points.

    Args:
        glyph:     The glyph to simplify.
        threshold: Maximum distance for point removal (default 1.0).
    """
    glyph._ff.simplify(threshold, ("mergelines",))


def remove_overlap(glyph: "Glyph") -> None:
    """Remove overlapping paths in a glyph.

    Args:
        glyph: The glyph to process.
    """
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
    glyph._ff.transform(tuple(matrix))


def reverse_direction(glyph: "Glyph") -> None:
    """Reverse the winding direction of all contours in a glyph.

    Args:
        glyph: The glyph to process.
    """
    glyph._ff.reverseDirection()
