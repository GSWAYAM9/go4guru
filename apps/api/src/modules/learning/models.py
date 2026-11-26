"""ORM models for Phase 5 Adaptive Concept Mastery, Misconceptions & Learning Paths."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class StudentConceptMastery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_concept_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "concept_id", name="uq_scm_student_concept"),
        Index("ix_scm_student_score", "student_id", "mastery_score"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    mastery_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default=text("0.00"), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default=text("0.00"), nullable=False
    )
    retention_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default=text("1.00"), nullable=False
    )
    independent_solve_ratio: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default=text("0.00"), nullable=False
    )
    transfer_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default=text("0.00"), nullable=False
    )
    improvement_slope: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default=text("0.50"), nullable=False
    )
    difficulty_weighted_accuracy: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default=text("0.00"), nullable=False
    )
    band: Mapped[str] = mapped_column(String(24), server_default=text("'novice'"), nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    last_practiced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_review_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mastery_breakdown_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False, default=dict
    )
    evidence_summary_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False, default=dict
    )


class StudentMisconception(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_misconceptions"
    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_misconceptions_severity"),
        Index("ix_sm_student_concept", "student_id", "concept_id", "resolved_at"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    misconception_code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(16), server_default=text("'medium'"), nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, server_default=text("1"), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningPath(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_paths"

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal_exam_track: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), server_default=text("'active'"), nullable=False)
    summary_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False, default=dict
    )


class LearningPathItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_path_items"

    learning_path_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_score: Mapped[float] = mapped_column(
        Float, server_default=text("50.0"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    target_metadata_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False, default=dict
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
