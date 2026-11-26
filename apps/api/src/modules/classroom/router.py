"""FastAPI REST & WebSocket routers for Live Classroom, Whiteboard, Voice & Languages."""

from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_context import AuthenticatedUser, get_db_session, require_permissions
from src.core.config import Settings, get_settings
from src.core.security import decode_access_token
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
    LessonGenerateRequest,
    LessonPlanOut,
    TTSRequestBody,
    TTSResponseOut,
    WhiteboardDrawRequest,
    WhiteboardEventOut,
    WhiteboardSnapshotOut,
)
from src.modules.classroom.service import WS_MANAGER, ClassroomService

classroom_router = APIRouter(prefix="/api/v1/classroom", tags=["classroom"])
whiteboard_router = APIRouter(prefix="/api/v1/whiteboard", tags=["whiteboard"])
voice_router = APIRouter(prefix="/api/v1/voice", tags=["voice"])
languages_router = APIRouter(prefix="/api/v1/languages", tags=["languages"])
classroom_ws_router = APIRouter(tags=["classroom-ws"])


def get_runtime_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", get_settings())


@languages_router.get("/capabilities", response_model=list[LanguageCapabilityOut])
async def get_language_capabilities(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> list[LanguageCapabilityOut]:
    return await ClassroomService(db, settings).list_language_capabilities()


@classroom_router.post(
    "/lessons/generate", response_model=LessonPlanOut, status_code=status.HTTP_201_CREATED
)
async def generate_classroom_lesson(
    payload: LessonGenerateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:create")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> LessonPlanOut:
    return await ClassroomService(db, settings).generate_lesson(payload, caller)


@classroom_router.get("/lessons", response_model=list[LessonPlanOut])
async def list_classroom_lessons(
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> list[LessonPlanOut]:
    return await ClassroomService(db, settings).list_lessons(caller)


@classroom_router.post(
    "/sessions",
    response_model=ClassroomSessionDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_classroom_session(
    payload: ClassroomSessionCreateRequest,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> ClassroomSessionDetailOut:
    return await ClassroomService(db, settings).create_session(payload, caller)


@classroom_router.get("/sessions", response_model=list[ClassroomSessionSummaryOut])
async def list_classroom_sessions(
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> list[ClassroomSessionSummaryOut]:
    return await ClassroomService(db, settings).list_sessions(caller)


@classroom_router.get("/sessions/{session_id}", response_model=ClassroomSessionDetailOut)
async def get_classroom_session_detail(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> ClassroomSessionDetailOut:
    return await ClassroomService(db, settings).get_session_detail(session_id, caller)


@classroom_router.post("/sessions/{session_id}/control", response_model=ClassroomSessionDetailOut)
async def control_classroom_session(
    session_id: UUID,
    payload: ClassroomControlRequest,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> ClassroomSessionDetailOut:
    return await ClassroomService(db, settings).apply_control(session_id, payload, caller)


@classroom_router.post("/sessions/{session_id}/checkpoint", response_model=CheckpointSubmitResponse)
async def submit_classroom_checkpoint(
    session_id: UUID,
    payload: CheckpointSubmitRequest,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> CheckpointSubmitResponse:
    return await ClassroomService(db, settings).submit_checkpoint(session_id, payload, caller)


@classroom_router.post("/sessions/{session_id}/doubt", response_model=DoubtInterruptResponse)
async def ask_classroom_doubt(
    session_id: UUID,
    payload: DoubtInterruptRequest,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> DoubtInterruptResponse:
    return await ClassroomService(db, settings).ask_doubt(session_id, payload, caller)


# ------------------------------------------------------------------
# Whiteboard Event Log, Student Drawing, Undo/Redo & Snapshots
# ------------------------------------------------------------------
@whiteboard_router.get("/sessions/{session_id}/events", response_model=list[WhiteboardEventOut])
async def get_whiteboard_events(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> list[WhiteboardEventOut]:
    return await ClassroomService(db, settings).list_whiteboard_events(session_id, caller)


@whiteboard_router.post(
    "/sessions/{session_id}/events",
    response_model=ClassroomSessionDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_whiteboard_event(
    session_id: UUID,
    payload: WhiteboardDrawRequest,
    caller: AuthenticatedUser = Depends(require_permissions("whiteboard:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> ClassroomSessionDetailOut:
    return await ClassroomService(db, settings).post_student_whiteboard_action(
        session_id, payload.action, caller
    )


@whiteboard_router.post("/sessions/{session_id}/undo", response_model=ClassroomSessionDetailOut)
async def undo_whiteboard_action(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("whiteboard:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> ClassroomSessionDetailOut:
    return await ClassroomService(db, settings).undo_whiteboard(session_id, caller)


@whiteboard_router.post("/sessions/{session_id}/redo", response_model=ClassroomSessionDetailOut)
async def redo_whiteboard_action(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("whiteboard:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> ClassroomSessionDetailOut:
    return await ClassroomService(db, settings).redo_whiteboard(session_id, caller)


@whiteboard_router.post("/sessions/{session_id}/snapshot", response_model=WhiteboardSnapshotOut)
async def create_whiteboard_snapshot(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("whiteboard:write")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> WhiteboardSnapshotOut:
    return await ClassroomService(db, settings).save_snapshot(session_id, caller)


@whiteboard_router.get(
    "/sessions/{session_id}/snapshots/latest", response_model=WhiteboardSnapshotOut
)
async def get_latest_whiteboard_snapshot(
    session_id: UUID,
    caller: AuthenticatedUser = Depends(require_permissions("classroom:attend")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> WhiteboardSnapshotOut:
    return await ClassroomService(db, settings).get_latest_snapshot(session_id, caller)


# ------------------------------------------------------------------
# Voice Synthesis & Cached Audio Delivery
# ------------------------------------------------------------------
@voice_router.post("/tts", response_model=TTSResponseOut)
async def synthesize_voice_tts(
    payload: TTSRequestBody,
    caller: AuthenticatedUser = Depends(require_permissions("voice:tts")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> TTSResponseOut:
    return await ClassroomService(db, settings).synthesize_tts(payload, caller)


@voice_router.get("/audio/{filename}")
async def fetch_cached_voice_audio(
    filename: str,
    caller: AuthenticatedUser = Depends(require_permissions("voice:tts")),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_runtime_settings),  # noqa: B008
) -> Response:
    _ = caller
    audio = ClassroomService(db, settings).read_cached_audio_bytes(filename)
    return Response(content=audio, media_type="audio/mpeg")


# ------------------------------------------------------------------
# Live Authoritative WebSocket Control & Synchronization Channel
# ------------------------------------------------------------------
@classroom_ws_router.websocket("/ws/v1/classroom/{session_id}")
async def classroom_live_ws(websocket: WebSocket, session_id: UUID) -> None:
    token = websocket.query_params.get("token", "")
    if not token:
        auth_hdr = websocket.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            token = auth_hdr.split(" ", 1)[1]
    settings: Settings = getattr(websocket.app.state, "settings", get_settings())
    try:
        claims = decode_access_token(token, settings=settings)
        caller_id = UUID(str(claims["sub"]))
        session_claim = UUID(str(claims["sid"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        await websocket.close(code=1008)
        return

    perms = frozenset(str(p) for p in claims.get("perms", []))
    roles = tuple(str(r) for r in claims.get("roles", []))
    caller = AuthenticatedUser(
        id=caller_id,
        email=str(claims.get("email", "")),
        roles=roles,
        permissions=perms,
        tenant_id=UUID(str(claims["tenant_id"])) if claims.get("tenant_id") else None,
        session_id=session_claim,
        mfa_verified=bool(claims.get("mfa_verified", False)),
        is_minor=bool(claims.get("is_minor", False)),
    )
    if "classroom:attend" not in caller.permissions:
        await websocket.close(code=1008)
        return

    db_mgr = websocket.app.state.db
    async with db_mgr.session_factory() as session:
        try:
            detail = await ClassroomService(session, settings).get_session_detail(
                session_id, caller, include_tts=False
            )
        except Exception:
            await websocket.close(code=1008)
            return

    await WS_MANAGER.connect(session_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "session.state",
                "state": detail.state,
                "current_segment_seq": detail.current_segment_seq,
                "playback_position_ms": detail.playback_position_ms,
                "playback_speed": detail.playback_speed,
                "voice_language": detail.voice_language,
                "subtitle_language": detail.subtitle_language,
            }
        )
        while True:
            msg = await websocket.receive_json()
            action = str(msg.get("action", "")).strip()
            async with db_mgr.session_factory() as session:
                svc = ClassroomService(session, settings)
                controls = {
                    "play",
                    "pause",
                    "resume",
                    "repeat",
                    "next",
                    "previous",
                    "seek",
                    "set_speed",
                }
                if action in controls:
                    updated = await svc.apply_control(
                        session_id,
                        ClassroomControlRequest(
                            action=action,
                            playback_position_ms=msg.get("playback_position_ms"),
                            playback_speed=msg.get("playback_speed"),
                        ),
                        caller,
                    )
                    await websocket.send_json(
                        {
                            "type": "session.ack",
                            "state": updated.state,
                            "current_segment_seq": updated.current_segment_seq,
                            "playback_position_ms": updated.playback_position_ms,
                            "playback_speed": updated.playback_speed,
                        }
                    )
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        WS_MANAGER.disconnect(session_id, websocket)
    except Exception:
        WS_MANAGER.disconnect(session_id, websocket)
