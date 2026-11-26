"""Phase 3 AI Tutor, Hybrid RAG, Deterministic Verification Cost Telemetry & Evals.

Revision ID: 0004_phase3_ai_tutor_rag
Revises: 0003_phase2_assessment_analytics
Create Date: 2026-11-26 22:08:00+05:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase3_ai_tutor_rag"
down_revision: str | Sequence[str] | None = "0003_phase2_assessment_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
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
        sa.Column("license_id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=True),
        sa.Column("grade_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'PUBLISHED'"), nullable=False
        ),
        sa.Column(
            "embedding_allowed", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("attribution_text", sa.String(length=512), nullable=True),
        sa.Column(
            "metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name=op.f("ck_knowledge_documents_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["content_sources.id"],
            ondelete="RESTRICT",
            name=op.f("fk_knowledge_docs_source"),
        ),
        sa.ForeignKeyConstraint(
            ["license_id"],
            ["content_licenses.id"],
            ondelete="RESTRICT",
            name=op.f("fk_knowledge_docs_license"),
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            ondelete="SET NULL",
            name=op.f("fk_knowledge_docs_cv"),
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"], ["grades.id"], ondelete="SET NULL", name=op.f("fk_knowledge_docs_grade")
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="SET NULL",
            name=op.f("fk_knowledge_docs_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            ondelete="SET NULL",
            name=op.f("fk_knowledge_docs_chapter"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], ondelete="SET NULL", name=op.f("fk_knowledge_docs_topic")
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="SET NULL",
            name=op.f("fk_knowledge_docs_concept"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name=op.f("fk_knowledge_docs_creator"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_documents")),
    )
    op.create_index(
        "ix_knowledge_docs_filter",
        "knowledge_documents",
        ["status", "embedding_allowed", "grade_id", "subject_id", "language_code"],
    )

    op.create_table(
        "knowledge_chunks",
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
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("hierarchy_path", sa.String(length=512), nullable=False),
        sa.Column("section_title", sa.String(length=240), nullable=True),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding_vec", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("fts_tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("token_estimate", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            ondelete="CASCADE",
            name=op.f("fk_knowledge_chunks_doc"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_chunks")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunks_doc_idx"),
    )
    op.create_index(
        "ix_knowledge_chunks_fts", "knowledge_chunks", ["fts_tsv"], postgresql_using="gin"
    )
    op.create_index(
        "ix_knowledge_chunks_doc_lang", "knowledge_chunks", ["document_id", "language_code"]
    )

    op.create_table(
        "ai_sessions",
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
        sa.Column(
            "session_type", sa.String(length=32), server_default=sa.text("'tutor'"), nullable=False
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "teaching_mode",
            sa.String(length=32),
            server_default=sa.text("'explain'"),
            nullable=False,
        ),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "curriculum_context_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False
        ),
        sa.CheckConstraint(
            "session_type IN ('tutor', 'doubt', 'lesson_companion', 'revision')",
            name=op.f("ck_ai_sessions_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_ai_sessions_student")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_sessions")),
    )
    op.create_index(
        "ix_ai_sessions_tenant_student", "ai_sessions", ["tenant_id", "student_id", "created_at"]
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ai_session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=48), nullable=True),
        sa.Column("pedagogical_mode", sa.String(length=32), nullable=True),
        sa.Column("spoiler_guard", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "citations_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "follow_up_questions_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "generated_practice_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            server_default=sa.text("'not_applicable'"),
            nullable=False,
        ),
        sa.Column(
            "verification_summary_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("provider_used", sa.String(length=48), nullable=True),
        sa.Column("model_used", sa.String(length=96), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "safety_verdict",
            sa.String(length=24),
            server_default=sa.text("'allow'"),
            nullable=False,
        ),
        sa.Column("tokens_in", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('student', 'assistant', 'system_event')",
            name=op.f("ck_ai_messages_role_valid"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'verification_failed', 'not_applicable')",
            name=op.f("ck_ai_messages_verif_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["ai_session_id"],
            ["ai_sessions.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_messages_session"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_messages")),
    )
    op.create_index(
        "ix_ai_messages_session_created", "ai_messages", ["ai_session_id", "created_at"]
    )

    op.create_table(
        "ai_tool_calls",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ai_message_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column(
            "input_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "output_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("succeeded", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ai_message_id"],
            ["ai_messages.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_tool_calls_msg"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_tool_calls")),
    )
    op.create_index("ix_ai_tool_calls_message", "ai_tool_calls", ["ai_message_id"])

    op.create_table(
        "provider_rate_cards",
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
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("model_id", sa.String(length=96), nullable=False),
        sa.Column("input_cost_per_1m_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("output_cost_per_1m_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_rate_cards")),
        sa.UniqueConstraint("provider", "model_id", name="uq_rate_card_provider_model"),
    )

    op.create_table(
        "ai_cost_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("ai_session_id", sa.Uuid(), nullable=True),
        sa.Column("ai_message_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("model_id", sa.String(length=96), nullable=False),
        sa.Column("task_type", sa.String(length=48), nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_ai_cost_events_user")
        ),
        sa.ForeignKeyConstraint(
            ["ai_session_id"],
            ["ai_sessions.id"],
            ondelete="SET NULL",
            name=op.f("fk_ai_cost_events_session"),
        ),
        sa.ForeignKeyConstraint(
            ["ai_message_id"],
            ["ai_messages.id"],
            ondelete="SET NULL",
            name=op.f("fk_ai_cost_events_msg"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_cost_events")),
    )
    op.create_index("ix_ai_cost_events_user_created", "ai_cost_events", ["user_id", "created_at"])

    op.create_table(
        "ai_review_queue",
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
        sa.Column("ai_session_id", sa.Uuid(), nullable=False),
        sa.Column("ai_message_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'edited_approved', 'rejected', 'escalated')",
            name=op.f("ck_ai_review_queue_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["ai_session_id"],
            ["ai_sessions.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_review_queue_session"),
        ),
        sa.ForeignKeyConstraint(
            ["ai_message_id"],
            ["ai_messages.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_review_queue_msg"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_review_queue_student"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_ai_review_queue_reviewer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_review_queue")),
    )
    op.create_index("ix_ai_review_queue_status", "ai_review_queue", ["status", "created_at"])

    op.create_table(
        "ai_eval_datasets",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("dataset_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_eval_datasets")),
        sa.UniqueConstraint("name", "version", name="uq_ai_eval_dataset_name_ver"),
    )

    op.create_table(
        "ai_eval_runs",
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
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("model_id", sa.String(length=96), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("passed_items", sa.Integer(), nullable=False),
        sa.Column("pass_rate_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "metrics_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'completed'"), nullable=False
        ),
        sa.Column("triggered_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["ai_eval_datasets.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_eval_runs_ds"),
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"], ["users.id"], ondelete="SET NULL", name=op.f("fk_ai_eval_runs_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_eval_runs")),
    )

    op.create_table(
        "ai_eval_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("eval_run_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.String(length=80), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column(
            "scores_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["eval_run_id"],
            ["ai_eval_runs.id"],
            ondelete="CASCADE",
            name=op.f("fk_ai_eval_results_run"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_eval_results")),
    )
    op.create_index("ix_ai_eval_results_run", "ai_eval_results", ["eval_run_id"])

    # Seed Phase 3 RBAC permissions (parent explicitly EXCLUDED from ai:chat!)
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('ai:chat', 'ai', 'chat'),
            ('ai:knowledge_manage', 'ai', 'knowledge_manage'),
            ('ai:eval_manage', 'ai', 'eval_manage'),
            ('ai:review_queue', 'ai', 'review_queue'),
            ('ai:cost_read', 'ai', 'cost_read')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code = 'student' AND p.code IN ('ai:chat'))
            OR (r.code = 'teacher' AND p.code IN ('ai:chat', 'ai:review_queue'))
            OR (r.code = 'content_admin' AND p.code IN ('ai:chat', 'ai:knowledge_manage'))
            OR (r.code = 'academic_reviewer' AND p.code IN ('ai:chat', 'ai:eval_manage', 'ai:review_queue'))
            OR (r.code = 'platform_admin' AND p.code IN ('ai:chat', 'ai:knowledge_manage', 'ai:eval_manage', 'ai:review_queue', 'ai:cost_read'))
        )
        ON CONFLICT DO NOTHING;
        """
    )

    # Seed reference provider rate cards
    op.execute(
        """
        INSERT INTO provider_rate_cards (provider, model_id, input_cost_per_1m_usd, output_cost_per_1m_usd, is_active) VALUES
            ('gemini', 'gemini-2.5-flash', 0.1500, 0.6000, true),
            ('gemini', 'gemini-2.5-pro', 1.2500, 10.0000, true),
            ('openai', 'gpt-4o-mini', 0.1500, 0.6000, true),
            ('openai', 'gpt-4o', 2.5000, 10.0000, true),
            ('anthropic', 'claude-3-5-haiku-latest', 0.8000, 4.0000, true),
            ('anthropic', 'claude-3-7-sonnet-latest', 3.0000, 15.0000, true),
            ('grounded_fallback', 'deterministic-v1', 0.0000, 0.0000, true)
        ON CONFLICT (provider, model_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("ai_eval_results")
    op.drop_table("ai_eval_runs")
    op.drop_table("ai_eval_datasets")
    op.drop_table("ai_review_queue")
    op.drop_table("ai_cost_events")
    op.drop_table("provider_rate_cards")
    op.drop_table("ai_tool_calls")
    op.drop_table("ai_messages")
    op.drop_table("ai_sessions")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
