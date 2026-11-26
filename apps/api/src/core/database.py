"""Async SQLAlchemy 2.0 database engine, Base metadata, and readiness helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import Settings, get_settings

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base with deterministic constraint naming for Alembic."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Standard UTC timestamptz columns required on all relational tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key generated server-side in PostgreSQL 18."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def create_db_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create the async SQLAlchemy engine configured for PostgreSQL 18."""
    cfg = settings or get_settings()
    connect_args: dict[str, Any] = {}
    if cfg.database_url.startswith("postgresql+asyncpg"):
        connect_args["timeout"] = cfg.database_connect_timeout_seconds
    return create_async_engine(
        cfg.database_url,
        echo=cfg.database_echo,
        pool_size=cfg.database_pool_size,
        max_overflow=cfg.database_max_overflow,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


class DatabaseManager:
    """Lifecycle wrapper owning the async engine and session factory."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.engine: AsyncEngine = create_db_engine(self.settings)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    async def check_connectivity(self) -> tuple[bool, str | None]:
        """Run a lightweight SELECT 1 check without faking health on error."""
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, None
        except Exception as exc:
            return False, exc.__class__.__name__

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield an async database session with clean close."""
        async with self.session_factory() as db_session:
            yield db_session

    async def dispose(self) -> None:
        """Dispose pooled DB connections during graceful shutdown."""
        await self.engine.dispose()
