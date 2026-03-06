"""AIFont core — high-level wrappers around FontForge's Python bindings."""

from aifont.core.font import AIFont
from aifont.core.glyph import Glyph

__all__ = ["AIFont", "Glyph"]
"""
aifont.core — Core SDK for font and glyph manipulation.

Modules
-------
font     : Font wrapper around ``fontforge.font``.
glyph    : Glyph wrapper around ``fontforge.glyph``.
"""aifont.core — Python wrappers around FontForge Python bindings.

DO NOT import fontforge directly from user code — use this sub-package.
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
"""
aifont.core — Core SDK modules for FontForge wrapping.

Exposes the primary classes and functions used to interact with fonts
through the high-level AIFont API.
"""

from .font import Font
from .glyph import Glyph
from .metrics import get_kern_pairs, set_kern, auto_space
from .contour import simplify, remove_overlap, transform
from .export import export_otf, export_ttf, export_woff2, export_ufo
from .svg_parser import svg_to_glyph
from .analyzer import analyze, FontReport
"""AIFont core SDK — high-level wrappers around FontForge Python bindings."""

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import get_kern_pairs, set_kern, auto_space
from aifont.core.analyzer import analyze

__all__ = ["Font", "Glyph", "get_kern_pairs", "set_kern", "auto_space", "analyze"]
"""
aifont.core — low-level SDK wrappers around FontForge Python bindings.

All modules in this sub-package wrap ``fontforge`` objects.  They never
contain business logic; that belongs in ``aifont.agents``.
"""

from __future__ import annotations

from aifont.core.font import Font
from aifont.core.glyph import Glyph

__all__ = ["Font", "Glyph"]
"""aifont.core — high-level Python wrappers around FontForge's Python bindings.

DO NOT import fontforge directly from user code — use this package instead.
All low-level font operations are delegated to fontforge internally.
"""

from aifont.core.metrics import Metrics

__all__ = ["Metrics"]
"""aifont.core — low-level wrappers around FontForge Python bindings."""
"""AIFont core — high-level wrappers around FontForge Python bindings."""

from aifont.core.analyzer import analyze
from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.metrics import auto_space, get_kern_pairs, set_kern
"""AIFont core SDK — wraps fontforge Python bindings with a clean Pythonic API."""

from aifont.core.analyzer import FontAnalyzer, FontReport, analyze

__all__ = ["FontAnalyzer", "FontReport", "analyze"]
"""
aifont.core — low-level Python wrappers around FontForge bindings.
"""

from aifont.core.font import Font
from aifont.core.glyph import Glyph
from aifont.core.contour import simplify, remove_overlap, correct_directions, transform
from aifont.core.analyzer import analyze, FontReport

__all__ = [
    "Font",
    "Glyph",
    "get_kern_pairs",
    "set_kern",
    "auto_space",
    "simplify",
    "remove_overlap",
    "transform",
    "export_otf",
    "export_ttf",
    "export_woff2",
    "export_ufo",
    "svg_to_glyph",
    "analyze",
    "FontReport",
    "analyze",
    "simplify",
    "remove_overlap",
    "correct_directions",
    "transform",
    "analyze",
    "FontReport",
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
