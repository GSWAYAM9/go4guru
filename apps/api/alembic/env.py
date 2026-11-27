"""Alembic async migration environment for PostgreSQL 18."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from src.core import outbox  # noqa: F401 — registers foundation ORM models on Base.metadata
from src.core.config import get_settings
from src.core.database import Base
from src.modules.ai import models as _ai_models  # noqa: F401
from src.modules.analytics import models as _analytics_models  # noqa: F401
from src.modules.assessment import exam_prep_models as _exam_prep_models  # noqa: F401
from src.modules.assessment import models as _assessment_models  # noqa: F401
from src.modules.billing import models as _billing_models  # noqa: F401
from src.modules.classroom import models as _classroom_models  # noqa: F401
from src.modules.classroom import multilingual_models as _multilingual_models  # noqa: F401
from src.modules.content import models as _content_models  # noqa: F401
from src.modules.curriculum import models as _curriculum_models  # noqa: F401
from src.modules.homework import models as _homework_models  # noqa: F401
from src.modules.identity import models as _identity_models  # noqa: F401
from src.modules.identity import parent_models as _parent_models  # noqa: F401
from src.modules.learning import models as _learning_models  # noqa: F401
from src.modules.mentor import models as _mentor_models  # noqa: F401
from src.modules.notifications import models as _notifications_models  # noqa: F401
from src.modules.organization import models as _organization_models  # noqa: F401
from src.modules.question_bank import models as _question_bank_models  # noqa: F401
from src.modules.revision import models as _revision_models  # noqa: F401
from src.modules.teacher import models as _teacher_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Resolve database URL from Alembic config override or typed settings."""
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode emitting PostgreSQL DDL without a live socket."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations synchronously against the provided connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run online migrations."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entrypoint for online migration execution."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
