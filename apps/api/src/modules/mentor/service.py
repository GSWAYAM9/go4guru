"""Service layer for Mentor Ecosystem (F-032).

Strictly enforces backend authorization:
- Mentors may ONLY view or manage students actively assigned to them.
- Unauthorized student lookups raise 403 MENTOR_STUDENT_FORBIDDEN.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.assessment.public import get_student_progress_snapshot
from src.modules.homework.public import get_student_homework_summary
from src.modules.identity.public import (
    get_student_onboarding_summary,
    get_user_displays_map,
    resolve_user_by_email,
)
from src.modules.learning.public import (
    get_concept_mastery_scores_map,
    list_weak_concept_summaries,
)
from src.modules.mentor.models import (
    MentorAssignment,
    MentorFollowUp,
    MentorGoal,
    MentorSession,
)
from src.modules.mentor.schemas import (
    MentorAssignStudentRequest,
    MentorDashboardResponse,
    MentorFollowUpCreateRequest,
    MentorFollowUpResponse,
    MentorFollowUpUpdateRequest,
    MentorGoalCreateRequest,
    MentorGoalResponse,
    MentorGoalUpdateRequest,
    MentorSessionCreateRequest,
    MentorSessionResponse,
    MentorSessionUpdateRequest,
    MentorStudentReviewResponse,
    MentorStudentRosterItem,
    MentorWeakConceptItem,
)
from src.modules.revision.public import get_student_revision_summary


async def _assert_mentor_assigned_to_student(
    db: AsyncSession, caller: AuthenticatedUser, student_id: UUID
) -> MentorAssignment | None:
    if caller.has_role("platform_admin"):
        return await db.scalar(
            select(MentorAssignment).where(
                MentorAssignment.student_id == student_id,
                MentorAssignment.status == "active",
            )
        )
    assignment = await db.scalar(
        select(MentorAssignment).where(
            MentorAssignment.mentor_id == caller.id,
            MentorAssignment.student_id == student_id,
            MentorAssignment.status == "active",
        )
    )
    if assignment is None:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="MENTOR_STUDENT_FORBIDDEN",
            message="Mentors may only access students explicitly assigned to them.",
        )
    if caller.tenant_id and assignment.tenant_id and assignment.tenant_id != caller.tenant_id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_FORBIDDEN",
            message="Cross-tenant mentor access is forbidden.",
        )
    return assignment


def _to_goal(g: MentorGoal) -> MentorGoalResponse:
    return MentorGoalResponse(
        id=g.id,
        mentor_id=g.mentor_id,
        student_id=g.student_id,
        title=g.title,
        description=g.description,
        target_date=g.target_date,
        progress_pct=g.progress_pct,
        status=g.status,
        created_at=g.created_at,
    )


def _to_session(s: MentorSession) -> MentorSessionResponse:
    return MentorSessionResponse(
        id=s.id,
        mentor_id=s.mentor_id,
        student_id=s.student_id,
        scheduled_at=s.scheduled_at,
        duration_minutes=s.duration_minutes,
        status=s.status,
        summary_notes=s.summary_notes,
        recommendations=[str(x) for x in (s.recommendations_jsonb or [])],
        created_at=s.created_at,
    )


def _to_followup(f: MentorFollowUp) -> MentorFollowUpResponse:
    return MentorFollowUpResponse(
        id=f.id,
        session_id=f.session_id,
        mentor_id=f.mentor_id,
        student_id=f.student_id,
        title=f.title,
        due_date=f.due_date,
        status=f.status,
        created_at=f.created_at,
    )


async def get_mentor_dashboard(
    db: AsyncSession, caller: AuthenticatedUser
) -> MentorDashboardResponse:
    stmt = select(MentorAssignment).where(MentorAssignment.status == "active")
    if not caller.has_role("platform_admin"):
        stmt = stmt.where(MentorAssignment.mentor_id == caller.id)
    assignments = (await db.scalars(stmt.order_by(MentorAssignment.created_at.desc()))).all()
    displays = await get_user_displays_map(db, [a.student_id for a in assignments])

    roster: list[MentorStudentRosterItem] = []
    total_active_goals = 0
    total_open_followups = 0
    for a in assignments:
        g_cnt = int(
            await db.scalar(
                select(func.count(MentorGoal.id)).where(
                    MentorGoal.mentor_id == a.mentor_id,
                    MentorGoal.student_id == a.student_id,
                    MentorGoal.status == "active",
                )
            )
            or 0
        )
        f_cnt = int(
            await db.scalar(
                select(func.count(MentorFollowUp.id)).where(
                    MentorFollowUp.mentor_id == a.mentor_id,
                    MentorFollowUp.student_id == a.student_id,
                    MentorFollowUp.status != "completed",
                )
            )
            or 0
        )
        total_active_goals += g_cnt
        total_open_followups += f_cnt
        disp = displays.get(a.student_id)
        roster.append(
            MentorStudentRosterItem(
                assignment_id=a.id,
                student_id=a.student_id,
                student_name=disp.display_name if disp else "Student",
                student_email=disp.email if disp else "",
                status=a.status,
                notes=a.notes,
                active_goals_count=g_cnt,
                open_follow_ups_count=f_cnt,
                created_at=a.created_at,
            )
        )

    sess_stmt = select(func.count(MentorSession.id)).where(MentorSession.status == "scheduled")
    if not caller.has_role("platform_admin"):
        sess_stmt = sess_stmt.where(MentorSession.mentor_id == caller.id)
    upcoming_sessions = int(await db.scalar(sess_stmt) or 0)

    return MentorDashboardResponse(
        mentor_id=caller.id,
        assigned_students_count=len(roster),
        active_goals_count=total_active_goals,
        upcoming_sessions_count=upcoming_sessions,
        open_follow_ups_count=total_open_followups,
        students=roster,
    )


async def assign_student_to_mentor(
    db: AsyncSession, caller: AuthenticatedUser, payload: MentorAssignStudentRequest
) -> MentorStudentRosterItem:
    student = await resolve_user_by_email(db, payload.student_email)
    if student is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="STUDENT_NOT_FOUND",
            message="No active student account matches that email.",
        )
    existing = await db.scalar(
        select(MentorAssignment).where(
            MentorAssignment.mentor_id == caller.id,
            MentorAssignment.student_id == student.user_id,
        )
    )
    if existing is not None:
        existing.status = "active"
        existing.notes = payload.notes
        assignment = existing
    else:
        assignment = MentorAssignment(
            tenant_id=caller.tenant_id,
            mentor_id=caller.id,
            student_id=student.user_id,
            status="active",
            assigned_by=caller.id,
            notes=payload.notes,
        )
        db.add(assignment)

    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "mentor",
        action="mentor_assignment.upserted",
        resource_type="mentor_assignment",
        resource_id=str(assignment.id),
        tenant_id=caller.tenant_id,
        metadata={"student_id": str(student.user_id)},
    )
    await db.commit()
    await db.refresh(assignment)
    return MentorStudentRosterItem(
        assignment_id=assignment.id,
        student_id=student.user_id,
        student_name=student.display_name,
        student_email=student.email,
        status=assignment.status,
        notes=assignment.notes,
        active_goals_count=0,
        open_follow_ups_count=0,
        created_at=assignment.created_at,
    )


async def get_student_review_for_mentor(
    db: AsyncSession, caller: AuthenticatedUser, student_id: UUID
) -> MentorStudentReviewResponse:
    await _assert_mentor_assigned_to_student(db, caller, student_id)
    displays = await get_user_displays_map(db, [student_id])
    disp = displays.get(student_id)
    onboarding = await get_student_onboarding_summary(db, student_id)
    progress = await get_student_progress_snapshot(db, student_id)
    accuracy = (
        round((progress.correct_attempts / progress.total_attempts) * 100.0, 2)
        if progress.total_attempts
        else 0.0
    )
    mastery_map = await get_concept_mastery_scores_map(db, student_id)
    mastery_avg = (
        round(sum(mastery_map.values()) / len(mastery_map), 2) if mastery_map else 0.0
    )
    weak_rows = await list_weak_concept_summaries(db, student_id, threshold=60.0)
    revision = await get_student_revision_summary(db, student_id)
    homework = await get_student_homework_summary(db, student_id)

    recommendations: list[str] = []
    if weak_rows:
        recommendations.append(
            f"Prioritize targeted remediation on {len(weak_rows)} low-mastery concept(s) below 60%."
        )
    if revision.due_flashcards_count > 0:
        recommendations.append(
            f"Clear {revision.due_flashcards_count} overdue spaced-repetition flashcard(s) this week."
        )
    if progress.total_attempts > 0 and accuracy < 65.0:
        recommendations.append(
            "Shift from timed tests to Hint-mode guided practice until accuracy rises above 70%."
        )
    if not recommendations:
        recommendations.append(
            "Maintain steady daily study cadence and introduce mixed chapter-level assessments."
        )

    goals = (
        await db.scalars(
            select(MentorGoal)
            .where(MentorGoal.mentor_id == caller.id, MentorGoal.student_id == student_id)
            .order_by(MentorGoal.created_at.desc())
        )
    ).all()
    sessions = (
        await db.scalars(
            select(MentorSession)
            .where(MentorSession.mentor_id == caller.id, MentorSession.student_id == student_id)
            .order_by(MentorSession.scheduled_at.desc())
        )
    ).all()
    follow_ups = (
        await db.scalars(
            select(MentorFollowUp)
            .where(MentorFollowUp.mentor_id == caller.id, MentorFollowUp.student_id == student_id)
            .order_by(MentorFollowUp.created_at.desc())
        )
    ).all()

    return MentorStudentReviewResponse(
        student_id=student_id,
        student_name=disp.display_name if disp else "Student",
        student_email=disp.email if disp else "",
        primary_exam_target=onboarding.primary_exam_target,
        daily_study_minutes_target=onboarding.daily_study_minutes_target,
        practice_total_attempts=progress.total_attempts,
        practice_accuracy_pct=accuracy,
        mastery_average_pct=mastery_avg,
        weak_concepts=[
            MentorWeakConceptItem(
                concept_id=w.concept_id,
                mastery_score=w.mastery_score,
                band=w.band,
            )
            for w in weak_rows[:10]
        ],
        due_flashcards_count=revision.due_flashcards_count,
        active_study_plans_count=revision.active_study_plans_count,
        completed_plan_items_count=revision.completed_plan_items_count,
        homework_evaluated_count=homework.evaluated_submissions,
        recommended_interventions=recommendations,
        goals=[_to_goal(g) for g in goals],
        sessions=[_to_session(s) for s in sessions],
        follow_ups=[_to_followup(f) for f in follow_ups],
    )


async def create_mentor_goal(
    db: AsyncSession, caller: AuthenticatedUser, payload: MentorGoalCreateRequest
) -> MentorGoalResponse:
    await _assert_mentor_assigned_to_student(db, caller, payload.student_id)
    goal = MentorGoal(
        tenant_id=caller.tenant_id,
        mentor_id=caller.id,
        student_id=payload.student_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        target_date=payload.target_date,
        progress_pct=0,
        status="active",
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return _to_goal(goal)


async def update_mentor_goal(
    db: AsyncSession,
    caller: AuthenticatedUser,
    goal_id: UUID,
    payload: MentorGoalUpdateRequest,
) -> MentorGoalResponse:
    goal = await db.get(MentorGoal, goal_id)
    if goal is None or (goal.mentor_id != caller.id and not caller.has_role("platform_admin")):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="MENTOR_GOAL_NOT_FOUND",
            message="Mentor goal not found.",
        )
    if payload.title is not None:
        goal.title = payload.title.strip()
    if payload.description is not None:
        goal.description = payload.description.strip()
    if payload.target_date is not None:
        goal.target_date = payload.target_date
    if payload.progress_pct is not None:
        goal.progress_pct = payload.progress_pct
    if payload.status is not None:
        goal.status = payload.status
    await db.commit()
    await db.refresh(goal)
    return _to_goal(goal)


async def create_mentor_session(
    db: AsyncSession, caller: AuthenticatedUser, payload: MentorSessionCreateRequest
) -> MentorSessionResponse:
    await _assert_mentor_assigned_to_student(db, caller, payload.student_id)
    sess = MentorSession(
        tenant_id=caller.tenant_id,
        mentor_id=caller.id,
        student_id=payload.student_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        status=payload.status,
        summary_notes=payload.summary_notes.strip(),
        recommendations_jsonb=[r.strip() for r in payload.recommendations if r.strip()],
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return _to_session(sess)


async def update_mentor_session(
    db: AsyncSession,
    caller: AuthenticatedUser,
    session_id: UUID,
    payload: MentorSessionUpdateRequest,
) -> MentorSessionResponse:
    sess = await db.get(MentorSession, session_id)
    if sess is None or (sess.mentor_id != caller.id and not caller.has_role("platform_admin")):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="MENTOR_SESSION_NOT_FOUND",
            message="Mentor session not found.",
        )
    if payload.status is not None:
        sess.status = payload.status
    if payload.summary_notes is not None:
        sess.summary_notes = payload.summary_notes.strip()
    if payload.recommendations is not None:
        sess.recommendations_jsonb = [r.strip() for r in payload.recommendations if r.strip()]
    await db.commit()
    await db.refresh(sess)
    return _to_session(sess)


async def create_mentor_follow_up(
    db: AsyncSession, caller: AuthenticatedUser, payload: MentorFollowUpCreateRequest
) -> MentorFollowUpResponse:
    await _assert_mentor_assigned_to_student(db, caller, payload.student_id)
    fu = MentorFollowUp(
        tenant_id=caller.tenant_id,
        session_id=payload.session_id,
        mentor_id=caller.id,
        student_id=payload.student_id,
        title=payload.title.strip(),
        due_date=payload.due_date,
        status="open",
    )
    db.add(fu)
    await db.commit()
    await db.refresh(fu)
    return _to_followup(fu)


async def update_mentor_follow_up(
    db: AsyncSession,
    caller: AuthenticatedUser,
    follow_up_id: UUID,
    payload: MentorFollowUpUpdateRequest,
) -> MentorFollowUpResponse:
    fu = await db.get(MentorFollowUp, follow_up_id)
    if fu is None or (fu.mentor_id != caller.id and not caller.has_role("platform_admin")):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="MENTOR_FOLLOWUP_NOT_FOUND",
            message="Mentor follow-up task not found.",
        )
    if payload.title is not None:
        fu.title = payload.title.strip()
    if payload.due_date is not None:
        fu.due_date = payload.due_date
    if payload.status is not None:
        fu.status = payload.status
    await db.commit()
    await db.refresh(fu)
    return _to_followup(fu)
