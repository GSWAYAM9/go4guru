"""API routes for content sources, licenses, and rights enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import (
    AuthenticatedUser,
    get_db_session,
    require_permissions,
    write_audit_log,
)
from src.core.errors import AppError
from src.modules.content.models import ContentLicense, ContentSource
from src.modules.content.schemas import (
    ContentLicenseCreate,
    ContentLicenseResponse,
    ContentLicenseReview,
    ContentSourceCreate,
    ContentSourceResponse,
)

rights_router = APIRouter(prefix="/api/v1/content-rights", tags=["content-rights"])


@rights_router.get("/sources", response_model=list[ContentSourceResponse])
async def list_sources(
    caller: AuthenticatedUser = Depends(require_permissions("rights:read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ContentSourceResponse]:
    rows = list((await db.scalars(select(ContentSource).order_by(ContentSource.name))).all())
    return [
        ContentSourceResponse(
            id=r.id,
            name=r.name,
            owner_name=r.owner_name,
            source_category=r.source_category,
            official_url=r.official_url,
            created_at=r.created_at,
        )
        for r in rows
    ]


@rights_router.post(
    "/sources",
    response_model=ContentSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    payload: ContentSourceCreate,
    caller: AuthenticatedUser = Depends(require_permissions("rights:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ContentSourceResponse:
    existing = await db.scalar(select(ContentSource).where(ContentSource.name == payload.name))
    if existing is not None:
        raise AppError(status_code=409, code="SOURCE_EXISTS", message="Content source exists.")
    src = ContentSource(
        name=payload.name,
        owner_name=payload.owner_name,
        source_category=payload.source_category,
        official_url=payload.official_url,
    )
    db.add(src)
    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0],
        action="rights.source_created",
        resource_type="content_source",
        resource_id=str(src.id),
        metadata={"category": payload.source_category},
    )
    await db.commit()
    await db.refresh(src)
    return ContentSourceResponse(
        id=src.id,
        name=src.name,
        owner_name=src.owner_name,
        source_category=src.source_category,
        official_url=src.official_url,
        created_at=src.created_at,
    )


@rights_router.get("/licenses", response_model=list[ContentLicenseResponse])
async def list_licenses(
    caller: AuthenticatedUser = Depends(require_permissions("rights:read")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ContentLicenseResponse]:
    rows = list(
        (await db.scalars(select(ContentLicense).order_by(ContentLicense.created_at.desc()))).all()
    )
    return [
        ContentLicenseResponse(
            id=r.id,
            source_id=r.source_id,
            license_name=r.license_name,
            commercial_use_allowed=r.commercial_use_allowed,
            distribution_allowed=r.distribution_allowed,
            hosting_allowed=r.hosting_allowed,
            embedding_allowed=r.embedding_allowed,
            attribution_required=r.attribution_required,
            attribution_text=r.attribution_text,
            territory=r.territory,
            expires_at=r.expires_at,
            legal_review_status=r.legal_review_status,
            reviewed_by=r.reviewed_by,
            reviewed_at=r.reviewed_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


@rights_router.post(
    "/licenses",
    response_model=ContentLicenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_license(
    payload: ContentLicenseCreate,
    caller: AuthenticatedUser = Depends(require_permissions("rights:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ContentLicenseResponse:
    src = await db.get(ContentSource, payload.source_id)
    if src is None:
        raise AppError(status_code=404, code="SOURCE_NOT_FOUND", message="Source not found.")
    initial_status = (
        "quarantined" if src.source_category == "quarantined_third_party" else "pending"
    )
    lic = ContentLicense(
        source_id=payload.source_id,
        license_name=payload.license_name,
        commercial_use_allowed=payload.commercial_use_allowed,
        distribution_allowed=payload.distribution_allowed,
        hosting_allowed=payload.hosting_allowed,
        embedding_allowed=payload.embedding_allowed,
        attribution_required=payload.attribution_required,
        attribution_text=payload.attribution_text,
        territory=payload.territory,
        expires_at=payload.expires_at,
        legal_review_status=initial_status,
    )
    db.add(lic)
    await db.flush()
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0],
        action="rights.license_created",
        resource_type="content_license",
        resource_id=str(lic.id),
    )
    await db.commit()
    await db.refresh(lic)
    return ContentLicenseResponse(
        id=lic.id,
        source_id=lic.source_id,
        license_name=lic.license_name,
        commercial_use_allowed=lic.commercial_use_allowed,
        distribution_allowed=lic.distribution_allowed,
        hosting_allowed=lic.hosting_allowed,
        embedding_allowed=lic.embedding_allowed,
        attribution_required=lic.attribution_required,
        attribution_text=lic.attribution_text,
        territory=lic.territory,
        expires_at=lic.expires_at,
        legal_review_status=lic.legal_review_status,
        reviewed_by=lic.reviewed_by,
        reviewed_at=lic.reviewed_at,
        created_at=lic.created_at,
    )


@rights_router.post("/licenses/{license_id}/review", response_model=ContentLicenseResponse)
async def review_license(
    license_id: UUID,
    payload: ContentLicenseReview,
    caller: AuthenticatedUser = Depends(require_permissions("rights:manage")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ContentLicenseResponse:
    lic = await db.get(ContentLicense, license_id)
    if lic is None:
        raise AppError(status_code=404, code="LICENSE_NOT_FOUND", message="License not found.")
    src = await db.get(ContentSource, lic.source_id)
    if (
        src is not None
        and src.source_category == "quarantined_third_party"
        and payload.legal_review_status == "approved"
    ):
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="QUARANTINED_SOURCE_FORBIDDEN",
            message=(
                "Quarantined third-party sources cannot be approved "
                "without reclassifying licensed rights."
            ),
        )

    lic.legal_review_status = payload.legal_review_status
    lic.reviewed_by = caller.id
    lic.reviewed_at = datetime.now(UTC)
    write_audit_log(
        db,
        actor_id=caller.id,
        actor_role=caller.roles[0],
        action="rights.license_reviewed",
        resource_type="content_license",
        resource_id=str(lic.id),
        metadata={"status": payload.legal_review_status},
    )
    await db.commit()
    await db.refresh(lic)
    return ContentLicenseResponse(
        id=lic.id,
        source_id=lic.source_id,
        license_name=lic.license_name,
        commercial_use_allowed=lic.commercial_use_allowed,
        distribution_allowed=lic.distribution_allowed,
        hosting_allowed=lic.hosting_allowed,
        embedding_allowed=lic.embedding_allowed,
        attribution_required=lic.attribution_required,
        attribution_text=lic.attribution_text,
        territory=lic.territory,
        expires_at=lic.expires_at,
        legal_review_status=lic.legal_review_status,
        reviewed_by=lic.reviewed_by,
        reviewed_at=lic.reviewed_at,
        created_at=lic.created_at,
    )
