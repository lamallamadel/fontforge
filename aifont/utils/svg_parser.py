"""aifont.utils.svg_parser — SVG import utilities (re-exported from core).

For the primary SVG parser implementation, see
:mod:`aifont.core.svg_parser`.  This module re-exports the public API
so that users can import from ``aifont.utils`` as documented.
"""

from aifont.core.svg_parser import (  # noqa: F401
    _apply_matrix,
    _parse_path_d,
    _parse_transform,
    _tokenise_path,
    svg_path_to_contours,
    svg_to_glyph,
)

__all__ = [
    "svg_to_glyph",
    "svg_path_to_contours",
]
