"""
aifont — Pythonic SDK built on top of FontForge Python bindings.

AIFont provides a high-level, ergonomic API for font creation and manipulation.
All low-level operations are delegated to the underlying ``fontforge`` engine.

Architecture Constraint
-----------------------
FontForge is the underlying engine — DO NOT modify any FontForge source code.
AIFont is a Python SDK layer built ON TOP of FontForge via its Python bindings
(``import fontforge``).

Usage::

    from aifont.core.font import Font

    font = Font.open("MyFont.sfd")
    glyph = font.glyph("A")
    glyph.width = 600
    glyph.scale(1.2)
    print(glyph.to_svg())
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["core"]
