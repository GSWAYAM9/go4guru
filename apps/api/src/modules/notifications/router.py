"""HTTP routes for Phase 5 In-App Notifications (`F-035`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.modules.notifications.service import list_notifications, mark_notification_read

notifications_router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: UUID
    notification_type: str
    title: str
    body: str
    action_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    metadata: dict[str, Any]
    created_at: datetime


@notifications_router.get("", response_model=list[NotificationOut])
async def get_my_notifications(
    caller: AuthenticatedUser = Depends(require_permissions("notifications:read_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[NotificationOut]:
    rows = await list_notifications(db, caller)
    return [
        NotificationOut(
            id=r.id,
            notification_type=r.notification_type,
            title=r.title,
            body=r.body,
            action_url=r.action_url,
            is_read=r.is_read,
            read_at=r.read_at,
            metadata=dict(r.metadata_jsonb or {}),
            created_at=r.created_at,
        )
        for r in rows
    ]


@notifications_router.post("/{notification_id}/read", response_model=NotificationOut)
async def read_my_notification(
    notification_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("notifications:read_own")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> NotificationOut:
    r = await mark_notification_read(db, notification_id, caller)
    return NotificationOut(
        id=r.id,
        notification_type=r.notification_type,
        title=r.title,
        body=r.body,
        action_url=r.action_url,
        is_read=r.is_read,
        read_at=r.read_at,
        metadata=dict(r.metadata_jsonb or {}),
        created_at=r.created_at,
    )
