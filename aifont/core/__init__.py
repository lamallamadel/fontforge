"""
aifont.core — low-level SDK wrappers around FontForge Python bindings.

All modules in this sub-package wrap ``fontforge`` objects.  They never
contain business logic; that belongs in ``aifont.agents``.
"""

from __future__ import annotations

from aifont.core.font import Font
from aifont.core.glyph import Glyph

__all__ = ["Font", "Glyph"]
