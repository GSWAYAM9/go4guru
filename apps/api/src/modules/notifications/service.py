"""In-app revision & mastery notifications service (`F-035`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.errors import AppError
from src.modules.notifications.models import StudentNotification


async def emit_in_app_notification(
    db: AsyncSession,
    *,
    user_id: UUID,
    tenant_id: UUID | None,
    notification_type: str,
    title: str,
    body: str,
    action_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> StudentNotification:
    """Create an honest persisted in-app notification unless an unread identical one exists."""
    existing = await db.scalar(
        select(StudentNotification).where(
            StudentNotification.user_id == user_id,
            StudentNotification.notification_type == notification_type,
            StudentNotification.title == title,
            StudentNotification.is_read.is_(False),
        )
    )
    if existing is not None:
        return existing

    note = StudentNotification(
        tenant_id=tenant_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
        is_read=False,
        metadata_jsonb=dict(metadata or {}),
    )
    db.add(note)
    await db.flush()
    return note


async def list_notifications(
    db: AsyncSession, caller: AuthenticatedUser, *, limit: int = 30
) -> list[StudentNotification]:
    return list(
        (
            await db.scalars(
                select(StudentNotification)
                .where(StudentNotification.user_id == caller.id)
                .order_by(StudentNotification.is_read.asc(), StudentNotification.created_at.desc())
                .limit(limit)
            )
        ).all()
    )


async def mark_notification_read(
    db: AsyncSession, notification_id: UUID, caller: AuthenticatedUser
) -> StudentNotification:
    note = await db.get(StudentNotification, notification_id)
    if note is None or note.user_id != caller.id:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOTIFICATION_NOT_FOUND",
            message="Notification not found.",
        )
    if not note.is_read:
        note.is_read = True
        note.read_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(note)
    return note
