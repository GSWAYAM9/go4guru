"""Phase 10: Multilingual Learning Expansion (14-Language Capability Registry, Glossary, Translation Review & Quality QA).

Revision ID: 0011_phase10_multilingual_expansion
Revises: 0010_phase9_exam_prep_ecosystem
Create Date: 2026-11-26 22:15:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_phase10_multilingual_expansion"
down_revision = "0010_phase9_exam_prep_ecosystem"
branch_labels = None
depends_on = None


def _seed_languages_data() -> list[dict[str, object]]:
    """Truthful 14-language registry seed mirroring multilingual_logic.CANONICAL_LANGUAGE_SEEDS."""
    return [
        {
            "language_code": "en",
            "display_name": "English",
            "native_name": "English",
            "script_name": "Latin",
            "rtl": False,
            "capability_status": "production",
            "testing_status": "passed",
            "availability_status": "available",
            "text_quality_tier": "tier_1_native",
            "translation_status": "native",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": True,
            "stt_supported": True,
            "subtitle_supported": True,
            "question_supported": True,
            "answer_supported": True,
            "voice_provider": "elevenlabs",
            "stt_provider": "elevenlabs_scribe",
            "translation_provider": "native_canonical",
            "pronunciation_tier": "high",
            "academic_review_status": "approved",
            "fallback_language_code": "en",
            "quality_score_pct": 98.0,
            "known_limitations": (
                "Primary canonical STEM language. Live audio synthesis and cloud STT require "
                "ELEVENLABS_API_KEY; otherwise timed subtitles and browser speech/text fallback apply."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai/anthropic", "status": "verified", "quality": "tier_1"},
                "tts": {"provider": "elevenlabs", "status": "verified_key_required", "quality": "high"},
                "stt": {"provider": "elevenlabs_scribe", "status": "verified_key_required", "quality": "high"},
                "translation": {"provider": "native_canonical", "status": "verified", "quality": "native"},
            },
        },
        {
            "language_code": "hi",
            "display_name": "Hindi",
            "native_name": "हिन्दी",
            "script_name": "Devanagari",
            "rtl": False,
            "capability_status": "production",
            "testing_status": "passed",
            "availability_status": "available",
            "text_quality_tier": "tier_1",
            "translation_status": "glossary_guided",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": True,
            "stt_supported": True,
            "subtitle_supported": True,
            "question_supported": True,
            "answer_supported": True,
            "voice_provider": "elevenlabs",
            "stt_provider": "elevenlabs_scribe",
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": "good_bilingual",
            "academic_review_status": "approved",
            "fallback_language_code": "en",
            "quality_score_pct": 91.5,
            "known_limitations": (
                "Recommended in Bilingual STEM mode (Devanagari prose + English technical symbols). "
                "Complex symbolic formulas remain KaTeX-rendered; ElevenLabs key required for live TTS/STT."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai/anthropic", "status": "verified", "quality": "tier_1"},
                "tts": {"provider": "elevenlabs", "status": "verified_key_required", "quality": "good_bilingual"},
                "stt": {"provider": "elevenlabs_scribe", "status": "verified_key_required", "quality": "good"},
                "translation": {"provider": "glossary_guided_llm", "status": "reviewed", "quality": "high"},
            },
        },
        {
            "language_code": "bn",
            "display_name": "Bengali",
            "native_name": "বাংলা",
            "script_name": "Bengali",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "in_review",
            "fallback_language_code": "en",
            "quality_score_pct": 81.0,
            "known_limitations": (
                "UI localization, bilingual explanations, and subtitles available in beta. "
                "TTS/STT disabled and question stems fall back to English until native STEM QA passes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "in_review", "quality": "beta"},
            },
        },
        {
            "language_code": "ta",
            "display_name": "Tamil",
            "native_name": "தமிழ்",
            "script_name": "Tamil",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "in_review",
            "fallback_language_code": "en",
            "quality_score_pct": 82.0,
            "known_limitations": (
                "UI, bilingual STEM explanations, and subtitles available in beta. "
                "TTS/STT disabled until Indic pronunciation QA for mathematical/scientific terms completes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "in_review", "quality": "beta"},
            },
        },
        {
            "language_code": "te",
            "display_name": "Telugu",
            "native_name": "తెలుగు",
            "script_name": "Telugu",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "in_review",
            "fallback_language_code": "en",
            "quality_score_pct": 80.5,
            "known_limitations": (
                "UI, bilingual explanations, and subtitles active in beta. "
                "TTS/STT disabled and question banks default to English until academic review finishes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "in_review", "quality": "beta"},
            },
        },
        {
            "language_code": "mr",
            "display_name": "Marathi",
            "native_name": "मराठी",
            "script_name": "Devanagari",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "in_review",
            "fallback_language_code": "hi",
            "quality_score_pct": 83.0,
            "known_limitations": (
                "Shares Devanagari script with Hindi; bilingual STEM text and UI strings in beta. "
                "Voice TTS/STT falls back to Hindi/English until native Marathi voice QA passes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "in_review", "quality": "beta"},
            },
        },
        {
            "language_code": "gu",
            "display_name": "Gujarati",
            "native_name": "ગુજરાતી",
            "script_name": "Gujarati",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "en",
            "quality_score_pct": 78.5,
            "known_limitations": (
                "UI localization and bilingual explanations in beta; TTS, STT, and translated "
                "assessment papers remain disabled pending subject-matter review."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "pending", "quality": "beta"},
            },
        },
        {
            "language_code": "kn",
            "display_name": "Kannada",
            "native_name": "ಕನ್ನಡ",
            "script_name": "Kannada",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "en",
            "quality_score_pct": 79.0,
            "known_limitations": (
                "UI chrome, bilingual text, and subtitles in beta. Voice synthesis/recognition and "
                "translated exam questions are disabled until verified."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "pending", "quality": "beta"},
            },
        },
        {
            "language_code": "ml",
            "display_name": "Malayalam",
            "native_name": "മലയാളം",
            "script_name": "Malayalam",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "en",
            "quality_score_pct": 77.5,
            "known_limitations": (
                "UI localization and bilingual STEM prose in beta; TTS/STT and exam paper translation "
                "fall back to English pending native academic evaluation."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "pending", "quality": "beta"},
            },
        },
        {
            "language_code": "pa",
            "display_name": "Punjabi",
            "native_name": "ਪੰਜਾਬੀ",
            "script_name": "Gurmukhi",
            "rtl": False,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "hi",
            "quality_score_pct": 76.0,
            "known_limitations": (
                "Gurmukhi UI and bilingual explanations in beta. Voice and formal exam papers fall "
                "back to Hindi/English until Gurmukhi STEM review completes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "pending", "quality": "beta"},
            },
        },
        {
            "language_code": "ur",
            "display_name": "Urdu",
            "native_name": "اردو",
            "script_name": "Perso-Arabic",
            "rtl": True,
            "capability_status": "beta",
            "testing_status": "partial",
            "availability_status": "limited",
            "text_quality_tier": "tier_2_beta",
            "translation_status": "beta_review",
            "ui_supported": True,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": True,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "glossary_guided_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "en",
            "quality_score_pct": 78.0,
            "known_limitations": (
                "RTL document direction active while mathematical equations stay strictly LTR via KaTeX. "
                "TTS/STT disabled until native Urdu STEM pronunciation QA completes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini/openai", "status": "beta", "quality": "tier_2"},
                "tts": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "stt": {"provider": "unverified", "status": "disabled_pending_qa", "quality": "untested"},
                "translation": {"provider": "glossary_guided_llm", "status": "pending", "quality": "beta"},
            },
        },
        {
            "language_code": "or",
            "display_name": "Odia",
            "native_name": "ଓଡ଼ିଆ",
            "script_name": "Odia",
            "rtl": False,
            "capability_status": "experimental",
            "testing_status": "pending",
            "availability_status": "limited",
            "text_quality_tier": "tier_3_experimental",
            "translation_status": "pending",
            "ui_supported": False,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": False,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "experimental_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "en",
            "quality_score_pct": None,
            "known_limitations": (
                "Experimental bilingual text and subtitle preview only. UI chrome, voice, STT, "
                "and question/answer workflows fall back to English until native QA passes."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini", "status": "experimental", "quality": "tier_3"},
                "tts": {"provider": "none", "status": "unavailable", "quality": "untested"},
                "stt": {"provider": "none", "status": "unavailable", "quality": "untested"},
                "translation": {"provider": "experimental_llm", "status": "unreviewed", "quality": "experimental"},
            },
        },
        {
            "language_code": "as",
            "display_name": "Assamese",
            "native_name": "অসমীয়া",
            "script_name": "Bengali",
            "rtl": False,
            "capability_status": "experimental",
            "testing_status": "pending",
            "availability_status": "limited",
            "text_quality_tier": "tier_3_experimental",
            "translation_status": "pending",
            "ui_supported": False,
            "explanation_supported": True,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": True,
            "question_supported": False,
            "answer_supported": False,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "experimental_llm",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "bn",
            "quality_score_pct": None,
            "known_limitations": (
                "Experimental bilingual explanation preview only; not yet benchmarked by native "
                "academic reviewers. UI and voice fall back through Bengali/English."
            ),
            "provider_matrix": {
                "llm": {"provider": "gemini", "status": "experimental", "quality": "tier_3"},
                "tts": {"provider": "none", "status": "unavailable", "quality": "untested"},
                "stt": {"provider": "none", "status": "unavailable", "quality": "untested"},
                "translation": {"provider": "experimental_llm", "status": "unreviewed", "quality": "experimental"},
            },
        },
        {
            "language_code": "sa",
            "display_name": "Sanskrit",
            "native_name": "संस्कृतम्",
            "script_name": "Devanagari",
            "rtl": False,
            "capability_status": "planned",
            "testing_status": "pending",
            "availability_status": "unavailable",
            "text_quality_tier": "tier_3_experimental",
            "translation_status": "pending",
            "ui_supported": False,
            "explanation_supported": False,
            "bilingual_supported": True,
            "tts_supported": False,
            "stt_supported": False,
            "subtitle_supported": False,
            "question_supported": False,
            "answer_supported": False,
            "voice_provider": None,
            "stt_provider": None,
            "translation_provider": "planned_academic_review",
            "pronunciation_tier": None,
            "academic_review_status": "pending",
            "fallback_language_code": "hi",
            "quality_score_pct": None,
            "known_limitations": (
                "Planned classical/academic track. Modern STEM explanations, UI localization, and "
                "voice synthesis are disabled and fall back to Hindi/English until vetted."
            ),
            "provider_matrix": {
                "llm": {"provider": "unverified", "status": "planned", "quality": "untested"},
                "tts": {"provider": "none", "status": "unavailable", "quality": "untested"},
                "stt": {"provider": "none", "status": "unavailable", "quality": "untested"},
                "translation": {"provider": "none", "status": "planned", "quality": "untested"},
            },
        },
    ]


def upgrade() -> None:
    # 1. Expand language_capabilities (backward-compatible)
    op.add_column(
        "language_capabilities",
        sa.Column("script_name", sa.String(length=32), server_default=sa.text("'Latin'"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("capability_status", sa.String(length=24), server_default=sa.text("'beta'"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("testing_status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("availability_status", sa.String(length=32), server_default=sa.text("'limited'"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("ui_supported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("explanation_supported", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("bilingual_supported", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("stt_provider", sa.String(length=48), nullable=True),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("translation_provider", sa.String(length=48), nullable=True),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("question_supported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("answer_supported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("fallback_language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("quality_score_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "language_capabilities",
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "language_capabilities",
        sa.Column(
            "provider_matrix_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    # 2. Expand user_profiles & voice_usage_logs
    op.add_column(
        "user_profiles",
        sa.Column(
            "bilingual_explanation_mode",
            sa.String(length=32),
            server_default=sa.text("'bilingual_stem_en'"),
            nullable=False,
        ),
    )
    op.add_column(
        "voice_usage_logs",
        sa.Column(
            "operation_type",
            sa.String(length=16),
            server_default=sa.text("'tts'"),
            nullable=False,
        ),
    )

    # 3. Create multilingual_glossary_terms
    op.create_table(
        "multilingual_glossary_terms",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("concept_key", sa.String(length=96), nullable=False),
        sa.Column("subject_area", sa.String(length=48), nullable=False),
        sa.Column("english_term", sa.String(length=160), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("localized_term", sa.String(length=200), nullable=False),
        sa.Column("transliteration", sa.String(length=200), nullable=True),
        sa.Column("preserve_english_in_bilingual", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("latex_symbol", sa.String(length=120), nullable=True),
        sa.Column("review_status", sa.String(length=24), server_default=sa.text("'approved'"), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "review_status IN ('draft', 'in_review', 'approved', 'rejected')",
            name=op.f("ck_glossary_review_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["language_code"],
            ["language_capabilities.language_code"],
            ondelete="CASCADE",
            name=op.f("fk_glossary_lang_code"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_glossary_reviewer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_multilingual_glossary_terms")),
        sa.UniqueConstraint("concept_key", "language_code", name="uq_glossary_concept_lang"),
    )
    op.create_index("ix_glossary_lang_subject", "multilingual_glossary_terms", ["language_code", "subject_area"])

    # 4. Create translation_entries
    op.create_table(
        "translation_entries",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_key", sa.String(length=160), nullable=False),
        sa.Column("source_language_code", sa.String(length=16), server_default=sa.text("'en'"), nullable=False),
        sa.Column("target_language_code", sa.String(length=16), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("bilingual_text", sa.Text(), nullable=True),
        sa.Column("notation_preserved", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "terminology_warnings_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'in_review'"), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resource_type IN ('ui_string', 'question', 'lesson_segment', 'formula_note', 'concept_summary')",
            name=op.f("ck_translation_resource_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'in_review', 'approved', 'rejected', 'needs_revision')",
            name=op.f("ck_translation_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["target_language_code"],
            ["language_capabilities.language_code"],
            ondelete="CASCADE",
            name=op.f("fk_translation_target_lang"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_translation_creator"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_translation_reviewer"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_translation_entries")),
        sa.UniqueConstraint(
            "resource_type",
            "resource_key",
            "target_language_code",
            name="uq_translation_resource_lang",
        ),
    )
    op.create_index("ix_translation_lang_status", "translation_entries", ["target_language_code", "status"])

    # 5. Create language_quality_evaluations
    op.create_table(
        "language_quality_evaluations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("modality", sa.String(length=24), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("test_suite_version", sa.String(length=32), server_default=sa.text("'phase10-v1'"), nullable=False),
        sa.Column("script_fidelity_score", sa.Float(), nullable=False),
        sa.Column("math_preservation_score", sa.Float(), nullable=False),
        sa.Column("science_notation_score", sa.Float(), nullable=False),
        sa.Column("terminology_accuracy_score", sa.Float(), nullable=False),
        sa.Column("fluency_score", sa.Float(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "findings_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("evaluated_by", sa.Uuid(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "modality IN ('ui', 'explanation', 'bilingual', 'voice', 'stt', 'subtitle', 'question', 'answer')",
            name=op.f("ck_lang_eval_modality_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["language_code"],
            ["language_capabilities.language_code"],
            ondelete="CASCADE",
            name=op.f("fk_lang_eval_code"),
        ),
        sa.ForeignKeyConstraint(
            ["evaluated_by"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_lang_eval_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_language_quality_evaluations")),
    )
    op.create_index("ix_lang_eval_code_date", "language_quality_evaluations", ["language_code", "evaluated_at"])

    # 6. Upsert all 14 canonical languages truthfully
    conn = op.get_bind()
    upsert_sql = sa.text(
        """
        INSERT INTO language_capabilities (
            language_code, display_name, native_name, script_name, rtl,
            capability_status, testing_status, availability_status,
            text_quality_tier, translation_status,
            ui_supported, explanation_supported, bilingual_supported,
            tts_supported, stt_supported, subtitle_supported,
            question_supported, answer_supported,
            voice_provider, stt_provider, translation_provider,
            pronunciation_tier, academic_review_status,
            fallback_language_code, quality_score_pct,
            known_limitations, provider_matrix_jsonb
        ) VALUES (
            :language_code, :display_name, :native_name, :script_name, :rtl,
            :capability_status, :testing_status, :availability_status,
            :text_quality_tier, :translation_status,
            :ui_supported, :explanation_supported, :bilingual_supported,
            :tts_supported, :stt_supported, :subtitle_supported,
            :question_supported, :answer_supported,
            :voice_provider, :stt_provider, :translation_provider,
            :pronunciation_tier, :academic_review_status,
            :fallback_language_code, :quality_score_pct,
            :known_limitations, CAST(:provider_matrix AS jsonb)
        )
        ON CONFLICT (language_code) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            native_name = EXCLUDED.native_name,
            script_name = EXCLUDED.script_name,
            rtl = EXCLUDED.rtl,
            capability_status = EXCLUDED.capability_status,
            testing_status = EXCLUDED.testing_status,
            availability_status = EXCLUDED.availability_status,
            text_quality_tier = EXCLUDED.text_quality_tier,
            translation_status = EXCLUDED.translation_status,
            ui_supported = EXCLUDED.ui_supported,
            explanation_supported = EXCLUDED.explanation_supported,
            bilingual_supported = EXCLUDED.bilingual_supported,
            tts_supported = EXCLUDED.tts_supported,
            stt_supported = EXCLUDED.stt_supported,
            subtitle_supported = EXCLUDED.subtitle_supported,
            question_supported = EXCLUDED.question_supported,
            answer_supported = EXCLUDED.answer_supported,
            voice_provider = EXCLUDED.voice_provider,
            stt_provider = EXCLUDED.stt_provider,
            translation_provider = EXCLUDED.translation_provider,
            pronunciation_tier = EXCLUDED.pronunciation_tier,
            academic_review_status = EXCLUDED.academic_review_status,
            fallback_language_code = EXCLUDED.fallback_language_code,
            quality_score_pct = EXCLUDED.quality_score_pct,
            known_limitations = EXCLUDED.known_limitations,
            provider_matrix_jsonb = EXCLUDED.provider_matrix_jsonb;
        """
    )
    for row in _seed_languages_data():
        params = dict(row)
        params["provider_matrix"] = json.dumps(row["provider_matrix"])
        conn.execute(upsert_sql, params)

    # 7. Seed STEM Glossary Terms across core Indian languages
    glossary_rows = [
        ("physics.velocity", "Physics", "velocity", "hi", "वेग", "veg", r"\vec{v}"),
        ("physics.acceleration", "Physics", "acceleration", "hi", "त्वरण", "tvaran", r"\vec{a}"),
        ("physics.force", "Physics", "force", "hi", "बल", "bal", r"\vec{F}"),
        ("chemistry.molarity", "Chemistry", "molarity", "hi", "मोलरता", "molarata", "M"),
        ("math.quadratic_equation", "Mathematics", "quadratic equation", "hi", "द्विघात समीकरण", "dvighat samikaran", r"ax^2+bx+c=0"),
        ("biology.photosynthesis", "Biology", "photosynthesis", "hi", "प्रकाश संश्लेषण", "prakash sanshleshan", None),
        ("physics.velocity", "Physics", "velocity", "ta", "திசைவேகம்", "thisaivegam", r"\vec{v}"),
        ("physics.acceleration", "Physics", "acceleration", "ta", "முடுக்கம்", "mudukkam", r"\vec{a}"),
        ("physics.velocity", "Physics", "velocity", "te", "వేగం", "vegam", r"\vec{v}"),
        ("physics.acceleration", "Physics", "acceleration", "te", "త్వరణం", "tvaranam", r"\vec{a}"),
        ("physics.velocity", "Physics", "velocity", "bn", "বেগ", "beg", r"\vec{v}"),
        ("physics.acceleration", "Physics", "acceleration", "bn", "ত্বরণ", "taran", r"\vec{a}"),
        ("physics.velocity", "Physics", "velocity", "mr", "वेग", "veg", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "gu", "વેગ", "veg", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "kn", "ವೇಗ", "vega", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "ml", "പ്രവേഗം", "pravegam", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "pa", "ਵੇਗ", "veg", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "ur", "رفتار", "raftar", r"\vec{v}"),
        ("physics.acceleration", "Physics", "acceleration", "ur", "اسراع", "isra", r"\vec{a}"),
        ("physics.velocity", "Physics", "velocity", "or", "ବେଗ", "bega", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "as", "বেগ", "beg", r"\vec{v}"),
        ("physics.velocity", "Physics", "velocity", "sa", "वेगः", "vegah", r"\vec{v}"),
    ]
    glossary_sql = sa.text(
        """
        INSERT INTO multilingual_glossary_terms (
            concept_key, subject_area, english_term, language_code,
            localized_term, transliteration, preserve_english_in_bilingual,
            latex_symbol, review_status
        ) VALUES (
            :concept_key, :subject_area, :english_term, :language_code,
            :localized_term, :transliteration, true, :latex_symbol, 'approved'
        )
        ON CONFLICT (concept_key, language_code) DO NOTHING;
        """
    )
    for ck, subj, en_t, lc, loc_t, tr, sym in glossary_rows:
        conn.execute(
            glossary_sql,
            {
                "concept_key": ck,
                "subject_area": subj,
                "english_term": en_t,
                "language_code": lc,
                "localized_term": loc_t,
                "transliteration": tr,
                "latex_symbol": sym,
            },
        )

    # 8. Seed Phase 10 RBAC permissions
    op.execute(
        """
        INSERT INTO permissions (code, resource, action) VALUES
            ('multilingual:read', 'multilingual', 'read'),
            ('multilingual:translate', 'multilingual', 'translate'),
            ('multilingual:review', 'multilingual', 'review'),
            ('multilingual:manage', 'multilingual', 'manage')
        ON CONFLICT (code) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE (
            (r.code IN ('student', 'teacher', 'mentor', 'parent', 'school_admin')
                AND p.code IN ('multilingual:read'))
            OR (r.code = 'content_admin'
                AND p.code IN ('multilingual:read', 'multilingual:translate'))
            OR (r.code = 'academic_reviewer'
                AND p.code IN ('multilingual:read', 'multilingual:translate', 'multilingual:review'))
            OR (r.code = 'platform_admin'
                AND p.code IN ('multilingual:read', 'multilingual:translate', 'multilingual:review', 'multilingual:manage'))
        )
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("language_quality_evaluations")
    op.drop_table("translation_entries")
    op.drop_table("multilingual_glossary_terms")
    op.drop_column("voice_usage_logs", "operation_type")
    op.drop_column("user_profiles", "bilingual_explanation_mode")
    op.drop_column("language_capabilities", "provider_matrix_jsonb")
    op.drop_column("language_capabilities", "last_evaluated_at")
    op.drop_column("language_capabilities", "quality_score_pct")
    op.drop_column("language_capabilities", "fallback_language_code")
    op.drop_column("language_capabilities", "answer_supported")
    op.drop_column("language_capabilities", "question_supported")
    op.drop_column("language_capabilities", "translation_provider")
    op.drop_column("language_capabilities", "stt_provider")
    op.drop_column("language_capabilities", "bilingual_supported")
    op.drop_column("language_capabilities", "explanation_supported")
    op.drop_column("language_capabilities", "ui_supported")
    op.drop_column("language_capabilities", "availability_status")
    op.drop_column("language_capabilities", "testing_status")
    op.drop_column("language_capabilities", "capability_status")
    op.drop_column("language_capabilities", "script_name")
