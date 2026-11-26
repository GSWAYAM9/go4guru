"""Phase 5 Adaptive Concept Mastery, Misconception & Learning Path Service."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.errors import AppError
from src.modules.assessment.public import get_student_attempt_evidence
from src.modules.curriculum.public import ConceptGraphSnapshot, get_concept_graph_snapshot
from src.modules.learning.adaptive_engine import (
    DEFAULT_MASTERY_CONFIG,
    AdaptiveRecommendation,
    ConceptEvidenceSample,
    ConceptMasteryComputation,
    build_adaptive_recommendations,
    compute_concept_mastery,
)
from src.modules.learning.models import (
    LearningPath,
    LearningPathItem,
    StudentConceptMastery,
    StudentMisconception,
)
from src.modules.learning.schemas import (
    AdaptiveOverviewOut,
    ConceptMasteryOut,
    LearningPathCreateRequest,
    LearningPathItemOut,
    LearningPathItemStatusRequest,
    LearningPathOut,
    MisconceptionCreateRequest,
    MisconceptionOut,
    RecommendationItemOut,
)
from src.modules.notifications.public import emit_in_app_notification
from src.modules.question_bank.public import get_pinned_versions_map


class AdaptiveLearningService:
    """Computes evidence-backed concept mastery, tracks misconceptions, and builds paths."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def recompute_student_mastery(
        self, caller: AuthenticatedUser
    ) -> tuple[list[ConceptMasteryOut], list[RecommendationItemOut], ConceptGraphSnapshot]:
        """Re-aggregate practice & assessment attempts into persistent concept mastery rows."""
        now = datetime.now(UTC)
        evidence_list = await get_student_attempt_evidence(self.db, caller.id)
        qv_ids = list({e.question_version_id for e in evidence_list})
        qv_map = await get_pinned_versions_map(self.db, qv_ids)
        graph = await get_concept_graph_snapshot(self.db)

        samples_by_concept: dict[UUID, list[ConceptEvidenceSample]] = {}
        wrong_by_concept: dict[UUID, list[tuple[UUID | None, str | None]]] = {}

        for ev in evidence_list:
            qv = qv_map.get(ev.question_version_id)
            if qv is None or qv.concept_id is None:
                continue
            samples_by_concept.setdefault(qv.concept_id, []).append(
                ConceptEvidenceSample(
                    concept_id=qv.concept_id,
                    is_correct=ev.is_correct,
                    difficulty=qv.difficulty,
                    question_type=qv.question_type,
                    hints_used_count=ev.hints_used_count,
                    source_context=ev.source_context,
                    attempted_at=ev.attempted_at,
                )
            )
            if not ev.is_correct:
                wrong_by_concept.setdefault(qv.concept_id, []).append(
                    (qv.question_id, qv.common_mistakes_markdown)
                )

        # Auto-record heuristic misconception entries for repeated wrong attempts on a concept
        existing_misc_rows = list(
            (
                await self.db.scalars(
                    select(StudentMisconception).where(StudentMisconception.student_id == caller.id)
                )
            ).all()
        )
        misc_by_concept_code: dict[tuple[UUID, str], StudentMisconception] = {
            (m.concept_id, m.misconception_code): m for m in existing_misc_rows
        }

        for cid, wrong_items in wrong_by_concept.items():
            samples = samples_by_concept.get(cid, [])
            recent_two_indep_ok = len(samples) >= 2 and all(
                s.is_correct and s.hints_used_count == 0 for s in samples[-2:]
            )
            code = f"CONCEPT_GAP_{str(cid)[:8].upper()}"
            cnode = graph.concepts.get(cid)
            ctitle = cnode.title if cnode else "Concept"
            common_hint = next((cm for _, cm in wrong_items if cm), None)
            existing_m = misc_by_concept_code.get((cid, code))
            sev = "high" if len(wrong_items) >= 2 else "medium"
            if existing_m is None and not recent_two_indep_ok:
                m_row = StudentMisconception(
                    tenant_id=caller.tenant_id,
                    student_id=caller.id,
                    concept_id=cid,
                    question_id=wrong_items[-1][0],
                    misconception_code=code,
                    title=f"Conceptual error pattern in {ctitle}",
                    description=common_hint
                    or f"Incorrect response(s) detected on {ctitle}; targeted drill advised.",
                    severity=sev,
                    occurrence_count=len(wrong_items),
                    last_observed_at=now,
                )
                self.db.add(m_row)
                existing_misc_rows.append(m_row)
                misc_by_concept_code[(cid, code)] = m_row
            elif existing_m is not None:
                if recent_two_indep_ok and existing_m.resolved_at is None:
                    existing_m.resolved_at = now
                elif not recent_two_indep_ok:
                    existing_m.occurrence_count = max(existing_m.occurrence_count, len(wrong_items))
                    existing_m.severity = sev
                    existing_m.last_observed_at = now
                    if existing_m.resolved_at is not None and len(wrong_items) > 1:
                        existing_m.resolved_at = None

        await self.db.flush()

        # Collect unresolved severities per concept
        unresolved_sevs: dict[UUID, list[str]] = {}
        for m in existing_misc_rows:
            if m.resolved_at is None:
                unresolved_sevs.setdefault(m.concept_id, []).append(m.severity)

        existing_mastery_rows = list(
            (
                await self.db.scalars(
                    select(StudentConceptMastery).where(
                        StudentConceptMastery.student_id == caller.id
                    )
                )
            ).all()
        )
        mastery_row_map: dict[UUID, StudentConceptMastery] = {
            row.concept_id: row for row in existing_mastery_rows
        }

        all_target_concepts = set(samples_by_concept.keys()) | set(mastery_row_map.keys())
        computations: dict[UUID, ConceptMasteryComputation] = {}
        for cid in all_target_concepts:
            comp = compute_concept_mastery(
                concept_id=cid,
                samples=samples_by_concept.get(cid, []),
                unresolved_severities=unresolved_sevs.get(cid, []),
                now=now,
                config=DEFAULT_MASTERY_CONFIG,
            )
            computations[cid] = comp

            row = mastery_row_map.get(cid)
            if row is None:
                row = StudentConceptMastery(
                    tenant_id=caller.tenant_id,
                    student_id=caller.id,
                    concept_id=cid,
                )
                self.db.add(row)
                mastery_row_map[cid] = row

            prev_band = row.band
            row.mastery_score = Decimal(f"{comp.mastery_score:.2f}")
            row.confidence = Decimal(f"{comp.confidence:.2f}")
            row.retention_score = Decimal(f"{comp.retention_score:.2f}")
            row.independent_solve_ratio = Decimal(f"{comp.independent_solve_ratio:.2f}")
            row.transfer_score = Decimal(f"{comp.transfer_score:.2f}")
            row.improvement_slope = Decimal(f"{comp.improvement_slope:.2f}")
            row.difficulty_weighted_accuracy = Decimal(f"{comp.difficulty_weighted_accuracy:.2f}")
            row.band = comp.band
            row.attempts_count = comp.attempts_count
            row.last_practiced_at = comp.last_practiced_at
            row.next_review_due_at = comp.next_review_due_at
            row.mastery_breakdown_jsonb = dict(comp.breakdown)
            row.evidence_summary_jsonb = {
                "correct_count": comp.correct_count,
                "independent_correct_count": comp.independent_correct_count,
                "assisted_correct_count": comp.assisted_correct_count,
                "active_misconception_penalty": comp.active_misconception_penalty,
            }

            cnode = graph.concepts.get(cid)
            cname = cnode.title if cnode else "Concept"
            if comp.attempts_count >= 1 and comp.band in {"novice", "developing"}:
                await emit_in_app_notification(
                    self.db,
                    user_id=caller.id,
                    tenant_id=caller.tenant_id,
                    notification_type="weak_concept_alert",
                    title=f"Needs Remediation: {cname}",
                    body=(
                        f"Your mastery on {cname} is {comp.mastery_score:.1f}/100 "
                        f"(independent solve {int(comp.independent_solve_ratio * 100)}%)."
                    ),
                    action_url="/adaptive",
                    metadata={"concept_id": str(cid), "mastery_score": comp.mastery_score},
                )
            elif comp.band == "mastered" and prev_band != "mastered":
                await emit_in_app_notification(
                    self.db,
                    user_id=caller.id,
                    tenant_id=caller.tenant_id,
                    notification_type="mastery_milestone",
                    title=f"Mastered: {cname}!",
                    body=(
                        f"You achieved {comp.mastery_score:.1f}/100 independent mastery on {cname}."
                    ),
                    action_url="/adaptive",
                    metadata={"concept_id": str(cid)},
                )

        await self.db.commit()

        concept_titles = {cid: c.title for cid, c in graph.concepts.items()}
        recs: list[AdaptiveRecommendation] = build_adaptive_recommendations(
            mastery_by_concept=computations,
            prerequisites_of=graph.prerequisites_of,
            dependents_of=graph.dependents_of,
            unresolved_misconceptions_by_concept={
                cid: len(sevs) for cid, sevs in unresolved_sevs.items()
            },
            concept_titles=concept_titles,
            config=DEFAULT_MASTERY_CONFIG,
        )

        out_mastery: list[ConceptMasteryOut] = []
        for cid, row in mastery_row_map.items():
            cnode = graph.concepts.get(cid)
            out_mastery.append(
                ConceptMasteryOut(
                    concept_id=cid,
                    concept_code=cnode.code if cnode else "CONCEPT",
                    concept_title=cnode.title if cnode else "Tracked Concept",
                    subject_name=cnode.subject_name if cnode else None,
                    chapter_title=cnode.chapter_title if cnode else None,
                    mastery_score=float(row.mastery_score),
                    confidence=float(row.confidence),
                    retention_score=float(row.retention_score),
                    independent_solve_ratio=float(row.independent_solve_ratio),
                    transfer_score=float(row.transfer_score),
                    improvement_slope=float(row.improvement_slope),
                    difficulty_weighted_accuracy=float(row.difficulty_weighted_accuracy),
                    band=row.band,
                    attempts_count=row.attempts_count,
                    last_practiced_at=row.last_practiced_at,
                    next_review_due_at=row.next_review_due_at,
                    breakdown=dict(row.mastery_breakdown_jsonb or {}),
                    evidence_summary=dict(row.evidence_summary_jsonb or {}),
                )
            )
        out_mastery.sort(key=lambda m: m.mastery_score)

        out_recs = [
            RecommendationItemOut(
                concept_id=r.concept_id,
                concept_title=concept_titles.get(r.concept_id, "Concept"),
                item_type=r.item_type,
                priority_score=r.priority_score,
                reason=r.reason,
                action_route=r.action_route,
            )
            for r in recs
        ]
        return out_mastery, out_recs, graph

    async def get_adaptive_overview(self, caller: AuthenticatedUser) -> AdaptiveOverviewOut:
        mastery, recs, graph = await self.recompute_student_mastery(caller)
        weak = [
            m for m in mastery if m.mastery_score < DEFAULT_MASTERY_CONFIG.weak_mastery_threshold
        ]
        mastered = [m for m in mastery if m.band == "mastered"]
        miscs = await self.list_misconceptions(caller, include_resolved=False, graph=graph)
        return AdaptiveOverviewOut(
            concepts=mastery,
            weak_concepts=weak,
            mastered_concepts=mastered,
            unresolved_misconceptions=miscs,
            recommendations=recs,
            algorithm_version="phase5_multi_signal_v1",
            limitations_note=(
                "Uses authored difficulty labels and attempt-context transfer proxies until "
                "empirical cohort IRT calibration reaches N>=500 responses per item."
            ),
        )

    async def list_misconceptions(
        self,
        caller: AuthenticatedUser,
        *,
        include_resolved: bool = True,
        graph: ConceptGraphSnapshot | None = None,
    ) -> list[MisconceptionOut]:
        g = graph or await get_concept_graph_snapshot(self.db)
        stmt = select(StudentMisconception).where(StudentMisconception.student_id == caller.id)
        if not include_resolved:
            stmt = stmt.where(StudentMisconception.resolved_at.is_(None))
        rows = (
            await self.db.scalars(stmt.order_by(StudentMisconception.last_observed_at.desc()))
        ).all()
        return [
            MisconceptionOut(
                id=r.id,
                concept_id=r.concept_id,
                concept_title=g.concepts[r.concept_id].title
                if r.concept_id in g.concepts
                else "Concept",
                question_id=r.question_id,
                misconception_code=r.misconception_code,
                title=r.title,
                description=r.description,
                severity=r.severity,
                occurrence_count=r.occurrence_count,
                last_observed_at=r.last_observed_at,
                resolved_at=r.resolved_at,
            )
            for r in rows
        ]

    async def record_misconception(
        self, payload: MisconceptionCreateRequest, caller: AuthenticatedUser
    ) -> MisconceptionOut:
        now = datetime.now(UTC)
        existing = await self.db.scalar(
            select(StudentMisconception).where(
                StudentMisconception.student_id == caller.id,
                StudentMisconception.concept_id == payload.concept_id,
                StudentMisconception.misconception_code == payload.misconception_code,
            )
        )
        if existing is None:
            row = StudentMisconception(
                tenant_id=caller.tenant_id,
                student_id=caller.id,
                concept_id=payload.concept_id,
                question_id=payload.question_id,
                misconception_code=payload.misconception_code,
                title=payload.title,
                description=payload.description,
                severity=payload.severity,
                occurrence_count=1,
                last_observed_at=now,
            )
            self.db.add(row)
        else:
            existing.occurrence_count += 1
            existing.severity = payload.severity
            existing.description = payload.description
            existing.last_observed_at = now
            existing.resolved_at = None
            row = existing
        await self.db.commit()
        await self.db.refresh(row)
        await self.recompute_student_mastery(caller)
        g = await get_concept_graph_snapshot(self.db)
        return MisconceptionOut(
            id=row.id,
            concept_id=row.concept_id,
            concept_title=g.concepts[row.concept_id].title
            if row.concept_id in g.concepts
            else "Concept",
            question_id=row.question_id,
            misconception_code=row.misconception_code,
            title=row.title,
            description=row.description,
            severity=row.severity,
            occurrence_count=row.occurrence_count,
            last_observed_at=row.last_observed_at,
            resolved_at=row.resolved_at,
        )

    async def resolve_misconception(
        self, misconception_id: UUID, caller: AuthenticatedUser
    ) -> MisconceptionOut:
        row = await self.db.get(StudentMisconception, misconception_id)
        if row is None or row.student_id != caller.id:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="MISCONCEPTION_NOT_FOUND",
                message="Misconception record not found.",
            )
        row.resolved_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(row)
        await self.recompute_student_mastery(caller)
        g = await get_concept_graph_snapshot(self.db)
        return MisconceptionOut(
            id=row.id,
            concept_id=row.concept_id,
            concept_title=g.concepts[row.concept_id].title
            if row.concept_id in g.concepts
            else "Concept",
            question_id=row.question_id,
            misconception_code=row.misconception_code,
            title=row.title,
            description=row.description,
            severity=row.severity,
            occurrence_count=row.occurrence_count,
            last_observed_at=row.last_observed_at,
            resolved_at=row.resolved_at,
        )

    async def generate_learning_path(
        self, payload: LearningPathCreateRequest, caller: AuthenticatedUser
    ) -> LearningPathOut:
        _, recs, graph = await self.recompute_student_mastery(caller)
        lp = LearningPath(
            tenant_id=caller.tenant_id,
            student_id=caller.id,
            title=payload.title,
            goal_exam_track=payload.goal_exam_track,
            status="active",
            summary_jsonb={"recommendation_count": len(recs)},
        )
        self.db.add(lp)
        await self.db.flush()

        items: list[LearningPathItem] = []
        for idx, rec in enumerate(recs[:12], start=1):
            it = LearningPathItem(
                learning_path_id=lp.id,
                concept_id=rec.concept_id,
                item_type=rec.item_type,
                sequence_no=idx,
                priority_score=rec.priority_score,
                reason=rec.reason,
                status="pending",
                target_metadata_jsonb={"action_route": rec.action_route},
            )
            self.db.add(it)
            items.append(it)
        await self.db.commit()
        await self.db.refresh(lp)
        for it in items:
            await self.db.refresh(it)

        return self._to_path_out(lp, items, graph)

    async def list_learning_paths(self, caller: AuthenticatedUser) -> list[LearningPathOut]:
        graph = await get_concept_graph_snapshot(self.db)
        paths = (
            await self.db.scalars(
                select(LearningPath)
                .where(LearningPath.student_id == caller.id)
                .order_by(LearningPath.created_at.desc())
                .limit(10)
            )
        ).all()
        out: list[LearningPathOut] = []
        for lp in paths:
            items = list(
                (
                    await self.db.scalars(
                        select(LearningPathItem)
                        .where(LearningPathItem.learning_path_id == lp.id)
                        .order_by(LearningPathItem.sequence_no.asc())
                    )
                ).all()
            )
            out.append(self._to_path_out(lp, items, graph))
        return out

    async def update_path_item_status(
        self,
        item_id: UUID,
        payload: LearningPathItemStatusRequest,
        caller: AuthenticatedUser,
    ) -> LearningPathItemOut:
        item = await self.db.get(LearningPathItem, item_id)
        if item is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LEARNING_PATH_ITEM_NOT_FOUND",
                message="Learning path step not found.",
            )
        lp = await self.db.get(LearningPath, item.learning_path_id)
        if lp is None or lp.student_id != caller.id:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LEARNING_PATH_ITEM_NOT_FOUND",
                message="Learning path step not found.",
            )
        item.status = payload.status
        item.completed_at = datetime.now(UTC) if payload.status == "completed" else None
        await self.db.commit()
        await self.db.refresh(item)
        graph = await get_concept_graph_snapshot(self.db)
        return LearningPathItemOut(
            id=item.id,
            concept_id=item.concept_id,
            concept_title=graph.concepts[item.concept_id].title
            if item.concept_id in graph.concepts
            else "Concept",
            item_type=item.item_type,
            sequence_no=item.sequence_no,
            priority_score=item.priority_score,
            reason=item.reason,
            status=item.status,
            completed_at=item.completed_at,
        )

    @staticmethod
    def _to_path_out(
        lp: LearningPath,
        items: list[LearningPathItem],
        graph: ConceptGraphSnapshot,
    ) -> LearningPathOut:
        return LearningPathOut(
            id=lp.id,
            title=lp.title,
            goal_exam_track=lp.goal_exam_track,
            status=lp.status,
            items=[
                LearningPathItemOut(
                    id=it.id,
                    concept_id=it.concept_id,
                    concept_title=graph.concepts[it.concept_id].title
                    if it.concept_id in graph.concepts
                    else "Concept",
                    item_type=it.item_type,
                    sequence_no=it.sequence_no,
                    priority_score=it.priority_score,
                    reason=it.reason,
                    status=it.status,
                    completed_at=it.completed_at,
                )
                for it in items
            ],
            created_at=lp.created_at,
        )
