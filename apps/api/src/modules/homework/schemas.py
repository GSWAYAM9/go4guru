"""Pydantic v2 schemas and subject-aware error taxonomies for Phase 6 Homework AI."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

HomeworkSubjectArea = Literal[
    "mathematics",
    "physics",
    "chemistry",
    "english",
    "social_science",
]

HomeworkSubjectSelection = Literal[
    "auto",
    "mathematics",
    "physics",
    "chemistry",
    "english",
    "social_science",
]

HomeworkSubmissionStatus = Literal[
    "uploaded",
    "ocr_processing",
    "needs_review",
    "analyzing",
    "feedback_ready",
    "retry_pending",
    "completed",
    "failed",
]

EvaluationOverallStatus = Literal[
    "correct",
    "partially_correct",
    "needs_correction",
    "unreadable_or_uncertain",
]

ConfidenceBand = Literal["high", "medium", "low", "uncertain"]

# Canonical subject-aware error classification taxonomy (Phase 6 requirements)
SUBJECT_ERROR_CATEGORIES: dict[HomeworkSubjectArea, tuple[str, ...]] = {
    "mathematics": (
        "algebra",
        "formula",
        "arithmetic",
        "sign",
        "logic",
        "missing_steps",
    ),
    "physics": (
        "concept",
        "formula",
        "units",
        "calculation",
        "diagram",
        "reasoning",
    ),
    "chemistry": (
        "equation",
        "reaction",
        "formula",
        "concept",
        "calculation",
        "units",
    ),
    "english": (
        "grammar",
        "spelling",
        "vocabulary",
        "sentence_structure",
        "comprehension",
        "writing",
    ),
    "social_science": (
        "factual_accuracy",
        "concept",
        "structure",
        "missing_points",
        "explanation",
        "map_timeline",
    ),
}


class HomeworkFileOut(BaseModel):
    id: UUID
    page_no: int
    original_filename: str
    mime_type: str
    detected_format: str
    size_bytes: int
    sha256: str
    exif_stripped: bool
    pdf_page_count: int | None = None
    scan_status: str
    download_url: str
    created_at: datetime


class HomeworkOcrPageOut(BaseModel):
    id: UUID
    page_no: int
    ocr_provider: str
    extracted_text: str
    extracted_latex: str | None = None
    handwriting_detected: bool
    handwriting_supported: bool
    confidence: float
    needs_review: bool
    student_corrected_text: str | None = None
    effective_text: str
    warnings: list[str] = Field(default_factory=list)


class ExtractedStepOut(BaseModel):
    step_no: int = Field(ge=1)
    content: str
    expression: str | None = None


class StepEvaluationOut(BaseModel):
    step_no: int = Field(ge=1)
    student_work: str
    status: Literal["correct", "partially_correct", "incorrect", "missing", "uncertain"]
    explanation: str
    error_categories: list[str] = Field(default_factory=list)
    verifier_note: str | None = None


class ErrorClassificationOut(BaseModel):
    subject_area: HomeworkSubjectArea
    category: str
    severity: Literal["low", "medium", "high"] = "medium"
    step_no: int | None = None
    summary: str
    guidance: str


class GraduatedHintOut(BaseModel):
    level: int = Field(ge=1, le=3)
    stage: Literal["conceptual_nudge", "method_scaffold", "targeted_correction"]
    title: str
    content_markdown: str
    spoiler_checked: bool = True


class RevisionRecommendationOut(BaseModel):
    topic_title: str
    reason: str
    recommended_action: Literal[
        "review_flashcards",
        "guided_practice",
        "adaptive_remediation",
        "tutor_socratic_drill",
    ]
    action_route: str
    priority: Literal["high", "medium", "low"] = "medium"
    error_categories: list[str] = Field(default_factory=list)


class FeedbackValidationReportOut(BaseModel):
    passed: bool
    spoiler_guard_passed: bool
    taxonomy_valid: bool
    verifier_agreement: Literal["verified", "partial", "discrepancy", "not_applicable"]
    safety_passed: bool
    confidence_adjusted: bool = False
    issues: list[str] = Field(default_factory=list)


class HomeworkEvaluationOut(BaseModel):
    id: UUID
    attempt_no: int
    subject_area: HomeworkSubjectArea
    detected_question: str
    student_work_summary: str
    extracted_steps: list[ExtractedStepOut] = Field(default_factory=list)
    step_evaluations: list[StepEvaluationOut] = Field(default_factory=list)
    error_classifications: list[ErrorClassificationOut] = Field(default_factory=list)
    overall_status: EvaluationOverallStatus
    feedback_summary: str
    strengths: list[str] = Field(default_factory=list)
    unlocked_hints: list[GraduatedHintOut] = Field(default_factory=list)
    current_hint_level_unlocked: int
    max_hint_level: int = 3
    has_more_hints: bool
    solution_revealed: bool
    complete_solution_markdown: str | None = None
    verifier_results: dict[str, Any] = Field(default_factory=dict)
    validation_report: FeedbackValidationReportOut
    revision_recommendations: list[RevisionRecommendationOut] = Field(default_factory=list)
    confidence: float
    confidence_band: ConfidenceBand
    provider_used: str
    model_id: str
    is_fallback: bool
    safety_verdict: str
    created_at: datetime


class HomeworkSubmissionSummaryOut(BaseModel):
    id: UUID
    title: str
    selected_subject: HomeworkSubjectSelection
    detected_subject: HomeworkSubjectArea | None = None
    subject_confidence: float | None = None
    language_code: str
    status: HomeworkSubmissionStatus
    page_count: int
    retry_count: int
    needs_ocr_review: bool
    latest_overall_status: EvaluationOverallStatus | None = None
    latest_confidence: float | None = None
    error_count: int = 0
    created_at: datetime
    updated_at: datetime


class HomeworkSubmissionDetailOut(BaseModel):
    id: UUID
    student_id: UUID
    title: str
    selected_subject: HomeworkSubjectSelection
    detected_subject: HomeworkSubjectArea | None = None
    subject_confidence: float | None = None
    language_code: str
    status: HomeworkSubmissionStatus
    page_count: int
    retry_count: int
    needs_ocr_review: bool
    failure_reason: str | None = None
    files: list[HomeworkFileOut] = Field(default_factory=list)
    ocr_pages: list[HomeworkOcrPageOut] = Field(default_factory=list)
    latest_evaluation: HomeworkEvaluationOut | None = None
    evaluation_history: list[HomeworkEvaluationOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OcrPageCorrectionItem(BaseModel):
    page_no: int = Field(ge=1)
    corrected_text: str = Field(min_length=1, max_length=20000)


class OcrCorrectionRequest(BaseModel):
    pages: list[OcrPageCorrectionItem] = Field(min_length=1, max_length=25)
    subject_override: HomeworkSubjectSelection | None = None
    re_evaluate: bool = True


class HomeworkRetryRequest(BaseModel):
    revised_work_text: str = Field(min_length=3, max_length=20000)
    student_reflection: str | None = Field(default=None, max_length=2000)


class UnlockHintRequest(BaseModel):
    target_level: int | None = Field(default=None, ge=1, le=3)


class RevealSolutionRequest(BaseModel):
    confirm_reveal: bool = Field(
        default=False,
        description="Must be explicitly true so complete solutions are never revealed accidentally.",
    )
