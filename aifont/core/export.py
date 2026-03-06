"""Generate OTF, TTF, WOFF2 and Variable Font outputs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font


def export_otf(font: Font, path: str | Path) -> None:
    """Generate an OpenType CFF (OTF) file at *path*.

    Delegates to :meth:`fontforge.font.generate` with format flags
    appropriate for OTF output.
    """
    font._raw.generate(str(path), flags=("opentype",))


def export_ttf(font: Font, path: str | Path) -> None:
    """Generate a TrueType (TTF) file at *path*."""
    font._raw.generate(str(path))


def export_woff2(font: Font, path: str | Path) -> None:
    """Generate a WOFF2 file at *path*.

    FontForge can produce WOFF2 natively via its ``generate()`` call.
    If the installed version lacks that support we fall back to
    :mod:`fontTools` post-processing.
    """
    import tempfile  # noqa: PLC0415

    path = Path(path)

    # Attempt native FontForge WOFF2 generation first.
    try:
        font._raw.generate(str(path), flags=("woff2",))
        return
    except Exception:  # noqa: BLE001
        pass

    # Fallback: generate TTF then compress with fontTools.
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        export_ttf(font, tmp_path)
        _ttf_to_woff2(tmp_path, str(path))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _ttf_to_woff2(ttf_path: str, woff2_path: str) -> None:
    """Compress a TTF file to WOFF2 using :mod:`fontTools`."""
    from fontTools.ttLib import TTFont  # noqa: PLC0415

    tt = TTFont(ttf_path)
    tt.flavor = "woff2"
    tt.save(woff2_path)
"""aifont/core/export.py — generate OTF, TTF, WOFF2 and Variable Font outputs.

All heavy lifting is delegated to ``fontforge.font.generate()`` and, for
WOFF2 compression, to ``fontTools.ttLib`` / ``fontTools.ttLib.woff2``.

Usage example::

    import fontforge
    from aifont.core.export import export_otf, export_ttf, export_woff2

    ff_font = fontforge.open("MyFont.sfd")
    export_otf(ff_font, "/tmp/MyFont.otf")
    export_ttf(ff_font, "/tmp/MyFont.ttf")
    export_woff2(ff_font, "/tmp/MyFont.woff2")
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
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

# fontforge is an optional C extension — guard the import so that the module
# can still be imported (e.g. during tests with mocks) when the native
# extension is not installed.
try:
    import fontforge as _ff  # noqa: F401  (used indirectly through font objects)
    _FF_AVAILABLE = True
except ImportError:
    _FF_AVAILABLE = False

try:
    from fontTools.ttLib import TTFont as _TTFont
    from fontTools.ttLib import woff2 as _woff2
    _FONTTOOLS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FONTTOOLS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def export_otf(
    font: object,
    path: str | os.PathLike,
    *,
    flags: Sequence[str] = (),
) -> Path:
    """Export *font* as an OpenType CFF (OTF) file.
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
        A ``fontforge.font`` instance.
    path:
        Destination file path (will be created/overwritten).
    flags:
        Extra ``fontforge`` generation flags, e.g. ``("opentype",)``.
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
        The resolved path of the generated file.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    gen_flags = tuple(flags) or ("opentype",)
    font.generate(str(dest), flags=gen_flags)
    return dest


def export_ttf(
    font: object,
    path: str | os.PathLike,
    *,
    autohint: bool = True,
    flags: Sequence[str] = (),
) -> Path:
    """Export *font* as a TrueType (TTF) file.
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
        A ``fontforge.font`` instance.
    path:
        Destination file path (will be created/overwritten).
    autohint:
        When ``True`` (default) run ``font.autoHint()`` before exporting
        so that the TrueType file benefits from basic hinting.
    flags:
        Extra ``fontforge`` generation flags.
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination file path.
    options:
        Fine-grained export options.

    Returns
    -------
    Path
        The resolved path of the generated file.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if autohint:
        try:
            font.autoHint()
        except Exception:  # pragma: no cover — fontforge may raise on empty fonts
            pass

    gen_flags = tuple(flags) or ("opentype",)
    font.generate(str(dest), flags=gen_flags)
    return dest


def export_woff2(
    font: object,
    path: str | os.PathLike,
    *,
    autohint: bool = False,
    flags: Sequence[str] = (),
) -> Path:
    """Export *font* as a WOFF2 file.

    The strategy is:

    1. Generate a temporary TTF via ``font.generate()``.
    2. Compress it to WOFF2 with ``fontTools.ttLib.woff2``.
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
        A ``fontforge.font`` instance.
    path:
        Destination ``.woff2`` file path (will be created/overwritten).
    autohint:
        Optionally apply auto-hinting before WOFF2 conversion.
    flags:
        Extra ``fontforge`` generation flags passed for the intermediate TTF.
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination file path.
    options:
        Fine-grained export options.

    Returns
    -------
    Path
        The resolved path of the generated WOFF2 file.

    Raises
    ------
    ImportError
        If ``fontTools`` is not installed.
    """
    if not _FONTTOOLS_AVAILABLE:
        raise ImportError(
            "fontTools is required for WOFF2 export. "
            "Install it with: pip install fonttools[woff]"
        )

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        ttf_path = Path(tmp) / "font.ttf"
        export_ttf(font, ttf_path, autohint=autohint, flags=flags)

        _woff2.compress(str(ttf_path), str(dest))

    return dest


