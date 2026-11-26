"""Server-authoritative Live AI Classroom State Machine, Replay, Sync & Doubt Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser
from src.core.config import Settings
from src.core.errors import AppError
from src.core.outbox import OutboxEvent
from src.modules.ai.public import resolve_classroom_doubt_answer
from src.modules.classroom.lesson_planner import generate_structured_lesson
from src.modules.classroom.models import (
    ClassroomEvent,
    ClassroomSession,
    LanguageCapability,
    LessonPlan,
    WhiteboardEvent,
    WhiteboardSnapshot,
)
from src.modules.classroom.schemas import (
    CheckpointSubmitRequest,
    CheckpointSubmitResponse,
    ClassroomControlRequest,
    ClassroomSessionCreateRequest,
    ClassroomSessionDetailOut,
    ClassroomSessionSummaryOut,
    DoubtInterruptRequest,
    DoubtInterruptResponse,
    LanguageCapabilityOut,
    LessonArtifact,
    LessonGenerateRequest,
    LessonPlanOut,
    TTSRequestBody,
    TTSResponseOut,
    WhiteboardActionSchema,
    WhiteboardEventOut,
    WhiteboardSnapshotOut,
)
from src.modules.classroom.voice.provider import (
    ElevenLabsVoiceAdapter,
    log_voice_usage,
)
from src.modules.classroom.whiteboard_engine import (
    append_whiteboard_event,
    get_active_whiteboard_state,
    redo_student_whiteboard_action,
    save_whiteboard_snapshot,
    undo_student_whiteboard_action,
)


class ClassroomConnectionManager:
    """In-memory WebSocket broadcast coordinator per classroom_session_id."""

    def __init__(self) -> None:
        self._sockets: dict[UUID, set[WebSocket]] = {}

    async def connect(self, session_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        self._sockets.setdefault(session_id, set()).add(ws)

    def disconnect(self, session_id: UUID, ws: WebSocket) -> None:
        conns = self._sockets.get(session_id)
        if conns and ws in conns:
            conns.discard(ws)

    async def broadcast(self, session_id: UUID, message: dict[str, Any]) -> None:
        conns = list(self._sockets.get(session_id, set()))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(session_id, ws)


WS_MANAGER = ClassroomConnectionManager()

_VALID_PLAY_SOURCES = {"IDLE", "READY", "PLAYING_SEGMENT", "PAUSED", "DOUBT_INTERRUPTION"}


class ClassroomService:
    """Controls authoritative Live Classroom sessions, whiteboard events, and TTS."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.voice_adapter = ElevenLabsVoiceAdapter(settings)

    # ------------------------------------------------------------------
    # Language Capability Registry
    # ------------------------------------------------------------------
    async def list_language_capabilities(self) -> list[LanguageCapabilityOut]:
        rows = (
            await self.db.scalars(
                select(LanguageCapability).order_by(
                    LanguageCapability.tts_supported.desc(),
                    LanguageCapability.language_code.asc(),
                )
            )
        ).all()
        return [
            LanguageCapabilityOut(
                language_code=r.language_code,
                display_name=r.display_name,
                native_name=r.native_name,
                rtl=r.rtl,
                text_quality_tier=r.text_quality_tier,
                translation_status=r.translation_status,
                tts_supported=r.tts_supported,
                stt_supported=r.stt_supported,
                voice_provider=r.voice_provider,
                pronunciation_tier=r.pronunciation_tier,
                subtitle_supported=r.subtitle_supported,
                academic_review_status=r.academic_review_status,
                known_limitations=r.known_limitations,
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Lesson Generation
    # ------------------------------------------------------------------
    async def generate_lesson(
        self, payload: LessonGenerateRequest, caller: AuthenticatedUser
    ) -> LessonPlanOut:
        artifact = await generate_structured_lesson(self.db, payload, caller.id)
        lp = LessonPlan(
            student_id=caller.id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            concept_id=payload.concept_id,
            title=artifact.title,
            language_code=artifact.language,
            voice_language=artifact.voice_language,
            subtitle_language=artifact.subtitle_language,
            schema_version=artifact.schema_version,
            lesson_artifact_jsonb=artifact.model_dump(mode="json"),
        )
        self.db.add(lp)
        await self.db.commit()
        await self.db.refresh(lp)
        return self._to_lesson_out(lp)

    async def list_lessons(self, caller: AuthenticatedUser) -> list[LessonPlanOut]:
        rows = (
            await self.db.scalars(
                select(LessonPlan)
                .where((LessonPlan.student_id == caller.id) | (LessonPlan.student_id.is_(None)))
                .order_by(LessonPlan.created_at.desc())
                .limit(30)
            )
        ).all()
        return [self._to_lesson_out(r) for r in rows]

    # ------------------------------------------------------------------
    # Classroom Sessions & Server State Machine
    # ------------------------------------------------------------------
    async def _next_classroom_seq(self, session_id: UUID) -> int:
        max_seq = await self.db.scalar(
            select(func.coalesce(func.max(ClassroomEvent.sequence_no), 0)).where(
                ClassroomEvent.classroom_session_id == session_id
            )
        )
        return int(max_seq or 0) + 1

    async def _record_event(
        self, session_id: UUID, event_type: str, payload: dict[str, Any]
    ) -> None:
        seq = await self._next_classroom_seq(session_id)
        self.db.add(
            ClassroomEvent(
                classroom_session_id=session_id,
                sequence_no=seq,
                event_type=event_type,
                payload_jsonb=payload,
            )
        )

    async def _seed_segment_whiteboard(
        self,
        *,
        session_id: UUID,
        segment_seq: int,
        actions: list[WhiteboardActionSchema],
    ) -> None:
        """Append AI canvas actions for segment if not already seeded, then snapshot."""
        existing_ai_for_seg = await self.db.scalar(
            select(func.count(WhiteboardEvent.id)).where(
                WhiteboardEvent.classroom_session_id == session_id,
                WhiteboardEvent.segment_seq == segment_seq,
                WhiteboardEvent.actor == "ai",
            )
        )
        if not existing_ai_for_seg:
            for act in actions:
                await append_whiteboard_event(
                    self.db,
                    session_id=session_id,
                    segment_seq=segment_seq,
                    actor="ai",
                    action=act,
                )
            await save_whiteboard_snapshot(self.db, session_id=session_id, segment_seq=segment_seq)

    async def create_session(
        self, payload: ClassroomSessionCreateRequest, caller: AuthenticatedUser
    ) -> ClassroomSessionDetailOut:
        lp = await self.db.get(LessonPlan, payload.lesson_plan_id)
        if lp is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LESSON_PLAN_NOT_FOUND",
                message="Lesson plan not found.",
            )
        artifact = LessonArtifact.model_validate(lp.lesson_artifact_jsonb)
        v_lang = (payload.voice_language or lp.voice_language).strip()
        s_lang = (payload.subtitle_language or lp.subtitle_language).strip()

        sess = ClassroomSession(
            student_id=caller.id,
            tenant_id=caller.tenant_id,
            lesson_plan_id=lp.id,
            state="READY",
            current_segment_seq=1,
            playback_position_ms=0,
            playback_speed=payload.playback_speed,
            voice_language=v_lang,
            subtitle_language=s_lang,
        )
        self.db.add(sess)
        await self.db.flush()

        # Seed initial Segment 1 AI whiteboard actions + snapshot
        first_seg = artifact.segments[0]
        await self._seed_segment_whiteboard(
            session_id=sess.id, segment_seq=1, actions=first_seg.canvas_actions
        )
        await self._record_event(
            sess.id, "session.created", {"lesson_plan_id": str(lp.id), "state": "READY"}
        )
        await self.db.commit()
        return await self.get_session_detail(sess.id, caller, include_tts=True)

    async def list_sessions(self, caller: AuthenticatedUser) -> list[ClassroomSessionSummaryOut]:
        rows = (
            await self.db.scalars(
                select(ClassroomSession)
                .where(ClassroomSession.student_id == caller.id)
                .order_by(ClassroomSession.last_active_at.desc())
                .limit(30)
            )
        ).all()
        out: list[ClassroomSessionSummaryOut] = []
        for s in rows:
            lp = await self.db.get(LessonPlan, s.lesson_plan_id)
            total_segs = len(lp.lesson_artifact_jsonb.get("segments", [])) if lp else 0
            out.append(
                ClassroomSessionSummaryOut(
                    id=s.id,
                    lesson_plan_id=s.lesson_plan_id,
                    title=lp.title if lp else "Live Lesson",
                    state=s.state,
                    current_segment_seq=s.current_segment_seq,
                    total_segments=total_segs,
                    playback_speed=s.playback_speed,
                    voice_language=s.voice_language,
                    subtitle_language=s.subtitle_language,
                    started_at=s.started_at,
                    last_active_at=s.last_active_at,
                    completed_at=s.completed_at,
                )
            )
        return out

    async def _load_owned_session(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> tuple[ClassroomSession, LessonArtifact]:
        sess = await self.db.get(ClassroomSession, session_id)
        if sess is None or sess.student_id != caller.id:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="CLASSROOM_SESSION_NOT_FOUND",
                message="Classroom session not found.",
            )
        lp = await self.db.get(LessonPlan, sess.lesson_plan_id)
        if lp is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="LESSON_PLAN_NOT_FOUND",
                message="Associated lesson plan missing.",
            )
        return sess, LessonArtifact.model_validate(lp.lesson_artifact_jsonb)

    async def _tts_for_segment(
        self,
        *,
        sess: ClassroomSession,
        artifact: LessonArtifact,
        caller: AuthenticatedUser,
    ) -> TTSResponseOut:
        seg = next(
            (s for s in artifact.segments if s.sequence == sess.current_segment_seq),
            artifact.segments[-1],
        )
        lang_cap = await self.db.get(LanguageCapability, sess.voice_language)
        if lang_cap is not None and not lang_cap.tts_supported:
            return TTSResponseOut(
                audio_available=False,
                audio_url=None,
                cache_key=None,
                normalized_speakable_text=seg.narration,
                provider="language_capability_registry",
                voice_id=self.voice_adapter.default_voice_id,
                language_code=sess.voice_language,
                characters_count=len(seg.narration),
                estimated_duration_ms=seg.duration_ms,
                cache_hit=False,
                is_fallback=True,
                fallback_mode="timed_subtitles_only",
                limitation_notice=lang_cap.known_limitations
                or f"Voice TTS disabled for '{sess.voice_language}'; using timed subtitles.",
            )

        res = await self.voice_adapter.synthesize_speech(
            text=seg.narration,
            language_code=sess.voice_language,
            speed=sess.playback_speed,
        )
        await log_voice_usage(
            self.db,
            user_id=caller.id,
            classroom_session_id=sess.id,
            language_code=sess.voice_language,
            res=res,
        )
        audio_url = (
            f"/api/v1/voice/audio/{res.cache_key.split('/')[-1]}"
            if res.audio_available and res.cache_key
            else None
        )
        return TTSResponseOut(
            audio_available=res.audio_available,
            audio_url=audio_url,
            cache_key=res.cache_key,
            normalized_speakable_text=res.normalized_text,
            provider=res.provider,
            voice_id=res.voice_id,
            language_code=sess.voice_language,
            characters_count=res.characters_count,
            estimated_duration_ms=res.estimated_duration_ms,
            cache_hit=res.cache_hit,
            is_fallback=res.is_fallback,
            fallback_mode=res.fallback_mode,
            limitation_notice=res.limitation_notice,
        )

    async def get_session_detail(
        self,
        session_id: UUID,
        caller: AuthenticatedUser,
        *,
        include_tts: bool = True,
    ) -> ClassroomSessionDetailOut:
        sess, artifact = await self._load_owned_session(session_id, caller)
        wb_actions, can_undo, can_redo = await get_active_whiteboard_state(self.db, sess.id)
        tts_preview = (
            await self._tts_for_segment(sess=sess, artifact=artifact, caller=caller)
            if include_tts
            else None
        )
        if include_tts:
            await self.db.commit()
        return ClassroomSessionDetailOut(
            id=sess.id,
            lesson_plan_id=sess.lesson_plan_id,
            state=sess.state,
            current_segment_seq=sess.current_segment_seq,
            playback_position_ms=sess.playback_position_ms,
            playback_speed=sess.playback_speed,
            voice_language=sess.voice_language,
            subtitle_language=sess.subtitle_language,
            checkpoint_results=dict(sess.checkpoint_results_jsonb or {}),
            lesson_artifact=artifact,
            active_whiteboard_actions=wb_actions,
            can_undo=can_undo,
            can_redo=can_redo,
            tts_preview=tts_preview,
            started_at=sess.started_at,
            last_active_at=sess.last_active_at,
            completed_at=sess.completed_at,
        )

    async def apply_control(
        self,
        session_id: UUID,
        payload: ClassroomControlRequest,
        caller: AuthenticatedUser,
    ) -> ClassroomSessionDetailOut:
        sess, artifact = await self._load_owned_session(session_id, caller)
        now = datetime.now(UTC)
        total_segs = len(artifact.segments)
        act = payload.action

        if act in {"play", "resume"}:
            if sess.state == "CHECKPOINT_WAIT":
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    code="INVALID_CLASSROOM_TRANSITION",
                    message="Complete the active checkpoint before resuming.",
                )
            if sess.state == "COMPLETED":
                sess.current_segment_seq = 1
                sess.playback_position_ms = 0
            elif sess.state not in _VALID_PLAY_SOURCES:
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    code="INVALID_CLASSROOM_TRANSITION",
                    message=f"Cannot play/resume from state {sess.state}.",
                )
            sess.state = "PLAYING_SEGMENT"
            cur_seg = artifact.segments[sess.current_segment_seq - 1]
            await self._seed_segment_whiteboard(
                session_id=sess.id,
                segment_seq=cur_seg.sequence,
                actions=cur_seg.canvas_actions,
            )

        elif act == "pause":
            if sess.state != "PLAYING_SEGMENT":
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    code="INVALID_CLASSROOM_TRANSITION",
                    message="Only PLAYING_SEGMENT sessions can pause.",
                )
            sess.state = "PAUSED"
            if payload.playback_position_ms is not None:
                sess.playback_position_ms = payload.playback_position_ms

        elif act == "repeat":
            sess.playback_position_ms = 0
            sess.state = "PLAYING_SEGMENT"

        elif act == "seek":
            if payload.playback_position_ms is not None:
                sess.playback_position_ms = payload.playback_position_ms

        elif act == "previous":
            target_seq = max(1, sess.current_segment_seq - 1)
            sess.current_segment_seq = target_seq
            sess.playback_position_ms = 0
            sess.state = "PLAYING_SEGMENT"

        elif act == "next":
            cur_seg = artifact.segments[sess.current_segment_seq - 1]
            ckpt_key = str(cur_seg.sequence)
            if (
                cur_seg.checkpoint is not None
                and not sess.checkpoint_results_jsonb.get(ckpt_key, {}).get("passed")
                and sess.state != "CHECKPOINT_WAIT"
            ):
                sess.state = "CHECKPOINT_WAIT"
            elif sess.current_segment_seq >= total_segs:
                sess.state = "COMPLETED"
                sess.completed_at = now
                self.db.add(
                    OutboxEvent(
                        tenant_id=sess.tenant_id,
                        aggregate_type="classroom_session",
                        aggregate_id=str(sess.id),
                        topic="classroom.lesson_completed",
                        idempotency_key=f"classroom_complete:{sess.id}",
                        payload_jsonb={
                            "student_id": str(sess.student_id),
                            "classroom_session_id": str(sess.id),
                            "lesson_plan_id": str(sess.lesson_plan_id),
                        },
                        status="pending",
                        available_at=now,
                    )
                )
            else:
                sess.current_segment_seq += 1
                sess.playback_position_ms = 0
                next_seg = artifact.segments[sess.current_segment_seq - 1]
                await self._seed_segment_whiteboard(
                    session_id=sess.id,
                    segment_seq=next_seg.sequence,
                    actions=next_seg.canvas_actions,
                )
                sess.state = "CHECKPOINT_WAIT" if next_seg.checkpoint else "PLAYING_SEGMENT"

        elif act == "set_speed":
            if payload.playback_speed is not None:
                sess.playback_speed = payload.playback_speed

        elif act == "set_language":
            if payload.voice_language:
                cap = await self.db.get(LanguageCapability, payload.voice_language)
                if cap is None:
                    raise AppError(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        code="UNSUPPORTED_LANGUAGE",
                        message=(
                            f"Language '{payload.voice_language}' is not in Capability Registry."
                        ),
                    )
                sess.voice_language = payload.voice_language
            if payload.subtitle_language:
                cap_s = await self.db.get(LanguageCapability, payload.subtitle_language)
                if cap_s is None:
                    raise AppError(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        code="UNSUPPORTED_LANGUAGE",
                        message=f"Subtitle language '{payload.subtitle_language}' not in Registry.",
                    )
                sess.subtitle_language = payload.subtitle_language

        elif act == "complete":
            sess.state = "COMPLETED"
            sess.completed_at = now
            await save_whiteboard_snapshot(
                self.db, session_id=sess.id, segment_seq=sess.current_segment_seq
            )
            self.db.add(
                OutboxEvent(
                    tenant_id=sess.tenant_id,
                    aggregate_type="classroom_session",
                    aggregate_id=str(sess.id),
                    topic="classroom.lesson_completed",
                    idempotency_key=f"classroom_complete:{sess.id}",
                    payload_jsonb={
                        "student_id": str(sess.student_id),
                        "classroom_session_id": str(sess.id),
                        "lesson_plan_id": str(sess.lesson_plan_id),
                    },
                    status="pending",
                    available_at=now,
                )
            )

        sess.last_active_at = now
        await self._record_event(
            sess.id,
            f"control.{act}",
            {
                "state": sess.state,
                "segment_seq": sess.current_segment_seq,
                "speed": sess.playback_speed,
                "voice_language": sess.voice_language,
            },
        )
        await self.db.commit()
        detail = await self.get_session_detail(sess.id, caller, include_tts=True)
        await WS_MANAGER.broadcast(
            sess.id,
            {
                "type": "session.sync",
                "state": detail.state,
                "current_segment_seq": detail.current_segment_seq,
                "playback_position_ms": detail.playback_position_ms,
                "playback_speed": detail.playback_speed,
            },
        )
        return detail

    async def submit_checkpoint(
        self,
        session_id: UUID,
        payload: CheckpointSubmitRequest,
        caller: AuthenticatedUser,
    ) -> CheckpointSubmitResponse:
        sess, artifact = await self._load_owned_session(session_id, caller)
        seg = artifact.segments[sess.current_segment_seq - 1]
        if seg.checkpoint is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="NO_ACTIVE_CHECKPOINT",
                message="Current lesson segment has no checkpoint question.",
            )
        ckpt = seg.checkpoint
        passed = False
        if ckpt.question_type == "mcq_single" and ckpt.correct_key:
            passed = (payload.selected_key or "").strip().upper() == ckpt.correct_key.upper()
        elif ckpt.question_type == "numerical" and ckpt.expected_value is not None:
            passed = (
                payload.numeric_value is not None
                and abs(payload.numeric_value - ckpt.expected_value) <= 0.05
            )

        results = dict(sess.checkpoint_results_jsonb or {})
        results[str(seg.sequence)] = {
            "passed": passed,
            "answered_at": datetime.now(UTC).isoformat(),
        }
        sess.checkpoint_results_jsonb = results
        sess.last_active_at = datetime.now(UTC)
        if passed:
            if sess.current_segment_seq < len(artifact.segments):
                sess.current_segment_seq += 1
                next_seg = artifact.segments[sess.current_segment_seq - 1]
                await self._seed_segment_whiteboard(
                    session_id=sess.id,
                    segment_seq=next_seg.sequence,
                    actions=next_seg.canvas_actions,
                )
                sess.state = "PLAYING_SEGMENT"
            else:
                sess.state = "COMPLETED"
                sess.completed_at = datetime.now(UTC)

        await self._record_event(
            sess.id,
            "checkpoint.submitted",
            {"segment_seq": seg.sequence, "passed": passed, "next_state": sess.state},
        )
        await self.db.commit()
        detail = await self.get_session_detail(sess.id, caller, include_tts=True)
        feedback = (
            "Correct! Advancing cleanly to the next segment."
            if passed
            else f"Not quite yet. Hint: {ckpt.remediation_hint}"
        )
        return CheckpointSubmitResponse(passed=passed, feedback=feedback, session=detail)

    async def ask_doubt(
        self,
        session_id: UUID,
        payload: DoubtInterruptRequest,
        caller: AuthenticatedUser,
    ) -> DoubtInterruptResponse:
        sess, artifact = await self._load_owned_session(session_id, caller)
        lp = await self.db.get(LessonPlan, sess.lesson_plan_id)
        sess.state = "DOUBT_INTERRUPTION"
        sess.last_active_at = datetime.now(UTC)

        ans = await resolve_classroom_doubt_answer(
            self.db,
            settings=self.settings,
            caller=caller,
            doubt_text=payload.question,
            lesson_title=artifact.title,
            subject_id=lp.subject_id if lp else None,
            chapter_id=lp.chapter_id if lp else None,
        )
        overlay = [
            WhiteboardActionSchema(
                id=f"doubt_note_{sess.current_segment_seq}",
                opcode="WRITE_TEXT",
                sequence=999,
                at_ms=0,
                aria_summary="Doubt clarification callout note added to whiteboard.",
                payload={
                    "x": 40,
                    "y": 445,
                    "text": f"Doubt Check ({ans.verification_status}): {payload.question[:80]}",
                    "font_size": 14,
                    "color": "#7c3aed",
                    "max_width": 620,
                },
            )
        ]
        if ans.safety_verdict == "allow":
            await append_whiteboard_event(
                self.db,
                session_id=sess.id,
                segment_seq=sess.current_segment_seq,
                actor="ai",
                action=overlay[0],
            )
        await self._record_event(
            sess.id,
            "doubt.interrupted",
            {
                "segment_seq": sess.current_segment_seq,
                "safety": ans.safety_verdict,
                "verification_status": ans.verification_status,
            },
        )
        await self.db.commit()
        detail = await self.get_session_detail(sess.id, caller, include_tts=False)
        await WS_MANAGER.broadcast(
            sess.id,
            {
                "type": "doubt.answered",
                "state": detail.state,
                "verification": ans.verification_status,
            },
        )
        return DoubtInterruptResponse(
            answer_markdown=ans.answer_markdown,
            verification_status=ans.verification_status,
            safety_verdict=ans.safety_verdict,
            overlay_actions=overlay if ans.safety_verdict == "allow" else [],
            session=detail,
        )

    # ------------------------------------------------------------------
    # Whiteboard Event History, Student Actions, Undo/Redo, Snapshots & TTS
    # ------------------------------------------------------------------
    async def list_whiteboard_events(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> list[WhiteboardEventOut]:
        await self._load_owned_session(session_id, caller)
        rows = (
            await self.db.scalars(
                select(WhiteboardEvent)
                .where(WhiteboardEvent.classroom_session_id == session_id)
                .order_by(WhiteboardEvent.sequence_no.asc())
            )
        ).all()
        return [
            WhiteboardEventOut(
                id=r.id,
                segment_seq=r.segment_seq,
                sequence_no=r.sequence_no,
                actor=r.actor,
                action_type=r.action_type,
                action=WhiteboardActionSchema.model_validate(r.action_payload_jsonb),
                is_undone=r.is_undone,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def post_student_whiteboard_action(
        self,
        session_id: UUID,
        action: WhiteboardActionSchema,
        caller: AuthenticatedUser,
    ) -> ClassroomSessionDetailOut:
        sess, _ = await self._load_owned_session(session_id, caller)
        await append_whiteboard_event(
            self.db,
            session_id=sess.id,
            segment_seq=sess.current_segment_seq,
            actor="student",
            action=action,
        )
        await self.db.commit()
        detail = await self.get_session_detail(sess.id, caller, include_tts=False)
        await WS_MANAGER.broadcast(
            sess.id,
            {"type": "whiteboard.updated", "count": len(detail.active_whiteboard_actions)},
        )
        return detail

    async def undo_whiteboard(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> ClassroomSessionDetailOut:
        await self._load_owned_session(session_id, caller)
        await undo_student_whiteboard_action(self.db, session_id)
        await self.db.commit()
        return await self.get_session_detail(session_id, caller, include_tts=False)

    async def redo_whiteboard(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> ClassroomSessionDetailOut:
        await self._load_owned_session(session_id, caller)
        await redo_student_whiteboard_action(self.db, session_id)
        await self.db.commit()
        return await self.get_session_detail(session_id, caller, include_tts=False)

    async def save_snapshot(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> WhiteboardSnapshotOut:
        sess, _ = await self._load_owned_session(session_id, caller)
        snap = await save_whiteboard_snapshot(
            self.db, session_id=sess.id, segment_seq=sess.current_segment_seq
        )
        await self.db.commit()
        await self.db.refresh(snap)
        actions = [
            WhiteboardActionSchema.model_validate(a) for a in snap.snapshot_jsonb.get("actions", [])
        ]
        return WhiteboardSnapshotOut(
            id=snap.id,
            segment_seq=snap.segment_seq,
            version=snap.version,
            actions=actions,
            created_at=snap.created_at,
        )

    async def get_latest_snapshot(
        self, session_id: UUID, caller: AuthenticatedUser
    ) -> WhiteboardSnapshotOut:
        await self._load_owned_session(session_id, caller)
        snap = await self.db.scalar(
            select(WhiteboardSnapshot)
            .where(WhiteboardSnapshot.classroom_session_id == session_id)
            .order_by(WhiteboardSnapshot.version.desc())
        )
        if snap is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="SNAPSHOT_NOT_FOUND",
                message="No whiteboard snapshot saved yet.",
            )
        actions = [
            WhiteboardActionSchema.model_validate(a) for a in snap.snapshot_jsonb.get("actions", [])
        ]
        return WhiteboardSnapshotOut(
            id=snap.id,
            segment_seq=snap.segment_seq,
            version=snap.version,
            actions=actions,
            created_at=snap.created_at,
        )

    async def synthesize_tts(
        self, payload: TTSRequestBody, caller: AuthenticatedUser
    ) -> TTSResponseOut:
        res = await self.voice_adapter.synthesize_speech(
            text=payload.text,
            language_code=payload.language_code,
            voice_id=payload.voice_id,
            speed=payload.speed,
        )
        await log_voice_usage(
            self.db,
            user_id=caller.id,
            classroom_session_id=payload.classroom_session_id,
            language_code=payload.language_code,
            res=res,
        )
        await self.db.commit()
        audio_url = (
            f"/api/v1/voice/audio/{res.cache_key.split('/')[-1]}"
            if res.audio_available and res.cache_key
            else None
        )
        return TTSResponseOut(
            audio_available=res.audio_available,
            audio_url=audio_url,
            cache_key=res.cache_key,
            normalized_speakable_text=res.normalized_text,
            provider=res.provider,
            voice_id=res.voice_id,
            language_code=payload.language_code,
            characters_count=res.characters_count,
            estimated_duration_ms=res.estimated_duration_ms,
            cache_hit=res.cache_hit,
            is_fallback=res.is_fallback,
            fallback_mode=res.fallback_mode,
            limitation_notice=res.limitation_notice,
        )

    def read_cached_audio_bytes(self, filename: str) -> bytes:
        try:
            return self.voice_adapter.read_cached_audio(f"voice_cache/{filename}")
        except (FileNotFoundError, ValueError) as exc:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="AUDIO_NOT_FOUND",
                message="Requested cached audio segment not found.",
            ) from exc

    @staticmethod
    def _to_lesson_out(lp: LessonPlan) -> LessonPlanOut:
        return LessonPlanOut(
            id=lp.id,
            title=lp.title,
            language_code=lp.language_code,
            voice_language=lp.voice_language,
            subtitle_language=lp.subtitle_language,
            schema_version=lp.schema_version,
            artifact=LessonArtifact.model_validate(lp.lesson_artifact_jsonb),
            created_at=lp.created_at,
        )
