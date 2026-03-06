"""
aifont.core — Core SDK modules for FontForge wrapping.

Exposes the primary classes and functions used to interact with fonts
through the high-level AIFont API.
"""

from .font import Font
from .glyph import Glyph
from .metrics import get_kern_pairs, set_kern, auto_space
from .contour import simplify, remove_overlap, transform
from .export import export_otf, export_ttf, export_woff2, export_ufo
from .svg_parser import svg_to_glyph
from .analyzer import analyze, FontReport

__all__ = [
    "Font",
    "Glyph",
    "get_kern_pairs",
    "set_kern",
    "auto_space",
    "simplify",
    "remove_overlap",
    "transform",
    "export_otf",
    "export_ttf",
    "export_woff2",
    "export_ufo",
    "svg_to_glyph",
    "analyze",
    "FontReport",
]
