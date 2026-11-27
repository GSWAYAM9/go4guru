"""SQLAlchemy ORM models for Phase 6 Homework AI (F-029)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.core.outbox import JSONBVariant


class HomeworkSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Student homework submission container supporting multi-page images/PDFs and retries."""

    __tablename__ = "homework_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'ocr_processing', 'needs_review', 'analyzing', "
            "'feedback_ready', 'retry_pending', 'completed', 'failed')",
            name="ck_hw_submissions_status",
        ),
        CheckConstraint(
            "selected_subject IN ('auto', 'mathematics', 'physics', 'chemistry', "
            "'english', 'social_science')",
            name="ck_hw_submissions_subject",
        ),
        Index("ix_hw_submissions_student_created", "student_id", "created_at"),
        Index("ix_hw_submissions_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    concept_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    selected_subject: Mapped[str] = mapped_column(String(40), nullable=False, default="auto")
    detected_subject: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subject_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    language_code: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_ocr_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )


class HomeworkFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable sanitized file record stored outside webroot in private storage."""

    __tablename__ = "homework_files"
    __table_args__ = (
        CheckConstraint(
            "scan_status IN ('pending', 'clean', 'rejected')",
            name="ck_hw_files_scan_status",
        ),
        CheckConstraint("page_no >= 1", name="ck_hw_files_page_no"),
        UniqueConstraint("submission_id", "page_no", name="uq_hw_files_submission_page"),
        Index("ix_hw_files_submission", "submission_id", "page_no"),
    )

    submission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("homework_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_format: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    exif_stripped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pdf_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scan_status: Mapped[str] = mapped_column(String(24), nullable=False, default="clean")
    validation_metadata_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )


class HomeworkOcrResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-page OCR and handwriting extraction output with student correction override."""

    __tablename__ = "homework_ocr_results"
    __table_args__ = (
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_hw_ocr_confidence"),
        UniqueConstraint("submission_id", "page_no", name="uq_hw_ocr_submission_page"),
    )

    submission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("homework_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("homework_files.id", ondelete="SET NULL"), nullable=True
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_latex: Mapped[str | None] = mapped_column(Text, nullable=True)
    handwriting_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    handwriting_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    student_corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)
    raw_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False, default=dict)


class HomeworkEvaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Attempt-versioned subject-aware step evaluation, graduated hints & retry tracking."""

    __tablename__ = "homework_evaluations"
    __table_args__ = (
        CheckConstraint(
            "subject_area IN ('mathematics', 'physics', 'chemistry', 'english', 'social_science')",
            name="ck_hw_eval_subject",
        ),
        CheckConstraint(
            "overall_status IN ('correct', 'partially_correct', "
            "'needs_correction', 'unreadable_or_uncertain')",
            name="ck_hw_eval_status",
        ),
        CheckConstraint(
            "current_hint_level_unlocked >= 0 AND current_hint_level_unlocked <= 3",
            name="ck_hw_eval_hint_level",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_hw_eval_confidence"),
        UniqueConstraint("submission_id", "attempt_no", name="uq_hw_eval_submission_attempt"),
        Index("ix_hw_eval_submission_attempt", "submission_id", "attempt_no"),
    )

    submission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("homework_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    subject_area: Mapped[str] = mapped_column(String(40), nullable=False)
    detected_question: Mapped[str] = mapped_column(Text, nullable=False)
    student_work_summary: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_steps_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    step_evaluations_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    error_classifications_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    overall_status: Mapped[str] = mapped_column(String(32), nullable=False)
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)
    hints_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    current_hint_level_unlocked: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    solution_revealed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    complete_solution_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    verifier_results_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    validation_report_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    revision_recommendations_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_band: Mapped[str] = mapped_column(String(24), nullable=False, default="medium")
    provider_used: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    safety_verdict: Mapped[str] = mapped_column(String(32), nullable=False, default="allow")
    teacher_override_jsonb: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBVariant, nullable=True
    )
