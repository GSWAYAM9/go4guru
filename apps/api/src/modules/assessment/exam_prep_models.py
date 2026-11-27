"""ORM models for Phase 9: Examination Preparation Ecosystem."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class ExamSyllabusChapter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned syllabus & chapter weightage mapping per exam track with explicit audit status."""

    __tablename__ = "exam_syllabus_chapters"
    __table_args__ = (
        UniqueConstraint(
            "exam_track_id",
            "pattern_version_label",
            "chapter_id",
            name="uq_exam_syllabus_track_ver_chapter",
        ),
        Index("ix_exam_syllabus_track_ver", "exam_track_id", "pattern_version_label"),
    )

    exam_track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    pattern_version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    chapter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    weightage_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default=text("0.00"), nullable=False
    )
    expected_questions: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    priority_tier: Mapped[str] = mapped_column(
        String(24), server_default=text("'core'"), nullable=False
    )
    syllabus_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'included'"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    audited_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExamFormulaSheet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """High-yield exam formula revision entries with KaTeX LaTeX and rights attribution."""

    __tablename__ = "exam_formula_sheets"
    __table_args__ = (
        Index("ix_exam_formula_track_subject_chap", "exam_track_id", "subject_id", "chapter_id"),
    )

    exam_track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    chapter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    topic_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    formula_latex: Mapped[str] = mapped_column(Text, nullable=False)
    variables_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    when_to_use: Mapped[str] = mapped_column(Text, nullable=False)
    common_pitfall: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(16), server_default=text("'medium'"), nullable=False
    )
    is_high_yield: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    source_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    license_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'PUBLISHED'"), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class ExamRevisionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Student exam-specific revision plan linking weak chapters, formulas, and mock cadence."""

    __tablename__ = "exam_revision_plans"
    __table_args__ = (
        Index("ix_exam_revision_plans_student_track", "student_id", "exam_track_id"),
    )

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    exam_track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    exam_pattern_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exam_patterns.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_minutes: Mapped[int] = mapped_column(Integer, server_default=text("90"), nullable=False)
    focus_chapters_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    schedule_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
