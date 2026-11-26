"""Phase 5 Adaptive Mastery, Misconceptions, Learning Paths, Spaced Repetition & Notifications.

Revision ID: 0006_phase5_adaptive_revision
Revises: 0005_phase4_classroom
Create Date: 2026-11-27 01:05:00+05:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase5_adaptive_revision"
down_revision: str | Sequence[str] | None = "0005_phase4_classroom"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_concept_mastery",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column(
            "mastery_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "retention_score",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("1.00"),
            nullable=False,
        ),
        sa.Column(
            "independent_solve_ratio",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "transfer_score",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "improvement_slope",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.50"),
            nullable=False,
        ),
        sa.Column(
            "difficulty_weighted_accuracy",
            sa.Numeric(precision=4, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column("band", sa.String(length=24), server_default=sa.text("'novice'"), nullable=False),
        sa.Column("attempts_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "mastery_breakdown_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_summary_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_scm_student"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_scm_concept"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_concept_mastery")),
        sa.UniqueConstraint("student_id", "concept_id", name="uq_scm_student_concept"),
    )
    op.create_index(
        "ix_scm_student_score",
        "student_concept_mastery",
        ["student_id", "mastery_score"],
    )

    op.create_table(
        "student_misconceptions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("misconception_code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity", sa.String(length=16), server_default=sa.text("'medium'"), nullable=False
        ),
        sa.Column("occurrence_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "last_observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name=op.f("ck_misconceptions_severity"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_sm_student"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_sm_concept"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_misconceptions")),
    )
    op.create_index(
        "ix_sm_student_concept",
        "student_misconceptions",
        ["student_id", "concept_id", "resolved_at"],
    )

    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("goal_exam_track", sa.String(length=64), nullable=True),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column(
            "summary_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_lp_student")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_paths")),
    )

    op.create_table(
        "learning_path_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("priority_score", sa.Float(), server_default=sa.text("50.0"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column(
            "target_metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["learning_path_id"],
            ["learning_paths.id"],
            ondelete="CASCADE",
            name=op.f("fk_lpi_path"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_lpi_concept"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_path_items")),
    )

    op.create_table(
        "flashcards",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "card_type", sa.String(length=32), server_default=sa.text("'concept'"), nullable=False
        ),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("source_question_id", sa.Uuid(), nullable=True),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column("front_markdown", sa.Text(), nullable=False),
        sa.Column("back_markdown", sa.Text(), nullable=False),
        sa.Column("hint_markdown", sa.Text(), nullable=True),
        sa.Column(
            "tags_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
        sa.CheckConstraint(
            "card_type IN ('concept', 'formula', 'vocabulary', 'missed_question')",
            name=op.f("ck_flashcards_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_flashcards_owner")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flashcards")),
    )
    op.create_index("ix_flashcards_owner_type", "flashcards", ["owner_user_id", "card_type"])

    op.create_table(
        "student_flashcards",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("flashcard_id", sa.Uuid(), nullable=False),
        sa.Column(
            "due_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("interval_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ease_factor", sa.Float(), server_default=sa.text("2.5"), nullable=False),
        sa.Column("repetitions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lapse_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_quality", sa.Integer(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_sf_student")
        ),
        sa.ForeignKeyConstraint(
            ["flashcard_id"], ["flashcards.id"], ondelete="CASCADE", name=op.f("fk_sf_card")
        ),
        sa.PrimaryKeyConstraint("student_id", "flashcard_id", name=op.f("pk_student_flashcards")),
    )
    op.create_index("ix_sf_student_due", "student_flashcards", ["student_id", "due_at"])

    op.create_table(
        "flashcard_reviews",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("flashcard_id", sa.Uuid(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("response_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("previous_interval_days", sa.Integer(), nullable=False),
        sa.Column("new_interval_days", sa.Integer(), nullable=False),
        sa.Column("previous_ease", sa.Float(), nullable=False),
        sa.Column("new_ease", sa.Float(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quality >= 0 AND quality <= 5", name=op.f("ck_fc_reviews_quality")),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_fcr_student")
        ),
        sa.ForeignKeyConstraint(
            ["flashcard_id"], ["flashcards.id"], ondelete="CASCADE", name=op.f("fk_fcr_card")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flashcard_reviews")),
    )

    op.create_table(
        "study_plans",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column(
            "daily_minutes_budget", sa.Integer(), server_default=sa.text("45"), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False
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
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_sp_student")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plans")),
    )

    op.create_table(
        "study_plan_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("study_plan_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("flashcard_id", sa.Uuid(), nullable=True),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), server_default=sa.text("15"), nullable=False),
        sa.Column("priority_score", sa.Float(), server_default=sa.text("50.0"), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["study_plan_id"], ["study_plans.id"], ondelete="CASCADE", name=op.f("fk_spi_plan")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plan_items")),
    )

    op.create_table(
        "student_notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(length=200), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_sn_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_notifications")),
    )
    op.create_index(
        "ix_sn_user_read", "student_notifications", ["user_id", "is_read", "created_at"]
    )

    # Seed Phase 5 RBAC Permissions & Roles
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('learning:adaptive_read', 'learning', 'adaptive_read'),
            ('revision:manage', 'revision', 'manage'),
            ('notifications:read_own', 'notifications', 'read_own')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code = 'student' AND p.code IN ('learning:adaptive_read', 'revision:manage', 'notifications:read_own'))
            OR (r.code IN ('teacher', 'mentor', 'school_admin', 'platform_admin') AND p.code IN ('learning:adaptive_read', 'revision:manage', 'notifications:read_own'))
        )
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("student_notifications")
    op.drop_table("study_plan_items")
    op.drop_table("study_plans")
    op.drop_table("flashcard_reviews")
    op.drop_table("student_flashcards")
    op.drop_table("flashcards")
    op.drop_table("learning_path_items")
    op.drop_table("learning_paths")
    op.drop_table("student_misconceptions")
    op.drop_table("student_concept_mastery")
