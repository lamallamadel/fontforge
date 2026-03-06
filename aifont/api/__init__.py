"""aifont.api — FastAPI server exposing the AIFont SDK as a REST service."""

from .main import create_app

__all__ = ["create_app"]
