"""ORM models for Mentor Ecosystem (F-032)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.core.outbox import JSONBVariant


class MentorAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentor_assignments"
    __table_args__ = (
        UniqueConstraint("mentor_id", "student_id", name="uq_mentor_student"),
        Index("ix_mentor_assignments_mentor", "mentor_id", "status"),
        Index("ix_mentor_assignments_tenant", "tenant_id", "mentor_id"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
    assigned_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MentorGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentor_goals"
    __table_args__ = (Index("ix_mentor_goals_mentor_student", "mentor_id", "student_id"),)

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )


class MentorSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentor_sessions"
    __table_args__ = (Index("ix_mentor_sessions_mentor_student", "mentor_id", "student_id"),)

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(
        Integer, server_default=text("30"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'scheduled'"), nullable=False
    )
    summary_notes: Mapped[str] = mapped_column(Text, server_default=text("''"), nullable=False)
    recommendations_jsonb: Mapped[list[Any]] = mapped_column(
        JSONBVariant, default=list, nullable=False
    )


class MentorFollowUp(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentor_follow_ups"
    __table_args__ = (Index("ix_mentor_follow_ups_mentor_student", "mentor_id", "student_id"),)

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mentor_sessions.id", ondelete="SET NULL"), nullable=True
    )
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'open'"), nullable=False
    )
