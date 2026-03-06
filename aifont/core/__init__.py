"""AIFont core SDK — wraps fontforge Python bindings with a clean Pythonic API."""

from aifont.core.analyzer import FontAnalyzer, FontReport, analyze

__all__ = ["FontAnalyzer", "FontReport", "analyze"]
