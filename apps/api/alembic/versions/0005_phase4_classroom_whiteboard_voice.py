"""Phase 4 Live AI Classroom, Synchronized Whiteboard, Language Registry & Voice Logs.

Revision ID: 0005_phase4_classroom
Revises: 0004_phase3_ai_tutor_rag
Create Date: 2026-11-27 00:35:00+05:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase4_classroom"
down_revision: str | Sequence[str] | None = "0004_phase3_ai_tutor_rag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "language_capabilities",
        sa.Column("language_code", sa.String(length=16), nullable=False),
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
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("native_name", sa.String(length=64), nullable=False),
        sa.Column("rtl", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "text_quality_tier",
            sa.String(length=32),
            server_default=sa.text("'tier_2_beta'"),
            nullable=False,
        ),
        sa.Column(
            "translation_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("tts_supported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("stt_supported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("voice_provider", sa.String(length=48), nullable=True),
        sa.Column("pronunciation_tier", sa.String(length=32), nullable=True),
        sa.Column(
            "subtitle_supported", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "academic_review_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("known_limitations", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("language_code", name=op.f("pk_language_capabilities")),
    )

    op.create_table(
        "whiteboard_assets",
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
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("license_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=256), nullable=False),
        sa.Column("alt_text", sa.String(length=300), nullable=False),
        sa.Column(
            "legal_review_status",
            sa.String(length=24),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "legal_review_status IN ('pending', 'approved', 'rejected', 'quarantined')",
            name=op.f("ck_whiteboard_assets_review_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["content_sources.id"],
            ondelete="RESTRICT",
            name=op.f("fk_wb_assets_source"),
        ),
        sa.ForeignKeyConstraint(
            ["license_id"],
            ["content_licenses.id"],
            ondelete="RESTRICT",
            name=op.f("fk_wb_assets_license"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name=op.f("fk_wb_assets_creator"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_whiteboard_assets")),
    )

    op.create_table(
        "lesson_plans",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column(
            "language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "voice_language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "subtitle_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=24),
            server_default=sa.text("'1.0.0'"),
            nullable=False,
        ),
        sa.Column("lesson_artifact_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], ondelete="SET NULL", name=op.f("fk_lesson_plans_student")
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            ondelete="SET NULL",
            name=op.f("fk_lesson_plans_cv"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], ondelete="SET NULL", name=op.f("fk_lesson_plans_subj")
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], ondelete="SET NULL", name=op.f("fk_lesson_plans_chap")
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"], ["concepts.id"], ondelete="SET NULL", name=op.f("fk_lesson_plans_conc")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lesson_plans")),
    )
    op.create_index("ix_lesson_plans_student", "lesson_plans", ["student_id", "created_at"])

    op.create_table(
        "classroom_sessions",
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
        sa.Column("lesson_plan_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=32), server_default=sa.text("'READY'"), nullable=False),
        sa.Column("current_segment_seq", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "playback_position_ms", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("playback_speed", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column(
            "voice_language", sa.String(length=16), server_default=sa.text("'en'"), nullable=False
        ),
        sa.Column(
            "subtitle_language",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "checkpoint_results_jsonb",
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
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('IDLE', 'READY', 'PLAYING_SEGMENT', 'PAUSED', "
            "'CHECKPOINT_WAIT', 'DOUBT_INTERRUPTION', 'COMPLETED')",
            name=op.f("ck_classroom_sessions_state_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_classroom_sessions_student"),
        ),
        sa.ForeignKeyConstraint(
            ["lesson_plan_id"],
            ["lesson_plans.id"],
            ondelete="CASCADE",
            name=op.f("fk_classroom_sessions_lp"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classroom_sessions")),
    )
    op.create_index(
        "ix_classroom_sessions_tenant_student",
        "classroom_sessions",
        ["tenant_id", "student_id", "created_at"],
    )

    op.create_table(
        "classroom_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("classroom_session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column(
            "payload_jsonb",
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
            ["classroom_session_id"],
            ["classroom_sessions.id"],
            ondelete="CASCADE",
            name=op.f("fk_classroom_events_sess"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classroom_events")),
        sa.UniqueConstraint("classroom_session_id", "sequence_no", name="uq_classroom_events_seq"),
    )

    op.create_table(
        "whiteboard_snapshots",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("classroom_session_id", sa.Uuid(), nullable=False),
        sa.Column("segment_seq", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["classroom_session_id"],
            ["classroom_sessions.id"],
            ondelete="CASCADE",
            name=op.f("fk_wb_snapshots_sess"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_whiteboard_snapshots")),
    )
    op.create_index(
        "ix_wb_snapshots_sess_seg",
        "whiteboard_snapshots",
        ["classroom_session_id", "segment_seq", "version"],
    )

    op.create_table(
        "whiteboard_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("classroom_session_id", sa.Uuid(), nullable=False),
        sa.Column("segment_seq", sa.Integer(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("action_payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_undone", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("actor IN ('ai', 'student')", name=op.f("ck_wb_events_actor_valid")),
        sa.ForeignKeyConstraint(
            ["classroom_session_id"],
            ["classroom_sessions.id"],
            ondelete="CASCADE",
            name=op.f("fk_wb_events_sess"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_whiteboard_events")),
        sa.UniqueConstraint("classroom_session_id", "sequence_no", name="uq_wb_events_sess_seq"),
    )

    op.create_table(
        "voice_usage_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_session_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("voice_id", sa.String(length=96), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("characters_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("audio_seconds", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(precision=12, scale=6),
            server_default=sa.text("0.000000"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_voice_usage_user")
        ),
        sa.ForeignKeyConstraint(
            ["classroom_session_id"],
            ["classroom_sessions.id"],
            ondelete="SET NULL",
            name=op.f("fk_voice_usage_sess"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_usage_logs")),
    )
    op.create_index("ix_voice_usage_user_created", "voice_usage_logs", ["user_id", "created_at"])

    # Seed Phase 4 Permissions & Roles
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('classroom:create', 'classroom', 'create'),
            ('classroom:attend', 'classroom', 'attend'),
            ('voice:tts', 'voice', 'tts'),
            ('whiteboard:write', 'whiteboard', 'write'),
            ('whiteboard:asset_manage', 'whiteboard', 'asset_manage')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code = 'student' AND p.code IN ('classroom:create', 'classroom:attend', 'voice:tts', 'whiteboard:write'))
            OR (r.code = 'teacher' AND p.code IN ('classroom:create', 'classroom:attend', 'voice:tts', 'whiteboard:write'))
            OR (r.code = 'content_admin' AND p.code IN ('classroom:create', 'classroom:attend', 'whiteboard:write', 'whiteboard:asset_manage'))
            OR (r.code = 'academic_reviewer' AND p.code IN ('classroom:attend'))
            OR (r.code = 'platform_admin' AND p.code IN ('classroom:create', 'classroom:attend', 'voice:tts', 'whiteboard:write', 'whiteboard:asset_manage'))
        )
        ON CONFLICT DO NOTHING;
        """
    )

    # Seed truthful Language Capability Registry (matches VOICE_MULTILINGUAL_ARCHITECTURE.md)
    op.execute(
        """
        INSERT INTO language_capabilities (
            language_code, display_name, native_name, rtl, text_quality_tier,
            translation_status, tts_supported, stt_supported, voice_provider,
            pronunciation_tier, subtitle_supported, academic_review_status, known_limitations
        ) VALUES
            ('en', 'English', 'English', false, 'tier_1_native', 'native', true, true, 'elevenlabs', 'high', true, 'approved', 'Primary STEM instruction language; uses timed subtitle fallback if ElevenLabs key is absent.'),
            ('hi', 'Hindi', 'हिन्दी', false, 'tier_1', 'glossary_guided', true, true, 'elevenlabs', 'good_bilingual', true, 'approved', 'Bilingual Hindi explanation preserving English technical STEM terms and KaTeX equations.'),
            ('ta', 'Tamil', 'தமிழ்', false, 'tier_2_beta', 'beta', false, false, null, null, true, 'pending', 'Text & subtitle preview only; TTS audio disabled until native academic pronunciation QA completes.'),
            ('te', 'Telugu', 'తెలుగు', false, 'tier_2_beta', 'beta', false, false, null, null, true, 'pending', 'Text & subtitle preview only; TTS audio disabled until native academic pronunciation QA completes.'),
            ('bn', 'Bengali', 'বাংলা', false, 'tier_2_beta', 'beta', false, false, null, null, true, 'pending', 'Text & subtitle preview only; TTS audio disabled until native academic pronunciation QA completes.'),
            ('mr', 'Marathi', 'मराठी', false, 'tier_2_beta', 'beta', false, false, null, null, true, 'pending', 'Text & subtitle preview only; TTS audio disabled until native academic pronunciation QA completes.'),
            ('kn', 'Kannada', 'ಕನ್ನಡ', false, 'tier_2_beta', 'beta', false, false, null, null, true, 'pending', 'Text & subtitle preview only; TTS audio disabled until native academic pronunciation QA completes.'),
            ('ur', 'Urdu', 'اردو', true, 'tier_2_beta', 'beta', false, false, null, null, true, 'pending', 'RTL subtitle layout ready; TTS audio disabled until native QA completes.')
        ON CONFLICT (language_code) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("voice_usage_logs")
    op.drop_table("whiteboard_events")
    op.drop_table("whiteboard_snapshots")
    op.drop_table("classroom_events")
    op.drop_table("classroom_sessions")
    op.drop_table("lesson_plans")
    op.drop_table("whiteboard_assets")
    op.drop_table("language_capabilities")
