"""Pydantic schemas for Configurable Exam Patterns, Quizzes, Tests, Attempts & Results."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.assessment.rule_engine import ExamPatternRules, ScoringRule

QuizType = Literal[
    "daily",
    "quick",
    "chapter",
    "topic",
    "concept",
    "diagnostic",
    "revision",
    "teacher",
    "ai_generated",
    "challenge",
    "competition",
    "institution",
]

TestCategory = Literal[
    "cbse_mock",
    "jee_main",
    "jee_adv",
    "neet",
    "chapter_test",
    "topic_test",
    "diagnostic",
    "teacher_test",
    "institution_test",
]


class ExamPatternCreate(BaseModel):
    exam_track_id: UUID
    version_label: str = Field(min_length=2, max_length=64)
    effective_year: int = Field(ge=2020, le=2040)
    is_active: bool = True
    rules: ExamPatternRules


class ExamPatternOut(BaseModel):
    id: UUID
    exam_track_id: UUID
    exam_track_code: str
    exam_track_name: str
    version_label: str
    effective_year: int
    is_active: bool
    rules: ExamPatternRules


class QuizGenerateRequest(BaseModel):
    quiz_type: QuizType = "chapter"
    title: str = Field(min_length=2, max_length=200)
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    exam_pattern_id: UUID | None = None
    question_count: int = Field(default=5, ge=1, le=100)
    duration_seconds: int | None = Field(default=600, ge=30, le=14400)
    grace_seconds: int = Field(default=15, ge=0, le=300)
    shuffle_questions: bool = True
    shuffle_options: bool = False
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    question_type_distribution: dict[str, int] = Field(default_factory=dict)
    scoring_rule: ScoringRule = Field(default_factory=ScoringRule)
    seed: int = Field(default=42, ge=0)


class QuizOut(BaseModel):
    id: UUID
    quiz_type: str
    title: str
    status: str
    question_count: int
    duration_seconds: int | None
    shuffle_questions: bool
    is_ai_generated: bool
    created_at: datetime


class TestSectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    question_count: int = Field(default=5, ge=1, le=200)
    allowed_question_types: list[str] = Field(default_factory=list)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    question_type_distribution: dict[str, int] = Field(default_factory=dict)
    attempt_limit: int | None = Field(default=None, ge=1, le=200)
    scoring_rule: ScoringRule = Field(default_factory=ScoringRule)
    explicit_question_ids: list[UUID] = Field(default_factory=list)


class TestCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    test_category: TestCategory = "chapter_test"
    exam_pattern_id: UUID | None = None
    duration_seconds: int | None = Field(default=1800, ge=30, le=21600)
    grace_seconds: int = Field(default=30, ge=0, le=300)
    max_attempts: int | None = Field(default=None, ge=1)
    shuffle_questions: bool = False
    shuffle_options: bool = False
    sections: list[TestSectionInput] = Field(min_length=1)


class TestSectionOut(BaseModel):
    id: UUID
    sequence_no: int
    name: str
    attempt_limit: int | None
    question_count: int
    marking_rule: ScoringRule


class TestOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    test_category: str
    exam_pattern_id: UUID | None
    duration_seconds: int | None
    grace_seconds: int
    total_marks: float
    status: str
    sections: list[TestSectionOut]
    created_at: datetime


class AttemptQuestionOptionView(BaseModel):
    option_key: str
    content_markdown: str


class AttemptQuestionStateItem(BaseModel):
    sequence_no: int
    section_id: UUID | None
    section_name: str | None
    question_id: UUID
    question_version_id: UUID
    question_type: str
    stem_markdown: str
    difficulty: str
    marks: float
    negative_marks: float
    options: list[AttemptQuestionOptionView]
    response_jsonb: dict[str, Any]
    is_visited: bool
    is_marked_for_review: bool
    time_spent_seconds: int


class AttemptStateResponse(BaseModel):
    attempt_id: UUID
    title: str
    source_kind: Literal["quiz", "test"]
    status: str
    started_at: datetime
    expires_at: datetime | None
    grace_until: datetime | None
    server_now_utc: datetime
    remaining_seconds: int | None
    questions: list[AttemptQuestionStateItem]


class AutosaveAnswerItem(BaseModel):
    question_version_id: UUID
    response_jsonb: dict[str, Any] = Field(default_factory=dict)
    is_visited: bool = True
    is_marked_for_review: bool = False
    time_spent_seconds: int = Field(default=0, ge=0, le=21600)


class AutosaveAnswersRequest(BaseModel):
    answers: list[AutosaveAnswerItem] = Field(min_length=1)


class AutosaveResponse(BaseModel):
    attempt_id: UUID
    saved_count: int
    server_now_utc: datetime
    remaining_seconds: int | None


class SubmitAttemptRequest(BaseModel):
    answers: list[AutosaveAnswerItem] = Field(default_factory=list)


class SectionScoreSummary(BaseModel):
    section_id: str | None
    section_name: str
    total_questions: int
    attempted: int
    correct: int
    wrong: int
    raw_score: float
    max_score: float


class AttemptResultQuestionItem(BaseModel):
    sequence_no: int
    section_name: str | None
    question_id: UUID
    question_version_id: UUID
    question_type: str
    stem_markdown: str
    options: list[AttemptQuestionOptionView]
    student_response_jsonb: dict[str, Any]
    correct_answer_jsonb: dict[str, Any]
    is_visited: bool
    is_marked_for_review: bool
    time_spent_seconds: int
    is_correct: bool
    marks_awarded: float
    explanation_markdown: str | None
    steps: list[str]
    common_mistakes_markdown: str | None


class AttemptResultResponse(BaseModel):
    attempt_id: UUID
    title: str
    source_kind: Literal["quiz", "test"]
    status: str
    raw_score: float
    max_score: float
    accuracy_pct: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    started_at: datetime
    submitted_at: datetime | None
    section_breakdown: list[SectionScoreSummary]
    items: list[AttemptResultQuestionItem]


class AttemptHistoryItem(BaseModel):
    attempt_id: UUID
    title: str
    source_kind: Literal["quiz", "test"]
    status: str
    raw_score: float | None
    max_score: float | None
    accuracy_pct: float | None
    started_at: datetime
    submitted_at: datetime | None
