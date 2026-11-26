"""ORM models for Phase 1 Practice Engine & Phase 2 Quiz/Assessment Engine."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
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


class PracticeSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (Index("ix_practice_sessions_student", "student_id", "started_at"),)

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    chapter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    topic_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    mode: Mapped[str] = mapped_column(
        String(32), server_default=text("'guided_practice'"), nullable=False
    )
    question_ids_jsonb: Mapped[list[str]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    hints_revealed_jsonb: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuestionAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_attempts"
    __table_args__ = (Index("ix_question_attempts_student_time", "student_id", "attempted_at"),)

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    question_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    question_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    practice_session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("practice_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    response_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score_awarded: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), server_default=text("0.00"), nullable=False
    )
    hints_used_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_notes"
    __table_args__ = (Index("ix_student_notes_student", "student_id", "updated_at"),)

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    question_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)


class SavedQuestion(TimestampMixin, Base):
    __tablename__ = "saved_questions"

    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    question_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    folder_name: Mapped[str] = mapped_column(
        String(80), server_default=text("'General'"), nullable=False
    )


# ----------------------------------------------------------------------
# Phase 2 ORM Models: Exam Patterns, Quizzes, Assessments & Attempts
# ----------------------------------------------------------------------
class ExamPattern(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exam_patterns"
    __table_args__ = (
        UniqueConstraint("exam_track_id", "version_label", name="uq_exam_patterns_track_version"),
    )

    exam_track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    rules_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False, default=dict)


class Quiz(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quizzes"
    __table_args__ = (Index("ix_quizzes_creator_type", "created_by", "quiz_type"),)

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    quiz_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    exam_pattern_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exam_patterns.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    chapter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    topic_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    config_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False, default=dict)
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'PUBLISHED'"), nullable=False
    )


class QuizQuestion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("quiz_id", "sequence_no", name="uq_quiz_questions_seq"),)

    quiz_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    question_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    marks_override: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    negative_marks_override: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)


class AssessmentTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tests"

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    exam_pattern_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exam_patterns.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_category: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grace_seconds: Mapped[int] = mapped_column(Integer, server_default=text("30"), nullable=False)
    total_marks: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), server_default=text("0.00"), nullable=False
    )
    retake_policy_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    shuffle_questions: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    shuffle_options: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), server_default=text("'DRAFT'"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TestSection(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "test_sections"
    __table_args__ = (UniqueConstraint("test_id", "sequence_no", name="uq_test_sections_seq"),)

    test_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    marking_rule_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TestQuestion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "test_questions"
    __table_args__ = (
        UniqueConstraint("section_id", "sequence_no", name="uq_test_questions_section_seq"),
    )

    test_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_sections.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    question_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    marks_override: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    negative_marks_override: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)


class AssessmentAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (Index("ix_assessment_attempts_student_started", "student_id", "started_at"),)

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    test_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tests.id", ondelete="RESTRICT"), nullable=True
    )
    quiz_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("quizzes.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'in_progress'"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_idempotency_key: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    seed: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    question_order_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    raw_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    max_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    accuracy_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    result_summary_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )


class AttemptAnswer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_version_id", name="uq_attempt_answers_att_qv"),
    )

    attempt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    section_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    response_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    is_visited: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    is_marked_for_review: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    time_spent_seconds: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    marks_awarded: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    last_saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
