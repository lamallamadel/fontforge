"""
aifont.utils.svg_parser — Re-export of :mod:`aifont.core.svg_parser`.

This module exists for convenience so that users can also import SVG
utilities from ``aifont.utils``.
"""

from aifont.core.svg_parser import svg_to_glyph, svg_path_to_contours  # noqa: F401

__all__ = ["svg_to_glyph", "svg_path_to_contours"]
