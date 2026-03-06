"""aifont.core.contour — Bézier curve and path manipulation utilities.

Provides functions to transform, simplify, and reshape glyph contours.
All operations wrap ``fontforge`` glyph methods via the :class:`Glyph`
wrapper object.

FontForge source code is never modified.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Sequence, Tuple

if TYPE_CHECKING:
    from aifont.core.glyph import Glyph

# A 2-D affine transformation matrix as a flat 6-tuple:
# (xx, xy, yx, yy, dx, dy)
Matrix = Tuple[float, float, float, float, float, float]


# ---------------------------------------------------------------------------
# Core transformation / cleanup functions
# ---------------------------------------------------------------------------


def simplify(glyph: "Glyph", threshold: float = 1.0) -> None:
    """Simplify the contours of *glyph* by removing redundant points.

    Args:
        glyph:     The target glyph.
        threshold: Maximum deviation allowed when removing points (font units).
    """
    ff = glyph._ff
    if hasattr(ff, "simplify"):
        try:
            ff.simplify(threshold)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def remove_overlap(glyph: "Glyph") -> None:
    """Remove overlapping contour regions from *glyph*.

    Delegates to ``fontforge.glyph.removeOverlap()``.
    """
    ff = glyph._ff
    if hasattr(ff, "removeOverlap"):
        try:
            ff.removeOverlap()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def transform(
    glyph: "Glyph",
    matrix: Sequence[float],
) -> None:
    """Apply an affine transformation matrix to all contours in *glyph*.

    *matrix* must be a 6-element sequence ``(xx, xy, yx, yy, dx, dy)``
    compatible with fontforge's ``psMat`` format.

    Args:
        glyph:  The target glyph.
        matrix: A 6-tuple ``(xx, xy, yx, yy, dx, dy)``.

    Raises:
        ValueError: If *matrix* does not have exactly 6 elements.
    """
    if len(matrix) != 6:
        raise ValueError(f"transform matrix must have 6 elements, got {len(matrix)}")
    ff = glyph._ff
    if hasattr(ff, "transform"):
        try:
            ff.transform(tuple(matrix))  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def correct_direction(glyph: "Glyph") -> None:
    """Set contour winding directions to the PostScript/TrueType convention.

    Outer contours are made counter-clockwise, inner contours (holes)
    are made clockwise.
    """
    ff = glyph._ff
    if hasattr(ff, "correctDirection"):
        try:
            ff.correctDirection()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def correct_directions(glyph: "Glyph") -> None:
    """Alias for :func:`correct_direction`."""
    correct_direction(glyph)


def reverse_direction(glyph: "Glyph") -> None:
    """Reverse the winding direction of all contours in *glyph*."""
    ff = glyph._ff
    if hasattr(ff, "reverseDirection"):
        try:
            ff.reverseDirection()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def add_extrema(glyph: "Glyph") -> None:
    """Add on-curve points at the extrema of every spline.

    Required for valid TrueType/OpenType outlines.
    """
    ff = glyph._ff
    if hasattr(ff, "addExtrema"):
        try:
            ff.addExtrema()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def round_to_int(glyph: "Glyph") -> None:
    """Round all point coordinates to integer values."""
    ff = glyph._ff
    if hasattr(ff, "round"):
        try:
            ff.round()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def auto_hint(glyph: "Glyph") -> None:
    """Automatically generate PostScript hints for *glyph*."""
    ff = glyph._ff
    if hasattr(ff, "autoHint"):
        try:
            ff.autoHint()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def apply_stroke(
    glyph: "Glyph",
    width: float,
    join_type: str = "miter",
) -> None:
    """Expand the glyph outline by *width* font units (boldification).

    Args:
        glyph:     The target glyph.
        width:     Stroke expansion amount in font units.
        join_type: Stroke join style (``"miter"``, ``"round"``, ``"bevel"``).
    """
    ff = glyph._ff
    if hasattr(ff, "changeWeight"):
        try:
            ff.changeWeight(width, join_type)  # type: ignore[union-attr]
        except TypeError:
            try:
                ff.changeWeight(width)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass


def apply_slant(
    glyph: "Glyph",
    angle_deg: float,
    x_origin: float = 0.0,
) -> None:
    """Shear *glyph* horizontally to simulate an italic effect.

    Args:
        glyph:     The target glyph.
        angle_deg: Slant angle in degrees (10–14° is typical).
        x_origin:  Horizontal pivot position in font units.
    """
    shear = math.tan(math.radians(angle_deg))
    matrix: Matrix = (1.0, 0.0, shear, 1.0, -x_origin * shear, 0.0)
    transform(glyph, matrix)


def scale(glyph: "Glyph", sx: float, sy: float) -> None:
    """Scale *glyph* by independent horizontal and vertical factors.

    Args:
        glyph: The target glyph.
        sx:    Horizontal scale factor (1.0 = no change).
        sy:    Vertical scale factor (1.0 = no change).
    """
    transform(glyph, (sx, 0.0, 0.0, sy, 0.0, 0.0))


def translate(glyph: "Glyph", dx: float, dy: float) -> None:
    """Translate *glyph* by *(dx, dy)* font units.

    Args:
        glyph: The target glyph.
        dx:    Horizontal offset in font units.
        dy:    Vertical offset in font units.
    """
    transform(glyph, (1.0, 0.0, 0.0, 1.0, dx, dy))


def smooth_transitions(glyph: "Glyph") -> None:
    """Attempt to smooth curve transitions at on-curve points.

    This is a lightweight wrapper around fontforge's simplify with
    smooth-only options.
    """
    ff = glyph._ff
    if hasattr(ff, "simplify"):
        try:
            ff.simplify(0.1, ("smoothcurves",))  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def to_svg_path(glyph: "Glyph") -> str:
    """Export the glyph outlines as an SVG ``<path d="...">`` string.

    Returns:
        SVG path data string, or empty string if the glyph has no contours.
    """
    import os
    import tempfile
    ff = glyph._ff
    if not hasattr(ff, "export"):
        return ""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_file = os.path.join(tmpdir, "glyph.svg")
            ff.export(svg_file)  # type: ignore[union-attr]
            with open(svg_file, "r", encoding="utf-8") as fh:
                return fh.read()
    except Exception:  # noqa: BLE001
        return ""
