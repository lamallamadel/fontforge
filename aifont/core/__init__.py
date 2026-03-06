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
]
