"""Alembic migration environment for AIFont.

This file is invoked by Alembic on every ``alembic`` CLI command.  It
configures the engine URL (from the ``DATABASE_URL`` environment variable,
with a fallback to the value in ``alembic.ini``), imports all SQLAlchemy
models so that autogenerate can detect schema changes, and drives both
*offline* (SQL-script) and *online* (live database) migration modes.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Import all models so that Base.metadata is fully populated before Alembic
# inspects it for autogenerate.
# ---------------------------------------------------------------------------
from aifont.db.database import Base  # noqa: F401 — registers metadata
import aifont.db.models  # noqa: F401 — side-effect: populate Base.metadata

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Override the SQLAlchemy URL with the DATABASE_URL env var when present.
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object for 'autogenerate' support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration: emit raw SQL without connecting to the database
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL (not a live connection) and emits
    migration SQL to stdout / a file.  Useful for review or production
    deployment via SQL scripts.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Emit ``BEGIN``/``COMMIT`` around each migration step.
        transaction_per_migration=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration: connect to the real database and apply migrations
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # Detect added/removed server defaults
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
