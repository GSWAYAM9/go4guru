"""ORM models for Phase 10 Multilingual Learning Expansion (Glossary, Translations, QA)."""

from __future__ import annotations

from datetime import datetime
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


class MultilingualGlossaryTerm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical STEM & academic terminology dictionary for bilingual explanations."""

    __tablename__ = "multilingual_glossary_terms"
    __table_args__ = (
        UniqueConstraint("concept_key", "language_code", name="uq_glossary_concept_lang"),
        CheckConstraint(
            "review_status IN ('draft', 'in_review', 'approved', 'rejected')",
            name="ck_glossary_review_status_valid",
        ),
        Index("ix_glossary_lang_subject", "language_code", "subject_area"),
    )

    concept_key: Mapped[str] = mapped_column(String(96), nullable=False)
    subject_area: Mapped[str] = mapped_column(String(48), nullable=False)
    english_term: Mapped[str] = mapped_column(String(160), nullable=False)
    language_code: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("language_capabilities.language_code", ondelete="CASCADE"),
        nullable=False,
    )
    localized_term: Mapped[str] = mapped_column(String(200), nullable=False)
    transliteration: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preserve_english_in_bilingual: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    latex_symbol: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(24), server_default=text("'approved'"), nullable=False
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TranslationEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reviewed translation infrastructure for UI strings, lessons, questions, and formulas."""

    __tablename__ = "translation_entries"
    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "resource_key",
            "target_language_code",
            name="uq_translation_resource_lang",
        ),
        CheckConstraint(
            "resource_type IN ('ui_string', 'question', 'lesson_segment', 'formula_note', 'concept_summary')",
            name="ck_translation_resource_type_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'in_review', 'approved', 'rejected', 'needs_revision')",
            name="ck_translation_status_valid",
        ),
        Index("ix_translation_lang_status", "target_language_code", "status"),
    )

    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    target_language_code: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("language_capabilities.language_code", ondelete="CASCADE"),
        nullable=False,
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    bilingual_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    notation_preserved: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    terminology_warnings_jsonb: Mapped[list[str]] = mapped_column(
        JSONBVariant, server_default=text("'[]'::jsonb"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'in_review'"), nullable=False
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LanguageQualityEvaluation(UUIDPrimaryKeyMixin, Base):
    """Auditable language-specific evaluation run tracking notation, script, and term QA."""

    __tablename__ = "language_quality_evaluations"
    __table_args__ = (
        CheckConstraint(
            "modality IN ('ui', 'explanation', 'bilingual', 'voice', 'stt', 'subtitle', 'question', 'answer')",
            name="ck_lang_eval_modality_valid",
        ),
        Index("ix_lang_eval_code_date", "language_code", "evaluated_at"),
    )

    language_code: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("language_capabilities.language_code", ondelete="CASCADE"),
        nullable=False,
    )
    modality: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    test_suite_version: Mapped[str] = mapped_column(
        String(32), server_default=text("'phase10-v1'"), nullable=False
    )
    script_fidelity_score: Mapped[float] = mapped_column(Float, nullable=False)
    math_preservation_score: Mapped[float] = mapped_column(Float, nullable=False)
    science_notation_score: Mapped[float] = mapped_column(Float, nullable=False)
    terminology_accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    fluency_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    findings_jsonb: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBVariant, server_default=text("'[]'::jsonb"), nullable=False
    )
    evaluated_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
