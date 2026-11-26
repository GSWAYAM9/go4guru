"""Phase 5 Flashcards, Missed-Question Revision Sync, SM-2+ & Study Planner Service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.errors import AppError
from src.modules.assessment.public import get_student_attempt_evidence
from src.modules.curriculum.public import ConceptGraphSnapshot, get_concept_graph_snapshot
from src.modules.learning.public import get_concept_mastery_scores_map, list_weak_concept_summaries
from src.modules.notifications.public import emit_in_app_notification
from src.modules.question_bank.public import get_pinned_versions_map
from src.modules.revision.models import (
    Flashcard,
    FlashcardReview,
    StudentFlashcard,
    StudyPlan,
    StudyPlanItem,
)
from src.modules.revision.scheduler import compute_due_priority_score, schedule_sm2_plus
from src.modules.revision.schemas import (
    FlashcardCreateRequest,
    FlashcardOut,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    RevisionAnalyticsOut,
    StudyPlanCreateRequest,
    StudyPlanItemOut,
    StudyPlanItemStatusRequest,
    StudyPlanOut,
    SyncMissedResponse,
)


class RevisionService:
    """Manages multi-modal flashcards, SM-2+ scheduling, study plans, and revision analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_flashcard(
        self, payload: FlashcardCreateRequest, caller: AuthenticatedUser
    ) -> FlashcardOut:
        now = datetime.now(UTC)
        card = Flashcard(
            tenant_id=caller.tenant_id,
            owner_user_id=caller.id,
            card_type=payload.card_type,
            concept_id=payload.concept_id,
            subject_id=payload.subject_id,
            source_question_id=payload.source_question_id,
            language_code=payload.language_code,
            front_markdown=payload.front_markdown,
            back_markdown=payload.back_markdown,
            hint_markdown=payload.hint_markdown,
            tags_jsonb=list(payload.tags),
        )
        self.db.add(card)
        await self.db.flush()

        sf = StudentFlashcard(
            student_id=caller.id,
            flashcard_id=card.id,
            due_at=now,
            interval_days=0,
            ease_factor=2.5,
            repetitions=0,
            lapse_count=0,
        )
        self.db.add(sf)
        await self.db.commit()
        await self.db.refresh(card)
        await self.db.refresh(sf)

        graph = await get_concept_graph_snapshot(self.db)
        mastery_map = await get_concept_mastery_scores_map(self.db, caller.id)
        return self._to_card_out(card, sf, graph=graph, mastery_map=mastery_map, now=now)

    async def list_flashcards(
        self,
        caller: AuthenticatedUser,
        *,
        due_only: bool = False,
        card_type: str | None = None,
    ) -> list[FlashcardOut]:
        now = datetime.now(UTC)
        stmt = (
            select(Flashcard, StudentFlashcard)
            .join(StudentFlashcard, StudentFlashcard.flashcard_id == Flashcard.id)
            .where(StudentFlashcard.student_id == caller.id)
        )
        if card_type:
            stmt = stmt.where(Flashcard.card_type == card_type)
        if due_only:
            stmt = stmt.where(StudentFlashcard.due_at <= now)

        rows = (await self.db.execute(stmt)).all()
        graph = await get_concept_graph_snapshot(self.db)
        mastery_map = await get_concept_mastery_scores_map(self.db, caller.id)

        out = [
            self._to_card_out(card, sf, graph=graph, mastery_map=mastery_map, now=now)
            for card, sf in rows
        ]
        out.sort(key=lambda item: (not item.is_due, -item.priority_score, item.due_at))
        return out

    async def sync_missed_questions(self, caller: AuthenticatedUser) -> SyncMissedResponse:
        """Convert incorrect practice/assessment attempts into missed_question revision cards."""
        now = datetime.now(UTC)
        evidence = await get_student_attempt_evidence(self.db, caller.id)
        missed_ev = [e for e in evidence if not e.is_correct]
        if not missed_ev:
            return SyncMissedResponse(created_count=0, existing_count=0, flashcards=[])

        qv_ids = list({e.question_version_id for e in missed_ev})
        qv_map = await get_pinned_versions_map(self.db, qv_ids)

        existing_cards = list(
            (
                await self.db.scalars(
                    select(Flashcard).where(
                        Flashcard.owner_user_id == caller.id,
                        Flashcard.card_type == "missed_question",
                        Flashcard.source_question_id.is_not(None),
                    )
                )
            ).all()
        )
        by_source_q: dict[UUID, Flashcard] = {
            c.source_question_id: c for c in existing_cards if c.source_question_id is not None
        }

        created_count = 0
        existing_count = 0
        touched_cards: dict[UUID, Flashcard] = {}

        for ev in missed_ev:
            qv = qv_map.get(ev.question_version_id)
            if qv is None:
                continue
            if qv.question_id in by_source_q:
                existing_card = by_source_q[qv.question_id]
                touched_cards[existing_card.id] = existing_card
                existing_count += 1
                continue

            ans_summary = qv.correct_answer_jsonb
            if "correct_key" in ans_summary:
                ans_text = f"Correct Answer: Option {ans_summary['correct_key']}"
            elif "expected_value" in ans_summary:
                ans_text = f"Correct Answer: {ans_summary['expected_value']}"
            else:
                ans_text = f"Correct Answer: {ans_summary}"
            back_parts = [ans_text]
            if qv.explanation_markdown:
                back_parts.append(qv.explanation_markdown)

            new_card = Flashcard(
                tenant_id=caller.tenant_id,
                owner_user_id=caller.id,
                card_type="missed_question",
                concept_id=qv.concept_id,
                subject_id=qv.subject_id,
                source_question_id=qv.question_id,
                language_code="en",
                front_markdown=qv.stem_markdown,
                back_markdown="\n\n".join(back_parts),
                hint_markdown=qv.common_mistakes_markdown,
                tags_jsonb=[qv.difficulty, qv.question_type, ev.source_context],
            )
            self.db.add(new_card)
            await self.db.flush()
            self.db.add(
                StudentFlashcard(
                    student_id=caller.id,
                    flashcard_id=new_card.id,
                    due_at=now,
                    interval_days=0,
                    ease_factor=2.3,
                    repetitions=0,
                    lapse_count=1,
                )
            )
            by_source_q[qv.question_id] = new_card
            touched_cards[new_card.id] = new_card
            created_count += 1

        if created_count > 0:
            await emit_in_app_notification(
                self.db,
                user_id=caller.id,
                tenant_id=caller.tenant_id,
                notification_type="due_revision",
                title=f"{created_count} Missed-Question Flashcard(s) Ready",
                body=(
                    "Review your missed practice and assessment problems with SM-2 "
                    "spaced repetition."
                ),
                action_url="/revision",
                metadata={"created_count": created_count},
            )
        await self.db.commit()

        all_cards = await self.list_flashcards(caller, card_type="missed_question")
        return SyncMissedResponse(
            created_count=created_count,
            existing_count=existing_count,
            flashcards=all_cards,
        )

    async def review_flashcard(
        self,
        flashcard_id: UUID,
        payload: FlashcardReviewRequest,
        caller: AuthenticatedUser,
    ) -> FlashcardReviewResponse:
        now = datetime.now(UTC)
        card = await self.db.get(Flashcard, flashcard_id)
        sf = await self.db.get(StudentFlashcard, (caller.id, flashcard_id))
        if card is None or sf is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="FLASHCARD_NOT_FOUND",
                message="Flashcard not found in your deck.",
            )

        mastery_map = await get_concept_mastery_scores_map(self.db, caller.id)
        concept_score = mastery_map.get(card.concept_id) if card.concept_id else None

        prev_interval = sf.interval_days
        prev_ease = sf.ease_factor
        outcome = schedule_sm2_plus(
            quality=payload.quality,
            previous_repetitions=sf.repetitions,
            previous_interval_days=sf.interval_days,
            previous_ease=sf.ease_factor,
            concept_mastery_score=concept_score,
            now=now,
        )

        sf.repetitions = outcome.repetitions
        sf.interval_days = outcome.interval_days
        sf.ease_factor = outcome.ease_factor
        sf.lapse_count += outcome.lapse_delta
        sf.last_quality = payload.quality
        sf.last_reviewed_at = now
        sf.due_at = outcome.due_at

        self.db.add(
            FlashcardReview(
                student_id=caller.id,
                flashcard_id=flashcard_id,
                quality=payload.quality,
                response_ms=payload.response_ms,
                previous_interval_days=prev_interval,
                new_interval_days=outcome.interval_days,
                previous_ease=prev_ease,
                new_ease=outcome.ease_factor,
                reviewed_at=now,
            )
        )
        await self.db.commit()
        await self.db.refresh(sf)

        graph = await get_concept_graph_snapshot(self.db)
        return FlashcardReviewResponse(
            flashcard=self._to_card_out(card, sf, graph=graph, mastery_map=mastery_map, now=now),
            previous_interval_days=prev_interval,
            new_interval_days=outcome.interval_days,
            previous_ease=prev_ease,
            new_ease=outcome.ease_factor,
        )

    async def generate_study_plan(
        self, payload: StudyPlanCreateRequest, caller: AuthenticatedUser
    ) -> StudyPlanOut:
        now = datetime.now(UTC)
        today = date.today()
        graph = await get_concept_graph_snapshot(self.db)
        weak_concepts = await list_weak_concept_summaries(self.db, caller.id)
        due_cards = await self.list_flashcards(caller, due_only=True)

        plan = StudyPlan(
            tenant_id=caller.tenant_id,
            student_id=caller.id,
            title=payload.title,
            target_date=payload.target_date or (today + timedelta(days=7)),
            daily_minutes_budget=payload.daily_minutes_budget,
            status="active",
        )
        self.db.add(plan)
        await self.db.flush()

        items: list[StudyPlanItem] = []
        used_minutes = 0
        budget = payload.daily_minutes_budget

        # 1. Prioritize missed-question flashcards & due spaced repetition deck
        if due_cards:
            missed_due = [c for c in due_cards if c.card_type == "missed_question"]
            if missed_due and used_minutes + 15 <= budget:
                items.append(
                    StudyPlanItem(
                        study_plan_id=plan.id,
                        concept_id=missed_due[0].concept_id,
                        flashcard_id=missed_due[0].id,
                        item_type="missed_question",
                        title=f"Missed-Question Repair ({len(missed_due)} cards)",
                        description=(
                            "Re-solve flagged missed questions before practicing new items."
                        ),
                        estimated_minutes=15,
                        priority_score=95.0,
                        scheduled_for=today,
                        status="pending",
                    )
                )
                used_minutes += 15
            if used_minutes + 15 <= budget:
                items.append(
                    StudyPlanItem(
                        study_plan_id=plan.id,
                        concept_id=due_cards[0].concept_id,
                        flashcard_id=due_cards[0].id,
                        item_type="due_revision",
                        title=f"SM-2+ Flashcard Queue ({len(due_cards)} due)",
                        description="Complete due concept, formula, and vocabulary recall deck.",
                        estimated_minutes=15,
                        priority_score=88.0,
                        scheduled_for=today,
                        status="pending",
                    )
                )
                used_minutes += 15

        # 2. Schedule weak concept remediation blocks (rolling forward across days if budget full)
        day_offset = 0
        day_minutes = used_minutes
        for idx, wc in enumerate(weak_concepts[:6]):
            block_mins = 20
            if day_minutes + block_mins > budget:
                day_offset += 1
                day_minutes = 0
            cnode = graph.concepts.get(wc.concept_id)
            ctitle = cnode.title if cnode else f"Weak Concept #{idx + 1}"
            items.append(
                StudyPlanItem(
                    study_plan_id=plan.id,
                    concept_id=wc.concept_id,
                    item_type="remediation",
                    title=f"Remediate: {ctitle}",
                    description=(
                        f"Current mastery {wc.mastery_score:.1f}/100 ({wc.band}). "
                        "Solve 3 independent practice questions without hints."
                    ),
                    estimated_minutes=block_mins,
                    priority_score=round(85.0 - wc.mastery_score * 0.4, 2),
                    scheduled_for=today + timedelta(days=day_offset),
                    status="pending",
                )
            )
            day_minutes += block_mins

        # 3. Guarantee at least one advancement/consolidation block when queue is light
        if not items:
            items.append(
                StudyPlanItem(
                    study_plan_id=plan.id,
                    item_type="advancement",
                    title="Daily Concept Consolidation & Practice",
                    description="Attempt mixed-difficulty practice questions across core concepts.",
                    estimated_minutes=min(25, budget),
                    priority_score=60.0,
                    scheduled_for=today,
                    status="pending",
                )
            )

        for it in items:
            self.db.add(it)

        await emit_in_app_notification(
            self.db,
            user_id=caller.id,
            tenant_id=caller.tenant_id,
            notification_type="study_plan_reminder",
            title=f"Study Plan Ready: {plan.title}",
            body=f"Scheduled {len(items)} revision blocks ({plan.daily_minutes_budget} min/day).",
            action_url="/revision",
            metadata={"study_plan_id": str(plan.id)},
        )
        await self.db.commit()
        await self.db.refresh(plan)
        for it in items:
            await self.db.refresh(it)

        _ = now
        return self._to_plan_out(plan, items)

    async def list_study_plans(self, caller: AuthenticatedUser) -> list[StudyPlanOut]:
        plans = (
            await self.db.scalars(
                select(StudyPlan)
                .where(StudyPlan.student_id == caller.id)
                .order_by(StudyPlan.created_at.desc())
                .limit(10)
            )
        ).all()
        out: list[StudyPlanOut] = []
        for plan in plans:
            items = list(
                (
                    await self.db.scalars(
                        select(StudyPlanItem)
                        .where(StudyPlanItem.study_plan_id == plan.id)
                        .order_by(
                            StudyPlanItem.scheduled_for.asc(), StudyPlanItem.priority_score.desc()
                        )
                    )
                ).all()
            )
            out.append(self._to_plan_out(plan, items))
        return out

    async def update_study_plan_item_status(
        self,
        item_id: UUID,
        payload: StudyPlanItemStatusRequest,
        caller: AuthenticatedUser,
    ) -> StudyPlanItemOut:
        item = await self.db.get(StudyPlanItem, item_id)
        if item is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="STUDY_PLAN_ITEM_NOT_FOUND",
                message="Study plan item not found.",
            )
        plan = await self.db.get(StudyPlan, item.study_plan_id)
        if plan is None or plan.student_id != caller.id:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="STUDY_PLAN_ITEM_NOT_FOUND",
                message="Study plan item not found.",
            )
        item.status = payload.status
        item.completed_at = datetime.now(UTC) if payload.status == "completed" else None
        await self.db.commit()
        await self.db.refresh(item)
        return self._to_plan_item_out(item)

    async def get_revision_analytics(self, caller: AuthenticatedUser) -> RevisionAnalyticsOut:
        now = datetime.now(UTC)
        rows = (
            await self.db.execute(
                select(Flashcard, StudentFlashcard)
                .join(StudentFlashcard, StudentFlashcard.flashcard_id == Flashcard.id)
                .where(StudentFlashcard.student_id == caller.id)
            )
        ).all()

        by_type: dict[str, int] = {}
        due_now = 0
        mastered = 0
        lapsed = 0
        missed_cards = 0
        for card, sf in rows:
            by_type[card.card_type] = by_type.get(card.card_type, 0) + 1
            due_utc = sf.due_at if sf.due_at.tzinfo else sf.due_at.replace(tzinfo=UTC)
            if due_utc <= now:
                due_now += 1
            if sf.repetitions >= 3 and sf.ease_factor >= 2.3:
                mastered += 1
            if sf.lapse_count > 0:
                lapsed += 1
            if card.card_type == "missed_question":
                missed_cards += 1

        reviews = (
            await self.db.scalars(
                select(FlashcardReview).where(FlashcardReview.student_id == caller.id)
            )
        ).all()
        total_reviews = len(reviews)
        avg_q = (
            round(sum(r.quality for r in reviews) / total_reviews, 2) if total_reviews > 0 else 0.0
        )
        retention_pct = (
            round(
                (sum(1 for r in reviews if r.quality >= 3) / total_reviews) * 100.0,
                2,
            )
            if total_reviews > 0
            else 0.0
        )

        latest_plan = await self.db.scalar(
            select(StudyPlan)
            .where(StudyPlan.student_id == caller.id)
            .order_by(StudyPlan.created_at.desc())
        )
        plan_pct = 0.0
        if latest_plan is not None:
            tot_items = int(
                await self.db.scalar(
                    select(func.count(StudyPlanItem.id)).where(
                        StudyPlanItem.study_plan_id == latest_plan.id
                    )
                )
                or 0
            )
            done_items = int(
                await self.db.scalar(
                    select(func.count(StudyPlanItem.id)).where(
                        StudyPlanItem.study_plan_id == latest_plan.id,
                        StudyPlanItem.status == "completed",
                    )
                )
                or 0
            )
            plan_pct = round((done_items / tot_items) * 100.0, 2) if tot_items > 0 else 0.0

        return RevisionAnalyticsOut(
            total_flashcards=len(rows),
            due_now_count=due_now,
            mastered_cards_count=mastered,
            lapsed_cards_count=lapsed,
            missed_question_cards_count=missed_cards,
            total_reviews=total_reviews,
            average_quality=avg_q,
            retention_success_rate_pct=retention_pct,
            active_plan_completion_pct=plan_pct,
            by_card_type=by_type,
        )

    @staticmethod
    def _to_card_out(
        card: Flashcard,
        sf: StudentFlashcard,
        *,
        graph: ConceptGraphSnapshot,
        mastery_map: dict[UUID, float],
        now: datetime,
    ) -> FlashcardOut:
        c_title = (
            graph.concepts[card.concept_id].title
            if card.concept_id and card.concept_id in graph.concepts
            else None
        )
        m_score = mastery_map.get(card.concept_id) if card.concept_id else None
        due_utc = sf.due_at if sf.due_at.tzinfo else sf.due_at.replace(tzinfo=UTC)
        prio = compute_due_priority_score(
            due_at=due_utc,
            card_type=card.card_type,
            lapse_count=sf.lapse_count,
            concept_mastery_score=m_score,
            now=now,
        )
        return FlashcardOut(
            id=card.id,
            card_type=card.card_type,
            concept_id=card.concept_id,
            concept_title=c_title,
            subject_id=card.subject_id,
            source_question_id=card.source_question_id,
            language_code=card.language_code,
            front_markdown=card.front_markdown,
            back_markdown=card.back_markdown,
            hint_markdown=card.hint_markdown,
            tags=list(card.tags_jsonb or []),
            due_at=sf.due_at,
            interval_days=sf.interval_days,
            ease_factor=sf.ease_factor,
            repetitions=sf.repetitions,
            lapse_count=sf.lapse_count,
            last_quality=sf.last_quality,
            last_reviewed_at=sf.last_reviewed_at,
            priority_score=prio,
            is_due=due_utc <= now,
        )

    @classmethod
    def _to_plan_out(cls, plan: StudyPlan, items: list[StudyPlanItem]) -> StudyPlanOut:
        return StudyPlanOut(
            id=plan.id,
            title=plan.title,
            target_date=plan.target_date,
            daily_minutes_budget=plan.daily_minutes_budget,
            status=plan.status,
            items=[cls._to_plan_item_out(i) for i in items],
            created_at=plan.created_at,
        )

    @staticmethod
    def _to_plan_item_out(it: StudyPlanItem) -> StudyPlanItemOut:
        return StudyPlanItemOut(
            id=it.id,
            concept_id=it.concept_id,
            flashcard_id=it.flashcard_id,
            item_type=it.item_type,
            title=it.title,
            description=it.description,
            estimated_minutes=it.estimated_minutes,
            priority_score=it.priority_score,
            scheduled_for=it.scheduled_for,
            status=it.status,
            completed_at=it.completed_at,
        )
