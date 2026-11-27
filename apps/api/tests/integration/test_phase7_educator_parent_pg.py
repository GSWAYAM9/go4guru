"""PostgreSQL 18 integration tests for Phase 7: Teacher, Mentor & Parent Ecosystem."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from src.core.config import Settings
from src.main import create_app
from src.modules.identity.models import Role, User, UserRole

from tests.conftest import StubCheck
from tests.integration.test_phase1_e2e_pg import pg18_database_url  # noqa: F401


async def _register_with_role(
    app,
    client: AsyncClient,
    *,
    email: str,
    password: str,
    display_name: str,
    role_code: str,
) -> tuple[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "date_of_birth_year": 2010 if role_code == "student" else 1985,
            "role": "student" if role_code in ("teacher", "mentor") else role_code,
        },
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["user"]["id"]

    if role_code in ("teacher", "mentor"):
        async with app.state.db.session_factory() as db:
            role = await db.scalar(select(Role).where(Role.code == role_code))
            user = await db.scalar(select(User).where(User.email == email))
            assert role is not None and user is not None
            db.add(UserRole(user_id=user.id, role_id=role.id))
            await db.commit()
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        return str(login.json()["access_token"]), str(user_id)

    return str(reg.json()["access_token"]), str(user_id)


async def test_phase7_teacher_mentor_parent_workflows_and_authz(
    pg18_database_url: str,  # noqa: F811
) -> None:
    settings = Settings(database_url=pg18_database_url)
    app = create_app(settings_override=settings)
    transport = ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        app.state.redis = StubCheck()  # type: ignore[assignment]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            teacher_tok, _ = await _register_with_role(
                app,
                client,
                email="p7.teacher@example.com",
                password="StrongPassword!123",
                display_name="Priya Teacher",
                role_code="teacher",
            )
            mentor_tok, _ = await _register_with_role(
                app,
                client,
                email="p7.mentor@example.com",
                password="StrongPassword!123",
                display_name="Rohan Mentor",
                role_code="mentor",
            )
            parent_tok, _ = await _register_with_role(
                app,
                client,
                email="p7.parent@example.com",
                password="StrongPassword!123",
                display_name="Meera Parent",
                role_code="parent",
            )
            student_tok, student_id = await _register_with_role(
                app,
                client,
                email="p7.student@example.com",
                password="StrongPassword!123",
                display_name="Aarav Student",
                role_code="student",
            )
            _, unassigned_student_id = await _register_with_role(
                app,
                client,
                email="p7.other.student@example.com",
                password="StrongPassword!123",
                display_name="Other Student",
                role_code="student",
            )

            # --- 1. Teacher Workflow + Strict Student AuthZ ---
            cls_resp = await client.post(
                "/api/v1/teacher/classes",
                headers={"Authorization": f"Bearer {teacher_tok}"},
                json={"name": "Class 10 Math", "grade_label": "Class 10", "subject_name": "Mathematics"},
            )
            assert cls_resp.status_code == 201, cls_resp.text
            class_id = cls_resp.json()["id"]

            sec_resp = await client.post(
                f"/api/v1/teacher/classes/{class_id}/sections",
                headers={"Authorization": f"Bearer {teacher_tok}"},
                json={"name": "Section A", "code": "A", "capacity": 40},
            )
            assert sec_resp.status_code == 201
            section_id = sec_resp.json()["id"]

            enroll_resp = await client.post(
                f"/api/v1/teacher/classes/{class_id}/students",
                headers={"Authorization": f"Bearer {teacher_tok}"},
                json={"student_email": "p7.student@example.com", "section_id": section_id, "roll_no": "10A-01"},
            )
            assert enroll_resp.status_code == 201

            # Teacher MUST be denied analytics for unenrolled student
            denied_stu = await client.get(
                f"/api/v1/teacher/students/{unassigned_student_id}/analytics",
                headers={"Authorization": f"Bearer {teacher_tok}"},
            )
            assert denied_stu.status_code == 403

            # Teacher can inspect enrolled student analytics
            ok_stu = await client.get(
                f"/api/v1/teacher/students/{student_id}/analytics",
                headers={"Authorization": f"Bearer {teacher_tok}"},
            )
            assert ok_stu.status_code == 200

            asgn_resp = await client.post(
                "/api/v1/teacher/assignments",
                headers={"Authorization": f"Bearer {teacher_tok}"},
                json={
                    "class_id": class_id,
                    "title": "Quadratic Roots Quiz",
                    "assignment_type": "quiz",
                    "instructions": "Solve x^2 - 5x + 6 = 0 showing all steps.",
                    "max_marks": 20,
                },
            )
            assert asgn_resp.status_code == 201
            asgn_id = asgn_resp.json()["id"]

            sub_resp = await client.post(
                f"/api/v1/teacher/assignments/{asgn_id}/submissions",
                headers={"Authorization": f"Bearer {student_tok}"},
                json={"response_text": "Step 1: Factor (x-2)(x-3)=0. Therefore x=2 or x=3."},
            )
            assert sub_resp.status_code == 201
            sub_id = sub_resp.json()["id"]

            ai_grade = await client.post(
                f"/api/v1/teacher/submissions/{sub_id}/ai-grade",
                headers={"Authorization": f"Bearer {teacher_tok}"},
            )
            assert ai_grade.status_code == 200
            assert ai_grade.json()["ai_suggested_score"] is not None

            override_resp = await client.patch(
                f"/api/v1/teacher/submissions/{sub_id}/override",
                headers={"Authorization": f"Bearer {teacher_tok}"},
                json={
                    "teacher_score": 19.5,
                    "teacher_feedback": "Excellent factoring steps!",
                    "teacher_override_reason": "Full credit for clear method",
                    "status": "returned",
                },
            )
            assert override_resp.status_code == 200
            assert override_resp.json()["teacher_score"] == 19.5
            assert override_resp.json()["effective_score"] == 19.5

            csv_resp = await client.get(
                f"/api/v1/teacher/classes/{class_id}/report.csv",
                headers={"Authorization": f"Bearer {teacher_tok}"},
            )
            assert csv_resp.status_code == 200
            assert "p7.student@example.com" in csv_resp.text

            # --- 2. Mentor Workflow + Strict Student AuthZ ---
            denied_mentor = await client.get(
                f"/api/v1/mentor/students/{unassigned_student_id}/review",
                headers={"Authorization": f"Bearer {mentor_tok}"},
            )
            assert denied_mentor.status_code == 403

            assign_m = await client.post(
                "/api/v1/mentor/students",
                headers={"Authorization": f"Bearer {mentor_tok}"},
                json={"student_email": "p7.student@example.com", "notes": "Board prep coaching"},
            )
            assert assign_m.status_code == 201

            goal_m = await client.post(
                "/api/v1/mentor/goals",
                headers={"Authorization": f"Bearer {mentor_tok}"},
                json={"student_id": student_id, "title": "Complete 30 algebra drills"},
            )
            assert goal_m.status_code == 201

            sess_m = await client.post(
                "/api/v1/mentor/sessions",
                headers={"Authorization": f"Bearer {mentor_tok}"},
                json={
                    "student_id": student_id,
                    "scheduled_at": datetime.now(UTC).isoformat(),
                    "summary_notes": "Reviewed weak quadratic topics",
                    "recommendations": ["Practice discriminant cases daily"],
                    "status": "completed",
                },
            )
            assert sess_m.status_code == 201

            review_m = await client.get(
                f"/api/v1/mentor/students/{student_id}/review",
                headers={"Authorization": f"Bearer {mentor_tok}"},
            )
            assert review_m.status_code == 200
            assert len(review_m.json()["goals"]) == 1
            assert len(review_m.json()["sessions"]) == 1

            # --- 3. Parent Workflow + Consent Gate + Raw AI Chat Denial ---
            link_resp = await client.post(
                "/api/v1/parent/links",
                headers={"Authorization": f"Bearer {parent_tok}"},
                json={"student_email": "p7.student@example.com", "relationship_type": "parent"},
            )
            assert link_resp.status_code == 201
            link_id = link_resp.json()["id"]
            code = link_resp.json()["verification_code_preview"]
            assert code

            # Before consent verification, summary MUST be 403
            pending_summary = await client.get(
                f"/api/v1/parent/students/{student_id}/summary",
                headers={"Authorization": f"Bearer {parent_tok}"},
            )
            assert pending_summary.status_code == 403

            verify_resp = await client.post(
                f"/api/v1/parent/links/{link_id}/verify",
                headers={"Authorization": f"Bearer {parent_tok}"},
                json={"verification_code": code},
            )
            assert verify_resp.status_code == 200
            assert verify_resp.json()["consent_status"] == "verified"

            # Privacy update MUST keep allow_raw_ai_transcripts locked false
            priv_resp = await client.patch(
                f"/api/v1/parent/links/{link_id}/privacy",
                headers={"Authorization": f"Bearer {parent_tok}"},
                json={"allow_raw_ai_transcripts": True, "share_weak_topics": True},
            )
            assert priv_resp.status_code == 200
            assert priv_resp.json()["privacy_settings"]["allow_raw_ai_transcripts"] is False

            # Verified parent gets learning summary (including upcoming assignment)
            summary_resp = await client.get(
                f"/api/v1/parent/students/{student_id}/summary",
                headers={"Authorization": f"Bearer {parent_tok}"},
            )
            assert summary_resp.status_code == 200
            assert summary_resp.json()["privacy_settings"]["allow_raw_ai_transcripts"] is False
            assert len(summary_resp.json()["upcoming_assessments"]) >= 1

            # Parent MUST NEVER access raw AI tutor sessions (403)
            raw_ai_resp = await client.get(
                "/api/v1/ai/sessions",
                headers={"Authorization": f"Bearer {parent_tok}"},
            )
            assert raw_ai_resp.status_code == 403
