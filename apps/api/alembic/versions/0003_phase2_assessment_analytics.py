"""Phase 2 quiz, assessment engine, exam patterns, and analytics tables.

Revision ID: 0003_phase2_assessment_analytics
Revises: 0002_phase1_core
Create Date: 2026-11-26 21:35:00+05:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase2_assessment_analytics"
down_revision: str | Sequence[str] | None = "0002_phase1_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exam_patterns",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("exam_track_id", sa.Uuid(), nullable=False),
        sa.Column("version_label", sa.String(length=64), nullable=False),
        sa.Column("effective_year", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "rules_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["exam_track_id"],
            ["exam_tracks.id"],
            ondelete="RESTRICT",
            name=op.f("fk_exam_patterns_exam_track_id_exam_tracks"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_patterns")),
        sa.UniqueConstraint(
            "exam_track_id", "version_label", name="uq_exam_patterns_track_version"
        ),
    )

    op.create_table(
        "quizzes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("quiz_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("exam_pattern_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column(
            "config_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_ai_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'PUBLISHED'"), nullable=False
        ),
        sa.CheckConstraint(
            "quiz_type IN ('daily', 'quick', 'chapter', 'topic', 'concept', 'diagnostic', "
            "'revision', 'teacher', 'ai_generated', 'challenge', 'competition', 'institution')",
            name=op.f("ck_quizzes_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name=op.f("ck_quizzes_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_quizzes_created_by")
        ),
        sa.ForeignKeyConstraint(
            ["exam_pattern_id"],
            ["exam_patterns.id"],
            ondelete="SET NULL",
            name=op.f("fk_quizzes_exam_pattern_id"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], ondelete="SET NULL", name=op.f("fk_quizzes_subject")
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], ondelete="SET NULL", name=op.f("fk_quizzes_chapter")
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], ondelete="SET NULL", name=op.f("fk_quizzes_topic")
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], ondelete="SET NULL", name=op.f("fk_quizzes_concept")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quizzes")),
    )
    op.create_index("ix_quizzes_creator_type", "quizzes", ["created_by", "quiz_type"])

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("marks_override", sa.Numeric(6, 2), nullable=True),
        sa.Column("negative_marks_override", sa.Numeric(6, 2), nullable=True),
        sa.ForeignKeyConstraint(
            ["quiz_id"], ["quizzes.id"], ondelete="CASCADE", name=op.f("fk_quiz_questions_quiz")
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quiz_questions_question"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_quiz_questions_qv"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_questions")),
        sa.UniqueConstraint("quiz_id", "sequence_no", name="uq_quiz_questions_seq"),
    )

    op.create_table(
        "tests",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("exam_pattern_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("test_category", sa.String(length=32), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("grace_seconds", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("total_marks", sa.Numeric(8, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column(
            "retake_policy_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text('\'{"max_attempts": null, "cooldown_minutes": 0}\'::jsonb'),
            nullable=False,
        ),
        sa.Column(
            "shuffle_questions", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("shuffle_options", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'DRAFT'"), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "test_category IN ('cbse_mock', 'jee_main', 'jee_adv', 'neet', "
            "'chapter_test', 'topic_test', 'diagnostic', 'teacher_test', 'institution_test')",
            name=op.f("ck_tests_category_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name=op.f("ck_tests_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["exam_pattern_id"],
            ["exam_patterns.id"],
            ondelete="SET NULL",
            name=op.f("fk_tests_exam_pattern_id"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_tests_created_by")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tests")),
    )

    op.create_table(
        "test_sections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column(
            "marking_rule_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("attempt_limit", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["test_id"], ["tests.id"], ondelete="CASCADE", name=op.f("fk_test_sections_test")
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="SET NULL",
            name=op.f("fk_test_sections_subject"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_sections")),
        sa.UniqueConstraint("test_id", "sequence_no", name="uq_test_sections_seq"),
    )

    op.create_table(
        "test_questions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("marks_override", sa.Numeric(6, 2), nullable=True),
        sa.Column("negative_marks_override", sa.Numeric(6, 2), nullable=True),
        sa.ForeignKeyConstraint(
            ["test_id"], ["tests.id"], ondelete="CASCADE", name=op.f("fk_test_questions_test")
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["test_sections.id"],
            ondelete="CASCADE",
            name=op.f("fk_test_questions_section"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_test_questions_question"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_test_questions_qv"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_questions")),
        sa.UniqueConstraint("section_id", "sequence_no", name="uq_test_questions_section_seq"),
    )

    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("test_id", sa.Uuid(), nullable=True),
        sa.Column("quiz_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'in_progress'"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("seed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "question_order_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("raw_score", sa.Numeric(8, 2), nullable=True),
        sa.Column("max_score", sa.Numeric(8, 2), nullable=True),
        sa.Column("accuracy_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "result_summary_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(test_id IS NOT NULL) OR (quiz_id IS NOT NULL)",
            name=op.f("ck_assessment_attempts_target_present"),
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'submitted', 'auto_submitted', 'graded')",
            name=op.f("ck_assessment_attempts_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_assessment_attempts_student"),
        ),
        sa.ForeignKeyConstraint(
            ["test_id"], ["tests.id"], ondelete="RESTRICT", name=op.f("fk_assessment_attempts_test")
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.id"],
            ondelete="RESTRICT",
            name=op.f("fk_assessment_attempts_quiz"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_attempts")),
        sa.UniqueConstraint(
            "submission_idempotency_key",
            name=op.f("uq_assessment_attempts_submission_idempotency_key"),
        ),
    )
    op.create_index(
        "ix_assessment_attempts_student_started",
        "assessment_attempts",
        ["student_id", "started_at"],
    )

    op.create_table(
        "attempt_answers",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column(
            "response_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_visited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "is_marked_for_review", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("time_spent_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("marks_awarded", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "last_saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["assessment_attempts.id"],
            ondelete="CASCADE",
            name=op.f("fk_attempt_answers_attempt"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_attempt_answers_qv"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attempt_answers")),
        sa.UniqueConstraint("attempt_id", "question_version_id", name="uq_attempt_answers_att_qv"),
    )

    op.create_table(
        "processed_event_ids",
        sa.Column("consumer_name", sa.String(length=80), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["outbox_events.id"],
            ondelete="CASCADE",
            name=op.f("fk_processed_event_ids_outbox"),
        ),
        sa.PrimaryKeyConstraint("consumer_name", "event_id", name=op.f("pk_processed_event_ids")),
    )

    op.create_table(
        "learning_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metrics_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_learning_events_student"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_events")),
    )
    op.create_index(
        "ix_learning_events_student_time", "learning_events", ["student_id", "occurred_at"]
    )

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("scope_key", sa.String(length=120), nullable=False),
        sa.Column(
            "metrics_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_analytics_snapshots_student"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analytics_snapshots")),
        sa.UniqueConstraint(
            "student_id", "scope_type", "scope_key", name="uq_analytics_snap_scope"
        ),
    )

    # Seed Phase 2 RBAC permissions cleanly
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('quiz:create', 'quiz', 'create'),
            ('quiz:attempt', 'quiz', 'attempt'),
            ('assessment:create', 'assessment', 'create'),
            ('assessment:attempt', 'assessment', 'attempt'),
            ('exam_pattern:manage', 'exam_pattern', 'manage'),
            ('analytics:read_own', 'analytics', 'read_own'),
            ('analytics:read_cohort', 'analytics', 'read_cohort')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code = 'student' AND p.code IN ('quiz:create', 'quiz:attempt', 'assessment:attempt', 'analytics:read_own'))
            OR (r.code = 'teacher' AND p.code IN ('quiz:create', 'quiz:attempt', 'assessment:create', 'assessment:attempt', 'analytics:read_cohort'))
            OR (r.code = 'school_admin' AND p.code IN ('assessment:create', 'exam_pattern:manage', 'analytics:read_cohort'))
            OR (r.code = 'content_admin' AND p.code IN ('quiz:create', 'assessment:create', 'exam_pattern:manage', 'analytics:read_cohort'))
            OR (r.code = 'academic_reviewer' AND p.code IN ('analytics:read_cohort'))
            OR (r.code = 'platform_admin' AND p.code IN ('quiz:create', 'quiz:attempt', 'assessment:create', 'assessment:attempt', 'exam_pattern:manage', 'analytics:read_own', 'analytics:read_cohort'))
        )
        ON CONFLICT DO NOTHING;
        """
    )

    # Seed initial configurable versioned exam patterns (editable/replaceable in DB)
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'cbse-2026-v1', 2026, true,
            '{"duration_seconds": 3600, "grace_seconds": 30, "shuffle_questions": false, "shuffle_options": false, "retake_policy": {"max_attempts": null, "cooldown_minutes": 0}, "sections": [{"code": "SEC-A", "name": "Objective & Assertion-Reason", "question_count": 20, "attempt_limit": null, "allowed_question_types": ["mcq_single", "assertion_reason"], "scoring": {"mode": "standard", "correct_marks": 1.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}]}'::jsonb
        FROM exam_tracks WHERE code = 'CBSE_BOARD'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'jee-main-2026-v1', 2026, true,
            '{"duration_seconds": 10800, "grace_seconds": 30, "shuffle_questions": true, "shuffle_options": true, "retake_policy": {"max_attempts": null, "cooldown_minutes": 0}, "sections": [{"code": "SEC-A", "name": "Single Choice (+4/-1)", "question_count": 20, "attempt_limit": null, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}, {"code": "SEC-B", "name": "Numerical Value (+4/-1)", "question_count": 10, "attempt_limit": 5, "allowed_question_types": ["numerical", "integer"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}]}'::jsonb
        FROM exam_tracks WHERE code = 'JEE_MAIN'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'jee-adv-2026-v1', 2026, true,
            '{"duration_seconds": 10800, "grace_seconds": 30, "shuffle_questions": true, "shuffle_options": false, "retake_policy": {"max_attempts": null, "cooldown_minutes": 0}, "sections": [{"code": "SEC-MULTI", "name": "One or More Correct (+4/+3/+2/+1/0/-2)", "question_count": 6, "attempt_limit": null, "allowed_question_types": ["mcq_multiple"], "scoring": {"mode": "partial_subset", "correct_marks": 4.0, "wrong_marks": -2.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 1.0}}, {"code": "SEC-SINGLE", "name": "Single Correct (+3/-1)", "question_count": 6, "attempt_limit": null, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 3.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}]}'::jsonb
        FROM exam_tracks WHERE code = 'JEE_ADVANCED'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'neet-2026-v1', 2026, true,
            '{"duration_seconds": 12000, "grace_seconds": 30, "shuffle_questions": true, "shuffle_options": true, "retake_policy": {"max_attempts": null, "cooldown_minutes": 0}, "sections": [{"code": "SEC-A", "name": "Mandatory (+4/-1)", "question_count": 35, "attempt_limit": null, "allowed_question_types": ["mcq_single", "assertion_reason"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}, {"code": "SEC-B", "name": "Optional Attempt Any 10 of 15 (+4/-1)", "question_count": 15, "attempt_limit": 10, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}]}'::jsonb
        FROM exam_tracks WHERE code = 'NEET'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("analytics_snapshots")
    op.drop_index("ix_learning_events_student_time", table_name="learning_events")
    op.drop_table("learning_events")
    op.drop_table("processed_event_ids")
    op.drop_table("attempt_answers")
    op.drop_index("ix_assessment_attempts_student_started", table_name="assessment_attempts")
    op.drop_table("assessment_attempts")
    op.drop_table("test_questions")
    op.drop_table("test_sections")
    op.drop_table("tests")
    op.drop_table("quiz_questions")
    op.drop_index("ix_quizzes_creator_type", table_name="quizzes")
    op.drop_table("quizzes")
    op.drop_table("exam_patterns")
