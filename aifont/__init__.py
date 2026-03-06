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
