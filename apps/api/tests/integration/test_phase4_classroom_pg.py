"""PostgreSQL 18 + WebSocket integration tests for Phase 4 Live Classroom, Whiteboard & Voice."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from src.core.config import Settings
from src.core.database import DatabaseManager
from src.core.outbox import OutboxEvent
from src.main import create_app
from src.modules.classroom.models import VoiceUsageLog
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import StubCheck
from tests.integration.test_phase1_e2e_pg import pg18_database_url  # noqa: F401


async def test_phase4_classroom_fsm_whiteboard_voice_and_isolation_pg18(
    pg18_database_url: str,  # noqa: F811
    tmp_path: Path,
) -> None:
    """Verify Phase 4 languages, FSM, checkpoints, doubts, whiteboard, voice & isolation."""
    settings = Settings(
        app_env="test",
        database_url=pg18_database_url,
        jwt_secret_key="phase4-integration-secret-key-at-least-32-chars",
        storage_local_dir=str(tmp_path / "p4_storage"),
    )
    app = create_app(settings_override=settings)
    db = DatabaseManager(settings)
    app.state.db = db
    app.state.redis = StubCheck(healthy=True)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Language Capability Registry honesty check
            r_lang = await client.get("/api/v1/languages/capabilities")
            assert r_lang.status_code == 200
            langs = {row["language_code"]: row for row in r_lang.json()}
            assert langs["en"]["tts_supported"] is True
            assert langs["hi"]["tts_supported"] is True
            assert langs["ta"]["tts_supported"] is False
            assert langs["ta"]["subtitle_supported"] is True
            assert langs["ur"]["rtl"] is True

            # 2. Register Student A & Student B
            r_a = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p4.student.a@example.com",
                    "password": "StudentPass!123",
                    "display_name": "P4 Student A",
                    "date_of_birth_year": 2009,
                    "role": "student",
                },
            )
            assert r_a.status_code == 201
            a_h = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

            r_b = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p4.student.b@example.com",
                    "password": "StudentPass!123",
                    "display_name": "P4 Student B",
                    "date_of_birth_year": 2009,
                    "role": "student",
                },
            )
            assert r_b.status_code == 201
            b_h = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

            # 3. Generate structured LessonArtifact
            r_gen = await client.post(
                "/api/v1/classroom/lessons/generate",
                headers=a_h,
                json={
                    "topic_title": "Quadratic Kinematics",
                    "language_code": "en",
                    "voice_language": "en",
                    "subtitle_language": "hi",
                },
            )
            assert r_gen.status_code == 201
            lp = r_gen.json()
            assert lp["title"] == "STEM: Quadratic Kinematics"
            assert len(lp["artifact"]["segments"]) == 4

            r_list_lp = await client.get("/api/v1/classroom/lessons", headers=a_h)
            assert r_list_lp.status_code == 200
            assert any(item["id"] == lp["id"] for item in r_list_lp.json())

            # 4. Create session -> READY state + honest TTS subtitle fallback
            r_sess = await client.post(
                "/api/v1/classroom/sessions",
                headers=a_h,
                json={"lesson_plan_id": lp["id"], "playback_speed": 1.0},
            )
            assert r_sess.status_code == 201
            sess = r_sess.json()
            sid = sess["id"]
            assert sess["state"] == "READY"
            assert sess["current_segment_seq"] == 1
            assert sess["tts_preview"]["audio_available"] is False
            assert sess["tts_preview"]["is_fallback"] is True
            assert sess["tts_preview"]["fallback_mode"] == "timed_subtitles_only"

            # Pause from READY must return 422 INVALID_CLASSROOM_TRANSITION
            r_bad_pause = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "pause"},
            )
            assert r_bad_pause.status_code == 422
            assert r_bad_pause.json()["error"]["code"] == "INVALID_CLASSROOM_TRANSITION"

            # Play -> Pause -> Seek -> Speed -> Set Language -> Resume
            r_play = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "play"},
            )
            assert r_play.status_code == 200
            assert r_play.json()["state"] == "PLAYING_SEGMENT"

            r_pause = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "pause", "playback_position_ms": 3400},
            )
            assert r_pause.status_code == 200
            assert r_pause.json()["state"] == "PAUSED"
            assert r_pause.json()["playback_position_ms"] == 3400

            r_speed = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "set_speed", "playback_speed": 1.25},
            )
            assert r_speed.status_code == 200
            assert r_speed.json()["playback_speed"] == 1.25

            r_bad_lang = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "set_language", "voice_language": "zz-invalid"},
            )
            assert r_bad_lang.status_code == 422

            r_resume = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "resume"},
            )
            assert r_resume.status_code == 200
            assert r_resume.json()["state"] == "PLAYING_SEGMENT"

            # 5. Advance Segment 1 -> 2 -> 3 (CHECKPOINT_WAIT)
            r_next2 = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "next"},
            )
            assert r_next2.status_code == 200
            assert r_next2.json()["current_segment_seq"] == 2

            r_next3 = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "next"},
            )
            assert r_next3.status_code == 200
            assert r_next3.json()["current_segment_seq"] == 3
            assert r_next3.json()["state"] == "CHECKPOINT_WAIT"

            # Cannot resume directly over active checkpoint
            r_res_ckpt = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "resume"},
            )
            assert r_res_ckpt.status_code == 422

            # Wrong checkpoint answer keeps CHECKPOINT_WAIT + hint
            r_ckpt_wrong = await client.post(
                f"/api/v1/classroom/sessions/{sid}/checkpoint",
                headers=a_h,
                json={"selected_key": "A"},
            )
            assert r_ckpt_wrong.status_code == 200
            assert r_ckpt_wrong.json()["passed"] is False
            assert r_ckpt_wrong.json()["session"]["state"] == "CHECKPOINT_WAIT"

            # Correct checkpoint answer advances cleanly to Segment 4
            r_ckpt_ok = await client.post(
                f"/api/v1/classroom/sessions/{sid}/checkpoint",
                headers=a_h,
                json={"selected_key": "B"},
            )
            assert r_ckpt_ok.status_code == 200
            assert r_ckpt_ok.json()["passed"] is True
            assert r_ckpt_ok.json()["session"]["current_segment_seq"] == 4
            assert r_ckpt_ok.json()["session"]["state"] == "PLAYING_SEGMENT"

            # Repeat and Previous work cleanly
            r_prev = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "previous"},
            )
            assert r_prev.status_code == 200
            assert r_prev.json()["current_segment_seq"] == 3

            r_repeat = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "repeat"},
            )
            assert r_repeat.status_code == 200
            assert r_repeat.json()["playback_position_ms"] == 0

            # 6. Student Doubt Interruption + Resume
            r_doubt = await client.post(
                f"/api/v1/classroom/sessions/{sid}/doubt",
                headers=a_h,
                json={"question": "Why is $y = 0.5 x^2$ symmetric around x = 0?"},
            )
            assert r_doubt.status_code == 200
            d_body = r_doubt.json()
            assert d_body["session"]["state"] == "DOUBT_INTERRUPTION"
            assert d_body["safety_verdict"] == "allow"
            assert len(d_body["overlay_actions"]) == 1

            r_res2 = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "resume"},
            )
            assert r_res2.status_code == 200
            assert r_res2.json()["state"] == "PLAYING_SEGMENT"

            # 7. Student Whiteboard Action, Undo, Redo, Snapshot & Reload Restore
            r_draw = await client.post(
                f"/api/v1/whiteboard/sessions/{sid}/events",
                headers=a_h,
                json={
                    "action": {
                        "id": "student_stroke_1",
                        "opcode": "DRAW_LINE",
                        "sequence": 100,
                        "at_ms": 0,
                        "aria_summary": "Student annotation arrow pointing at vertex",
                        "payload": {"x1": 100, "y1": 100, "x2": 220, "y2": 180, "color": "#2563eb"},
                    }
                },
            )
            assert r_draw.status_code == 201
            assert r_draw.json()["can_undo"] is True
            ids_after_draw = {a["id"] for a in r_draw.json()["active_whiteboard_actions"]}
            assert "student_stroke_1" in ids_after_draw

            r_undo = await client.post(
                f"/api/v1/whiteboard/sessions/{sid}/undo",
                headers=a_h,
            )
            assert r_undo.status_code == 200
            assert r_undo.json()["can_redo"] is True
            assert "student_stroke_1" not in {
                a["id"] for a in r_undo.json()["active_whiteboard_actions"]
            }

            r_redo = await client.post(
                f"/api/v1/whiteboard/sessions/{sid}/redo",
                headers=a_h,
            )
            assert r_redo.status_code == 200
            assert "student_stroke_1" in {
                a["id"] for a in r_redo.json()["active_whiteboard_actions"]
            }

            r_snap = await client.post(
                f"/api/v1/whiteboard/sessions/{sid}/snapshot",
                headers=a_h,
            )
            assert r_snap.status_code == 200
            assert r_snap.json()["version"] >= 1

            r_snap_latest = await client.get(
                f"/api/v1/whiteboard/sessions/{sid}/snapshots/latest",
                headers=a_h,
            )
            assert r_snap_latest.status_code == 200
            assert r_snap_latest.json()["id"] == r_snap.json()["id"]

            r_events = await client.get(
                f"/api/v1/whiteboard/sessions/{sid}/events",
                headers=a_h,
            )
            assert r_events.status_code == 200
            assert any(e["actor"] == "student" for e in r_events.json())

            # Session reload restores persisted state cleanly
            r_reload = await client.get(f"/api/v1/classroom/sessions/{sid}", headers=a_h)
            assert r_reload.status_code == 200
            assert r_reload.json()["playback_speed"] == 1.25
            assert "3" in r_reload.json()["checkpoint_results"]
            assert r_reload.json()["checkpoint_results"]["3"]["passed"] is True

            # Complete session -> emits OutboxEvent classroom.lesson_completed
            r_comp = await client.post(
                f"/api/v1/classroom/sessions/{sid}/control",
                headers=a_h,
                json={"action": "complete"},
            )
            assert r_comp.status_code == 200
            assert r_comp.json()["state"] == "COMPLETED"
            assert r_comp.json()["completed_at"] is not None

            # Cross-student isolation: Student B cannot access Student A's session
            r_iso = await client.get(f"/api/v1/classroom/sessions/{sid}", headers=b_h)
            assert r_iso.status_code == 404

            r_iso_wb = await client.post(
                f"/api/v1/whiteboard/sessions/{sid}/undo",
                headers=b_h,
            )
            assert r_iso_wb.status_code == 404

        async with db.session_factory() as verify_sess:
            voice_count = await verify_sess.scalar(
                select(func.count(VoiceUsageLog.id)).where(
                    VoiceUsageLog.classroom_session_id == UUID(sid)
                )
            )
            assert (voice_count or 0) >= 1
            outbox_row = await verify_sess.scalar(
                select(OutboxEvent).where(OutboxEvent.topic == "classroom.lesson_completed")
            )
            assert outbox_row is not None
            assert outbox_row.aggregate_id == sid
    finally:
        await db.dispose()


def test_phase4_classroom_websocket_pg18(
    pg18_database_url: str,  # noqa: F811
    tmp_path: Path,
) -> None:
    """Verify WebSocket status endpoint, JWT enforcement, live controls, and reconnect state."""
    settings = Settings(
        app_env="test",
        database_url=pg18_database_url,
        jwt_secret_key="phase4-ws-secret-key-at-least-32-chars",
        storage_local_dir=str(tmp_path / "p4_ws_storage"),
    )
    app = create_app(settings_override=settings)

    with TestClient(app) as client:
        # 1. /ws/v1/classroom/status reports ONLINE phase_4
        with client.websocket_connect("/ws/v1/classroom/status") as status_ws:
            hello = status_ws.receive_json()
            assert hello["type"] == "ONLINE"
            assert hello["phase"] == "phase_4"

        # 2. Create Student + Lesson + Session
        r_stu = client.post(
            "/api/v1/auth/register",
            json={
                "email": "p4.ws.student@example.com",
                "password": "StudentPass!123",
                "display_name": "P4 WS Student",
                "date_of_birth_year": 2009,
                "role": "student",
            },
        )
        assert r_stu.status_code == 201
        token = r_stu.json()["access_token"]
        hdrs = {"Authorization": f"Bearer {token}"}

        r_lp = client.post(
            "/api/v1/classroom/lessons/generate",
            headers=hdrs,
            json={"topic_title": "Projectile Motion"},
        )
        assert r_lp.status_code == 201
        r_sess = client.post(
            "/api/v1/classroom/sessions",
            headers=hdrs,
            json={"lesson_plan_id": r_lp.json()["id"]},
        )
        assert r_sess.status_code == 201
        sid = r_sess.json()["id"]

        # 3. Unauthenticated WS connection is rejected cleanly
        closed_unauth = False
        try:
            with client.websocket_connect(f"/ws/v1/classroom/{sid}") as bad_ws:
                bad_ws.receive_json()
        except WebSocketDisconnect:
            closed_unauth = True
        assert closed_unauth is True

        # 4. Authenticated WS connection receives initial READY state, responds to ping & play
        with client.websocket_connect(f"/ws/v1/classroom/{sid}?token={token}") as ws:
            init_msg = ws.receive_json()
            assert init_msg["type"] == "session.state"
            assert init_msg["state"] == "READY"

            ws.send_json({"action": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"

            ws.send_json({"action": "play"})
            m1 = ws.receive_json()
            m2 = ws.receive_json()
            assert {m1["type"], m2["type"]} == {"session.sync", "session.ack"}
            assert m1["state"] == "PLAYING_SEGMENT"
            assert m2["state"] == "PLAYING_SEGMENT"

        # 5. Reconnect recovers PLAYING_SEGMENT state from PostgreSQL
        with client.websocket_connect(f"/ws/v1/classroom/{sid}?token={token}") as ws_re:
            re_msg = ws_re.receive_json()
            assert re_msg["type"] == "session.state"
            assert re_msg["state"] == "PLAYING_SEGMENT"
