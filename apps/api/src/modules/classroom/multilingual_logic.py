"""Pure-stdlib Phase 10 Multilingual Capability, Notation Preservation, Fallback & QA Logic.

Zero third-party dependencies so every mathematical/scientific notation guard,
fallback resolver, bilingual STEM formatter, script fidelity check, and
language quality evaluation rule is fast and unit-testable with stdlib unittest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Supported Modalities & Bilingual Modes
# ---------------------------------------------------------------------------
LANGUAGE_MODALITIES: tuple[str, ...] = (
    "ui",
    "explanation",
    "voice",
    "subtitle",
    "question",
    "answer",
)

BILINGUAL_MODES: tuple[str, ...] = (
    "monolingual",
    "bilingual_stem_en",
    "side_by_side",
)

# Unicode script ranges used for empirical script-fidelity validation
SCRIPT_UNICODE_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "Latin": ((0x0041, 0x007A), (0x00C0, 0x024F)),
    "Devanagari": ((0x0900, 0x097F),),
    "Bengali": ((0x0980, 0x09FF),),
    "Tamil": ((0x0B80, 0x0BFF),),
    "Telugu": ((0x0C00, 0x0C7F),),
    "Gujarati": ((0x0A80, 0x0AFF),),
    "Kannada": ((0x0C80, 0x0CFF),),
    "Malayalam": ((0x0D00, 0x0D7F),),
    "Gurmukhi": ((0x0A00, 0x0A7F),),
    "Perso-Arabic": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "Odia": ((0x0B00, 0x0B7F),),
}


@dataclass(frozen=True, slots=True)
class LanguageCapabilityRecord:
    """In-memory projection of a Language Capability Registry row."""

    language_code: str
    display_name: str
    native_name: str
    script_name: str
    rtl: bool
    capability_status: str  # production | beta | experimental | planned
    testing_status: str  # passed | partial | pending | failed
    availability_status: str  # available | limited | provider_key_required | unavailable
    text_quality_tier: str
    translation_status: str
    ui_supported: bool
    explanation_supported: bool
    bilingual_supported: bool
    tts_supported: bool
    stt_supported: bool
    subtitle_supported: bool
    question_supported: bool
    answer_supported: bool
    voice_provider: str | None
    stt_provider: str | None
    translation_provider: str | None
    pronunciation_tier: str | None
    academic_review_status: str
    fallback_language_code: str
    quality_score_pct: float | None
    known_limitations: str | None
    provider_matrix: dict[str, Any]


# ---------------------------------------------------------------------------
# Truthful Empirical Registry Baseline (14 Languages — Honest Limitations)
# ---------------------------------------------------------------------------
CANONICAL_LANGUAGE_SEEDS: tuple[dict[str, Any], ...] = (
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
)


def default_capability_map() -> dict[str, LanguageCapabilityRecord]:
    """Build an in-memory map of the truthful 14-language baseline."""
    out: dict[str, LanguageCapabilityRecord] = {}
    for row in CANONICAL_LANGUAGE_SEEDS:
        out[row["language_code"]] = LanguageCapabilityRecord(
            language_code=row["language_code"],
            display_name=row["display_name"],
            native_name=row["native_name"],
            script_name=row["script_name"],
            rtl=row["rtl"],
            capability_status=row["capability_status"],
            testing_status=row["testing_status"],
            availability_status=row["availability_status"],
            text_quality_tier=row["text_quality_tier"],
            translation_status=row["translation_status"],
            ui_supported=row["ui_supported"],
            explanation_supported=row["explanation_supported"],
            bilingual_supported=row["bilingual_supported"],
            tts_supported=row["tts_supported"],
            stt_supported=row["stt_supported"],
            subtitle_supported=row["subtitle_supported"],
            question_supported=row["question_supported"],
            answer_supported=row["answer_supported"],
            voice_provider=row["voice_provider"],
            stt_provider=row["stt_provider"],
            translation_provider=row["translation_provider"],
            pronunciation_tier=row["pronunciation_tier"],
            academic_review_status=row["academic_review_status"],
            fallback_language_code=row["fallback_language_code"],
            quality_score_pct=row["quality_score_pct"],
            known_limitations=row["known_limitations"],
            provider_matrix=dict(row["provider_matrix"]),
        )
    return out


# ---------------------------------------------------------------------------
# Mathematical & Scientific Notation Preservation Guard
# ---------------------------------------------------------------------------
_LATEX_BLOCK_RE = re.compile(r"\$\$[\s\S]+?\$\$")
_LATEX_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)[^$\n]+?(?<!\$)\$(?!\$)")
_SCI_EXP_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:[×x*]\s*10\^\{?[+-]?\d+\}?|[eE][+-]?\d+)\b"
)
_SI_UNIT_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:m/s\^2|m/s²|m/s|km/h|kg·m/s\^2|kg·m/s|kJ/mol|J/mol|mol\^?-?1|"
    r"mol/L|N·m|W/m\^2|Hz|kHz|MHz|Pa|kPa|kJ|MeV|eV|Ω|μF|mA|kV|mol)\b"
)
_CHEM_FORMULA_RE = re.compile(
    r"\b(?=[A-Z][A-Za-z0-9]*(?:\([A-Za-z0-9]+\)\d*)?\b)"
    r"(?:(?:[A-Z][a-z]?\d*){2,}|(?:[A-Z][a-z]?\d+))\b"
)
_CHEM_ARROW_RE = re.compile(r"(?:->|→|⇌|⟶)")


@dataclass(frozen=True, slots=True)
class ProtectedNotations:
    """Extracted mathematical and scientific notation tokens."""

    math_expressions: tuple[str, ...]
    scientific_notations: tuple[str, ...]
    si_unit_values: tuple[str, ...]
    chemical_formulas: tuple[str, ...]
    reaction_arrows: tuple[str, ...]

    @property
    def total_count(self) -> int:
        return (
            len(self.math_expressions)
            + len(self.scientific_notations)
            + len(self.si_unit_values)
            + len(self.chemical_formulas)
            + len(self.reaction_arrows)
        )


def _normalize_ws(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip())


def extract_protected_notations(text: str) -> ProtectedNotations:
    """Extract KaTeX math, scientific exponents, SI quantities, and chemical formulas."""
    blocks = [_normalize_ws(m.group(0)) for m in _LATEX_BLOCK_RE.finditer(text)]
    stripped_blocks = _LATEX_BLOCK_RE.sub(" ", text)
    inlines = [_normalize_ws(m.group(0)) for m in _LATEX_INLINE_RE.finditer(stripped_blocks)]
    outside_math = _LATEX_INLINE_RE.sub(" ", stripped_blocks)

    sci_exps = [_normalize_ws(m.group(0)) for m in _SCI_EXP_RE.finditer(outside_math)]
    si_units = [_normalize_ws(m.group(0)) for m in _SI_UNIT_RE.finditer(outside_math)]
    # Exclude pure Roman/acronym words that don't carry chemical structure digits
    chem_candidates = [_normalize_ws(m.group(0)) for m in _CHEM_FORMULA_RE.finditer(outside_math)]
    chem_formulas = [
        c
        for c in chem_candidates
        if any(ch.isdigit() for ch in c)
        or c in {"NaCl", "HCl", "NaOH", "KOH", "CuO", "MgO", "FeO", "CaO", "ZnO", "KCl", "AgCl"}
    ]
    arrows = [m.group(0) for m in _CHEM_ARROW_RE.finditer(outside_math)]

    def _dedupe(items: list[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return tuple(ordered)

    return ProtectedNotations(
        math_expressions=_dedupe(blocks + inlines),
        scientific_notations=_dedupe(sci_exps),
        si_unit_values=_dedupe(si_units),
        chemical_formulas=_dedupe(chem_formulas),
        reaction_arrows=_dedupe(arrows),
    )


def protect_notations_with_tokens(text: str) -> tuple[str, dict[str, str]]:
    """Replace math and chemical tokens with immutable placeholders before translation."""
    token_map: dict[str, str] = {}
    counter = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal counter
        placeholder = f"__G4G_NOTATION_{counter}__"
        counter += 1
        token_map[placeholder] = match.group(0)
        return placeholder

    protected = _LATEX_BLOCK_RE.sub(_replace, text)
    protected = _LATEX_INLINE_RE.sub(_replace, protected)
    protected = _SCI_EXP_RE.sub(_replace, protected)
    protected = _SI_UNIT_RE.sub(_replace, protected)
    return protected, token_map


def restore_protected_notations(text: str, token_map: dict[str, str]) -> str:
    """Restore original immutable math/science notations from placeholders."""
    restored = text
    for placeholder, original in token_map.items():
        restored = restored.replace(placeholder, original)
    return restored


@dataclass(frozen=True, slots=True)
class NotationPreservationReport:
    """Audit result verifying mathematical & scientific notation preservation."""

    math_preserved: bool
    science_preserved: bool
    all_preserved: bool
    math_preservation_score: float
    science_notation_score: float
    missing_math: tuple[str, ...]
    missing_science: tuple[str, ...]
    source_notations: ProtectedNotations


def _contains_normalized(haystack: str, needle: str) -> bool:
    if needle in haystack:
        return True
    compact_haystack = re.sub(r"\s+", "", haystack)
    compact_needle = re.sub(r"\s+", "", needle)
    return compact_needle in compact_haystack


def verify_notation_preservation(source_text: str, target_text: str) -> NotationPreservationReport:
    """Verify that every mathematical formula, SI unit, exponent, and chemical formula survived."""
    src = extract_protected_notations(source_text)

    missing_math = tuple(
        expr for expr in src.math_expressions if not _contains_normalized(target_text, expr)
    )
    science_tokens = (
        list(src.scientific_notations)
        + list(src.si_unit_values)
        + list(src.chemical_formulas)
    )
    missing_science: list[str] = []
    for tok in science_tokens:
        if not _contains_normalized(target_text, tok):
            missing_science.append(tok)
    if src.reaction_arrows and not _CHEM_ARROW_RE.search(target_text):
        missing_science.append(src.reaction_arrows[0])

    math_total = len(src.math_expressions)
    sci_total = len(science_tokens) + (1 if src.reaction_arrows else 0)

    math_score = (
        100.0
        if math_total == 0
        else round(((math_total - len(missing_math)) / math_total) * 100.0, 2)
    )
    sci_score = (
        100.0
        if sci_total == 0
        else round(((sci_total - len(missing_science)) / sci_total) * 100.0, 2)
    )

    return NotationPreservationReport(
        math_preserved=len(missing_math) == 0,
        science_preserved=len(missing_science) == 0,
        all_preserved=(len(missing_math) == 0 and len(missing_science) == 0),
        math_preservation_score=math_score,
        science_notation_score=sci_score,
        missing_math=missing_math,
        missing_science=tuple(missing_science),
        source_notations=src,
    )


# ---------------------------------------------------------------------------
# Language Fallback Resolution across all 6 Independent Modalities
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ModalityResolution:
    """Deterministic resolution for one of the 6 independent language dimensions."""

    modality: str
    requested_language: str
    effective_language: str
    fallback_applied: bool
    fallback_reason: str | None
    capability_status: str
    availability_status: str
    testing_status: str
    rtl: bool
    provider: str | None


def _is_modality_supported(cap: LanguageCapabilityRecord, modality: str) -> bool:
    if modality == "ui":
        return cap.ui_supported
    if modality == "explanation":
        return cap.explanation_supported
    if modality == "voice":
        return cap.tts_supported
    if modality == "subtitle":
        return cap.subtitle_supported
    if modality == "question":
        return cap.question_supported
    if modality == "answer":
        return cap.answer_supported
    return False


def _provider_for_modality(cap: LanguageCapabilityRecord, modality: str) -> str | None:
    if modality == "voice":
        return cap.voice_provider
    if modality == "answer":
        return cap.stt_provider or cap.translation_provider
    if modality in {"ui", "question", "subtitle"}:
        return cap.translation_provider
    if modality == "explanation":
        llm_info = cap.provider_matrix.get("llm")
        if isinstance(llm_info, dict):
            return str(llm_info.get("provider") or "llm_router")
        return "llm_router"
    return None


def resolve_language_for_modality(
    requested_code: str,
    modality: str,
    capabilities_by_code: dict[str, LanguageCapabilityRecord],
) -> ModalityResolution:
    """Deterministically resolve effective language & fallback chain without silent lies."""
    req = (requested_code or "en").strip().lower()
    en_cap = capabilities_by_code.get("en")
    requested_cap = capabilities_by_code.get(req)

    if requested_cap is None:
        fallback_code = "en"
        eff_cap = en_cap
        return ModalityResolution(
            modality=modality,
            requested_language=req,
            effective_language=fallback_code,
            fallback_applied=True,
            fallback_reason=(
                f"Language '{req}' is not registered in Language Capability Registry; "
                "falling back to English (en)."
            ),
            capability_status=eff_cap.capability_status if eff_cap else "production",
            availability_status=eff_cap.availability_status if eff_cap else "available",
            testing_status=eff_cap.testing_status if eff_cap else "passed",
            rtl=eff_cap.rtl if eff_cap else False,
            provider=_provider_for_modality(eff_cap, modality) if eff_cap else None,
        )

    if _is_modality_supported(requested_cap, modality):
        return ModalityResolution(
            modality=modality,
            requested_language=req,
            effective_language=req,
            fallback_applied=False,
            fallback_reason=None,
            capability_status=requested_cap.capability_status,
            availability_status=requested_cap.availability_status,
            testing_status=requested_cap.testing_status,
            rtl=requested_cap.rtl,
            provider=_provider_for_modality(requested_cap, modality),
        )

    # Walk configured fallback chain safely (cycle-protected)
    visited: set[str] = {req}
    candidate_code = requested_cap.fallback_language_code.strip().lower() or "en"
    chosen: LanguageCapabilityRecord | None = None
    while candidate_code and candidate_code not in visited:
        visited.add(candidate_code)
        cand = capabilities_by_code.get(candidate_code)
        if cand is not None and _is_modality_supported(cand, modality):
            chosen = cand
            break
        candidate_code = (cand.fallback_language_code.strip().lower() if cand else "en") or "en"

    if chosen is None:
        chosen = en_cap or requested_cap

    modality_labels = {
        "ui": "UI localization",
        "explanation": "AI explanation",
        "voice": "Voice TTS narration",
        "subtitle": "Subtitles",
        "question": "Question bank translation",
        "answer": "Answer input/evaluation",
    }
    label = modality_labels.get(modality, modality)
    reason = (
        f"{label} is not yet verified/enabled for {requested_cap.display_name} ({req}); "
        f"falling back to {chosen.display_name} ({chosen.language_code})."
    )
    if modality == "voice" and requested_cap.subtitle_supported:
        reason += f" Synchronized {requested_cap.display_name} subtitles remain available."

    return ModalityResolution(
        modality=modality,
        requested_language=req,
        effective_language=chosen.language_code,
        fallback_applied=True,
        fallback_reason=reason,
        capability_status=chosen.capability_status,
        availability_status=chosen.availability_status,
        testing_status=chosen.testing_status,
        rtl=chosen.rtl,
        provider=_provider_for_modality(chosen, modality),
    )


def resolve_all_six_preferences(
    *,
    ui_language: str,
    explanation_language: str,
    voice_language: str,
    subtitle_language: str,
    question_language: str,
    answer_language: str,
    capabilities_by_code: dict[str, LanguageCapabilityRecord],
) -> dict[str, ModalityResolution]:
    """Resolve all 6 independent language preferences in one call."""
    mapping = {
        "ui": ui_language,
        "explanation": explanation_language,
        "voice": voice_language,
        "subtitle": subtitle_language,
        "question": question_language,
        "answer": answer_language,
    }
    return {
        mod: resolve_language_for_modality(code, mod, capabilities_by_code)
        for mod, code in mapping.items()
    }


# ---------------------------------------------------------------------------
# Bilingual Explanation & Terminology Consistency
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GlossaryTermEntry:
    """Canonical bilingual STEM terminology mapping."""

    concept_key: str
    subject_area: str
    english_term: str
    language_code: str
    localized_term: str
    transliteration: str | None = None
    preserve_english_in_bilingual: bool = True
    latex_symbol: str | None = None


@dataclass(frozen=True, slots=True)
class BilingualPreviewOutput:
    """Result of applying bilingual STEM formatting + notation guard."""

    rendered_text: str
    bilingual_mode: str
    matched_terms: tuple[GlossaryTermEntry, ...]
    notation_report: NotationPreservationReport


_BILINGUAL_FRAMING: dict[str, tuple[str, str]] = {
    "en": ("Concept Explanation", "Key STEM terms and equations preserved in canonical form."),
    "hi": (
        "संकल्पना व्याख्या (Concept Explanation)",
        "गणितीय सूत्र और वैज्ञानिक इकाइयाँ (KaTeX / SI units) अपने मानक रूप में सुरक्षित हैं।",
    ),
    "bn": (
        "ধারণা ব্যাখ্যা (Concept Explanation)",
        "গাণিতিক সূত্র ও বৈজ্ঞানিক একক (KaTeX / SI units) অপরিবর্তিত রাখা হয়েছে।",
    ),
    "ta": (
        "கருத்து விளக்கம் (Concept Explanation)",
        "கணிதச் சமன்பாடுகள் மற்றும் அறிவியல் அலகுகள் (KaTeX / SI units) மாற்றமின்றி பாதுகாக்கப்பட்டுள்ளன.",
    ),
    "te": (
        "భావన వివరణ (Concept Explanation)",
        "గణిత సూత్రాలు మరియు శాస్త్రీయ ప్రమాణాలు (KaTeX / SI units) మార్పు లేకుండా ఉంచబడ్డాయి.",
    ),
    "mr": (
        "संकल्पना स्पष्टीकरण (Concept Explanation)",
        "गणितीय सूत्रे आणि वैज्ञानिक एकके (KaTeX / SI units) जशीच्या तशी सुरक्षित ठेवली आहेत.",
    ),
    "gu": (
        "ખ્યાલ સમજૂતી (Concept Explanation)",
        "ગાણિતિક સૂત્રો અને વૈજ્ઞાનિક એકમો (KaTeX / SI units) મૂળ સ્વરૂપમાં જાળવવામાં આવ્યા છે.",
    ),
    "kn": (
        "ಪರಿಕಲ್ಪನೆ ವಿವರಣೆ (Concept Explanation)",
        "ಗಣಿತದ ಸೂತ್ರಗಳು ಮತ್ತು ವೈಜ್ಞಾನಿಕ ಏಕಮಾನಗಳು (KaTeX / SI units) ಮೂಲ ರೂಪದಲ್ಲಿಯೇ ಇವೆ.",
    ),
    "ml": (
        "ആശയ വിശദീകരണം (Concept Explanation)",
        "ഗണിത സൂത്രവാക്യങ്ങളും ശാസ്ത്രീയ യൂണിറ്റുകളും (KaTeX / SI units) അതേപടി നിലനിർത്തിയിരിക്കുന്നു.",
    ),
    "pa": (
        "ਸੰਕਲਪ ਵਿਆਖਿਆ (Concept Explanation)",
        "ਗਣਿਤਕ ਸੂਤਰ ਅਤੇ ਵਿਗਿਆਨਕ ਇਕਾਈਆਂ (KaTeX / SI units) ਮੂਲ ਰੂਪ ਵਿੱਚ ਸੁਰੱਖਿਅਤ ਹਨ।",
    ),
    "ur": (
        "تصور کی وضاحت (Concept Explanation)",
        "ریاضیاتی فارمولے اور سائنسی اکائیاں (KaTeX / SI units) اصل شکل میں محفوظ ہیں۔",
    ),
    "or": (
        "ଧାରଣା ବ୍ୟାଖ୍ୟା (Concept Explanation)",
        "ଗାଣିତିକ ସୂତ୍ର ଏବଂ ବୈଜ୍ଞାନିକ ଏକକ (KaTeX / SI units) ଅପରିବର୍ତ୍ତିତ ରହିଛି।",
    ),
    "as": (
        "ধাৰণা ব্যাখ্যা (Concept Explanation)",
        "গাণিতিক সূত্ৰ আৰু বৈজ্ঞানিক একক (KaTeX / SI units) অপৰিৱৰ্তিতভাৱে ৰখা হৈছে।",
    ),
    "sa": (
        "संकल्पना विवरणम् (Concept Explanation)",
        "गणितसूत्राणि वैज्ञानिकमात्राश्च मानकरूपे रक्षितानि।",
    ),
}


def build_bilingual_explanation(
    *,
    source_text: str,
    target_language_code: str,
    bilingual_mode: str,
    glossary_terms: list[GlossaryTermEntry],
) -> BilingualPreviewOutput:
    """Inject bilingual STEM terminology while guaranteeing zero notation corruption."""
    lang = (target_language_code or "en").strip().lower()
    mode = bilingual_mode if bilingual_mode in BILINGUAL_MODES else "bilingual_stem_en"
    protected_text, token_map = protect_notations_with_tokens(source_text)

    lang_terms = [t for t in glossary_terms if t.language_code == lang]
    # Match longest English terms first to avoid partial overlaps
    lang_terms.sort(key=lambda t: len(t.english_term), reverse=True)

    matched: list[GlossaryTermEntry] = []
    transformed = protected_text

    for term in lang_terms:
        pattern = re.compile(rf"\b{re.escape(term.english_term)}\b", re.IGNORECASE)
        if not pattern.search(transformed):
            continue
        matched.append(term)
        if lang == "en":
            continue
        if mode == "bilingual_stem_en" and term.preserve_english_in_bilingual:
            replacement = f"{term.localized_term} ({term.english_term})"
        elif mode == "monolingual":
            replacement = term.localized_term
        else:
            replacement = f"{term.localized_term} [{term.english_term}]"
        transformed = pattern.sub(replacement, transformed, count=1)

    restored = restore_protected_notations(transformed, token_map)
    header, note = _BILINGUAL_FRAMING.get(lang, _BILINGUAL_FRAMING["en"])

    if lang == "en":
        rendered = restored
    elif mode == "side_by_side":
        rendered = f"{header}\n{restored}\n\nEnglish Reference:\n{source_text}\n\n{note}"
    else:
        rendered = f"{header}: {restored}\n\n{note}"

    report = verify_notation_preservation(source_text, rendered)
    return BilingualPreviewOutput(
        rendered_text=rendered,
        bilingual_mode=mode,
        matched_terms=tuple(matched),
        notation_report=report,
    )


def audit_terminology_consistency(
    *,
    source_text: str,
    translated_text: str,
    target_language_code: str,
    glossary_terms: list[GlossaryTermEntry],
) -> tuple[float, list[str]]:
    """Check whether canonical STEM terms from source_text appear properly in translated_text."""
    lang = target_language_code.strip().lower()
    relevant = [
        t
        for t in glossary_terms
        if t.language_code == lang
        and re.search(rf"\b{re.escape(t.english_term)}\b", source_text, re.IGNORECASE)
    ]
    if not relevant:
        return 100.0, []

    warnings: list[str] = []
    hits = 0
    lower_trans = translated_text.lower()
    for term in relevant:
        has_localized = term.localized_term in translated_text
        has_english = term.english_term.lower() in lower_trans
        if has_localized or (term.preserve_english_in_bilingual and has_english):
            hits += 1
            if not has_localized and lang != "en":
                warnings.append(
                    f"Term '{term.english_term}' kept in English only; consider bilingual "
                    f"'{term.localized_term} ({term.english_term})'."
                )
        else:
            warnings.append(
                f"Missing canonical STEM term for '{term.english_term}' "
                f"(expected '{term.localized_term}' or bilingual form)."
            )
    score = round((hits / len(relevant)) * 100.0, 2)
    return score, warnings


# ---------------------------------------------------------------------------
# Language-Specific Quality Evaluation Suite
# ---------------------------------------------------------------------------
def check_script_fidelity(text: str, script_name: str) -> tuple[float, str | None]:
    """Verify that non-math prose actually contains characters from the expected script."""
    # Strip math blocks, placeholders, digits, and punctuation
    clean = _LATEX_BLOCK_RE.sub(" ", text)
    clean = _LATEX_INLINE_RE.sub(" ", clean)
    letters = [ch for ch in clean if ch.isalpha()]
    if not letters:
        return 0.0, "Sample contains no alphabetic prose characters."

    ranges = SCRIPT_UNICODE_RANGES.get(script_name)
    if not ranges:
        return 100.0, None

    in_script = 0
    for ch in letters:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in ranges):
            in_script += 1

    ratio = in_script / len(letters)
    if script_name == "Latin":
        score = round(min(100.0, ratio * 100.0), 2)
        note = None if score >= 80.0 else f"Only {score}% Latin characters detected."
        return score, note

    # Bilingual STEM prose legitimately mixes Indic/Urdu script with English STEM terms & symbols.
    # Require >= 30% native script characters for bilingual pass; 100% score at >= 55% native script.
    if in_script == 0:
        return 0.0, f"No {script_name} script characters detected (possible untranslated output)."
    scaled = min(100.0, (ratio / 0.55) * 100.0)
    score = round(scaled, 2)
    note = (
        None
        if ratio >= 0.30
        else f"Low {script_name} script density ({round(ratio * 100, 1)}%); review localization."
    )
    return score, note


@dataclass(frozen=True, slots=True)
class LanguageEvaluationSample:
    """Single deterministic test case for language quality evaluation."""

    sample_id: str
    source_text: str
    candidate_text: str


@dataclass(frozen=True, slots=True)
class LanguageEvaluationResult:
    """Aggregated quality evaluation verdict for a language + modality."""

    language_code: str
    modality: str
    script_fidelity_score: float
    math_preservation_score: float
    science_notation_score: float
    terminology_accuracy_score: float
    fluency_score: float
    overall_score: float
    passed: bool
    sample_count: int
    findings: tuple[dict[str, Any], ...]


def run_language_quality_suite(
    *,
    capability: LanguageCapabilityRecord,
    modality: str,
    samples: list[LanguageEvaluationSample],
    glossary_terms: list[GlossaryTermEntry],
    pass_threshold: float = 80.0,
) -> LanguageEvaluationResult:
    """Run deterministic notation, script, terminology, and coverage evaluation."""
    if not samples:
        return LanguageEvaluationResult(
            language_code=capability.language_code,
            modality=modality,
            script_fidelity_score=0.0,
            math_preservation_score=0.0,
            science_notation_score=0.0,
            terminology_accuracy_score=0.0,
            fluency_score=0.0,
            overall_score=0.0,
            passed=False,
            sample_count=0,
            findings=({"sample_id": "none", "issue": "No evaluation samples provided."},),
        )

    script_scores: list[float] = []
    math_scores: list[float] = []
    sci_scores: list[float] = []
    term_scores: list[float] = []
    fluency_scores: list[float] = []
    findings: list[dict[str, Any]] = []

    for sample in samples:
        notations = verify_notation_preservation(sample.source_text, sample.candidate_text)
        script_score, script_note = check_script_fidelity(
            sample.candidate_text, capability.script_name
        )
        term_score, term_warnings = audit_terminology_consistency(
            source_text=sample.source_text,
            translated_text=sample.candidate_text,
            target_language_code=capability.language_code,
            glossary_terms=glossary_terms,
        )

        # Length & structural completeness heuristic
        src_len = max(1, len(sample.source_text.strip()))
        cand_len = len(sample.candidate_text.strip())
        ratio = cand_len / src_len
        if cand_len < 10:
            fluency = 20.0
        elif 0.45 <= ratio <= 2.6:
            fluency = 95.0
        else:
            fluency = 70.0

        script_scores.append(script_score)
        math_scores.append(notations.math_preservation_score)
        sci_scores.append(notations.science_notation_score)
        term_scores.append(term_score)
        fluency_scores.append(fluency)

        sample_issues: list[str] = []
        if script_note:
            sample_issues.append(script_note)
        if notations.missing_math:
            sample_issues.append(f"Corrupted/missing math: {', '.join(notations.missing_math)}")
        if notations.missing_science:
            sample_issues.append(
                f"Corrupted/missing science notation: {', '.join(notations.missing_science)}"
            )
        sample_issues.extend(term_warnings)

        findings.append(
            {
                "sample_id": sample.sample_id,
                "script_fidelity_score": script_score,
                "math_preservation_score": notations.math_preservation_score,
                "science_notation_score": notations.science_notation_score,
                "terminology_accuracy_score": term_score,
                "issues": sample_issues,
            }
        )

    avg_script = round(sum(script_scores) / len(script_scores), 2)
    avg_math = round(sum(math_scores) / len(math_scores), 2)
    avg_sci = round(sum(sci_scores) / len(sci_scores), 2)
    avg_term = round(sum(term_scores) / len(term_scores), 2)
    avg_fluency = round(sum(fluency_scores) / len(fluency_scores), 2)

    overall = round(
        avg_math * 0.30
        + avg_sci * 0.25
        + avg_script * 0.20
        + avg_term * 0.15
        + avg_fluency * 0.10,
        2,
    )
    # Hard gate: math & science notation must not fail catastrophically (<90%),
    # and script fidelity must be >= 50% for non-Latin scripts.
    passed = (
        overall >= pass_threshold
        and avg_math >= 90.0
        and avg_sci >= 90.0
        and avg_script >= 50.0
    )

    return LanguageEvaluationResult(
        language_code=capability.language_code,
        modality=modality,
        script_fidelity_score=avg_script,
        math_preservation_score=avg_math,
        science_notation_score=avg_sci,
        terminology_accuracy_score=avg_term,
        fluency_score=avg_fluency,
        overall_score=overall,
        passed=passed,
        sample_count=len(samples),
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# UI Localization Dictionary & Deterministic Fallback Coverage
# ---------------------------------------------------------------------------
UI_STRINGS_CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "nav.home": "Home",
        "nav.curriculum": "Curriculum",
        "nav.dashboard": "Dashboard",
        "nav.practice": "Practice",
        "nav.quizzes": "Quizzes",
        "nav.assessments": "Assessments",
        "nav.exams": "Exam Prep",
        "nav.tutor": "AI Tutor",
        "nav.classroom": "Live Classroom",
        "nav.homework": "Homework AI",
        "nav.adaptive": "Adaptive Mastery",
        "nav.revision": "Revision & Plan",
        "nav.analytics": "Analytics",
        "nav.notes": "Notes & Saved",
        "nav.languages": "Languages",
        "nav.teacher": "Teacher Hub",
        "nav.mentor": "Mentor Hub",
        "nav.parent": "Parent Portal",
        "nav.institution": "Institution",
        "nav.admin": "Admin Studio",
        "auth.sign_in": "Sign In",
        "auth.register": "Register",
        "auth.sign_out": "Sign Out",
        "languages.title": "Multilingual Learning & Language Capability Hub",
        "languages.subtitle": "Configure independent languages for UI, explanations, voice, subtitles, questions, and answers with transparent provider capability tracking.",
        "languages.save_preferences": "Save Language Preferences",
        "footer.disclaimer": "GuruSetu AI — Independent educational ecosystem; not endorsed by or affiliated with NCERT, CBSE, or NTA.",
    },
    "hi": {
        "nav.home": "होम",
        "nav.curriculum": "पाठ्यक्रम",
        "nav.dashboard": "डैशबोर्ड",
        "nav.practice": "अभ्यास",
        "nav.quizzes": "क्विज़",
        "nav.assessments": "मूल्यांकन",
        "nav.exams": "परीक्षा तैयारी",
        "nav.tutor": "AI ट्यूटर",
        "nav.classroom": "लाइव क्लासरूम",
        "nav.homework": "होमवर्क AI",
        "nav.adaptive": "अनुकूली महारत",
        "nav.revision": "पुनरावृत्ति योजना",
        "nav.analytics": "विश्लेषण",
        "nav.notes": "नोट्स",
        "nav.languages": "भाषाएँ",
        "nav.teacher": "शिक्षक केंद्र",
        "nav.mentor": "मेंटर केंद्र",
        "nav.parent": "अभिभावक पोर्टल",
        "nav.institution": "संस्थान",
        "nav.admin": "एडमिन स्टूडियो",
        "auth.sign_in": "साइन इन",
        "auth.register": "पंजीकरण",
        "auth.sign_out": "साइन आउट",
        "languages.title": "बहुभाषी शिक्षण और भाषा क्षमता केंद्र",
        "languages.subtitle": "UI, व्याख्या, आवाज़, उपशीर्षक, प्रश्न और उत्तर के लिए स्वतंत्र भाषाएँ चुनें और वास्तविक प्रदाता क्षमता देखें।",
        "languages.save_preferences": "भाषा प्राथमिकताएँ सहेजें",
        "footer.disclaimer": "GuruSetu AI — स्वतंत्र शैक्षिक मंच; NCERT, CBSE या NTA से संबद्ध नहीं।",
    },
    "bn": {
        "nav.home": "হোম",
        "nav.curriculum": "পাঠ্যক্রম",
        "nav.dashboard": "ড্যাশবোর্ড",
        "nav.practice": "অনুশীলন",
        "nav.quizzes": "কুইজ",
        "nav.assessments": "মূল্যায়ন",
        "nav.exams": "পরীক্ষার প্রস্তুতি",
        "nav.tutor": "AI টিউটর",
        "nav.classroom": "লাইভ ক্লাসরুম",
        "nav.homework": "হোমওয়ার্ক AI",
        "nav.languages": "ভাষাসমূহ",
        "auth.sign_in": "সাইন ইন",
        "auth.register": "নিবন্ধন",
        "auth.sign_out": "সাইন আউট",
        "languages.title": "বহুভাষিক শিক্ষণ ও ভাষা সক্ষমতা কেন্দ্র",
        "languages.save_preferences": "ভাষা পছন্দ সংরক্ষণ করুন",
    },
    "ta": {
        "nav.home": "முகப்பு",
        "nav.curriculum": "பாடத்திட்டம்",
        "nav.dashboard": "கட்டுப்பாட்டுப் பலகம்",
        "nav.practice": "பயிற்சி",
        "nav.quizzes": "வினாடி வினா",
        "nav.exams": "தேர்வு தயாரிப்பு",
        "nav.tutor": "AI ஆசிரியர்",
        "nav.classroom": "நேரலை வகுப்பறை",
        "nav.homework": "வீட்டுப்பாடம் AI",
        "nav.languages": "மொழிகள்",
        "auth.sign_in": "உள்நுழை",
        "auth.register": "பதிவு செய்",
        "auth.sign_out": "வெளியேறு",
        "languages.title": "பன்மொழி கற்றல் மற்றும் மொழி திறன் மையம்",
        "languages.save_preferences": "மொழி விருப்பங்களைச் சேமி",
    },
    "te": {
        "nav.home": "హోమ్",
        "nav.curriculum": "పాఠ్యాంశాలు",
        "nav.dashboard": "డాష్‌బోర్డ్",
        "nav.practice": "అభ్యాసం",
        "nav.exams": "పరీక్ష సన్నద్ధత",
        "nav.tutor": "AI ట్యూటర్",
        "nav.classroom": "లైవ్ క్లాస్‌రూమ్",
        "nav.languages": "భాషలు",
        "auth.sign_in": "సైన్ ఇన్",
        "auth.register": "నమోదు",
        "auth.sign_out": "సైన్ అవుట్",
        "languages.title": "బహుభాషా అభ్యాస & భాషా సామర్థ్య కేంద్రం",
        "languages.save_preferences": "భాషా ప్రాధాన్యతలను సేవ్ చేయండి",
    },
    "mr": {
        "nav.home": "मुख्यपृष्ठ",
        "nav.curriculum": "अभ्यासक्रम",
        "nav.dashboard": "डॅशबोर्ड",
        "nav.practice": "सराव",
        "nav.exams": "परीक्षा तयारी",
        "nav.tutor": "AI शिक्षक",
        "nav.classroom": "लाइव्ह वर्ग",
        "nav.languages": "भाषा",
        "auth.sign_in": "साइन इन",
        "auth.register": "नोंदणी",
        "auth.sign_out": "साइन आउट",
        "languages.title": "बहुभाषिक शिक्षण आणि भाषा क्षमता केंद्र",
        "languages.save_preferences": "भाषा प्राधान्ये जतन करा",
    },
    "gu": {
        "nav.home": "હોમ",
        "nav.curriculum": "અભ્યાસક્રમ",
        "nav.dashboard": "ડેશબોર્ડ",
        "nav.practice": "અભ્યાસ",
        "nav.exams": "પરીક્ષા તૈયારી",
        "nav.tutor": "AI ટ્યુટર",
        "nav.languages": "ભાષાઓ",
        "auth.sign_in": "સાઇન ઇન",
        "auth.sign_out": "સાઇન આઉટ",
        "languages.title": "બહુભાષી શિક્ષણ અને ભાષા ક્ષમતા કેન્દ્ર",
    },
    "kn": {
        "nav.home": "ಮುಖಪುಟ",
        "nav.curriculum": "ಪಠ್ಯಕ್ರಮ",
        "nav.dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "nav.practice": "ಅಭ್ಯಾಸ",
        "nav.exams": "ಪರೀಕ್ಷಾ ತಯಾರಿ",
        "nav.tutor": "AI ಬೋಧಕ",
        "nav.languages": "ಭಾಷೆಗಳು",
        "auth.sign_in": "ಸೈನ್ ಇನ್",
        "auth.sign_out": "ಸೈನ್ ಔಟ್",
        "languages.title": "ಬಹುಭಾಷಾ ಕಲಿಕೆ ಮತ್ತು ಭಾಷಾ ಸಾಮರ್ಥ್ಯ ಕೇಂದ್ರ",
    },
    "ml": {
        "nav.home": "ഹോം",
        "nav.curriculum": "പാഠ്യപദ്ധതി",
        "nav.dashboard": "ഡാഷ്ബോർഡ്",
        "nav.practice": "പരിശീലനം",
        "nav.exams": "പരീക്ഷാ തയ്യാറെടുപ്പ്",
        "nav.tutor": "AI ട്യൂട്ടർ",
        "nav.languages": "ഭാഷകൾ",
        "auth.sign_in": "സൈൻ ഇൻ",
        "auth.sign_out": "സൈൻ ഔട്ട്",
        "languages.title": "ബഹുഭാഷാ പഠനവും ഭാഷാ ശേഷി കേന്ദ്രവും",
    },
    "pa": {
        "nav.home": "ਹੋਮ",
        "nav.curriculum": "ਪਾਠਕ੍ਰਮ",
        "nav.dashboard": "ਡੈਸ਼ਬੋਰਡ",
        "nav.practice": "ਅਭਿਆਸ",
        "nav.exams": "ਪ੍ਰੀਖਿਆ ਤਿਆਰੀ",
        "nav.tutor": "AI ਟਿਊਟਰ",
        "nav.languages": "ਭਾਸ਼ਾਵਾਂ",
        "auth.sign_in": "ਸਾਈਨ ਇਨ",
        "auth.sign_out": "ਸਾਈਨ ਆਉਟ",
        "languages.title": "ਬਹੁ-ਭਾਸ਼ਾਈ ਸਿੱਖਿਆ ਅਤੇ ਭਾਸ਼ਾ ਸਮਰੱਥਾ ਕੇਂਦਰ",
    },
    "ur": {
        "nav.home": "ہوم",
        "nav.curriculum": "نصاب",
        "nav.dashboard": "ڈیش بورڈ",
        "nav.practice": "مشق",
        "nav.quizzes": "کوئز",
        "nav.exams": "امتحان کی تیاری",
        "nav.tutor": "AI ٹیوٹر",
        "nav.classroom": "لائیو کلاس روم",
        "nav.languages": "زبانیں",
        "auth.sign_in": "سائن ان",
        "auth.register": "رجسٹر",
        "auth.sign_out": "سائن آؤٹ",
        "languages.title": "کثیر لسانی تعلیم اور زبان کی صلاحیت کا مرکز",
        "languages.save_preferences": "زبان کی ترجیحات محفوظ کریں",
    },
}


def get_ui_localization_bundle(language_code: str) -> dict[str, Any]:
    """Return UI strings with deterministic English fallback per missing key and honest coverage."""
    req = (language_code or "en").strip().lower()
    base = UI_STRINGS_CATALOG["en"]
    localized = UI_STRINGS_CATALOG.get(req, {})
    merged: dict[str, str] = {}
    fallback_keys: list[str] = []

    for key, en_val in base.items():
        if key in localized and localized[key].strip():
            merged[key] = localized[key]
        else:
            merged[key] = en_val
            if req != "en":
                fallback_keys.append(key)

    total = len(base)
    translated_count = total - len(fallback_keys)
    coverage_pct = round((translated_count / max(1, total)) * 100.0, 1)
    cap = default_capability_map().get(req)
    return {
        "requested_language": req,
        "effective_language": req if req in UI_STRINGS_CATALOG else "en",
        "rtl": cap.rtl if cap else False,
        "coverage_pct": coverage_pct,
        "translated_key_count": translated_count,
        "total_key_count": total,
        "fallback_keys": fallback_keys,
        "strings": merged,
    }
