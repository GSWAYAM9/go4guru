# Database Schema Design (`docs/DATABASE_SCHEMA.md`)

**Engine:** PostgreSQL 18 + `pgvector` extension (Phase 3+)  
**Identifiers:** UUIDv7 (time-ordered UUIDs for index locality) or `gen_random_uuid()`  
**Conventions:** `created_at` (`timestamptz`), `updated_at` (`timestamptz`), `deleted_at` (`timestamptz` nullable for soft-delete where appropriate), explicit foreign keys, `CHECK` constraints, `tenant_id` scoping on all tenant-owned records, relational normalization (JSONB reserved strictly for genuinely polymorphic metadata/configurations).

---

## 1. Domain Schemas & Core Tables

### 1.1 Identity & Privacy (`identity`)
- `users`: `id (PK)`, `email (unique nullable)`, `phone_e164 (unique nullable)`, `password_hash` (Argon2id), `status` (`active|suspended|pending_parent_consent|deleted`), `date_of_birth_year`, `is_minor (bool)`, `mfa_enabled (bool)`, `mfa_secret_enc`, `last_login_at`, `created_at`, `updated_at`, `deleted_at`.
- `user_profiles`: `user_id (PK, FK->users)`, `display_name`, `avatar_url`, `timezone`, `ui_language`, `preferred_explanation_language`, `preferred_voice_language`, `preferred_subtitle_language`, `preferred_question_language`.
- `auth_providers`: `id (PK)`, `user_id (FK)`, `provider` (`local|google|school_sso`), `provider_subject_id`, `verified_at`.
- `roles`: `id (PK)`, `code (unique)` (`student|parent|teacher|mentor|school_admin|content_admin|academic_reviewer|platform_admin`), `description`.
- `permissions`: `id (PK)`, `code (unique)` (e.g., `question:approve`, `ai_chat:read_own`), `resource`, `action`.
- `role_permissions`: `role_id (FK)`, `permission_id (FK)`, PK `(role_id, permission_id)`.
- `user_roles`: `id (PK)`, `user_id (FK)`, `role_id (FK)`, `tenant_id (FK->organizations nullable)`, `granted_by (FK)`, `created_at`, `revoked_at`.
- `sessions`: `id (PK)`, `user_id (FK)`, `refresh_token_hash`, `device_id (FK->devices)`, `ip_hash`, `expires_at`, `revoked_at`.
- `devices`: `id (PK)`, `user_id (FK)`, `device_fingerprint_hash`, `platform` (`web|android|ios`), `push_token_enc`, `last_seen_at`.
- `audit_logs` *(append-only)*: `id (PK)`, `actor_user_id`, `tenant_id`, `action`, `resource_type`, `resource_id`, `metadata_jsonb`, `ip_hash`, `correlation_id`, `created_at`.

### 1.2 Student & Parent Consent (`student`)
- `student_profiles`: `user_id (PK, FK->users)`, `board_id (FK)`, `academic_session_id (FK)`, `grade_id (FK)`, `curriculum_version_id (FK)`, `primary_exam_target` (`cbse_board|jee_main|jee_advanced|neet|foundation`), `daily_study_minutes_target`, `onboarding_completed_at`.
- `student_preferences`: `student_id (PK, FK)`, `default_tutor_mode`, `voice_speed`, `selected_voice_id`, `bilingual_mode (bool)`, `accessibility_prefs_jsonb`.
- `student_goals`: `id (PK)`, `student_id (FK)`, `goal_type`, `target_exam_code`, `target_date`, `target_score_or_percentile`, `status`, `created_by (FK->users)`.
- `consents`: `id (PK)`, `student_user_id (FK)`, `guardian_user_id (FK nullable)`, `consent_type` (`minor_platform_usage|parent_link|ai_processing|billing`), `policy_version`, `status` (`pending|granted|withdrawn`), `verification_method`, `granted_at`, `withdrawn_at`, `evidence_jsonb`.
- `parent_links`: `id (PK)`, `parent_user_id (FK)`, `student_user_id (FK)`, `relationship` (`mother|father|legal_guardian`), `consent_id (FK->consents)`, `status` (`pending|active|revoked`), `privacy_settings_jsonb` (never unlocks raw AI chats), UNIQUE `(parent_user_id, student_user_id)`.

