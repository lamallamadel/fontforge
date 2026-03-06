"""AIFont core SDK — wrappers around FontForge Python bindings."""

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import get_kern_pairs, set_kern, auto_space
from aifont.core.contour import simplify, remove_overlap, transform
from aifont.core.svg_parser import svg_to_glyph
from aifont.core.export import export_otf, export_ttf, export_woff2
from aifont.core.analyzer import FontReport, analyze

__all__ = [
    "Font",
    "Glyph",
    "get_kern_pairs",
    "set_kern",
    "auto_space",
    "simplify",
    "remove_overlap",
    "transform",
    "svg_to_glyph",
    "export_otf",
    "export_ttf",
    "export_woff2",
    "FontReport",
    "analyze",
]
