"""aifont.utils — utility helpers for the AIFont SDK."""

from __future__ import annotations

from aifont.utils.font_analyzer import FontReport, analyze
from aifont.utils.svg_parser import svg_path_to_contours, svg_to_glyph

__all__ = [
    "svg_to_glyph",
    "svg_path_to_contours",
    "analyze",
    "FontReport",
]
