"""Pydantic v2 contracts for Live AI Classroom, LessonArtifacts, Whiteboard & Voice."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

ClassroomState = Literal[
    "IDLE",
    "READY",
    "PLAYING_SEGMENT",
    "PAUSED",
    "CHECKPOINT_WAIT",
    "DOUBT_INTERRUPTION",
    "COMPLETED",
]

WhiteboardOpcode = Literal[
    "WRITE_TEXT",
    "INSERT_FORMULA",
    "DRAW_LINE",
    "DRAW_ARROW",
    "DRAW_SHAPE",
    "DRAW_GRAPH",
    "DRAW_DIAGRAM",
    "INSERT_IMAGE",
    "HIGHLIGHT",
    "ERASE",
    "MOVE",
    "TRANSFORM",
]

_UNSAFE_MARKUP_RE = re.compile(r"<\s*script|javascript:|onerror=|onload=|eval\s*\(", re.IGNORECASE)


def _contains_unsafe(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_UNSAFE_MARKUP_RE.search(value))
    if isinstance(value, list):
        return any(_contains_unsafe(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_unsafe(v) for v in value.values())
    return False


class WhiteboardActionSchema(BaseModel):
    """Strictly validated canvas action opcode (zero arbitrary code execution)."""

    id: str = Field(min_length=1, max_length=80)
    opcode: WhiteboardOpcode
    sequence: int = Field(ge=0)
    at_ms: int = Field(default=0, ge=0, le=3_600_000)
    aria_summary: str = Field(min_length=1, max_length=400)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_safety(self) -> WhiteboardActionSchema:
        if _contains_unsafe(self.aria_summary) or _contains_unsafe(self.payload):
            raise ValueError("Unsafe markup or script pattern rejected from whiteboard action.")
        if self.opcode == "INSERT_IMAGE":
            if "url" in self.payload or "src" in self.payload:
                raise ValueError("External URLs are forbidden in INSERT_IMAGE; use asset_id.")
            if not self.payload.get("asset_id"):
                raise ValueError("INSERT_IMAGE requires a vetted asset_id.")
        return self


class SubtitleCue(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=500)


class CheckpointOption(BaseModel):
    key: str
    text: str


class CheckpointSpec(BaseModel):
    question_type: Literal["mcq_single", "numerical"] = "mcq_single"
    prompt: str
    options: list[CheckpointOption] = Field(default_factory=list)
    correct_key: str | None = None
    expected_value: float | None = None
    remediation_hint: str


class LessonSegment(BaseModel):
    sequence: int = Field(ge=1)
    type: Literal[
        "concept_explanation",
        "worked_example",
        "checkpoint_question",
        "summary",
    ]
    title: str = Field(min_length=2, max_length=200)
    narration: str = Field(min_length=5)
    subtitle_cues: list[SubtitleCue] = Field(default_factory=list)
    canvas_actions: list[WhiteboardActionSchema] = Field(default_factory=list)
    checkpoint: CheckpointSpec | None = None
    duration_ms: int = Field(ge=2000, le=600_000)


class LessonArtifact(BaseModel):
    """Canonical schema-validated Live Classroom Lesson Artifact (Section 1)."""

    schema_version: str = "1.0.0"
    title: str = Field(min_length=3, max_length=240)
    curriculum_context: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"
    voice_language: str = "en"
    subtitle_language: str = "en"
    objectives: list[str] = Field(min_length=1)
    segments: list[LessonSegment] = Field(min_length=1)


# ------------------------------------------------------------------
# HTTP & WebSocket API Contracts
# ------------------------------------------------------------------
class LanguageCapabilityOut(BaseModel):
    language_code: str
    display_name: str
    native_name: str
    rtl: bool
    text_quality_tier: str
    translation_status: str
    tts_supported: bool
    stt_supported: bool
    voice_provider: str | None = None
    pronunciation_tier: str | None = None
    subtitle_supported: bool
    academic_review_status: str
    known_limitations: str | None = None


class LessonGenerateRequest(BaseModel):
    topic_title: str = Field(min_length=2, max_length=200)
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    concept_id: UUID | None = None
    language_code: str = Field(default="en", max_length=16)
    voice_language: str = Field(default="en", max_length=16)
    subtitle_language: str = Field(default="en", max_length=16)


class LessonPlanOut(BaseModel):
    id: UUID
    title: str
    language_code: str
    voice_language: str
    subtitle_language: str
    schema_version: str
    artifact: LessonArtifact
    created_at: datetime


class ClassroomSessionCreateRequest(BaseModel):
    lesson_plan_id: UUID
    playback_speed: float = Field(default=1.0, ge=0.75, le=1.75)
    voice_language: str | None = Field(default=None, max_length=16)
    subtitle_language: str | None = Field(default=None, max_length=16)


class ClassroomControlRequest(BaseModel):
    action: Literal[
        "play",
        "pause",
        "resume",
        "repeat",
        "next",
        "previous",
        "seek",
        "set_speed",
        "set_language",
        "complete",
    ]
    playback_position_ms: int | None = Field(default=None, ge=0)
    playback_speed: float | None = Field(default=None, ge=0.75, le=1.75)
    voice_language: str | None = Field(default=None, max_length=16)
    subtitle_language: str | None = Field(default=None, max_length=16)


class CheckpointSubmitRequest(BaseModel):
    selected_key: str | None = None
    numeric_value: float | None = None


class CheckpointSubmitResponse(BaseModel):
    passed: bool
    feedback: str
    session: ClassroomSessionDetailOut


class DoubtInterruptRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class DoubtInterruptResponse(BaseModel):
    answer_markdown: str
    verification_status: str
    safety_verdict: str
    overlay_actions: list[WhiteboardActionSchema]
    session: ClassroomSessionDetailOut


class WhiteboardEventOut(BaseModel):
    id: UUID
    segment_seq: int
    sequence_no: int
    actor: str
    action_type: str
    action: WhiteboardActionSchema
    is_undone: bool
    created_at: datetime


class WhiteboardDrawRequest(BaseModel):
    action: WhiteboardActionSchema


class WhiteboardSnapshotOut(BaseModel):
    id: UUID
    segment_seq: int
    version: int
    actions: list[WhiteboardActionSchema]
    created_at: datetime


class TTSRequestBody(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    language_code: str = Field(default="en", max_length=16)
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.75, le=1.75)
    classroom_session_id: UUID | None = None


class TTSResponseOut(BaseModel):
    audio_available: bool
    audio_url: str | None = None
    cache_key: str | None = None
    normalized_speakable_text: str
    provider: str
    voice_id: str
    language_code: str
    characters_count: int
    estimated_duration_ms: int
    cache_hit: bool
    is_fallback: bool
    fallback_mode: str | None = None
    limitation_notice: str | None = None


class ClassroomSessionSummaryOut(BaseModel):
    id: UUID
    lesson_plan_id: UUID
    title: str
    state: ClassroomState
    current_segment_seq: int
    total_segments: int
    playback_speed: float
    voice_language: str
    subtitle_language: str
    started_at: datetime
    last_active_at: datetime
    completed_at: datetime | None = None


class ClassroomSessionDetailOut(BaseModel):
    id: UUID
    lesson_plan_id: UUID
    state: ClassroomState
    current_segment_seq: int
    playback_position_ms: int
    playback_speed: float
    voice_language: str
    subtitle_language: str
    checkpoint_results: dict[str, Any]
    lesson_artifact: LessonArtifact
    active_whiteboard_actions: list[WhiteboardActionSchema]
    can_undo: bool
    can_redo: bool
    tts_preview: TTSResponseOut | None = None
    started_at: datetime
    last_active_at: datetime
    completed_at: datetime | None = None
