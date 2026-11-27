"""Pydantic v2 request/response contracts for Phase 9: Examination Preparation Ecosystem."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.assessment.exam_schemas import ExamPatternOut


class ExamCoverageAuditOut(BaseModel):
    exam_code: str
    mapped_chapters_count: int
    included_chapters_count: int
    audited_chapters_count: int
    chapters_with_questions_count: int
    published_question_count: int
    verified_pyq_count: int
    unverified_pyq_excluded_count: int
    audited_coverage_pct: float
    question_coverage_pct: float
    coverage_status: Literal["empty", "partial_unverified", "audited_partial", "audited_complete"]
    coverage_disclaimer: str


class ExamTrackOverviewOut(BaseModel):
    id: UUID
    code: str
    name: str
    target_seconds_per_question: int
    active_pattern: ExamPatternOut | None
    patterns: list[ExamPatternOut]
    coverage_audit: ExamCoverageAuditOut


class SyllabusTopicItemOut(BaseModel):
    id: UUID
    title: str


class ExamSyllabusChapterOut(BaseModel):
    id: UUID
    exam_track_id: UUID
    pattern_version_label: str
    subject_id: UUID
    subject_name: str
    chapter_id: UUID
    chapter_title: str
    weightage_pct: float
    expected_questions: int
    priority_tier: Literal["high_yield", "core", "optional"]
    syllabus_status: Literal["included", "reduced", "excluded"]
    notes: str | None
    audit_verified: bool
    audited_at: datetime | None
    published_question_count: int
    verified_pyq_count: int
    topics: list[SyllabusTopicItemOut]


class ExamSyllabusResponse(BaseModel):
    exam_code: str
    exam_name: str
    pattern_version_label: str
    coverage_audit: ExamCoverageAuditOut
    chapters: list[ExamSyllabusChapterOut]


class ExamSyllabusChapterUpsert(BaseModel):
    pattern_version_label: str = Field(min_length=2, max_length=64)
    subject_id: UUID
    chapter_id: UUID
    weightage_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    expected_questions: int = Field(default=0, ge=0, le=100)
    priority_tier: Literal["high_yield", "core", "optional"] = "core"
    syllabus_status: Literal["included", "reduced", "excluded"] = "included"
    notes: str | None = Field(default=None, max_length=2000)
    audit_verified: bool = False


class VerifiedPyqBadgeOut(BaseModel):
    is_verified_pyq: bool = True
    badge_label: str
    exam_name: str
    exam_year: int
    exam_session: str | None
    exam_shift: str | None
    paper_code: str | None
    question_number: str | None
    source_url: str | None
    verification_status: str = "verified"


class ExamQuestionOptionRedactedOut(BaseModel):
    option_key: str
    content_markdown: str


class ExamQuestionItemOut(BaseModel):
    question_id: UUID
    question_version_id: UUID
    question_type: str
    subject_id: UUID
    subject_name: str
    chapter_id: UUID
    chapter_title: str
    topic_id: UUID | None
    topic_title: str | None
    concept_id: UUID | None
    concept_title: str | None
    stem_markdown: str
    difficulty: str
    default_marks: float
    default_negative_marks: float
    estimated_seconds: int
    options: list[ExamQuestionOptionRedactedOut]
    pyq_provenance: VerifiedPyqBadgeOut | None


class ExamQuestionFacetsOut(BaseModel):
    available_years: list[int]
    available_sessions: list[str]
    available_difficulties: list[str]
    available_question_types: list[str]
    total_published_questions: int
    total_verified_pyqs: int
    unverified_pyq_excluded_count: int


class ExamQuestionsExplorerResponse(BaseModel):
    exam_code: str
    verified_pyq_only: bool
    facets: ExamQuestionFacetsOut
    questions: list[ExamQuestionItemOut]


class ExamPracticeLaunchRequest(BaseModel):
    mode: Literal["chapter_practice", "topic_practice", "verified_pyq_drill"] = "chapter_practice"
    title: str | None = Field(default=None, max_length=200)
    exam_pattern_id: UUID | None = None
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    question_type: str | None = None
    exam_year: int | None = Field(default=None, ge=1980, le=2035)
    exam_session: str | None = None
    verified_pyq_only: bool = False
    question_count: int = Field(default=10, ge=1, le=50)
    duration_seconds: int | None = Field(default=None, ge=60, le=10800)


class ExamMockGenerateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    exam_pattern_id: UUID | None = None
    mock_scope: Literal["full_mock", "timed_section_mock"] = "full_mock"
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    verified_pyq_only: bool = False
    seed: int = Field(default=42, ge=1, le=999999)


class LaunchedExamAttemptOut(BaseModel):
    attempt_id: UUID
    exam_code: str
    test_id: UUID | None
    quiz_id: UUID | None
    title: str
    pattern_version_label: str | None
    question_count: int
    duration_seconds: int | None
    started_at: datetime
    expires_at: datetime | None


class WeaknessBucketOut(BaseModel):
    entity_id: str | None
    name: str
    attempts: int
    correct: int
    accuracy_pct: float
    avg_seconds: float
    severity: Literal["critical", "needs_focus", "developing"]


class ExamPerformanceHistoryItemOut(BaseModel):
    attempt_id: UUID
    title: str
    category: str
    submitted_at: datetime
    raw_score: float
    max_score: float
    accuracy_pct: float
    avg_seconds_per_question: float


class ExamAnalyticsResponse(BaseModel):
    exam_code: str
    exam_name: str
    total_attempts: int
    total_questions_answered: int
    overall_accuracy_pct: float
    average_seconds_per_question: float
    target_seconds_per_question: int
    pacing_status: str
    weak_subjects: list[WeaknessBucketOut]
    weak_chapters: list[WeaknessBucketOut]
    weak_concepts: list[WeaknessBucketOut]
    performance_history: list[ExamPerformanceHistoryItemOut]
    improvement_recommendations: list[str]


class FormulaVariableItem(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    meaning: str = Field(min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=64)


class ExamFormulaCreate(BaseModel):
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    title: str = Field(min_length=2, max_length=200)
    formula_latex: str = Field(min_length=1, max_length=1000)
    variables: list[FormulaVariableItem] = Field(default_factory=list)
    when_to_use: str = Field(min_length=3, max_length=2000)
    common_pitfall: str | None = Field(default=None, max_length=2000)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    is_high_yield: bool = True
    status: Literal["DRAFT", "PUBLISHED"] = "PUBLISHED"


class ExamFormulaOut(BaseModel):
    id: UUID
    exam_track_id: UUID
    subject_id: UUID
    subject_name: str
    chapter_id: UUID
    chapter_title: str
    topic_id: UUID | None
    topic_title: str | None
    title: str
    formula_latex: str
    variables: list[FormulaVariableItem]
    when_to_use: str
    common_pitfall: str | None
    difficulty: str
    is_high_yield: bool
    status: str


class ExamRevisionPlanCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    exam_pattern_id: UUID | None = None
    target_exam_date: date
    daily_minutes: int = Field(default=90, ge=15, le=600)
    focus_chapter_ids: list[UUID] = Field(default_factory=list)


class ExamRevisionPlanOut(BaseModel):
    id: UUID
    exam_track_id: UUID
    exam_code: str
    exam_pattern_id: UUID | None
    title: str
    target_exam_date: date
    daily_minutes: int
    focus_chapters: list[dict[str, Any]]
    schedule: list[dict[str, Any]]
    status: str
    created_at: datetime


class DetailedSolutionItemOut(BaseModel):
    sequence_no: int
    question_id: UUID
    question_version_id: UUID
    question_type: str
    subject_name: str
    chapter_title: str
    stem_markdown: str
    options: list[ExamQuestionOptionRedactedOut]
    student_response_jsonb: dict[str, Any]
    correct_answer_jsonb: dict[str, Any]
    is_correct: bool | None
    marks_awarded: float
    time_spent_seconds: int
    explanation_markdown: str | None
    steps: list[str]
    common_mistakes_markdown: str | None


class AttemptDetailedSolutionsResponse(BaseModel):
    attempt_id: UUID
    title: str
    status: str
    raw_score: float
    max_score: float
    accuracy_pct: float
    submitted_at: datetime | None
    items: list[DetailedSolutionItemOut]
