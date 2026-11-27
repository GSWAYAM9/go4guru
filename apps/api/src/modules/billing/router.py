"""FastAPI router for Subscription Plans & Tenant Entitlements (/api/v1/billing/*)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.core.errors import AppError
from src.modules.billing.schemas import (
    SubscriptionPlanResponse,
    TenantSubscriptionResponse,
    TenantSubscriptionUpdateRequest,
)
from src.modules.billing.service import (
    get_tenant_subscription,
    list_subscription_plans,
    update_tenant_subscription,
)

billing_router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@billing_router.get("/plans", response_model=list[SubscriptionPlanResponse])
async def list_plans_endpoint(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    _caller: AuthenticatedUser = Depends(require_permissions("billing:manage_subscription")),  # noqa: B008
) -> list[SubscriptionPlanResponse]:
    return await list_subscription_plans(db)


@billing_router.get("/tenants/{tenant_id}/subscription", response_model=TenantSubscriptionResponse)
async def get_tenant_subscription_endpoint(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("billing:manage_subscription")),  # noqa: B008
) -> TenantSubscriptionResponse:
    if not caller.has_role("platform_admin") and caller.tenant_id != tenant_id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_FORBIDDEN",
            message="Cannot inspect subscription for another tenant.",
        )
    return await get_tenant_subscription(db, tenant_id)


@billing_router.put("/tenants/{tenant_id}/subscription", response_model=TenantSubscriptionResponse)
async def update_tenant_subscription_endpoint(
    tenant_id: UUID,
    payload: TenantSubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    caller: AuthenticatedUser = Depends(require_permissions("billing:manage_subscription")),  # noqa: B008
) -> TenantSubscriptionResponse:
    return await update_tenant_subscription(db, caller, tenant_id, payload)
