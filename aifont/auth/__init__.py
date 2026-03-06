"""AIFont authentication and user management module."""

__all__ = ["router"]


def __getattr__(name: str) -> object:  # noqa: N807 — module-level __getattr__
    if name == "router":
        from .router import router  # lazy import avoids sqlalchemy at import time

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
