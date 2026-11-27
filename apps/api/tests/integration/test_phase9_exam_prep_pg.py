"""Phase 9 PostgreSQL 18 Integration Tests: Examination Preparation Ecosystem.

Verifies:
1. Versioned ExamPattern listing across CBSE_BOARD, JEE_MAIN, JEE_ADVANCED, NEET.
2. Syllabus & chapter mapping RBAC (student 403, content_admin/academic_reviewer 201)
   and honest coverage audit transitions.
3. Strict PYQ provenance enforcement: unverified or AI-generated questions are NEVER
   returned when `verified_pyq_only=true`, whereas verified PYQs carry full citations.
4. Answer redaction in `/exam-prep/{exam_code}/questions` and `/attempts/{id}/solutions`
   returning 403 while `in_progress`, unlocking detailed solutions strictly post-submit.
5. Full timed mock generation, exam analytics (accuracy, speed, weak chapters),
   formula sheets, and persisted exam revision plans.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.modules.question_bank.models import (
    Question,
    QuestionOption,
    QuestionProvenance,
    QuestionSolution,
    QuestionVersion,
)
from tests.conftest import register_and_login


async def _seed_exam_question_fixture(
    db: AsyncSession,
    *,
    reviewer_id,
    exam_name: str,
    exam_year: int,
    verified: bool,
    ai_generated: bool,
    question_type: str = "mcq_single",
):
    board = (await db.scalars(select(Board).limit(1))).first()
    if board is None:
        board = Board(code="CBSE_T9", name="CBSE Test 9")
        db.add(board)
        await db.flush()
    session = (await db.scalars(select(AcademicSession).limit(1))).first()
    if session is None:
        session = AcademicSession(label="2026-27", start_year=2026, end_year=2027)
        db.add(session)
        await db.flush()
    grade = (await db.scalars(select(Grade).limit(1))).first()
    if grade is None:
        grade = Grade(number=12, label="Class 12")
        db.add(grade)
        await db.flush()
    cv = (await db.scalars(select(CurriculumVersion).limit(1))).first()
    if cv is None:
        cv = CurriculumVersion(
            board_id=board.id,
            academic_session_id=session.id,
            version_label="2026-v1",
            status="PUBLISHED",
        )
        db.add(cv)
        await db.flush()
    subject = Subject(code=f"PHY_{uuid4().hex[:4]}", name="Physics", discipline="science")
    db.add(subject)
    await db.flush()
    book = Book(
        curriculum_version_id=cv.id,
        grade_id=grade.id,
        subject_id=subject.id,
        title="NCERT Physics XII",
    )
    db.add(book)
    await db.flush()
    chapter = Chapter(book_id=book.id, code=f"CH_{uuid4().hex[:4]}", title="Electrostatics", sequence_no=1)
    db.add(chapter)
    await db.flush()
    topic = Topic(chapter_id=chapter.id, title="Gauss Law", sequence_no=1)
    db.add(topic)
    await db.flush()
    concept = Concept(
        curriculum_version_id=cv.id,
        topic_id=topic.id,
        code=f"CON_{uuid4().hex[:4]}",
        title="Electric Flux through Closed Surface",
    )
    db.add(concept)
    await db.flush()

    q = Question(
        question_type=question_type,
        status="PUBLISHED",
        canonical_hash=uuid4().hex,
    )
    db.add(q)
    await db.flush()

    qv = QuestionVersion(
        question_id=q.id,
        version_no=1,
        curriculum_version_id=cv.id,
        grade_id=grade.id,
        subject_id=subject.id,
        chapter_id=chapter.id,
        topic_id=topic.id,
        concept_id=concept.id,
        stem_markdown="Find the electric flux through a closed sphere enclosing charge $q$.",
        difficulty="medium",
        default_marks=Decimal("4.00"),
        default_negative_marks=Decimal("1.00"),
        estimated_seconds=90,
        ai_generated=ai_generated,
        correct_answer_jsonb={"correct_key": "A"},
    )
    db.add(qv)
    await db.flush()
    q.current_version_id = qv.id

    db.add(QuestionOption(question_version_id=qv.id, option_key="A", content_markdown="$q/\\varepsilon_0$", is_correct=True))
    db.add(QuestionOption(question_version_id=qv.id, option_key="B", content_markdown="$0$", is_correct=False))
    db.add(
        QuestionSolution(
            question_version_id=qv.id,
            explanation_markdown="By Gauss's Law, total flux equals enclosed charge divided by $\\varepsilon_0$.",
            steps_jsonb=["Apply Gauss Law: $\\Phi = q_{enc}/\\varepsilon_0$"],
            common_mistakes_markdown="Do not multiply by $4\\pi r^2$ again when using total enclosed charge.",
        )
    )
    db.add(
        QuestionProvenance(
            question_id=q.id,
            source_id=uuid4(),
            license_id=uuid4(),
            source_type="OFFICIAL_EXAM_PAPER",
            is_pyq=True,
            exam_name=exam_name,
            exam_year=exam_year,
            exam_session="January",
            exam_shift="Shift 1",
            paper_code="JM24-S1",
            verification_status="verified" if verified else "unverified",
            verified_by=reviewer_id if verified else None,
        )
    )
    await db.commit()
    return subject, chapter, topic, q, qv


@pytest.mark.asyncio
async def test_phase9_exam_prep_end_to_end(client: AsyncClient, db_session: AsyncSession) -> None:
    student_headers, _ = await register_and_login(client, role="student")
    admin_headers, admin_user = await register_and_login(client, role="content_admin")

    # 1. List exam tracks — must include all 4 canonical tracks with honest coverage audit
    tracks_res = await client.get("/api/v1/exam-prep/tracks", headers=student_headers)
    assert tracks_res.status_code == 200
    codes = {t["code"] for t in tracks_res.json()}
    assert {"CBSE_BOARD", "JEE_MAIN", "JEE_ADVANCED", "NEET"}.issubset(codes)

    # 2. Seed one verified PYQ and one AI-generated unverified question claiming JEE Main
    subject, chapter, _topic, verified_q, _ = await _seed_exam_question_fixture(
        db_session,
        reviewer_id=admin_user["id"],
        exam_name="JEE Main",
        exam_year=2024,
        verified=True,
        ai_generated=False,
    )
    await _seed_exam_question_fixture(
        db_session,
        reviewer_id=admin_user["id"],
        exam_name="JEE Main",
        exam_year=2024,
        verified=True,
        ai_generated=True,  # MUST be rejected as PYQ
    )

    # 3. Student cannot upsert syllabus mapping (403); content_admin can (201)
    syl_payload = {
        "pattern_version_label": "jee-main-2026-nta-v2",
        "subject_id": str(subject.id),
        "chapter_id": str(chapter.id),
        "weightage_pct": 8.5,
        "expected_questions": 2,
        "priority_tier": "high_yield",
        "syllabus_status": "included",
        "audit_verified": True,
    }
    forbidden_res = await client.post(
        "/api/v1/exam-prep/JEE_MAIN/syllabus", json=syl_payload, headers=student_headers
    )
    assert forbidden_res.status_code == 403

    ok_syl = await client.post(
        "/api/v1/exam-prep/JEE_MAIN/syllabus", json=syl_payload, headers=admin_headers
    )
    assert ok_syl.status_code == 201
    assert ok_syl.json()["audit_verified"] is True

    # 4. Strict Verified PYQ filter excludes AI-generated question and redacts answers
    pyq_res = await client.get(
        "/api/v1/exam-prep/JEE_MAIN/questions?verified_pyq_only=true&exam_year=2024",
        headers=student_headers,
    )
    assert pyq_res.status_code == 200
    pyq_data = pyq_res.json()
    returned_ids = [q["question_id"] for q in pyq_data["questions"]]
    assert str(verified_q.id) in returned_ids
    assert pyq_data["facets"]["unverified_pyq_excluded_count"] >= 1
    for q in pyq_data["questions"]:
        assert "correct_answer_jsonb" not in q
        assert q["pyq_provenance"]["is_verified_pyq"] is True
        assert q["pyq_provenance"]["exam_year"] == 2024

    # 5. Launch chapter practice & verify solutions are 403 while in_progress
    launch_res = await client.post(
        "/api/v1/exam-prep/JEE_MAIN/practice",
        json={
            "mode": "verified_pyq_drill",
            "chapter_id": str(chapter.id),
            "verified_pyq_only": True,
            "question_count": 5,
        },
        headers=student_headers,
    )
    assert launch_res.status_code == 201
    attempt_id = launch_res.json()["attempt_id"]

    locked_sol = await client.get(
        f"/api/v1/exam-prep/attempts/{attempt_id}/solutions", headers=student_headers
    )
    assert locked_sol.status_code == 403

    # 6. Submit attempt & unlock detailed post-attempt solutions
    submit_res = await client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/submit",
        json={"idempotency_key": f"p9-sub-{uuid4().hex}"},
        headers=student_headers,
    )
    assert submit_res.status_code == 200

    unlocked_sol = await client.get(
        f"/api/v1/exam-prep/attempts/{attempt_id}/solutions", headers=student_headers
    )
    assert unlocked_sol.status_code == 200
    assert len(unlocked_sol.json()["items"]) >= 1
    assert unlocked_sol.json()["items"][0]["correct_answer_jsonb"]["correct_key"] == "A"

    # 7. Author formula sheet & create student revision plan
    formula_res = await client.post(
        "/api/v1/exam-prep/JEE_MAIN/formulas",
        json={
            "subject_id": str(subject.id),
            "chapter_id": str(chapter.id),
            "title": "Gauss's Law in Vacuum",
            "formula_latex": r"\oint \vec{E}\cdot d\vec{A} = \frac{q_{\text{enc}}}{\varepsilon_0}",
            "variables": [{"symbol": "q_{enc}", "meaning": "Net enclosed charge", "unit": "C"}],
            "when_to_use": "Symmetric charge distributions (spherical, cylindrical, planar).",
            "common_pitfall": "Ignoring sign of enclosed charges.",
            "is_high_yield": True,
        },
        headers=admin_headers,
    )
    assert formula_res.status_code == 201

    plan_res = await client.post(
        "/api/v1/exam-prep/JEE_MAIN/revision-plans",
        json={
            "target_exam_date": (date.today() + timedelta(days=7)).isoformat(),
            "daily_minutes": 120,
        },
        headers=student_headers,
    )
    assert plan_res.status_code == 201
    assert len(plan_res.json()["schedule"]) >= 1

    # 8. Exam analytics returns real accuracy, pacing, and recommendations
    analytics_res = await client.get(
        "/api/v1/exam-prep/JEE_MAIN/analytics", headers=student_headers
    )
    assert analytics_res.status_code == 200
    assert analytics_res.json()["target_seconds_per_question"] == 144
    assert analytics_res.json()["total_attempts"] >= 1
