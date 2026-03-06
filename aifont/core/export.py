"""
aifont.core.export — generate OTF, TTF, WOFF, WOFF2, and UFO outputs.

Wraps ``fontforge.font.generate()`` with format-specific options.
For WOFF2 compression fontTools is used when fontforge does not support
it natively.

FontForge source code is never modified.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

try:
    import fontforge as _ff  # noqa: F401
    _FF_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FF_AVAILABLE = False

try:
    from fontTools.ttLib import TTFont as _TTFont
    from fontTools.ttLib import woff2 as _woff2
    _FONTTOOLS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FONTTOOLS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_ff_font(font: object) -> object:
    """Return the raw fontforge font from a wrapper or raw object."""
    if hasattr(font, "_font"):
        return font._font  # type: ignore[attr-defined]
    return font


def _generate(ff_font: object, path: str, flags: tuple = ()) -> None:
    """Call fontforge's generate with the given flags tuple."""
    ff_font.generate(path, flags=flags)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_otf(
    font: object,
    path: str | Path,
    *,
    hints: bool = True,
) -> Path:
    """Export the font as an OpenType CFF (.otf) file.

    Args:
        font:  Font wrapper or raw fontforge font.
        path:  Destination file path (should end in ``.otf``).
        hints: Include PostScript hints (default: True).

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    ff = _get_ff_font(font)
    flags: tuple = () if hints else ("no-hints",)
    _generate(ff, str(out), flags)
    return out


def export_ttf(
    font: object,
    path: str | Path,
    *,
    hints: bool = False,
) -> Path:
    """Export the font as a TrueType (.ttf) file.

    Args:
        font:  Font wrapper or raw fontforge font.
        path:  Destination file path (should end in ``.ttf``).
        hints: Include TrueType hints (default: False).

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    ff = _get_ff_font(font)
    flags: tuple = () if hints else ("no-hints",)
    _generate(ff, str(out), flags)
    return out


def export_woff(
    font: object,
    path: str | Path,
) -> Path:
    """Export the font as a WOFF file.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination file path (should end in ``.woff``).

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    ff = _get_ff_font(font)
    _generate(ff, str(out))
    return out


def export_woff2(
    font: object,
    path: str | Path,
    *,
    use_fonttools: bool = True,
) -> Path:
    """Export the font as a WOFF2 file.

    When *use_fonttools* is ``True`` (default), the function first
    generates a TTF/OTF into a temporary file and then compresses it to
    WOFF2 using :mod:`fontTools.ttLib.woff2`.  This produces better
    compression than fontforge's built-in WOFF2 writer.

    Args:
        font:           Font wrapper or raw fontforge font.
        path:           Destination file path (should end in ``.woff2``).
        use_fonttools:  Use fontTools for compression (default: True).

    Returns:
        The resolved :class:`~pathlib.Path` that was written.

    Raises:
        RuntimeError: If fontTools is not installed and *use_fonttools*
                      is True.
    """
    out = Path(path)

    if use_fonttools:
        if not _FONTTOOLS_AVAILABLE:
            raise RuntimeError(
                "fontTools is required for WOFF2 export.  "
                "Install it with: pip install fonttools[woff]"
            )
        ff = _get_ff_font(font)

        # Generate a temporary TTF then recompress as WOFF2.
        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            _generate(ff, tmp_path)
            with open(tmp_path, "rb") as f_in, open(str(out), "wb") as f_out:
                _woff2.compress(f_in, f_out)
        finally:
            os.unlink(tmp_path)
    else:
        ff = _get_ff_font(font)
        _generate(ff, str(out))

    return out


def export_ufo(
    font: object,
    path: str | Path,
) -> Path:
    """Export the font as a UFO (Unified Font Object) directory.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination directory path (e.g. ``"MyFont.ufo"``).

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    ff = _get_ff_font(font)
    _generate(ff, str(out))
    return out
