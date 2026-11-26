"""ORM models for Phase 5 Spaced Repetition Flashcards & Personalized Study Plans."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSONBVariant = JSON().with_variant(JSONB(), "postgresql")


class Flashcard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "flashcards"
    __table_args__ = (
        CheckConstraint(
            "card_type IN ('concept', 'formula', 'vocabulary', 'missed_question')",
            name="ck_flashcards_type_valid",
        ),
        Index("ix_flashcards_owner_type", "owner_user_id", "card_type"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    card_type: Mapped[str] = mapped_column(
        String(32), server_default=text("'concept'"), nullable=False
    )
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source_question_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    language_code: Mapped[str] = mapped_column(
        String(16), server_default=text("'en'"), nullable=False
    )
    front_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    back_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    hint_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_jsonb: Mapped[list[str]] = mapped_column(
        JSONBVariant, server_default=text("'[]'::jsonb"), nullable=False, default=list
    )


class StudentFlashcard(TimestampMixin, Base):
    __tablename__ = "student_flashcards"
    __table_args__ = (Index("ix_sf_student_due", "student_id", "due_at"),)

    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    flashcard_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), primary_key=True
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    interval_days: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, server_default=text("2.5"), nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    lapse_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    last_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FlashcardReview(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "flashcard_reviews"
    __table_args__ = (
        CheckConstraint("quality >= 0 AND quality <= 5", name="ck_fc_reviews_quality"),
    )

    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    flashcard_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    response_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    previous_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    new_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_ease: Mapped[float] = mapped_column(Float, nullable=False)
    new_ease: Mapped[float] = mapped_column(Float, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudyPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "study_plans"

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_minutes_budget: Mapped[int] = mapped_column(
        Integer, server_default=text("45"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), server_default=text("'active'"), nullable=False)


class StudyPlanItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "study_plan_items"

    study_plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    flashcard_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(
        Integer, server_default=text("15"), nullable=False
    )
    priority_score: Mapped[float] = mapped_column(
        Float, server_default=text("50.0"), nullable=False
    )
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'pending'"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
