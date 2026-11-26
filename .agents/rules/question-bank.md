---
trigger: model_decision
description: Rules for the canonical Question Bank, 18+ question types, PYQ provenance verification, answer redaction, and the 14-stage Excel ingestion pipeline.
---

# Question Bank & Excel Ingestion Rules

Reference: [docs/QUESTION_BANK_SCHEMA.md](../../docs/QUESTION_BANK_SCHEMA.md), [docs/EXCEL_IMPORT_SPECIFICATION.md](../../docs/EXCEL_IMPORT_SPECIFICATION.md).

1. **Versioned Canonical Schema:** Store permanent identity in `questions` and immutable content in `question_versions` (supporting `mcq_single`, `mcq_multiple`, `numerical`, `integer`, `assertion_reason`, `case_based`, `match_following`, `matrix_match`, `short_answer`, `long_answer`, `essay`, `diagram_based`, `passage_based`, `comprehension`, `map_based`, `image_based`, `audio_based`, `extensible_json`). Assessments MUST pin `question_version_id`.
2. **Strict PYQ Provenance:** Never set `is_pyq = true` on AI-generated or unverified questions. Genuine PYQs require verified `exam_name`, `exam_year`, `verification_status = 'verified'`, `verified_by`, and available `session`/`shift`/`paper_code`/`source_url` metadata.
3. **AI-Generated Question Labeling:** AI-generated questions MUST carry `ai_generated = true`, `source_type = 'ai_generated'`, pass schema + verifier + dedup checks, and obtain `academic_reviewer` approval before entering official exams.
4. **Answer Key Redaction:** Never serialize `correct_answer_jsonb`, `question_options.is_correct`, or `question_solutions` in student-facing active quiz/assessment payloads.
5. **14-Stage Excel Ingestion Rules:**
   - Never modify original `.xlsx`/`.csv` files; archive immutable copies by SHA-256 in private object storage.
   - Never hardcode assumed Excel sheet/column names; use dynamic sheet inspection + interactive admin Column Mapping into `import_staging_rows`.
   - Neutralize Excel formula injection (`=`, `+`, `-`, `@`), deduplicate via `canonical_hash`, validate answers vs options, generate row-level error reports, and support idempotent re-runs + batch rollback prior to publishing.
