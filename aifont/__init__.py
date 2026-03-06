"""AIFont — Python SDK and AI agent layer built on top of FontForge."""

__version__ = "0.1.0"

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.analyzer import FontReport, analyze

__all__ = ["Font", "Glyph", "FontReport", "analyze", "__version__"]
"""
AIFont — a Pythonic SDK built on top of FontForge's Python bindings.

Usage::

    from aifont import AIFont

    font = AIFont.create("MyFont", family="Sans-Serif")
    font.save("output.sfd")
"""

from aifont.core.font import AIFont

__all__ = ["AIFont"]
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
"""AIFont — Python SDK built on top of FontForge Python bindings.

FontForge is the underlying engine. DO NOT modify any FontForge source code.
This package wraps FontForge via ``import fontforge`` only.
"""

from aifont.core.font import Font
from aifont.core.variable import (
    VariationAxis,
    NamedInstance,
    Master,
    VariableFontBuilder,
)

__all__ = [
    "Font",
    "VariationAxis",
    "NamedInstance",
    "Master",
    "VariableFontBuilder",
]
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
"""AIFont — AI-powered font design SDK built on top of FontForge."""

__version__ = "0.1.0"
__author__ = "AIFont Contributors"

from aifont.core.font import Font
from aifont.core.glyph import Glyph

__all__ = ["Font", "Glyph", "__version__"]
"""
aifont — AI-powered font SDK built on top of FontForge.

This package provides a high-level Python API for font manipulation and
AI-driven font agents.  FontForge is used as a black-box backend via its
Python bindings (``import fontforge``).  No FontForge source code is
modified.

Sub-packages
------------
aifont.core
    Low-level wrappers around fontforge objects (Font, Glyph, contours,
    analysis).
aifont.agents
    High-level AI agents that orchestrate font design tasks by calling
    only ``aifont.core`` APIs.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["core"]
__all__ = ["__version__"]
"""AIFont — Python SDK built on top of FontForge."""
"""
AIFont — Python SDK and AI agent layer built on top of FontForge.

FontForge is the underlying engine. All font operations are delegated
to FontForge via its Python bindings (``import fontforge``).
FontForge source code is never modified; this package wraps it as a
black-box engine.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["core", "utils"]
from importlib.metadata import PackageNotFoundError, version
"""AIFont — Python SDK built on top of FontForge."""
"""AIFont — Python SDK + AI agent layer built on top of FontForge."""
"""AIFont — Python SDK built on top of FontForge."""
"""AIFont — Python SDK and AI agent layer built on top of FontForge.

DO NOT import fontforge here directly; let each sub-module handle it
so that the package can be imported for tooling purposes without a live
FontForge installation (e.g. linting, unit tests with mocks).
"""

__version__ = "0.1.0"
__all__ = ["core", "agents", "api"]
"""AIFont — AI-powered font design SDK built on top of FontForge."""
"""AIFont — Python SDK built on top of FontForge's Python bindings."""
"""
AIFont — Python SDK and AI agent layer built on top of FontForge.

All font operations delegate to the FontForge Python bindings (``import fontforge``).
FontForge source code is never modified; this package wraps it as a black-box engine.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("aifont")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["core"]
__all__ = ["core", "agents"]
AIFont — Python SDK + AI agent layer built on top of FontForge.

FontForge is the underlying engine. All font operations are delegated
to FontForge via its Python bindings (``import fontforge``).
"""
"""AIFont — AI-powered font SDK built on top of FontForge."""

__version__ = "0.1.0"
