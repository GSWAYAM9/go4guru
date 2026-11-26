"""Pydantic v2 contracts for Phase 5 Flashcards, Spaced Repetition & Study Planner."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FlashcardType = Literal["concept", "formula", "vocabulary", "missed_question"]


class FlashcardCreateRequest(BaseModel):
    card_type: FlashcardType = "concept"
    concept_id: UUID | None = None
    subject_id: UUID | None = None
    source_question_id: UUID | None = None
    language_code: str = Field(default="en", max_length=16)
    front_markdown: str = Field(min_length=2, max_length=4000)
    back_markdown: str = Field(min_length=1, max_length=4000)
    hint_markdown: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)


class FlashcardOut(BaseModel):
    id: UUID
    card_type: FlashcardType
    concept_id: UUID | None = None
    concept_title: str | None = None
    subject_id: UUID | None = None
    source_question_id: UUID | None = None
    language_code: str
    front_markdown: str
    back_markdown: str
    hint_markdown: str | None = None
    tags: list[str]
    due_at: datetime
    interval_days: int
    ease_factor: float
    repetitions: int
    lapse_count: int
    last_quality: int | None = None
    last_reviewed_at: datetime | None = None
    priority_score: float = 0.0
    is_due: bool = True


class FlashcardReviewRequest(BaseModel):
    quality: int = Field(ge=0, le=5)
    response_ms: int = Field(default=0, ge=0, le=600_000)


class FlashcardReviewResponse(BaseModel):
    flashcard: FlashcardOut
    previous_interval_days: int
    new_interval_days: int
    previous_ease: float
    new_ease: float


class SyncMissedResponse(BaseModel):
    created_count: int
    existing_count: int
    flashcards: list[FlashcardOut]


class StudyPlanCreateRequest(BaseModel):
    title: str = Field(default="Daily Adaptive Revision Plan", min_length=2, max_length=200)
    target_date: date | None = None
    daily_minutes_budget: int = Field(default=45, ge=15, le=360)


class StudyPlanItemStatusRequest(BaseModel):
    status: Literal["pending", "completed", "skipped"]


class StudyPlanItemOut(BaseModel):
    id: UUID
    concept_id: UUID | None = None
    flashcard_id: UUID | None = None
    item_type: str
    title: str
    description: str
    estimated_minutes: int
    priority_score: float
    scheduled_for: date
    status: str
    completed_at: datetime | None = None


class StudyPlanOut(BaseModel):
    id: UUID
    title: str
    target_date: date | None = None
    daily_minutes_budget: int
    status: str
    items: list[StudyPlanItemOut]
    created_at: datetime


class RevisionAnalyticsOut(BaseModel):
    total_flashcards: int
    due_now_count: int
    mastered_cards_count: int
    lapsed_cards_count: int
    missed_question_cards_count: int
    total_reviews: int
    average_quality: float
    retention_success_rate_pct: float
    active_plan_completion_pct: float
    by_card_type: dict[str, int]
