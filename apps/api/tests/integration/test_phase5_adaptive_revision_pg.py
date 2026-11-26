"""PostgreSQL 18 integration tests for Phase 5 Adaptive Mastery, SM-2+ & Study Plans."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from src.core.config import Settings
from src.core.database import DatabaseManager
from src.core.security import hash_password
from src.main import create_app
from src.modules.assessment.models import PracticeSession, QuestionAttempt
from src.modules.content.models import ContentLicense, ContentSource
from src.modules.curriculum.models import (
    AcademicSession,
    Board,
    Book,
    Chapter,
    Concept,
    ConceptPrerequisite,
    CurriculumVersion,
    Grade,
    LearningObjective,
    Subject,
    Topic,
)
from src.modules.identity.models import Role, User, UserProfile, UserRole
from src.modules.question_bank.importer import compute_canonical_hash
from src.modules.question_bank.models import (
    Question,
    QuestionOption,
    QuestionProvenance,
    QuestionSolution,
    QuestionVersion,
)

from tests.conftest import StubCheck
from tests.integration.test_phase1_e2e_pg import pg18_database_url  # noqa: F401


async def _seed_phase5_curriculum_and_attempts(
    db: DatabaseManager, student_id: UUID
) -> dict[str, UUID]:
    async with db.session_factory() as s:
        author = User(
            email="p5.author@example.com",
            password_hash=hash_password("AuthorPass!123"),
            status="active",
            is_minor=False,
        )
        s.add(author)
        await s.flush()
        s.add(UserProfile(user_id=author.id, display_name="P5 Author"))
        r = await s.scalar(select(Role).where(Role.code == "content_admin"))
        assert r is not None
        s.add(UserRole(user_id=author.id, role_id=r.id))

        src = ContentSource(
            name="Go4Guru Original Phase 5",
            owner_name="Go4Guru",
            source_category="original_platform",
        )
        s.add(src)
        await s.flush()
        lic = ContentLicense(
            source_id=src.id,
            license_name="Original Platform License",
            hosting_allowed=True,
            embedding_allowed=True,
            legal_review_status="approved",
        )
        s.add(lic)

        board = Board(code="CBSE_P5", name="CBSE Phase 5")
        grade = await s.scalar(select(Grade).where(Grade.number == 10))
        if grade is None:
            grade = Grade(number=10, label="Class 10")
            s.add(grade)
            await s.flush()
        subj = Subject(code="MATH_P5", name="Mathematics", discipline="mathematics")
        sess = AcademicSession(
            code="2026-27-P5",
            starts_on=date(2026, 4, 1),
            ends_on=date(2027, 3, 31),
            is_active=True,
        )
        s.add_all([board, subj, sess])
        await s.flush()

        cv = CurriculumVersion(
            board_id=board.id,
            academic_session_id=sess.id,
            version_tag="CBSE-P5-v1",
            status="published",
            published_at=datetime.now(UTC),
        )
        s.add(cv)
        await s.flush()
        book = Book(
            curriculum_version_id=cv.id,
            grade_id=grade.id,
            subject_id=subj.id,
            title="Math 10",
            publisher="Go4Guru Original",
        )
        s.add(book)
        await s.flush()
        chap = Chapter(book_id=book.id, code="CH_QUAD", title="Quadratic Equations", sequence_no=1)
        s.add(chap)
        await s.flush()
        topic = Topic(chapter_id=chap.id, title="Factorization & Discriminant", sequence_no=1)
        s.add(topic)
        await s.flush()

        c_prereq = Concept(
            topic_id=topic.id,
            curriculum_version_id=cv.id,
            code="LIN_EXPR",
            title="Linear Expressions",
        )
        c_target = Concept(
            topic_id=topic.id,
            curriculum_version_id=cv.id,
            code="QUAD_DISC",
            title="Quadratic Discriminant",
        )
        c_master = Concept(
            topic_id=topic.id,
            curriculum_version_id=cv.id,
            code="NUM_SYSTEM",
            title="Real Number Identities",
        )
        s.add_all([c_prereq, c_target, c_master])
        await s.flush()

        s.add_all(
            [
                LearningObjective(
                    concept_id=c_prereq.id,
                    bloom_level="apply",
                    statement="Transpose linear terms accurately",
                ),
                LearningObjective(
                    concept_id=c_target.id,
                    bloom_level="analyze",
                    statement="Compute discriminant D = b^2 - 4ac",
                ),
                LearningObjective(
                    concept_id=c_master.id,
                    bloom_level="apply",
                    statement="Apply real number identities independently",
                ),
                ConceptPrerequisite(concept_id=c_target.id, prerequisite_concept_id=c_prereq.id),
            ]
        )

        # Create 3 Questions mapped to c_prereq, c_target, c_master
        async def _mk_q(
            cid: UUID, stem: str, diff: str, qtype: str, key: str, wrong_note: str
        ) -> tuple[UUID, UUID]:
            q = Question(
                canonical_hash=compute_canonical_hash(stem, qtype),
                question_type=qtype,
                status="PUBLISHED",
                created_by=author.id,
            )
            s.add(q)
            await s.flush()
            qv = QuestionVersion(
                question_id=q.id,
                version_no=1,
                language_code="en",
                curriculum_version_id=cv.id,
                grade_id=grade.id,
                subject_id=subj.id,
                chapter_id=chap.id,
                topic_id=topic.id,
                concept_id=cid,
                stem_markdown=stem,
                difficulty=diff,
                correct_answer_jsonb={"correct_key": key},
                ai_generated=False,
            )
            s.add(qv)
            await s.flush()
            q.current_version_id = qv.id
            s.add_all(
                [
                    QuestionOption(
                        question_version_id=qv.id,
                        option_key="A",
                        content_markdown="Opt A",
                        is_correct=(key == "A"),
                    ),
                    QuestionOption(
                        question_version_id=qv.id,
                        option_key="B",
                        content_markdown="Opt B",
                        is_correct=(key == "B"),
                    ),
                    QuestionSolution(
                        question_version_id=qv.id,
                        language_code="en",
                        solution_type="primary",
                        explanation_markdown="Detailed textbook derivation.",
                        steps_jsonb=["Step 1", "Step 2"],
                        common_mistakes_markdown=wrong_note,
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
            return q.id, qv.id

        q_pre, qv_pre = await _mk_q(
            c_prereq.id,
            "Solve 3x - 9 = 0",
            "easy",
            "mcq_single",
            "A",
            "Sign flip error on transposition",
        )
        q_tgt, qv_tgt = await _mk_q(
            c_target.id,
            "Find discriminant of x^2 + 4x + 4 = 0",
            "medium",
            "mcq_single",
            "B",
            "Forgot minus 4ac",
        )
        q_mst, qv_mst = await _mk_q(
            c_master.id,
            "Evaluate (a+b)^2 - (a-b)^2",
            "hard",
            "mcq_single",
            "A",
            "Expansion mistake",
        )

        ps = PracticeSession(student_id=student_id, subject_id=subj.id, chapter_id=chap.id)
        s.add(ps)
        await s.flush()

        # Student missed q_pre and q_tgt (hinted), and solved q_mst cleanly 4x independently
        s.add_all(
            [
                QuestionAttempt(
                    student_id=student_id,
                    question_id=q_pre,
                    question_version_id=qv_pre,
                    practice_session_id=ps.id,
                    response_jsonb={"selected_key": "B"},
                    is_correct=False,
                    hints_used_count=0,
                ),
                QuestionAttempt(
                    student_id=student_id,
                    question_id=q_tgt,
                    question_version_id=qv_tgt,
                    practice_session_id=ps.id,
                    response_jsonb={"selected_key": "A"},
                    is_correct=False,
                    hints_used_count=2,
                ),
                *[
                    QuestionAttempt(
                        student_id=student_id,
                        question_id=q_mst,
                        question_version_id=qv_mst,
                        practice_session_id=ps.id,
                        response_jsonb={"selected_key": "A"},
                        is_correct=True,
                        hints_used_count=0,
                    )
                    for _ in range(4)
                ],
            ]
        )
        await s.commit()
        return {"prereq": c_prereq.id, "target": c_target.id, "master": c_master.id}


async def test_phase5_adaptive_mastery_flashcards_study_plan_and_isolation_pg18(
    pg18_database_url: str,  # noqa: F811
    tmp_path: Path,
) -> None:
    """Verify mastery, misconceptions, remediation, missed-Q SM-2+, study plans & isolation."""
    settings = Settings(
        app_env="test",
        database_url=pg18_database_url,
        jwt_secret_key="phase5-integration-secret-key-at-least-32-chars",
        storage_local_dir=str(tmp_path / "p5_storage"),
    )
    app = create_app(settings_override=settings)
    db = DatabaseManager(settings)
    app.state.db = db
    app.state.redis = StubCheck(healthy=True)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            r_a = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p5.student.a@example.com",
                    "password": "StudentPass!123",
                    "display_name": "P5 Student A",
                    "date_of_birth_year": 2009,
                    "role": "student",
                },
            )
            assert r_a.status_code == 201
            a_id = UUID(r_a.json()["user"]["id"])
            a_h = {"Authorization": f"Bearer {r_a.json()['access_token']}"}

            r_b = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "p5.student.b@example.com",
                    "password": "StudentPass!123",
                    "display_name": "P5 Student B",
                    "date_of_birth_year": 2009,
                    "role": "student",
                },
            )
            b_h = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

            concept_ids = await _seed_phase5_curriculum_and_attempts(db, a_id)

            # 1. Recompute mastery & inspect adaptive overview
            r_rec = await client.post("/api/v1/learning/recompute", headers=a_h)
            assert r_rec.status_code == 200
            ov = r_rec.json()
            assert len(ov["concepts"]) == 3
            assert len(ov["weak_concepts"]) >= 2
            assert len(ov["unresolved_misconceptions"]) >= 2
            rec_types = [(UUID(r["concept_id"]), r["item_type"]) for r in ov["recommendations"]]
            assert rec_types[0] == (concept_ids["prereq"], "remediate_prerequisite")

            # Resolve one misconception manually & record one explicit misconception
            misc_id = ov["unresolved_misconceptions"][0]["id"]
            r_res = await client.post(
                f"/api/v1/learning/misconceptions/{misc_id}/resolve",
                headers=a_h,
            )
            assert r_res.status_code == 200
            assert r_res.json()["resolved_at"] is not None

            # 2. Generate & persist LearningPath and mark step completed
            r_lp = await client.post(
                "/api/v1/learning/learning-paths",
                headers=a_h,
                json={"title": "Quadratic Recovery Path", "goal_exam_track": "CBSE_BOARD"},
            )
            assert r_lp.status_code == 201
            assert len(r_lp.json()["items"]) >= 2
            first_lp_item_id = r_lp.json()["items"][0]["id"]
            r_lp_done = await client.patch(
                f"/api/v1/learning/learning-paths/items/{first_lp_item_id}",
                headers=a_h,
                json={"status": "completed"},
            )
            assert r_lp_done.status_code == 200
            assert r_lp_done.json()["status"] == "completed"

            # 3. Sync missed questions into flashcards & create formula/vocab cards
            r_sync = await client.post("/api/v1/revision/flashcards/sync-missed", headers=a_h)
            assert r_sync.status_code == 200
            assert r_sync.json()["created_count"] == 2

            r_fcard = await client.post(
                "/api/v1/revision/flashcards",
                headers=a_h,
                json={
                    "card_type": "formula",
                    "concept_id": str(concept_ids["target"]),
                    "front_markdown": "Discriminant of $ax^2 + bx + c = 0$",
                    "back_markdown": "$$D = b^2 - 4ac$$",
                },
            )
            assert r_fcard.status_code == 201

            # Due queue prioritizes missed_question & weak concepts first
            r_due = await client.get("/api/v1/revision/flashcards/due", headers=a_h)
            assert r_due.status_code == 200
            due_cards = r_due.json()
            assert len(due_cards) == 3
            assert due_cards[0]["card_type"] == "missed_question"

            # Review card 1 with quality 5 (1d), then review card 2 with quality 2 (lapse)
            r_rev1 = await client.post(
                f"/api/v1/revision/flashcards/{due_cards[0]['id']}/review",
                headers=a_h,
                json={"quality": 5, "response_ms": 2400},
            )
            assert r_rev1.status_code == 200
            assert r_rev1.json()["new_interval_days"] == 1
            assert r_rev1.json()["flashcard"]["is_due"] is False

            r_rev2 = await client.post(
                f"/api/v1/revision/flashcards/{due_cards[1]['id']}/review",
                headers=a_h,
                json={"quality": 2, "response_ms": 9500},
            )
            assert r_rev2.status_code == 200
            assert r_rev2.json()["flashcard"]["lapse_count"] >= 2

            # 4. Generate personalized StudyPlan & complete an item
            r_sp = await client.post(
                "/api/v1/revision/study-plans",
                headers=a_h,
                json={"title": "Week 1 Remediation Sprint", "daily_minutes_budget": 45},
            )
            assert r_sp.status_code == 201
            sp_items = r_sp.json()["items"]
            assert len(sp_items) >= 2
            r_sp_done = await client.patch(
                f"/api/v1/revision/study-plans/items/{sp_items[0]['id']}",
                headers=a_h,
                json={"status": "completed"},
            )
            assert r_sp_done.status_code == 200

            # 5. Revision Analytics & Notifications
            r_ana = await client.get("/api/v1/revision/analytics", headers=a_h)
            assert r_ana.status_code == 200
            ana = r_ana.json()
            assert ana["total_flashcards"] == 3
            assert ana["missed_question_cards_count"] == 2
            assert ana["total_reviews"] == 2
            assert ana["active_plan_completion_pct"] > 0.0

            r_notifs = await client.get("/api/v1/notifications", headers=a_h)
            assert r_notifs.status_code == 200
            assert len(r_notifs.json()) >= 2
            nid = r_notifs.json()[0]["id"]
            r_read = await client.post(f"/api/v1/notifications/{nid}/read", headers=a_h)
            assert r_read.status_code == 200
            assert r_read.json()["is_read"] is True

            # 6. Cross-student isolation
            assert (
                len((await client.get("/api/v1/revision/flashcards/due", headers=b_h)).json()) == 0
            )
            r_iso = await client.post(f"/api/v1/notifications/{nid}/read", headers=b_h)
            assert r_iso.status_code == 404
    finally:
        await db.dispose()
