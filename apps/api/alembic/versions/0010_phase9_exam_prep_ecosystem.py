"""Phase 9: Examination Preparation Ecosystem (CBSE Board, JEE Main, JEE Advanced, NEET).

Revision ID: 0010_phase9_exam_prep_ecosystem
Revises: 0009_phase8_multitenant_institutions
Create Date: 2026-11-26 14:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_phase9_exam_prep_ecosystem"
down_revision = "0009_phase8_multitenant_institutions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_syllabus_chapters",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
        sa.Column("pattern_version_label", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column(
            "weightage_pct",
            sa.Numeric(5, 2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "expected_questions",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "priority_tier",
            sa.String(length=24),
            server_default=sa.text("'core'"),
            nullable=False,
        ),
        sa.Column(
            "syllabus_status",
            sa.String(length=24),
            server_default=sa.text("'included'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "audit_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("audited_by", sa.Uuid(), nullable=True),
        sa.Column("audited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["exam_track_id"],
            ["exam_tracks.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_syllabus_chapters_exam_track"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_syllabus_chapters_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_syllabus_chapters_chapter"),
        ),
        sa.CheckConstraint(
            "priority_tier IN ('high_yield', 'core', 'optional')",
            name="ck_exam_syllabus_priority_tier",
        ),
        sa.CheckConstraint(
            "syllabus_status IN ('included', 'reduced', 'excluded')",
            name="ck_exam_syllabus_status",
        ),
        sa.CheckConstraint(
            "weightage_pct >= 0 AND weightage_pct <= 100",
            name="ck_exam_syllabus_weightage_bounds",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_syllabus_chapters")),
        sa.UniqueConstraint(
            "exam_track_id",
            "pattern_version_label",
            "chapter_id",
            name="uq_exam_syllabus_track_ver_chapter",
        ),
    )
    op.create_index(
        "ix_exam_syllabus_track_ver",
        "exam_syllabus_chapters",
        ["exam_track_id", "pattern_version_label"],
    )

    op.create_table(
        "exam_formula_sheets",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("formula_latex", sa.Text(), nullable=False),
        sa.Column(
            "variables_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("when_to_use", sa.Text(), nullable=False),
        sa.Column("common_pitfall", sa.Text(), nullable=True),
        sa.Column(
            "difficulty",
            sa.String(length=16),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),
        sa.Column(
            "is_high_yield",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("license_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'PUBLISHED'"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["exam_track_id"],
            ["exam_tracks.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_formula_sheets_exam_track"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_formula_sheets_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_formula_sheets_chapter"),
        ),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_exam_formula_difficulty",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name="ck_exam_formula_status",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_formula_sheets")),
    )
    op.create_index(
        "ix_exam_formula_track_subject_chap",
        "exam_formula_sheets",
        ["exam_track_id", "subject_id", "chapter_id"],
    )

    op.create_table(
        "exam_revision_plans",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
        sa.Column("exam_track_id", sa.Uuid(), nullable=False),
        sa.Column("exam_pattern_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_exam_date", sa.Date(), nullable=False),
        sa.Column(
            "daily_minutes",
            sa.Integer(),
            server_default=sa.text("90"),
            nullable=False,
        ),
        sa.Column(
            "focus_chapters_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "schedule_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_revision_plans_student"),
        ),
        sa.ForeignKeyConstraint(
            ["exam_track_id"],
            ["exam_tracks.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_revision_plans_exam_track"),
        ),
        sa.ForeignKeyConstraint(
            ["exam_pattern_id"],
            ["exam_patterns.id"],
            ondelete="SET NULL",
            name=op.f("fk_exam_revision_plans_pattern"),
        ),
        sa.CheckConstraint(
            "daily_minutes >= 15 AND daily_minutes <= 600",
            name="ck_exam_revision_plans_daily_minutes",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_exam_revision_plans_status",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_revision_plans")),
    )
    op.create_index(
        "ix_exam_revision_plans_student_track",
        "exam_revision_plans",
        ["student_id", "exam_track_id"],
    )

    # Ensure all 4 canonical exam tracks exist idempotently
    op.execute(
        """
        INSERT INTO exam_tracks (code, name) VALUES
            ('CBSE_BOARD', 'CBSE Board Examination'),
            ('JEE_MAIN', 'JEE Main'),
            ('JEE_ADVANCED', 'JEE Advanced'),
            ('NEET', 'NEET-UG')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # Seed Phase 9 versioned blueprint patterns (preserving existing v1 patterns)
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'cbse-board-2026-blueprint-v2', 2026, true,
            '{
              "duration_seconds": 10800,
              "grace_seconds": 60,
              "shuffle_questions": false,
              "shuffle_options": false,
              "retake_policy": {"max_attempts": null, "cooldown_minutes": 0},
              "sections": [
                {"code": "SEC-A", "name": "MCQ & Assertion-Reason (1 mark, no negative)", "question_count": 20, "attempt_limit": null, "allowed_question_types": ["mcq_single", "assertion_reason"], "scoring": {"mode": "standard", "correct_marks": 1.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "SEC-B", "name": "Very Short Answer (2 marks, rubric)", "question_count": 5, "attempt_limit": null, "allowed_question_types": ["short_answer"], "scoring": {"mode": "standard", "correct_marks": 2.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "SEC-C", "name": "Short Answer (3 marks, rubric)", "question_count": 6, "attempt_limit": null, "allowed_question_types": ["short_answer"], "scoring": {"mode": "standard", "correct_marks": 3.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "SEC-D", "name": "Long Answer (5 marks, rubric)", "question_count": 4, "attempt_limit": null, "allowed_question_types": ["long_answer"], "scoring": {"mode": "standard", "correct_marks": 5.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "SEC-E", "name": "Case-Based Competency (4 marks)", "question_count": 3, "attempt_limit": null, "allowed_question_types": ["case_study", "mcq_single"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}
              ]
            }'::jsonb
        FROM exam_tracks WHERE code = 'CBSE_BOARD'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'jee-main-2026-nta-v2', 2026, true,
            '{
              "duration_seconds": 10800,
              "grace_seconds": 30,
              "shuffle_questions": true,
              "shuffle_options": true,
              "retake_policy": {"max_attempts": null, "cooldown_minutes": 0},
              "sections": [
                {"code": "PHY-A", "name": "Physics MCQ (+4/-1)", "question_count": 20, "attempt_limit": null, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "PHY-B", "name": "Physics Numerical (+4/-1)", "question_count": 5, "attempt_limit": 5, "allowed_question_types": ["numerical", "integer"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "CHEM-A", "name": "Chemistry MCQ (+4/-1)", "question_count": 20, "attempt_limit": null, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "CHEM-B", "name": "Chemistry Numerical (+4/-1)", "question_count": 5, "attempt_limit": 5, "allowed_question_types": ["numerical", "integer"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "MATH-A", "name": "Mathematics MCQ (+4/-1)", "question_count": 20, "attempt_limit": null, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "MATH-B", "name": "Mathematics Numerical (+4/-1)", "question_count": 5, "attempt_limit": 5, "allowed_question_types": ["numerical", "integer"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}
              ]
            }'::jsonb
        FROM exam_tracks WHERE code = 'JEE_MAIN'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'jee-adv-2026-p1-v2', 2026, true,
            '{
              "duration_seconds": 10800,
              "grace_seconds": 30,
              "shuffle_questions": true,
              "shuffle_options": false,
              "retake_policy": {"max_attempts": null, "cooldown_minutes": 0},
              "sections": [
                {"code": "SEC-1", "name": "Single Correct (+3/-1)", "question_count": 12, "attempt_limit": null, "allowed_question_types": ["mcq_single"], "scoring": {"mode": "standard", "correct_marks": 3.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "SEC-2", "name": "One or More Correct (+4/+3/+2/+1/0/-2)", "question_count": 9, "attempt_limit": null, "allowed_question_types": ["mcq_multiple"], "scoring": {"mode": "jee_adv_partial", "correct_marks": 4.0, "wrong_marks": -2.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 1.0}},
                {"code": "SEC-3", "name": "Non-Negative Integer / Numerical (+4/0)", "question_count": 18, "attempt_limit": null, "allowed_question_types": ["integer", "numerical"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": 0.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "SEC-4", "name": "Match List (+3/-1)", "question_count": 12, "attempt_limit": null, "allowed_question_types": ["match_following", "mcq_single"], "scoring": {"mode": "standard", "correct_marks": 3.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}
              ]
            }'::jsonb
        FROM exam_tracks WHERE code = 'JEE_ADVANCED'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_patterns (exam_track_id, version_label, effective_year, is_active, rules_jsonb)
        SELECT id, 'neet-ug-2026-nta-v2', 2026, true,
            '{
              "duration_seconds": 10800,
              "grace_seconds": 30,
              "shuffle_questions": true,
              "shuffle_options": true,
              "retake_policy": {"max_attempts": null, "cooldown_minutes": 0},
              "sections": [
                {"code": "PHY", "name": "Physics Mandatory (45 Q, +4/-1)", "question_count": 45, "attempt_limit": null, "allowed_question_types": ["mcq_single", "assertion_reason"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "CHEM", "name": "Chemistry Mandatory (45 Q, +4/-1)", "question_count": 45, "attempt_limit": null, "allowed_question_types": ["mcq_single", "assertion_reason"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}},
                {"code": "BIO", "name": "Biology (Botany + Zoology, 90 Q, +4/-1)", "question_count": 90, "attempt_limit": null, "allowed_question_types": ["mcq_single", "assertion_reason", "match_following"], "scoring": {"mode": "standard", "correct_marks": 4.0, "wrong_marks": -1.0, "unanswered_marks": 0.0, "partial_credit_per_correct_option": 0.0}}
              ]
            }'::jsonb
        FROM exam_tracks WHERE code = 'NEET'
        ON CONFLICT DO NOTHING;
        """
    )

    # Seed Phase 9 RBAC permissions
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('exam_prep:read', 'exam_prep', 'read'),
            ('exam_prep:manage', 'exam_prep', 'manage')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code IN ('student', 'teacher', 'mentor', 'school_admin', 'content_admin', 'academic_reviewer', 'platform_admin') AND p.code = 'exam_prep:read')
            OR (r.code IN ('school_admin', 'content_admin', 'academic_reviewer', 'platform_admin') AND p.code = 'exam_prep:manage')
        )
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_exam_revision_plans_student_track", table_name="exam_revision_plans")
    op.drop_table("exam_revision_plans")
    op.drop_index("ix_exam_formula_track_subject_chap", table_name="exam_formula_sheets")
    op.drop_table("exam_formula_sheets")
    op.drop_index("ix_exam_syllabus_track_ver", table_name="exam_syllabus_chapters")
    op.drop_table("exam_syllabus_chapters")
