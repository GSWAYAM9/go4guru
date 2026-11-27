"""Public contract boundary for identity module."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.models import Role, StudentProfile, User, UserProfile, UserRole
from src.modules.identity.parent_router import parent_router
from src.modules.identity.router import admin_identity_router, auth_router, users_router

MODULE_NAME = "identity"
MODULE_PHASE = "Phase 1 + Phase 7 (Guardian & Parent Portal)"
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


@dataclass(frozen=True, slots=True)
class UserDisplayContract:
    """Authorized user summary contract for Teacher, Mentor, and Institution rosters."""

    user_id: UUID
    email: str
    display_name: str
    status: str


async def resolve_user_by_email(db: AsyncSession, email: str) -> UserDisplayContract | None:
    """Resolve an active user by email address via public identity contract."""
    user = await db.scalar(
        select(User).where(
            User.email == email.lower().strip(),
            User.deleted_at.is_(None),
        )
    )
    if user is None:
        return None
    profile = await db.get(UserProfile, user.id)
    return UserDisplayContract(
        user_id=user.id,
        email=user.email,
        display_name=profile.display_name if profile else user.email.split("@")[0],
        status=user.status,
    )


async def get_user_displays_map(
    db: AsyncSession, user_ids: list[UUID]
) -> dict[UUID, UserDisplayContract]:
    """Batch-fetch user display labels for authorized roster views."""
    if not user_ids:
        return {}
    unique_ids = list(dict.fromkeys(user_ids))
    users = (await db.scalars(select(User).where(User.id.in_(unique_ids)))).all()
    profiles = (
        await db.scalars(select(UserProfile).where(UserProfile.user_id.in_(unique_ids)))
    ).all()
    profile_map = {p.user_id: p for p in profiles}
    return {
        u.id: UserDisplayContract(
            user_id=u.id,
            email=u.email,
            display_name=(
                profile_map[u.id].display_name if u.id in profile_map else u.email.split("@")[0]
            ),
            status=u.status,
        )
        for u in users
    }


async def ensure_user_tenant_role(
    db: AsyncSession,
    *,
    user_id: UUID,
    role_code: str,
    tenant_id: UUID,
    granted_by: UUID | None = None,
) -> bool:
    """Idempotently grant a tenant-scoped RBAC role to an existing user."""
    role = await db.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        return False
    existing = await db.scalar(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
            UserRole.tenant_id == tenant_id,
            UserRole.revoked_at.is_(None),
        )
    )
    if existing is not None:
        return False
    db.add(
        UserRole(
            user_id=user_id,
            role_id=role.id,
            tenant_id=tenant_id,
            granted_by=granted_by,
        )
    )
    return True


@dataclass(frozen=True, slots=True)
class UserLanguagePreferencesContract:
    """User's 6 independent multilingual preferences + bilingual STEM mode."""

    ui_language: str
    preferred_explanation_language: str
    preferred_voice_language: str
    preferred_subtitle_language: str
    preferred_question_language: str
    preferred_answer_language: str
    bilingual_explanation_mode: str


async def get_user_language_preferences(
    db: AsyncSession, user_id: UUID
) -> UserLanguagePreferencesContract:
    """Read a user's 6 independent language preferences via public identity boundary."""
    profile = await db.get(UserProfile, user_id)
    if profile is None:
        return UserLanguagePreferencesContract(
            ui_language="en",
            preferred_explanation_language="en",
            preferred_voice_language="en",
            preferred_subtitle_language="en",
            preferred_question_language="en",
            preferred_answer_language="en",
            bilingual_explanation_mode="bilingual_stem_en",
        )
    return UserLanguagePreferencesContract(
        ui_language=profile.ui_language,
        preferred_explanation_language=profile.preferred_explanation_language,
        preferred_voice_language=profile.preferred_voice_language,
        preferred_subtitle_language=profile.preferred_subtitle_language,
        preferred_question_language=profile.preferred_question_language,
        preferred_answer_language=profile.preferred_answer_language,
        bilingual_explanation_mode=profile.bilingual_explanation_mode,
    )


async def update_user_language_preferences(
    db: AsyncSession,
    user_id: UUID,
    *,
    ui_language: str | None = None,
    preferred_explanation_language: str | None = None,
    preferred_voice_language: str | None = None,
    preferred_subtitle_language: str | None = None,
    preferred_question_language: str | None = None,
    preferred_answer_language: str | None = None,
    bilingual_explanation_mode: str | None = None,
) -> UserLanguagePreferencesContract:
    """Persist validated independent language preferences on UserProfile."""
    profile = await db.get(UserProfile, user_id)
    if profile is None:
        return await get_user_language_preferences(db, user_id)
    if ui_language is not None:
        profile.ui_language = ui_language
    if preferred_explanation_language is not None:
        profile.preferred_explanation_language = preferred_explanation_language
    if preferred_voice_language is not None:
        profile.preferred_voice_language = preferred_voice_language
    if preferred_subtitle_language is not None:
        profile.preferred_subtitle_language = preferred_subtitle_language
    if preferred_question_language is not None:
        profile.preferred_question_language = preferred_question_language
    if preferred_answer_language is not None:
        profile.preferred_answer_language = preferred_answer_language
    if bilingual_explanation_mode is not None:
        profile.bilingual_explanation_mode = bilingual_explanation_mode
    await db.flush()
    return UserLanguagePreferencesContract(
        ui_language=profile.ui_language,
        preferred_explanation_language=profile.preferred_explanation_language,
        preferred_voice_language=profile.preferred_voice_language,
        preferred_subtitle_language=profile.preferred_subtitle_language,
        preferred_question_language=profile.preferred_question_language,
        preferred_answer_language=profile.preferred_answer_language,
        bilingual_explanation_mode=profile.bilingual_explanation_mode,
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "AnonymizedStudentContextContract",
    "StudentOnboardingContract",
    "UserDisplayContract",
    "UserLanguagePreferencesContract",
    "admin_identity_router",
    "auth_router",
    "ensure_user_tenant_role",
    "get_anonymized_student_context",
    "get_student_onboarding_summary",
    "get_user_displays_map",
    "get_user_language_preferences",
    "parent_router",
    "resolve_user_by_email",
    "update_user_language_preferences",
    "users_router",
]
