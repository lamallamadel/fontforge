"""aifont.api — FastAPI REST server exposing the AIFont SDK as a REST service."""

from aifont.api.app import create_app

__all__ = ["create_app"]
