"""ORM models for guardian linking, verifiable consent, and parent goals (F-004, F-033)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.core.outbox import JSONBVariant


class GuardianLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Verifiable parent/guardian link to a student account with privacy controls."""

    __tablename__ = "guardian_links"
    __table_args__ = (
        UniqueConstraint("parent_user_id", "student_user_id", name="uq_guardian_parent_student"),
        Index("ix_guardian_links_parent", "parent_user_id", "consent_status"),
        Index("ix_guardian_links_student", "student_user_id", "consent_status"),
    )

    parent_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String(32), server_default=text("'parent'"), nullable=False
    )
    consent_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    verification_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    consent_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    privacy_settings_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant,
        nullable=False,
        default=lambda: {
            "share_learning_summary": True,
            "share_weak_topics": True,
            "share_upcoming_tests": True,
            "allow_raw_ai_transcripts": False,
        },
    )


class ParentGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Collaborative study goal created by a verified parent/guardian for a linked student."""

    __tablename__ = "parent_goals"
    __table_args__ = (
        Index("ix_parent_goals_parent_student", "parent_user_id", "student_user_id"),
    )

    parent_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_minutes_per_day: Mapped[int] = mapped_column(
        Integer, server_default=text("45"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