### 1.3 Multi-Tenant Organization (`organization`)
- `organizations`: `id (PK)`, `name`, `slug (unique)`, `org_type` (`school_group|coaching_institute|standalone_school`), `status`, `config_jsonb`.
- `schools`: `id (PK)`, `organization_id (FK)`, `name`, `board_affiliation_code`, `udise_or_reg_no`.
- `branches`: `id (PK)`, `school_id (FK)`, `organization_id (FK)`, `name`, `city`, `state`, `timezone`.
- `academic_years`: `id (PK)`, `organization_id (FK)`, `label` (`2026-27`), `starts_on`, `ends_on`, `is_active`.
- `classes`: `id (PK)`, `organization_id (FK)`, `branch_id (FK)`, `academic_year_id (FK)`, `grade_id (FK)`, `name`.
- `sections`: `id (PK)`, `organization_id (FK)`, `class_id (FK)`, `name` (`Section A`, `JEE Batch 1`), `capacity`.
- `enrollments`: `id (PK)`, `organization_id (FK)`, `section_id (FK)`, `student_user_id (FK)`, `roll_number`, `status` (`active|transferred|completed`), `enrolled_at`.
- `staff_assignments`: `id (PK)`, `organization_id (FK)`, `user_id (FK)`, `role_code` (`teacher|mentor|school_admin`), `branch_id (FK nullable)`, `section_id (FK nullable)`, `subject_id (FK nullable)`.

### 1.4 Curriculum (`curriculum`)
- `boards`: `id (PK)`, `code` (`CBSE|NCERT|ICSE`), `name`, `country`.
- `academic_sessions`: `id (PK)`, `code` (`2026-27`), `starts_on`, `ends_on`.
- `curriculum_versions`: `id (PK)`, `board_id (FK)`, `academic_session_id (FK)`, `version_tag`, `status` (`draft|published|archived`), `published_at`.
- `grades`: `id (PK)`, `number` (`6..12`), `label` (`Class 6..12`).
- `subjects`: `id (PK)`, `code`, `name`, `discipline` (`mathematics|science|physics|chemistry|biology|botany|zoology|english|social_science`).
- `books`: `id (PK)`, `curriculum_version_id (FK)`, `grade_id (FK)`, `subject_id (FK)`, `title`, `publisher`, `official_source_url`, `edition_year`.
- `chapters`: `id (PK)`, `book_id (FK)`, `sequence_no`, `code`, `title`, `summary`.
- `sections`: `id (PK)`, `chapter_id (FK)`, `sequence_no`, `title`.
- `topics`: `id (PK)`, `chapter_id (FK)`, `section_id (FK nullable)`, `sequence_no`, `title`.
- `concepts`: `id (PK)`, `topic_id (FK)`, `code (unique per version)`, `title`, `difficulty_baseline` (`1..5`), `skill_tags (text[])`, `exam_tags (text[])`.
- `learning_objectives`: `id (PK)`, `concept_id (FK)`, `bloom_level`, `statement`.
- `concept_prerequisites`: `concept_id (FK)`, `prerequisite_concept_id (FK)`, `strength` (`required|recommended`), PK `(concept_id, prerequisite_concept_id)`, CHECK `concept_id <> prerequisite_concept_id`.
- `exam_tracks`: `id (PK)`, `code` (`CBSE_BOARD|JEE_MAIN|JEE_ADVANCED|NEET`), `name`.
- `exam_concept_mappings`: `exam_track_id (FK)`, `concept_id (FK)`, `weightage_pct`, `priority_tier`, PK `(exam_track_id, concept_id)`.

