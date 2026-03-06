"""AIFont core — high-level wrappers around FontForge Python bindings."""

from aifont.core.analyzer import analyze
from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import auto_space, get_kern_pairs, set_kern

__all__ = [
    "Font",
    "Glyph",
    "get_kern_pairs",
    "set_kern",
    "auto_space",
    "analyze",
]
