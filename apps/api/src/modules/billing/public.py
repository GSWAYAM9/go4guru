"""Public contract boundary for billing module (Phase 8 F-036)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.billing.router import billing_router
from src.modules.billing.service import (
    assert_quota_for_tenant,
    ensure_default_tenant_subscription,
    get_tenant_subscription,
)

MODULE_NAME = "billing"
MODULE_PHASE = "Phase 8"
MODULE_STATUS = "IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class TenantEntitlementsContract:
    tenant_id: UUID
    plan_code: str
    plan_name: str
    tier: str
    status: str
    seat_limit: int
    max_teachers: int
    max_branches: int
    entitlements: dict[str, bool]


async def attach_default_plan_to_tenant(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    plan_code: str = "school_starter",
) -> TenantEntitlementsContract:
    sub = await ensure_default_tenant_subscription(db, tenant_id=tenant_id, plan_code=plan_code)
    return TenantEntitlementsContract(
        tenant_id=sub.tenant_id,
        plan_code=sub.plan_code,
        plan_name=sub.plan_name,
        tier=sub.tier,
        status=sub.status,
        seat_limit=sub.seat_limit,
        max_teachers=sub.max_teachers,
        max_branches=sub.max_branches,
        entitlements=dict(sub.effective_entitlements),
    )


async def get_tenant_entitlements_contract(
    db: AsyncSession, tenant_id: UUID
) -> TenantEntitlementsContract | None:
    try:
        sub = await get_tenant_subscription(db, tenant_id)
    except Exception:
        return None
    return TenantEntitlementsContract(
        tenant_id=sub.tenant_id,
        plan_code=sub.plan_code,
        plan_name=sub.plan_name,
        tier=sub.tier,
        status=sub.status,
        seat_limit=sub.seat_limit,
        max_teachers=sub.max_teachers,
        max_branches=sub.max_branches,
        entitlements=dict(sub.effective_entitlements),
    )


async def assert_tenant_quota_available(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    resource: str,
    current_used: int,
) -> None:
    await assert_quota_for_tenant(
        db,
        tenant_id=tenant_id,
        resource=resource,
        current_used=current_used,
    )


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "TenantEntitlementsContract",
    "assert_tenant_quota_available",
    "attach_default_plan_to_tenant",
    "billing_router",
    "get_tenant_entitlements_contract",
]
