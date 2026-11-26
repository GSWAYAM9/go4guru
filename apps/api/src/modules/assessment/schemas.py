"""Pydantic schemas for Practice Sessions, Attempts, Hints, Notes, and Bookmarks."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PracticeSessionCreateRequest(BaseModel):
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    limit: int = Field(default=10, ge=1, le=50)
    mode: str = Field(default="guided_practice", max_length=32)


class PracticeOptionView(BaseModel):
    option_key: str
    content_markdown: str


class PracticeQuestionView(BaseModel):
    question_id: UUID
    question_version_id: UUID
    question_type: str
    stem_markdown: str
    difficulty: str
    default_marks: float
    options: list[PracticeOptionView]


class HintRevealRequest(BaseModel):
    question_id: UUID
    hint_level: int = Field(ge=1, le=3)


class HintRevealOut(BaseModel):
    question_id: UUID
    hint_level: int
    hint_markdown: str | None
    hints_used_count: int


class AttemptSubmitRequest(BaseModel):
    question_id: UUID
    response_jsonb: dict[str, Any]
    time_spent_seconds: int = Field(default=0, ge=0, le=7200)


class AttemptResultOut(BaseModel):
    id: UUID
    question_id: UUID
    question_version_id: UUID
    is_correct: bool
    score_awarded: float
    hints_used_count: int
    time_spent_seconds: int
    attempted_at: datetime
    correct_answer_jsonb: dict[str, Any] | None
    explanation_markdown: str | None
    steps: list[str]
    common_mistakes_markdown: str | None


class PracticeSessionOut(BaseModel):
    id: UUID
    mode: str
    subject_id: UUID | None
    chapter_id: UUID | None
    topic_id: UUID | None
    concept_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    questions: list[PracticeQuestionView]
    attempts: list[AttemptResultOut]
    hints_revealed: dict[str, list[dict[str, Any]]]


class StudentNoteCreate(BaseModel):
    concept_id: UUID | None = None
    question_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    body_markdown: str = Field(min_length=1)


class StudentNoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body_markdown: str | None = Field(default=None, min_length=1)


class StudentNoteOut(BaseModel):
    id: UUID
    concept_id: UUID | None
    question_id: UUID | None
    title: str
    body_markdown: str
    created_at: datetime
    updated_at: datetime


class BookmarkCreateRequest(BaseModel):
    question_id: UUID
    folder_name: str = Field(default="General", min_length=1, max_length=80)


class BookmarkOut(BaseModel):
    question_id: UUID
    folder_name: str
    created_at: datetime
