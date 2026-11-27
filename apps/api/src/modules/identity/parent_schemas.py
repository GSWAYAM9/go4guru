"""Pydantic v2 schemas for Parent & Guardian Portal (F-004, F-033)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ParentPrivacySettingsSchema(BaseModel):
    share_learning_summary: bool = True
    share_weak_topics: bool = True
    share_upcoming_tests: bool = True
    allow_raw_ai_transcripts: bool = False


class GuardianLinkRequest(BaseModel):
    student_email: EmailStr
    relationship_type: Literal["parent", "guardian"] = "parent"


class GuardianConsentVerifyRequest(BaseModel):
    verification_code: str = Field(min_length=6, max_length=32)


class GuardianPrivacyUpdateRequest(BaseModel):
    share_learning_summary: bool | None = None
    share_weak_topics: bool | None = None
    share_upcoming_tests: bool | None = None
    # Accepted in payload so clients receive deterministic false enforcement
    allow_raw_ai_transcripts: bool | None = None


class GuardianLinkResponse(BaseModel):
    id: UUID
    parent_user_id: UUID
    student_user_id: UUID
    student_name: str
    student_email: str
    relationship_type: str
    consent_status: str
    consent_granted_at: datetime | None
    revoked_at: datetime | None
    privacy_settings: ParentPrivacySettingsSchema
    verification_code_preview: str | None = None
    created_at: datetime


class ParentGoalCreateRequest(BaseModel):
    student_user_id: UUID
    title: str = Field(min_length=3, max_length=200)
    target_date: date | None = None
    target_minutes_per_day: int = Field(default=45, ge=10, le=360)


class ParentGoalUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    target_date: date | None = None
    target_minutes_per_day: int | None = Field(default=None, ge=10, le=360)
    status: Literal["active", "achieved", "archived"] | None = None


class ParentGoalResponse(BaseModel):
    id: UUID
    parent_user_id: UUID
    student_user_id: UUID
    title: str
    target_date: date | None
    target_minutes_per_day: int
    status: str
    created_at: datetime


class ParentWeakTopicItem(BaseModel):
    concept_id: UUID
    mastery_score: float
    band: str


class ParentUpcomingTestItem(BaseModel):
    id: UUID
    title: str
    assignment_type: str
    due_at: datetime | None
    max_marks: float


class ParentLearningSummaryResponse(BaseModel):
    student_user_id: UUID
    student_name: str
    consent_status: str
    privacy_notice: str
    privacy_settings: ParentPrivacySettingsSchema
    onboarding_completed: bool
    primary_exam_target: str
    daily_study_minutes_target: int
    practice_total_attempts: int
    practice_correct_attempts: int
    practice_accuracy_pct: float
    practice_sessions_completed: int
    mastery_average_pct: float
    mastered_concepts_count: int
    weak_topics: list[ParentWeakTopicItem]
    revision_due_flashcards: int
    revision_total_flashcards: int
    revision_active_study_plans: int
    revision_completed_plan_items: int
    homework_total_submissions: int
    homework_evaluated_submissions: int
    upcoming_assessments: list[ParentUpcomingTestItem]
    goals: list[ParentGoalResponse]
    generated_at: datetime


class ParentDashboardResponse(BaseModel):
    parent_user_id: UUID
    linked_students: list[GuardianLinkResponse]
    active_goals_count: int
    verified_links_count: int
    pending_links_count: int
