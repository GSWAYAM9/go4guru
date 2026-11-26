"""Phase 1 core platform tables: identity, curriculum, content rights, question bank, imports, practice.

Revision ID: 0002_phase1_core
Revises: 0001_phase0_baseline
Create Date: 2026-11-26 21:00:00+05:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase1_core"
down_revision: str | Sequence[str] | None = "0001_phase0_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Identity & RBAC base tables (users -> roles -> permissions)
    # ------------------------------------------------------------------
    op.create_table(
        "users",
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column(
            "status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column("date_of_birth_year", sa.Integer(), nullable=True),
        sa.Column("is_minor", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("mfa_secret", sa.String(length=128), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'pending_parent_consent', 'deleted')",
            name=op.f("ck_users_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
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
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'Asia/Kolkata'"),
            nullable=False,
        ),
        sa.Column(
            "ui_language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "preferred_explanation_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_voice_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_subtitle_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_question_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_answer_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_user_profiles_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_profiles")),
    )

    op.create_table(
        "roles",
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
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False),
        sa.CheckConstraint(
            "code IN ('student', 'parent', 'teacher', 'mentor', 'school_admin', 'content_admin', 'academic_reviewer', 'platform_admin')",
            name=op.f("ck_roles_code_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
    )

    op.create_table(
        "permissions",
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
        sa.Column("code", sa.String(length=96), nullable=False),
        sa.Column("resource", sa.String(length=48), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("code", name=op.f("uq_permissions_code")),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            ondelete="CASCADE",
            name=op.f("fk_role_permissions_role_id_roles"),
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
            name=op.f("fk_role_permissions_permission_id_permissions"),
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_role_permissions")),
    )

    op.create_table(
        "user_roles",
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
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("granted_by", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_user_roles_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], ondelete="CASCADE", name=op.f("fk_user_roles_role_id_roles")
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_user_roles_granted_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_roles")),
    )
    op.create_index("ix_user_roles_user_active", "user_roles", ["user_id", "revoked_at"])

    op.create_table(
        "sessions",
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
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_family_id", sa.Uuid(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
        sa.Column("mfa_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_sessions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_sessions_refresh_token_hash")),
    )
    op.create_index("ix_sessions_user_family", "sessions", ["user_id", "token_family_id"])

    # ------------------------------------------------------------------
    # 2. Versioned 11-Level Curriculum Hierarchy
    # ------------------------------------------------------------------
    op.create_table(
        "boards",
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
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("country", sa.String(length=64), server_default=sa.text("'IN'"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_boards")),
        sa.UniqueConstraint("code", name=op.f("uq_boards_code")),
    )

    op.create_table(
        "academic_sessions",
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
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("ends_on > starts_on", name=op.f("ck_academic_sessions_dates_valid")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_sessions")),
        sa.UniqueConstraint("code", name=op.f("uq_academic_sessions_code")),
    )

    op.create_table(
        "grades",
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
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.CheckConstraint("number >= 6 AND number <= 12", name=op.f("ck_grades_range_6_12")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grades")),
        sa.UniqueConstraint("number", name=op.f("uq_grades_number")),
    )

    op.create_table(
        "curriculum_versions",
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
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("academic_session_id", sa.Uuid(), nullable=False),
        sa.Column("version_tag", sa.String(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name=op.f("ck_curriculum_versions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["board_id"],
            ["boards.id"],
            ondelete="RESTRICT",
            name=op.f("fk_curriculum_versions_board_id_boards"),
        ),
        sa.ForeignKeyConstraint(
            ["academic_session_id"],
            ["academic_sessions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_curriculum_versions_academic_session_id_academic_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_versions")),
        sa.UniqueConstraint(
            "board_id",
            "academic_session_id",
            "version_tag",
            name="uq_curriculum_versions_board_session_tag",
        ),
    )

    op.create_table(
        "student_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
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
        sa.Column("board_id", sa.Uuid(), nullable=True),
        sa.Column("academic_session_id", sa.Uuid(), nullable=True),
        sa.Column("grade_id", sa.Uuid(), nullable=True),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "primary_exam_target",
            sa.String(length=32),
            server_default=sa.text("'cbse_board'"),
            nullable=False,
        ),
        sa.Column(
            "daily_study_minutes_target", sa.Integer(), server_default=sa.text("60"), nullable=False
        ),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "primary_exam_target IN ('cbse_board', 'jee_main', 'jee_advanced', 'neet', 'foundation')",
            name=op.f("ck_student_profiles_exam_target_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_student_profiles_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["board_id"],
            ["boards.id"],
            ondelete="SET NULL",
            name=op.f("fk_student_profiles_board_id_boards"),
        ),
        sa.ForeignKeyConstraint(
            ["academic_session_id"],
            ["academic_sessions.id"],
            ondelete="SET NULL",
            name=op.f("fk_student_profiles_academic_session_id_academic_sessions"),
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["grades.id"],
            ondelete="SET NULL",
            name=op.f("fk_student_profiles_grade_id_grades"),
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            ondelete="SET NULL",
            name=op.f("fk_student_profiles_curriculum_version_id_curriculum_versions"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_student_profiles")),
    )

    op.create_table(
        "subjects",
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
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("discipline", sa.String(length=48), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
        sa.UniqueConstraint("code", name=op.f("uq_subjects_code")),
    )

    op.create_table(
        "books",
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
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("grade_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("publisher", sa.String(length=120), nullable=False),
        sa.Column("official_source_url", sa.String(length=512), nullable=True),
        sa.Column("edition_year", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            ondelete="CASCADE",
            name=op.f("fk_books_curriculum_version_id_curriculum_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"], ["grades.id"], ondelete="RESTRICT", name=op.f("fk_books_grade_id_grades")
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="RESTRICT",
            name=op.f("fk_books_subject_id_subjects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_books")),
    )

    op.create_table(
        "chapters",
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
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], ondelete="CASCADE", name=op.f("fk_chapters_book_id_books")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chapters")),
        sa.UniqueConstraint("book_id", "code", name="uq_chapters_book_code"),
    )

    op.create_table(
        "sections",
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
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="CASCADE",
            name=op.f("fk_sections_chapter_id_chapters"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sections")),
    )

    op.create_table(
        "topics",
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
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="CASCADE",
            name=op.f("fk_topics_chapter_id_chapters"),
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            ondelete="SET NULL",
            name=op.f("fk_topics_section_id_sections"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
    )

    op.create_table(
        "concepts",
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
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("difficulty_baseline", sa.Integer(), server_default=sa.text("2"), nullable=False),
        sa.Column(
            "skill_tags_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "exam_tags_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "difficulty_baseline >= 1 AND difficulty_baseline <= 5",
            name=op.f("ck_concepts_difficulty_range"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="CASCADE",
            name=op.f("fk_concepts_topic_id_topics"),
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            ondelete="CASCADE",
            name=op.f("fk_concepts_curriculum_version_id_curriculum_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_concepts")),
        sa.UniqueConstraint("curriculum_version_id", "code", name="uq_concepts_version_code"),
    )

    op.create_table(
        "learning_objectives",
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
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("bloom_level", sa.String(length=32), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "bloom_level IN ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create')",
            name=op.f("ck_learning_objectives_bloom_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_learning_objectives_concept_id_concepts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_objectives")),
    )

    op.create_table(
        "concept_prerequisites",
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("prerequisite_concept_id", sa.Uuid(), nullable=False),
        sa.Column(
            "strength", sa.String(length=24), server_default=sa.text("'required'"), nullable=False
        ),
        sa.CheckConstraint(
            "concept_id <> prerequisite_concept_id",
            name=op.f("ck_concept_prerequisites_no_self_loop"),
        ),
        sa.CheckConstraint(
            "strength IN ('required', 'recommended')",
            name=op.f("ck_concept_prerequisites_strength_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_concept_prerequisites_concept_id_concepts"),
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_concept_prerequisites_prereq_id_concepts"),
        ),
        sa.PrimaryKeyConstraint(
            "concept_id", "prerequisite_concept_id", name=op.f("pk_concept_prerequisites")
        ),
    )

    op.create_table(
        "exam_tracks",
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
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_tracks")),
        sa.UniqueConstraint("code", name=op.f("uq_exam_tracks_code")),
    )

    op.create_table(
        "exam_concept_mappings",
        sa.Column("exam_track_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("weightage_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "priority_tier", sa.String(length=16), server_default=sa.text("'core'"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["exam_track_id"],
            ["exam_tracks.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_concept_mappings_track"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
            name=op.f("fk_exam_concept_mappings_concept"),
        ),
        sa.PrimaryKeyConstraint(
            "exam_track_id", "concept_id", name=op.f("pk_exam_concept_mappings")
        ),
    )

    # ------------------------------------------------------------------
    # 3. Content Sources & Licenses (Quarantine & Rights Enforcement)
    # ------------------------------------------------------------------
    op.create_table(
        "content_sources",
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
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("owner_name", sa.String(length=160), nullable=False),
        sa.Column("source_category", sa.String(length=40), nullable=False),
        sa.Column("official_url", sa.String(length=512), nullable=True),
        sa.CheckConstraint(
            "source_category IN ('original_platform', 'official_link', 'licensed_partner', 'ai_generated', 'teacher_created', 'student_created', 'quarantined_third_party')",
            name=op.f("ck_content_sources_category_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_content_sources_name")),
    )

    op.create_table(
        "content_licenses",
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
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("license_name", sa.String(length=160), nullable=False),
        sa.Column(
            "commercial_use_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "distribution_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("hosting_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "embedding_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "attribution_required", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("attribution_text", sa.String(length=512), nullable=True),
        sa.Column(
            "territory", sa.String(length=64), server_default=sa.text("'IN'"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "legal_review_status",
            sa.String(length=24),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "legal_review_status IN ('pending', 'approved', 'rejected', 'quarantined')",
            name=op.f("ck_content_licenses_review_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["content_sources.id"],
            ondelete="CASCADE",
            name=op.f("fk_content_licenses_source_id_content_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_content_licenses_reviewed_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_licenses")),
    )

    # ------------------------------------------------------------------
    # 4. Canonical Question Bank & Excel/CSV Import Staging
    # ------------------------------------------------------------------
    op.create_table(
        "import_batches",
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
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(length=256), nullable=False),
        sa.Column("file_format", sa.String(length=16), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'uploaded'"), nullable=False
        ),
        sa.Column(
            "detected_sheets_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("selected_sheet", sa.String(length=128), nullable=True),
        sa.Column(
            "column_mapping_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("total_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "report_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "file_format IN ('xlsx', 'csv')", name=op.f("ck_import_batches_format_valid")
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'mapped', 'validated', 'preview_ready', 'committed', 'failed', 'rolled_back')",
            name=op.f("ck_import_batches_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name=op.f("fk_import_batches_uploaded_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
    )
    op.create_index("ix_import_batches_sha256", "import_batches", ["file_sha256"])

    op.create_table(
        "questions",
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("canonical_hash", sa.String(length=64), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'DRAFT'"), nullable=False
        ),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'VALIDATION', 'REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED')",
            name=op.f("ck_questions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
            name=op.f("fk_questions_import_batch_id_import_batches"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name=op.f("fk_questions_created_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
    )
    op.create_index("ix_questions_canonical_hash", "questions", ["canonical_hash"])
    op.create_index("ix_questions_status", "questions", ["status"])

    op.create_table(
        "question_versions",
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
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("grade_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("learning_objective_id", sa.Uuid(), nullable=True),
        sa.Column("stem_markdown", sa.Text(), nullable=False),
        sa.Column("passage_markdown", sa.Text(), nullable=True),
        sa.Column(
            "media_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "answer_schema_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "correct_answer_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "difficulty", sa.String(length=16), server_default=sa.text("'medium'"), nullable=False
        ),
        sa.Column(
            "default_marks", sa.Numeric(6, 2), server_default=sa.text("4.00"), nullable=False
        ),
        sa.Column(
            "default_negative_marks",
            sa.Numeric(6, 2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column("estimated_seconds", sa.Integer(), server_default=sa.text("60"), nullable=False),
        sa.Column("cognitive_level", sa.String(length=32), nullable=True),
        sa.Column("competency_tag", sa.String(length=64), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "ai_metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard', 'olympiad')",
            name=op.f("ck_question_versions_difficulty_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_versions_question_id_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_versions_cv"),
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["grades.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_versions_grade_id_grades"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_versions_subject_id_subjects"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_versions_chapter_id_chapters"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="SET NULL",
            name=op.f("fk_question_versions_topic_id_topics"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="SET NULL",
            name=op.f("fk_question_versions_concept_id_concepts"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_objective_id"],
            ["learning_objectives.id"],
            ondelete="SET NULL",
            name=op.f("fk_question_versions_lo"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_versions")),
        sa.UniqueConstraint(
            "question_id", "version_no", name="uq_question_versions_question_version"
        ),
    )
    op.create_index(
        "ix_question_versions_curriculum_facets",
        "question_versions",
        ["grade_id", "subject_id", "chapter_id", "topic_id", "concept_id"],
    )

    op.create_table(
        "question_options",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("option_key", sa.String(length=16), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column(
            "media_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("match_pair_key", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_options_qv"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_options")),
        sa.UniqueConstraint(
            "question_version_id", "option_key", name="uq_question_options_version_key"
        ),
    )

    op.create_table(
        "question_solutions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "solution_type",
            sa.String(length=16),
            server_default=sa.text("'primary'"),
            nullable=False,
        ),
        sa.Column("explanation_markdown", sa.Text(), nullable=False),
        sa.Column(
            "steps_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("common_mistakes_markdown", sa.Text(), nullable=True),
        sa.Column(
            "misconception_tags_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "rubric_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "solution_type IN ('primary', 'alternative')",
            name=op.f("ck_question_solutions_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_solutions_qv"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_solutions")),
    )

    op.create_table(
        "question_hints",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("hint_level", sa.Integer(), nullable=False),
        sa.Column("hint_markdown", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "hint_level >= 1 AND hint_level <= 3", name=op.f("ck_question_hints_level_valid")
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_hints_qv"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_hints")),
        sa.UniqueConstraint(
            "question_version_id", "hint_level", name="uq_question_hints_version_level"
        ),
    )

    op.create_table(
        "question_provenance",
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("license_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("is_pyq", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("exam_name", sa.String(length=120), nullable=True),
        sa.Column("exam_year", sa.Integer(), nullable=True),
        sa.Column("exam_session", sa.String(length=64), nullable=True),
        sa.Column("exam_shift", sa.String(length=64), nullable=True),
        sa.Column("paper_code", sa.String(length=64), nullable=True),
        sa.Column("question_number", sa.String(length=32), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(length=24),
            server_default=sa.text("'unverified'"),
            nullable=False,
        ),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_type IN ('original', 'licensed', 'verified_pyq', 'ai_generated', 'teacher_created')",
            name=op.f("ck_question_provenance_source_type_valid"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'disputed')",
            name=op.f("ck_question_provenance_verification_valid"),
        ),
        sa.CheckConstraint(
            "NOT (is_pyq = true AND (verification_status <> 'verified' OR exam_name IS NULL OR exam_year IS NULL OR verified_by IS NULL))",
            name=op.f("ck_question_provenance_pyq_requires_verified_metadata"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_provenance_question_id_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["content_sources.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_provenance_source_id_content_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["license_id"],
            ["content_licenses.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_provenance_license_id_content_licenses"),
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_question_provenance_verified_by_users"),
        ),
        sa.PrimaryKeyConstraint("question_id", name=op.f("pk_question_provenance")),
    )

    op.create_table(
        "question_reviews",
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
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected', 'changes_requested')",
            name=op.f("ck_question_reviews_decision_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_reviews_qv"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_reviews_reviewer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_reviews")),
    )

    op.create_table(
        "import_staging_rows",
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
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_name", sa.String(length=128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "normalized_payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("row_fingerprint_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "validation_status",
            sa.String(length=24),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "errors_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_question_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'warning', 'error', 'duplicate', 'imported', 'rolled_back')",
            name=op.f("ck_import_staging_rows_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="CASCADE",
            name=op.f("fk_import_staging_rows_batch"),
        ),
        sa.ForeignKeyConstraint(
            ["created_question_id"],
            ["questions.id"],
            ondelete="SET NULL",
            name=op.f("fk_import_staging_rows_question"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_staging_rows")),
    )
    op.create_index(
        "ix_import_staging_rows_batch_status",
        "import_staging_rows",
        ["import_batch_id", "validation_status"],
    )

    # ------------------------------------------------------------------
    # 5. Practice Engine, Attempts, Notes & Bookmarks
    # ------------------------------------------------------------------
    op.create_table(
        "practice_sessions",
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
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column(
            "mode",
            sa.String(length=32),
            server_default=sa.text("'guided_practice'"),
            nullable=False,
        ),
        sa.Column(
            "question_ids_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "hints_revealed_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_practice_sessions_student_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="SET NULL",
            name=op.f("fk_practice_sessions_subject_id_subjects"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="SET NULL",
            name=op.f("fk_practice_sessions_chapter_id_chapters"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="SET NULL",
            name=op.f("fk_practice_sessions_topic_id_topics"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="SET NULL",
            name=op.f("fk_practice_sessions_concept_id_concepts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_sessions")),
    )
    op.create_index(
        "ix_practice_sessions_student", "practice_sessions", ["student_id", "started_at"]
    )

    op.create_table(
        "question_attempts",
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
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("practice_session_id", sa.Uuid(), nullable=True),
        sa.Column(
            "response_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column(
            "score_awarded", sa.Numeric(6, 2), server_default=sa.text("0.00"), nullable=False
        ),
        sa.Column("hints_used_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_attempts_student_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_attempts_question_id_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            ondelete="RESTRICT",
            name=op.f("fk_question_attempts_qv"),
        ),
        sa.ForeignKeyConstraint(
            ["practice_session_id"],
            ["practice_sessions.id"],
            ondelete="SET NULL",
            name=op.f("fk_question_attempts_ps"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_attempts")),
    )
    op.create_index(
        "ix_question_attempts_student_time", "question_attempts", ["student_id", "attempted_at"]
    )

    op.create_table(
        "student_notes",
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
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_student_notes_student_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="SET NULL",
            name=op.f("fk_student_notes_concept_id_concepts"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="SET NULL",
            name=op.f("fk_student_notes_question_id_questions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_notes")),
    )
    op.create_index("ix_student_notes_student", "student_notes", ["student_id", "updated_at"])

    op.create_table(
        "saved_questions",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
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
        sa.Column(
            "folder_name", sa.String(length=80), server_default=sa.text("'General'"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_saved_questions_student_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
            name=op.f("fk_saved_questions_question_id_questions"),
        ),
        sa.PrimaryKeyConstraint("student_id", "question_id", name=op.f("pk_saved_questions")),
    )

    # ------------------------------------------------------------------
    # 6. Structural Reference Seed Data (Roles, Permissions, Grades 6..12, Tracks)
    # Zero fabricated curriculum chapters or fake PYQ items.
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO roles (code, description) VALUES
            ('student', 'Learner accessing published curriculum, practice, notes, and personal dashboard'),
            ('parent', 'Guardian with privacy-preserving learning summary access in later phase'),
            ('teacher', 'Educator viewing curriculum, verified questions, and class workflows'),
            ('mentor', 'Academic mentor tracking assigned students'),
            ('school_admin', 'Multi-tenant school administrator (MFA required)'),
            ('content_admin', 'Curriculum, content rights, and Excel import administrator (MFA required)'),
            ('academic_reviewer', 'Academic QA reviewer approving questions and PYQ provenance (MFA required)'),
            ('platform_admin', 'Global platform administrator and role/audit manager (MFA required)')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('curriculum:read', 'curriculum', 'read'),
            ('curriculum:write', 'curriculum', 'write'),
            ('curriculum:publish', 'curriculum', 'publish'),
            ('rights:read', 'rights', 'read'),
            ('rights:manage', 'rights', 'manage'),
            ('question:read_redacted', 'question', 'read_redacted'),
            ('question:read_full', 'question', 'read_full'),
            ('question:write', 'question', 'write'),
            ('question:review', 'question', 'review'),
            ('question:publish', 'question', 'publish'),
            ('import:manage', 'import', 'manage'),
            ('practice:use', 'practice', 'use'),
            ('notes:manage_own', 'notes', 'manage_own'),
            ('dashboard:student_own', 'dashboard', 'student_own'),
            ('admin:users_manage', 'admin', 'users_manage'),
            ('admin:audit_read', 'admin', 'audit_read')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code = 'student' AND p.code IN ('curriculum:read', 'question:read_redacted', 'practice:use', 'notes:manage_own', 'dashboard:student_own'))
            OR (r.code = 'parent' AND p.code IN ('curriculum:read'))
            OR (r.code = 'teacher' AND p.code IN ('curriculum:read', 'question:read_full', 'rights:read'))
            OR (r.code = 'mentor' AND p.code IN ('curriculum:read', 'question:read_redacted'))
            OR (r.code = 'school_admin' AND p.code IN ('curriculum:read', 'question:read_redacted'))
            OR (r.code = 'content_admin' AND p.code IN ('curriculum:read', 'curriculum:write', 'curriculum:publish', 'rights:read', 'rights:manage', 'question:read_full', 'question:write', 'import:manage'))
            OR (r.code = 'academic_reviewer' AND p.code IN ('curriculum:read', 'rights:read', 'question:read_full', 'question:review', 'question:publish', 'import:manage'))
            OR (r.code = 'platform_admin')
        )
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO grades (number, label) VALUES
            (6, 'Class 6'),
            (7, 'Class 7'),
            (8, 'Class 8'),
            (9, 'Class 9'),
            (10, 'Class 10'),
            (11, 'Class 11'),
            (12, 'Class 12')
        ON CONFLICT (number) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO exam_tracks (code, name) VALUES
            ('CBSE_BOARD', 'CBSE Board Examination'),
            ('JEE_MAIN', 'JEE Main'),
            ('JEE_ADVANCED', 'JEE Advanced'),
            ('NEET', 'NEET UG')
        ON CONFLICT (code) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("saved_questions")
    op.drop_index("ix_student_notes_student", table_name="student_notes")
    op.drop_table("student_notes")
    op.drop_index("ix_question_attempts_student_time", table_name="question_attempts")
    op.drop_table("question_attempts")
    op.drop_index("ix_practice_sessions_student", table_name="practice_sessions")
    op.drop_table("practice_sessions")
    op.drop_index("ix_import_staging_rows_batch_status", table_name="import_staging_rows")
    op.drop_table("import_staging_rows")
    op.drop_table("question_reviews")
    op.drop_table("question_provenance")
    op.drop_table("question_hints")
    op.drop_table("question_solutions")
    op.drop_table("question_options")
    op.drop_index("ix_question_versions_curriculum_facets", table_name="question_versions")
    op.drop_table("question_versions")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_index("ix_questions_canonical_hash", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_import_batches_sha256", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_table("content_licenses")
    op.drop_table("content_sources")
    op.drop_table("exam_concept_mappings")
    op.drop_table("exam_tracks")
    op.drop_table("concept_prerequisites")
    op.drop_table("learning_objectives")
    op.drop_table("concepts")
    op.drop_table("topics")
    op.drop_table("sections")
    op.drop_table("chapters")
    op.drop_table("books")
    op.drop_table("subjects")
    op.drop_table("student_profiles")
    op.drop_table("curriculum_versions")
    op.drop_table("grades")
    op.drop_table("academic_sessions")
    op.drop_table("boards")
    op.drop_index("ix_sessions_user_family", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_user_roles_user_active", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("user_profiles")
    op.drop_table("users")
