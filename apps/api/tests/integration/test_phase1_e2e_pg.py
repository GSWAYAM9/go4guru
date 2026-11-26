"""End-to-end PG18 suite covering Phase 1 APIs, RBAC, Rights, Excel, and Practice."""

from __future__ import annotations

import io
import os
import shutil
import socket
import subprocess
import tempfile
import uuid
from pathlib import Path

import openpyxl
import pyotp
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from src.core.config import Settings, get_settings
from src.core.database import DatabaseManager
from src.core.outbox import OutboxEvent
from src.core.security import hash_password
from src.main import create_app
from src.modules.identity.models import Role, User, UserProfile, UserRole

from tests.conftest import StubCheck

API_ROOT = Path(__file__).resolve().parents[2]
PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def pg18_database_url() -> str:
    """Provide a real PostgreSQL 18 database (CI URL or isolated ephemeral local cluster)."""
    explicit = os.getenv("GO4GURU_TEST_DATABASE_URL")
    if explicit:
        return explicit

    initdb_exe = PG_BIN / "initdb.exe"
    pg_ctl_exe = PG_BIN / "pg_ctl.exe"
    if not initdb_exe.is_file() or not pg_ctl_exe.is_file():
        pytest.skip("PostgreSQL 18 binaries not found and GO4GURU_TEST_DATABASE_URL not set.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="go4guru_pg18_"))
    data_dir = tmp_dir / "data"
    log_file = tmp_dir / "postgres.log"
    port = _find_free_port()

    subprocess.run(  # noqa: S603
        [
            str(initdb_exe),
            "-D",
            str(data_dir),
            "-U",
            "postgres",
            "-A",
            "trust",
            "--encoding=UTF8",
            "--no-locale",
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(  # noqa: S603
        [
            str(pg_ctl_exe),
            "-D",
            str(data_dir),
            "-l",
            str(log_file),
            "-o",
            f"-p {port} -h 127.0.0.1",
            "start",
            "-w",
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    url = f"postgresql+asyncpg://postgres@127.0.0.1:{port}/postgres"
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(API_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
        cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(cfg, "head")
        yield url
    finally:
        get_settings.cache_clear()
        subprocess.run(  # noqa: S603
            [str(pg_ctl_exe), "-D", str(data_dir), "stop", "-m", "immediate"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)


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


def _make_test_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Custom_STEM_Bank"
    ws.append(
        [
            "Question_Text",
            "Opt_A",
            "Opt_B",
            "Opt_C",
            "Opt_D",
            "Answer_Key",
            "Difficulty",
            "Explanation",
            "Hint1",
        ]
    )
    ws.append(
        [
            (
                "For an ideal resistor obeying Ohm's Law, what is $V$ "
                "when $I=2\\text{ A}$ and $R=5\\,\\Omega$?"
            ),
            "2.5 V",
            "10 V",
            "7 V",
            "0.4 V",
            "B",
            "easy",
            "By Ohm's law, $V = I \\times R = 2 \\times 5 = 10\\text{ V}$.",
            "Recall the linear relation between voltage, current, and resistance.",
        ]
    )
    # Duplicate of row 1
    ws.append(
        [
            "For an ideal resistor obeying Ohm's Law, what is V when I=2 text A and R=5 Omega",
            "2.5 V",
            "10 V",
            "7 V",
            "0.4 V",
            "B",
            "easy",
            "Dup explanation",
            "",
        ]
    )
    # Invalid row (answer key 'Z' doesn't exist)
    ws.append(
        [
            "Bad option key sample question?",
            "1",
            "2",
            "",
            "",
            "Z",
            "medium",
            "",
            "",
        ]
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def test_full_phase1_core_flows_against_real_pg18(
    pg18_database_url: str, tmp_path: Path
) -> None:
    """Verify full Phase 1 backend flows end-to-end against real PG18."""
    settings = Settings(
        app_env="test",
        database_url=pg18_database_url,
        jwt_secret_key="phase1-integration-secret-key-at-least-32-chars",
        storage_local_dir=str(tmp_path / "private_storage"),
    )
    app = create_app(settings_override=settings)
    db_mgr = DatabaseManager(settings=settings)
    app.state.db = db_mgr
    app.state.redis = StubCheck(healthy=True)

    try:
        # Provision privileged content_admin + academic_reviewer accounts
        await _promote_user_role(db_mgr, "cadmin@example.com", "content_admin")
        await _promote_user_role(db_mgr, "reviewer@example.com", "academic_reviewer")
        await _promote_user_role(db_mgr, "padmin@example.com", "platform_admin")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Unauthenticated caller -> 401
            r_unauth = await client.get("/api/v1/questions")
            assert r_unauth.status_code == 401

            # 2. Student A & Student B register (cannot pass privileged role in public signup)
            r_stu_a = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "student.a@example.com",
                    "password": "StudentPass123",
                    "display_name": "Student A",
                    "date_of_birth_year": 2010,
                    "role": "student",
                },
            )
            assert r_stu_a.status_code == 201, r_stu_a.text
            assert r_stu_a.json()["user"]["is_minor"] is True
            stu_a_token = r_stu_a.json()["access_token"]
            stu_a_headers = {"Authorization": f"Bearer {stu_a_token}"}

            r_stu_b = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "student.b@example.com",
                    "password": "StudentPass123",
                    "display_name": "Student B",
                    "date_of_birth_year": 2009,
                    "role": "student",
                },
            )
            assert r_stu_b.status_code == 201
            stu_b_headers = {"Authorization": f"Bearer {r_stu_b.json()['access_token']}"}

            # 3. Refresh token rotation & reuse detection (clear Student B cookie first)
            client.cookies.clear()
            old_cookie = r_stu_a.cookies.get(settings.refresh_cookie_name)
            assert old_cookie
            r_ref1 = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": old_cookie},
            )
            assert r_ref1.status_code == 200
            # Reusing the ALREADY rotated old_cookie triggers 401 REFRESH_TOKEN_REUSED
            client.cookies.clear()
            r_reuse = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": old_cookie},
            )
            assert r_reuse.status_code == 401
            assert r_reuse.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

            # Fresh student login after family revocation
            r_stu_login = await client.post(
                "/api/v1/auth/login",
                json={"email": "student.a@example.com", "password": "StudentPass123"},
            )
            assert r_stu_login.status_code == 200
            stu_a_headers = {"Authorization": f"Bearer {r_stu_login.json()['access_token']}"}

            # 4. Student blocked from privileged admin/curriculum/import endpoints (403)
            assert (
                await client.post(
                    "/api/v1/curriculum/boards",
                    headers=stu_a_headers,
                    json={"code": "CBSE", "name": "CBSE Board"},
                )
            ).status_code == 403
            assert (
                await client.get("/api/v1/admin/audit-logs", headers=stu_a_headers)
            ).status_code == 403

            # 5. Privileged Content Admin MFA enforcement
            r_ca_login = await client.post(
                "/api/v1/auth/login",
                json={"email": "cadmin@example.com", "password": "AdminPass!123"},
            )
            assert r_ca_login.status_code == 200
            assert r_ca_login.json()["mfa_required"] is True
            ca_unverified_headers = {"Authorization": f"Bearer {r_ca_login.json()['access_token']}"}
            r_mfa_blocked = await client.post(
                "/api/v1/curriculum/boards",
                headers=ca_unverified_headers,
                json={"code": "CBSE", "name": "CBSE"},
            )
            assert r_mfa_blocked.status_code == 403
            assert r_mfa_blocked.json()["error"]["code"] == "MFA_REQUIRED"

            r_setup = await client.post("/api/v1/auth/mfa/setup", headers=ca_unverified_headers)
            assert r_setup.status_code == 200
            totp_code = pyotp.TOTP(r_setup.json()["secret"]).now()
            r_verify = await client.post(
                "/api/v1/auth/mfa/verify",
                headers=ca_unverified_headers,
                json={"code": totp_code},
            )
            assert r_verify.status_code == 200
            assert r_verify.json()["mfa_verified"] is True
            ca_headers = {"Authorization": f"Bearer {r_verify.json()['access_token']}"}

            # Reviewer & Platform Admin MFA verify helper
            async def _auth_privileged(email: str) -> dict[str, str]:
                rl = await client.post(
                    "/api/v1/auth/login", json={"email": email, "password": "AdminPass!123"}
                )
                uh = {"Authorization": f"Bearer {rl.json()['access_token']}"}
                rs = await client.post("/api/v1/auth/mfa/setup", headers=uh)
                rv = await client.post(
                    "/api/v1/auth/mfa/verify",
                    headers=uh,
                    json={"code": pyotp.TOTP(rs.json()["secret"]).now()},
                )
                return {"Authorization": f"Bearer {rv.json()['access_token']}"}

            rev_headers = await _auth_privileged("reviewer@example.com")
            padmin_headers = await _auth_privileged("padmin@example.com")

            # 6. Content Rights & Quarantine Gate (F-007)
            r_q_src = await client.post(
                "/api/v1/content-rights/sources",
                headers=ca_headers,
                json={
                    "name": "External Quarantined Sample",
                    "owner_name": "Third Party",
                    "source_category": "quarantined_third_party",
                },
            )
            assert r_q_src.status_code == 201
            q_src_id = r_q_src.json()["id"]
            r_q_lic = await client.post(
                "/api/v1/content-rights/licenses",
                headers=ca_headers,
                json={"source_id": q_src_id, "license_name": "None"},
            )
            assert r_q_lic.json()["legal_review_status"] == "quarantined"
            r_q_approve = await client.post(
                f"/api/v1/content-rights/licenses/{r_q_lic.json()['id']}/review",
                headers=ca_headers,
                json={"legal_review_status": "approved"},
            )
            assert r_q_approve.status_code == 422

            # Valid Original Platform source + approved license
            r_src = await client.post(
                "/api/v1/content-rights/sources",
                headers=ca_headers,
                json={
                    "name": "Go4Guru Original Authors",
                    "owner_name": "Go4Guru",
                    "source_category": "original_platform",
                },
            )
            src_id = r_src.json()["id"]
            r_lic = await client.post(
                "/api/v1/content-rights/licenses",
                headers=ca_headers,
                json={
                    "source_id": src_id,
                    "license_name": "Go4Guru Internal Copyright",
                    "commercial_use_allowed": True,
                    "hosting_allowed": True,
                    "embedding_allowed": True,
                },
            )
            lic_id = r_lic.json()["id"]
            assert (
                await client.post(
                    f"/api/v1/content-rights/licenses/{lic_id}/review",
                    headers=ca_headers,
                    json={"legal_review_status": "approved"},
                )
            ).status_code == 200

            # 7. Versioned Curriculum & DAG cycle check (F-005)
            board = (
                await client.post(
                    "/api/v1/curriculum/boards",
                    headers=ca_headers,
                    json={"code": "CBSE", "name": "Central Board of Secondary Education"},
                )
            ).json()
            sess = (
                await client.post(
                    "/api/v1/curriculum/sessions",
                    headers=ca_headers,
                    json={
                        "code": "2026-27",
                        "starts_on": "2026-04-01",
                        "ends_on": "2027-03-31",
                    },
                )
            ).json()
            ver = (
                await client.post(
                    "/api/v1/curriculum/versions",
                    headers=ca_headers,
                    json={
                        "board_id": board["id"],
                        "academic_session_id": sess["id"],
                        "version_tag": "2026-27-v1",
                    },
                )
            ).json()
            grades = (await client.get("/api/v1/curriculum/grades")).json()
            grade_10 = next(g for g in grades if g["number"] == 10)
            subj = (
                await client.post(
                    "/api/v1/curriculum/subjects",
                    headers=ca_headers,
                    json={"code": "PHY", "name": "Physics", "discipline": "physics"},
                )
            ).json()
            book = (
                await client.post(
                    "/api/v1/curriculum/books",
                    headers=ca_headers,
                    json={
                        "curriculum_version_id": ver["id"],
                        "grade_id": grade_10["id"],
                        "subject_id": subj["id"],
                        "title": "Class 10 Science Foundations",
                        "publisher": "Go4Guru Original",
                    },
                )
            ).json()
            chap = (
                await client.post(
                    "/api/v1/curriculum/chapters",
                    headers=ca_headers,
                    json={
                        "book_id": book["id"],
                        "sequence_no": 1,
                        "code": "CH-ELEC",
                        "title": "Electricity",
                    },
                )
            ).json()
            sec = (
                await client.post(
                    "/api/v1/curriculum/sections",
                    headers=ca_headers,
                    json={
                        "chapter_id": chap["id"],
                        "sequence_no": 1,
                        "title": "1.1 Electric Current",
                    },
                )
            ).json()
            topic = (
                await client.post(
                    "/api/v1/curriculum/topics",
                    headers=ca_headers,
                    json={
                        "chapter_id": chap["id"],
                        "section_id": sec["id"],
                        "sequence_no": 1,
                        "title": "Ohm's Law",
                    },
                )
            ).json()
            c1 = (
                await client.post(
                    "/api/v1/curriculum/concepts",
                    headers=ca_headers,
                    json={
                        "topic_id": topic["id"],
                        "code": "PHY-10-CHARGE",
                        "title": "Electric Charge",
                    },
                )
            ).json()
            c2 = (
                await client.post(
                    "/api/v1/curriculum/concepts",
                    headers=ca_headers,
                    json={"topic_id": topic["id"], "code": "PHY-10-OHM", "title": "Ohm's Law"},
                )
            ).json()
            await client.post(
                "/api/v1/curriculum/learning-objectives",
                headers=ca_headers,
                json={
                    "concept_id": c2["id"],
                    "bloom_level": "apply",
                    "statement": "Calculate V=IR for simple resistive circuits.",
                },
            )
            assert (
                await client.post(
                    "/api/v1/curriculum/prerequisites",
                    headers=ca_headers,
                    json={"concept_id": c2["id"], "prerequisite_concept_id": c1["id"]},
                )
            ).status_code == 201
            # Reverse prerequisite creates a cycle -> 422
            r_cycle = await client.post(
                "/api/v1/curriculum/prerequisites",
                headers=ca_headers,
                json={"concept_id": c1["id"], "prerequisite_concept_id": c2["id"]},
            )
            assert r_cycle.status_code == 422
            assert r_cycle.json()["error"]["code"] == "CYCLIC_PREREQUISITE"

            # Draft curriculum is NOT visible to student until published
            r_draft_tree = await client.get("/api/v1/curriculum/tree", headers=stu_a_headers)
            assert r_draft_tree.json() is None

            assert (
                await client.post(
                    f"/api/v1/curriculum/versions/{ver['id']}/publish", headers=ca_headers
                )
            ).status_code == 200
            r_pub_tree = await client.get("/api/v1/curriculum/tree", headers=stu_a_headers)
            assert r_pub_tree.json()["books"][0]["chapters"][0]["title"] == "Electricity"

            # Student onboarding profile persistence
            r_sp = await client.put(
                "/api/v1/users/me/student-profile",
                headers=stu_a_headers,
                json={
                    "board_id": board["id"],
                    "academic_session_id": sess["id"],
                    "grade_id": grade_10["id"],
                    "curriculum_version_id": ver["id"],
                    "primary_exam_target": "cbse_board",
                    "daily_study_minutes_target": 90,
                },
            )
            assert r_sp.status_code == 200
            assert r_sp.json()["onboarding_completed_at"] is not None

            # 8. Canonical Question Bank, AI-vs-PYQ rejection, Versioning & Redaction (F-008)
            r_ai_q = await client.post(
                "/api/v1/questions",
                headers=ca_headers,
                json={
                    "question_type": "numerical",
                    "curriculum_version_id": ver["id"],
                    "grade_id": grade_10["id"],
                    "subject_id": subj["id"],
                    "chapter_id": chap["id"],
                    "topic_id": topic["id"],
                    "concept_id": c2["id"],
                    "stem_markdown": "If V=12V and R=3 ohm, compute current in A.",
                    "correct_answer_jsonb": {"expected_value": 4.0, "tolerance_abs": 0.01},
                    "ai_generated": True,
                    "provenance": {
                        "source_id": src_id,
                        "license_id": lic_id,
                        "source_type": "ai_generated",
                    },
                },
            )
            assert r_ai_q.status_code == 201
            # AI question MUST NOT be allowed to become PYQ
            r_ai_pyq = await client.post(
                f"/api/v1/questions/{r_ai_q.json()['id']}/verify-pyq",
                headers=rev_headers,
                json={"exam_name": "CBSE Class 10", "exam_year": 2024},
            )
            assert r_ai_pyq.status_code == 422
            assert r_ai_pyq.json()["error"]["code"] == "AI_QUESTION_CANNOT_BE_PYQ"

            # Publish AI question cleanly via reviewer (only after review!)
            r_pub_q = await client.post(
                f"/api/v1/questions/{r_ai_q.json()['id']}/review",
                headers=rev_headers,
                json={"decision": "approved", "publish": True},
            )
            assert r_pub_q.status_code == 200
            assert r_pub_q.json()["status"] == "PUBLISHED"

            # Student search/get MUST redact correct_answer_jsonb and solutions!
            r_stu_qs = await client.get(
                f"/api/v1/questions?q=ohm&chapter_id={chap['id']}", headers=stu_a_headers
            )
            assert r_stu_qs.status_code == 200
            assert r_stu_qs.json()["total"] == 1
            assert r_stu_qs.json()["items"][0]["correct_answer_jsonb"] is None
            assert r_stu_qs.json()["items"][0]["solutions"] is None

            # Create immutable v2 of question while preserving v1
            r_v2 = await client.post(
                f"/api/v1/questions/{r_ai_q.json()['id']}/versions",
                headers=ca_headers,
                json={
                    "curriculum_version_id": ver["id"],
                    "grade_id": grade_10["id"],
                    "subject_id": subj["id"],
                    "chapter_id": chap["id"],
                    "topic_id": topic["id"],
                    "concept_id": c2["id"],
                    "stem_markdown": "If V = 12 V and R = 3 Ohm, calculate current (A).",
                    "correct_answer_jsonb": {"expected_value": 4.0, "tolerance_abs": 0.01},
                },
            )
            assert r_v2.status_code == 201
            assert r_v2.json()["version_no"] == 2
            await client.post(
                f"/api/v1/questions/{r_ai_q.json()['id']}/review",
                headers=rev_headers,
                json={"decision": "approved", "publish": True},
            )

            # 9. Excel (.xlsx) 14-stage Upload -> Validate -> Commit -> Rollback (F-009)
            xlsx_bytes = _make_test_xlsx()
            r_up = await client.post(
                "/api/v1/imports/upload",
                headers=ca_headers,
                files={
                    "file": (
                        "custom_physics.xlsx",
                        xlsx_bytes,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert r_up.status_code == 201
            batch_id = r_up.json()["id"]
            assert r_up.json()["detected_sheets"][0]["sheet_name"] == "Custom_STEM_Bank"

            r_map = await client.post(
                f"/api/v1/imports/{batch_id}/mapping",
                headers=ca_headers,
                json={
                    "selected_sheet": "Custom_STEM_Bank",
                    "column_map": {
                        "stem_markdown": "Question_Text",
                        "option_a": "Opt_A",
                        "option_b": "Opt_B",
                        "option_c": "Opt_C",
                        "option_d": "Opt_D",
                        "correct_answer": "Answer_Key",
                        "difficulty": "Difficulty",
                        "explanation": "Explanation",
                        "hint_1": "Hint1",
                    },
                    "default_curriculum_version_id": ver["id"],
                    "default_grade_id": grade_10["id"],
                    "default_subject_id": subj["id"],
                    "default_chapter_id": chap["id"],
                    "default_topic_id": topic["id"],
                    "default_concept_id": c2["id"],
                    "source_id": src_id,
                    "license_id": lic_id,
                },
            )
            assert r_map.status_code == 200

            r_val = await client.post(f"/api/v1/imports/{batch_id}/validate", headers=ca_headers)
            assert r_val.status_code == 200
            assert r_val.json()["duplicate_rows"] == 1
            assert r_val.json()["error_rows"] == 1
            assert (r_val.json()["valid_rows"] + r_val.json()["warning_rows"]) == 1

            r_prev = await client.get(f"/api/v1/imports/{batch_id}/preview", headers=ca_headers)
            assert r_prev.status_code == 200
            assert len(r_prev.json()["rows"]) == 3

            r_commit = await client.post(
                f"/api/v1/imports/{batch_id}/commit",
                headers=ca_headers,
                json={"target_status": "REVIEW", "include_warnings": True},
            )
            assert r_commit.status_code == 200
            assert r_commit.json()["committed_count"] == 1

            r_rollback = await client.post(
                f"/api/v1/imports/{batch_id}/rollback", headers=ca_headers
            )
            assert r_rollback.status_code == 200
            assert r_rollback.json()["rolled_back_questions"] == 1

            r_report = await client.get(f"/api/v1/imports/{batch_id}/report", headers=ca_headers)
            assert r_report.status_code == 200
            assert "text/csv" in r_report.headers["content-type"]

            # Non-AI MCQ question with Hint Level 1 + genuine PYQ provenance verification
            r_mcq_q = await client.post(
                "/api/v1/questions",
                headers=ca_headers,
                json={
                    "question_type": "mcq_single",
                    "curriculum_version_id": ver["id"],
                    "grade_id": grade_10["id"],
                    "subject_id": subj["id"],
                    "chapter_id": chap["id"],
                    "topic_id": topic["id"],
                    "concept_id": c2["id"],
                    "stem_markdown": "SI unit of electric resistance is:",
                    "correct_answer_jsonb": {"correct_key": "B"},
                    "ai_generated": False,
                    "options": [
                        {"option_key": "A", "content_markdown": "Volt", "is_correct": False},
                        {"option_key": "B", "content_markdown": "Ohm", "is_correct": True},
                    ],
                    "solutions": [
                        {
                            "explanation_markdown": "Resistance is measured in Ohm ($\\Omega$).",
                            "steps": ["Recall R = V / I", "Unit is Ohm"],
                        }
                    ],
                    "hints": [{"hint_level": 1, "hint_markdown": "Named after Georg Simon Ohm."}],
                    "provenance": {
                        "source_id": src_id,
                        "license_id": lic_id,
                        "source_type": "original",
                    },
                },
            )
            assert r_mcq_q.status_code == 201
            assert (
                await client.post(
                    f"/api/v1/questions/{r_mcq_q.json()['id']}/verify-pyq",
                    headers=rev_headers,
                    json={"exam_name": "Sample Practice Archive", "exam_year": 2024},
                )
            ).status_code == 200
            assert (
                await client.post(
                    f"/api/v1/questions/{r_mcq_q.json()['id']}/review",
                    headers=rev_headers,
                    json={"decision": "approved", "publish": True},
                )
            ).status_code == 200

            # 10. Practice Engine, Hints, Attempts, Outbox, Notes & Dashboard (F-010, F-030)
            q_id = uuid.UUID(r_ai_q.json()["id"])
            mcq_q_id = uuid.UUID(r_mcq_q.json()["id"])
            r_ps = await client.post(
                "/api/v1/practice/sessions",
                headers=stu_a_headers,
                json={"chapter_id": chap["id"], "subject_id": subj["id"], "limit": 5},
            )
            assert r_ps.status_code == 201
            ps_id = r_ps.json()["id"]
            assert len(r_ps.json()["questions"]) == 2

            r_hint = await client.post(
                f"/api/v1/practice/sessions/{ps_id}/hints",
                headers=stu_a_headers,
                json={"question_id": str(mcq_q_id), "hint_level": 1},
            )
            assert r_hint.status_code == 200
            assert "Georg Simon Ohm" in (r_hint.json()["hint_markdown"] or "")
            assert r_hint.json()["hints_used_count"] == 1

            r_att = await client.post(
                f"/api/v1/practice/sessions/{ps_id}/attempts",
                headers=stu_a_headers,
                json={
                    "question_id": str(mcq_q_id),
                    "response_jsonb": {"selected_key": "B"},
                    "time_spent_seconds": 18,
                },
            )
            assert r_att.status_code == 200
            assert r_att.json()["is_correct"] is True
            assert r_att.json()["score_awarded"] == 4.0
            assert r_att.json()["hints_used_count"] == 1
            assert r_att.json()["correct_answer_jsonb"] == {"correct_key": "B"}
            assert "Ohm" in (r_att.json()["explanation_markdown"] or "")

            # Verify outbox_events row persisted atomically inside PostgreSQL 18
            async with db_mgr.session_factory() as check_sess:
                outbox_cnt = int(
                    await check_sess.scalar(
                        select(func.count(OutboxEvent.id)).where(
                            OutboxEvent.topic == "learning.question_attempted"
                        )
                    )
                    or 0
                )
                assert outbox_cnt == 1

            # Notes & Bookmarks with cross-student owner isolation
            r_note = await client.post(
                "/api/v1/notes",
                headers=stu_a_headers,
                json={
                    "concept_id": c2["id"],
                    "question_id": str(q_id),
                    "title": "Ohm Law Note",
                    "body_markdown": "Remember $V = IR$.",
                },
            )
            assert r_note.status_code == 201
            assert (
                await client.patch(
                    f"/api/v1/notes/{r_note.json()['id']}",
                    headers=stu_b_headers,
                    json={"title": "Hijacked"},
                )
            ).status_code == 404

            r_bm = await client.post(
                "/api/v1/bookmarks",
                headers=stu_a_headers,
                json={"question_id": str(q_id), "folder_name": "Physics Ch1"},
            )
            assert r_bm.status_code == 201

            # Student A dashboard shows real persisted stats; Student B sees genuine 0s!
            r_dash_a = await client.get("/api/v1/dashboard/student", headers=stu_a_headers)
            assert r_dash_a.status_code == 200
            assert r_dash_a.json()["onboarding_completed"] is True
            assert r_dash_a.json()["total_attempts"] == 1
            assert r_dash_a.json()["correct_attempts"] == 1
            assert r_dash_a.json()["accuracy_pct"] == 100.0
            assert r_dash_a.json()["saved_questions_count"] == 1
            assert r_dash_a.json()["notes_count"] == 1

            r_dash_b = await client.get("/api/v1/dashboard/student", headers=stu_b_headers)
            assert r_dash_b.status_code == 200
            assert r_dash_b.json()["onboarding_completed"] is False
            assert r_dash_b.json()["total_attempts"] == 0
            assert r_dash_b.json()["notes_count"] == 0

            # Audit log query accessible by platform_admin
            r_audits = await client.get("/api/v1/admin/audit-logs?limit=20", headers=padmin_headers)
            assert r_audits.status_code == 200
            assert len(r_audits.json()) >= 5
    finally:
        await db_mgr.dispose()
