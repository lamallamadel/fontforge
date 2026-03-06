"""Export module for AIFont — generate OTF, TTF, WOFF, WOFF2, UFO, and SVG Font outputs.

All heavy lifting is delegated to FontForge's ``font.generate()`` method and, for
WOFF2 when FontForge lacks native support, to ``fontTools.ttLib``.

Architecture note
-----------------
FontForge is the underlying engine.  **Do not** modify any FontForge source code.
AIFont is a Python SDK layer built *on top* of FontForge via its Python bindings
(``import fontforge``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple, Union

import fontforge

__all__ = [
    "ExportOptions",
    "export_otf",
    "export_ttf",
    "export_woff",
    "export_woff2",
    "export_ufo",
    "export_svg",
    "export_all",
]

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

FontLike = Union[object, "str", "Path"]  # fontforge.font object or path to open one

# Flags accepted by fontforge.font.generate()
_GenerateFlags = Tuple[str, ...]


# ---------------------------------------------------------------------------
# Export options dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExportOptions:
    """Options controlling how a font is exported.

    Attributes
    ----------
    hints:
        Whether to apply auto-hinting before export.  Defaults to ``False``.
    round_to_int:
        Whether to round all coordinates to integer values before export.
        Defaults to ``False``.
    opentype:
        Include OpenType features in the output.  Defaults to ``True``.
    old_style_kern:
        Write old-style kern table in addition to GPOS kerning.
        Defaults to ``False``.
    extra_flags:
        Additional raw flag strings forwarded directly to
        ``fontforge.font.generate()``.  See FontForge documentation for the
        full list.
    woff2_fallback:
        When FontForge does not support WOFF2 natively (i.e. the
        ``"woff2"`` format string is unavailable), fall back to generating a
        TTF first and then compressing it with ``fontTools``.
        Defaults to ``True``.
    """

    hints: bool = False
    round_to_int: bool = False
    opentype: bool = True
    old_style_kern: bool = False
    extra_flags: Sequence[str] = field(default_factory=list)
    woff2_fallback: bool = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_flags(self) -> _GenerateFlags:
        """Return the tuple of flag strings for ``font.generate()``."""
        flags: list[str] = []
        if self.opentype:
            flags.append("opentype")
        if self.old_style_kern:
            flags.append("old-kern")
        flags.extend(self.extra_flags)
        return tuple(flags)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_font(font: FontLike) -> Tuple[fontforge.font, bool]:
    """Return a ``(fontforge.font, opened_here)`` pair.

    If *font* is a path-like object the file is opened and ``opened_here`` is
    ``True`` so the caller knows to close the object afterwards.
    """
    if isinstance(font, (str, Path)):
        return fontforge.open(str(font)), True
    return font, False


def _prepare_font(ff_font: fontforge.font, options: ExportOptions) -> None:
    """Apply pre-export transformations in-place."""
    if options.round_to_int:
        ff_font.selection.all()
        ff_font.round()
    if options.hints:
        ff_font.selection.all()
        ff_font.autoHint()


def _ensure_dir(path: Union[str, Path]) -> None:
    """Create parent directories of *path* if they do not exist."""
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Public export functions
# ---------------------------------------------------------------------------


def export_otf(
    font: FontLike,
    output_path: Union[str, Path],
    options: Optional[ExportOptions] = None,
) -> Path:
    """Export a font as OpenType CFF (OTF).

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance **or** a file-system path to a
        font file that FontForge can open.
    output_path:
        Destination file path.  The ``.otf`` extension is added automatically
        if missing.
    options:
        Fine-grained export options.  Defaults to :class:`ExportOptions`.

    Returns
    -------
    Path
        The resolved output path.
    """
    if options is None:
        options = ExportOptions()
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".otf":
        output_path = output_path.with_suffix(".otf")
    _ensure_dir(output_path)

    ff_font, opened = _resolve_font(font)
    try:
        _prepare_font(ff_font, options)
        ff_font.generate(str(output_path), flags=options._build_flags())
    finally:
        if opened:
            ff_font.close()
    return output_path


def export_ttf(
    font: FontLike,
    output_path: Union[str, Path],
    options: Optional[ExportOptions] = None,
) -> Path:
    """Export a font as TrueType (TTF).

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination file path.
    options:
        Fine-grained export options.

    Returns
    -------
    Path
        The resolved output path.
    """
    if options is None:
        options = ExportOptions()
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".ttf":
        output_path = output_path.with_suffix(".ttf")
    _ensure_dir(output_path)

    ff_font, opened = _resolve_font(font)
    try:
        _prepare_font(ff_font, options)
        ff_font.generate(str(output_path), flags=options._build_flags())
    finally:
        if opened:
            ff_font.close()
    return output_path


def export_woff(
    font: FontLike,
    output_path: Union[str, Path],
    options: Optional[ExportOptions] = None,
) -> Path:
    """Export a font as WOFF.

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination file path.
    options:
        Fine-grained export options.

    Returns
    -------
    Path
        The resolved output path.
    """
    if options is None:
        options = ExportOptions()
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".woff":
        output_path = output_path.with_suffix(".woff")
    _ensure_dir(output_path)

    ff_font, opened = _resolve_font(font)
    try:
        _prepare_font(ff_font, options)
        ff_font.generate(str(output_path), flags=options._build_flags())
    finally:
        if opened:
            ff_font.close()
    return output_path


def export_woff2(
    font: FontLike,
    output_path: Union[str, Path],
    options: Optional[ExportOptions] = None,
) -> Path:
    """Export a font as WOFF2.

    FontForge generates WOFF2 directly when built with WOFF2 support.  If it
    is not available (``options.woff2_fallback`` is ``True``), the function
    generates a temporary TTF and then compresses it with
    ``fontTools.ttLib`` + ``brotli``.

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination file path.
    options:
        Fine-grained export options.

    Returns
    -------
    Path
        The resolved output path.

    Raises
    ------
    RuntimeError
        If WOFF2 generation fails and fallback is disabled.
    """
    if options is None:
        options = ExportOptions()
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".woff2":
        output_path = output_path.with_suffix(".woff2")
    _ensure_dir(output_path)

    ff_font, opened = _resolve_font(font)
    try:
        _prepare_font(ff_font, options)
        # Try native FontForge WOFF2 export first.
        try:
            ff_font.generate(str(output_path), flags=options._build_flags())
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
        except Exception:
            pass

        # Fallback: TTF → WOFF2 via fontTools.
        if not options.woff2_fallback:
            raise RuntimeError(
                "FontForge WOFF2 export failed and woff2_fallback is disabled."
            )
        return _woff2_via_fonttools(ff_font, output_path, options)
    finally:
        if opened:
            ff_font.close()


def _woff2_via_fonttools(
    ff_font: fontforge.font,
    output_path: Path,
    options: ExportOptions,
) -> Path:
    """Generate WOFF2 by first producing a TTF and then using fontTools."""
    import tempfile

    try:
        from fontTools.ttLib.woff2 import compress as woff2_compress
    except ImportError as exc:
        raise RuntimeError(
            "fontTools is required for WOFF2 fallback export.  "
            "Install it with: pip install fonttools[woff]"
        ) from exc

    with tempfile.TemporaryDirectory() as tmp_dir:
        ttf_path = Path(tmp_dir) / "font.ttf"
        ff_font.generate(str(ttf_path), flags=options._build_flags())
        woff2_compress(str(ttf_path), str(output_path))
    return output_path


def export_ufo(
    font: FontLike,
    output_path: Union[str, Path],
    options: Optional[ExportOptions] = None,
) -> Path:
    """Export a font as UFO (Unified Font Object) directory.

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination directory path.  The ``.ufo`` extension is added
        automatically if missing.
    options:
        Fine-grained export options (hinting/rounding applied before save).

    Returns
    -------
    Path
        The resolved output path.
    """
    if options is None:
        options = ExportOptions()
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".ufo":
        output_path = output_path.with_suffix(".ufo")
    _ensure_dir(output_path)

    ff_font, opened = _resolve_font(font)
    try:
        _prepare_font(ff_font, options)
        # FontForge writes UFO when the path ends in .ufo.
        ff_font.save(str(output_path))
    finally:
        if opened:
            ff_font.close()
    return output_path


def export_svg(
    font: FontLike,
    output_path: Union[str, Path],
    options: Optional[ExportOptions] = None,
) -> Path:
    """Export a font as SVG Font.

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination file path.  The ``.svg`` extension is added automatically
        if missing.
    options:
        Fine-grained export options.

    Returns
    -------
    Path
        The resolved output path.
    """
    if options is None:
        options = ExportOptions()
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".svg":
        output_path = output_path.with_suffix(".svg")
    _ensure_dir(output_path)

    ff_font, opened = _resolve_font(font)
    try:
        _prepare_font(ff_font, options)
        ff_font.generate(str(output_path), flags=options._build_flags())
    finally:
        if opened:
            ff_font.close()
    return output_path


def export_all(
    font: FontLike,
    output_dir: Union[str, Path],
    basename: Optional[str] = None,
    formats: Optional[Sequence[str]] = None,
    options: Optional[ExportOptions] = None,
) -> Dict[str, Path]:
    """Batch export a font to multiple formats at once.

    Parameters
    ----------
    font:
        A :class:`fontforge.font` instance or a file-system path.
    output_dir:
        Directory where all output files will be written.
    basename:
        Base filename (without extension).  Defaults to the font's
        ``fontname`` attribute.
    formats:
        Sequence of format identifiers to export.  Supported values:
        ``"otf"``, ``"ttf"``, ``"woff"``, ``"woff2"``, ``"ufo"``,
        ``"svg"``.  Defaults to all formats.
    options:
        Fine-grained export options applied to every format.

    Returns
    -------
    dict
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

    if options is None:
        options = ExportOptions()
    if formats is None:
        formats = _ALL_FORMATS

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the font once; keep it open for the whole batch.
    ff_font, opened = _resolve_font(font)
    try:
        if basename is None:
            basename = ff_font.fontname or "font"

        results: Dict[str, Path] = {}
        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in _EXPORTERS:
                raise ValueError(
                    f"Unknown format {fmt!r}.  "
                    f"Supported formats: {', '.join(_ALL_FORMATS)}"
                )
            dest = output_dir / basename
            results[fmt] = _EXPORTERS[fmt](ff_font, dest, options)
    finally:
        if opened:
            ff_font.close()

    return results
