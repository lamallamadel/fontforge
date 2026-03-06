"""
aifont.utils.font_analyzer — Re-export of :mod:`aifont.core.analyzer`.

This module exists for convenience so that users can also import font
analysis utilities from ``aifont.utils``.
"""

from aifont.core.analyzer import analyze, FontReport, GlyphIssue  # noqa: F401

__all__ = ["analyze", "FontReport", "GlyphIssue"]
