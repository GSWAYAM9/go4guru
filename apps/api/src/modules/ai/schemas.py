"""Typed Pydantic v2 contracts across the 16-module AI orchestration pipeline and HTTP APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

TeachingMode = Literal[
    "explain",
    "hint",
    "socratic",
    "step_by_step",
    "practice",
    "exam_prep",
    "revision",
]

IntentType = Literal[
    "concept_explain",
    "step_by_step",
    "hint",
    "socratic",
    "practice_generate",
    "doubt",
    "revision",
    "exam_prep",
    "out_of_scope",
]

VerificationStatus = Literal[
    "verified",
    "unverified",
    "verification_failed",
    "not_applicable",
]

SafetyAction = Literal["allow", "block", "safe_redirect", "escalate"]


class SafetyVerdict(BaseModel):
    action: SafetyAction
    reason_code: str | None = None
    safe_message: str | None = None
    requires_review_escalation: bool = False


class IntentClassification(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    needs_verification: bool = False
    verification_kind: Literal["math", "physics_units", "chemistry", "none"] = "none"
    complexity: Literal["light", "reasoning"] = "light"


class AnonymizedStudentContext(BaseModel):
    """PII-stripped learner context (never contains name, email, phone, or school)."""

    grade_id: UUID | None = None
    grade_number: int | None = None
    board_id: UUID | None = None
    board_code: str = "CBSE"
    curriculum_version_id: UUID | None = None
    primary_exam_target: str = "cbse_board"
    preferred_explanation_language: str = "en"
    preferred_question_language: str = "en"
    preferred_answer_language: str = "en"
    practice_total_attempts: int = 0
    practice_accuracy_pct: float = 0.0
    mastery_band: Literal["developing", "proficient", "advanced"] = "developing"
    is_minor: bool = True


class CurriculumContext(BaseModel):
    board_code: str | None = None
    grade_number: int | None = None
    subject_id: UUID | None = None
    subject_name: str | None = None
    discipline: str | None = None
    chapter_id: UUID | None = None
    chapter_title: str | None = None
    topic_id: UUID | None = None
    topic_title: str | None = None
    concept_id: UUID | None = None
    concept_title: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class CitedChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    hierarchy_path: str
    section_title: str | None = None
    language_code: str = "en"
    excerpt: str
    source_attribution: str | None = None
    score: float


class PedagogicalPlan(BaseModel):
    mode: TeachingMode
    spoiler_guard: bool
    grade_band: str
    exam_framing: str
    target_language: str
    target_steps: int = Field(default=3, ge=1, le=8)
    prompt_version: str = "v3.1.0"


class VerificationCheckResult(BaseModel):
    verified: bool
    status: VerificationStatus
    verifier_type: Literal["sympy_math", "pint_physics", "chem_stoichiometry", "none"]
    expression_or_equation: str | None = None
    computed_value: str | None = None
    unit_ok: bool | None = None
    details: str | None = None


class PracticeDraftOption(BaseModel):
    option_key: str
    content_markdown: str
    is_correct: bool = False


class PracticeDraftOut(BaseModel):
    question_type: str = "mcq_single"
    stem_markdown: str
    options: list[PracticeDraftOption] = Field(default_factory=list)
    hint_markdown: str | None = None
    is_ai_generated: bool = True
    is_pyq: bool = False
    verification_status: VerificationStatus = "unverified"


class StructuredTutorOutput(BaseModel):
    answer_markdown: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    candidate_math_expr: str | None = None
    candidate_physics_lhs_unit: str | None = None
    candidate_physics_rhs_unit: str | None = None
    candidate_chem_equation: str | None = None
    practice_drafts: list[PracticeDraftOut] = Field(default_factory=list)


# ------------------------------------------------------------------
# HTTP Request / Response Schemas (/api/v1/ai/*)
# ------------------------------------------------------------------
class AiSessionCreateRequest(BaseModel):
    session_type: Literal["tutor", "doubt", "lesson_companion", "revision"] = "tutor"
    title: str = Field(min_length=2, max_length=200)
    teaching_mode: TeachingMode = "explain"
    language_code: str | None = Field(default=None, max_length=16)
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    concept_id: UUID | None = None


class AiSessionOut(BaseModel):
    id: UUID
    session_type: str
    title: str
    teaching_mode: str
    language_code: str
    curriculum_context: CurriculumContext
    context_summary: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class AiModeUpdateRequest(BaseModel):
    teaching_mode: TeachingMode
    language_code: str | None = Field(default=None, max_length=16)


class AiTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    teaching_mode: TeachingMode | None = None
    language_code: str | None = Field(default=None, max_length=16)
    preferred_provider: Literal["auto", "gemini", "openai", "anthropic"] = "auto"


class AiMessageOut(BaseModel):
    id: UUID
    role: str
    content_markdown: str
    intent: str | None = None
    pedagogical_mode: str | None = None
    spoiler_guard: bool = False
    citations: list[CitedChunk] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    generated_practice: list[PracticeDraftOut] = Field(default_factory=list)
    verification_status: VerificationStatus = "not_applicable"
    verification_summary: dict[str, Any] = Field(default_factory=dict)
    provider_used: str | None = None
    model_used: str | None = None
    prompt_version: str | None = None
    is_fallback: bool = False
    safety_verdict: str = "allow"
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    created_at: datetime


class AiTurnResponse(BaseModel):
    session_id: UUID
    student_message: AiMessageOut
    assistant_message: AiMessageOut


class KnowledgeDocIngestRequest(BaseModel):
    source_id: UUID
    license_id: UUID
    title: str = Field(min_length=2, max_length=240)
    content_markdown: str = Field(min_length=10, max_length=200000)
    hierarchy_path: str = Field(min_length=3, max_length=512)
    language_code: str = Field(default="en", max_length=16)
    curriculum_version_id: UUID | None = None
    grade_id: UUID | None = None
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    concept_id: UUID | None = None
    attribution_text: str | None = Field(default=None, max_length=512)


class KnowledgeDocOut(BaseModel):
    id: UUID
    title: str
    language_code: str
    status: str
    embedding_allowed: bool
    chunk_count: int
    created_at: datetime


class ModelCapabilityOut(BaseModel):
    provider: str
    configured: bool
    fast_model: str
    reasoning_model: str
    circuit_state: str
    notes: str


class AiModelsCatalogResponse(BaseModel):
    primary_provider: str
    providers: list[ModelCapabilityOut]
    daily_turn_limit: int
    rpm_limit: int
    supported_languages: list[str]
    known_limitations: list[str]


class AiUsageQuotaResponse(BaseModel):
    turns_used_today: int
    daily_turn_limit: int
    turns_remaining_today: int
    estimated_cost_usd_today: float
    rpm_limit: int


class AiFlagMessageRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=120)


class AiReviewQueueOut(BaseModel):
    id: UUID
    ai_session_id: UUID
    ai_message_id: UUID
    reason: str
    status: str
    reviewer_notes: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class AiReviewDecisionRequest(BaseModel):
    decision: Literal["approved", "edited_approved", "rejected", "escalated"]
    reviewer_notes: str | None = Field(default=None, max_length=2000)


class AiEvalRunResponse(BaseModel):
    id: UUID
    dataset_name: str
    dataset_version: str
    provider: str
    model_id: str
    prompt_version: str
    total_items: int
    passed_items: int
    pass_rate_pct: float
    metrics: dict[str, Any]
    created_at: datetime


class AiCostSummaryResponse(BaseModel):
    total_events: int
    total_tokens_in: int
    total_tokens_out: int
    total_estimated_cost_usd: float
    fallback_count: int
