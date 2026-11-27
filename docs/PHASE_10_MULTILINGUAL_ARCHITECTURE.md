# Phase 10: Multilingual Learning Expansion Architecture (`docs/PHASE_10_MULTILINGUAL_ARCHITECTURE.md`)

**Status:** Implemented (Backend pure logic, Alembic migration `0011`, REST APIs, Voice TTS/STT abstraction, Next.js `/languages` Multilingual Learning Studio, global `LanguageProvider` with RTL/LTR KaTeX isolation, and automated unit + UI tests verified; live PostgreSQL 18 integration pytest & external provider keys pending host configuration).

---

## 1. Guiding Principles & Honesty Policy

1. **Zero Universal Parity Claims:** Go4Guru tracks 14 initial Indian & English language tracks (`en`, `hi`, `bn`, `ta`, `te`, `mr`, `gu`, `kn`, `ml`, `pa`, `ur`, `or`, `as`, `sa`) and supports adding any provider-evaluated language via the registry. Each language explicitly records:
   - `capability_status` (`production` | `beta` | `experimental` | `planned`)
   - `testing_status` (`passed` | `partial` | `pending` | `failed`)
   - `availability_status` (`available` | `limited` | `provider_key_required` | `unavailable`)
   - `quality_score_pct`, `last_evaluated_at`, `provider_matrix_jsonb` (per-modality LLM/TTS/STT/translation provider statuses), and explicit `known_limitations`.
2. **Six Independent Language Modalities:** Stored on `user_profiles` and exposed via `GET/PUT /api/v1/languages/preferences`:
   - `ui_language`
   - `preferred_explanation_language`
   - `preferred_voice_language`
   - `preferred_subtitle_language`
   - `preferred_question_language`
   - `preferred_answer_language`
   - Plus `bilingual_explanation_mode` (`monolingual` | `bilingual_stem_en` | `side_by_side`).
3. **Deterministic Fallback Resolution:** Every modality resolves independently against `language_capabilities`. Unsupported modalities follow `fallback_language_code -> en` with cycle protection and return an explicit `fallback_reason` (for example, Odia voice falls back to Hindi/English voice while keeping synchronized Odia subtitles active).
4. **Mathematical & Scientific Notation Preservation:**
   - LaTeX expressions (`$...$`, `$$...$$`), scientific notation (`6.022 × 10^23`), SI units (`9.8 m/s^2`, `kJ/mol`), and chemical formulas (`2H2 + O2 -> 2H2O`, `H2SO4`, `NaCl`) are extracted, tokenized during localization, and verified post-translation.
   - `<MathText />` forces `dir="ltr"` on rendered KaTeX blocks so equations never flip when Urdu (`ur`) activates `<html dir="rtl">`.

---

## 2. Database Schema (Migration `0011_phase10_multilingual_expansion.py`)

- **`language_capabilities` (Expanded):** Added `script_name`, `capability_status`, `testing_status`, `availability_status`, `ui_supported`, `explanation_supported`, `bilingual_supported`, `stt_provider`, `translation_provider`, `question_supported`, `answer_supported`, `fallback_language_code`, `quality_score_pct`, `last_evaluated_at`, and `provider_matrix_jsonb`. Idempotently upserted all 14 canonical languages with empirical statuses.
- **`user_profiles` (Expanded):** Added `bilingual_explanation_mode` alongside the 6 existing independent language columns.
- **`voice_usage_logs` (Expanded):** Added `operation_type` (`tts` | `stt`) to meter speech-to-text alongside text-to-speech.
- **`multilingual_glossary_terms` (New):** Bilingual STEM terminology dictionary preserving English NCERT/JEE/NEET terms, transliterations, and LaTeX symbols (`22` verified seed rows).
- **`translation_entries` (New):** Versioned translation review workflow with automated `notation_preserved`, `terminology_warnings_jsonb`, `quality_score`, reviewer audit fields, and status transitions (`pending_review` -> `approved` | `needs_revision` | `rejected`).
- **`language_quality_evaluations` (New):** Persisted language-specific QA evaluation runs tracking `script_fidelity_score`, `math_preservation_score`, `science_notation_score`, `terminology_accuracy_score`, `fluency_score`, `overall_score`, `passed`, and per-sample `findings_jsonb`.
- **RBAC Permissions:** Seeded `multilingual:read`, `multilingual:translate`, `multilingual:review`, and `multilingual:manage`.

---

## 3. API Surface

### `/api/v1/languages/*` (`classroom/multilingual_router.py`)
- `GET /api/v1/languages/capabilities` — Public empirical Language Capability Registry.
- `PATCH /api/v1/languages/capabilities/{language_code}` — Governance update (`academic_reviewer`, `content_admin`, `platform_admin`).
- `GET /api/v1/languages/preferences` / `PUT /api/v1/languages/preferences` — Authenticated 6-modality preferences + per-modality fallback resolutions.
- `GET /api/v1/languages/ui-bundle/{language_code}` — UI localization catalog with English per-key fallback & coverage percentage.
- `GET /api/v1/languages/glossary` / `POST /api/v1/languages/glossary` — STEM terminology dictionary & authorized upsert.
- `POST /api/v1/languages/bilingual-preview` — Live bilingual STEM preview, KaTeX notation preservation audit, speakable math narration, and matched glossary terms.
- `GET /api/v1/languages/translations`, `POST /api/v1/languages/translations`, `POST /api/v1/languages/translations/{entry_id}/review` — Translation infrastructure & academic review queue.
- `GET /api/v1/languages/evaluations`, `POST /api/v1/languages/evaluations/run` — Empirical language quality evaluation suite.

### `/api/v1/voice/*` (`classroom/multilingual_router.py` & `voice/provider.py`)
- `GET /api/v1/voice/capabilities` — Honest TTS & STT provider configuration status (ElevenLabs `eleven_multilingual_v2` & `scribe_v1`).
- `POST /api/v1/voice/stt` — Speech-to-text behind `VoiceProviderInterface.transcribe_audio`, logging `voice_usage_logs(operation_type='stt')` and returning an honest `text_input` fallback whenever credentials are absent or the requested language is unverified.

---

## 4. Verification & Limitations

- **Pure Python Language Evaluation Tests:** `apps/api/tests/unit/test_phase10_multilingual_logic.py` (11/11 passing) verifies all 14 languages' Unicode script fidelity, LaTeX/SI/chemical notation preservation & corruption detection, 6-modality fallback resolution, bilingual formatting, UI localization fallback coverage, and evaluation scoring.
- **PostgreSQL 18 Integration Tests:** `apps/api/tests/integration/test_phase10_multilingual_pg.py` (syntax-checked; execute via `alembic upgrade head && pytest apps/api/tests/integration/test_phase10_multilingual_pg.py` on the Python 3.12 + PG18 host).
- **Frontend Unit & UI Tests:** `apps/web/src/lib/multilingual-helpers.test.ts` (`node:test`) and `apps/web/tests/phase10.test.tsx` (Vitest) verify all 5 studio tabs, Urdu RTL + LTR math isolation, honest fallback notices, bilingual lab, glossary, translation review, and quality eval runner.
- **External Providers:** Live ElevenLabs TTS/STT audio requires `ELEVENLABS_API_KEY`; live LLM multilingual tutoring requires `GEMINI_API_KEY` or `OPENAI_API_KEY`. No synthetic audio or fake transcripts are generated when keys are absent.