### 1.5 Content Management & Rights (`content`)
- `content_sources`: `id (PK)`, `name`, `owner_name`, `source_category` (`original_platform|official_link|licensed_partner|ai_generated|teacher_created|student_created|quarantined_third_party`), `official_url`.
- `content_licenses`: `id (PK)`, `source_id (FK)`, `license_name`, `commercial_use_allowed (bool)`, `distribution_allowed (bool)`, `hosting_allowed (bool)`, `embedding_allowed (bool)`, `attribution_required (bool)`, `attribution_text`, `territory`, `expires_at`, `legal_review_status` (`pending|approved|rejected|quarantined`), `reviewed_by (FK)`, `reviewed_at`.
- `content_items`: `id (PK)`, `tenant_id (nullable)`, `content_type` (`concept_note|summary|formula_sheet|worked_example|diagram|video_link|textbook_ref|exercise`), `concept_id (FK nullable)`, `chapter_id (FK nullable)`, `source_id (FK)`, `license_id (FK)`, `created_by (FK)`, `status` (`DRAFT|VALIDATION|REVIEW|APPROVED|PUBLISHED|ARCHIVED`), `current_version_id`.
- `content_versions`: `id (PK)`, `content_item_id (FK)`, `version_no`, `language_code`, `title`, `body_markdown`, `structured_blocks_jsonb`, `media_assets_jsonb`, `ai_generated (bool)`, `ai_metadata_jsonb`, `created_at`.
- `content_translations`: `id (PK)`, `content_version_id (FK)`, `language_code`, `translated_title`, `translated_body_markdown`, `review_status` (`machine_draft|human_reviewed|approved`), `reviewer_id (FK nullable)`.
- `content_reviews`: `id (PK)`, `content_version_id (FK)`, `reviewer_id (FK)`, `decision` (`approved|rejected|changes_requested`), `notes`, `created_at`.
- `content_publications`: `id (PK)`, `content_item_id (FK)`, `content_version_id (FK)`, `curriculum_version_id (FK)`, `published_by (FK)`, `published_at`.

### 1.6 Question Bank & Excel Imports (`question_bank`)
- `questions`: `id (PK)`, `tenant_id (nullable)`, `canonical_hash (indexed)`, `question_type`, `status` (`DRAFT|VALIDATION|REVIEW|APPROVED|PUBLISHED|ARCHIVED`), `current_version_id`, `import_batch_id (FK nullable)`, `created_by (FK)`, `created_at`, `updated_at`.
- `question_versions`: `id (PK)`, `question_id (FK)`, `version_no`, `language_code`, `curriculum_version_id (FK)`, `grade_id (FK)`, `subject_id (FK)`, `chapter_id (FK)`, `topic_id (FK nullable)`, `concept_id (FK nullable)`, `learning_objective_id (FK nullable)`, `stem_markdown`, `passage_markdown`, `media_jsonb`, `answer_schema_jsonb`, `correct_answer_jsonb`, `difficulty` (`easy|medium|hard|olympiad`), `default_marks (numeric)`, `default_negative_marks (numeric)`, `estimated_seconds (int)`, `cognitive_level`, `competency_tag`, `ai_generated (bool)`, `ai_metadata_jsonb`.
- `question_options`: `id (PK)`, `question_version_id (FK)`, `option_key` (`A|B|C|D|...`), `content_markdown`, `media_jsonb`, `is_correct (bool)`, `match_pair_key (nullable)`.
- `question_solutions`: `id (PK)`, `question_version_id (FK)`, `language_code`, `solution_type` (`primary|alternative`), `explanation_markdown`, `steps_jsonb`, `common_mistakes_markdown`, `misconception_tags (text[])`, `rubric_jsonb`.
- `question_hints`: `id (PK)`, `question_version_id (FK)`, `hint_level` (`1|2|3`), `hint_markdown`.
- `question_provenance`: `question_id (PK, FK)`, `source_id (FK)`, `license_id (FK)`, `source_type` (`original|licensed|verified_pyq|ai_generated|teacher_created`), `is_pyq (bool)`, `exam_name`, `exam_year (int)`, `exam_session`, `exam_shift`, `paper_code`, `question_number`, `source_url`, `verification_status` (`unverified|verified|disputed`), `verified_by (FK nullable)`, `verified_at`, CHECK `NOT (is_pyq = true AND verification_status = 'verified' AND exam_year IS NULL)`.
- `question_tags`: `question_id (FK)`, `tag_type` (`skill|exam|competency`), `tag_value`, PK `(question_id, tag_type, tag_value)`.
- `question_reviews`: `id (PK)`, `question_version_id (FK)`, `reviewer_id (FK)`, `decision`, `feedback`, `created_at`.
- `import_batches`: `id (PK)`, `uploaded_by (FK)`, `tenant_id (nullable)`, `original_filename`, `file_sha256`, `storage_key`, `status` (`uploaded|validating|mapped|preview_ready|importing|completed|failed|rolled_back`), `total_rows`, `valid_rows`, `error_rows`, `duplicate_rows`, `report_jsonb`, `created_at`, `completed_at`.
- `import_staging_rows`: `id (PK)`, `import_batch_id (FK)`, `sheet_name`, `row_number (int)`, `raw_payload_jsonb`, `normalized_payload_jsonb`, `row_fingerprint_sha256`, `validation_status` (`pending|valid|warning|error|duplicate|imported`), `errors_jsonb`, `warnings_jsonb`, `created_question_id (FK nullable)`.

