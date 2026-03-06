"""aifont.core — high-level Python wrappers around FontForge bindings.

DO NOT import fontforge directly from user code — use this package instead.
"""

from __future__ import annotations

from aifont.core.analyzer import FontReport, analyze
from aifont.core.contour import correct_directions, remove_overlap, simplify, transform
from aifont.core.export import export_otf, export_ttf, export_ufo, export_woff2
from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import auto_space, get_kern_pairs, set_kern
from aifont.core.svg_parser import svg_to_glyph

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
    "export_ufo",
    "svg_to_glyph",
    "FontReport",
    "analyze",
]
