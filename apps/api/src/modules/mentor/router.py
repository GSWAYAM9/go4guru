"""FastAPI router for Mentor Ecosystem (/api/v1/mentor/*)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
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
)
from src.modules.mentor.service import (
    assign_student_to_mentor,
    create_mentor_follow_up,
    create_mentor_goal,
    create_mentor_session,
    get_mentor_dashboard,
    get_student_review_for_mentor,
    update_mentor_follow_up,
    update_mentor_goal,
    update_mentor_session,
)

mentor_router = APIRouter(prefix="/api/v1/mentor", tags=["mentor"])


@mentor_router.get("/dashboard", response_model=MentorDashboardResponse)
async def mentor_dashboard_endpoint(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorDashboardResponse:
    return await get_mentor_dashboard(db, caller)


@mentor_router.post(
    "/students",
    response_model=MentorStudentRosterItem,
    status_code=status.HTTP_201_CREATED,
)
async def assign_student_endpoint(
    payload: MentorAssignStudentRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorStudentRosterItem:
    return await assign_student_to_mentor(db, caller, payload)


@mentor_router.get(
    "/students/{student_id}/review",
    response_model=MentorStudentReviewResponse,
)
async def mentor_student_review_endpoint(
    student_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:view_analytics")),  # noqa: B008
) -> MentorStudentReviewResponse:
    return await get_student_review_for_mentor(db, caller, student_id)


@mentor_router.post(
    "/goals",
    response_model=MentorGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_goal_endpoint(
    payload: MentorGoalCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorGoalResponse:
    return await create_mentor_goal(db, caller, payload)


@mentor_router.patch("/goals/{goal_id}", response_model=MentorGoalResponse)
async def update_goal_endpoint(
    goal_id: UUID,
    payload: MentorGoalUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorGoalResponse:
    return await update_mentor_goal(db, caller, goal_id, payload)


@mentor_router.post(
    "/sessions",
    response_model=MentorSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_endpoint(
    payload: MentorSessionCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorSessionResponse:
    return await create_mentor_session(db, caller, payload)


@mentor_router.patch("/sessions/{session_id}", response_model=MentorSessionResponse)
async def update_session_endpoint(
    session_id: UUID,
    payload: MentorSessionUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorSessionResponse:
    return await update_mentor_session(db, caller, session_id, payload)


@mentor_router.post(
    "/follow-ups",
    response_model=MentorFollowUpResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_follow_up_endpoint(
    payload: MentorFollowUpCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorFollowUpResponse:
    return await create_mentor_follow_up(db, caller, payload)


@mentor_router.patch("/follow-ups/{follow_up_id}", response_model=MentorFollowUpResponse)
async def update_follow_up_endpoint(
    follow_up_id: UUID,
    payload: MentorFollowUpUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("mentor:manage_students")),  # noqa: B008
) -> MentorFollowUpResponse:
    return await update_mentor_follow_up(db, caller, follow_up_id, payload)
