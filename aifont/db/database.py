"""Database connection and session management for AIFont."""

import os
from collections.abc import Generator
from contextlib import contextmanager

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
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    # Keep a small pool for API workloads; agents may spawn many tasks.
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # detect stale connections
    echo=os.environ.get("SQLALCHEMY_ECHO", "false").lower() == "true",
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal: sessionmaker = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ---------------------------------------------------------------------------
# Declarative base shared by all models
# ---------------------------------------------------------------------------
Base = declarative_base()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_session() -> Generator[Session, None, None]:
    """Yield a database session and guarantee clean-up.

    Intended for use as a FastAPI dependency or in ``with`` blocks::

        with get_session() as session:
            session.add(obj)
    """
    session: Session = SessionLocal()
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
