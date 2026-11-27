"""Pure-stdlib multi-tenant boundary guard and config helpers (Phase 8 F-003)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any
from uuid import UUID

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

DEFAULT_TENANT_CONFIG: dict[str, Any] = {
    "default_language": "en",
    "allow_ai_tutor": True,
    "allow_homework_ai": True,
    "require_mfa_for_admins": True,
    "allow_parent_portal": True,
}


def normalize_tenant_slug(raw: str) -> str:
    """Normalize an organization slug to lowercase alphanumeric + hyphens."""
    slug = re.sub(r"[^a-z0-9-]+", "-", raw.strip().lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) < 3:
        raise ValueError("Organization slug must contain at least 3 alphanumeric characters.")
    return slug[:80]


def merge_tenant_config(
    existing: dict[str, Any] | None,
    patch: dict[str, Any] | None,
) -> dict[str, Any]:
    """Deterministically merge tenant configuration keys with safe defaults."""
    merged = dict(DEFAULT_TENANT_CONFIG)
    if existing:
        merged.update(existing)
    if patch:
        for key, value in patch.items():
            if value is not None:
                merged[key] = value
    return merged


def is_tenant_access_allowed(
    *,
    caller_roles: tuple[str, ...],
    caller_tenant_id: UUID | None,
    target_tenant_id: UUID,
    active_membership_tenant_ids: set[UUID] | None = None,
) -> bool:
    """Strict backend multi-tenant isolation policy.

    - `platform_admin` may administer any tenant.
    - Non-platform callers MUST match `target_tenant_id` either via their verified JWT
      `tenant_id` claim OR an active `institution_memberships` record for `target_tenant_id`.
    - Cross-tenant access (Tenant A -> Tenant B) is unconditionally denied.
    """
    if "platform_admin" in caller_roles:
        return True
    if caller_tenant_id is not None and caller_tenant_id == target_tenant_id:
        return True
    if active_membership_tenant_ids and target_tenant_id in active_membership_tenant_ids:
        return True
    return False


def is_resource_in_tenant(*, resource_tenant_id: UUID | None, target_tenant_id: UUID) -> bool:
    """Verify a child entity belongs strictly to the requested tenant."""
    return resource_tenant_id is not None and resource_tenant_id == target_tenant_id


def sanitize_csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in _FORMULA_PREFIXES:
        return "'" + text
    return text


def render_org_report_csv(headers: list[str], rows: list[list[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([sanitize_csv_cell(h) for h in headers])
    for row in rows:
        writer.writerow([sanitize_csv_cell(cell) for cell in row])
    return buf.getvalue()
