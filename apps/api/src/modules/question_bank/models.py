"""ORM models for Canonical Question Bank, Versioning, Provenance, and Import Staging."""

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (Index("ix_import_batches_sha256", "file_sha256"),)

    uploaded_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    file_format: Mapped[str] = mapped_column(String(16), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'uploaded'"), nullable=False
    )
    detected_sheets_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    selected_sheet: Mapped[str | None] = mapped_column(String(128), nullable=True)
    column_mapping_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    total_rows: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    warning_rows: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    error_rows: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    report_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_canonical_hash", "canonical_hash"),
        Index("ix_questions_status", "status"),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    canonical_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), server_default=text("'DRAFT'"), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    import_batch_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)


class QuestionVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_versions"
    __table_args__ = (
        UniqueConstraint("question_id", "version_no", name="uq_question_versions_question_version"),
        Index(
            "ix_question_versions_curriculum_facets",
            "grade_id",
            "subject_id",
            "chapter_id",
            "topic_id",
            "concept_id",
        ),
    )

    question_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    curriculum_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    grade_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    chapter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    topic_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    learning_objective_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    stem_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    passage_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    answer_schema_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    correct_answer_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )
    difficulty: Mapped[str] = mapped_column(
        String(16), server_default=text("'medium'"), nullable=False
    )
    default_marks: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), server_default=text("4.00"), nullable=False
    )
    default_negative_marks: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), server_default=text("0.00"), nullable=False
    )
    estimated_seconds: Mapped[int] = mapped_column(
        Integer, server_default=text("60"), nullable=False
    )
    cognitive_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    competency_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_generated: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    ai_metadata_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, nullable=False, default=dict
    )


class QuestionOption(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint(
            "question_version_id", "option_key", name="uq_question_options_version_key"
        ),
    )

    question_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=False
    )
    option_key: Mapped[str] = mapped_column(String(16), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    media_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    match_pair_key: Mapped[str | None] = mapped_column(String(32), nullable=True)


class QuestionSolution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "question_solutions"

    question_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    solution_type: Mapped[str] = mapped_column(
        String(16), server_default=text("'primary'"), nullable=False
    )
    explanation_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    steps_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)
    common_mistakes_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    misconception_tags_jsonb: Mapped[list[str]] = mapped_column(
        JSONBVariant, nullable=False, default=list
    )
    rubric_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False, default=dict)


class QuestionHint(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "question_hints"
    __table_args__ = (
        UniqueConstraint(
            "question_version_id", "hint_level", name="uq_question_hints_version_level"
        ),
    )

    question_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=False
    )
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_markdown: Mapped[str] = mapped_column(Text, nullable=False)


class QuestionProvenance(Base):
    __tablename__ = "question_provenance"

    question_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    license_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_pyq: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    exam_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    exam_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_session: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exam_shift: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paper_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'unverified'"), nullable=False
    )
    verified_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuestionReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_reviews"

    question_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("question_versions.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportStagingRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_staging_rows"
    __table_args__ = (
        Index("ix_import_staging_rows_batch_status", "import_batch_id", "validation_status"),
    )

    import_batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False)
    normalized_payload_jsonb: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBVariant, nullable=True
    )
    row_fingerprint_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validation_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    errors_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)
    warnings_jsonb: Mapped[list[str]] = mapped_column(JSONBVariant, nullable=False, default=list)
    created_question_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
    )
