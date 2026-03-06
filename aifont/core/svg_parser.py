"""Import SVG files (or raw SVG path data) into font glyphs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font
    from aifont.core.glyph import Glyph

_SVG_NS = "http://www.w3.org/2000/svg"


def svg_to_glyph(
    svg_path: str | Path,
    font: Font,
    unicode_point: int,
    glyph_name: str | None = None,
) -> Glyph:
    """Import an SVG file into a new or existing glyph.

    Parsing strategy:
    1. Use fontforge's native SVG import (``glyph.importOutlines``) if the
       file contains a single ``<path>`` element with a ``d`` attribute.
    2. Fall back to ``xml.etree`` for multi-path SVGs, injecting each path
       individually.

    Args:
        svg_path:      Path to the ``.svg`` file.
        font:          Target :class:`~aifont.core.font.Font`.
        unicode_point: Unicode codepoint to assign to the glyph.
        glyph_name:    Optional glyph name; defaults to ``uniXXXX`` form.

    Returns:
        The populated :class:`~aifont.core.glyph.Glyph`.
    """
    from aifont.core.glyph import Glyph  # noqa: PLC0415

    svg_path = Path(svg_path)
    if not svg_path.is_file():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    name = glyph_name or f"uni{unicode_point:04X}"
    ff = font._raw

    if name not in ff:
        ff.createChar(unicode_point, name)
    glyph = Glyph(ff[name])

    # Prefer fontforge's own import for simplicity and accuracy.
    try:
        glyph._raw.importOutlines(str(svg_path))
        return glyph
    except Exception:  # noqa: BLE001
        pass

    # Manual fallback: parse SVG and import path-by-path via temp files.
    _import_svg_manual(glyph, svg_path)
    return glyph


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _import_svg_manual(glyph: Glyph, svg_path: Path) -> None:
    """Parse multi-path SVG and inject outlines into *glyph*."""
    import tempfile  # noqa: PLC0415

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Strip namespace for easier querying.
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    paths = root.findall(".//path")
    if not paths:
        raise ValueError(f"No <path> elements found in {svg_path}")

    for path_elem in paths:
        d = path_elem.get("d", "")
        if not d:
            continue

        # Build a minimal SVG containing only this path and import it.
        mini_svg = (
            '<?xml version="1.0"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 1000 1000">'
            f'<path d="{d}"/>'
            "</svg>"
        )
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as fh:
            fh.write(mini_svg)
            tmp = fh.name

        try:
            glyph._raw.importOutlines(tmp)
        finally:
            Path(tmp).unlink(missing_ok=True)
