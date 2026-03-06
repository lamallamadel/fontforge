"""AIFont — Python SDK and AI agent layer built on top of FontForge."""

__version__ = "0.1.0"

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.analyzer import FontReport, analyze

__all__ = ["Font", "Glyph", "FontReport", "analyze", "__version__"]
