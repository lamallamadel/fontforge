"""
AIFont — A Pythonic SDK built on top of FontForge.

This package provides high-level wrappers and utilities around FontForge's
Python bindings, enabling clean programmatic font creation and manipulation.

Modules
-------
aifont.core.font        — Font class, open/save/iterate glyphs
aifont.core.glyph       — Glyph wrapper, contours, metrics
aifont.core.metrics     — Kerning and spacing utilities
aifont.core.contour     — Bézier curve/path manipulation
aifont.core.export      — Export to OTF, TTF, WOFF2, UFO
aifont.core.svg_parser  — Import SVG paths as glyphs
aifont.core.analyzer    — Font diagnostics and reporting

Usage
-----
    from aifont.core.font import Font

    font = Font.open("MyFont.otf")
    for glyph in font.glyphs:
        print(glyph.name, glyph.width)
    font.save("out/MyFont.otf")
"""

from .core.font import Font
from .core.glyph import Glyph
from .core.metrics import get_kern_pairs, set_kern, auto_space
from .core.export import export_otf, export_ttf, export_woff2, export_ufo
from .core.analyzer import analyze

__all__ = [
    "Font",
    "Glyph",
    "get_kern_pairs",
    "set_kern",
    "auto_space",
    "export_otf",
    "export_ttf",
    "export_woff2",
    "export_ufo",
    "analyze",
]

__version__ = "0.1.0"
