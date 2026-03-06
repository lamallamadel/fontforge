"""aifont.utils.svg_parser — SVG import utilities (re-exported from core).

For the primary SVG parser implementation, see
:mod:`aifont.core.svg_parser`.  This module re-exports the public API
so that users can import from ``aifont.utils`` as documented.
"""

from aifont.core.svg_parser import (  # noqa: F401
    svg_to_glyph,
    svg_path_to_contours,
    _parse_transform,
    _apply_matrix,
    _tokenise_path,
    _parse_path_d,
)

__all__ = [
    "svg_to_glyph",
    "svg_path_to_contours",
]
