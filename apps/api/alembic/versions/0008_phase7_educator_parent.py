"""Phase 7: Teacher, Mentor & Parent Ecosystem (F-031, F-032, F-004, F-033).

Revision ID: 0008_phase7_educator_parent
Revises: 0007_phase6_homework_ai
Create Date: 2026-11-26
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_phase7_educator_parent"
down_revision = "0007_phase6_homework_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Parent Guardian Linking, Verifiable Consent & Goals (F-004, F-033)
    # ------------------------------------------------------------------
    op.create_table(
        "guardian_links",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "parent_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(32), nullable=False, server_default=sa.text("'parent'")),
        sa.Column("consent_status", sa.String(24), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("verification_code_hash", sa.String(128), nullable=True),
        sa.Column("consent_granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "privacy_settings_jsonb",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(
                '\'{"share_learning_summary": true, "share_weak_topics": true, "share_upcoming_tests": true, "allow_raw_ai_transcripts": false}\'::jsonb'
            ),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("relationship_type IN ('parent', 'guardian')", name="ck_guardian_rel_type"),
        sa.CheckConstraint("consent_status IN ('pending', 'verified', 'revoked')", name="ck_guardian_consent"),
        sa.UniqueConstraint("parent_user_id", "student_user_id", name="uq_guardian_parent_student"),
    )
    op.create_index("ix_guardian_links_parent", "guardian_links", ["parent_user_id", "consent_status"])
    op.create_index("ix_guardian_links_student", "guardian_links", ["student_user_id", "consent_status"])

    op.create_table(
        "parent_goals",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "parent_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("target_minutes_per_day", sa.Integer(), nullable=False, server_default=sa.text("45")),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active', 'achieved', 'archived')", name="ck_parent_goals_status"),
        sa.CheckConstraint("target_minutes_per_day >= 10 AND target_minutes_per_day <= 360", name="ck_parent_goals_mins"),
    )
    op.create_index("ix_parent_goals_parent_student", "parent_goals", ["parent_user_id", "student_user_id"])

    # ------------------------------------------------------------------
    # 2. Teacher Ecosystem: Classes, Sections, Enrollments, Assignments, Grading (F-031)
    # ------------------------------------------------------------------
    op.create_table(
        "teacher_classes",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("school_id", sa.Uuid(), nullable=True),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("academic_year_id", sa.Uuid(), nullable=True),
        sa.Column(
            "teacher_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("grade_label", sa.String(40), nullable=False),
        sa.Column("subject_name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_teacher_classes_status"),
    )
    op.create_index("ix_teacher_classes_teacher", "teacher_classes", ["teacher_id", "status"])
    op.create_index("ix_teacher_classes_tenant", "teacher_classes", ["tenant_id", "status"])

    op.create_table(
        "teacher_sections",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("teacher_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default=sa.text("40")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("class_id", "code", name="uq_teacher_sections_class_code"),
    )

    op.create_table(
        "class_enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("teacher_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            sa.Uuid(),
            sa.ForeignKey("teacher_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("roll_no", sa.String(32), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active', 'withdrawn')", name="ck_class_enrollments_status"),
        sa.UniqueConstraint("class_id", "student_id", name="uq_class_enrollments_class_student"),
    )
    op.create_index("ix_class_enrollments_student", "class_enrollments", ["student_id", "status"])
    op.create_index("ix_class_enrollments_tenant", "class_enrollments", ["tenant_id", "class_id"])

    op.create_table(
        "teacher_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "class_id",
            sa.Uuid(),
            sa.ForeignKey("teacher_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            sa.Uuid(),
            sa.ForeignKey("teacher_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "teacher_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("assignment_type", sa.String(24), nullable=False, server_default=sa.text("'assignment'")),
        sa.Column("linked_quiz_id", sa.Uuid(), nullable=True),
        sa.Column("linked_test_id", sa.Uuid(), nullable=True),
        sa.Column(
            "question_ids_jsonb",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("max_marks", sa.Float(), nullable=False, server_default=sa.text("20.0")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'published'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("assignment_type IN ('assignment', 'quiz', 'test')", name="ck_teacher_asgn_type"),
        sa.CheckConstraint("status IN ('draft', 'published', 'closed')", name="ck_teacher_asgn_status"),
        sa.CheckConstraint("max_marks > 0", name="ck_teacher_asgn_marks"),
    )
    op.create_index("ix_teacher_assignments_class", "teacher_assignments", ["class_id", "due_at"])
    op.create_index("ix_teacher_assignments_tenant", "teacher_assignments", ["tenant_id", "teacher_id"])

    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "assignment_id",
            sa.Uuid(),
            sa.ForeignKey("teacher_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("homework_submission_id", sa.Uuid(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("ai_suggested_score", sa.Float(), nullable=True),
        sa.Column("ai_feedback_summary", sa.Text(), nullable=True),
        sa.Column("teacher_score", sa.Float(), nullable=True),
        sa.Column("teacher_override_reason", sa.Text(), nullable=True),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'submitted'")),
        sa.Column("graded_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('submitted', 'ai_graded', 'teacher_reviewed', 'returned')",
            name="ck_asgn_sub_status",
        ),
        sa.UniqueConstraint("assignment_id", "student_id", name="uq_asgn_sub_assignment_student"),
    )
    op.create_index("ix_asgn_sub_assignment", "assignment_submissions", ["assignment_id", "status"])

    # ------------------------------------------------------------------
    # 3. Mentor Ecosystem: Assignments, Goals, Sessions & Follow-ups (F-032)
    # ------------------------------------------------------------------
    op.create_table(
        "mentor_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("mentor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("assigned_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active', 'paused', 'ended')", name="ck_mentor_asgn_status"),
        sa.UniqueConstraint("mentor_id", "student_id", name="uq_mentor_student"),
    )
    op.create_index("ix_mentor_assignments_mentor", "mentor_assignments", ["mentor_id", "status"])
    op.create_index("ix_mentor_assignments_tenant", "mentor_assignments", ["tenant_id", "mentor_id"])

    op.create_table(
        "mentor_goals",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("mentor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("progress_pct >= 0 AND progress_pct <= 100", name="ck_mentor_goals_pct"),
        sa.CheckConstraint("status IN ('active', 'completed', 'paused')", name="ck_mentor_goals_status"),
    )
    op.create_index("ix_mentor_goals_mentor_student", "mentor_goals", ["mentor_id", "student_id"])

    op.create_table(
        "mentor_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("mentor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("summary_notes", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "recommendations_jsonb",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')", name="ck_mentor_sess_status"),
    )
    op.create_index("ix_mentor_sessions_mentor_student", "mentor_sessions", ["mentor_id", "student_id"])

    op.create_table(
        "mentor_follow_ups",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("mentor_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mentor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'open'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'completed')", name="ck_mentor_followup_status"),
    )
    op.create_index("ix_mentor_follow_ups_mentor_student", "mentor_follow_ups", ["mentor_id", "student_id"])

    # ------------------------------------------------------------------
    # 4. Seed Phase 7 RBAC Permissions (idempotent)
    # ------------------------------------------------------------------
    conn = op.get_bind()
    perms = [
        ("teacher:manage_classes", "teacher", "manage_classes"),
        ("teacher:grade_submissions", "teacher", "grade_submissions"),
        ("teacher:view_analytics", "teacher", "view_analytics"),
        ("mentor:manage_students", "mentor", "manage_students"),
        ("mentor:view_analytics", "mentor", "view_analytics"),
        ("parent:manage_links", "parent", "manage_links"),
        ("parent:view_summaries", "parent", "view_summaries"),
    ]
    perm_ids: dict[str, uuid.UUID] = {}
    for code, resource, action in perms:
        existing = conn.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}
        ).scalar()
        if existing:
            perm_ids[code] = existing
        else:
            pid = uuid.uuid4()
            conn.execute(
                sa.text(
                    "INSERT INTO permissions (id, code, resource, action) "
                    "VALUES (:id, :code, :resource, :action)"
                ),
                {"id": pid, "code": code, "resource": resource, "action": action},
            )
            perm_ids[code] = pid

    role_grants: dict[str, tuple[str, ...]] = {
        "teacher": ("teacher:manage_classes", "teacher:grade_submissions", "teacher:view_analytics"),
        "mentor": ("mentor:manage_students", "mentor:view_analytics"),
        "parent": ("parent:manage_links", "parent:view_summaries"),
        "school_admin": (
            "teacher:manage_classes",
            "teacher:grade_submissions",
            "teacher:view_analytics",
            "mentor:manage_students",
            "mentor:view_analytics",
        ),
        "platform_admin": tuple(perm_ids.keys()),
    }
    for role_code, granted_codes in role_grants.items():
        role_id = conn.execute(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": role_code}
        ).scalar()
        if not role_id:
            continue
        for pcode in granted_codes:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:rid, :pid) ON CONFLICT DO NOTHING"
                ),
                {"rid": role_id, "pid": perm_ids[pcode]},
            )


def downgrade() -> None:
    op.drop_table("mentor_follow_ups")
    op.drop_table("mentor_sessions")
    op.drop_table("mentor_goals")
    op.drop_table("mentor_assignments")
    op.drop_table("assignment_submissions")
    op.drop_table("teacher_assignments")
    op.drop_table("class_enrollments")
    op.drop_table("teacher_sections")
    op.drop_table("teacher_classes")
    op.drop_table("parent_goals")
    op.drop_table("guardian_links")
