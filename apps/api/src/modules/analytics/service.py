"""Idempotent outbox analytics projector and learning analytics service (`F-034`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.outbox import OutboxEvent
from src.modules.analytics.models import (
    AnalyticsSnapshot,
    LearningEvent,
    ProcessedEventId,
)

CONSUMER_NAME = "analytics_learning_projector_v1"


async def process_outbox_learning_events(db: AsyncSession, *, limit: int = 100) -> int:
    """Consume pending learning/assessment outbox events idempotently into analytics tables."""
    events = list(
        (
            await db.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.topic.in_(
                        ["learning.question_attempted", "assessment.attempt_submitted"]
                    ),
                    OutboxEvent.status == "pending",
                )
                .order_by(OutboxEvent.created_at.asc())
                .limit(limit)
            )
        ).all()
    )
    if not events:
        return 0

    affected_students: set[UUID] = set()
    processed_count = 0
    now = datetime.now(UTC)

    for ev in events:
        already = await db.get(ProcessedEventId, (CONSUMER_NAME, ev.id))
        if already is not None:
            ev.status = "published"
            ev.processed_at = now
            continue

        payload = ev.payload_jsonb
        student_raw = payload.get("student_id")
        if not student_raw:
            ev.status = "published"
            ev.processed_at = now
            continue
        student_id = UUID(str(student_raw))
        affected_students.add(student_id)

        self_concept = UUID(str(payload["concept_id"])) if payload.get("concept_id") else None
        entity_raw = payload.get("attempt_id") or ev.aggregate_id
        try:
            entity_id: UUID | None = UUID(str(entity_raw))
        except ValueError:
            entity_id = None

        db.add(ProcessedEventId(consumer_name=CONSUMER_NAME, event_id=ev.id))
        db.add(
            LearningEvent(
                student_id=student_id,
                tenant_id=ev.tenant_id,
                event_type=ev.topic,
                concept_id=self_concept,
                entity_id=entity_id,
                metrics_jsonb=dict(payload),
                occurred_at=ev.created_at,
            )
        )
        ev.status = "published"
        ev.processed_at = now
        processed_count += 1

    await db.flush()

    for sid in affected_students:
        all_events = list(
            (
                await db.scalars(
                    select(LearningEvent)
                    .where(LearningEvent.student_id == sid)
                    .order_by(LearningEvent.occurred_at.asc())
                )
            ).all()
        )
        assessments_completed = 0
        assessment_acc_sum = 0.0
        practice_attempts = 0
        practice_correct = 0

        for le in all_events:
            m = le.metrics_jsonb
            if le.event_type == "assessment.attempt_submitted":
                assessments_completed += 1
                assessment_acc_sum += float(m.get("accuracy_pct", 0.0))
            elif le.event_type == "learning.question_attempted":
                practice_attempts += 1
                if m.get("is_correct"):
                    practice_correct += 1

        snapshot_metrics: dict[str, Any] = {
            "assessments_completed": assessments_completed,
            "average_assessment_accuracy_pct": (
                round(assessment_acc_sum / assessments_completed, 2)
                if assessments_completed
                else 0.0
            ),
            "practice_attempts": practice_attempts,
            "practice_correct": practice_correct,
            "practice_accuracy_pct": (
                round((practice_correct / practice_attempts) * 100.0, 2)
                if practice_attempts
                else 0.0
            ),
            "total_learning_events": len(all_events),
        }

        snap = await db.scalar(
            select(AnalyticsSnapshot).where(
                AnalyticsSnapshot.student_id == sid,
                AnalyticsSnapshot.scope_type == "student_overview",
                AnalyticsSnapshot.scope_key == "all",
            )
        )
        if snap is None:
            db.add(
                AnalyticsSnapshot(
                    student_id=sid,
                    scope_type="student_overview",
                    scope_key="all",
                    metrics_jsonb=snapshot_metrics,
                    computed_at=now,
                )
            )
        else:
            snap.metrics_jsonb = snapshot_metrics
            snap.computed_at = now

    await db.commit()
    return processed_count