def export_variable(
    font: object,
    path: str | os.PathLike,
    *,
    flags: Sequence[str] = (),
) -> Path:
    """Export *font* as a variable OpenType font.

    This calls ``font.generate()`` with the ``"opentype"`` flag.  The font
    object must already have variation axes and masters set up (e.g. via
    FontForge's multiple-master support).
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
        A ``fontforge.font`` instance with variation data.
    path:
        Destination file path.
    flags:
        Extra ``fontforge`` generation flags.
        A :class:`fontforge.font` instance or a file-system path.
    output_path:
        Destination directory path.  The ``.ufo`` extension is added
        automatically if missing.
    options:
        Fine-grained export options (hinting/rounding applied before save).

    Returns
    -------
    Path
        The resolved path of the generated file.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    gen_flags = tuple(flags) or ("opentype",)
    font.generate(str(dest), flags=gen_flags)
    return dest


def subset_font(
    input_path: str | os.PathLike,
    output_path: str | os.PathLike,
    *,
    unicodes: Optional[Iterable[int]] = None,
    language_tags: Optional[Iterable[str]] = None,
    glyphs: Optional[Iterable[str]] = None,
) -> Path:
    """Create a subset of a font using ``fontTools.subset``.

    At least one of *unicodes*, *language_tags*, or *glyphs* must be provided.

    Parameters
    ----------
    input_path:
        Source font file (.otf, .ttf, or .woff2).
    output_path:
        Destination file path for the subset font.
    unicodes:
        Iterable of Unicode code points to keep.
    language_tags:
        IETF BCP-47 language tags (e.g. ``["fr", "de"]``).  The function
        maps tags to the Unicode ranges required by those scripts via a
        built-in lookup table.
    glyphs:
        Explicit glyph names to keep.
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
        The resolved path of the generated subset font.

    Raises
    ------
    ImportError
        If ``fontTools`` is not installed.
    ValueError
        If no subset criteria are specified.
    """
    if not _FONTTOOLS_AVAILABLE:
        raise ImportError(
            "fontTools is required for subsetting. "
            "Install it with: pip install fonttools"
        )

    if unicodes is None and language_tags is None and glyphs is None:
        raise ValueError(
            "At least one of `unicodes`, `language_tags`, or `glyphs` must be provided."
        )

    from fontTools import subset as _subset  # local import to keep module fast

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Build the unicode set
    unicode_set: set[int] = set(unicodes or [])
    for tag in language_tags or []:
        unicode_set.update(_language_tag_to_unicodes(tag))

    # Build subsetter options
    options = _subset.Options()
    options.layout_features = ["*"]  # keep all OpenType features
    options.name_IDs = ["*"]         # keep all name table entries

    subsetter = _subset.Subsetter(options=options)

    tt = _TTFont(str(input_path))

    if unicode_set:
        subsetter.populate(unicodes=sorted(unicode_set))
    if glyphs:
        subsetter.populate(glyphs=list(glyphs))

    subsetter.subset(tt)
    tt.save(str(dest))
    return dest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Compact mapping from IETF language tag (or script identifier) to the
# primary Unicode ranges used by that language.  This is intentionally
# minimal — extend as needed.
_LANG_UNICODE_RANGES: Dict[str, list[tuple[int, int]]] = {
    # Latin-script languages
    "en":  [(0x0020, 0x007E), (0x00A0, 0x00FF)],
    "fr":  [(0x0020, 0x007E), (0x00A0, 0x00FF)],
    "de":  [(0x0020, 0x007E), (0x00A0, 0x00FF), (0x1E00, 0x1EFF)],
    "es":  [(0x0020, 0x007E), (0x00A0, 0x00FF)],
    "pt":  [(0x0020, 0x007E), (0x00A0, 0x00FF)],
    "it":  [(0x0020, 0x007E), (0x00A0, 0x00FF)],
    "nl":  [(0x0020, 0x007E), (0x00A0, 0x00FF)],
    "pl":  [(0x0020, 0x007E), (0x0100, 0x017F)],
    "cs":  [(0x0020, 0x007E), (0x0100, 0x017F)],
    "ro":  [(0x0020, 0x007E), (0x0100, 0x017F)],
    "hu":  [(0x0020, 0x007E), (0x0100, 0x017F)],
    "tr":  [(0x0020, 0x007E), (0x00A0, 0x00FF), (0x0100, 0x017F)],
    # Cyrillic
    "ru":  [(0x0020, 0x007E), (0x0400, 0x04FF)],
    "uk":  [(0x0020, 0x007E), (0x0400, 0x04FF)],
    "bg":  [(0x0020, 0x007E), (0x0400, 0x04FF)],
    # Greek
    "el":  [(0x0020, 0x007E), (0x0370, 0x03FF), (0x1F00, 0x1FFF)],
    # Arabic
    "ar":  [(0x0020, 0x007E), (0x0600, 0x06FF), (0x0750, 0x077F)],
    # Hebrew
    "he":  [(0x0020, 0x007E), (0x0590, 0x05FF)],
    # CJK
    "zh":  [(0x0020, 0x007E), (0x4E00, 0x9FFF), (0x3000, 0x303F)],
    "ja":  [(0x0020, 0x007E), (0x3040, 0x309F), (0x30A0, 0x30FF),
             (0x4E00, 0x9FFF), (0xFF00, 0xFFEF)],
    "ko":  [(0x0020, 0x007E), (0xAC00, 0xD7AF), (0x1100, 0x11FF)],
}


def _language_tag_to_unicodes(tag: str) -> list[int]:
    """Return the list of Unicode code points for a BCP-47 language *tag*.

    Falls back to the base language subtag (e.g. ``"fr-CA"`` → ``"fr"``) when
    the full tag is not found.  Returns an empty list for unknown tags.
    """
    key = tag.lower()
    ranges = _LANG_UNICODE_RANGES.get(key)
    if ranges is None:
        base = key.split("-")[0]
        ranges = _LANG_UNICODE_RANGES.get(base, [])
    return [cp for start, end in ranges for cp in range(start, end + 1)]
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
