"""aifont.core — low-level wrappers around FontForge Python bindings."""

from .contour import (
    ContourPoint,
    Contour,
    simplify,
    smooth_transitions,
    reverse_direction,
    remove_overlap,
    transform,
    to_svg_path,
)

__all__ = [
    "ContourPoint",
    "Contour",
    "simplify",
    "smooth_transitions",
    "reverse_direction",
    "remove_overlap",
    "transform",
    "to_svg_path",
]
