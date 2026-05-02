"""
Alembic environment configuration for async database migrations.

This module configures Alembic to work with async SQLAlchemy and asyncpg
for PostgreSQL database migrations.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from grins_platform.database import Base, DatabaseSettings

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# Import all models here so they are registered with Base.metadata
from grins_platform.models import Customer, Property  # noqa: F401

target_metadata = Base.metadata

# Load database URL from environment
db_settings = DatabaseSettings()


# Hosts that look like the Railway-managed Postgres for this project.
# Running alembic against these from a developer workstation has caused
# the deployed DB to advance to a never-committed revision and crash-loop
# the container on the next push (incident: 2026-05-02). Inside the
# Railway container itself ``RAILWAY_ENVIRONMENT`` is set, which bypasses
# the guard so deploys keep working.
_REMOTE_HOST_FRAGMENTS = (
    ".railway.app",
    ".railway.internal",
    ".up.railway.app",
)


def _is_remote_host(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return any(fragment in host for fragment in _REMOTE_HOST_FRAGMENTS)


def _guard_against_remote_db(url: str) -> None:
    """Refuse to run alembic against a Railway-hosted DB from outside the container.

    Override with ``ALEMBIC_ALLOW_REMOTE=1`` if you genuinely intend to
    run a migration against the deployed DB (rare — the normal path is
    ``git push origin <branch>`` and let Railway run it on container start).
    """
    if not _is_remote_host(url):
        return
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return
    if os.environ.get("ALEMBIC_ALLOW_REMOTE") == "1":
        return
    host = urlparse(url).hostname
    sys.stderr.write(
        "\n[alembic env.py] Refusing to run against remote DB host "
        f"{host!r}.\n"
        "  Migrations should be applied by the deployed Railway container,\n"
        "  not from a developer workstation. Push the migration to its\n"
        "  branch and Railway will apply it on the next container start.\n"
        "  If you really mean it, re-run with ALEMBIC_ALLOW_REMOTE=1.\n\n",
    )
    raise SystemExit(2)


def get_url() -> str:
    """Get the database URL from settings."""
    url = db_settings.async_database_url
    _guard_against_remote_db(url)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
