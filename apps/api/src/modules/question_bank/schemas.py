"""Pydantic v2 DTOs for Question Bank, Versioning, Search, Provenance, and Excel Imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

QuestionType = Literal[
    "mcq_single",
    "mcq_multiple",
    "numerical",
    "integer",
    "assertion_reason",
    "case_based",
    "match_following",
    "matrix_match",
    "short_answer",
    "long_answer",
    "essay",
    "diagram_based",
    "passage_based",
    "comprehension",
    "map_based",
    "image_based",
    "audio_based",
    "extensible_json",
]

DifficultyLevel = Literal["easy", "medium", "hard", "olympiad"]
QuestionStatus = Literal["DRAFT", "VALIDATION", "REVIEW", "APPROVED", "PUBLISHED", "ARCHIVED"]
SourceType = Literal["original", "licensed", "verified_pyq", "ai_generated", "teacher_created"]


class OptionInput(BaseModel):
    option_key: str = Field(min_length=1, max_length=16)
    content_markdown: str = Field(min_length=1)
    is_correct: bool = False
    match_pair_key: str | None = Field(default=None, max_length=32)


class SolutionInput(BaseModel):
    language_code: str = Field(default="en", max_length=16)
    solution_type: Literal["primary", "alternative"] = "primary"
    explanation_markdown: str = Field(min_length=1)
    steps: list[str] = Field(default_factory=list)
    common_mistakes_markdown: str | None = None
    misconception_tags: list[str] = Field(default_factory=list)
    rubric: dict[str, Any] = Field(default_factory=dict)


class HintInput(BaseModel):
    hint_level: int = Field(ge=1, le=3)
    hint_markdown: str = Field(min_length=1)


class ProvenanceInput(BaseModel):
    source_id: UUID
    license_id: UUID
    source_type: SourceType
    is_pyq: bool = False
    exam_name: str | None = Field(default=None, max_length=120)
    exam_year: int | None = Field(default=None, ge=1950, le=2035)
    exam_session: str | None = Field(default=None, max_length=64)
    exam_shift: str | None = Field(default=None, max_length=64)
    paper_code: str | None = Field(default=None, max_length=64)
    question_number: str | None = Field(default=None, max_length=32)
    source_url: str | None = Field(default=None, max_length=512)


class QuestionCreateRequest(BaseModel):
    question_type: QuestionType
    language_code: str = Field(default="en", max_length=16)
    curriculum_version_id: UUID
    grade_id: UUID
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    learning_objective_id: UUID | None = None
    stem_markdown: str = Field(min_length=3)
    passage_markdown: str | None = None
    difficulty: DifficultyLevel = "medium"
    default_marks: float = Field(default=4.0, gt=0)
    default_negative_marks: float = Field(default=0.0, ge=0)
    estimated_seconds: int = Field(default=60, ge=5, le=3600)
    cognitive_level: str | None = Field(default=None, max_length=32)
    competency_tag: str | None = Field(default=None, max_length=64)
    answer_schema_jsonb: dict[str, Any] = Field(default_factory=dict)
    correct_answer_jsonb: dict[str, Any]
    ai_generated: bool = False
    ai_metadata_jsonb: dict[str, Any] = Field(default_factory=dict)
    options: list[OptionInput] = Field(default_factory=list)
    solutions: list[SolutionInput] = Field(default_factory=list)
    hints: list[HintInput] = Field(default_factory=list)
    provenance: ProvenanceInput


class QuestionNewVersionRequest(BaseModel):
    language_code: str = Field(default="en", max_length=16)
    curriculum_version_id: UUID
    grade_id: UUID
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    learning_objective_id: UUID | None = None
    stem_markdown: str = Field(min_length=3)
    passage_markdown: str | None = None
    difficulty: DifficultyLevel = "medium"
    default_marks: float = Field(default=4.0, gt=0)
    default_negative_marks: float = Field(default=0.0, ge=0)
    estimated_seconds: int = Field(default=60, ge=5, le=3600)
    answer_schema_jsonb: dict[str, Any] = Field(default_factory=dict)
    correct_answer_jsonb: dict[str, Any]
    options: list[OptionInput] = Field(default_factory=list)
    solutions: list[SolutionInput] = Field(default_factory=list)
    hints: list[HintInput] = Field(default_factory=list)


class QuestionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected", "changes_requested"]
    feedback: str | None = None
    publish: bool = False


class VerifyPyqRequest(BaseModel):
    exam_name: str = Field(min_length=2, max_length=120)
    exam_year: int = Field(ge=1950, le=2035)
    exam_session: str | None = Field(default=None, max_length=64)
    exam_shift: str | None = Field(default=None, max_length=64)
    paper_code: str | None = Field(default=None, max_length=64)
    question_number: str | None = Field(default=None, max_length=32)
    source_url: str | None = Field(default=None, max_length=512)


class OptionOut(BaseModel):
    option_key: str
    content_markdown: str
    is_correct: bool | None = None
    match_pair_key: str | None = None


class SolutionOut(BaseModel):
    language_code: str
    solution_type: str
    explanation_markdown: str
    steps: list[str]
    common_mistakes_markdown: str | None


class HintOut(BaseModel):
    hint_level: int
    hint_markdown: str


class ProvenanceOut(BaseModel):
    source_id: UUID
    license_id: UUID
    source_type: str
    is_pyq: bool
    exam_name: str | None
    exam_year: int | None
    exam_session: str | None
    verification_status: str


class QuestionOut(BaseModel):
    id: UUID
    version_id: UUID
    version_no: int
    status: str
    question_type: str
    language_code: str
    curriculum_version_id: UUID
    grade_id: UUID
    subject_id: UUID
    chapter_id: UUID
    topic_id: UUID | None
    concept_id: UUID | None
    stem_markdown: str
    passage_markdown: str | None
    difficulty: str
    default_marks: float
    default_negative_marks: float
    estimated_seconds: int
    ai_generated: bool
    options: list[OptionOut]
    hints_available_count: int
    provenance: ProvenanceOut | None
    # Redacted (None) when serialized to students before attempt submission:
    correct_answer_jsonb: dict[str, Any] | None = None
    solutions: list[SolutionOut] | None = None


class QuestionSearchResponse(BaseModel):
    items: list[QuestionOut]
    total: int
    limit: int
    offset: int


# ------------------------------------------------------------------
# Excel / CSV 14-Stage Import Schemas
# ------------------------------------------------------------------
class DetectedSheetInfo(BaseModel):
    sheet_name: str
    row_count: int
    headers: list[str]
    sample_rows: list[dict[str, Any]]


class ImportBatchOut(BaseModel):
    id: UUID
    original_filename: str
    file_format: str
    file_sha256: str
    status: str
    selected_sheet: str | None
    detected_sheets: list[DetectedSheetInfo]
    column_mapping: dict[str, Any]
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    duplicate_rows: int
    duplicate_file_warning: str | None = None
    created_at: datetime
    completed_at: datetime | None


class ColumnMappingRequest(BaseModel):
    selected_sheet: str = Field(min_length=1, max_length=128)
    column_map: dict[str, str] = Field(
        description="Mapping from canonical_field_name -> source_column_header"
    )
    default_curriculum_version_id: UUID
    default_grade_id: UUID
    default_subject_id: UUID
    default_chapter_id: UUID
    default_topic_id: UUID | None = None
    default_concept_id: UUID | None = None
    source_id: UUID
    license_id: UUID


class StagingRowOut(BaseModel):
    id: UUID
    sheet_name: str
    row_number: int
    validation_status: str
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any] | None
    errors: list[str]
    warnings: list[str]
    created_question_id: UUID | None


class ImportPreviewResponse(BaseModel):
    batch: ImportBatchOut
    rows: list[StagingRowOut]


class ImportCommitRequest(BaseModel):
    target_status: Literal["DRAFT", "REVIEW"] = "REVIEW"
    include_warnings: bool = True


class ImportCommitResponse(BaseModel):
    batch_id: UUID
    committed_count: int
    skipped_count: int
    status: str


class ImportRollbackResponse(BaseModel):
    batch_id: UUID
    rolled_back_questions: int
    status: str
