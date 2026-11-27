"""Phase 6 Homework AI — Submissions, Multi-Page Files, OCR Results, Evaluations & Retries.

Revision ID: 0007_phase6_homework_ai
Revises: 0006_phase5_adaptive_revision
Create Date: 2026-11-27 12:15:00+05:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_phase6_homework_ai"
down_revision: str | Sequence[str] | None = "0006_phase5_adaptive_revision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "homework_submissions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "selected_subject",
            sa.String(length=40),
            server_default=sa.text("'auto'"),
            nullable=False,
        ),
        sa.Column("detected_subject", sa.String(length=40), nullable=True),
        sa.Column("subject_confidence", sa.Float(), nullable=True),
        sa.Column(
            "language_code",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'uploaded'"),
            nullable=False,
        ),
        sa.Column("page_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "needs_ocr_review",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'ocr_processing', 'needs_review', 'analyzing', "
            "'feedback_ready', 'retry_pending', 'completed', 'failed')",
            name=op.f("ck_hw_submissions_status"),
        ),
        sa.CheckConstraint(
            "selected_subject IN ('auto', 'mathematics', 'physics', 'chemistry', "
            "'english', 'social_science')",
            name=op.f("ck_hw_submissions_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_hw_submissions_student"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="SET NULL",
            name=op.f("fk_hw_submissions_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="SET NULL",
            name=op.f("fk_hw_submissions_chapter"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="SET NULL",
            name=op.f("fk_hw_submissions_concept"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homework_submissions")),
    )
    op.create_index(
        "ix_hw_submissions_student_created",
        "homework_submissions",
        ["student_id", "created_at"],
    )
    op.create_index(
        "ix_hw_submissions_tenant_status",
        "homework_submissions",
        ["tenant_id", "status"],
    )

    op.create_table(
        "homework_files",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("detected_format", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("exif_stripped", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("pdf_page_count", sa.Integer(), nullable=True),
        sa.Column(
            "scan_status",
            sa.String(length=24),
            server_default=sa.text("'clean'"),
            nullable=False,
        ),
        sa.Column(
            "validation_metadata_jsonb",
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
        sa.CheckConstraint(
            "scan_status IN ('pending', 'clean', 'rejected')",
            name=op.f("ck_hw_files_scan_status"),
        ),
        sa.CheckConstraint("page_no >= 1", name=op.f("ck_hw_files_page_no")),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["homework_submissions.id"],
            ondelete="CASCADE",
            name=op.f("fk_hw_files_submission"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homework_files")),
        sa.UniqueConstraint("submission_id", "page_no", name="uq_hw_files_submission_page"),
    )
    op.create_index("ix_hw_files_submission", "homework_files", ["submission_id", "page_no"])

    op.create_table(
        "homework_ocr_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=True),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("ocr_provider", sa.String(length=64), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("extracted_latex", sa.Text(), nullable=True),
        sa.Column(
            "handwriting_detected",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "handwriting_supported",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column(
            "needs_review",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("student_corrected_text", sa.Text(), nullable=True),
        sa.Column(
            "warnings_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "raw_jsonb",
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
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name=op.f("ck_hw_ocr_confidence"),
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["homework_submissions.id"],
            ondelete="CASCADE",
            name=op.f("fk_hw_ocr_submission"),
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["homework_files.id"],
            ondelete="SET NULL",
            name=op.f("fk_hw_ocr_file"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homework_ocr_results")),
        sa.UniqueConstraint("submission_id", "page_no", name="uq_hw_ocr_submission_page"),
    )

    op.create_table(
        "homework_evaluations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("subject_area", sa.String(length=40), nullable=False),
        sa.Column("detected_question", sa.Text(), nullable=False),
        sa.Column("student_work_summary", sa.Text(), nullable=False),
        sa.Column(
            "extracted_steps_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "step_evaluations_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "error_classifications_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("overall_status", sa.String(length=32), nullable=False),
        sa.Column("feedback_summary", sa.Text(), nullable=False),
        sa.Column(
            "strengths_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "hints_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "current_hint_level_unlocked",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "solution_revealed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("complete_solution_markdown", sa.Text(), nullable=False),
        sa.Column(
            "verifier_results_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "validation_report_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "revision_recommendations_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column(
            "confidence_band",
            sa.String(length=24),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),
        sa.Column("provider_used", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("safety_verdict", sa.String(length=32), server_default=sa.text("'allow'"), nullable=False),
        sa.Column("teacher_override_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "subject_area IN ('mathematics', 'physics', 'chemistry', 'english', 'social_science')",
            name=op.f("ck_hw_eval_subject"),
        ),
        sa.CheckConstraint(
            "overall_status IN ('correct', 'partially_correct', 'needs_correction', 'unreadable_or_uncertain')",
            name=op.f("ck_hw_eval_status"),
        ),
        sa.CheckConstraint(
            "current_hint_level_unlocked >= 0 AND current_hint_level_unlocked <= 3",
            name=op.f("ck_hw_eval_hint_level"),
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name=op.f("ck_hw_eval_confidence"),
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["homework_submissions.id"],
            ondelete="CASCADE",
            name=op.f("fk_hw_eval_submission"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homework_evaluations")),
        sa.UniqueConstraint("submission_id", "attempt_no", name="uq_hw_eval_submission_attempt"),
    )
    op.create_index(
        "ix_hw_eval_submission_attempt",
        "homework_evaluations",
        ["submission_id", "attempt_no"],
    )

    # Seed Phase 6 RBAC Permissions & Role Grants
    # NOTE: Parent role is intentionally excluded from raw homework AI coaching endpoints.
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('homework:manage_own', 'homework', 'manage_own'),
            ('homework:review', 'homework', 'review')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code = 'student' AND p.code = 'homework:manage_own')
            OR (r.code IN ('teacher', 'mentor', 'school_admin', 'academic_reviewer', 'platform_admin')
                AND p.code IN ('homework:manage_own', 'homework:review'))
        )
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("homework_evaluations")
    op.drop_table("homework_ocr_results")
    op.drop_table("homework_files")
    op.drop_table("homework_submissions")
