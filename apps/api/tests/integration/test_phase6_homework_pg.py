"""PostgreSQL 18 integration tests for Phase 6 Homework AI (F-029)."""

from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient
from src.core.config import Settings
from src.main import create_app

from tests.conftest import StubCheck
from tests.integration.test_phase1_e2e_pg import pg18_database_url  # noqa: F401


def _sample_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return (
        "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Pages /Count 1 >>\nendobj\n"
        "2 0 obj\n<< /Type /Page /Parent 1 0 R >>\nendobj\n"
        "3 0 obj\n<< /Length 96 >>\nstream\n"
        f"BT /F1 12 Tf ({escaped}) Tj ET\n"
        "endstream\nendobj\n"
        "%%EOF\n"
    ).encode("latin-1")


async def _register_and_token(
    client: AsyncClient, *, email: str, password: str, display_name: str, role: str = "student"
) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "date_of_birth_year": 2010 if role == "student" else 1984,
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["access_token"])


async def test_phase6_homework_end_to_end_security_hints_ocr_and_retry(
    pg18_database_url: str,  # noqa: F811
    tmp_path: Path,
) -> None:
    settings = Settings(
        database_url=pg18_database_url,
        storage_local_dir=str(tmp_path / "private_storage"),
        homework_ocr_provider="auto",
    )
    app = create_app(settings_override=settings)
    transport = ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        app.state.redis = StubCheck()  # type: ignore[assignment]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            student_token = await _register_and_token(
                client,
                email="p6.student@example.com",
                password="StudentPass!123",
                display_name="Phase 6 Student",
                role="student",
            )
            other_student_token = await _register_and_token(
                client,
                email="p6.other@example.com",
                password="StudentPass!123",
                display_name="Other Student",
                role="student",
            )
            parent_token = await _register_and_token(
                client,
                email="p6.parent@example.com",
                password="ParentPass!123",
                display_name="Phase 6 Parent",
                role="parent",
            )

            # 1. Parent role is strictly denied access to Homework AI (403)
            parent_list = await client.get(
                "/api/v1/homework/submissions",
                headers={"Authorization": f"Bearer {parent_token}"},
            )
            assert parent_list.status_code == 403

            # 2. Malicious SVG disguised as image is rejected before persistence (422)
            bad_upload = await client.post(
                "/api/v1/homework/submissions",
                headers={"Authorization": f"Bearer {student_token}"},
                data={"title": "Bad Upload", "selected_subject": "mathematics"},
                files={"files": ("bad.png", b"<svg><script>alert(1)</script></svg>", "image/png")},
            )
            assert bad_upload.status_code == 422

            # 3. Valid PDF homework submission with sign error -> evaluated with anti-spoiler guard
            pdf_bytes = _sample_pdf("Question: Solve 2x + 4 = 10\nStep 1: 2x = 14\nStep 2: x = 7")
            created_resp = await client.post(
                "/api/v1/homework/submissions",
                headers={"Authorization": f"Bearer {student_token}"},
                data={"title": "Linear Equations Q4", "selected_subject": "auto"},
                files={"files": ("linear_q4.pdf", pdf_bytes, "application/pdf")},
            )
            assert created_resp.status_code == 201, created_resp.text
            detail = created_resp.json()
            sub_id = detail["id"]
            file_id = detail["files"][0]["id"]

            assert detail["detected_subject"] == "mathematics"
            assert detail["latest_evaluation"]["overall_status"] == "needs_correction"
            # Anti-spoiler default: Level 1 hint unlocked, complete solution hidden
            assert detail["latest_evaluation"]["current_hint_level_unlocked"] == 1
            assert len(detail["latest_evaluation"]["unlocked_hints"]) == 1
            assert detail["latest_evaluation"]["solution_revealed"] is False
            assert detail["latest_evaluation"]["complete_solution_markdown"] is None

            # 4. Cross-student access is strictly forbidden (403)
            other_get = await client.get(
                f"/api/v1/homework/submissions/{sub_id}",
                headers={"Authorization": f"Bearer {other_student_token}"},
            )
            assert other_get.status_code == 403

            # 5. Private file download enforces auth & nosniff header
            file_resp = await client.get(
                f"/api/v1/homework/submissions/{sub_id}/files/{file_id}",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert file_resp.status_code == 200
            assert file_resp.headers["x-content-type-options"] == "nosniff"
            assert file_resp.content.startswith(b"%PDF-")

            # 6. Unlock Hint Level 2 without spoiling complete solution
            hint2_resp = await client.post(
                f"/api/v1/homework/submissions/{sub_id}/hints/unlock",
                headers={"Authorization": f"Bearer {student_token}"},
                json={"target_level": 2},
            )
            assert hint2_resp.status_code == 200
            assert hint2_resp.json()["current_hint_level_unlocked"] == 2
            assert hint2_resp.json()["solution_revealed"] is False
            assert hint2_resp.json()["complete_solution_markdown"] is None

            # 7. Student submits corrected retry -> Attempt #2 passes cleanly & status becomes completed
            retry_resp = await client.post(
                f"/api/v1/homework/submissions/{sub_id}/retry",
                headers={"Authorization": f"Bearer {student_token}"},
                json={
                    "revised_work_text": "Step 1: 2x = 10 - 4\nStep 2: 2x = 6\nStep 3: x = 3",
                    "student_reflection": "Subtracted 4 from both sides instead of adding.",
                },
            )
            assert retry_resp.status_code == 200, retry_resp.text
            retried = retry_resp.json()
            assert retried["retry_count"] == 1
            assert retried["status"] == "completed"
            assert retried["latest_evaluation"]["attempt_no"] == 2
            assert retried["latest_evaluation"]["overall_status"] == "correct"
            assert len(retried["evaluation_history"]) == 2

            # 8. Explicit solution reveal requires confirm_reveal=true
            reveal_reject = await client.post(
                f"/api/v1/homework/submissions/{sub_id}/solution/reveal",
                headers={"Authorization": f"Bearer {student_token}"},
                json={"confirm_reveal": False},
            )
            assert reveal_reject.status_code == 400

            reveal_ok = await client.post(
                f"/api/v1/homework/submissions/{sub_id}/solution/reveal",
                headers={"Authorization": f"Bearer {student_token}"},
                json={"confirm_reveal": True},
            )
            assert reveal_ok.status_code == 200
            assert reveal_ok.json()["solution_revealed"] is True
            assert reveal_ok.json()["complete_solution_markdown"] is not None
