---
trigger: model_decision
description: Rules for independent language preferences, Language Capability Registry honesty, bilingual STEM terminology preservation, KaTeX notation, and localization quality review.
---

# Multilingual Support Rules

Reference: [docs/VOICE_MULTILINGUAL_ARCHITECTURE.md](../../docs/VOICE_MULTILINGUAL_ARCHITECTURE.md).

1. **Six Independent Language Preferences:** Store and honor `ui_language`, `explanation_language`, `voice_language`, `subtitle_language`, `question_language`, and `answer_language` independently on every user profile. Switching explanation or subtitle language MUST NOT unexpectedly alter UI chrome or question language unless configured.
2. **Truthful Language Capability Registry:** Drive all language, voice, and STT selectors dynamically from `language_capabilities`. Never advertise unsupported languages or enable TTS/STT for languages marked `tts_supported = false` / `stt_supported = false` or `academic_review_status != 'approved'`.
3. **Bilingual & STEM Notation Integrity:** Support bilingual explanations (e.g., Hindi/regional prose preserving canonical English STEM terms via `terminology_glossary`). Never translate or corrupt LaTeX equations (`$...$`), SI units, or chemical formulas (`H_2SO_4`).
4. **Translation Review & Fallbacks:** Separate `machine_draft` translations from `human_reviewed` / `approved` translations; provide transparent language fallback notices and prepare RTL layout support (`dir="rtl"`) for Urdu (`ur`) plus proper `lang` attributes for screen readers.
