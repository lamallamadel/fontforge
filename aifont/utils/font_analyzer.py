"""
aifont.utils.font_analyzer — font analysis utilities (re-exported from core).

For the primary analyzer implementation, see :mod:`aifont.core.analyzer`.
This module re-exports the public API so that users can import from
``aifont.utils`` as documented in the issue structure.
"""

from aifont.core.analyzer import FontAnalyzer, FontReport, analyze  # noqa: F401

__all__ = ["FontAnalyzer", "FontReport", "analyze"]
aifont.utils.font_analyzer — Re-export of :mod:`aifont.core.analyzer`.

This module exists for convenience so that users can also import font
analysis utilities from ``aifont.utils``.
"""

from aifont.core.analyzer import analyze, FontReport, GlyphIssue  # noqa: F401

__all__ = ["analyze", "FontReport", "GlyphIssue"]
