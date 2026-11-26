"""Pydantic v2 contracts for Phase 5 Adaptive Concept Mastery & Learning Paths."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ConceptMasteryOut(BaseModel):
    concept_id: UUID
    concept_code: str
    concept_title: str
    subject_name: str | None = None
    chapter_title: str | None = None
    mastery_score: float
    confidence: float
    retention_score: float
    independent_solve_ratio: float
    transfer_score: float
    improvement_slope: float
    difficulty_weighted_accuracy: float
    band: Literal["novice", "developing", "proficient", "mastered"]
    attempts_count: int
    last_practiced_at: datetime | None = None
    next_review_due_at: datetime | None = None
    breakdown: dict[str, Any]
    evidence_summary: dict[str, Any]


class MisconceptionCreateRequest(BaseModel):
    concept_id: UUID
    question_id: UUID | None = None
    misconception_code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=2, max_length=2000)
    severity: Literal["low", "medium", "high"] = "medium"


class MisconceptionOut(BaseModel):
    id: UUID
    concept_id: UUID
    concept_title: str
    question_id: UUID | None = None
    misconception_code: str
    title: str
    description: str
    severity: str
    occurrence_count: int
    last_observed_at: datetime
    resolved_at: datetime | None = None


class RecommendationItemOut(BaseModel):
    concept_id: UUID
    concept_title: str
    item_type: str
    priority_score: float
    reason: str
    action_route: str


class LearningPathItemOut(BaseModel):
    id: UUID
    concept_id: UUID
    concept_title: str
    item_type: str
    sequence_no: int
    priority_score: float
    reason: str
    status: str
    completed_at: datetime | None = None


class LearningPathCreateRequest(BaseModel):
    title: str = Field(default="Adaptive Mastery Path", min_length=2, max_length=200)
    goal_exam_track: str | None = Field(default=None, max_length=64)


class LearningPathItemStatusRequest(BaseModel):
    status: Literal["pending", "in_progress", "completed", "skipped"]


class LearningPathOut(BaseModel):
    id: UUID
    title: str
    goal_exam_track: str | None = None
    status: str
    items: list[LearningPathItemOut]
    created_at: datetime


class AdaptiveOverviewOut(BaseModel):
    concepts: list[ConceptMasteryOut]
    weak_concepts: list[ConceptMasteryOut]
    mastered_concepts: list[ConceptMasteryOut]
    unresolved_misconceptions: list[MisconceptionOut]
    recommendations: list[RecommendationItemOut]
    algorithm_version: str
    limitations_note: str
