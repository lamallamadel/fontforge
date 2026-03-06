"""AIFont core SDK — high-level wrappers around FontForge Python bindings."""

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import get_kern_pairs, set_kern, auto_space
from aifont.core.analyzer import analyze

__all__ = ["Font", "Glyph", "get_kern_pairs", "set_kern", "auto_space", "analyze"]
