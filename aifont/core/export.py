"""aifont.core.export — generate OTF, TTF, WOFF, WOFF2, UFO, and SFD outputs.

Wraps ``fontforge.font.generate()`` with format-specific options.
FontForge source code is never modified.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

try:
    from fontTools.ttLib import woff2 as _woff2_module  # type: ignore
    _FONTTOOLS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _woff2_module = None  # type: ignore[assignment]
    _FONTTOOLS_AVAILABLE = False

__all__ = [
    "ExportOptions",
    "export_otf",
    "export_ttf",
    "export_woff",
    "export_woff2",
    "export_ufo",
    "export_svg",
    "export_sfd",
    "export_all",
    "_FONTTOOLS_AVAILABLE",
    "_convert_ttf_to_woff2",
]


# ---------------------------------------------------------------------------
# Export options
# ---------------------------------------------------------------------------


@dataclass
class ExportOptions:
    """Fine-grained export options."""

    hints: bool = False
    round_to_int: bool = False
    opentype: bool = True
    extra_flags: Sequence[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_ff_font(font: object) -> object:
    """Return the raw fontforge font from a wrapper or raw object."""
    if hasattr(font, "_font"):
        return font._font  # type: ignore[attr-defined]
    return font


def _ensure_dir(path: Union[str, Path]) -> None:
    """Create parent directories of *path* if they do not exist."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _convert_ttf_to_woff2(ttf_path: str, woff2_path: str) -> None:
    """Convert a TTF file at *ttf_path* to WOFF2 at *woff2_path*.

    Requires fontTools.

    Raises:
        RuntimeError: If fontTools is not available.
        ImportError:  If fontTools cannot be imported.
    """
    if not _FONTTOOLS_AVAILABLE or _woff2_module is None:
        raise RuntimeError(
            "fontTools is required for WOFF2 conversion. "
            "Install it with: pip install fonttools[woff]"
        )
    with open(ttf_path, "rb") as f_in, open(woff2_path, "wb") as f_out:
        _woff2_module.compress(f_in, f_out)


# ---------------------------------------------------------------------------
# Public export functions
# ---------------------------------------------------------------------------


def export_otf(
    font: object,
    path: Union[str, Path],
) -> Path:
    """Export the font as an OpenType CFF (.otf) file.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination file path.

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    _ensure_dir(out)
    ff = _get_ff_font(font)
    ff.generate(str(out), flags=("opentype",))  # type: ignore[attr-defined]
    return out


def export_ttf(
    font: object,
    path: Union[str, Path],
) -> Path:
    """Export the font as a TrueType (.ttf) file.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination file path.

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    _ensure_dir(out)
    ff = _get_ff_font(font)
    ff.generate(str(out))  # type: ignore[attr-defined]
    return out


def export_woff(
    font: object,
    path: Union[str, Path],
) -> Path:
    """Export the font as a WOFF file.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination file path.

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    _ensure_dir(out)
    ff = _get_ff_font(font)
    ff.generate(str(out))  # type: ignore[attr-defined]
    return out


def export_woff2(
    font: object,
    path: Union[str, Path],
    *,
    use_fonttools: bool = False,
) -> Path:
    """Export the font as a WOFF2 file.

    Strategy:
    1. If ``use_fonttools=True`` and fontTools is unavailable, raise immediately.
    2. Otherwise, try ``generate(path, flags=("woff2",))`` natively.
    3. If native WOFF2 fails, fall back: generate a temporary TTF then call
       :func:`_convert_ttf_to_woff2`.

    Args:
        font:           Font wrapper or raw fontforge font.
        path:           Destination file path.
        use_fonttools:  Require fontTools (raises if unavailable).

    Returns:
        The resolved :class:`~pathlib.Path` that was written.

    Raises:
        RuntimeError: If ``use_fonttools=True`` but fontTools is not installed.
    """
    out = Path(path)
    _ensure_dir(out)

    if use_fonttools and not _FONTTOOLS_AVAILABLE:
        raise RuntimeError(
            "fontTools is required for WOFF2 export. "
            "Install it with: pip install fonttools[woff]"
        )

    ff = _get_ff_font(font)

    # Try native WOFF2 generation
    try:
        ff.generate(str(out), flags=("woff2",))  # type: ignore[attr-defined]
        return out
    except Exception:  # noqa: BLE001
        pass

    # Fallback: TTF → WOFF2 via fontTools
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ff.generate(tmp_path)  # type: ignore[attr-defined]
        _convert_ttf_to_woff2(tmp_path, str(out))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return out


def export_ufo(
    font: object,
    path: Union[str, Path],
) -> Path:
    """Export the font as a UFO (Unified Font Object) directory.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination directory path.

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    ff = _get_ff_font(font)
    try:
        ff.save(str(out))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        ff.generate(str(out))  # type: ignore[attr-defined]
    return out


def export_svg(
    font: object,
    path: Union[str, Path],
) -> Path:
    """Export the font as an SVG font file.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination file path.

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    _ensure_dir(out)
    ff = _get_ff_font(font)
    ff.generate(str(out))  # type: ignore[attr-defined]
    return out


def export_sfd(
    font: object,
    path: Union[str, Path],
) -> Path:
    """Save the font in FontForge's native SFD format.

    Args:
        font: Font wrapper or raw fontforge font.
        path: Destination ``.sfd`` file path.

    Returns:
        The resolved :class:`~pathlib.Path` that was written.
    """
    out = Path(path)
    _ensure_dir(out)
    ff = _get_ff_font(font)
    ff.save(str(out))  # type: ignore[attr-defined]
    return out


def export_all(
    font: object,
    output_dir: Union[str, Path],
    basename: Optional[str] = None,
    formats: Optional[Sequence[str]] = None,
    options: Optional[ExportOptions] = None,
) -> Dict[str, Path]:
    """Batch export a font to multiple formats.

    Args:
        font:       Font wrapper or raw fontforge font.
        output_dir: Directory where all output files will be written.
        basename:   Base filename. Defaults to font's PostScript name.
        formats:    Format identifiers to export.  Defaults to all.
        options:    Fine-grained export options (currently unused).

    Returns:
        Mapping from format identifier to the output :class:`Path`.
    """
    _ALL_FORMATS = ("otf", "ttf", "woff", "woff2", "ufo", "svg")
    _EXPORTERS = {
        "otf": export_otf,
        "ttf": export_ttf,
        "woff": export_woff,
        "woff2": export_woff2,
        "ufo": export_ufo,
        "svg": export_svg,
    }
    _EXT = {
        "otf": ".otf", "ttf": ".ttf", "woff": ".woff",
        "woff2": ".woff2", "ufo": ".ufo", "svg": ".svg",
    }
    if formats is None:
        formats = _ALL_FORMATS

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ff = _get_ff_font(font)
    if basename is None:
        basename = str(getattr(ff, "fontname", None) or "font")

    results: Dict[str, Path] = {}
    for fmt in formats:
        fmt_lower = fmt.lower()
        if fmt_lower not in _EXPORTERS:
            raise ValueError(
                f"Unknown format {fmt!r}. Supported: {', '.join(_ALL_FORMATS)}"
            )
        dest = out_dir / f"{basename}{_EXT[fmt_lower]}"
        results[fmt_lower] = _EXPORTERS[fmt_lower](font, dest)

    return results
