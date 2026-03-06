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
