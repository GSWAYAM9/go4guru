"""ORM models for Phase 3 Modular AI Tutor, Hybrid RAG, Cost Telemetry, Safety Review & Evals."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")
FloatArrayVariant = JSON().with_variant(ARRAY(Float), "postgresql")
TsvectorVariant = Text().with_variant(TSVECTOR(), "postgresql")


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Rights-cleared curriculum source document eligible for RAG chunking."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name="ck_knowledge_documents_status_valid",
        ),
        Index(
            "ix_knowledge_docs_filter",
            "status",
            "embedding_allowed",
            "grade_id",
            "subject_id",
            "language_code",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_sources.id", ondelete="RESTRICT"), nullable=False
    )
    license_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_licenses.id", ondelete="RESTRICT"), nullable=False
    )
    curriculum_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("curriculum_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    grade_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("grades.id", ondelete="SET NULL"), nullable=True
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    topic_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    concept_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'PUBLISHED'"), nullable=False
    )
    embedding_allowed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    attribution_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Hierarchy-preserving knowledge chunk indexed by PG18 FTS TSVECTOR and dense vector."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_doc_idx"),
        Index("ix_knowledge_chunks_fts", "fts_tsv", postgresql_using="gin"),
        Index("ix_knowledge_chunks_doc_lang", "document_id", "language_code"),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    hierarchy_path: Mapped[str] = mapped_column(String(512), nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vec: Mapped[list[float]] = mapped_column(FloatArrayVariant, nullable=False)
    fts_tsv: Mapped[str | None] = mapped_column(TsvectorVariant, nullable=True)
    token_estimate: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    metadata_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )


class AiSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persistent student-owned AI tutoring conversation session (Parent read denied)."""

    __tablename__ = "ai_sessions"
    __table_args__ = (
        CheckConstraint(
            "session_type IN ('tutor', 'doubt', 'lesson_companion', 'revision')",
            name="ck_ai_sessions_type_valid",
        ),
        Index("ix_ai_sessions_tenant_student", "tenant_id", "student_id", "created_at"),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    session_type: Mapped[str] = mapped_column(
        String(32), server_default=text("'tutor'"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    teaching_mode: Mapped[str] = mapped_column(
        String(32), server_default=text("'explain'"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    curriculum_context_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), server_default=text("'active'"), nullable=False)


class AiMessage(UUIDPrimaryKeyMixin, Base):
    """Ordered turn history carrying verification status, citations, model & prompt provenance."""

    __tablename__ = "ai_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'assistant', 'system_event')",
            name="ck_ai_messages_role_valid",
        ),
        CheckConstraint(
            "verification_status IN "
            "('verified', 'unverified', 'verification_failed', 'not_applicable')",
            name="ck_ai_messages_verif_valid",
        ),
        Index("ix_ai_messages_session_created", "ai_session_id", "created_at"),
    )

    ai_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(48), nullable=True)
    pedagogical_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spoiler_guard: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    citations_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, server_default=text("'[]'::jsonb"), nullable=False
    )
    follow_up_questions_jsonb: Mapped[list[str]] = mapped_column(
        JSONBVariant, server_default=text("'[]'::jsonb"), nullable=False
    )
    generated_practice_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, server_default=text("'[]'::jsonb"), nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(32), server_default=text("'not_applicable'"), nullable=False
    )
    verification_summary_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    provider_used: Mapped[str | None] = mapped_column(String(48), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(96), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    safety_verdict: Mapped[str] = mapped_column(
        String(24), server_default=text("'allow'"), nullable=False
    )
    tokens_in: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AiToolCall(UUIDPrimaryKeyMixin, Base):
    """Structured audit trail of tool executions (RAG, SymPy, Pint, Chem, Safety) per turn."""

    __tablename__ = "ai_tool_calls"
    __table_args__ = (Index("ix_ai_tool_calls_message", "ai_message_id"),)

    ai_message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    input_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    output_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    succeeded: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderRateCard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Configurable per-million token USD pricing table for live cost attribution."""

    __tablename__ = "provider_rate_cards"
    __table_args__ = (UniqueConstraint("provider", "model_id", name="uq_rate_card_provider_model"),)

    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    model_id: Mapped[str] = mapped_column(String(96), nullable=False)
    input_cost_per_1m_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    output_cost_per_1m_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class AiCostEvent(UUIDPrimaryKeyMixin, Base):
    """Granular per-call AI inference token, latency, and USD cost ledger."""

    __tablename__ = "ai_cost_events"
    __table_args__ = (Index("ix_ai_cost_events_user_created", "user_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    ai_session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_sessions.id", ondelete="SET NULL"), nullable=True
    )
    ai_message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_messages.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    model_id: Mapped[str] = mapped_column(String(96), nullable=False)
    task_type: Mapped[str] = mapped_column(String(48), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AiReviewQueueItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Human Academic Reviewer & Safety Escalation queue for flagged/unverified outputs."""

    __tablename__ = "ai_review_queue"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'edited_approved', 'rejected', 'escalated')",
            name="ck_ai_review_queue_status_valid",
        ),
        Index("ix_ai_review_queue_status", "status", "created_at"),
    )

    ai_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_sessions.id", ondelete="CASCADE"), nullable=False
    )
    ai_message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiEvalDataset(UUIDPrimaryKeyMixin, Base):
    """Versioned offline/regression golden evaluation dataset registry."""

    __tablename__ = "ai_eval_datasets"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_ai_eval_dataset_name_ver"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AiEvalRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Execution record for a regression evaluation suite run."""

    __tablename__ = "ai_eval_runs"

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_eval_datasets.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    model_id: Mapped[str] = mapped_column(String(96), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_items: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    metrics_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'completed'"), nullable=False
    )
    triggered_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AiEvalResult(UUIDPrimaryKeyMixin, Base):
    """Per-case evaluation result with deterministic score breakdown."""

    __tablename__ = "ai_eval_results"
    __table_args__ = (Index("ix_ai_eval_results_run", "eval_run_id"),)

    eval_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_eval_runs.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(80), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    scores_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
