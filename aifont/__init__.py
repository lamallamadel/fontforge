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
__all__ = ["__version__"]
