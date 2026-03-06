"""aifont.api — FastAPI server exposing the AIFont SDK as a REST service."""

from .main import create_app
"""AIFont REST API module."""
"""aifont.api — FastAPI REST server exposing AIFont SDK and agents."""
"""AIFont REST API — FastAPI server exposing the SDK and agents."""

from aifont.api.app import create_app

__all__ = ["create_app"]
