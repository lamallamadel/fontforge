"""
aifont.core.export — Font export utilities (OTF, TTF, WOFF2, UFO, etc.).

Wraps FontForge's ``font.generate()`` with format-specific defaults and,
for WOFF2, falls back to ``fontTools.ttLib`` compression when FontForge
does not natively support the format.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .font import Font


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_dir(path: str) -> None:
    """Create parent directories for *path* if they do not exist."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def _generate(ff_font: object, path: str, fmt: str, flags: tuple = ()) -> None:
    """Call ``fontforge.font.generate()`` with error handling."""
    try:
        ff_font.generate(path, fmt, flags)  # type: ignore[attr-defined]
    except TypeError:
        # Older fontforge versions do not accept flags
        ff_font.generate(path, fmt)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_otf(
    font: "Font",
    path: str,
    *,
    round_ps_to_int: bool = True,
) -> None:
    """Export *font* as an OpenType CFF (OTF) file.

    Parameters
    ----------
    font : Font
        Source font to export.
    path : str
        Destination ``.otf`` file path.  Parent directories are created
        automatically.
    round_ps_to_int : bool, optional
        When ``True`` (default) coordinates are rounded to integers
        before export, which improves compatibility.

    Examples
    --------
    ::

        from aifont.core.font import Font
        from aifont.core.export import export_otf

        font = Font.open("MyFont.sfd")
        export_otf(font, "dist/MyFont.otf")
    """
    _ensure_dir(path)
    flags: tuple = ("round",) if round_ps_to_int else ()
    _generate(font.ff_font, path, "opentype", flags)


def export_ttf(
    font: "Font",
    path: str,
    *,
    round_to_int: bool = True,
) -> None:
    """Export *font* as a TrueType (TTF) file.

    Parameters
    ----------
    font : Font
        Source font to export.
    path : str
        Destination ``.ttf`` file path.
    round_to_int : bool, optional
        Round coordinates to integers before export.  Defaults to ``True``.
    """
    _ensure_dir(path)
    flags: tuple = ("round",) if round_to_int else ()
    _generate(font.ff_font, path, "ttf", flags)


def export_woff(font: "Font", path: str) -> None:
    """Export *font* as a WOFF (Web Open Font Format) file.

    Parameters
    ----------
    font : Font
        Source font to export.
    path : str
        Destination ``.woff`` file path.
    """
    _ensure_dir(path)
    _generate(font.ff_font, path, "woff")


def export_woff2(font: "Font", path: str) -> None:
    """Export *font* as a WOFF2 file.

    First tries FontForge's native WOFF2 generator.  If that fails (some
    builds lack WOFF2 support), the function exports to a temporary TTF
    and converts it with ``fontTools.ttLib`` + ``brotli``.

    Parameters
    ----------
    font : Font
        Source font to export.
    path : str
        Destination ``.woff2`` file path.

    Raises
    ------
    ImportError
        If WOFF2 fallback is needed but ``fonttools`` is not installed.
    """
    _ensure_dir(path)

    # Try native FontForge WOFF2 generation first
    try:
        _generate(font.ff_font, path, "woff2")
        # Verify the file was actually written
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return
    except Exception:  # noqa: BLE001
        pass

    # Fallback: TTF → WOFF2 via fontTools
    try:
        from fontTools.ttLib import TTFont  # noqa: PLC0415
        from fontTools.ttLib.woff2 import compress  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "WOFF2 export requires fonttools with WOFF2 support. "
            "Install it with: pip install fonttools[woff]"
        ) from exc

    with tempfile.TemporaryDirectory() as tmp:
        ttf_path = os.path.join(tmp, "tmp.ttf")
        _generate(font.ff_font, ttf_path, "ttf")
        compress(ttf_path, path)


def export_ufo(font: "Font", path: str, ufo_version: int = 3) -> None:
    """Export *font* as a UFO (Unified Font Object) package.

    Parameters
    ----------
    font : Font
        Source font to export.
    path : str
        Destination directory (``*.ufo``).
    ufo_version : int, optional
        UFO format version.  Supported values are ``2`` and ``3``
        (default).
    """
    _ensure_dir(path)
    fmt = f"ufo{ufo_version}"
    _generate(font.ff_font, path, fmt)


def export_svg_font(font: "Font", path: str) -> None:
    """Export *font* as an SVG font file (deprecated in modern browsers).

    Parameters
    ----------
    font : Font
        Source font to export.
    path : str
        Destination ``.svg`` file path.
    """
    _ensure_dir(path)
    _generate(font.ff_font, path, "svg")


def export_sfd(font: "Font", path: str) -> None:
    """Save *font* in FontForge's native SFD format.

    Parameters
    ----------
    font : Font
        Source font to save.
    path : str
        Destination ``.sfd`` file path.
    """
    _ensure_dir(path)
    font.ff_font.save(path)  # type: ignore[attr-defined]
