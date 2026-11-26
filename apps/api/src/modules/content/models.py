"""ORM models for Content Sources and Content Licenses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContentSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Origin attribution classification for curriculum content and questions."""

    __tablename__ = "content_sources"

    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_category: Mapped[str] = mapped_column(String(40), nullable=False)
    official_url: Mapped[str | None] = mapped_column(String(512), nullable=True)


class ContentLicense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Explicit licensing rights and legal review approval record."""

    __tablename__ = "content_licenses"

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_sources.id", ondelete="CASCADE"), nullable=False
    )
    license_name: Mapped[str] = mapped_column(String(160), nullable=False)
    commercial_use_allowed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    distribution_allowed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    hosting_allowed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    embedding_allowed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    attribution_required: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    attribution_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    territory: Mapped[str] = mapped_column(String(64), server_default=text("'IN'"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legal_review_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
