"""ORM models for Phase 4 Live AI Classroom, Synchronized Whiteboard & ElevenLabs Voice."""

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class LanguageCapability(TimestampMixin, Base):
    """Empirical Language Capability Registry governing truthful UI/TTS/STT options."""

    __tablename__ = "language_capabilities"

    language_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    native_name: Mapped[str] = mapped_column(String(64), nullable=False)
    script_name: Mapped[str] = mapped_column(
        String(32), server_default=text("'Latin'"), nullable=False
    )
    rtl: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    capability_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'beta'"), nullable=False
    )
    testing_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    availability_status: Mapped[str] = mapped_column(
        String(32), server_default=text("'limited'"), nullable=False
    )
    text_quality_tier: Mapped[str] = mapped_column(
        String(32), server_default=text("'tier_2_beta'"), nullable=False
    )
    translation_status: Mapped[str] = mapped_column(
        String(32), server_default=text("'pending'"), nullable=False
    )
    ui_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    explanation_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    bilingual_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    tts_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    stt_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    voice_provider: Mapped[str | None] = mapped_column(String(48), nullable=True)
    stt_provider: Mapped[str | None] = mapped_column(String(48), nullable=True)
    translation_provider: Mapped[str | None] = mapped_column(String(48), nullable=True)
    pronunciation_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subtitle_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    question_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    answer_supported: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    academic_review_status: Mapped[str] = mapped_column(
        String(32), server_default=text("'pending'"), nullable=False
    )
    fallback_language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    quality_score_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_matrix_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    known_limitations: Mapped[str | None] = mapped_column(Text, nullable=True)


class WhiteboardAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Rights-vetted educational image assets permitted in INSERT_IMAGE actions."""

    __tablename__ = "whiteboard_assets"
    __table_args__ = (
        CheckConstraint(
            "legal_review_status IN ('pending', 'approved', 'rejected', 'quarantined')",
            name="ck_whiteboard_assets_review_valid",
        ),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_sources.id", ondelete="RESTRICT"), nullable=False
    )
    license_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("content_licenses.id", ondelete="RESTRICT"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(256), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(300), nullable=False)
    legal_review_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class LessonPlan(UUIDPrimaryKeyMixin, Base):
    """Persisted structured LessonArtifact JSON before Live Classroom playback."""

    __tablename__ = "lesson_plans"
    __table_args__ = (Index("ix_lesson_plans_student", "student_id", "created_at"),)

    student_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    curriculum_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("curriculum_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )
    concept_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    voice_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    subtitle_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    schema_version: Mapped[str] = mapped_column(
        String(24), server_default=text("'1.0.0'"), nullable=False
    )
    lesson_artifact_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClassroomSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Server-authoritative Live AI Classroom state machine session."""

    __tablename__ = "classroom_sessions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('IDLE', 'READY', 'PLAYING_SEGMENT', 'PAUSED', "
            "'CHECKPOINT_WAIT', 'DOUBT_INTERRUPTION', 'COMPLETED')",
            name="ck_classroom_sessions_state_valid",
        ),
        Index("ix_classroom_sessions_tenant_student", "tenant_id", "student_id", "created_at"),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    lesson_plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), server_default=text("'READY'"), nullable=False)
    current_segment_seq: Mapped[int] = mapped_column(
        Integer, server_default=text("1"), nullable=False
    )
    playback_position_ms: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    playback_speed: Mapped[float] = mapped_column(Float, server_default=text("1.0"), nullable=False)
    voice_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    subtitle_language: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    checkpoint_results_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClassroomEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only state transition, doubt interruption & checkpoint log."""

    __tablename__ = "classroom_events"
    __table_args__ = (
        UniqueConstraint("classroom_session_id", "sequence_no", name="uq_classroom_events_seq"),
    )

    classroom_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("classroom_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    payload_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, server_default=text("'{}'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WhiteboardSnapshot(UUIDPrimaryKeyMixin, Base):
    """Full canvas state checkpoint for fast segment reload & session restore."""

    __tablename__ = "whiteboard_snapshots"
    __table_args__ = (
        Index("ix_wb_snapshots_sess_seg", "classroom_session_id", "segment_seq", "version"),
    )

    classroom_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("classroom_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WhiteboardEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only structured WhiteboardAction log supporting undo/redo & replay."""

    __tablename__ = "whiteboard_events"
    __table_args__ = (
        CheckConstraint("actor IN ('ai', 'student')", name="ck_wb_events_actor_valid"),
        UniqueConstraint("classroom_session_id", "sequence_no", name="uq_wb_events_sess_seq"),
    )

    classroom_session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("classroom_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_payload_jsonb: Mapped[dict[str, Any]] = mapped_column(JSONBVariant, nullable=False)
    is_undone: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VoiceUsageLog(UUIDPrimaryKeyMixin, Base):
    """ElevenLabs/Voice TTS character, cache-hit, latency, and USD cost ledger."""

    __tablename__ = "voice_usage_logs"
    __table_args__ = (Index("ix_voice_usage_user_created", "user_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    classroom_session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("classroom_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    operation_type: Mapped[str] = mapped_column(
        String(16), server_default=text("'tts'"), nullable=False
    )
    voice_id: Mapped[str] = mapped_column(String(96), nullable=False)
    language_code: Mapped[str] = mapped_column(String(16), nullable=False)
    characters_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    audio_seconds: Mapped[float] = mapped_column(Float, server_default=text("0.0"), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), server_default=text("0.000000"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
