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
