"""SVG-to-glyph importer."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:
    import defusedxml.ElementTree as ET  # type: ignore
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore  # noqa: PLC0414

if TYPE_CHECKING:
    from aifont.core.font import Font


_SVG_NS = "http://www.w3.org/2000/svg"


def svg_to_glyph(
    svg_path: str | Path,
    font: "Font",
    unicode_point: int,
    glyph_name: Optional[str] = None,
) -> None:
    """Import an SVG file as a glyph into *font*.

    The SVG is imported using FontForge's built-in SVG importer after the
    target glyph slot has been created / selected.

    Args:
        svg_path:      Path to the SVG file to import.
        font:          Target :class:`~aifont.core.font.Font`.
        unicode_point: Unicode code point to assign (e.g. ``0x0041`` for 'A').
        glyph_name:    Optional glyph name override.  Defaults to the
                       Unicode character name.

    Raises:
        FileNotFoundError: If the SVG file does not exist.
        ValueError:        If the SVG has no ``<path>`` elements.
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    # Basic validation
    tree = ET.parse(svg_path)
    root = tree.getroot()
    paths = (
        root.findall(f".//{{{_SVG_NS}}}path")
        + root.findall(".//path")
    )
    if not paths:
        raise ValueError(f"No <path> elements found in {svg_path}")

    ff = font._ff
    if ff is None:
        raise RuntimeError("No font loaded.")

    # Create or select the glyph slot
    if unicode_point in ff:
        glyph = ff[unicode_point]
    else:
        glyph_name = glyph_name or f"uni{unicode_point:04X}"
        glyph = ff.createChar(unicode_point, glyph_name)

    # FontForge can import SVG directly
    glyph.importOutlines(str(svg_path))
    glyph.correctDirection()
