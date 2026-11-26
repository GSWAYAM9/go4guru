"""Public contract boundary for content rights verification."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AppError
from src.modules.content.models import ContentLicense, ContentSource
from src.modules.content.router import rights_router

MODULE_NAME = "content"
MODULE_PHASE = "Phase 1"
MODULE_STATUS = "IMPLEMENTED_RIGHTS_FOUNDATION"


async def assert_license_usable(
    db: AsyncSession,
    *,
    source_id: UUID,
    license_id: UUID,
    require_approved: bool = True,
    for_embedding: bool = False,
) -> tuple[str, str]:
    """Validate that source+license exist, are not quarantined, and permit intended use."""
    src = await db.get(ContentSource, source_id)
    lic = await db.get(ContentLicense, license_id)
    if src is None or lic is None or lic.source_id != src.id:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_RIGHTS_REFERENCE",
            message="Content source and matching license are required.",
        )
    if src.source_category == "quarantined_third_party" or lic.legal_review_status == "quarantined":
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="QUARANTINED_CONTENT_BLOCKED",
            message="Quarantined third-party sources cannot be authored, published, or indexed.",
        )
    if require_approved and lic.legal_review_status != "approved":
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="LICENSE_NOT_APPROVED",
            message="License must have legal_review_status='approved' before publishing.",
        )
    if require_approved and src.source_category != "official_link" and not lic.hosting_allowed:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="HOSTING_NOT_ALLOWED",
            message="License does not permit hosting this item.",
        )
    if lic.expires_at is not None and lic.expires_at <= datetime.now(UTC):
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="LICENSE_EXPIRED",
            message="Content license has expired.",
        )
    if for_embedding and not lic.embedding_allowed:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="EMBEDDING_NOT_ALLOWED",
            message="Content license prohibits vector indexing.",
        )
    return src.source_category, lic.legal_review_status


async def get_source_by_name(db: AsyncSession, name: str) -> tuple[UUID, UUID] | None:
    """Resolve an approved source + first approved license ID by source name."""
    src = await db.scalar(select(ContentSource).where(ContentSource.name == name))
    if src is None or src.source_category == "quarantined_third_party":
        return None
    lic = await db.scalar(
        select(ContentLicense).where(
            ContentLicense.source_id == src.id,
            ContentLicense.legal_review_status == "approved",
        )
    )
    if lic is None:
        return None
    return src.id, lic.id


__all__ = [
    "MODULE_NAME",
    "MODULE_PHASE",
    "MODULE_STATUS",
    "assert_license_usable",
    "get_source_by_name",
    "rights_router",
]
