"""FastAPI router for Parent & Guardian Ecosystem (/api/v1/parent/*)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions, require_roles
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
)
from src.modules.identity.parent_service import (
    create_parent_goal,
    get_parent_dashboard,
    get_student_learning_summary_for_parent,
    list_parent_goals,
    request_guardian_link,
    revoke_guardian_link,
    update_guardian_privacy,
    update_parent_goal,
    verify_guardian_consent,
)

parent_router = APIRouter(prefix="/api/v1/parent", tags=["parent"])


@parent_router.get("/dashboard", response_model=ParentDashboardResponse)
async def parent_dashboard_endpoint(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("parent:view_summaries")),  # noqa: B008
) -> ParentDashboardResponse:
    return await get_parent_dashboard(db, caller)


@parent_router.post(
    "/links",
    response_model=GuardianLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_guardian_link_endpoint(
    payload: GuardianLinkRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("parent:manage_links")),  # noqa: B008
) -> GuardianLinkResponse:
    return await request_guardian_link(db, caller, payload)


@parent_router.post("/links/{link_id}/verify", response_model=GuardianLinkResponse)
async def verify_guardian_link_endpoint(
    link_id: UUID,
    payload: GuardianConsentVerifyRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(
        require_roles("parent", "student", "platform_admin")
    ),  # noqa: B008
) -> GuardianLinkResponse:
    return await verify_guardian_consent(db, caller, link_id, payload)


@parent_router.post("/links/{link_id}/revoke", response_model=GuardianLinkResponse)
async def revoke_guardian_link_endpoint(
    link_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(
        require_roles("parent", "student", "platform_admin")
    ),  # noqa: B008
) -> GuardianLinkResponse:
    return await revoke_guardian_link(db, caller, link_id)


@parent_router.patch("/links/{link_id}/privacy", response_model=GuardianLinkResponse)
async def update_guardian_privacy_endpoint(
    link_id: UUID,
    payload: GuardianPrivacyUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(
        require_roles("parent", "student", "platform_admin")
    ),  # noqa: B008
) -> GuardianLinkResponse:
    return await update_guardian_privacy(db, caller, link_id, payload)


@parent_router.get(
    "/students/{student_user_id}/summary",
    response_model=ParentLearningSummaryResponse,
)
async def parent_student_summary_endpoint(
    student_user_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("parent:view_summaries")),  # noqa: B008
) -> ParentLearningSummaryResponse:
    return await get_student_learning_summary_for_parent(db, caller, student_user_id)


@parent_router.get("/goals", response_model=list[ParentGoalResponse])
async def list_parent_goals_endpoint(
    student_user_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("parent:view_summaries")),  # noqa: B008
) -> list[ParentGoalResponse]:
    return await list_parent_goals(db, caller, student_user_id=student_user_id)


@parent_router.post(
    "/goals",
    response_model=ParentGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_parent_goal_endpoint(
    payload: ParentGoalCreateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("parent:manage_links")),  # noqa: B008
) -> ParentGoalResponse:
    return await create_parent_goal(db, caller, payload)


@parent_router.patch("/goals/{goal_id}", response_model=ParentGoalResponse)
async def update_parent_goal_endpoint(
    goal_id: UUID,
    payload: ParentGoalUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("parent:manage_links")),  # noqa: B008
) -> ParentGoalResponse:
    return await update_parent_goal(db, caller, goal_id, payload)
