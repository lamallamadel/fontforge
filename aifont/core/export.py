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

    Parameters
    ----------
    font:
        A ``fontforge.font`` instance.
    path:
        Destination file path (will be created/overwritten).
    flags:
        Extra ``fontforge`` generation flags, e.g. ``("opentype",)``.

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

    Parameters
    ----------
    font:
        A ``fontforge.font`` instance with variation data.
    path:
        Destination file path.
    flags:
        Extra ``fontforge`` generation flags.

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
