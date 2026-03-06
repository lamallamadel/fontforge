"""aifont.core — high-level Python wrappers around FontForge's Python bindings.

DO NOT import fontforge directly from user code — use this package instead.
All low-level font operations are delegated to fontforge internally.
"""

from aifont.core.metrics import Metrics

__all__ = ["Metrics"]
