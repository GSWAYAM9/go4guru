"""Server-side Schema-Driven Whiteboard Event Log, Snapshot & Undo/Redo Engine."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import AppError
from src.modules.classroom.models import (
    WhiteboardAsset,
    WhiteboardEvent,
    WhiteboardSnapshot,
)
from src.modules.classroom.schemas import WhiteboardActionSchema


async def validate_whiteboard_asset_access(
    db: AsyncSession, action: WhiteboardActionSchema
) -> None:
    """Block unvetted or non-approved assets on INSERT_IMAGE."""
    if action.opcode != "INSERT_IMAGE":
        return
    raw_asset_id = str(action.payload.get("asset_id", ""))
    try:
        asset_uuid = UUID(raw_asset_id)
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_WHITEBOARD_ASSET",
            message="INSERT_IMAGE asset_id must be a valid approved asset UUID.",
        ) from exc
    asset = await db.get(WhiteboardAsset, asset_uuid)
    if asset is None or asset.legal_review_status != "approved":
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="UNAPPROVED_WHITEBOARD_ASSET",
            message="Whiteboard image asset is missing or not legally approved.",
        )


def reduce_actions_to_list(
    actions: list[WhiteboardActionSchema],
) -> list[WhiteboardActionSchema]:
    """Deterministically normalize active canvas actions (applies ERASE/MOVE/TRANSFORM)."""
    ordered = sorted(actions, key=lambda a: a.sequence)
    by_id: dict[str, WhiteboardActionSchema] = {}
    for act in ordered:
        if act.opcode == "ERASE":
            if act.payload.get("clear_all") is True:
                by_id.clear()
                continue
            targets = act.payload.get("target_ids")
            if isinstance(targets, list):
                for t in targets:
                    by_id.pop(str(t), None)
            elif act.payload.get("target_id"):
                by_id.pop(str(act.payload["target_id"]), None)
            continue
        if act.opcode == "MOVE":
            tid = str(act.payload.get("target_id", ""))
            existing = by_id.get(tid)
            if existing is not None:
                merged_payload: dict[str, Any] = dict(existing.payload)
                merged_payload["dx"] = float(merged_payload.get("dx", 0)) + float(
                    act.payload.get("dx", 0)
                )
                merged_payload["dy"] = float(merged_payload.get("dy", 0)) + float(
                    act.payload.get("dy", 0)
                )
                by_id[tid] = existing.model_copy(update={"payload": merged_payload})
            continue
        if act.opcode == "TRANSFORM":
            tid = str(act.payload.get("target_id", ""))
            existing = by_id.get(tid)
            if existing is not None:
                merged_t: dict[str, Any] = dict(existing.payload)
                for key in ("scale_x", "scale_y", "rotate_deg"):
                    if key in act.payload:
                        merged_t[key] = act.payload[key]
                by_id[tid] = existing.model_copy(update={"payload": merged_t})
            continue
        if act.opcode == "HIGHLIGHT":
            tid = str(act.payload.get("target_id", ""))
            existing = by_id.get(tid)
            if existing is not None:
                merged_h: dict[str, Any] = dict(existing.payload)
                merged_h["highlighted"] = True
                merged_h["highlight_color"] = act.payload.get("color", "#f59e0b")
                by_id[tid] = existing.model_copy(update={"payload": merged_h})
            continue
        by_id[act.id] = act
    return list(by_id.values())


async def next_whiteboard_sequence(db: AsyncSession, session_id: UUID) -> int:
    max_seq = await db.scalar(
        select(func.coalesce(func.max(WhiteboardEvent.sequence_no), 0)).where(
            WhiteboardEvent.classroom_session_id == session_id
        )
    )
    return int(max_seq or 0) + 1


async def append_whiteboard_event(
    db: AsyncSession,
    *,
    session_id: UUID,
    segment_seq: int,
    actor: str,
    action: WhiteboardActionSchema,
) -> WhiteboardEvent:
    await validate_whiteboard_asset_access(db, action)
    seq_no = await next_whiteboard_sequence(db, session_id)
    normalized = action.model_copy(update={"sequence": seq_no})
    ev = WhiteboardEvent(
        classroom_session_id=session_id,
        segment_seq=segment_seq,
        sequence_no=seq_no,
        actor=actor,
        action_type=normalized.opcode,
        action_payload_jsonb=normalized.model_dump(mode="json"),
        is_undone=False,
    )
    db.add(ev)
    await db.flush()
    return ev


async def get_active_whiteboard_state(
    db: AsyncSession, session_id: UUID
) -> tuple[list[WhiteboardActionSchema], bool, bool]:
    """Reconstruct active canvas state plus undo/redo availability from snapshot + events."""
    events = list(
        (
            await db.scalars(
                select(WhiteboardEvent)
                .where(WhiteboardEvent.classroom_session_id == session_id)
                .order_by(WhiteboardEvent.sequence_no.asc())
            )
        ).all()
    )
    active_raw = [
        WhiteboardActionSchema.model_validate(e.action_payload_jsonb)
        for e in events
        if not e.is_undone
    ]
    can_undo = any(not e.is_undone and e.actor == "student" for e in events)
    can_redo = any(e.is_undone and e.actor == "student" for e in events)
    return reduce_actions_to_list(active_raw), can_undo, can_redo


async def save_whiteboard_snapshot(
    db: AsyncSession, *, session_id: UUID, segment_seq: int
) -> WhiteboardSnapshot:
    actions, _, _ = await get_active_whiteboard_state(db, session_id)
    max_ver = int(
        await db.scalar(
            select(func.coalesce(func.max(WhiteboardSnapshot.version), 0)).where(
                WhiteboardSnapshot.classroom_session_id == session_id
            )
        )
        or 0
    )
    snap = WhiteboardSnapshot(
        classroom_session_id=session_id,
        segment_seq=segment_seq,
        version=max_ver + 1,
        snapshot_jsonb={"actions": [a.model_dump(mode="json") for a in actions]},
    )
    db.add(snap)
    await db.flush()
    return snap


async def undo_student_whiteboard_action(db: AsyncSession, session_id: UUID) -> bool:
    last_active = await db.scalar(
        select(WhiteboardEvent)
        .where(
            WhiteboardEvent.classroom_session_id == session_id,
            WhiteboardEvent.actor == "student",
            WhiteboardEvent.is_undone.is_(False),
        )
        .order_by(WhiteboardEvent.sequence_no.desc())
    )
    if last_active is None:
        return False
    last_active.is_undone = True
    await db.flush()
    return True


async def redo_student_whiteboard_action(db: AsyncSession, session_id: UUID) -> bool:
    first_undone = await db.scalar(
        select(WhiteboardEvent)
        .where(
            WhiteboardEvent.classroom_session_id == session_id,
            WhiteboardEvent.actor == "student",
            WhiteboardEvent.is_undone.is_(True),
        )
        .order_by(WhiteboardEvent.sequence_no.asc())
    )
    if first_undone is None:
        return False
    first_undone.is_undone = False
    await db.flush()
    return True
