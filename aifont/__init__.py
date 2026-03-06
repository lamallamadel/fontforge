"""AIFont — Python SDK built on top of FontForge Python bindings.

FontForge is the underlying engine. DO NOT modify any FontForge source code.
This package wraps FontForge via ``import fontforge`` only.
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
