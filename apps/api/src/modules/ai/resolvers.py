"""Modules 1, 2 & 3: Intent Router, PII-free Student Context Resolver & Curriculum Resolver."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ai.schemas import (
    AnonymizedStudentContext,
    CurriculumContext,
    IntentClassification,
    IntentType,
    TeachingMode,
)
from src.modules.assessment.public import get_student_progress_snapshot
from src.modules.curriculum.public import resolve_tutor_curriculum_context
from src.modules.identity.public import get_anonymized_student_context

_MATH_EXPR_HINT = re.compile(
    r"([=+\-*/^]|solve|integrate|differentiate|derivative|equation|factor|quadratic|root|simplify)",
    re.IGNORECASE,
)
_PHYSICS_UNIT_HINT = re.compile(
    r"\b(newton|joule|watt|velocity|acceleration|m/s|kg|ampere|ohm|volt|force|momentum|unit|dimension)\b",
    re.IGNORECASE,
)
_CHEM_EQ_HINT = re.compile(
    r"(->|→|\bbalance\b|\bmole\b|\bstoichiometry\b|\bH2O\b|\bCO2\b|\bH2\b|\bO2\b|\bFe\b|\bNaOH\b)",
    re.IGNORECASE,
)


def classify_intent(
    user_message: str, *, requested_mode: TeachingMode | None = None
) -> IntentClassification:
    """Classify pedagogical intent & required deterministic verification kind (Module 1)."""
    text = user_message.strip()
    lower = text.lower()

    verif_kind: Literal["math", "physics_units", "chemistry", "none"] = "none"
    needs_verif = False
    if _CHEM_EQ_HINT.search(text) and ("->" in text or "→" in text or "balance" in lower):
        verif_kind = "chemistry"
        needs_verif = True
    elif _PHYSICS_UNIT_HINT.search(text):
        verif_kind = "physics_units"
        needs_verif = True
    elif _MATH_EXPR_HINT.search(text):
        verif_kind = "math"
        needs_verif = True

    complexity: Literal["light", "reasoning"] = (
        "reasoning"
        if any(w in lower for w in ("derive", "prove", "jee", "advanced", "why", "multi-step"))
        else "light"
    )

    intent: IntentType
    if requested_mode == "socratic" or "guide me" in lower or "without giving answer" in lower:
        intent = "socratic"
    elif requested_mode == "hint" or "hint" in lower or "clue" in lower:
        intent = "hint"
    elif requested_mode == "practice" or "practice question" in lower or "give me a quiz" in lower:
        intent = "practice_generate"
    elif requested_mode == "step_by_step" or "step by step" in lower or "solve" in lower:
        intent = "step_by_step"
    elif requested_mode == "revision" or "revise" in lower or "flash" in lower:
        intent = "revision"
    elif requested_mode == "exam_prep" or any(w in lower for w in ("cbse", "jee", "neet", "board")):
        intent = "exam_prep"
    elif "?" in text and any(w in lower for w in ("wrong", "mistake", "stuck", "doubt", "error")):
        intent = "doubt"
    else:
        intent = "concept_explain"

    return IntentClassification(
        intent=intent,
        confidence=0.88,
        needs_verification=needs_verif,
        verification_kind=verif_kind,
        complexity=complexity,
    )


async def resolve_student_context(db: AsyncSession, student_id: UUID) -> AnonymizedStudentContext:
    """Module 2: Assemble strictly PII-stripped learner profile + mastery band."""
    id_ctx = await get_anonymized_student_context(db, student_id)
    progress = await get_student_progress_snapshot(db, student_id)
    curr = await resolve_tutor_curriculum_context(
        db,
        board_id=id_ctx.board_id,
        curriculum_version_id=id_ctx.curriculum_version_id,
        grade_id=id_ctx.grade_id,
    )

    acc = (
        round((progress.correct_attempts / progress.total_attempts) * 100.0, 1)
        if progress.total_attempts > 0
        else 0.0
    )
    band: Literal["developing", "proficient", "advanced"]
    if acc >= 80.0 and progress.total_attempts >= 3:
        band = "advanced"
    elif acc >= 50.0 and progress.total_attempts >= 2:
        band = "proficient"
    else:
        band = "developing"

    return AnonymizedStudentContext(
        grade_id=id_ctx.grade_id,
        grade_number=curr.grade_number,
        board_id=id_ctx.board_id,
        board_code=curr.board_code or "CBSE",
        curriculum_version_id=id_ctx.curriculum_version_id,
        primary_exam_target=id_ctx.primary_exam_target,
        preferred_explanation_language=id_ctx.preferred_explanation_language,
        preferred_question_language=id_ctx.preferred_question_language,
        preferred_answer_language=id_ctx.preferred_answer_language,
        practice_total_attempts=progress.total_attempts,
        practice_accuracy_pct=acc,
        mastery_band=band,
        is_minor=id_ctx.is_minor,
    )


async def resolve_curriculum_context(
    db: AsyncSession,
    *,
    student_ctx: AnonymizedStudentContext,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
    topic_id: UUID | None = None,
    concept_id: UUID | None = None,
) -> CurriculumContext:
    """Module 3: Resolve curriculum hierarchy names, objectives, and prerequisites."""
    resolved = await resolve_tutor_curriculum_context(
        db,
        board_id=student_ctx.board_id,
        curriculum_version_id=student_ctx.curriculum_version_id,
        grade_id=student_ctx.grade_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        topic_id=topic_id,
        concept_id=concept_id,
    )
    return CurriculumContext(
        board_code=resolved.board_code or student_ctx.board_code,
        grade_number=resolved.grade_number or student_ctx.grade_number,
        subject_id=resolved.subject_id,
        subject_name=resolved.subject_name,
        discipline=resolved.discipline,
        chapter_id=resolved.chapter_id,
        chapter_title=resolved.chapter_title,
        topic_id=resolved.topic_id,
        topic_title=resolved.topic_title,
        concept_id=resolved.concept_id,
        concept_title=resolved.concept_title,
        learning_objectives=list(resolved.learning_objectives),
        prerequisites=list(resolved.prerequisites),
    )
