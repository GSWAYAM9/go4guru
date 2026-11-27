"""Pydantic v2 schemas for Mentor Ecosystem (F-032)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class MentorAssignStudentRequest(BaseModel):
    student_email: EmailStr
    notes: str | None = Field(default=None, max_length=1000)


class MentorStudentRosterItem(BaseModel):
    assignment_id: UUID
    student_id: UUID
    student_name: str
    student_email: str
    status: str
    notes: str | None
    active_goals_count: int
    open_follow_ups_count: int
    created_at: datetime


class MentorGoalCreateRequest(BaseModel):
    student_id: UUID
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    target_date: date | None = None


class MentorGoalUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    target_date: date | None = None
    progress_pct: int | None = Field(default=None, ge=0, le=100)
    status: Literal["active", "completed", "paused"] | None = None


class MentorGoalResponse(BaseModel):
    id: UUID
    mentor_id: UUID
    student_id: UUID
    title: str
    description: str
    target_date: date | None
    progress_pct: int
    status: str
    created_at: datetime


class MentorSessionCreateRequest(BaseModel):
    student_id: UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=10, le=180)
    summary_notes: str = Field(default="", max_length=4000)
    recommendations: list[str] = Field(default_factory=list, max_length=20)
    status: Literal["scheduled", "completed", "cancelled"] = "scheduled"


class MentorSessionUpdateRequest(BaseModel):
    status: Literal["scheduled", "completed", "cancelled"] | None = None
    summary_notes: str | None = Field(default=None, max_length=4000)
    recommendations: list[str] | None = Field(default=None, max_length=20)


class MentorSessionResponse(BaseModel):
    id: UUID
    mentor_id: UUID
    student_id: UUID
    scheduled_at: datetime
    duration_minutes: int
    status: str
    summary_notes: str
    recommendations: list[str]
    created_at: datetime


class MentorFollowUpCreateRequest(BaseModel):
    student_id: UUID
    session_id: UUID | None = None
    title: str = Field(min_length=3, max_length=200)
    due_date: date | None = None


class MentorFollowUpUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    due_date: date | None = None
    status: Literal["open", "in_progress", "completed"] | None = None


class MentorFollowUpResponse(BaseModel):
    id: UUID
    session_id: UUID | None
    mentor_id: UUID
    student_id: UUID
    title: str
    due_date: date | None
    status: str
    created_at: datetime


class MentorWeakConceptItem(BaseModel):
    concept_id: UUID
    mastery_score: float
    band: str


class MentorStudentReviewResponse(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    primary_exam_target: str
    daily_study_minutes_target: int
    practice_total_attempts: int
    practice_accuracy_pct: float
    mastery_average_pct: float
    weak_concepts: list[MentorWeakConceptItem]
    due_flashcards_count: int
    active_study_plans_count: int
    completed_plan_items_count: int
    homework_evaluated_count: int
    recommended_interventions: list[str]
    goals: list[MentorGoalResponse]
    sessions: list[MentorSessionResponse]
    follow_ups: list[MentorFollowUpResponse]


class MentorDashboardResponse(BaseModel):
    mentor_id: UUID
    assigned_students_count: int
    active_goals_count: int
    upcoming_sessions_count: int
    open_follow_ups_count: int
    students: list[MentorStudentRosterItem]
