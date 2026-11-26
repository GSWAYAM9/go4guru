"""Full-stack Playwright E2E orchestrator: ephemeral PG18 + FastAPI + Next.js + Chromium."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

ROOT_DIR = Path(__file__).resolve().parents[3]
API_DIR = ROOT_DIR / "apps" / "api"
WEB_DIR = ROOT_DIR / "apps" / "web"
PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _find_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http(url: str, timeout_s: float = 45.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:  # noqa: S310
                if resp.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Service did not respond at {url} within {timeout_s}s.")


async def _seed_e2e_curriculum_and_question(db_url: str) -> None:
    from src.core.config import Settings
    from src.core.database import DatabaseManager
    from src.core.security import hash_password
    from src.modules.ai.models import KnowledgeChunk, KnowledgeDocument
    from src.modules.ai.retrieval import compute_local_embedding
    from src.modules.assessment.models import (
        AssessmentTemplate,
        TestQuestion,
        TestSection,
    )
    from src.modules.content.models import ContentLicense, ContentSource
    from src.modules.curriculum.models import (
        AcademicSession,
        Board,
        Book,
        Chapter,
        Concept,
        CurriculumVersion,
        Grade,
        Subject,
        Topic,
    )
    from src.modules.identity.models import Role, User, UserProfile, UserRole
    from src.modules.question_bank.importer import compute_canonical_hash
    from src.modules.question_bank.models import (
        Question,
        QuestionHint,
        QuestionOption,
        QuestionProvenance,
        QuestionSolution,
        QuestionVersion,
    )

    from datetime import UTC, date, datetime

    db_mgr = DatabaseManager(settings=Settings(app_env="test", database_url=db_url))
    try:
        async with db_mgr.session_factory() as s:
            admin = User(
                email="e2e.author@example.com",
                password_hash=hash_password("AuthorPass123"),
                status="active",
                is_minor=False,
            )
            s.add(admin)
            await s.flush()
            s.add(UserProfile(user_id=admin.id, display_name="E2E Author"))
            ca_role = await s.scalar(select(Role).where(Role.code == "content_admin"))
            assert ca_role is not None
            s.add(UserRole(user_id=admin.id, role_id=ca_role.id))

            board = Board(code="CBSE", name="CBSE Curriculum Framework")
            sess = AcademicSession(
                code="2026-27",
                starts_on=date(2026, 4, 1),
                ends_on=date(2027, 3, 31),
                is_active=True,
            )
            s.add_all([board, sess])
            await s.flush()

            ver = CurriculumVersion(
                board_id=board.id,
                academic_session_id=sess.id,
                version_tag="2026-27-v1",
                status="published",
                published_at=datetime.now(UTC),
            )
            subj = Subject(code="MATH", name="Mathematics", discipline="mathematics")
            grade_10 = await s.scalar(select(Grade).where(Grade.number == 10))
            assert grade_10 is not None
            s.add_all([ver, subj])
            await s.flush()

            book = Book(
                curriculum_version_id=ver.id,
                grade_id=grade_10.id,
                subject_id=subj.id,
                title="Class 10 Mathematics Starter",
                publisher="Go4Guru Original",
            )
            s.add(book)
            await s.flush()

            chap = Chapter(
                book_id=book.id,
                sequence_no=1,
                code="CH-LIN-EQ",
                title="Linear Equations Foundations",
            )
            s.add(chap)
            await s.flush()

            topic = Topic(chapter_id=chap.id, sequence_no=1, title="One-Variable Solving")
            s.add(topic)
            await s.flush()

            concept = Concept(
                topic_id=topic.id,
                curriculum_version_id=ver.id,
                code="MATH-10-LIN-01",
                title="Solving Linear Equations",
                difficulty_baseline=1,
                skill_tags_jsonb=["algebra"],
                exam_tags_jsonb=["CBSE_BOARD"],
            )
            src = ContentSource(
                name="Go4Guru Original Authoring",
                owner_name="Go4Guru",
                source_category="original_platform",
            )
            s.add_all([concept, src])
            await s.flush()

            lic = ContentLicense(
                source_id=src.id,
                license_name="Go4Guru Original",
                commercial_use_allowed=True,
                hosting_allowed=True,
                embedding_allowed=True,
                legal_review_status="approved",
                reviewed_by=admin.id,
                reviewed_at=datetime.now(UTC),
            )
            s.add(lic)
            await s.flush()

            stem = "Solve for $x$: $2x + 4 = 10$"
            q = Question(
                canonical_hash=compute_canonical_hash(stem, "mcq_single"),
                question_type="mcq_single",
                status="PUBLISHED",
                created_by=admin.id,
            )
            s.add(q)
            await s.flush()

            qv = QuestionVersion(
                question_id=q.id,
                version_no=1,
                language_code="en",
                curriculum_version_id=ver.id,
                grade_id=grade_10.id,
                subject_id=subj.id,
                chapter_id=chap.id,
                topic_id=topic.id,
                concept_id=concept.id,
                stem_markdown=stem,
                correct_answer_jsonb={"correct_key": "B"},
                difficulty="easy",
                ai_generated=False,
            )
            s.add(qv)
            await s.flush()
            q.current_version_id = qv.id

            s.add_all(
                [
                    QuestionOption(question_version_id=qv.id, option_key="A", content_markdown="2", is_correct=False),
                    QuestionOption(question_version_id=qv.id, option_key="B", content_markdown="3", is_correct=True),
                    QuestionOption(question_version_id=qv.id, option_key="C", content_markdown="4", is_correct=False),
                    QuestionSolution(
                        question_version_id=qv.id,
                        language_code="en",
                        solution_type="primary",
                        explanation_markdown="Subtract 4 to get 2x = 6, then divide by 2 to get x = 3.",
                        steps_jsonb=["2x = 6", "x = 3"],
                    ),
                    QuestionHint(
                        question_version_id=qv.id,
                        hint_level=1,
                        hint_markdown="Subtract 4 from both sides first.",
                    ),
                    QuestionProvenance(
                        question_id=q.id,
                        source_id=src.id,
                        license_id=lic.id,
                        source_type="original",
                        is_pyq=False,
                        verification_status="unverified",
                    ),
                ]
            )

            # Seed second chapter + numerical question + published mock test for Phase 2 E2E
            chap2 = Chapter(
                book_id=book.id,
                sequence_no=2,
                code="CH-2",
                title="Quadratic Numericals",
            )
            s.add(chap2)
            await s.flush()

            stem2 = "Evaluate $3^2 + 4^2$ as a positive integer."
            q2 = Question(
                canonical_hash=compute_canonical_hash(stem2, "numerical"),
                question_type="numerical",
                status="PUBLISHED",
                created_by=admin.id,
            )
            s.add(q2)
            await s.flush()

            qv2 = QuestionVersion(
                question_id=q2.id,
                version_no=1,
                language_code="en",
                curriculum_version_id=ver.id,
                grade_id=grade_10.id,
                subject_id=subj.id,
                chapter_id=chap2.id,
                topic_id=None,
                concept_id=concept.id,
                stem_markdown=stem2,
                correct_answer_jsonb={"expected_value": 25.0, "tolerance_abs": 0.01},
                difficulty="medium",
                ai_generated=False,
            )
            s.add(qv2)
            await s.flush()
            q2.current_version_id = qv2.id

            s.add_all(
                [
                    QuestionSolution(
                        question_version_id=qv2.id,
                        language_code="en",
                        solution_type="primary",
                        explanation_markdown="9 + 16 = 25.",
                        steps_jsonb=["3^2 = 9", "4^2 = 16", "9 + 16 = 25"],
                    ),
                    QuestionProvenance(
                        question_id=q2.id,
                        source_id=src.id,
                        license_id=lic.id,
                        source_type="original",
                        is_pyq=False,
                        verification_status="unverified",
                    ),
                ]
            )

            mock_test = AssessmentTemplate(
                title="CBSE E2E Diagnostic Mock",
                description="Seeded published Phase 2 mock with standard +4/-1 scoring.",
                test_category="cbse_mock",
                duration_seconds=900,
                grace_seconds=30,
                shuffle_questions=False,
                shuffle_options=False,
                created_by=admin.id,
                status="PUBLISHED",
                published_at=datetime.now(UTC),
            )
            s.add(mock_test)
            await s.flush()

            mock_sec = TestSection(
                test_id=mock_test.id,
                sequence_no=1,
                name="Core Mathematics",
                subject_id=subj.id,
                marking_rule_jsonb={
                    "mode": "standard",
                    "correct_marks": 4.0,
                    "wrong_marks": -1.0,
                    "unanswered_marks": 0.0,
                    "partial_credit_per_correct_option": 0.0,
                },
            )
            s.add(mock_sec)
            await s.flush()

            s.add_all(
                [
                    TestQuestion(
                        test_id=mock_test.id,
                        section_id=mock_sec.id,
                        question_id=q.id,
                        question_version_id=qv.id,
                        sequence_no=1,
                    ),
                    TestQuestion(
                        test_id=mock_test.id,
                        section_id=mock_sec.id,
                        question_id=q2.id,
                        question_version_id=qv2.id,
                        sequence_no=2,
                    ),
                ]
            )

            # Seed published RAG Knowledge Document + Chunk for Phase 3 E2E
            rag_doc = KnowledgeDocument(
                source_id=src.id,
                license_id=lic.id,
                curriculum_version_id=ver.id,
                grade_id=grade_10.id,
                subject_id=subj.id,
                chapter_id=chap.id,
                topic_id=topic.id,
                concept_id=concept.id,
                title="Linear Equations Balance Principle",
                language_code="en",
                status="PUBLISHED",
                embedding_allowed=True,
                attribution_text="Go4Guru Original Authoring",
                created_by=admin.id,
            )
            s.add(rag_doc)
            await s.flush()

            rag_txt = (
                "Solving linear equations such as 2*x + 4 = 10 uses the inverse operation "
                "principle: subtract 4 from both sides to isolate 2*x = 6, then divide by 2 "
                "so x = 3."
            )
            rag_chunk = KnowledgeChunk(
                document_id=rag_doc.id,
                chunk_index=1,
                hierarchy_path="CBSE > Class 10 > Mathematics > Linear Equations Foundations",
                section_title="Balancing One-Variable Equations",
                language_code="en",
                chunk_text=rag_txt,
                embedding_vec=compute_local_embedding(rag_txt),
                token_estimate=len(rag_txt.split()),
            )
            s.add(rag_chunk)
            await s.flush()
            await s.execute(
                text(
                    "UPDATE knowledge_chunks SET fts_tsv = to_tsvector('english', :t) "
                    "WHERE id = :cid"
                ),
                {"t": rag_txt, "cid": rag_chunk.id},
            )
            await s.commit()
    finally:
        await db_mgr.dispose()


def main() -> int:
    pg_port = _find_free_port(55432)
    api_port = 8000 if _find_free_port(8000) == 8000 else _find_free_port(8015)
    web_port = _find_free_port(3000)

    tmp_dir = Path(tempfile.mkdtemp(prefix="go4guru_e2e_pg_"))
    data_dir = tmp_dir / "data"
    log_file = tmp_dir / "postgres.log"
    storage_dir = tmp_dir / "storage"
    pg_started = False
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None

    try:
        subprocess.run(
            [
                str(PG_BIN / "initdb.exe"),
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
        subprocess.run(
            [
                str(PG_BIN / "pg_ctl.exe"),
                "-D",
                str(data_dir),
                "-l",
                str(log_file),
                "-o",
                f"-p {pg_port} -h 127.0.0.1",
                "start",
                "-w",
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        pg_started = True

        db_url = f"postgresql+asyncpg://postgres@127.0.0.1:{pg_port}/postgres"
        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(cfg, "head")

        asyncio.run(_seed_e2e_curriculum_and_question(db_url))

        web_origin = f"http://127.0.0.1:{web_port}"
        api_env = os.environ.copy()
        api_env.update(
            {
                "APP_ENV": "test",
                "DATABASE_URL": db_url,
                "JWT_SECRET_KEY": "e2e-runtime-jwt-secret-must-exceed-32-characters",
                "STORAGE_LOCAL_DIR": str(storage_dir),
                "CORS_ALLOWED_ORIGINS": f'["{web_origin}","http://localhost:{web_port}"]',
            }
        )
        api_proc = subprocess.Popen(
            [
                str(ROOT_DIR / ".venv" / "Scripts" / "uvicorn.exe"),
                "src.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            cwd=str(API_DIR),
            env=api_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_http(f"http://127.0.0.1:{api_port}/health/live")

        web_env = os.environ.copy()
        web_env.update(
            {
                "NEXT_PUBLIC_API_BASE_URL": f"http://127.0.0.1:{api_port}",
                "E2E_WEB_URL": web_origin,
            }
        )
        pnpm_cmd = shutil.which("pnpm") or "pnpm"
        web_proc = subprocess.Popen(
            [
                pnpm_cmd,
                "--dir",
                str(WEB_DIR),
                "exec",
                "next",
                "start",
                "-p",
                str(web_port),
            ],
            cwd=str(ROOT_DIR),
            env=web_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        _wait_http(f"{web_origin}/login")

        e2e_res = subprocess.run(
            [pnpm_cmd, "--dir", str(WEB_DIR), "exec", "playwright", "test"],
            cwd=str(ROOT_DIR),
            env=web_env,
            shell=True,
        )
        return int(e2e_res.returncode)
    finally:
        if web_proc is not None:
            web_proc.terminate()
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(web_proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        if api_proc is not None:
            api_proc.terminate()
            try:
                api_proc.wait(timeout=5)
            except Exception:
                api_proc.kill()
        if pg_started:
            subprocess.run(
                [str(PG_BIN / "pg_ctl.exe"), "-D", str(data_dir), "stop", "-m", "immediate"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