### 1.7 Practice & Assessment (`assessment`)
- `practice_sessions`: `id (PK)`, `student_id (FK)`, `concept_id (FK nullable)`, `chapter_id (FK nullable)`, `mode`, `started_at`, `ended_at`.
- `question_attempts`: `id (PK)`, `student_id (FK)`, `question_id (FK)`, `question_version_id (FK)`, `practice_session_id (FK nullable)`, `assessment_attempt_id (FK nullable)`, `response_jsonb`, `is_correct (bool nullable)`, `score_awarded (numeric)`, `hints_used_count (int)`, `time_spent_seconds (int)`, `attempted_at`.
- `student_notes`: `id (PK)`, `student_id (FK)`, `concept_id (FK nullable)`, `question_id (FK nullable)`, `title`, `body_markdown`, `created_at`, `updated_at`.
- `saved_questions`: `student_id (FK)`, `question_id (FK)`, `folder_name`, `created_at`, PK `(student_id, question_id)`.
- `exam_patterns`: `id (PK)`, `exam_track_id (FK)`, `version_label`, `effective_year`, `rules_jsonb` (sections, marking rules, multi-correct partial marking, optional questions), `is_active`.
- `quizzes`: `id (PK)`, `tenant_id (nullable)`, `quiz_type`, `title`, `created_by (FK)`, `config_jsonb`, `is_ai_generated (bool)`, `status`.
- `tests`: `id (PK)`, `tenant_id (nullable)`, `exam_pattern_id (FK nullable)`, `title`, `test_category` (`cbse_mock|jee_main|jee_adv|neet|teacher_test|institution_test`), `duration_seconds`, `total_marks`, `retake_policy_jsonb`, `created_by (FK)`, `published_at`.
- `test_sections`: `id (PK)`, `test_id (FK)`, `sequence_no`, `name`, `subject_id (FK nullable)`, `marking_rule_jsonb`, `duration_seconds (nullable)`.
- `test_questions`: `id (PK)`, `test_id (FK)`, `section_id (FK)`, `question_id (FK)`, `question_version_id (FK)`, `sequence_no`, `marks_override`, `negative_marks_override`.
- `assessment_attempts`: `id (PK)`, `tenant_id (nullable)`, `student_id (FK)`, `test_id (FK nullable)`, `quiz_id (FK nullable)`, `status` (`in_progress|submitted|auto_submitted|graded`), `started_at`, `expires_at`, `submitted_at`, `submission_idempotency_key (unique nullable)`, `question_order_jsonb`, `raw_score (numeric)`, `max_score (numeric)`, `accuracy_pct (numeric)`.
- `attempt_answers`: `id (PK)`, `attempt_id (FK)`, `question_version_id (FK)`, `response_jsonb`, `is_marked_for_review (bool)`, `time_spent_seconds (int)`, `is_correct (bool nullable)`, `marks_awarded (numeric nullable)`, `last_saved_at`, UNIQUE `(attempt_id, question_version_id)`.

