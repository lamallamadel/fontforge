"""AIFont — AI-powered font design SDK built on top of FontForge."""

__version__ = "0.1.0"
__author__ = "AIFont Contributors"

from aifont.core.font import Font
from aifont.core.glyph import Glyph

__all__ = ["Font", "Glyph", "__version__"]
