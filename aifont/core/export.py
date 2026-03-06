"""Font export helpers for OTF, TTF, and WOFF2 output formats."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aifont.core.font import Font


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)


def export_otf(font: "Font", path: str) -> None:
    """Generate an OTF file at *path* from *font*."""
    _ensure_dir(path)
    font._ff.generate(path, flags=("opentype",))  # type: ignore[union-attr]


def export_ttf(font: "Font", path: str) -> None:
    """Generate a TTF file at *path* from *font*."""
    _ensure_dir(path)
    font._ff.generate(path)  # type: ignore[union-attr]


def export_woff2(font: "Font", path: str) -> None:
    """Generate a WOFF2 file at *path* from *font*.

    Uses fontforge's native WOFF2 generation if available; otherwise
    falls back to fontTools for compression.
    """
    _ensure_dir(path)
    ff = font._ff
    # Try native WOFF2 generation
    try:
        ff.generate(path, flags=("woff2",))  # type: ignore[union-attr]
        return
    except (AttributeError, TypeError, Exception):
        pass
    # Fallback: generate TTF then convert with fontTools
    tmp_ttf = path.replace(".woff2", "_tmp.ttf")
    try:
        ff.generate(tmp_ttf)  # type: ignore[union-attr]
        _convert_ttf_to_woff2(tmp_ttf, path)
    finally:
        if os.path.exists(tmp_ttf):
            os.remove(tmp_ttf)


def _convert_ttf_to_woff2(ttf_path: str, woff2_path: str) -> None:
    """Convert a TTF file to WOFF2 using fontTools."""
    try:
        from fontTools.ttLib import TTFont  # type: ignore[import]
        from fontTools.ttLib.sfnt import WOFFFlavorData  # type: ignore[import]

        tt = TTFont(ttf_path)
        tt.flavor = "woff2"
        tt.save(woff2_path)
    except ImportError as exc:
        raise RuntimeError(
            "fontTools is required for WOFF2 export when fontforge native "
            "support is unavailable. Install it with: pip install fonttools"
        ) from exc
