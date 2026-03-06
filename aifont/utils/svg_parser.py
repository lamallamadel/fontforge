"""
aifont.utils.svg_parser — SVG import utilities (re-exported from core).

For the primary SVG parser implementation, see
:mod:`aifont.core.svg_parser`.  This module re-exports the public API
so that users can import from ``aifont.utils`` as documented in the
issue structure.
"""

from aifont.core.svg_parser import svg_to_glyph  # noqa: F401

__all__ = ["svg_to_glyph"]
