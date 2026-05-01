"""Alembic environment.

We do NOT use the `sqlalchemy.url` from alembic.ini. Instead we read the active
configuration via `tallykeep.configuration.get_settings()`, which itself reads
TALLYKEEP_DATABASE_URL from the environment. This keeps a single source of truth and
avoids drift between Alembic and the running app.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from tallykeep.configuration import get_settings
from tallykeep.models import Base

# Alembic Config object — gives access to the values within the .ini file.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the runtime database URL so autogenerate and upgrade both use the same one.
# Tests may pre-set the URL via `cfg.set_main_option(...)` before invoking alembic
# programmatically — in that case we must NOT overwrite their value with the
# environment's URL.
if not config.get_main_option("sqlalchemy.url"):
    settings = get_settings()
    if settings.database_url:
        config.set_main_option("sqlalchemy.url", settings.database_url)

# Target metadata for autogenerate. Importing tallykeep.models above triggers
# registration of every Row class.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against an existing connection."""
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
