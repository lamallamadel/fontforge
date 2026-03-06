"""
aifont.core — Core SDK for font and glyph manipulation.

Modules
-------
font     : Font wrapper around ``fontforge.font``.
glyph    : Glyph wrapper around ``fontforge.glyph``.
"""

from __future__ import annotations

from aifont.core.font import Font
from aifont.core.glyph import Glyph

__all__ = ["Font", "Glyph"]
