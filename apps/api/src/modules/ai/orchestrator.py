"""Coordinated 16-Module AI Teaching Orchestrator, Quota Guard & Cost Ledger."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.config import Settings
from src.core.errors import AppError
from src.modules.ai.models import (
    AiCostEvent,
    AiMessage,
    AiReviewQueueItem,
    AiSession,
    AiToolCall,
    ProviderRateCard,
)
from src.modules.ai.pedagogy import (
    SUPPORTED_LANGUAGES,
    build_conversation_window,
    build_pedagogical_plan,
    build_specialized_prompts,
    run_deterministic_verification_for_query,
    synthesize_grounded_fallback,
)
from src.modules.ai.provider import AIRouterGateway, CircuitBreaker, ProviderInvocationRequest
from src.modules.ai.resolvers import (
    classify_intent,
    resolve_curriculum_context,
    resolve_student_context,
)
from src.modules.ai.retrieval import HybridRetrievalService, validate_citations
from src.modules.ai.safety import evaluate_input_safety, evaluate_output_safety, scrub_pii_text
from src.modules.ai.schemas import (
    AiCostSummaryResponse,
    AiFlagMessageRequest,
    AiMessageOut,
    AiModelsCatalogResponse,
    AiModeUpdateRequest,
    AiReviewDecisionRequest,
    AiReviewQueueOut,
    AiSessionCreateRequest,
    AiSessionOut,
    AiTurnRequest,
    AiTurnResponse,
    AiUsageQuotaResponse,
    CitedChunk,
    CurriculumContext,
    ModelCapabilityOut,
    PracticeDraftOut,
    StructuredTutorOutput,
    TeachingMode,
    VerificationStatus,
)

# Shared process circuit breaker tracks provider stability across requests
_SHARED_BREAKER = CircuitBreaker()


class AIOrchestratorService:
    """Executes the bounded 16-module AI Tutor workflow with strict DB auditability."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        *,
        gateway: AIRouterGateway | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.gateway = gateway or AIRouterGateway(settings, breaker=_SHARED_BREAKER)

    async def get_models_catalog(self) -> AiModelsCatalogResponse:
        """Expose configured providers/models truthfully without leaking any secret keys."""
        providers_meta = [
            ModelCapabilityOut(
                provider="gemini",
                configured=self.gateway.providers["gemini"].is_configured(),
                fast_model=self.settings.ai_gemini_fast_model,
                reasoning_model=self.settings.ai_gemini_reasoning_model,
                circuit_state=self.gateway.breaker.state("gemini"),
                notes="Google Gemini REST API; light/fast routing + reasoning tier.",
            ),
            ModelCapabilityOut(
                provider="openai",
                configured=self.gateway.providers["openai"].is_configured(),
                fast_model=self.settings.ai_openai_fast_model,
                reasoning_model=self.settings.ai_openai_reasoning_model,
                circuit_state=self.gateway.breaker.state("openai"),
                notes="OpenAI Chat Completions API; structured JSON fallback tier.",
            ),
            ModelCapabilityOut(
                provider="anthropic",
                configured=self.gateway.providers["anthropic"].is_configured(),
                fast_model=self.settings.ai_anthropic_fast_model,
                reasoning_model=self.settings.ai_anthropic_reasoning_model,
                circuit_state=self.gateway.breaker.state("anthropic"),
                notes="Anthropic Messages API; strong pedagogical reasoning tier.",
            ),
            ModelCapabilityOut(
                provider="grounded_fallback",
                configured=True,
                fast_model="deterministic-v1",
                reasoning_model="deterministic-v1",
                circuit_state="closed",
                notes=(
                    "Active whenever external vendor API keys are absent or offline: "
                    "returns curated curriculum excerpts + SymPy/Pint/Chemistry verifier checks."
                ),
            ),
        ]
        return AiModelsCatalogResponse(
            primary_provider=self.settings.ai_primary_provider,
            providers=providers_meta,
            daily_turn_limit=self.settings.ai_daily_turn_limit,
            rpm_limit=self.settings.ai_rpm_limit,
            supported_languages=SUPPORTED_LANGUAGES,
            known_limitations=[
                "Only external providers with configured backend keys run live LLM inference.",
                (
                    "Non-symbolic qualitative answers without deterministic proofs "
                    "are marked unverified/not_applicable."
                ),
                (
                    "Unlicensed third-party PDFs (ALLEN quarantine) are strictly "
                    "excluded from RAG retrieval."
                ),
            ],
        )

    async def get_usage_quota(self, caller: AuthenticatedUser) -> AiUsageQuotaResponse:
        now = datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        turns_today = int(
            await self.db.scalar(
                select(func.count(AiCostEvent.id)).where(
                    AiCostEvent.user_id == caller.id,
                    AiCostEvent.created_at >= day_start,
                )
            )
            or 0
        )
        cost_today = float(
            await self.db.scalar(
                select(func.coalesce(func.sum(AiCostEvent.estimated_cost_usd), 0)).where(
                    AiCostEvent.user_id == caller.id,
                    AiCostEvent.created_at >= day_start,
                )
            )
            or 0.0
        )
        return AiUsageQuotaResponse(
            turns_used_today=turns_today,
            daily_turn_limit=self.settings.ai_daily_turn_limit,
            turns_remaining_today=max(0, self.settings.ai_daily_turn_limit - turns_today),
            estimated_cost_usd_today=round(cost_today, 6),
            rpm_limit=self.settings.ai_rpm_limit,
        )

    async def _enforce_rate_and_quota(self, caller: AuthenticatedUser) -> None:
        now = datetime.now(UTC)
        minute_ago = now - timedelta(minutes=1)
        rpm_count = int(
            await self.db.scalar(
                select(func.count(AiCostEvent.id)).where(
                    AiCostEvent.user_id == caller.id,
                    AiCostEvent.created_at >= minute_ago,
                )
            )
            or 0
        )
        if rpm_count >= self.settings.ai_rpm_limit:
            raise AppError(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="AI_RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded ({self.settings.ai_rpm_limit} turns/minute).",
            )

        quota = await self.get_usage_quota(caller)
        if quota.turns_remaining_today <= 0:
            raise AppError(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="AI_DAILY_QUOTA_EXCEEDED",
                message="Daily AI Tutor turn quota reached.",
            )

    async def create_session(
        self, payload: AiSessionCreateRequest, caller: AuthenticatedUser
    ) -> AiSessionOut:
        student_ctx = await resolve_student_context(self.db, caller.id)
        curr_ctx = await resolve_curriculum_context(
            self.db,
            student_ctx=student_ctx,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
        )
        lang = (payload.language_code or student_ctx.preferred_explanation_language or "en").strip()

        sess = AiSession(
            student_id=caller.id,
            tenant_id=caller.tenant_id,
            session_type=payload.session_type,
            title=payload.title.strip(),
            teaching_mode=payload.teaching_mode,
            language_code=lang,
            curriculum_context_jsonb=curr_ctx.model_dump(mode="json"),
        )
        self.db.add(sess)
        await self.db.commit()
        await self.db.refresh(sess)
        return self._to_session_out(sess)

    async def list_sessions(self, caller: AuthenticatedUser) -> list[AiSessionOut]:
        rows = (
            await self.db.scalars(
                select(AiSession)
                .where(AiSession.student_id == caller.id)
                .order_by(AiSession.updated_at.desc())
                .limit(30)
            )
        ).all()
        return [self._to_session_out(r) for r in rows]

    async def _load_owned_session(self, session_id: UUID, caller: AuthenticatedUser) -> AiSession:
        sess = await self.db.get(AiSession, session_id)
        if sess is None or sess.student_id != caller.id:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="AI_SESSION_NOT_FOUND",
                message="AI tutor session not found.",
            )
        return sess

    async def update_session_mode(
        self, session_id: UUID, payload: AiModeUpdateRequest, caller: AuthenticatedUser
    ) -> AiSessionOut:
        sess = await self._load_owned_session(session_id, caller)
        sess.teaching_mode = payload.teaching_mode
        if payload.language_code:
            sess.language_code = payload.language_code.strip()
        await self.db.commit()
        await self.db.refresh(sess)
        return self._to_session_out(sess)

    async def list_messages(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> list[AiMessageOut]:
        await self._load_owned_session(session_id, caller)
        rows = (
            await self.db.scalars(
                select(AiMessage)
                .where(AiMessage.ai_session_id == session_id)
                .order_by(AiMessage.created_at.asc())
            )
        ).all()
        return [self._to_message_out(m) for m in rows]

    async def _estimate_cost(self, provider: str, model_id: str, tin: int, tout: int) -> Decimal:
        card = await self.db.scalar(
            select(ProviderRateCard).where(
                ProviderRateCard.provider == provider,
                ProviderRateCard.model_id == model_id,
            )
        )
        if card is None:
            return Decimal("0.000000")
        cost_in = (Decimal(tin) / Decimal(1_000_000)) * card.input_cost_per_1m_usd
        cost_out = (Decimal(tout) / Decimal(1_000_000)) * card.output_cost_per_1m_usd
        return (cost_in + cost_out).quantize(Decimal("0.000001"))

    async def execute_turn(
        self,
        session_id: UUID,
        payload: AiTurnRequest,
        caller: AuthenticatedUser,
    ) -> AiTurnResponse:
        t_start = time.perf_counter()
        sess = await self._load_owned_session(session_id, caller)
        await self._enforce_rate_and_quota(caller)

        raw_msg = payload.message.strip()
        # Module 15 (Input Safety Gate)
        safety_in = evaluate_input_safety(raw_msg, is_minor=caller.is_minor)

        student_msg = AiMessage(
            ai_session_id=sess.id,
            role="student",
            content_markdown=scrub_pii_text(raw_msg),
            safety_verdict=safety_in.action,
        )
        self.db.add(student_msg)
        await self.db.flush()

        # Immediate safe redirect / block handling without calling external LLMs
        if safety_in.action != "allow":
            asst = AiMessage(
                ai_session_id=sess.id,
                role="assistant",
                content_markdown=safety_in.safe_message
                or "Request blocked by child safety policy.",
                intent="out_of_scope",
                pedagogical_mode=sess.teaching_mode,
                spoiler_guard=True,
                verification_status="not_applicable",
                provider_used="safety_guard",
                model_used="policy-rules-v1",
                prompt_version="safety_v1",
                is_fallback=False,
                safety_verdict=safety_in.action,
                latency_ms=int((time.perf_counter() - t_start) * 1000),
            )
            self.db.add(asst)
            await self.db.flush()

            self.db.add(
                AiToolCall(
                    ai_message_id=asst.id,
                    tool_name="safety_check",
                    input_jsonb={"length": len(raw_msg)},
                    output_jsonb={"action": safety_in.action, "reason": safety_in.reason_code},
                    succeeded=True,
                    latency_ms=1,
                )
            )
            if safety_in.requires_review_escalation:
                self.db.add(
                    AiReviewQueueItem(
                        ai_session_id=sess.id,
                        ai_message_id=asst.id,
                        student_id=caller.id,
                        reason=safety_in.reason_code or "safety_escalation",
                        status="escalated",
                    )
                )
            self.db.add(
                AiCostEvent(
                    user_id=caller.id,
                    tenant_id=caller.tenant_id,
                    ai_session_id=sess.id,
                    ai_message_id=asst.id,
                    provider="safety_guard",
                    model_id="policy-rules-v1",
                    task_type="safety_gate",
                    tokens_in=0,
                    tokens_out=0,
                    estimated_cost_usd=Decimal("0.000000"),
                    latency_ms=asst.latency_ms,
                    is_fallback=False,
                )
            )
            await self.db.commit()
            await self.db.refresh(student_msg)
            await self.db.refresh(asst)
            return AiTurnResponse(
                session_id=sess.id,
                student_message=self._to_message_out(student_msg),
                assistant_message=self._to_message_out(asst),
            )

        # Module 1: Intent Router
        mode_choice = cast(TeachingMode, payload.teaching_mode or sess.teaching_mode)
        intent_res = classify_intent(raw_msg, requested_mode=mode_choice)

        # Module 2 & 3: PII-Stripped Student Context + Curriculum Context Resolvers
        student_ctx = await resolve_student_context(self.db, caller.id)
        curr_ctx = CurriculumContext.model_validate(sess.curriculum_context_jsonb)
        target_lang = (
            payload.language_code
            or sess.language_code
            or student_ctx.preferred_explanation_language
        )

        # Module 4: Rights-Filtered Hybrid RAG Search
        t_rag = time.perf_counter()
        chunks = await HybridRetrievalService(self.db).retrieve(
            query=raw_msg,
            grade_id=student_ctx.grade_id,
            subject_id=curr_ctx.subject_id,
            chapter_id=curr_ctx.chapter_id,
            language_code=target_lang,
            top_k=5,
        )
        rag_ms = int((time.perf_counter() - t_rag) * 1000)

        # Module 5: Pedagogical Teaching Planner & Conversation Window
        plan = build_pedagogical_plan(
            intent=intent_res,
            mode_override=mode_choice,
            student_ctx=student_ctx,
            curriculum_ctx=curr_ctx,
            target_language=target_lang,
        )
        history_rows = list(
            (
                await self.db.scalars(
                    select(AiMessage)
                    .where(AiMessage.ai_session_id == sess.id)
                    .order_by(AiMessage.created_at.asc())
                )
            ).all()
        )
        history_text = build_conversation_window(
            history_rows[:-1], session_summary=sess.context_summary, max_recent_turns=8
        )
        if len(history_rows) > 10:
            sess.context_summary = (
                f"Studied {curr_ctx.subject_name or 'STEM'} ({plan.mode}) "
                f"across {len(history_rows)} messages."
            )

        scrubbed_query = scrub_pii_text(raw_msg)
        sys_inst, usr_prompt = build_specialized_prompts(
            plan=plan,
            student_ctx=student_ctx,
            curriculum_ctx=curr_ctx,
            chunks=chunks,
            history_text=history_text,
            scrubbed_query=scrubbed_query,
        )

        # Execute LLM Gateway + Bounded Math/Science Verifier Retry Loop (max 2 retries)
        tool_records: list[tuple[str, dict[str, Any], dict[str, Any], bool, int]] = [
            (
                "rag_retrieve",
                {"query_len": len(raw_msg), "language": target_lang},
                {"chunks_returned": len(chunks)},
                True,
                rag_ms,
            )
        ]

        structured: StructuredTutorOutput | None = None
        provider_used = "grounded_fallback"
        model_used = "deterministic-v1"
        is_fallback = True
        tokens_in = 0
        tokens_out = 0

        llm_res, prov_errors = await self.gateway.invoke_or_fallback(
            ProviderInvocationRequest(
                system_instruction=sys_inst,
                user_prompt=usr_prompt,
                complexity=intent_res.complexity,
                response_json_schema={"type": "object"},
            ),
            preferred_provider=payload.preferred_provider,
        )

        if llm_res is not None:
            provider_used = llm_res.provider
            model_used = llm_res.model_id
            is_fallback = False
            tokens_in += llm_res.tokens_in
            tokens_out += llm_res.tokens_out
            try:
                if llm_res.parsed_json:
                    structured = StructuredTutorOutput.model_validate(llm_res.parsed_json)
                else:
                    structured = StructuredTutorOutput(answer_markdown=llm_res.raw_text)
            except Exception:
                structured = StructuredTutorOutput(answer_markdown=llm_res.raw_text)

        t_ver = time.perf_counter()
        verif_res = run_deterministic_verification_for_query(
            query=raw_msg,
            intent=intent_res,
            structured=structured,
        )
        ver_ms = int((time.perf_counter() - t_ver) * 1000)
        tool_records.append(
            (
                verif_res.verifier_type if verif_res.verifier_type != "none" else "sympy_verify",
                {"expr": verif_res.expression_or_equation},
                verif_res.model_dump(),
                verif_res.status != "verification_failed",
                ver_ms,
            )
        )

        # Bounded retry (<= 2 attempts) ONLY if external LLM failed verification and retries remain
        retries_used = 0
        while (
            llm_res is not None
            and verif_res.status == "verification_failed"
            and retries_used < self.settings.ai_max_verifier_retries
        ):
            retries_used += 1
            retry_prompt = (
                f"{usr_prompt}\n\n[VERIFIER_CORRECTION_ATTEMPT_{retries_used}]: "
                f"Previous candidate failed deterministic check: {verif_res.details}. "
                "Re-derive cleanly or acknowledge uncertainty."
            )
            retry_res, _ = await self.gateway.invoke_or_fallback(
                ProviderInvocationRequest(
                    system_instruction=sys_inst,
                    user_prompt=retry_prompt,
                    complexity="reasoning",
                    response_json_schema={"type": "object"},
                ),
                preferred_provider=payload.preferred_provider,
            )
            if retry_res is None:
                break
            tokens_in += retry_res.tokens_in
            tokens_out += retry_res.tokens_out
            if retry_res.parsed_json:
                structured = StructuredTutorOutput.model_validate(retry_res.parsed_json)
            else:
                structured = StructuredTutorOutput(answer_markdown=retry_res.raw_text)
            verif_res = run_deterministic_verification_for_query(
                query=raw_msg,
                intent=intent_res,
                structured=structured,
            )

        if structured is None:
            structured = synthesize_grounded_fallback(
                plan=plan,
                intent=intent_res,
                curriculum_ctx=curr_ctx,
                chunks=chunks,
                query=raw_msg,
                verif=verif_res,
                provider_errors=prov_errors,
            )
            tokens_in = max(1, len(usr_prompt.split()))
            tokens_out = max(1, len(structured.answer_markdown.split()))

        # Citation validation & Output safety
        valid_citations: list[CitedChunk] = validate_citations(structured.cited_chunk_ids, chunks)
        safety_out = evaluate_output_safety(structured.answer_markdown)
        final_markdown = (
            safety_out.safe_message
            if safety_out.action == "block" and safety_out.safe_message
            else scrub_pii_text(structured.answer_markdown)
        )

        latency_total = int((time.perf_counter() - t_start) * 1000)
        asst_msg = AiMessage(
            ai_session_id=sess.id,
            role="assistant",
            content_markdown=final_markdown,
            intent=intent_res.intent,
            pedagogical_mode=plan.mode,
            spoiler_guard=plan.spoiler_guard,
            citations_jsonb=[c.model_dump(mode="json") for c in valid_citations],
            follow_up_questions_jsonb=structured.follow_up_questions[:4],
            generated_practice_jsonb=[
                d.model_dump(mode="json") for d in structured.practice_drafts[:3]
            ],
            verification_status=verif_res.status,
            verification_summary_jsonb=verif_res.model_dump(mode="json"),
            provider_used=provider_used,
            model_used=model_used,
            prompt_version=plan.prompt_version,
            is_fallback=is_fallback,
            safety_verdict=safety_out.action,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_total,
        )
        self.db.add(asst_msg)
        await self.db.flush()

        for t_name, t_in, t_out, t_ok, t_ms in tool_records:
            self.db.add(
                AiToolCall(
                    ai_message_id=asst_msg.id,
                    tool_name=t_name,
                    input_jsonb=json.loads(json.dumps(t_in, default=str)),
                    output_jsonb=json.loads(json.dumps(t_out, default=str)),
                    succeeded=t_ok,
                    latency_ms=t_ms,
                )
            )

        est_cost = await self._estimate_cost(provider_used, model_used, tokens_in, tokens_out)
        self.db.add(
            AiCostEvent(
                user_id=caller.id,
                tenant_id=caller.tenant_id,
                ai_session_id=sess.id,
                ai_message_id=asst_msg.id,
                provider=provider_used,
                model_id=model_used,
                task_type=intent_res.intent,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=est_cost,
                latency_ms=latency_total,
                is_fallback=is_fallback,
            )
        )

        # Auto-enqueue verification failures or generated practice drafts for Academic Reviewer
        if verif_res.status == "verification_failed" or structured.practice_drafts:
            self.db.add(
                AiReviewQueueItem(
                    ai_session_id=sess.id,
                    ai_message_id=asst_msg.id,
                    student_id=caller.id,
                    reason=(
                        "verification_failed"
                        if verif_res.status == "verification_failed"
                        else "ai_practice_draft_generated"
                    ),
                    status="pending",
                )
            )

        sess.teaching_mode = plan.mode
        sess.language_code = plan.target_language
        await self.db.commit()
        await self.db.refresh(student_msg)
        await self.db.refresh(asst_msg)

        return AiTurnResponse(
            session_id=sess.id,
            student_message=self._to_message_out(student_msg),
            assistant_message=self._to_message_out(asst_msg),
        )

    async def flag_message(
        self, message_id: UUID, payload: AiFlagMessageRequest, caller: AuthenticatedUser
    ) -> AiReviewQueueOut:
        msg = await self.db.get(AiMessage, message_id)
        if msg is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="AI_MESSAGE_NOT_FOUND",
                message="Message not found.",
            )
        await self._load_owned_session(msg.ai_session_id, caller)
        item = AiReviewQueueItem(
            ai_session_id=msg.ai_session_id,
            ai_message_id=msg.id,
            student_id=caller.id,
            reason=f"student_report:{payload.reason.strip()}",
            status="pending",
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return self._to_review_out(item)

    async def list_review_queue(self) -> list[AiReviewQueueOut]:
        rows = (
            await self.db.scalars(
                select(AiReviewQueueItem).order_by(AiReviewQueueItem.created_at.desc()).limit(50)
            )
        ).all()
        return [self._to_review_out(r) for r in rows]

    async def decide_review_item(
        self,
        item_id: UUID,
        payload: AiReviewDecisionRequest,
        caller: AuthenticatedUser,
    ) -> AiReviewQueueOut:
        item = await self.db.get(AiReviewQueueItem, item_id)
        if item is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="REVIEW_ITEM_NOT_FOUND",
                message="AI review queue item not found.",
            )
        item.status = payload.decision
        item.reviewer_id = caller.id
        item.reviewer_notes = payload.reviewer_notes
        item.reviewed_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(item)
        return self._to_review_out(item)

    async def get_admin_cost_summary(self) -> AiCostSummaryResponse:
        rows = (await self.db.scalars(select(AiCostEvent))).all()
        return AiCostSummaryResponse(
            total_events=len(rows),
            total_tokens_in=sum(r.tokens_in for r in rows),
            total_tokens_out=sum(r.tokens_out for r in rows),
            total_estimated_cost_usd=round(sum(float(r.estimated_cost_usd) for r in rows), 6),
            fallback_count=sum(1 for r in rows if r.is_fallback),
        )

    @staticmethod
    def _to_session_out(sess: AiSession) -> AiSessionOut:
        return AiSessionOut(
            id=sess.id,
            session_type=sess.session_type,
            title=sess.title,
            teaching_mode=sess.teaching_mode,
            language_code=sess.language_code,
            curriculum_context=CurriculumContext.model_validate(sess.curriculum_context_jsonb),
            context_summary=sess.context_summary,
            status=sess.status,
            created_at=sess.created_at,
            updated_at=sess.updated_at,
        )

    @staticmethod
    def _to_message_out(m: AiMessage) -> AiMessageOut:
        return AiMessageOut(
            id=m.id,
            role=m.role,
            content_markdown=m.content_markdown,
            intent=m.intent,
            pedagogical_mode=m.pedagogical_mode,
            spoiler_guard=m.spoiler_guard,
            citations=[CitedChunk.model_validate(c) for c in (m.citations_jsonb or [])],
            follow_up_questions=list(m.follow_up_questions_jsonb or []),
            generated_practice=[
                PracticeDraftOut.model_validate(d) for d in (m.generated_practice_jsonb or [])
            ],
            verification_status=cast(VerificationStatus, m.verification_status),
            verification_summary=dict(m.verification_summary_jsonb or {}),
            provider_used=m.provider_used,
            model_used=m.model_used,
            prompt_version=m.prompt_version,
            is_fallback=m.is_fallback,
            safety_verdict=m.safety_verdict,
            tokens_in=m.tokens_in,
            tokens_out=m.tokens_out,
            latency_ms=m.latency_ms,
            created_at=m.created_at,
        )

    @staticmethod
    def _to_review_out(r: AiReviewQueueItem) -> AiReviewQueueOut:
        return AiReviewQueueOut(
            id=r.id,
            ai_session_id=r.ai_session_id,
            ai_message_id=r.ai_message_id,
            reason=r.reason,
            status=r.status,
            reviewer_notes=r.reviewer_notes,
            created_at=r.created_at,
            reviewed_at=r.reviewed_at,
        )
