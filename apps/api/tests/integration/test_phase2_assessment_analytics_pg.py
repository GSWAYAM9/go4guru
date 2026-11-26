"""PostgreSQL 18 integration tests for Phase 2 Quiz & Assessment Engine + Outbox Analytics."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pyotp
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from src.core.config import Settings, get_settings
from src.core.database import DatabaseManager
from src.core.outbox import OutboxEvent
from src.core.security import hash_password
from src.main import create_app
from src.modules.analytics.public import process_outbox_learning_events
from src.modules.assessment.models import AssessmentAttempt
from src.modules.identity.models import Role, User, UserProfile, UserRole

from tests.conftest import StubCheck
from tests.integration.test_phase1_e2e_pg import pg18_database_url  # noqa: F401


async def _promote_user_role(db: DatabaseManager, email: str, role_code: str) -> None:
    async with db.session_factory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password("AdminPass!123"),
                status="active",
                is_minor=False,
            )
            session.add(user)
            await session.flush()
            session.add(UserProfile(user_id=user.id, display_name=f"Role {role_code}"))
        role = await session.scalar(select(Role).where(Role.code == role_code))
        assert role is not None
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()


async def _auth_mfa(client: AsyncClient, email: str) -> dict[str, str]:
    rl = await client.post("/api/v1/auth/login", json={"email": email, "password": "AdminPass!123"})
    assert rl.status_code == 200
    uh = {"Authorization": f"Bearer {rl.json()['access_token']}"}
    rs = await client.post("/api/v1/auth/mfa/setup", headers=uh)
    assert rs.status_code == 200
    rv = await client.post(
        "/api/v1/auth/mfa/verify",
        headers=uh,
        json={"code": pyotp.TOTP(rs.json()["secret"]).now()},
    )
    assert rv.status_code == 200
    return {"Authorization": f"Bearer {rv.json()['access_token']}"}


async def test_phase2_quiz_assessment_timer_concurrency_and_analytics_pg18(
    pg18_database_url: str,  # noqa: F811
    tmp_path: Path,
) -> None:
    """Exercise configurable patterns, quiz selection, timer expiry, parallel submit, and outbox."""
    settings = Settings(
        app_env="test",
        database_url=pg18_database_url,
        jwt_secret_key="integration-test-jwt-secret-key-0123456789abcdef",
        redis_url="redis://127.0.0.1:6379/0",
        storage_local_dir=str(tmp_path / "private_storage"),
    )
    app = create_app(settings_override=settings)
    db = DatabaseManager(settings)
    app.state.db = db
    app.state.redis = StubCheck(healthy=True)

    try:
        await _promote_user_role(db, "p2.cadmin@example.com", "content_admin")
        await _promote_user_role(db, "p2.reviewer@example.com", "academic_reviewer")
        await _promote_user_role(db, "p2.teacher@example.com", "teacher")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Register two students & login privileged actors
            r_stu_a = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p2.student.a@example.com",
                    "password": "StudentPass!123",
                    "display_name": "Phase2 Student A",
                    "date_of_birth_year": 2008,
                    "role": "student",
                },
            )
            assert r_stu_a.status_code == 201
            stu_a_h = {"Authorization": f"Bearer {r_stu_a.json()['access_token']}"}

            r_stu_b = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p2.student.b@example.com",
                    "password": "StudentPass!123",
                    "display_name": "Phase2 Student B",
                    "date_of_birth_year": 2008,
                    "role": "student",
                },
            )
            assert r_stu_b.status_code == 201
            stu_b_h = {"Authorization": f"Bearer {r_stu_b.json()['access_token']}"}

            ca_h = await _auth_mfa(client, "p2.cadmin@example.com")
            rev_h = await _auth_mfa(client, "p2.reviewer@example.com")
            r_t_login = await client.post(
                "/api/v1/auth/login",
                json={"email": "p2.teacher@example.com", "password": "AdminPass!123"},
            )
            assert r_t_login.status_code == 200
            teacher_h = {"Authorization": f"Bearer {r_t_login.json()['access_token']}"}

            # 2. Seed Content Rights, Curriculum & 6 Published Questions (3 types / 3 difficulties)
            src = (
                await client.post(
                    "/api/v1/content-rights/sources",
                    headers=ca_h,
                    json={
                        "name": "Phase2 Original Physics Authors",
                        "owner_name": "Go4Guru",
                        "source_category": "original_platform",
                    },
                )
            ).json()
            lic = (
                await client.post(
                    "/api/v1/content-rights/licenses",
                    headers=ca_h,
                    json={
                        "source_id": src["id"],
                        "license_name": "Go4Guru Phase2 Internal",
                        "commercial_use_allowed": True,
                        "hosting_allowed": True,
                        "embedding_allowed": True,
                    },
                )
            ).json()
            await client.post(
                f"/api/v1/content-rights/licenses/{lic['id']}/review",
                headers=ca_h,
                json={"legal_review_status": "approved"},
            )

            board = (
                await client.post(
                    "/api/v1/curriculum/boards",
                    headers=ca_h,
                    json={"code": "P2-CBSE", "name": "Phase2 CBSE Board"},
                )
            ).json()
            sess = (
                await client.post(
                    "/api/v1/curriculum/sessions",
                    headers=ca_h,
                    json={"code": "2026-P2", "starts_on": "2026-04-01", "ends_on": "2027-03-31"},
                )
            ).json()
            ver = (
                await client.post(
                    "/api/v1/curriculum/versions",
                    headers=ca_h,
                    json={
                        "board_id": board["id"],
                        "academic_session_id": sess["id"],
                        "version_tag": "2026-p2-v1",
                    },
                )
            ).json()
            grades = (await client.get("/api/v1/curriculum/grades")).json()
            grade_12 = next(g for g in grades if g["number"] == 12)
            subj = (
                await client.post(
                    "/api/v1/curriculum/subjects",
                    headers=ca_h,
                    json={"code": "P2-PHY", "name": "Phase2 Physics", "discipline": "physics"},
                )
            ).json()
            book = (
                await client.post(
                    "/api/v1/curriculum/books",
                    headers=ca_h,
                    json={
                        "curriculum_version_id": ver["id"],
                        "grade_id": grade_12["id"],
                        "subject_id": subj["id"],
                        "title": "Class 12 Physics Volume 1",
                        "publisher": "Go4Guru Original",
                    },
                )
            ).json()
            chap = (
                await client.post(
                    "/api/v1/curriculum/chapters",
                    headers=ca_h,
                    json={
                        "book_id": book["id"],
                        "sequence_no": 1,
                        "code": "CH-KIN",
                        "title": "Kinematics",
                    },
                )
            ).json()
            sec = (
                await client.post(
                    "/api/v1/curriculum/sections",
                    headers=ca_h,
                    json={
                        "chapter_id": chap["id"],
                        "sequence_no": 1,
                        "title": "Motion in 1D",
                    },
                )
            ).json()
            topic = (
                await client.post(
                    "/api/v1/curriculum/topics",
                    headers=ca_h,
                    json={
                        "chapter_id": chap["id"],
                        "section_id": sec["id"],
                        "sequence_no": 1,
                        "title": "Velocity & Acceleration",
                    },
                )
            ).json()
            concept = (
                await client.post(
                    "/api/v1/curriculum/concepts",
                    headers=ca_h,
                    json={
                        "topic_id": topic["id"],
                        "code": "CON-EQ",
                        "title": "Kinematic Equations",
                    },
                )
            ).json()
            await client.post(f"/api/v1/curriculum/versions/{ver['id']}/publish", headers=ca_h)

            async def _create_and_publish_q(
                *,
                qtype: str,
                difficulty: str,
                stem: str,
                correct: dict[str, object],
                options: list[dict[str, object]],
            ) -> tuple[str, str]:
                r_q = await client.post(
                    "/api/v1/questions",
                    headers=ca_h,
                    json={
                        "question_type": qtype,
                        "curriculum_version_id": ver["id"],
                        "grade_id": grade_12["id"],
                        "subject_id": subj["id"],
                        "chapter_id": chap["id"],
                        "topic_id": topic["id"],
                        "concept_id": concept["id"],
                        "difficulty": difficulty,
                        "stem_markdown": stem,
                        "correct_answer_jsonb": correct,
                        "options": options,
                        "ai_generated": False,
                        "provenance": {
                            "source_id": src["id"],
                            "license_id": lic["id"],
                            "source_type": "original",
                        },
                        "solutions": [
                            {
                                "explanation_markdown": ("Solved directly from kinematic rules."),
                                "steps_jsonb": ["Identify knowns", "Apply formula"],
                                "common_mistakes_markdown": "Watch units.",
                            }
                        ],
                    },
                )
                assert r_q.status_code == 201, r_q.text
                qid = r_q.json()["id"]
                qvid = r_q.json()["version_id"]
                rp = await client.post(
                    f"/api/v1/questions/{qid}/review",
                    headers=rev_h,
                    json={"decision": "approved", "publish": True},
                )
                assert rp.status_code == 200
                return qid, qvid

            mcq_opts_b = [
                {"option_key": "A", "content_markdown": "5 m/s", "is_correct": False},
                {"option_key": "B", "content_markdown": "10 m/s", "is_correct": True},
                {"option_key": "C", "content_markdown": "15 m/s", "is_correct": False},
                {"option_key": "D", "content_markdown": "20 m/s", "is_correct": False},
            ]
            mcq_multi_opts_ac = [
                {"option_key": "A", "content_markdown": "Displacement", "is_correct": True},
                {"option_key": "B", "content_markdown": "Distance", "is_correct": False},
                {"option_key": "C", "content_markdown": "Velocity", "is_correct": True},
                {"option_key": "D", "content_markdown": "Speed", "is_correct": False},
            ]

            q_mcq1, qv_mcq1 = await _create_and_publish_q(
                qtype="mcq_single",
                difficulty="easy",
                stem="Q1: Final velocity after 2s from rest at $5\\text{ m/s}^2$?",
                correct={"correct_key": "B"},
                options=mcq_opts_b,
            )
            q_mcq2, qv_mcq2 = await _create_and_publish_q(
                qtype="mcq_single",
                difficulty="medium",
                stem="Q2: Speed of object at 2s starting from rest with a=5?",
                correct={"correct_key": "B"},
                options=mcq_opts_b,
            )
            q_num1, qv_num1 = await _create_and_publish_q(
                qtype="numerical",
                difficulty="medium",
                stem="Q3: Compute distance covered in 2s with u=0, a=4 m/s^2 (m).",
                correct={"expected_value": 8.0, "tolerance_abs": 0.05},
                options=[],
            )
            q_num2, qv_num2 = await _create_and_publish_q(
                qtype="numerical",
                difficulty="hard",
                stem="Q4: Compute average acceleration when dv=18 m/s over dt=3s.",
                correct={"expected_value": 6.0, "tolerance_abs": 0.05},
                options=[],
            )
            q_multi, qv_multi = await _create_and_publish_q(
                qtype="mcq_multiple",
                difficulty="hard",
                stem="Q5: Which of the following quantities are vectors?",
                correct={"correct_keys": ["A", "C"]},
                options=mcq_multi_opts_ac,
            )

            # 3. Configurable Versioned Exam Patterns & RBAC
            r_pat_list = await client.get("/api/v1/assessments/exam-patterns", headers=stu_a_h)
            assert r_pat_list.status_code == 200
            patterns = r_pat_list.json()
            assert len(patterns) >= 4
            labels = {p["version_label"] for p in patterns}
            assert {"cbse-2026-v1", "jee-main-2026-v1", "jee-adv-2026-v1", "neet-2026-v1"}.issubset(
                labels
            )
            jee_main_pat = next(p for p in patterns if p["version_label"] == "jee-main-2026-v1")

            # Student MUST be forbidden (403) from creating exam patterns or test templates
            r_stu_pat = await client.post(
                "/api/v1/assessments/exam-patterns",
                headers=stu_a_h,
                json={
                    "exam_track_id": jee_main_pat["exam_track_id"],
                    "version_label": "hack-v1",
                    "effective_year": 2026,
                    "rules": {"duration_seconds": 600, "grace_seconds": 10, "sections": []},
                },
            )
            assert r_stu_pat.status_code == 403

            # Content admin creates custom configurable versioned pattern
            r_new_pat = await client.post(
                "/api/v1/assessments/exam-patterns",
                headers=ca_h,
                json={
                    "exam_track_id": jee_main_pat["exam_track_id"],
                    "version_label": "jee-main-2026-custom-v2",
                    "effective_year": 2026,
                    "rules": {
                        "duration_seconds": 900,
                        "grace_seconds": 15,
                        "shuffle_questions": False,
                        "sections": [
                            {
                                "code": "SEC-A",
                                "name": "Physics MCQ",
                                "question_count": 2,
                                "scoring": {
                                    "mode": "standard",
                                    "correct_marks": 4.0,
                                    "wrong_marks": -1.0,
                                    "unanswered_marks": 0.0,
                                },
                            },
                            {
                                "code": "SEC-B",
                                "name": "Numerical Choice",
                                "question_count": 2,
                                "attempt_limit": 1,
                                "scoring": {
                                    "mode": "standard",
                                    "correct_marks": 4.0,
                                    "wrong_marks": 0.0,
                                    "unanswered_marks": 0.0,
                                },
                            },
                        ],
                    },
                },
            )
            assert r_new_pat.status_code == 201
            custom_pat_id = r_new_pat.json()["id"]

            # 4. Quiz generation with distributions, answer redaction & /result lock
            r_quiz = await client.post(
                "/api/v1/quizzes/generate",
                headers=stu_a_h,
                json={
                    "quiz_type": "chapter",
                    "title": "Kinematics Timed Sprint",
                    "chapter_id": chap["id"],
                    "question_count": 3,
                    "duration_seconds": 300,
                    "grace_seconds": 10,
                    "shuffle_questions": True,
                    "difficulty_distribution": {"easy": 1, "medium": 1, "hard": 1},
                    "question_type_distribution": {"mcq_single": 1, "numerical": 1},
                    "scoring_rule": {
                        "mode": "standard",
                        "correct_marks": 4.0,
                        "wrong_marks": -1.0,
                        "unanswered_marks": 0.0,
                    },
                },
            )
            assert r_quiz.status_code == 201, r_quiz.text
            quiz_id = r_quiz.json()["id"]
            assert r_quiz.json()["question_count"] == 3

            r_q_start = await client.post(f"/api/v1/quizzes/{quiz_id}/start", headers=stu_a_h)
            assert r_q_start.status_code == 201
            q_attempt_id = r_q_start.json()["attempt_id"]
            assert r_q_start.json()["remaining_seconds"] is not None
            # Options MUST NOT expose is_correct or correct_answer during active attempt
            for q_item in r_q_start.json()["questions"]:
                assert "correct_answer_jsonb" not in q_item
                for opt in q_item["options"]:
                    assert set(opt.keys()) == {"option_key", "content_markdown"}

            # Viewing result BEFORE submission is blocked (403)
            r_early_res = await client.get(
                f"/api/v1/assessments/attempts/{q_attempt_id}/result",
                headers=stu_a_h,
            )
            assert r_early_res.status_code == 403

            # Cross-student isolation: Student B cannot inspect or submit Student A's attempt
            assert (
                await client.get(
                    f"/api/v1/assessments/attempts/{q_attempt_id}/state",
                    headers=stu_b_h,
                )
            ).status_code == 404
            assert (
                await client.post(
                    f"/api/v1/assessments/attempts/{q_attempt_id}/submit",
                    headers=stu_b_h,
                    json={"answers": []},
                )
            ).status_code == 404

            # 5. Server-side timer expiry test on Quiz attempt:
            # Autosave one correct answer BEFORE expiry, then backdate grace_until
            first_q = r_q_start.json()["questions"][0]
            if first_q["question_type"] == "mcq_single":
                ans_payload = {"selected_key": "B"}
            elif first_q["question_type"] == "mcq_multiple":
                ans_payload = {"selected_keys": ["A", "C"]}
            else:
                expected_val = 8.0 if first_q["question_version_id"] == qv_num1 else 6.0
                ans_payload = {"numeric_value": expected_val}

            r_save_q = await client.put(
                f"/api/v1/assessments/attempts/{q_attempt_id}/answers",
                headers=stu_a_h,
                json={
                    "answers": [
                        {
                            "question_version_id": first_q["question_version_id"],
                            "response_jsonb": ans_payload,
                            "is_visited": True,
                            "is_marked_for_review": True,
                            "time_spent_seconds": 18,
                        }
                    ]
                },
            )
            assert r_save_q.status_code == 200

            # Force attempt past expires_at & grace_until in PG
            async with db.session_factory() as session:
                past = datetime.now(UTC) - timedelta(minutes=10)
                await session.execute(
                    update(AssessmentAttempt)
                    .where(AssessmentAttempt.id == UUID(q_attempt_id))
                    .values(expires_at=past - timedelta(seconds=20), grace_until=past)
                )
                await session.commit()

            # Late autosave triggers auto-submission and returns 422 ASSESSMENT_TIME_EXPIRED
            r_late_save = await client.put(
                f"/api/v1/assessments/attempts/{q_attempt_id}/answers",
                headers=stu_a_h,
                json={
                    "answers": [
                        {
                            "question_version_id": first_q["question_version_id"],
                            "response_jsonb": ans_payload,
                            "is_visited": True,
                        }
                    ]
                },
            )
            assert r_late_save.status_code == 422
            assert r_late_save.json()["error"]["code"] == "ASSESSMENT_TIME_EXPIRED"

            # Calling GET /result shows status="auto_submitted" preserving pre-expiry answer
            r_auto_res = await client.get(
                f"/api/v1/assessments/attempts/{q_attempt_id}/result",
                headers=stu_a_h,
            )
            assert r_auto_res.status_code == 200
            assert r_auto_res.json()["status"] == "auto_submitted"
            assert r_auto_res.json()["raw_score"] == 4.0

            # Also verify Student B calling POST /submit directly while expired & in_progress
            # receives 422 ASSESSMENT_TIME_EXPIRED while auto_submitting pre-expiry state
            r_qb_start = await client.post(f"/api/v1/quizzes/{quiz_id}/start", headers=stu_b_h)
            assert r_qb_start.status_code == 201
            qb_attempt_id = r_qb_start.json()["attempt_id"]
            async with db.session_factory() as session:
                past = datetime.now(UTC) - timedelta(minutes=10)
                await session.execute(
                    update(AssessmentAttempt)
                    .where(AssessmentAttempt.id == UUID(qb_attempt_id))
                    .values(expires_at=past - timedelta(seconds=20), grace_until=past)
                )
                await session.commit()
            r_late_direct_sub = await client.post(
                f"/api/v1/assessments/attempts/{qb_attempt_id}/submit",
                headers=stu_b_h,
                json={"answers": []},
            )
            assert r_late_direct_sub.status_code == 422
            assert r_late_direct_sub.json()["error"]["code"] == "ASSESSMENT_TIME_EXPIRED"

            # 6. Multi-section Test Template:
            # Sec A (+4/-1), Sec B (attempt_limit=1), Sec C (partial_subset)
            r_test = await client.post(
                "/api/v1/assessments/tests",
                headers=teacher_h,
                json={
                    "title": "Kinematics Multi-Rule Mock",
                    "description": "Configurable multi-section mock",
                    "test_category": "jee_main",
                    "exam_pattern_id": custom_pat_id,
                    "duration_seconds": 1200,
                    "grace_seconds": 20,
                    "max_attempts": 1,
                    "sections": [
                        {
                            "name": "Section A: Single Choice",
                            "question_count": 2,
                            "explicit_question_ids": [q_mcq1, q_mcq2],
                            "scoring_rule": {
                                "mode": "standard",
                                "correct_marks": 4.0,
                                "wrong_marks": -1.0,
                                "unanswered_marks": 0.0,
                            },
                        },
                        {
                            "name": "Section B: Numerical (Best/First 1)",
                            "question_count": 2,
                            "attempt_limit": 1,
                            "explicit_question_ids": [q_num1, q_num2],
                            "scoring_rule": {
                                "mode": "standard",
                                "correct_marks": 4.0,
                                "wrong_marks": 0.0,
                                "unanswered_marks": 0.0,
                            },
                        },
                        {
                            "name": "Section C: Partial Credit Multi",
                            "question_count": 1,
                            "explicit_question_ids": [q_multi],
                            "scoring_rule": {
                                "mode": "partial_subset",
                                "correct_marks": 4.0,
                                "wrong_marks": -2.0,
                                "unanswered_marks": 0.0,
                                "partial_credit_per_correct_option": 1.0,
                            },
                        },
                    ],
                },
            )
            assert r_test.status_code == 201, r_test.text
            test_id = r_test.json()["id"]
            assert r_test.json()["status"] == "DRAFT"

            # Publish test (only draft -> published)
            r_pub_test = await client.post(
                f"/api/v1/assessments/tests/{test_id}/publish", headers=teacher_h
            )
            assert r_pub_test.status_code == 200
            assert r_pub_test.json()["status"] == "PUBLISHED"

            r_t_start = await client.post(
                f"/api/v1/assessments/tests/{test_id}/attempts", headers=stu_a_h
            )
            assert r_t_start.status_code == 201
            t_attempt_id = r_t_start.json()["attempt_id"]
            assert len(r_t_start.json()["questions"]) == 5

            # Max attempts = 1 enforced
            r_retake = await client.post(
                f"/api/v1/assessments/tests/{test_id}/attempts", headers=stu_a_h
            )
            assert r_retake.status_code == 403
            assert r_retake.json()["error"]["code"] == "MAX_RETAKES_REACHED"

            # Autosave answers with mark-for-review, then verify reload recovery via GET /state
            # Sec A: qv_mcq1 CORRECT (+4), qv_mcq2 WRONG (-1) => +3
            # Sec B (attempt_limit=1): both qv_num1 (+4) & qv_num2 -> 2nd capped => +4
            # Sec C (partial_subset): ["A"] (1 of ["A","C"], 1 pt each) => +1
            # Expected Total = 4 - 1 + 4 + 1 = 8.0!
            r_autosave = await client.put(
                f"/api/v1/assessments/attempts/{t_attempt_id}/answers",
                headers=stu_a_h,
                json={
                    "answers": [
                        {
                            "question_version_id": qv_mcq1,
                            "response_jsonb": {"selected_key": "B"},
                            "is_visited": True,
                            "is_marked_for_review": False,
                            "time_spent_seconds": 25,
                        },
                        {
                            "question_version_id": qv_mcq2,
                            "response_jsonb": {"selected_key": "A"},
                            "is_visited": True,
                            "is_marked_for_review": True,
                            "time_spent_seconds": 30,
                        },
                        {
                            "question_version_id": qv_num1,
                            "response_jsonb": {"numeric_value": 8.0},
                            "is_visited": True,
                            "is_marked_for_review": False,
                            "time_spent_seconds": 40,
                        },
                        {
                            "question_version_id": qv_num2,
                            "response_jsonb": {"numeric_value": 6.0},
                            "is_visited": True,
                            "is_marked_for_review": False,
                            "time_spent_seconds": 15,
                        },
                        {
                            "question_version_id": qv_multi,
                            "response_jsonb": {"selected_keys": ["A"]},
                            "is_visited": True,
                            "is_marked_for_review": True,
                            "time_spent_seconds": 22,
                        },
                    ]
                },
            )
            assert r_autosave.status_code == 200
            assert r_autosave.json()["saved_count"] == 5

            # Reload recovery check
            r_recover = await client.get(
                f"/api/v1/assessments/attempts/{t_attempt_id}/state", headers=stu_a_h
            )
            assert r_recover.status_code == 200
            rec_map = {q["question_version_id"]: q for q in r_recover.json()["questions"]}
            assert rec_map[qv_mcq2]["is_marked_for_review"] is True
            assert rec_map[qv_mcq1]["response_jsonb"] == {"selected_key": "B"}
            assert rec_map[qv_num1]["time_spent_seconds"] == 40

            # 7. Concurrent Duplicate Submissions via TWO separate HTTP clients + DB sessions
            async with (
                AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c1,
                AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c2,
            ):
                r_sub_1, r_sub_2 = await asyncio.gather(
                    c1.post(
                        f"/api/v1/assessments/attempts/{t_attempt_id}/submit",
                        headers={**stu_a_h, "Idempotency-Key": "submit-idem-1"},
                        json={"answers": []},
                    ),
                    c2.post(
                        f"/api/v1/assessments/attempts/{t_attempt_id}/submit",
                        headers={**stu_a_h, "Idempotency-Key": "submit-idem-1"},
                        json={"answers": []},
                    ),
                )

            assert r_sub_1.status_code == 200, r_sub_1.text
            assert r_sub_2.status_code == 200, r_sub_2.text
            assert r_sub_1.json()["status"] == "submitted"
            assert r_sub_2.json()["status"] == "submitted"
            assert r_sub_1.json()["raw_score"] == 8.0
            assert r_sub_2.json()["raw_score"] == 8.0
            assert r_sub_1.json()["correct_count"] == 2
            # qv_mcq2 (-1 wrong) + qv_multi (+1 partial, not full is_correct) => 2 non-full-credit
            assert r_sub_1.json()["wrong_count"] == 2

            # Verify outbox_events contains ONLY 1 submitted event for this attempt
            async with db.session_factory() as session:
                ev_count = await session.scalar(
                    select(func.count(OutboxEvent.id)).where(
                        OutboxEvent.aggregate_id == str(t_attempt_id),
                        OutboxEvent.topic == "assessment.attempt_submitted",
                    )
                )
                assert ev_count == 1

                # Project outbox once AND replay immediately (processed_event_ids)
                n1 = await process_outbox_learning_events(session, limit=100)
                n2 = await process_outbox_learning_events(session, limit=100)
                assert n1 >= 2
                assert n2 == 0

            # 8. Attempt History & Analytics Endpoints + RBAC
            r_hist = await client.get("/api/v1/assessments/attempts", headers=stu_a_h)
            assert r_hist.status_code == 200
            assert len(r_hist.json()) == 2

            r_ana = await client.get("/api/v1/analytics/student/overview", headers=stu_a_h)
            assert r_ana.status_code == 200
            ana = r_ana.json()
            assert ana["assessments_completed"] == 2
            assert ana["total_learning_events"] >= 2
            assert len(ana["recent_events"]) >= 2

            # Student MUST get 403 on cohort analytics; Teacher gets 200
            assert (
                await client.get("/api/v1/analytics/cohort", headers=stu_a_h)
            ).status_code == 403
            r_cohort = await client.get("/api/v1/analytics/cohort", headers=teacher_h)
            assert r_cohort.status_code == 200
            assert r_cohort.json()["total_submitted_attempts"] >= 2
    finally:
        await db.dispose()
        get_settings.cache_clear()
