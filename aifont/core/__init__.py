"""
aifont.core — high-level Python wrappers around FontForge bindings.

DO NOT import fontforge directly from user code — use this package instead.
"""

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import get_kern_pairs, set_kern, auto_space
from aifont.core.contour import simplify, remove_overlap, correct_directions, transform
from aifont.core.export import export_otf, export_ttf, export_woff2
from aifont.core.analyzer import FontAnalyzer, FontReport, analyze

__all__ = [
    "Font",
    "Glyph",
    "get_kern_pairs",
    "set_kern",
    "auto_space",
    "simplify",
    "remove_overlap",
    "correct_directions",
    "transform",
    "export_otf",
    "export_ttf",
    "export_woff2",
    "FontAnalyzer",
    "FontReport",
    "analyze",
]
