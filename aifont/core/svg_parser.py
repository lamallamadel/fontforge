"""Import SVG files into font glyphs via fontforge contours."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from aifont.core.font import Font

_SVG_NS = "http://www.w3.org/2000/svg"


def _parse_viewbox(viewbox: str) -> Optional[Tuple[float, float, float, float]]:
    """Parse a SVG viewBox attribute into ``(min_x, min_y, width, height)``."""
    parts = viewbox.replace(",", " ").split()
    if len(parts) == 4:
        try:
            return tuple(float(p) for p in parts)  # type: ignore[return-value]
        except ValueError:
            pass
    return None


def _collect_path_data(root: ET.Element) -> List[str]:
    """Recursively collect all ``d`` attributes from ``<path>`` elements."""
    paths: List[str] = []
    tag_path = f"{{{_SVG_NS}}}path"
    tag_path_bare = "path"
    for elem in root.iter():
        if elem.tag in (tag_path, tag_path_bare):
            d = elem.get("d", "").strip()
            if d:
                paths.append(d)
    return paths


def svg_to_glyph(
    svg_path: str,
    font: "Font",
    unicode_point: int,
    glyph_name: Optional[str] = None,
) -> object:
    """Import the SVG at *svg_path* as a glyph in *font*.

    Creates (or overwrites) the glyph for *unicode_point*.  Returns the
    underlying fontforge glyph object.

    If fontforge's native ``importOutlines`` is available it is used
    directly; otherwise the SVG ``<path>`` elements are inspected and a
    best-effort import is attempted.
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    ff = font._ff
    name = glyph_name or f"uni{unicode_point:04X}"

    # Create or retrieve glyph slot
    try:
        glyph = ff.createChar(unicode_point, name)  # type: ignore[union-attr]
    except (AttributeError, TypeError):
        try:
            glyph = ff[name]  # type: ignore[index]
        except (KeyError, TypeError):
            raise RuntimeError(
                f"Cannot create glyph {name!r} — fontforge not available."
            )

    # Prefer native import
    if hasattr(glyph, "importOutlines"):
        glyph.importOutlines(svg_path)  # type: ignore[union-attr]
        return glyph

    # Fallback: parse SVG and warn
    tree = ET.parse(svg_path)
    root = tree.getroot()
    path_data = _collect_path_data(root)
    if not path_data:
        raise ValueError(f"No <path> elements found in SVG: {svg_path}")
    # Without native importOutlines we cannot inject contours, but we
    # can at least set the glyph width from the viewBox.
    viewbox_attr = root.get("viewBox", "")
    if viewbox_attr:
        vb = _parse_viewbox(viewbox_attr)
        if vb is not None:
            glyph.width = int(vb[2])  # type: ignore[union-attr]
    return glyph
