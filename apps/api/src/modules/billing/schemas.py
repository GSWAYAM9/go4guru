"""Pydantic v2 schemas for Subscription Plans & Tenant Entitlements (F-036)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    code: str
    name: str
    tier: str
    monthly_price_inr: int
    max_students: int
    max_teachers: int
    max_branches: int
    entitlements: dict[str, bool]
    is_active: bool


class TenantSubscriptionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    plan_id: UUID
    plan_code: str
    plan_name: str
    tier: str
    status: str
    seat_limit: int
    max_teachers: int
    max_branches: int
    effective_entitlements: dict[str, bool]
    starts_at: datetime
    ends_at: datetime | None


class TenantSubscriptionUpdateRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=48)
    status: Literal["trial", "active", "past_due", "cancelled"] = "active"
    seat_limit: int | None = Field(default=None, ge=1, le=100000)
    entitlement_overrides: dict[str, bool] | None = None
