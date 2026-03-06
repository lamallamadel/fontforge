"""
aifont.utils — Utility helpers for the AIFont SDK.
"""

from .svg_parser import svg_to_glyph, svg_path_to_contours
from .font_analyzer import analyze, FontReport

__all__ = [
    "svg_to_glyph",
    "svg_path_to_contours",
    "analyze",
    "FontReport",
]
"""AIFont utility modules."""
