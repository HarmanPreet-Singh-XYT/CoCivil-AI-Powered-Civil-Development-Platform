"""
alembic_users/env.py

Alembic migration environment for the USERS / BILLING database.
This file tells Alembic:
  - which database URL to connect to
  - which SQLAlchemy models to inspect for autogenerate

IMPORTANT: This env.py imports UsersBase (not the main app Base).
That means running:
    alembic -c alembic_users.ini revision --autogenerate
will ONLY detect changes to models in app/models/users_db.py.
It will never touch or see the main app database tables.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Make `app` importable when alembic runs from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings

# Import ONLY UsersBase — scopes autogenerate to the users DB models.
# Never import the main app Base here.
from app.models.users_db import UsersBase

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate diffs against UsersBase metadata only
target_metadata = UsersBase.metadata

# Pull real URL from settings/.env — credentials never hardcoded in .ini
config.set_main_option("sqlalchemy.url", settings.USERS_DATABASE_URL)


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()