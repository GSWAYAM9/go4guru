"""Phase 8: Institutional Multi-Tenant Platform & Subscription Entitlements (F-003, F-036).

Revision ID: 0009_phase8_multitenant_institutions
Revises: 0008_phase7_educator_parent
Create Date: 2026-11-26
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_phase8_multitenant_institutions"
down_revision = "0008_phase7_educator_parent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Organizations, Schools, Branches, Academic Years, Batches (F-003)
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "organization_type",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'school_group'"),
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("contact_email", sa.String(320), nullable=False),
        sa.Column(
            "config_jsonb",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(
                '\'{"default_language": "en", "allow_ai_tutor": true, "allow_homework_ai": true, "require_mfa_for_admins": true}\'::jsonb'
            ),
        ),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "organization_type IN ('school_group', 'coaching_institute', 'standalone_school')",
            name="ck_organizations_type",
        ),
        sa.CheckConstraint(
            "status IN ('onboarding', 'active', 'suspended')",
            name="ck_organizations_status",
        ),
    )

    op.create_table(
        "schools",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("board_code", sa.String(32), nullable=False, server_default=sa.text("'CBSE'")),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("config_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "code", name="uq_schools_tenant_code"),
    )
    op.create_index("ix_schools_tenant", "schools", ["tenant_id", "status"])

    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.Uuid(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("school_id", "code", name="uq_branches_school_code"),
    )
    op.create_index("ix_branches_tenant_school", "branches", ["tenant_id", "school_id"])

    op.create_table(
        "academic_years",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.Uuid(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("school_id", "label", name="uq_academic_years_school_label"),
    )
    op.create_index("ix_academic_years_tenant", "academic_years", ["tenant_id", "school_id"])

    op.create_table(
        "institution_batches",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "school_id",
            sa.Uuid(),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Uuid(),
            sa.ForeignKey("branches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "academic_year_id",
            sa.Uuid(),
            sa.ForeignKey("academic_years.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("grade_label", sa.String(40), nullable=False),
        sa.Column("section_name", sa.String(40), nullable=False, server_default=sa.text("'A'")),
        sa.Column("exam_track", sa.String(40), nullable=False, server_default=sa.text("'cbse_board'")),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_institution_batches_tenant", "institution_batches", ["tenant_id", "school_id"])

    op.create_table(
        "institution_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("schools.id", ondelete="SET NULL"), nullable=True),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "member_role IN ('school_admin', 'teacher', 'mentor', 'student')",
            name="ck_inst_member_role",
        ),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_inst_member_status"),
        sa.UniqueConstraint("tenant_id", "user_id", "member_role", name="uq_inst_member_tenant_user_role"),
    )
    op.create_index("ix_inst_memberships_tenant", "institution_memberships", ["tenant_id", "member_role"])
    op.create_index("ix_inst_memberships_user", "institution_memberships", ["user_id", "status"])

    op.create_table(
        "batch_enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "batch_id",
            sa.Uuid(),
            sa.ForeignKey("institution_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("roll_no", sa.String(32), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("batch_id", "student_id", name="uq_batch_enrollments_batch_student"),
    )
    op.create_index("ix_batch_enrollments_tenant", "batch_enrollments", ["tenant_id", "batch_id"])

    op.create_table(
        "institution_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "batch_id",
            sa.Uuid(),
            sa.ForeignKey("institution_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False, server_default=sa.text("'test'")),
        sa.Column("linked_test_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_marks", sa.Float(), nullable=False, server_default=sa.text("100.0")),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'published'")),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("kind IN ('assignment', 'test')", name="ck_inst_asmt_kind"),
        sa.CheckConstraint("status IN ('draft', 'published', 'closed')", name="ck_inst_asmt_status"),
    )
    op.create_index("ix_inst_assessments_tenant", "institution_assessments", ["tenant_id", "school_id"])

    # ------------------------------------------------------------------
    # 2. Subscriptions & Entitlements (F-036)
    # ------------------------------------------------------------------
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(48), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("monthly_price_inr", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_students", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("max_teachers", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("max_branches", sa.Integer(), nullable=False, server_default=sa.text("2")),
        sa.Column(
            "entitlements_jsonb",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "plan_id",
            sa.Uuid(),
            sa.ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'active'")),
        sa.Column("seat_limit", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "entitlement_overrides_jsonb",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('trial', 'active', 'past_due', 'cancelled')",
            name="ck_tenant_sub_status",
        ),
    )

    # ------------------------------------------------------------------
    # 3. Seed Canonical Institutional Plans & Phase 8 RBAC Permissions
    # ------------------------------------------------------------------
    conn = op.get_bind()
    plans = [
        (
            "school_starter",
            "School Starter",
            "starter",
            9999,
            150,
            20,
            2,
            '{"ai_tutor": true, "homework_ai": true, "live_classroom": false, "institution_reports": true, "csv_export": true}',
        ),
        (
            "school_growth",
            "School Growth",
            "growth",
            24999,
            1000,
            100,
            10,
            '{"ai_tutor": true, "homework_ai": true, "live_classroom": true, "institution_reports": true, "csv_export": true}',
        ),
        (
            "school_enterprise",
            "Institution Enterprise",
            "enterprise",
            79999,
            10000,
            1000,
            100,
            '{"ai_tutor": true, "homework_ai": true, "live_classroom": true, "institution_reports": true, "csv_export": true, "custom_branding": true}',
        ),
    ]
    for code, name, tier, price, max_stu, max_tch, max_br, ent_json in plans:
        existing = conn.execute(
            sa.text("SELECT id FROM subscription_plans WHERE code = :code"), {"code": code}
        ).scalar()
        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO subscription_plans "
                    "(id, code, name, tier, monthly_price_inr, max_students, max_teachers, max_branches, entitlements_jsonb) "
                    "VALUES (:id, :code, :name, :tier, :price, :ms, :mt, :mb, CAST(:ent AS jsonb))"
                ),
                {
                    "id": uuid.uuid4(),
                    "code": code,
                    "name": name,
                    "tier": tier,
                    "price": price,
                    "ms": max_stu,
                    "mt": max_tch,
                    "mb": max_br,
                    "ent": ent_json,
                },
            )

    perms = [
        ("org:manage_tenant", "org", "manage_tenant"),
        ("org:manage_staff", "org", "manage_staff"),
        ("org:manage_enrollments", "org", "manage_enrollments"),
        ("org:view_reports", "org", "view_reports"),
        ("billing:manage_subscription", "billing", "manage_subscription"),
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

    for role_code in ("school_admin", "platform_admin"):
        role_id = conn.execute(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": role_code}
        ).scalar()
        if not role_id:
            continue
        for pid in perm_ids.values():
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:rid, :pid) ON CONFLICT DO NOTHING"
                ),
                {"rid": role_id, "pid": pid},
            )


def downgrade() -> None:
    op.drop_table("tenant_subscriptions")
    op.drop_table("subscription_plans")
    op.drop_table("institution_assessments")
    op.drop_table("batch_enrollments")
    op.drop_table("institution_memberships")
    op.drop_table("institution_batches")
    op.drop_table("academic_years")
    op.drop_table("branches")
    op.drop_table("schools")
    op.drop_table("organizations")
