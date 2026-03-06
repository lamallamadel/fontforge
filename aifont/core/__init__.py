"""
aifont.core — high-level Python wrappers around FontForge bindings.

DO NOT import fontforge directly from user code — use this package instead.
"""
"""AIFont core SDK — Python wrappers around FontForge's Python bindings."""
"""AIFont core SDK — high-level wrappers around FontForge's Python bindings."""

from aifont.core.export import (
    export_otf,
    export_ttf,
    export_woff2,
    export_variable,
    subset_font,
    export_woff,
    export_woff2,
    export_ufo,
    export_svg,
    export_all,
    ExportOptions,
)

__all__ = [
    "export_otf",
    "export_ttf",
    "export_woff2",
    "export_variable",
    "subset_font",
    "export_woff",
    "export_woff2",
    "export_ufo",
    "export_svg",
    "export_all",
    "ExportOptions",
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
