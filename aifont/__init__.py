"""AIFont — Python SDK and AI agent layer built on top of FontForge.

DO NOT import fontforge here directly; let each sub-module handle it
so that the package can be imported for tooling purposes without a live
FontForge installation (e.g. linting, unit tests with mocks).
"""

__version__ = "0.1.0"
__all__ = ["core", "agents", "api"]
