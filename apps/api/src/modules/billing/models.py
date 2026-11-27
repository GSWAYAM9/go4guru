"""ORM models for Subscription Plans and Tenant Entitlements (F-036)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.core.outbox import JSONBVariant


class SubscriptionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_plans"

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    monthly_price_inr: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    max_students: Mapped[int] = mapped_column(Integer, server_default=text("100"), nullable=False)
    max_teachers: Mapped[int] = mapped_column(Integer, server_default=text("15"), nullable=False)
    max_branches: Mapped[int] = mapped_column(Integer, server_default=text("2"), nullable=False)
    entitlements_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )


class TenantSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenant_subscriptions"

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24), server_default=text("'active'"), nullable=False
    )
    seat_limit: Mapped[int] = mapped_column(Integer, server_default=text("100"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entitlement_overrides_jsonb: Mapped[dict[str, Any]] = mapped_column(
        JSONBVariant, default=dict, nullable=False
    )
