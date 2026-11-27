"""Service layer for Parent & Guardian Portal (F-004, F-033).

Strictly enforces:
- Verifiable guardian consent before any student learning summary is returned.
- Hard privacy boundary: parents never receive raw AI chat transcripts.
- Cross-module reads exclusively through public module contracts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.identity.models import StudentProfile, User, UserProfile
from src.modules.identity.parent_logic import (
    generate_consent_verification_code,
    hash_consent_verification_code,
    sanitize_parent_privacy_settings,
    verify_consent_verification_code,
)
from src.modules.identity.parent_models import GuardianLink, ParentGoal
from src.modules.identity.parent_schemas import (
    GuardianConsentVerifyRequest,
    GuardianLinkRequest,
    GuardianLinkResponse,
    GuardianPrivacyUpdateRequest,
    ParentDashboardResponse,
    ParentGoalCreateRequest,
    ParentGoalResponse,
    ParentGoalUpdateRequest,
    ParentLearningSummaryResponse,
    ParentPrivacySettingsSchema,
    ParentUpcomingTestItem,
    ParentWeakTopicItem,
)


async def _load_user_label(db: AsyncSession, user_id: UUID) -> tuple[str, str]:
    user = await db.get(User, user_id)
    profile = await db.get(UserProfile, user_id)
    name = profile.display_name if profile else (user.email.split("@")[0] if user else "Learner")
    email = user.email if user else ""
    return name, email


def _to_link_response(
    link: GuardianLink,
    *,
    student_name: str,
    student_email: str,
    verification_code_preview: str | None = None,
) -> GuardianLinkResponse:
    safe_privacy = sanitize_parent_privacy_settings(None, existing=link.privacy_settings_jsonb)
    return GuardianLinkResponse(
        id=link.id,
        parent_user_id=link.parent_user_id,
        student_user_id=link.student_user_id,
        student_name=student_name,
        student_email=student_email,
        relationship_type=link.relationship_type,
        consent_status=link.consent_status,
        consent_granted_at=link.consent_granted_at,
        revoked_at=link.revoked_at,
        privacy_settings=ParentPrivacySettingsSchema(**safe_privacy),
        verification_code_preview=verification_code_preview,
        created_at=link.created_at,
    )


def _to_goal_response(goal: ParentGoal) -> ParentGoalResponse:
    return ParentGoalResponse(
        id=goal.id,
        parent_user_id=goal.parent_user_id,
        student_user_id=goal.student_user_id,
        title=goal.title,
        target_date=goal.target_date,
        target_minutes_per_day=goal.target_minutes_per_day,
        status=goal.status,
        created_at=goal.created_at,
    )


async def _require_verified_link(
    db: AsyncSession,
    *,
    parent_user_id: UUID,
    student_user_id: UUID,
) -> GuardianLink:
    link = await db.scalar(
        select(GuardianLink).where(
            GuardianLink.parent_user_id == parent_user_id,
            GuardianLink.student_user_id == student_user_id,
        )
    )
    if link is None:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="GUARDIAN_NOT_LINKED",
            message="You are not linked to this student account.",
        )
    if link.consent_status != "verified":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="GUARDIAN_CONSENT_REQUIRED",
            message="Verifiable guardian consent must be completed before accessing student summaries.",
        )
    return link


async def get_parent_dashboard(
    db: AsyncSession, caller: AuthenticatedUser
) -> ParentDashboardResponse:
    links = (
        await db.scalars(
            select(GuardianLink)
            .where(GuardianLink.parent_user_id == caller.id)
            .order_by(GuardianLink.created_at.desc())
        )
    ).all()
    link_items: list[GuardianLinkResponse] = []
    verified_count = 0
    pending_count = 0
    for link in links:
        name, email = await _load_user_label(db, link.student_user_id)
        if link.consent_status == "verified":
            verified_count += 1
        elif link.consent_status == "pending":
            pending_count += 1
        link_items.append(
            _to_link_response(link, student_name=name, student_email=email)
        )

    goals = (
        await db.scalars(
            select(ParentGoal).where(
                ParentGoal.parent_user_id == caller.id,
                ParentGoal.status == "active",
            )
        )
    ).all()

    return ParentDashboardResponse(
        parent_user_id=caller.id,
        linked_students=link_items,
        active_goals_count=len(goals),
        verified_links_count=verified_count,
        pending_links_count=pending_count,
    )


async def request_guardian_link(
    db: AsyncSession,
    caller: AuthenticatedUser,
    payload: GuardianLinkRequest,
) -> GuardianLinkResponse:
    student = await db.scalar(
        select(User).where(
            User.email == payload.student_email.lower().strip(),
            User.deleted_at.is_(None),
        )
    )
    if student is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="STUDENT_NOT_FOUND",
            message="No active student account matches that email address.",
        )
    if student.id == caller.id:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_GUARDIAN_LINK",
            message="A user cannot link themselves as their own guardian.",
        )

    existing = await db.scalar(
        select(GuardianLink).where(
            GuardianLink.parent_user_id == caller.id,
            GuardianLink.student_user_id == student.id,
        )
    )
    code = generate_consent_verification_code()
    salt = f"{caller.id}:{student.id}"
    code_hash = hash_consent_verification_code(code, salt=salt)

    if existing is not None:
        if existing.consent_status == "verified":
            name, email = await _load_user_label(db, student.id)
            return _to_link_response(existing, student_name=name, student_email=email)
        existing.relationship_type = payload.relationship_type
        existing.consent_status = "pending"
        existing.verification_code_hash = code_hash
        existing.revoked_at = None
        link = existing
    else:
        link = GuardianLink(
            parent_user_id=caller.id,
            student_user_id=student.id,
            relationship_type=payload.relationship_type,
            consent_status="pending",
            verification_code_hash=code_hash,
            privacy_settings_jsonb=sanitize_parent_privacy_settings(None),
        )
        db.add(link)

    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "parent",
        action="guardian_link.requested",
        resource_type="guardian_link",
        resource_id=str(link.id),
        tenant_id=caller.tenant_id,
        metadata={"student_user_id": str(student.id), "relationship_type": payload.relationship_type},
    )
    await db.commit()
    await db.refresh(link)

    name, email = await _load_user_label(db, student.id)
    return _to_link_response(
        link,
        student_name=name,
        student_email=email,
        verification_code_preview=code,
    )


async def verify_guardian_consent(
    db: AsyncSession,
    caller: AuthenticatedUser,
    link_id: UUID,
    payload: GuardianConsentVerifyRequest,
) -> GuardianLinkResponse:
    link = await db.get(GuardianLink, link_id)
    if link is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="GUARDIAN_LINK_NOT_FOUND",
            message="Guardian link record not found.",
        )
    if caller.id not in (link.parent_user_id, link.student_user_id) and not caller.has_role(
        "platform_admin"
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="Not authorized to verify consent for this guardian link.",
        )
    salt = f"{link.parent_user_id}:{link.student_user_id}"
    if not verify_consent_verification_code(
        payload.verification_code,
        salt=salt,
        expected_hash=link.verification_code_hash,
    ):
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_CONSENT_CODE",
            message="The guardian consent verification code is invalid.",
        )

    link.consent_status = "verified"
    link.consent_granted_at = datetime.now(UTC)
    link.revoked_at = None
    link.verification_code_hash = None

    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "parent",
        action="guardian_link.consent_verified",
        resource_type="guardian_link",
        resource_id=str(link.id),
        tenant_id=caller.tenant_id,
        metadata={"student_user_id": str(link.student_user_id)},
    )
    await db.commit()
    await db.refresh(link)
    name, email = await _load_user_label(db, link.student_user_id)
    return _to_link_response(link, student_name=name, student_email=email)


async def revoke_guardian_link(
    db: AsyncSession,
    caller: AuthenticatedUser,
    link_id: UUID,
) -> GuardianLinkResponse:
    link = await db.get(GuardianLink, link_id)
    if link is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="GUARDIAN_LINK_NOT_FOUND",
            message="Guardian link record not found.",
        )
    if caller.id not in (link.parent_user_id, link.student_user_id) and not caller.has_role(
        "platform_admin"
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="Not authorized to revoke this guardian link.",
        )
    link.consent_status = "revoked"
    link.revoked_at = datetime.now(UTC)
    link.verification_code_hash = None
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "parent",
        action="guardian_link.revoked",
        resource_type="guardian_link",
        resource_id=str(link.id),
        tenant_id=caller.tenant_id,
    )
    await db.commit()
    await db.refresh(link)
    name, email = await _load_user_label(db, link.student_user_id)
    return _to_link_response(link, student_name=name, student_email=email)


async def update_guardian_privacy(
    db: AsyncSession,
    caller: AuthenticatedUser,
    link_id: UUID,
    payload: GuardianPrivacyUpdateRequest,
) -> GuardianLinkResponse:
    link = await db.get(GuardianLink, link_id)
    if link is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="GUARDIAN_LINK_NOT_FOUND",
            message="Guardian link record not found.",
        )
    if caller.id not in (link.parent_user_id, link.student_user_id) and not caller.has_role(
        "platform_admin"
    ):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="Not authorized to update privacy controls for this link.",
        )
    requested = payload.model_dump(exclude_none=True)
    link.privacy_settings_jsonb = sanitize_parent_privacy_settings(
        requested, existing=link.privacy_settings_jsonb
    )
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "parent",
        action="guardian_link.privacy_updated",
        resource_type="guardian_link",
        resource_id=str(link.id),
        tenant_id=caller.tenant_id,
        metadata=link.privacy_settings_jsonb,
    )
    await db.commit()
    await db.refresh(link)
    name, email = await _load_user_label(db, link.student_user_id)
    return _to_link_response(link, student_name=name, student_email=email)


async def get_student_learning_summary_for_parent(
    db: AsyncSession,
    caller: AuthenticatedUser,
    student_user_id: UUID,
    *,
    upcoming_items: list[ParentUpcomingTestItem] | None = None,
) -> ParentLearningSummaryResponse:
    """Build a privacy-preserving learning summary for a consent-verified child.

    Never reads or returns raw student AI chat transcripts (`ai_messages`).
    """
    link = await _require_verified_link(
        db, parent_user_id=caller.id, student_user_id=student_user_id
    )
    privacy = sanitize_parent_privacy_settings(None, existing=link.privacy_settings_jsonb)
    student_name, _ = await _load_user_label(db, student_user_id)
    sp = await db.get(StudentProfile, student_user_id)

    from src.modules.assessment.public import get_student_progress_snapshot
    from src.modules.homework.public import get_student_homework_summary
    from src.modules.learning.public import (
        get_concept_mastery_scores_map,
        list_weak_concept_summaries,
    )
    from src.modules.revision.public import get_student_revision_summary
    from src.modules.teacher.public import list_upcoming_assignments_for_student

    if privacy["share_learning_summary"]:
        progress = await get_student_progress_snapshot(db, student_user_id)
        mastery_map = await get_concept_mastery_scores_map(db, student_user_id)
        revision = await get_student_revision_summary(db, student_user_id)
        homework = await get_student_homework_summary(db, student_user_id)
    else:
        progress = None
        mastery_map = {}
        revision = None
        homework = None

    if upcoming_items is None and privacy["share_upcoming_tests"]:
        upcoming_raw = await list_upcoming_assignments_for_student(db, student_user_id)
        upcoming_items = [
            ParentUpcomingTestItem(
                id=item.assignment_id,
                title=item.title,
                assignment_type=item.assignment_type,
                due_at=item.due_at,
                max_marks=item.max_marks,
            )
            for item in upcoming_raw
        ]

    total_attempts = progress.total_attempts if progress else 0
    correct_attempts = progress.correct_attempts if progress else 0
    accuracy_pct = round((correct_attempts / total_attempts) * 100.0, 2) if total_attempts else 0.0
    mastery_avg = (
        round(sum(mastery_map.values()) / len(mastery_map), 2) if mastery_map else 0.0
    )
    mastered_count = sum(1 for score in mastery_map.values() if score >= 80.0)

    weak_topics: list[ParentWeakTopicItem] = []
    if privacy["share_weak_topics"] and privacy["share_learning_summary"]:
        weak_rows = await list_weak_concept_summaries(db, student_user_id, threshold=60.0)
        weak_topics = [
            ParentWeakTopicItem(
                concept_id=w.concept_id,
                mastery_score=w.mastery_score,
                band=w.band,
            )
            for w in weak_rows[:12]
        ]

    goals = (
        await db.scalars(
            select(ParentGoal)
            .where(
                ParentGoal.parent_user_id == caller.id,
                ParentGoal.student_user_id == student_user_id,
            )
            .order_by(ParentGoal.created_at.desc())
        )
    ).all()

    return ParentLearningSummaryResponse(
        student_user_id=student_user_id,
        student_name=student_name,
        consent_status=link.consent_status,
        privacy_notice=(
            "Privacy-preserving academic summary only. Raw AI tutor and homework chat "
            "transcripts are strictly excluded by child-safety policy."
        ),
        privacy_settings=ParentPrivacySettingsSchema(**privacy),
        onboarding_completed=bool(sp and sp.onboarding_completed_at is not None),
        primary_exam_target=sp.primary_exam_target if sp else "cbse_board",
        daily_study_minutes_target=sp.daily_study_minutes_target if sp else 60,
        practice_total_attempts=total_attempts,
        practice_correct_attempts=correct_attempts,
        practice_accuracy_pct=accuracy_pct,
        practice_sessions_completed=progress.total_sessions if progress else 0,
        mastery_average_pct=mastery_avg,
        mastered_concepts_count=mastered_count,
        weak_topics=weak_topics,
        revision_due_flashcards=revision.due_flashcards_count if revision else 0,
        revision_total_flashcards=revision.total_flashcards_count if revision else 0,
        revision_active_study_plans=revision.active_study_plans_count if revision else 0,
        revision_completed_plan_items=revision.completed_plan_items_count if revision else 0,
        homework_total_submissions=homework.total_submissions if homework else 0,
        homework_evaluated_submissions=homework.evaluated_submissions if homework else 0,
        upcoming_assessments=upcoming_items if (privacy["share_upcoming_tests"] and upcoming_items) else [],
        goals=[_to_goal_response(g) for g in goals],
        generated_at=datetime.now(UTC),
    )


async def list_parent_goals(
    db: AsyncSession, caller: AuthenticatedUser, student_user_id: UUID | None = None
) -> list[ParentGoalResponse]:
    stmt = select(ParentGoal).where(ParentGoal.parent_user_id == caller.id)
    if student_user_id is not None:
        await _require_verified_link(
            db, parent_user_id=caller.id, student_user_id=student_user_id
        )
        stmt = stmt.where(ParentGoal.student_user_id == student_user_id)
    rows = (await db.scalars(stmt.order_by(ParentGoal.created_at.desc()))).all()
    return [_to_goal_response(g) for g in rows]


async def create_parent_goal(
    db: AsyncSession, caller: AuthenticatedUser, payload: ParentGoalCreateRequest
) -> ParentGoalResponse:
    await _require_verified_link(
        db, parent_user_id=caller.id, student_user_id=payload.student_user_id
    )
    goal = ParentGoal(
        parent_user_id=caller.id,
        student_user_id=payload.student_user_id,
        title=payload.title.strip(),
        target_date=payload.target_date,
        target_minutes_per_day=payload.target_minutes_per_day,
        status="active",
    )
    db.add(goal)
    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "parent",
        action="parent_goal.created",
        resource_type="parent_goal",
        resource_id=str(goal.id),
        tenant_id=caller.tenant_id,
        metadata={"student_user_id": str(payload.student_user_id)},
    )
    await db.commit()
    await db.refresh(goal)
    return _to_goal_response(goal)


async def update_parent_goal(
    db: AsyncSession,
    caller: AuthenticatedUser,
    goal_id: UUID,
    payload: ParentGoalUpdateRequest,
) -> ParentGoalResponse:
    goal = await db.get(ParentGoal, goal_id)
    if goal is None or goal.parent_user_id != caller.id:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PARENT_GOAL_NOT_FOUND",
            message="Parent goal not found.",
        )
    if payload.title is not None:
        goal.title = payload.title.strip()
    if payload.target_date is not None:
        goal.target_date = payload.target_date
    if payload.target_minutes_per_day is not None:
        goal.target_minutes_per_day = payload.target_minutes_per_day
    if payload.status is not None:
        goal.status = payload.status
    await db.commit()
    await db.refresh(goal)
    return _to_goal_response(goal)
