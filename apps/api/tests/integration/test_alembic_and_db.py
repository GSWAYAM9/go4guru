"""Integration checks for Alembic migration graph, PostgreSQL DDL generation, and boundaries."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from src.core import outbox  # noqa: F401
from src.core.database import Base, DatabaseManager
from src.core.redis_client import RedisManager
from src.modules import DOMAIN_MODULES

API_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_single_head_and_offline_postgresql_ddl() -> None:
    """Verify Alembic migration script graph and PostgreSQL 18 offline SQL DDL output."""
    buf = io.StringIO()
    cfg = Config(str(API_ROOT / "alembic.ini"), stdout=buf)
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))

    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["0006_phase5_adaptive_revision"]

    with contextlib.redirect_stdout(buf):
        command.upgrade(cfg, "head", sql=True)
    ddl = buf.getvalue()
    assert "CREATE TABLE audit_logs" in ddl
    assert "CREATE TABLE outbox_events" in ddl
    assert "CREATE TABLE users" in ddl
    assert "CREATE TABLE curriculum_versions" in ddl
    assert "CREATE TABLE questions" in ddl
    assert "CREATE TABLE question_provenance" in ddl
    assert "CREATE TABLE import_staging_rows" in ddl
    assert "CREATE TABLE practice_sessions" in ddl
    assert "CREATE TABLE exam_patterns" in ddl
    assert "CREATE TABLE quizzes" in ddl
    assert "CREATE TABLE tests" in ddl
    assert "CREATE TABLE assessment_attempts" in ddl
    assert "CREATE TABLE learning_events" in ddl
    assert "CREATE TABLE knowledge_documents" in ddl
    assert "CREATE TABLE knowledge_chunks" in ddl
    assert "CREATE TABLE ai_sessions" in ddl
    assert "CREATE TABLE ai_messages" in ddl
    assert "CREATE TABLE ai_cost_events" in ddl
    assert "CREATE TABLE ai_eval_runs" in ddl
    assert "CREATE TABLE language_capabilities" in ddl
    assert "CREATE TABLE lesson_plans" in ddl
    assert "CREATE TABLE classroom_sessions" in ddl
    assert "CREATE TABLE whiteboard_snapshots" in ddl
    assert "CREATE TABLE whiteboard_events" in ddl
    assert "CREATE TABLE voice_usage_logs" in ddl
    assert "CREATE TABLE student_concept_mastery" in ddl
    assert "CREATE TABLE student_misconceptions" in ddl
    assert "CREATE TABLE flashcards" in ddl
    assert "CREATE TABLE study_plans" in ddl
    assert "CREATE TABLE student_notifications" in ddl
    assert "gen_random_uuid()" in ddl
    assert "JSONB" in ddl
    assert "TIMESTAMP WITH TIME ZONE" in ddl


def test_foundation_orm_metadata_matches_schema_conventions() -> None:
    """Confirm core + Phase 1-4 ORM metadata includes key relational tables."""
    required = {
        "audit_logs",
        "outbox_events",
        "users",
        "roles",
        "permissions",
        "boards",
        "curriculum_versions",
        "concepts",
        "content_sources",
        "content_licenses",
        "questions",
        "question_versions",
        "import_batches",
        "import_staging_rows",
        "practice_sessions",
        "question_attempts",
        "student_notes",
        "saved_questions",
        "exam_patterns",
        "quizzes",
        "quiz_questions",
        "tests",
        "test_sections",
        "test_questions",
        "assessment_attempts",
        "attempt_answers",
        "processed_event_ids",
        "learning_events",
        "analytics_snapshots",
        "knowledge_documents",
        "knowledge_chunks",
        "ai_sessions",
        "ai_messages",
        "ai_tool_calls",
        "provider_rate_cards",
        "ai_cost_events",
        "ai_review_queue",
        "ai_eval_datasets",
        "ai_eval_runs",
        "ai_eval_results",
        "language_capabilities",
        "whiteboard_assets",
        "lesson_plans",
        "classroom_sessions",
        "classroom_events",
        "whiteboard_snapshots",
        "whiteboard_events",
        "voice_usage_logs",
        "student_concept_mastery",
        "student_misconceptions",
        "learning_paths",
        "learning_path_items",
        "flashcards",
        "student_flashcards",
        "flashcard_reviews",
        "study_plans",
        "study_plan_items",
        "student_notifications",
    }
    assert required.issubset(set(Base.metadata.tables.keys()))


def test_all_16_domain_module_boundaries_exist() -> None:
    """Confirm every domain module has an explicit public.py contract boundary."""
    assert len(DOMAIN_MODULES) == 16
    for descriptor in DOMAIN_MODULES:
        mod_dir = API_ROOT / "src" / "modules" / descriptor.name
        assert (mod_dir / "__init__.py").is_file()
        assert (mod_dir / "public.py").is_file()


@pytest.mark.skipif(
    os.getenv("GO4GURU_RUN_LIVE_DB_TESTS") != "1",
    reason="Set GO4GURU_RUN_LIVE_DB_TESTS=1 with live PG18 + Redis services to test live sockets.",
)
async def test_live_postgres_and_redis_connections() -> None:
    """Optional live Postgres 18 and Redis verification (enabled in CI)."""
    db = DatabaseManager()
    redis = RedisManager()
    try:
        db_ok, db_err = await db.check_connectivity()
        redis_ok, redis_err = await redis.check_connectivity()
        assert db_ok, f"Postgres failed: {db_err}"
        assert redis_ok, f"Redis failed: {redis_err}"
    finally:
        await redis.close()
        await db.dispose()
