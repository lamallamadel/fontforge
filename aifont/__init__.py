"""AIFont — Python SDK + AI agent layer built on top of FontForge."""
"""AIFont — Python SDK built on top of FontForge."""
"""AIFont — Python SDK and AI agent layer built on top of FontForge.

DO NOT import fontforge here directly; let each sub-module handle it
so that the package can be imported for tooling purposes without a live
FontForge installation (e.g. linting, unit tests with mocks).
"""

__version__ = "0.1.0"
__all__ = ["core", "agents", "api"]
"""AIFont — AI-powered font design SDK built on top of FontForge."""
"""AIFont — Python SDK built on top of FontForge's Python bindings."""
"""
AIFont — Python SDK and AI agent layer built on top of FontForge.

All font operations delegate to the FontForge Python bindings (``import fontforge``).
FontForge source code is never modified; this package wraps it as a black-box engine.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("aifont")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["core", "agents"]
AIFont — Python SDK + AI agent layer built on top of FontForge.

FontForge is the underlying engine. All font operations are delegated
to FontForge via its Python bindings (``import fontforge``).
"""
"""AIFont — AI-powered font SDK built on top of FontForge."""

__version__ = "0.1.0"
