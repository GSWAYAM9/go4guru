"""Public contract boundary for ai module (Phase 3 AI Tutor & Grounded AI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.config import Settings
from src.modules.ai.evals import run_golden_evaluation_suite
from src.modules.ai.pedagogy import (
    build_pedagogical_plan,
    run_deterministic_verification_for_query,
    synthesize_grounded_fallback,
)
from src.modules.ai.provider import (
    AIRouterGateway,
    ProviderInvocationRequest,
    ProviderInvocationResult,
)
from src.modules.ai.resolvers import classify_intent, resolve_student_context
from src.modules.ai.retrieval import HybridRetrievalService
from src.modules.ai.router import ai_admin_router, ai_router
from src.modules.ai.safety import (
    evaluate_input_safety,
    evaluate_output_safety,
    scrub_pii_text,
)
from src.modules.ai.schemas import CurriculumContext, SafetyVerdict, VerificationCheckResult
from src.modules.ai.verifier import (
    check_algebraic_equivalence,
    verify_chemical_equation,
    verify_math_expression,
    verify_physics_units,
)

MODULE_NAME = "ai"
MODULE_PHASE = "Phase 3"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class ClassroomDoubtAnswerContract:
    """Grounded, safety-checked answer for Live Classroom doubt interruptions."""

    answer_markdown: str
    verification_status: str
    safety_verdict: str
    citations: tuple[dict[str, Any], ...]


async def resolve_classroom_doubt_answer(
    db: AsyncSession,
    *,
    settings: Settings,
    caller: AuthenticatedUser,
    doubt_text: str,
    lesson_title: str,
    subject_id: UUID | None = None,
    chapter_id: UUID | None = None,
) -> ClassroomDoubtAnswerContract:
    """Safely handle live classroom doubt interruptions via AI Safety + RAG + Verifier."""
    _ = settings
    safety = evaluate_input_safety(doubt_text, is_minor=caller.is_minor)
    if safety.action != "allow":
        return ClassroomDoubtAnswerContract(
            answer_markdown=safety.safe_message or "Blocked by child safety policy.",
            verification_status="not_applicable",
            safety_verdict=safety.action,
            citations=(),
        )
    stu_ctx = await resolve_student_context(db, caller.id)
    intent = classify_intent(doubt_text, requested_mode="explain")
    curr_ctx = CurriculumContext(
        board_code=stu_ctx.board_code,
        grade_number=stu_ctx.grade_number,
        subject_id=subject_id,
        chapter_id=chapter_id,
        chapter_title=lesson_title,
    )
    chunks = await HybridRetrievalService(db).retrieve(
        query=doubt_text,
        grade_id=stu_ctx.grade_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        language_code=stu_ctx.preferred_explanation_language,
        top_k=3,
    )
    plan = build_pedagogical_plan(
        intent=intent,
        mode_override="explain",
        student_ctx=stu_ctx,
        curriculum_ctx=curr_ctx,
    )
    verif = run_deterministic_verification_for_query(query=doubt_text, intent=intent)
    out = synthesize_grounded_fallback(
        plan=plan,
        intent=intent,
        curriculum_ctx=curr_ctx,
        chunks=chunks,
        query=scrub_pii_text(doubt_text),
        verif=verif,
        provider_errors=[],
    )
    return ClassroomDoubtAnswerContract(
        answer_markdown=out.answer_markdown,
        verification_status=verif.status,
        safety_verdict="allow",
        citations=tuple(c.model_dump(mode="json") for c in chunks),
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "AIRouterGateway",
    "ClassroomDoubtAnswerContract",
    "CurriculumContext",
    "ProviderInvocationRequest",
    "ProviderInvocationResult",
    "SafetyVerdict",
    "VerificationCheckResult",
    "ai_admin_router",
    "ai_router",
    "check_algebraic_equivalence",
    "evaluate_input_safety",
    "evaluate_output_safety",
    "resolve_classroom_doubt_answer",
    "run_golden_evaluation_suite",
    "scrub_pii_text",
    "verify_chemical_equation",
    "verify_math_expression",
    "verify_physics_units",
]
