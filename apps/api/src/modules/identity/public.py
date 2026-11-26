"""Public contract boundary for identity module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.models import StudentProfile, User, UserProfile
from src.modules.identity.router import admin_identity_router, auth_router, users_router

MODULE_NAME = "identity"
MODULE_PHASE = "Phase 1"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class AnonymizedStudentContextContract:
    """Strictly PII-free academic & language context for AI orchestration."""

    grade_id: UUID | None
    board_id: UUID | None
    curriculum_version_id: UUID | None
    primary_exam_target: str
    preferred_explanation_language: str
    preferred_question_language: str
    preferred_answer_language: str
    is_minor: bool


async def get_anonymized_student_context(
    db: AsyncSession, student_id: UUID
) -> AnonymizedStudentContextContract:
    """Return ONLY non-PII academic preferences and minor flag (never name/email/phone)."""
    user = await db.get(User, student_id)
    profile = await db.get(UserProfile, student_id)
    sp = await db.get(StudentProfile, student_id)
    return AnonymizedStudentContextContract(
        grade_id=sp.grade_id if sp else None,
        board_id=sp.board_id if sp else None,
        curriculum_version_id=sp.curriculum_version_id if sp else None,
        primary_exam_target=sp.primary_exam_target if sp else "cbse_board",
        preferred_explanation_language=(
            profile.preferred_explanation_language if profile else "en"
        ),
        preferred_question_language=profile.preferred_question_language if profile else "en",
        preferred_answer_language=profile.preferred_answer_language if profile else "en",
        is_minor=bool(user.is_minor) if user else True,
    )


@dataclass(frozen=True, slots=True)
class StudentOnboardingContract:
    onboarding_completed: bool
    primary_exam_target: str
    daily_study_minutes_target: int


async def get_student_onboarding_summary(
    db: AsyncSession, student_id: UUID
) -> StudentOnboardingContract:
    """Return student's real onboarding state without exposing identity internals."""
    sp = await db.get(StudentProfile, student_id)
    if sp is None:
        return StudentOnboardingContract(
            onboarding_completed=False,
            primary_exam_target="cbse_board",
            daily_study_minutes_target=60,
        )
    return StudentOnboardingContract(
        onboarding_completed=sp.onboarding_completed_at is not None,
        primary_exam_target=sp.primary_exam_target,
        daily_study_minutes_target=sp.daily_study_minutes_target,
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "AnonymizedStudentContextContract",
    "StudentOnboardingContract",
    "admin_identity_router",
    "auth_router",
    "get_anonymized_student_context",
    "get_student_onboarding_summary",
    "users_router",
]
