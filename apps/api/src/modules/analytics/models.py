"""ORM models for idempotent outbox consumption, learning events, and snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class ProcessedEventId(Base):
    """Idempotency ledger guaranteeing each outbox event is applied once per consumer."""

    __tablename__ = "processed_event_ids"

    consumer_name: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Normalized learning telemetry derived from practice & assessment mutations."""

    __tablename__ = "learning_events"
    __table_args__ = (Index("ix_learning_events_student_time", "student_id", "occurred_at"),)

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    metrics_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalyticsSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Pre-aggregated student/scope learning telemetry snapshots."""

    __tablename__ = "analytics_snapshots"

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(120), nullable=False)
    metrics_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