### 1.8 Learning, Adaptive Mastery & Revision (`learning`, `revision`)
- `outbox_events`: `id (PK)`, `aggregate_type`, `aggregate_id`, `event_type`, `payload_jsonb`, `created_at`, `published_at (nullable)`, `retry_count`.
- `processed_event_ids`: `consumer_name`, `event_id`, `processed_at`, PK `(consumer_name, event_id)`.
- `learning_events`: `id (PK)`, `student_id (FK)`, `tenant_id (nullable)`, `event_type`, `concept_id (FK nullable)`, `entity_id`, `metrics_jsonb`, `occurred_at`.
- `student_concept_mastery`: `id (PK)`, `student_id (FK)`, `concept_id (FK)`, `mastery_score (numeric 0..100)`, `confidence_score (numeric 0..1)`, `attempts_count`, `correct_count`, `independent_correct_count`, `hints_used_total`, `avg_time_seconds`, `retention_stability`, `last_studied_at`, `next_revision_due_at`, `evidence_jsonb`, UNIQUE `(student_id, concept_id)`.
- `student_misconceptions`: `id (PK)`, `student_id (FK)`, `concept_id (FK)`, `misconception_code`, `description`, `occurrence_count`, `resolved_at (nullable)`.
- `learning_paths` & `learning_path_items`: ordered personalized remediation/advancement sequences with explainable `reason_text`.
- `flashcards`: `id (PK)`, `concept_id (FK nullable)`, `question_id (FK nullable)`, `card_type`, `language_code`, `front_markdown`, `back_markdown`, `media_jsonb`, `source_id (FK)`, `status`.
- `student_flashcards`: `id (PK)`, `student_id (FK)`, `flashcard_id (FK)`, `state` (`new|learning|review|relearning|suspended`), `ease_factor`, `interval_days`, `repetitions`, `lapses`, `due_at`, `last_reviewed_at`, UNIQUE `(student_id, flashcard_id)`.
- `flashcard_reviews`: `id (PK)`, `student_flashcard_id (FK)`, `rating` (`again|hard|good|easy`), `response_ms`, `scheduled_interval_before`, `scheduled_interval_after`, `reviewed_at`.
- `study_plans` & `study_plan_items`: daily/weekly scheduled tasks linked to `concept_id`, `test_id`, or `revision`.

