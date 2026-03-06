"""
aifont.core — low-level Python wrappers around FontForge bindings.
"""

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.contour import simplify, remove_overlap, correct_directions, transform
from aifont.core.analyzer import analyze, FontReport

__all__ = [
    "Font",
    "Glyph",
    "simplify",
    "remove_overlap",
    "correct_directions",
    "transform",
    "analyze",
    "FontReport",
]
