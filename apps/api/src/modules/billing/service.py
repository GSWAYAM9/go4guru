"""Service layer for Subscription Plans and Tenant Entitlements (F-036)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, write_audit_log
from src.core.errors import AppError
from src.modules.billing.logic import evaluate_entitlement_quota, merge_plan_entitlements
from src.modules.billing.models import SubscriptionPlan, TenantSubscription
from src.modules.billing.schemas import (
    SubscriptionPlanResponse,
    TenantSubscriptionResponse,
    TenantSubscriptionUpdateRequest,
)


def _to_plan_response(plan: SubscriptionPlan) -> SubscriptionPlanResponse:
    return SubscriptionPlanResponse(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        tier=plan.tier,
        monthly_price_inr=plan.monthly_price_inr,
        max_students=plan.max_students,
        max_teachers=plan.max_teachers,
        max_branches=plan.max_branches,
        entitlements=merge_plan_entitlements(plan.entitlements_jsonb, None),
        is_active=plan.is_active,
    )


def _to_sub_response(
    sub: TenantSubscription, plan: SubscriptionPlan
) -> TenantSubscriptionResponse:
    return TenantSubscriptionResponse(
        id=sub.id,
        tenant_id=sub.tenant_id,
        plan_id=plan.id,
        plan_code=plan.code,
        plan_name=plan.name,
        tier=plan.tier,
        status=sub.status,
        seat_limit=sub.seat_limit,
        max_teachers=plan.max_teachers,
        max_branches=plan.max_branches,
        effective_entitlements=merge_plan_entitlements(
            plan.entitlements_jsonb, sub.entitlement_overrides_jsonb
        ),
        starts_at=sub.starts_at,
        ends_at=sub.ends_at,
    )


async def list_subscription_plans(db: AsyncSession) -> list[SubscriptionPlanResponse]:
    rows = (
        await db.scalars(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active.is_(True))
            .order_by(SubscriptionPlan.monthly_price_inr.asc())
        )
    ).all()
    return [_to_plan_response(p) for p in rows]


async def get_tenant_subscription(
    db: AsyncSession, tenant_id: UUID
) -> TenantSubscriptionResponse:
    sub = await db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    if sub is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TENANT_SUBSCRIPTION_NOT_FOUND",
            message="No subscription record found for this tenant.",
        )
    plan = await db.get(SubscriptionPlan, sub.plan_id)
    if plan is None:
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="SUBSCRIPTION_PLAN_MISSING",
            message="Associated subscription plan record is missing.",
        )
    return _to_sub_response(sub, plan)


async def ensure_default_tenant_subscription(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    plan_code: str = "school_starter",
) -> TenantSubscriptionResponse:
    existing = await db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    if existing is not None:
        plan = await db.get(SubscriptionPlan, existing.plan_id)
        if plan is not None:
            return _to_sub_response(existing, plan)

    plan = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code))
    if plan is None:
        plan = await db.scalar(
            select(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price_inr.asc())
        )
    if plan is None:
        plan = SubscriptionPlan(
            code="school_starter",
            name="School Starter",
            tier="starter",
            monthly_price_inr=9999,
            max_students=150,
            max_teachers=20,
            max_branches=2,
            entitlements_jsonb={
                "ai_tutor": True,
                "homework_ai": True,
                "live_classroom": False,
                "institution_reports": True,
                "csv_export": True,
            },
            is_active=True,
        )
        db.add(plan)
        await db.flush()

    sub = TenantSubscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        status="active",
        seat_limit=plan.max_students,
        starts_at=datetime.now(UTC),
        entitlement_overrides_jsonb={},
    )
    db.add(sub)
    await db.flush()
    return _to_sub_response(sub, plan)


async def update_tenant_subscription(
    db: AsyncSession,
    caller: AuthenticatedUser,
    tenant_id: UUID,
    payload: TenantSubscriptionUpdateRequest,
) -> TenantSubscriptionResponse:
    if not caller.has_role("platform_admin") and caller.tenant_id != tenant_id:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CROSS_TENANT_FORBIDDEN",
            message="Cannot modify subscription for another tenant.",
        )

    plan = await db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == payload.plan_code,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    if plan is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PLAN_NOT_FOUND",
            message=f"Subscription plan '{payload.plan_code}' not found.",
        )

    sub = await db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    if sub is None:
        sub = TenantSubscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            status=payload.status,
            seat_limit=payload.seat_limit or plan.max_students,
            starts_at=datetime.now(UTC),
            entitlement_overrides_jsonb=payload.entitlement_overrides or {},
        )
        db.add(sub)
    else:
        sub.plan_id = plan.id
        sub.status = payload.status
        sub.seat_limit = payload.seat_limit if payload.seat_limit is not None else plan.max_students
        if payload.entitlement_overrides is not None:
            sub.entitlement_overrides_jsonb = payload.entitlement_overrides

    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0] if caller.roles else "school_admin",
        action="tenant_subscription.updated",
        resource_type="tenant_subscription",
        resource_id=str(sub.id),
        tenant_id=tenant_id,
        metadata={
            "plan_code": plan.code,
            "status": sub.status,
            "seat_limit": sub.seat_limit,
        },
    )
    await db.commit()
    await db.refresh(sub)
    return _to_sub_response(sub, plan)


async def assert_quota_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    resource: str,
    current_used: int,
) -> None:
    sub = await db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    if sub is None:
        return
    plan = await db.get(SubscriptionPlan, sub.plan_id)
    if plan is None:
        return
    if resource == "students":
        limit = sub.seat_limit
    elif resource == "teachers":
        limit = plan.max_teachers
    elif resource == "branches":
        limit = plan.max_branches
    else:
        limit = sub.seat_limit

    decision = evaluate_entitlement_quota(
        subscription_status=sub.status,
        resource=resource,
        used=current_used,
        limit=limit,
    )
    if not decision.allowed:
        raise AppError(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            code="ENTITLEMENT_QUOTA_EXCEEDED",
            message=decision.reason or "Tenant subscription quota exceeded.",
            details={"resource": resource, "used": current_used, "limit": limit},
        )