### 1.9 AI, Classroom, Whiteboard & Voice (`ai`, `classroom`)
- `ai_sessions`: `id (PK)`, `student_id (FK)`, `tenant_id (nullable)`, `session_type` (`tutor|doubt|lesson_companion`), `curriculum_context_jsonb`, `language_code`, `teaching_mode`, `created_at`.
- `ai_messages`: `id (PK)`, `ai_session_id (FK)`, `role` (`student|assistant|system_event`), `content_markdown`, `citations_jsonb`, `verification_status`, `model_used`, `prompt_version`, `tokens_in`, `tokens_out`, `created_at`.
- `ai_tool_calls`: `id (PK)`, `ai_message_id (FK)`, `tool_name` (`rag_retrieve|sympy_verify|pint_units|chem_balance|safety_check`), `input_jsonb`, `output_jsonb`, `succeeded (bool)`, `latency_ms`.
- `knowledge_documents`: `id (PK)`, `content_version_id (FK)`, `source_id (FK)`, `license_id (FK)`, `curriculum_tags_jsonb`, `embedding_allowed (bool)`, `indexed_at`.
- `knowledge_chunks`: `id (PK)`, `document_id (FK)`, `hierarchy_path`, `section_title`, `language_code`, `chunk_text`, `embedding (vector(1536))`, `fts_tsv (tsvector)`, `metadata_jsonb`. *(GIN on `fts_tsv`, HNSW/IVFFlat on `embedding`, B-tree on metadata fields).*
- `ai_eval_datasets`, `ai_eval_runs`, `ai_eval_results`, `ai_review_queue`.
- `lesson_plans`: `id (PK)`, `student_id (FK nullable)`, `concept_id (FK)`, `language_code`, `schema_version`, `lesson_artifact_jsonb`, `created_at`.
- `classroom_sessions`: `id (PK)`, `student_id (FK)`, `lesson_plan_id (FK)`, `state` (`IDLE|READY|PLAYING_SEGMENT|PAUSED|CHECKPOINT_WAIT|DOUBT_INTERRUPTION|COMPLETED`), `current_segment_seq`, `playback_speed`, `voice_language`, `subtitle_language`, `started_at`, `last_active_at`, `completed_at`.
- `classroom_events`: `id (PK)`, `classroom_session_id (FK)`, `sequence_no`, `event_type`, `payload_jsonb`, `created_at`.
- `whiteboard_snapshots`: `id (PK)`, `classroom_session_id (FK)`, `segment_seq`, `version`, `snapshot_jsonb` (or `storage_key`), `created_at`.
- `whiteboard_events`: `id (PK)`, `classroom_session_id (FK)`, `segment_seq`, `sequence_no`, `actor` (`ai|student`), `action_type`, `action_payload_jsonb`, `created_at`.
- `language_capabilities`: `language_code (PK)`, `display_name`, `native_name`, `rtl (bool)`, `text_quality_tier`, `translation_status`, `tts_supported (bool)`, `stt_supported (bool)`, `voice_provider`, `pronunciation_tier`, `subtitle_supported (bool)`, `academic_review_status`, `known_limitations`.
- `voice_usage_logs`: `id (PK)`, `user_id (FK)`, `classroom_session_id (FK nullable)`, `provider` (`elevenlabs|...`), `voice_id`, `language_code`, `characters_count`, `audio_seconds`, `latency_ms`, `estimated_cost_usd`, `created_at`.

### 1.10 Homework, Teacher, Mentor, Billing & Analytics (`homework`, `teacher`, `billing`, `analytics`)
- `homework_submissions`: `id (PK)`, `student_id (FK)`, `assignment_id (FK nullable)`, `subject_id (FK nullable)`, `status` (`uploaded|ocr_processing|analyzing|feedback_ready|retry_pending|completed|failed`), `created_at`.
- `homework_files`: `id (PK)`, `submission_id (FK)`, `page_no`, `storage_key`, `mime_type`, `size_bytes`, `sha256`, `scan_status` (`pending|clean|rejected`).
- `homework_ocr_results`: `submission_id (FK)`, `page_no`, `ocr_provider`, `extracted_text`, `extracted_latex`, `confidence`, `raw_jsonb`.
- `homework_evaluations`: `id (PK)`, `submission_id (FK)`, `detected_question`, `extracted_steps_jsonb`, `error_classifications_jsonb`, `verifier_results_jsonb`, `hints_jsonb` (Levels 1..3), `current_hint_level_unlocked (int)`, `teacher_override_jsonb`.
- `assignments`, `assignment_submissions`, `teacher_notes`, `teacher_reports`.
- `mentor_assignments`, `mentoring_sessions`, `follow_up_tasks`.
- `plans`, `plan_entitlements`, `subscriptions`, `usage_ledgers`, `transactions`, `invoices`, `refunds`, `provider_rate_cards`, `ai_cost_events`.
- `analytics_snapshots`, `notifications`, `notification_preferences`, `safety_incidents`, `feature_flags`.

---

## 2. Indexing, Partitioning & Retention Principles

1. **Tenant & Auth Composite Indexes:** Every tenant-scoped table indexes `(tenant_id, ...)` as the leading index key.
2. **Time-Series Partitioning Ready:** `learning_events`, `ai_cost_events`, `audit_logs`, and `classroom_events` are designed for PostgreSQL monthly range partitioning (`occurred_at` / `created_at`) once volume grows.
3. **Retention & Deletion:** Deletion requests anonymize `users`/`user_profiles`, purge S3 files (`homework_files`, `voice` recordings), and preserve anonymized aggregate counts/financial ledger compliance records per legal policy.
