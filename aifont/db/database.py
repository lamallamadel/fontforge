"""Database connection and session management for AIFont."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Connection URL
# ---------------------------------------------------------------------------
# Defaults to a local dev database; override via DATABASE_URL environment
# variable in all other environments.
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://aifont:aifont@localhost:5432/aifont",
)

# ---------------------------------------------------------------------------
# Declarative base shared by all models
# ---------------------------------------------------------------------------
Base = declarative_base()

# ---------------------------------------------------------------------------
# Lazy engine / session factory
# ---------------------------------------------------------------------------
# Engine and session factory are created on first access to avoid requiring
# a running database (or the psycopg2 driver) at import time.

_engine: Any = None
_SessionLocal: Any = None


def _get_engine() -> Any:
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=os.environ.get("SQLALCHEMY_ECHO", "false").lower() == "true",
        )
    return _engine


def _get_session_local() -> Any:
    global _SessionLocal  # noqa: PLW0603
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


# Public aliases that trigger lazy initialisation
class _LazyEngine:
    """Proxy that initialises the SQLAlchemy engine on first attribute access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_engine(), name)

    def __repr__(self) -> str:
        return repr(_get_engine())


class _LazySessionMaker:
    """Proxy that initialises the session factory on first call/attribute access."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return _get_session_local()(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_session_local(), name)


engine = _LazyEngine()
SessionLocal = _LazySessionMaker()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_session() -> Generator[Session, None, None]:
    """Yield a database session and guarantee clean-up.

    Intended for use as a FastAPI dependency or in ``with`` blocks::

        with get_session() as session:
            session.add(obj)
    """
    session: Session = _get_session_local()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Alias so callers can write ``with get_session() as db:``
get_session = contextmanager(get_session)
