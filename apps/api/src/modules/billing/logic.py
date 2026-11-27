"""Pure-stdlib deterministic subscription entitlement and quota logic (F-036)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QuotaEvaluationResult:
    allowed: bool
    resource: str
    used: int
    limit: int
    reason: str | None = None


def merge_plan_entitlements(
    plan_entitlements: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> dict[str, bool]:
    """Deterministically merge plan entitlements with tenant-specific overrides."""
    merged: dict[str, bool] = {}
    for source in (plan_entitlements or {}, overrides or {}):
        for key, value in source.items():
            merged[str(key)] = bool(value)
    return merged


def evaluate_entitlement_quota(
    *,
    subscription_status: str,
    resource: str,
    used: int,
    limit: int,
) -> QuotaEvaluationResult:
    """Deterministically enforce tenant subscription status and seat/branch quota caps."""
    if subscription_status not in ("trial", "active"):
        return QuotaEvaluationResult(
            allowed=False,
            resource=resource,
            used=used,
            limit=limit,
            reason=f"Subscription status '{subscription_status}' does not allow adding {resource}.",
        )
    if limit <= 0 or used >= limit:
        return QuotaEvaluationResult(
            allowed=False,
            resource=resource,
            used=used,
            limit=limit,
            reason=f"Tenant {resource} limit reached ({used}/{limit}). Upgrade subscription plan.",
        )
    return QuotaEvaluationResult(
        allowed=True,
        resource=resource,
        used=used,
        limit=limit,
        reason=None,
    )
