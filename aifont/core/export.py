"""Font export utilities — OTF, TTF, WOFF2, Variable Font."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aifont.core.font import Font


def export_otf(font: "Font", path: str | Path) -> Path:
    """Export the font as OpenType (CFF) OTF.

    Args:
        font: Source font.
        path: Output path (should end in ``.otf``).

    Returns:
        Resolved output path.
    """
    path = Path(path)
    font._ff.generate(str(path), flags=("opentype",))
    return path


def export_ttf(font: "Font", path: str | Path) -> Path:
    """Export the font as TrueType TTF.

    Args:
        font: Source font.
        path: Output path (should end in ``.ttf``).

    Returns:
        Resolved output path.
    """
    path = Path(path)
    font._ff.generate(str(path))
    return path


def export_woff2(font: "Font", path: str | Path) -> Path:
    """Export the font as WOFF2 (web font).

    Uses fontTools for WOFF2 compression when available, falling back to
    FontForge's built-in WOFF2 support.

    Args:
        font: Source font.
        path: Output path (should end in ``.woff2``).

    Returns:
        Resolved output path.
    """
    path = Path(path)
    # First export as TTF, then compress with fontTools
    tmp_ttf = path.with_suffix(".ttf")
    export_ttf(font, tmp_ttf)
    try:
        from fontTools.ttLib import TTFont  # type: ignore
        from fontTools.ttLib.woff2 import compress  # type: ignore

        compress(str(tmp_ttf), str(path))
        tmp_ttf.unlink(missing_ok=True)
    except ImportError:
        # Fallback: FontForge native WOFF2
        font._ff.generate(str(path), flags=("woff2",))
        tmp_ttf.unlink(missing_ok=True)
    return path


def export_variable(font: "Font", path: str | Path) -> Path:
    """Export the font as a Variable Font (experimental).

    Args:
        font: Source font (must have variation axes defined).
        path: Output path (should end in ``.ttf`` or ``.otf``).

    Returns:
        Resolved output path.
    """
    path = Path(path)
    font._ff.generate(str(path), flags=("opentype", "variable"))
    return path
