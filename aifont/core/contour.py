"""
aifont.core.contour — Bézier curve and path manipulation utilities.

This module provides high-level operations on glyph outlines (contours /
paths) by delegating to FontForge's contour/point APIs.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from .glyph import Glyph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def simplify(glyph: "Glyph", threshold: float = 1.0) -> None:
    """Simplify the glyph's outline by removing redundant on-curve points.

    Delegates to FontForge's ``simplify()`` with the given error
    *threshold*.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    threshold : float, optional
        Maximum deviation (in font units) allowed when removing points.
        Smaller values preserve more detail; larger values simplify more
        aggressively.  Default is ``1.0``.

    Examples
    --------
    ::

        from aifont.core.font import Font
        from aifont.core.contour import simplify

        font = Font.open("MyFont.otf")
        simplify(font["A"], threshold=2.0)
    """
    try:
        glyph.ff_glyph.simplify(threshold)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def remove_overlap(glyph: "Glyph") -> None:
    """Remove overlapping contours in *glyph*.

    Delegates to FontForge's ``removeOverlap()`` method.  After calling
    this function the glyph will contain a single, non-self-intersecting
    outline.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    """
    try:
        glyph.ff_glyph.removeOverlap()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def transform(
    glyph: "Glyph",
    matrix: Tuple[float, float, float, float, float, float],
) -> None:
    """Apply an affine transformation matrix to *glyph*.

    The *matrix* is a 6-element tuple representing the standard 2-D
    affine transformation::

        | a  b  0 |
        | c  d  0 |
        | e  f  1 |

    expressed as ``(a, b, c, d, e, f)``, identical to the PostScript /
    PDF matrix convention used by FontForge's ``psMat`` module.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    matrix : tuple of 6 float
        Affine transformation matrix ``(a, b, c, d, e, f)``.

    Examples
    --------
    Scale a glyph to 50 % using :mod:`psMat`::

        import psMat
        from aifont.core.contour import transform

        transform(glyph, psMat.scale(0.5))
    """
    if len(matrix) != 6:
        raise ValueError(f"matrix must have 6 elements, got {len(matrix)}")
    try:
        glyph.ff_glyph.transform(matrix)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def reverse_direction(glyph: "Glyph") -> None:
    """Reverse the winding direction of all contours in *glyph*.

    Delegates to FontForge's ``correctDirection()`` in reverse mode.
    This is useful for fixing path direction problems.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    """
    try:
        glyph.ff_glyph.reverseDirection()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def correct_direction(glyph: "Glyph") -> None:
    """Set contour winding directions to the PostScript/TrueType convention.

    Outer contours are made counter-clockwise, inner contours
    (holes) are made clockwise, following the PostScript convention.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    """
    try:
        glyph.ff_glyph.correctDirection()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def add_extrema(glyph: "Glyph") -> None:
    """Add on-curve points at the extrema of every spline.

    This is required for valid TrueType/OpenType outlines and is
    delegated to FontForge's ``addExtrema()`` method.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    """
    try:
        glyph.ff_glyph.addExtrema()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def round_to_int(glyph: "Glyph") -> None:
    """Round all point coordinates to integer values.

    Delegates to FontForge's ``round()`` method.  Useful for
    cleaning up outlines before export.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    """
    try:
        glyph.ff_glyph.round()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def auto_hint(glyph: "Glyph") -> None:
    """Automatically generate PostScript hints for *glyph*.

    Delegates to FontForge's ``autoHint()`` method.

    Parameters
    ----------
    glyph : Glyph
        The target :class:`~aifont.core.glyph.Glyph`.
    """
    try:
        glyph.ff_glyph.autoHint()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
