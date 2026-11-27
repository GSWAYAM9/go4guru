"""Pydantic v2 DTOs for Phase 10 Multilingual Learning Expansion."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

CapabilityStatus = Literal["production", "beta", "experimental", "planned"]
TestingStatus = Literal["passed", "partial", "pending", "failed"]
AvailabilityStatus = Literal["available", "limited", "provider_key_required", "unavailable"]
BilingualMode = Literal["monolingual", "bilingual_stem_en", "side_by_side"]
TranslationResourceType = Literal[
    "ui_string", "question", "lesson_segment", "formula_note", "concept_summary"
]
TranslationReviewDecision = Literal["approved", "rejected", "needs_revision"]
EvalModality = Literal[
    "ui", "explanation", "bilingual", "voice", "stt", "subtitle", "question", "answer"
]


class LanguageCapabilityDetailOut(BaseModel):
    """Backward-compatible enriched Language Capability Registry item."""

    language_code: str
    display_name: str
    native_name: str
    script_name: str = "Latin"
    rtl: bool
    capability_status: str = "beta"
    testing_status: str = "pending"
    availability_status: str = "limited"
    text_quality_tier: str
    translation_status: str
    ui_supported: bool = False
    explanation_supported: bool = True
    bilingual_supported: bool = True
    tts_supported: bool
    stt_supported: bool
    voice_provider: str | None = None
    stt_provider: str | None = None
    translation_provider: str | None = None
    pronunciation_tier: str | None = None
    subtitle_supported: bool
    question_supported: bool = False
    answer_supported: bool = False
    academic_review_status: str
    fallback_language_code: str = "en"
    quality_score_pct: float | None = None
    last_evaluated_at: datetime | None = None
    provider_matrix: dict[str, Any] = Field(default_factory=dict)
    known_limitations: str | None = None


class LanguageCapabilityPatchRequest(BaseModel):
    """Admin/reviewer update for honest language capability metadata."""

    capability_status: CapabilityStatus | None = None
    testing_status: TestingStatus | None = None
    availability_status: AvailabilityStatus | None = None
    text_quality_tier: str | None = Field(default=None, max_length=32)
    translation_status: str | None = Field(default=None, max_length=32)
    ui_supported: bool | None = None
    explanation_supported: bool | None = None
    bilingual_supported: bool | None = None
    tts_supported: bool | None = None
    stt_supported: bool | None = None
    subtitle_supported: bool | None = None
    question_supported: bool | None = None
    answer_supported: bool | None = None
    voice_provider: str | None = Field(default=None, max_length=48)
    stt_provider: str | None = Field(default=None, max_length=48)
    translation_provider: str | None = Field(default=None, max_length=48)
    pronunciation_tier: str | None = Field(default=None, max_length=32)
    academic_review_status: str | None = Field(default=None, max_length=32)
    fallback_language_code: str | None = Field(default=None, min_length=2, max_length=16)
    known_limitations: str | None = Field(default=None, max_length=2000)
    provider_matrix: dict[str, Any] | None = None


class ModalityResolutionOut(BaseModel):
    """Resolved language & honest fallback detail for one independent modality."""

    modality: str
    requested_language: str
    effective_language: str
    fallback_applied: bool
    fallback_reason: str | None = None
    capability_status: str
    availability_status: str
    testing_status: str
    rtl: bool
    provider: str | None = None


class UserLanguagePreferencesOut(BaseModel):
    """6 independent language settings + bilingual mode + per-modality fallback resolutions."""

    ui_language: str
    preferred_explanation_language: str
    preferred_voice_language: str
    preferred_subtitle_language: str
    preferred_question_language: str
    preferred_answer_language: str
    bilingual_explanation_mode: str
    resolutions: dict[str, ModalityResolutionOut]


class UserLanguagePreferencesUpdateRequest(BaseModel):
    """Update any subset of the 6 independent language preferences."""

    ui_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_explanation_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_voice_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_subtitle_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_question_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_answer_language: str | None = Field(default=None, min_length=2, max_length=16)
    bilingual_explanation_mode: BilingualMode | None = None


class UiLocalizationBundleOut(BaseModel):
    """UI localization dictionary with explicit English fallback coverage metrics."""

    requested_language: str
    effective_language: str
    rtl: bool
    coverage_pct: float
    translated_key_count: int
    total_key_count: int
    fallback_keys: list[str]
    strings: dict[str, str]


class GlossaryTermOut(BaseModel):
    id: UUID
    concept_key: str
    subject_area: str
    english_term: str
    language_code: str
    localized_term: str
    transliteration: str | None = None
    preserve_english_in_bilingual: bool
    latex_symbol: str | None = None
    review_status: str
    notes: str | None = None
    created_at: datetime


class GlossaryTermCreateRequest(BaseModel):
    concept_key: str = Field(min_length=2, max_length=96)
    subject_area: str = Field(min_length=2, max_length=48)
    english_term: str = Field(min_length=1, max_length=160)
    language_code: str = Field(min_length=2, max_length=16)
    localized_term: str = Field(min_length=1, max_length=200)
    transliteration: str | None = Field(default=None, max_length=200)
    preserve_english_in_bilingual: bool = True
    latex_symbol: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class NotationPreservationOut(BaseModel):
    math_preserved: bool
    science_preserved: bool
    all_preserved: bool
    math_preservation_score: float
    science_notation_score: float
    math_expressions: list[str]
    scientific_notations: list[str]
    si_unit_values: list[str]
    chemical_formulas: list[str]
    missing_math: list[str]
    missing_science: list[str]


class BilingualPreviewRequest(BaseModel):
    source_text: str = Field(min_length=5, max_length=4000)
    explanation_language: str = Field(default="hi", min_length=2, max_length=16)
    subtitle_language: str = Field(default="hi", min_length=2, max_length=16)
    voice_language: str = Field(default="hi", min_length=2, max_length=16)
    bilingual_mode: BilingualMode = "bilingual_stem_en"


class BilingualPreviewResponse(BaseModel):
    rendered_text: str
    bilingual_mode: str
    explanation_resolution: ModalityResolutionOut
    subtitle_resolution: ModalityResolutionOut
    voice_resolution: ModalityResolutionOut
    speakable_math_text: str
    notation_report: NotationPreservationOut
    matched_glossary_terms: list[dict[str, Any]]
    tts_provider_configured: bool
    stt_provider_configured: bool


class TranslationEntryOut(BaseModel):
    id: UUID
    resource_type: str
    resource_key: str
    source_language_code: str
    target_language_code: str
    source_text: str
    translated_text: str
    bilingual_text: str | None = None
    notation_preserved: bool
    terminology_warnings: list[str]
    status: str
    quality_score: float | None = None
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class TranslationEntryCreateRequest(BaseModel):
    resource_type: TranslationResourceType
    resource_key: str = Field(min_length=2, max_length=160)
    source_language_code: str = Field(default="en", min_length=2, max_length=16)
    target_language_code: str = Field(min_length=2, max_length=16)
    source_text: str = Field(min_length=2, max_length=5000)
    translated_text: str = Field(min_length=2, max_length=5000)
    bilingual_text: str | None = Field(default=None, max_length=5000)


class TranslationReviewRequest(BaseModel):
    decision: TranslationReviewDecision
    reviewer_notes: str | None = Field(default=None, max_length=1500)


class LanguageEvaluationSampleIn(BaseModel):
    sample_id: str = Field(min_length=1, max_length=64)
    source_text: str = Field(min_length=5, max_length=2000)
    candidate_text: str = Field(min_length=5, max_length=2000)


class LanguageQualityRunRequest(BaseModel):
    language_code: str = Field(min_length=2, max_length=16)
    modality: EvalModality = "bilingual"
    provider_name: str = Field(default="glossary_guided_pipeline", min_length=2, max_length=64)
    samples: list[LanguageEvaluationSampleIn] = Field(default_factory=list)


class LanguageQualityEvaluationOut(BaseModel):
    id: UUID
    language_code: str
    modality: str
    provider_name: str
    test_suite_version: str
    script_fidelity_score: float
    math_preservation_score: float
    science_notation_score: float
    terminology_accuracy_score: float
    fluency_score: float
    overall_score: float
    passed: bool
    sample_count: int
    findings: list[dict[str, Any]]
    evaluated_at: datetime


class STTRequestBody(BaseModel):
    language_code: str = Field(default="en", min_length=2, max_length=16)
    audio_base64: str | None = Field(default=None, max_length=4_000_000)
    mime_type: str = Field(default="audio/webm", max_length=64)
    browser_transcript_hint: str | None = Field(default=None, max_length=2000)
    classroom_session_id: UUID | None = None


class STTResponseOut(BaseModel):
    stt_available: bool
    transcript: str | None = None
    confidence: float | None = None
    requested_language: str
    effective_language: str
    fallback_applied: bool
    provider: str
    latency_ms: int
    audio_seconds: float
    is_fallback: bool
    fallback_mode: str | None = None
    limitation_notice: str | None = None


class VoiceProviderStatusOut(BaseModel):
    elevenlabs_configured: bool
    tts_model_id: str
    stt_model_id: str
    verified_tts_languages: list[str]
    verified_stt_languages: list[str]
    honest_status_notice: str
