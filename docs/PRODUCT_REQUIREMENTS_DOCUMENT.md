# Product Requirements Document (`docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`)

**Product Working Identity:** **GuruSetu AI** *(placeholder internal working name; final brand customizable via white-label tenant config)*  
**Version:** 1.0 (Phase 0 Baseline)  
**Target Users:** Classes 6–12 Students (CBSE, Board Exams, JEE Main, JEE Advanced, NEET), Teachers, Mentors/Tutors, Parents/Guardians, School Administrators, Content Administrators, Academic Reviewers, Platform Administrators.

---

## 1. Product Vision & Strategic Scope

Build a production-grade, multilingual, curriculum-grounded AI learning ecosystem combining:
1. Structured curriculum & textbook-referenced learning (Classes 6–12 CBSE + competitive mappings).
2. Pedagogical AI Tutor (explain, hint, Socratic, step-by-step, practice, revision, doubt solving) backed by deterministic math/science verification.
3. Interactive Live AI Classroom with structured lesson artifacts, synchronized voice narration (ElevenLabs adapter + provider abstraction), and structured schema-driven interactive whiteboard.
4. Comprehensive Question Bank, Excel ingestion pipeline, Practice Engine, Quiz Engine, and server-authoritative Assessment/Exam Engine (CBSE Boards, JEE Main, JEE Advanced, NEET, verified PYQs).
5. Adaptive concept-level mastery tracking, spaced-repetition flashcards, personalized study plans, and OCR-powered Homework AI with graduated hints.
6. Multi-role, multi-tenant dashboards (Student, Parent with consent & privacy boundaries, Teacher, Mentor, School Admin, Content Admin, Academic Reviewer, Platform Admin), billing/unit-economics controls, observability, and DPDP-aware child safety.

---

## 2. Role Summary Matrix

| Role Code | Role Name | Core Scope | Isolation / Privacy Rule |
| :--- | :--- | :--- | :--- |
| `student` | Student | Curriculum, AI tutor, live classroom, whiteboard, voice, practice, quizzes, exams, homework, flashcards, notes, study plans, personal analytics | Own data + enrolled classes/tenant only |
| `parent` | Parent / Guardian | Consent-based child linking, privacy-preserving summaries, goals, completed lessons, practice activity, weak topics, upcoming assessments, privacy settings | **Must NOT** have unrestricted access to raw student AI chat transcripts |
| `teacher` | Teacher | Class/section management, assignments, quizzes, tests, question selection, grading + AI-assist + override, class & student analytics, reports | Assigned classes/sections within tenant only |
| `mentor` | Mentor / Tutor | Assigned students, learning goals, study plans, mentoring session logs, follow-up tasks, interventions | Assigned students only |
| `school_admin` | School Administrator | Institution, branches, academic years, classes, sections, staff, enrollment, institutional tests/analytics, institutional subscriptions | Strict `tenant_id` isolation |
| `content_admin` | Content Administrator | Curriculum versioning, Excel imports, CMS items, metadata, translations, publishing status | Cannot bypass Academic Review on high-stakes exam content |
| `academic_reviewer` | Academic Reviewer | Question review, solution review, AI content QA, PYQ provenance verification, approve/reject/flag, review audit history | Immutable review trail |
| `platform_admin` | Platform Administrator | Global config, roles, feature flags, subscriptions, system health, security/audit logs, moderation/support | MFA mandatory; all actions audited |

---

## 3. Comprehensive Feature Specifications (All 40 Vision Capabilities + Cross-Cutting Modules)

> **Status Key:** All features are currently `NOT_STARTED` (Phase 0 discovery complete; no code implemented yet).  
> **Non-Functional Baseline (Applies to All Features):** API P95 < 300ms (non-AI), WCAG 2.1 AA accessibility, responsive desktop/tablet/mobile UI, TLS in transit, encryption at rest, RBAC + tenant check in backend, structured error/loading/empty states, audit logging for mutations.

### Domain A: Identity, Multi-Tenancy & Access Control (Phase 1, 8, 9)

#### `F-001` — Authentication, Session Security & Privileged MFA
- **Role:** All Roles | **Priority:** P0 | **Phase:** Phase 1 (MFA P0 for Admins in Phase 1/9)
- **User Problem:** Users need secure, age-aware access across devices; minors and institutions require strong account protection.
- **Description:** Email/phone/SSO registration & login, Argon2id password hashing, HTTP-only secure refresh + short-lived JWT access tokens, device/session revocation, TOTP MFA required for `platform_admin`, `school_admin`, `content_admin`, `academic_reviewer`.
- **User Flow:** Register/Login → Verify email/OTP → Age gate check (minor triggers parent consent workflow) → Role-scoped session issued → MFA challenge for privileged roles → Redirect to role workspace.
- **Functional Reqs:** Password complexity & breach check; account lockout/rate limiting; session list & revoke; role-aware token claims; password reset with single-use hashed tokens.
- **Non-Functional Reqs:** Auth P95 < 250ms; Argon2id tuned ≥ 64MB; CSRF protection on cookie flows.
- **API / DB / AI Deps:** `POST /api/v1/auth/{register,login,refresh,logout,mfa/*}`; `users`, `auth_providers`, `sessions`, `devices`, `user_roles`; No AI.
- **Security & Accessibility:** Rate-limited by IP+account; audit log on login/failure/MFA; keyboard-accessible forms, screen-reader error live regions.
- **Acceptance Criteria & Tests:** Unauthenticated requests return 401; expired/revoked refresh tokens rejected; privileged login blocked without MFA; unit + API integration + brute-force tests pass.
- **Status:** `NOT_STARTED`

#### `F-002` — Role-Based Access Control (RBAC) & Backend Enforcement
- **Role:** Platform Admin, All | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** Multi-persona EdTech platforms fail catastrophically if permissions are only hidden in UI.
- **Description:** Fine-grained permission policies evaluated on every API endpoint and DB query (`require_permission`, `require_tenant_scope`).
- **User Flow:** Request arrives → Auth middleware parses user → Policy resolver validates role + permissions + tenant + ownership/assignment → Allows or returns 403.
- **Functional Reqs:** Role-permission mapping table; multi-role support per user (e.g., Teacher + Parent); deny-by-default.
- **Non-Functional Reqs:** Policy evaluation < 5ms (cached/in-request).
- **API / DB / AI Deps:** `roles`, `permissions`, `role_permissions`, `user_roles`; No AI.
- **Security & Accessibility:** Explicit cross-role and horizontal privilege-escalation tests; accessible 403 UI state.
- **Acceptance Criteria & Tests:** Automated matrix test verifies Student cannot hit Teacher/Admin endpoints, Teacher cannot view unassigned classes, Parent cannot read raw AI chat logs.
- **Status:** `NOT_STARTED`

#### `F-003` — Multi-Tenant School & Institution Management
- **Role:** School Admin, Platform Admin | **Priority:** P1 | **Phase:** Phase 9
- **User Problem:** Schools and coaching institutes need isolated data, branches, academic years, batches, and licensing.
- **Description:** Organizations → Schools → Branches → Academic Years → Classes → Sections/Batches → Staff Assignments → Enrollments, all scoped by `tenant_id`.
- **User Flow:** Platform Admin provisions Org/License → School Admin creates Branches, Academic Year, Classes/Sections → Bulk enrolls Students & assigns Teachers/Mentors.
- **Functional Reqs:** Tenant scoping middleware + PostgreSQL RLS/mandatory `tenant_id` predicates; academic year archival; CSV/roster enrollment import.
- **Non-Functional Reqs:** Zero cross-tenant leakage under concurrent load.
- **API / DB / AI Deps:** `/api/v1/institutions/*`; `organizations`, `schools`, `branches`, `academic_years`, `classes`, `sections`, `enrollments`, `staff_assignments`.
- **Security & Accessibility:** Cross-tenant integration fuzz tests; accessible data tables with keyboard sorting.
- **Acceptance Criteria & Tests:** User from Tenant A receives 403/404 when requesting Tenant B UUIDs across every endpoint.
- **Status:** `NOT_STARTED`

#### `F-004` — Parent/Guardian Consent & Privacy-Preserving Linking
- **Role:** Parent, Student | **Priority:** P1 | **Phase:** Phase 8
- **User Problem:** Minor privacy (DPDP Act) requires verifiable guardian consent while preserving student psychological safety in AI tutoring.
- **Description:** Parent invites/links minor student (or minor nominates guardian at signup) via verifiable OTP/consent record; parent gets summarized learning insights without raw private AI conversation logs.
- **User Flow:** Student registers (<18) → Enters parent contact → Consent token dispatched → Parent verifies identity & accepts consent → Linked account appears in Parent Dashboard.
- **Functional Reqs:** Consent versioning & timestamps; consent withdrawal workflow; privacy toggle controls; restricted parent projection endpoints.
- **Non-Functional Reqs:** Consent audit immutable; PII minimized.
- **API / DB / AI Deps:** `/api/v1/parents/links/*`, `/api/v1/consents/*`; `parent_links`, `consents`, `audit_logs`.
- **Security & Accessibility:** Explicit backend denial of `/ai/sessions/{id}/messages` to Parent role; clear plain-language consent screens.
- **Acceptance Criteria & Tests:** Parent cannot view unconsented child or raw AI chat; revoking consent immediately halts minor AI access per policy.
- **Status:** `NOT_STARTED`

---

### Domain B: Curriculum, Content Management & Rights (Phase 1, 10, 11)

#### `F-005` — Versioned Data-Driven Curriculum Hierarchy
- **Role:** Content Admin, Student, Teacher | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** CBSE/NCERT/JEE/NEET syllabi evolve across academic sessions; hardcoding breaks historical records.
- **Description:** 11-level academic hierarchy: `Board → Academic Session → Grade (6–12) → Subject → Book → Chapter → Section → Topic → Concept → Learning Objective → Prerequisite`, plus cross-mapping to competitive exams (`JEE Main`, `JEE Advanced`, `NEET`).
- **User Flow:** Content Admin creates/versions syllabus → Maps concepts, prerequisites, skill tags, exam tags, and language labels → Student/Teacher browses dynamically.
- **Functional Reqs:** Immutable curriculum versions (`curriculum_version_id`); prerequisite DAG validation (acyclic); exam tag mappings; soft archival.
- **Non-Functional Reqs:** Cached tree retrieval < 100ms.
- **API / DB / AI Deps:** `/api/v1/curriculum/*`; `boards`, `academic_sessions`, `grades`, `subjects`, `books`, `chapters`, `sections`, `topics`, `concepts`, `learning_objectives`, `concept_prerequisites`, `exam_concept_mappings`.
- **Security & Accessibility:** Public/student read only published curriculum versions; accessible tree/breadcrumb navigation.
- **Acceptance Criteria & Tests:** Prerequisite cycle detection rejects cyclic DAGs; updating v2 syllabus does not mutate v1 exam attempts; tree API + UI tests pass.
- **Status:** `NOT_STARTED`

#### `F-006` — Curriculum & Textbook Content Management System (CMS)
- **Role:** Content Admin, Academic Reviewer, Student | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** Learning requires multi-format explanations, formulas, diagrams, summaries, worked examples, and exercises with editorial workflow.
- **Description:** Rights-aware CMS supporting Markdown, rich text, KaTeX math, diagrams, tables, audio, video, animations, interactive activities, chapter summaries, notes, formula sheets, worked solutions, and external official textbook links.
- **User Flow:** Content Admin drafts item → Automated validation → Academic Reviewer inspects → Approves → Publishes to active curriculum version.
- **Functional Reqs:** Lifecycle state machine (`DRAFT → VALIDATION → REVIEW → APPROVED → PUBLISHED → ARCHIVED`); semantic versioning; side-by-side diff; review history log.
- **Non-Functional Reqs:** Rich media served via signed URLs; XSS sanitization on rich text/Markdown.
- **API / DB / AI Deps:** `/api/v1/content/*`; `content_items`, `content_versions`, `content_translations`, `content_reviews`, `content_publications`.
- **Security & Accessibility:** Unapproved content strictly hidden from student/exam queries; alt-text required on instructional images; math screen-reader/ARIA support.
- **Acceptance Criteria & Tests:** Cannot transition `DRAFT → PUBLISHED` directly; XSS payloads stripped; published content renders KaTeX accurately.
- **Status:** `NOT_STARTED`

#### `F-007` — Content Rights, Licensing & Provenance Governance
- **Role:** Content Admin, Academic Reviewer, Platform Admin | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** Using scraped coaching PDFs or hosting copyrighted textbooks creates severe legal liability.
- **Description:** Mandatory rights metadata on every content item and question (`source_owner`, `license_type`, `commercial_use_allowed`, `distribution_allowed`, `hosting_allowed`, `embedding_allowed`, `attribution_text`, `territory`, `expiry_date`, `legal_review_status`), separating `LICENSED`, `OFFICIAL_LINK`, `ORIGINAL_PLATFORM`, `AI_GENERATED`, `TEACHER_CREATED`, `STUDENT_CREATED`, `THIRD_PARTY_QUARANTINED`.
- **User Flow:** Creator/Importer attaches source & license → System enforces hosting/embedding rules (e.g., blocks RAG indexing if `embedding_allowed=false`) → Legal/Content Admin approves before publishing.
- **Functional Reqs:** Automated policy gate preventing unlicensed third-party files (e.g., ALLEN PDFs) from publishing or entering vector index; attribution rendering where required; no implied NCERT/CBSE endorsement disclaimer.
- **Non-Functional Reqs:** 100% of published assets have non-null rights classification.
- **API / DB / AI Deps:** `content_sources`, `content_licenses`, `rights_reviews`; Retrieval service filters strictly on `embedding_allowed = true AND status = 'PUBLISHED'`.
- **Security & Accessibility:** Tamper-evident audit logs on rights changes; attribution accessible in UI.
- **Acceptance Criteria & Tests:** Attempting to publish/index an asset with `hosting_allowed=false` or `legal_review_status != 'APPROVED'` fails with 422/403.
- **Status:** `NOT_STARTED`

---

### Domain C: Question Bank & Excel Ingestion (Phase 1, 2, 10)

#### `F-008` — Canonical Multi-Format Question Bank
- **Role:** Content Admin, Academic Reviewer, Teacher, Student | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** Generic MCQ tables fail for JEE Advanced (multi-correct, numerical, matrix match), CBSE (assertion-reason, case-based, subjective rubrics), and multilingual delivery.
- **Description:** Versioned question bank supporting 18+ question types (Single MCQ, Multi-Correct MCQ, Numerical, Integer, Assertion–Reason, Case-Based, Match-the-Following, Matrix Match, Short Answer, Long Answer, Essay, Diagram-Based, Passage-Based, Comprehension, Map-Based, Image-Based, Audio-Based, Extensible JSON schema), rich solutions (step-by-step, alternative methods, hints, common mistakes, misconceptions, rubric), strict provenance, and AI metadata.
- **User Flow:** Author/Import question → Map curriculum & tags → Attach verified solution/rubric & provenance → Academic Reviewer verifies → Publish.
- **Functional Reqs:** Separate `question_provenance` (PYQs require verified exam/year/session/shift/paper/source_url + reviewer sign-off; AI-generated questions cannot be tagged `is_pyq=true`); full-text + metadata search; version pinning for historical tests.
- **Non-Functional Reqs:** Search P95 < 200ms over 500k questions; strict KaTeX validation.
- **API / DB / AI Deps:** `/api/v1/questions/*`; `questions`, `question_versions`, `question_options`, `question_solutions`, `question_hints`, `question_tags`, `question_provenance`, `question_reviews`.
- **Security & Accessibility:** Answer keys never leaked in student-facing question-fetch DTOs during active attempts; keyboard-navigable question types & math ARIA.
- **Acceptance Criteria & Tests:** DB constraint/service rule blocks `is_pyq=true` without verified provenance; student attempt API omits `correct_answer` until submission.
- **Status:** `NOT_STARTED`

#### `F-009` — Safe Excel Question Bank Ingestion Pipeline
- **Role:** Content Admin, Academic Reviewer | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** Bulk question spreadsheets vary widely in sheets/columns, contain duplicates, typos, missing fields, and unverified PYQ claims.
- **Description:** 14-stage idempotent import pipeline (`UPLOAD → FILE VALIDATION → SHEET DETECTION → STAGING → COLUMN MAPPING → DATA NORMALIZATION → VALIDATION → DUPLICATE DETECTION → ACADEMIC MAPPING → SOURCE VALIDATION → PREVIEW → REVIEW → IMPORT → PUBLISH`).
- **User Flow:** Upload `.xlsx/.csv` → System stores immutable copy in object storage, detects sheets & headers → Admin maps columns → Validation & SHA-256/SimHash duplicate detection run in worker → Row-level error/warning report & preview → Reviewer approves → Batch commits into `DRAFT`/`REVIEW` state → Import report generated; rollback supported by `import_batch_id`.
- **Functional Reqs:** Never modify original files; staging tables (`import_batches`, `import_rows`); question-type inference; difficulty & answer validation; idempotent re-run via batch checksum + row fingerprint; rollback per batch.
- **Non-Functional Reqs:** Handle 10,000-row workbooks asynchronously without blocking API; memory-safe streaming parser.
- **API / DB / AI Deps:** `/api/v1/imports/*`; `import_batches`, `import_sheet_mappings`, `import_staging_rows`, `import_reports`.
- **Security & Accessibility:** Strict MIME/zip-bomb/formula-injection sanitization (`=CMD|...` stripped); private signed upload; accessible row-error table + CSV error export.
- **Acceptance Criteria & Tests:** Malformed Excel, formula injection, duplicate question, and missing required answer produce row-level errors without partial corrupt DB commits; rollback cleanly removes batch draft rows.
- **Status:** `NOT_STARTED`

---

### Domain D: Practice, Quiz & Assessment Engine (Phase 1, 2, 10)

#### `F-010` — Guided Practice Engine, Notes & Saved Questions
- **Role:** Student | **Priority:** P0 | **Phase:** Phase 1
- **User Problem:** Students need low-stakes chapter/topic/concept practice with immediate step-by-step explanations, bookmarking, and personal notes.
- **Description:** Filterable practice sessions (board/grade/subject/chapter/topic/concept/difficulty/source/exam), hint reveal tracking, immediate verification, personal markdown/math notes linked to concepts/questions, and saved question collections.
- **User Flow:** Select subject & chapter → Choose practice mode → Solve question → Request hint or submit → View verified step-by-step solution & common pitfalls → Save note or bookmark question.
- **Functional Reqs:** Emits `QUESTION_ATTEMPTED`, `HINT_USED`, `QUESTION_CORRECT/INCORRECT` events; supports personal folders/tags for saved questions.
- **Non-Functional Reqs:** Instant answer check < 150ms.
- **API / DB / AI Deps:** `/api/v1/practice/*`, `/api/v1/notes/*`, `/api/v1/bookmarks/*`; `practice_sessions`, `question_attempts`, `student_notes`, `saved_questions`.
- **Security & Accessibility:** Notes/bookmarks scoped to `student_id` (or shared explicitly); full keyboard navigation.
- **Acceptance Criteria & Tests:** Hint usage recorded accurately; notes persist and render math safely; bookmarking is idempotent.
- **Status:** `NOT_STARTED`

#### `F-011` — Configurable Quiz Engine
- **Role:** Student, Teacher, AI System | **Priority:** P0 | **Phase:** Phase 2
- **User Problem:** Students and teachers need quick daily, diagnostic, chapter, revision, challenge, and AI-assisted quizzes tailored to goals.
- **Description:** Supports 12 quiz types (Daily, Quick, Chapter, Topic, Concept, Diagnostic, Revision, Teacher, AI-generated, Challenge, Competition, Institution) with configurable counts, difficulty mix, question types, marks/negative marks, randomization, feedback timing, retake policies, and language.
- **User Flow:** Pick preset or configure quiz → Server generates quiz blueprint & selects validated questions → Student completes quiz → Immediate or end-of-quiz feedback + event emission.
- **Functional Reqs:** AI-generated quizzes undergo schema + answer + ambiguity + deduplication checks and carry `AI_GENERATED` badge; deterministic seed-based randomization per attempt.
- **Non-Functional Reqs:** Blueprint assembly < 300ms.
- **API / DB / AI Deps:** `/api/v1/quizzes/*`; `quizzes`, `quiz_questions`, `quiz_attempts`; AI Quiz Generator (Phase 3+).
- **Security & Accessibility:** AI quiz quota enforced; WCAG-compliant timer alerts (no flashing, polite ARIA announcements).
- **Acceptance Criteria & Tests:** Generated quiz matches exact requested counts/marks/difficulty constraints; AI-generated flag never hidden.
- **Status:** `NOT_STARTED`

#### `F-012` — Server-Authoritative Assessment & Mock Exam Engine
- **Role:** Student, Teacher, School Admin | **Priority:** P0 | **Phase:** Phase 2
- **User Problem:** Client-side timers and browser-calculated scores are easily manipulated and lost on network drops.
- **Description:** Full examination platform with test templates, multi-section blueprints, server-authoritative UTC timers + grace windows, question palette (Answered / Not Answered / Marked for Review / Not Visited), answer autosave with local recovery buffer, idempotent final submission, configurable scoring/negative marking/partial marking (e.g., JEE Adv), and detailed post-exam analytics.
- **User Flow:** Enter exam lobby → Review instructions & rules → Start attempt (`started_at`, `expires_at` locked on server) → Solve & autosave answers → Mark for review / navigate sections → Submit (or auto-finalize at expiry) → Server computes authoritative score & analytics.
- **Functional Reqs:** Server rejects submissions past `expires_at + grace_seconds`; `idempotency_key` prevents duplicate scoring; score calculated exclusively in backend; supports retakes per policy.
- **Non-Functional Reqs:** Autosave < 150ms; offline/flaky network queue retries without losing responses.
- **API / DB / AI Deps:** `/api/v1/assessments/*`; `tests`, `test_blueprints`, `test_sections`, `assessment_sessions`, `assessment_attempts`, `attempt_answers`, `assessment_results`, `grading_rubrics`.
- **Security & Accessibility:** Correct answers never sent to client during active attempt; timer remaining synced on heartbeat; accessible question palette & keyboard shortcuts.
- **Acceptance Criteria & Tests:** Tampering with client clock or submitting modified score payload has zero effect; concurrent duplicate submit calls return identical single scored result; auto-submit worker closes expired sessions.
- **Status:** `NOT_STARTED`

#### `F-013` — CBSE Board Preparation Workflows (Classes 10 & 12 + 6–12)
- **Role:** Student, Teacher | **Priority:** P0 | **Phase:** Phase 2 & Phase 10
- **User Problem:** CBSE boards require competency-based, case-based, assertion–reason, and structured subjective answer-writing practice aligned to marking schemes.
- **Description:** Configurable CBSE exam blueprints, chapter/topic/year/paper/difficulty filters, verified PYQs, sample papers, subjective answer upload/text writing with rubric-based evaluation, weak chapter detection, and improvement plans.
- **User Flow:** Select CBSE Board Track → Choose Sample Paper / Verified PYQ / Competency Practice → Write or upload subjective answers + solve objective sections → Receive step-wise rubric feedback & weak-chapter diagnosis.
- **Functional Reqs:** Configurable CBSE pattern versioning per academic session; rubric step-marking support; strict provenance verification on CBSE PYQs.
- **Non-Functional Reqs:** PDF/image subjective answer upload processed reliably.
- **API / DB / AI Deps:** `/api/v1/exams/cbse/*`; `exam_patterns`, `assessments`, `grading_rubrics`, `question_provenance`.
- **Security & Accessibility:** Do not imply CBSE official endorsement; accessible case-study passage split view.
- **Acceptance Criteria & Tests:** Pattern config supports changing section weights across sessions without code deploy; rubric scorer breaks down marks by step.
- **Status:** `NOT_STARTED`

#### `F-014` — JEE Main Preparation Ecosystem
- **Role:** Student | **Priority:** P1 | **Phase:** Phase 10
- **User Problem:** JEE Main requires speed, accuracy, numerical-value precision, session/shift-tagged PYQs, and multi-concept Physics/Chemistry/Maths mastery.
- **Description:** Physics/Chemistry/Mathematics tracks, chapter/concept/difficulty practice, verified session/shift PYQs, integer/numerical tolerance validation, timed NTA-style CBT mock simulations, speed vs accuracy analysis, alternative solution methods, and formula revision.
- **User Flow:** Select JEE Main Track → Launch CBT Mock or Concept Drill → Solve Sections A & B (numerical) → Inspect per-question time vs peer/benchmark pacing, accuracy, and alternative fast methods.
- **Functional Reqs:** Configurable NTA pattern rules (e.g., optional/mandatory numerical counts by exam year); exact & decimal-tolerance numerical grading; time-spent telemetry per question.
- **Non-Functional Reqs:** CBT UI responsive and low-latency during 3-hour sessions.
- **API / DB / AI Deps:** `/api/v1/exams/jee-main/*`; `exam_patterns`, `question_provenance` (`session`, `shift`), `attempt_question_timings`.
- **Security & Accessibility:** PYQ shift tags only shown when provenance verified; screen-reader friendly CBT navigation.
- **Acceptance Criteria & Tests:** Numerical evaluator respects configurable rounding/precision rules; negative marking applies per section rule config.
- **Status:** `NOT_STARTED`

#### `F-015` — JEE Advanced Preparation Ecosystem
- **Role:** Student | **Priority:** P1 | **Phase:** Phase 10
- **User Problem:** JEE Advanced features unpredictable patterns, partial marking on multi-correct questions, matrix/matching, and deep multi-concept synthesis.
- **Description:** Multi-concept dependency mapping, complex multi-correct (partial/zero/negative marking rules), numerical, matching, matrix, paragraph-based questions, Paper 1 + Paper 2 mock simulations, concept-dependency failure diagnosis, and multi-method solutions.
- **User Flow:** Select JEE Advanced Track → Attempt Paper 1/2 Simulation → Review multi-concept dependency breakdown (e.g., Electrostatics + Rotational Mechanics) and time allocation.
- **Functional Reqs:** Versioned `exam_pattern_rules` JSON schema per year/paper so partial marking (+4/+3/+2/+1/0/-2) is never hardcoded; concept graph dependency attribution.
- **Non-Functional Reqs:** Accurate handling of complex composite inputs.
- **API / DB / AI Deps:** `/api/v1/exams/jee-advanced/*`; `exam_patterns`, `question_types` (`multi_correct`, `matrix`, `matching`), `concept_prerequisites`.
- **Security & Accessibility:** Strict rule-engine unit tests covering every partial-marking edge case.
- **Acceptance Criteria & Tests:** Multi-correct partial credit computes identically to configured JEE Advanced year rule across all subsets.
- **Status:** `NOT_STARTED`

#### `F-016` — NEET Preparation Ecosystem
- **Role:** Student | **Priority:** P1 | **Phase:** Phase 10
- **User Problem:** NEET requires high-speed accuracy across Physics, Chemistry, Botany, and Zoology with deep NCERT line/fact alignment and misconception remediation.
- **Description:** Physics, Chemistry, Biology (Botany & Zoology) tracks, NCERT-focused concept mappings, verified PYQs, configurable NEET full mock simulations, negative marking, speed/accuracy & biological misconception tracking, formula & biology fact revision decks.
- **User Flow:** Select NEET Track → Drill NCERT Biology facts or take 200-min/180-question configurable mock → Review subject-split analytics and misconception flashcards.
- **Functional Reqs:** Configurable NEET rule engine (e.g., Section A/B rules across exam years); subject/sub-discipline tagging (`Botany`, `Zoology`).
- **Non-Functional Reqs:** Fast rendering of diagram-heavy Biology questions.
- **API / DB / AI Deps:** `/api/v1/exams/neet/*`; `exam_patterns`, `misconceptions`, `flashcards`.
- **Security & Accessibility:** High-contrast biological diagrams with alt descriptions.
- **Acceptance Criteria & Tests:** Mock exam enforces configurable section rules and negative marking; biology misconception tags link to spaced repetition queue.
- **Status:** `NOT_STARTED`

---

### Domain E: AI Tutor, Orchestration, RAG & Verification (Phase 3)

#### `F-017` — Modular AI Teaching Orchestrator & Context Resolver
- **Role:** Student, AI System | **Priority:** P0 | **Phase:** Phase 3
- **User Problem:** Monolithic LLM prompts hallucinate, leak answers prematurely, ignore grade/board context, and create runaway costs.
- **Description:** Explicit 16-component modular orchestrator: Intent Router → Context Resolver → Curriculum Resolver → Retrieval Service → Teaching Planner → Problem Solver → Math/Science Verification → Lesson/Quiz/Homework/Revision Generators → Translation → Whiteboard/Voice Planners → Safety Layer → Quality Evaluation.
- **User Flow:** Student submits query → Safety & quota check → Intent Router classifies intent → Context & Curriculum Resolvers load grade/board/mastery/misconceptions (minimized PII) → Retrieval grounds response → Teaching Planner selects pedagogy → Tool Verifier checks math/science → Safety Layer validates output → Streamed response + logged telemetry.
- **Functional Reqs:** Strictly typed Pydantic input/output schemas per module; bounded step limits (no uncontrolled agent loops); deterministic enforcement of quotas, permissions, scoring, and timers; model-agnostic `LLMProvider` router.
- **Non-Functional Reqs:** First-token latency < 1.5s; full request timeout & graceful fallback.
- **API / DB / AI Deps:** `/api/v1/ai/orchestrate`, `/api/v1/ai/sessions/*`; `ai_sessions`, `ai_messages`, `ai_tool_calls`, `ai_evaluations`.
- **Security & Accessibility:** Prompt injection defenses; zero arbitrary code `eval`; no PII (name/email/phone) sent to LLM providers; screen-reader accessible chat & math output.
- **Acceptance Criteria & Tests:** Prompt injection tests fail safely; tool loop cap enforced; student profile context omits PII in provider payload snapshots.
- **Status:** `NOT_STARTED`

#### `F-018` — Multi-Mode Pedagogical AI Tutor & Doubt Solver
- **Role:** Student | **Priority:** P0 | **Phase:** Phase 3
- **User Problem:** Students learn poorly when an AI immediately dumps final answers without adapting to their grade, language, mastery, or exam goal.
- **Description:** Interactive tutor supporting 10 pedagogical modes (`Explain`, `Hint`, `Socratic`, `Step-by-step`, `Practice`, `Exam Prep`, `Revision`, `Advanced`, `Beginner-friendly`, `Homework Coaching`), context-aware of class/board/session/chapter/concept/mastery/misconceptions/language/exam target, with analogies, alternative methods, and follow-up checks.
- **User Flow:** Student asks doubt (text/image/voice) → Tutor detects mode (or user selects Socratic/Hint/Explain) → Guides student with graduated prompts & checks understanding before giving full answer.
- **Functional Reqs:** Default anti-spoiler policy for active homework/practice problems; mode switching mid-session; source citations back to published curriculum items.
- **Non-Functional Reqs:** Structured KaTeX math & clear reading level calibrated to grade.
- **API / DB / AI Deps:** `/api/v1/ai/tutor/turns`; `ai_sessions`, `ai_messages`, `student_concept_mastery`, `student_misconceptions`.
- **Security & Accessibility:** Child-safe content guardrails; moderation escalation; ARIA live streaming updates.
- **Acceptance Criteria & Tests:** In Socratic/Hint mode on a benchmark math set, AI does not emit final numerical solution on Turn 1; math steps verified; mode transitions persisted.
- **Status:** `NOT_STARTED`

#### `F-019` — Curriculum-Grounded Hybrid RAG Knowledge System
- **Role:** Student, AI System | **Priority:** P0 | **Phase:** Phase 3
- **User Problem:** Generic LLM parametric memory contradicts CBSE/NCERT definitions, uses wrong grade terminology, or fabricates references.
- **Description:** Hierarchy-preserving RAG pipeline (`SOURCE → INGESTION → PARSING → OCR → METADATA → HIERARCHICAL CHUNKING → EMBEDDING → PGVECTOR+FTS INDEX → HYBRID RETRIEVAL → RERANK → GENERATION → CITATION → VALIDATION`).
- **User Flow:** Rights-approved content is parsed preserving `book → chapter → section → topic → concept` hierarchy → Embedded & indexed → Retrieval filters strictly by `board, session, grade, subject, chapter, topic, concept, language, source_type, license, status='PUBLISHED', embedding_allowed=true` → Hybrid BM25/FTS + cosine similarity + reranker supplies grounded citations.
- **Functional Reqs:** Zero arbitrary fixed-token splitting across headings/formulas; mandatory metadata + rights filter before vector similarity; citation verification check.
- **Non-Functional Reqs:** Hybrid retrieval P95 < 120ms; benchmarked recall@5 tracked before adding external vector DBs.
- **API / DB / AI Deps:** `knowledge_documents`, `knowledge_chunks` (`vector(1536)` + `tsvector` GIN index); pgvector.
- **Security & Accessibility:** Quarantined/unlicensed/unpublished documents strictly excluded at SQL query level.
- **Acceptance Criteria & Tests:** Query with Class 6 filter never retrieves Class 12 chunks; unpublished/unlicensed chunks return 0 hits even on exact match.
- **Status:** `NOT_STARTED`

#### `F-020` — Deterministic Math & Science Verification Engine
- **Role:** AI System, Student | **Priority:** P0 | **Phase:** Phase 3
- **User Problem:** LLMs frequently make arithmetic, algebraic sign, calculus, unit-conversion, and chemical stoichiometry errors while sounding confident.
- **Description:** Tool-assisted verification layer integrating SymPy (algebra, equations, calculus, matrices, statistics), SciPy/NumPy (numerical), Pint/custom dimensional checker (physics units & dimensional consistency), and chemistry stoichiometry/equation balancer.
- **User Flow:** Problem Solver drafts symbolic/numeric formulation → Executes deterministic SymPy/Pint/Chemistry verifier in sandboxed tool → If verification fails, safely retries or switches method → If still unverified, surfaces explicit uncertainty warning instead of false confidence.
- **Functional Reqs:** Timeout & memory-bounded SymPy execution (no raw `exec` of arbitrary user/AI Python); step-by-step intermediate check; confidence flag stored in `ai_tool_calls`.
- **Non-Functional Reqs:** Verification < 500ms; deterministic repeatability.
- **API / DB / AI Deps:** Internal `verification` service + `ai_tool_calls` audit log.
- **Security & Accessibility:** AST-whitelisted expression parsing (never arbitrary `eval`/`exec`); clear error/uncertainty banners.
- **Acceptance Criteria & Tests:** Intentionally flawed LLM math draft is caught and corrected or flagged uncertain in unit/integration tests; malicious expression strings rejected by AST parser.
- **Status:** `NOT_STARTED`

#### `F-021` — AI Quality Evaluation & Human Review System
- **Role:** Academic Reviewer, Content Admin, Platform Admin | **Priority:** P1 | **Phase:** Phase 3
- **User Problem:** Model/prompt/RAG changes can silently degrade accuracy, grade appropriateness, or hint quality.
- **Description:** Automated + human-in-the-loop evaluation suite scoring correctness, grounding, curriculum alignment, grade level, difficulty, clarity, language quality, math/diagram correctness, safety, and hint quality across versioned golden datasets.
- **User Flow:** Code/prompt/model change triggers eval suite in CI/staging → Regression report compares scores against baseline → Low-confidence/failed items route to Academic Reviewer queue.
- **Functional Reqs:** Golden dataset per subject/grade; automated regression gates; human review queue UI & API; side-by-side failure inspection.
- **Non-Functional Reqs:** Eval runs reproducible with prompt/model version pinning.
- **API / DB / AI Deps:** `/api/v1/ai-evals/*`; `eval_datasets`, `eval_runs`, `eval_cases`, `ai_review_queue`.
- **Security & Accessibility:** Eval datasets free of real student PII; keyboard-triagable review queue.
- **Acceptance Criteria & Tests:** Prompt regression introducing answer leakage or math errors fails automated eval threshold; reviewer approve/reject logs immutable record.
- **Status:** `NOT_STARTED`

---

### Domain F: Interactive Live AI Classroom, Whiteboard & Voice/Multilingual (Phase 4 & 11)

#### `F-022` — Interactive Live AI Classroom (Structured Lesson Artifacts & State Machine)
- **Role:** Student | **Priority:** P0 | **Phase:** Phase 4
- **User Problem:** Unstructured streaming text chats fail to deliver coherent, multi-sensory lessons with pacing, checkpoints, and synchronization.
- **Description:** Server-controlled classroom state machine executing structured JSON lesson artifacts (`objectives`, ordered `segments` with `narration`, `canvas_actions`, `checkpoint`, `duration`). Supports Play, Pause, Resume, Repeat, Skip, Prev/Next Segment, Speed Control, Language Switching, Student Interruption ("Ask a Doubt"), Transcript, Subtitles, Notes, and Session Save/Resume.
- **User Flow:** Student starts concept lesson → Lesson Generator produces & validates structured lesson JSON → Server creates classroom session (`IDLE → READY → PLAYING_SEGMENT → CHECKPOINT_WAIT → DOUBT_INTERRUPTION → COMPLETED`) → WebSocket streams synchronized segment cues, audio URL/stream, subtitles, and whiteboard actions → Student interrupts with doubt → Tutor resolves doubt in context → Resumes exact segment state.
- **Functional Reqs:** Strict JSON Schema validation on generated lessons; server-authoritative `current_segment_index` & checkpoint state; persistent resume across devices/reloads.
- **Non-Functional Reqs:** WebSocket reconnect & state resync < 500ms; audio-visual drift < 250ms.
- **API / DB / AI Deps:** `REST /api/v1/classroom/*` + `WS /ws/v1/classroom/{session_id}`; `lesson_plans`, `classroom_sessions`, `classroom_events`, `classroom_checkpoints`.
- **Security & Accessibility:** Session token scoped to `student_id`; full transcript, closed captions, keyboard media controls (`Space` play/pause, arrow segment nav).
- **Acceptance Criteria & Tests:** Invalid lesson schema rejected before playback; browser refresh resumes exact segment & whiteboard state; doubt interruption pauses and cleanly resumes playback.
- **Status:** `NOT_STARTED`

#### `F-023` — Interactive Schema-Driven Whiteboard System
- **Role:** Student, AI Teacher, Teacher | **Priority:** P0 | **Phase:** Phase 4
- **User Problem:** Students need visual diagrams, math notation, graphs, physics free-body diagrams, and handwriting alongside explanations without unsafe code execution.
- **Description:** Interactive canvas (evaluated: `tldraw` / `Excalidraw` — see [WHITEBOARD_SPECIFICATION.md](file:///d:/go4guru/docs/WHITEBOARD_SPECIFICATION.md) for commercial licensing decision) supporting handwriting, text, shapes, arrows, lines, diagrams, KaTeX math blocks, function graphs, images, tables, geometry, timelines, concept/mind maps, eraser, undo/redo, zoom/pan, layering, PNG/SVG/JSON export, and event/snapshot persistence + replay.
- **User Flow:** AI emits validated structured whiteboard commands (`WRITE_TEXT`, `DRAW_LINE`, `DRAW_ARROW`, `DRAW_SHAPE`, `DRAW_GRAPH`, `DRAW_DIAGRAM`, `INSERT_IMAGE`, `INSERT_FORMULA`, `HIGHLIGHT`, `ERASE`, `MOVE`, `TRANSFORM`) → Client deterministically renders primitives → Student annotates/draws alongside → Events & periodic snapshots persisted to DB/S3.
- **Functional Reqs:** Zero arbitrary JS/HTML/SVG `<script>` execution; deterministic coordinate & bounding-box normalization; replay scrubber synchronized with lesson timeline.
- **Non-Functional Reqs:** Smooth 60fps pan/zoom; snapshot compression.
- **API / DB / AI Deps:** `/api/v1/whiteboard/*` + Classroom WS; `whiteboard_events`, `whiteboard_snapshots`, `whiteboard_assets`.
- **Security & Accessibility:** Strict JSON schema validation + SVG sanitization; alternative text summary of board state for screen readers & keyboard-accessible toolbar.
- **Acceptance Criteria & Tests:** Unrecognized action opcode or XSS SVG payload rejected; replay reconstructs exact canvas state from `events + base_snapshot`.
- **Status:** `NOT_STARTED`

#### `F-024` — Voice Provider Abstraction (ElevenLabs Initial Adapter) & Audio Pipeline
- **Role:** Student | **Priority:** P1 | **Phase:** Phase 4 & 11
- **User Problem:** Hardcoding one TTS/STT vendor locks in pricing/latency and breaks when regional Indian languages need better provider coverage.
- **Description:** Pluggable `VoiceProviderInterface` (`synthesize_speech`, `transcribe_audio`, `stream_speech`, `list_voices`, `get_capabilities`) with ElevenLabs as initial adapter + future adapters, supporting voice selection, speed control, text chunking, audio streaming, caching (where rights allow), replay/pause/resume, word/segment timing metadata for subtitles, latency & cost tracking, and fallback.
- **User Flow:** Lesson segment narration requests TTS → Voice Router checks capability registry & audio cache → Calls ElevenLabs (or fallback/text-only mode if quota/provider fails) → Streams audio + timing metadata → Logs characters/cost.
- **Functional Reqs:** Graceful degradation to synchronized text + subtitles if voice provider unavailable or quota exhausted; per-request cost & latency metering.
- **Non-Functional Reqs:** Streaming first-byte audio < 800ms where supported; circuit breaker on provider errors.
- **API / DB / AI Deps:** `/api/v1/voice/*`; `voice_profiles`, `audio_cache_metadata`, `voice_usage_logs`.
- **Security & Accessibility:** Audio uploads (STT) malware/size/duration checked; ElevenLabs API key strictly server-side; captions always available alongside audio.
- **Acceptance Criteria & Tests:** Swapping mock/alternate provider adapter requires zero changes in Classroom or Tutor callers; cost ledger records exact characters billed.
- **Status:** `NOT_STARTED`

#### `F-025` — Multilingual Architecture & Language Capability Registry
- **Role:** Student, Content Admin, Academic Reviewer | **Priority:** P1 | **Phase:** Phase 4 & 11
- **User Problem:** EdTech platforms often claim "15 languages supported" when TTS, STT, or scientific terminology fails badly in several languages.
- **Description:** Language-independent architecture supporting independent preferences (`ui_language`, `explanation_language`, `voice_language`, `subtitle_language`, `question_language`, `answer_language`), bilingual explanations (e.g., Hindi/Hinglish or Tamil explanation with English technical terms preserved), script/math rendering, and an explicit **Language Capability Registry** truthfully tracking per-language text/translation/TTS/STT/pronunciation/subtitle/academic review status and known limitations.
- **User Flow:** Student independently sets UI=English, Explanation=Hindi, Voice=Hindi, Subtitles=English → Registry validates capability → Bilingual terminology glossary preserves standard scientific terms (`Force / बल`) → Unsupported voice language transparently falls back with clear badge.
- **Functional Reqs:** Never advertise unsupported TTS/STT languages in UI; glossary term preservation during translation; human translation review workflow.
- **Non-Functional Reqs:** RTL support ready (for Urdu); UTF-8 Noto fonts for Indic scripts + KaTeX compatibility.
- **API / DB / AI Deps:** `/api/v1/languages/*`; `language_capabilities`, `user_language_preferences`, `terminology_glossary`, `content_translations`.
- **Security & Accessibility:** Proper `lang` HTML attributes per block for screen readers; clear fallback notifications.
- **Acceptance Criteria & Tests:** UI hides voice option or marks text-only for any language with `tts_enabled=false` in registry; changing explanation language does not alter UI chrome language.
- **Status:** `NOT_STARTED`

---

### Domain G: Adaptive Learning, Mastery, Spaced Repetition & Homework AI (Phase 5 & 6)

#### `F-026` — Event-Driven Concept Mastery & Adaptive Learning Engine
- **Role:** Student, Teacher, Mentor | **Priority:** P1 | **Phase:** Phase 5
- **User Problem:** A raw overall percentage hides whether a student truly understands concepts independently or relies heavily on hints.
- **Description:** Concept-level mastery engine powered by transactional outbox learning events (`LESSON_COMPLETED`, `CHECKPOINT_ANSWERED`, `QUESTION_ATTEMPTED`, `HINT_USED`, `QUIZ_COMPLETED`, `TEST_COMPLETED`, `HOMEWORK_EVALUATED`, `FLASHCARD_REVIEWED`). Tracks attempts, accuracy, difficulty weight, independent solving ratio, hint dependency, response time, confidence, misconceptions, retention decay, and explainable next-step recommendations across the full loop (`LEARN → CHECKPOINT → PRACTICE → EVALUATE → UPDATE MASTERY → IDENTIFY WEAKNESS → REMEDIATE → RETEST → ADVANCE → SCHEDULE REVISION`).
- **User Flow:** Student solves problems → API commits attempt + outbox event → Worker idempotently updates `student_concept_mastery` using transparent rule-based scoring (v1) → Dashboard explains *why* a concept is weak (e.g., "35% independent accuracy on Sign Conventions; 3 hints used") and queues remediation.
- **Functional Reqs:** Idempotent event consumer (`processed_event_ids`); explainable mastery breakdown stored in `evidence` JSON; pluggable mastery estimator interface for future BKT/IRT/ML upgrade.
- **Non-Functional Reqs:** Event-to-mastery update lag < 5s under normal load.
- **API / DB / AI Deps:** `/api/v1/learning/*`; `outbox_events`, `learning_events`, `student_concept_mastery`, `student_misconceptions`, `learning_paths`, `learning_recommendations`.
- **Security & Accessibility:** Student mastery visible only to student + authorized teacher/mentor + summarized to consented parent; color + icon + text mastery indicators (never color-alone).
- **Acceptance Criteria & Tests:** Duplicate event delivery does not double-count attempts; mastery score visibly rises on independent correct solves of higher difficulty and decays/flags on repeated hint dependence or failure.
- **Status:** `NOT_STARTED`

#### `F-027` — Spaced Repetition & Multi-Modal Flashcards
- **Role:** Student | **Priority:** P1 | **Phase:** Phase 5
- **User Problem:** Students forget formulas, biology facts, reactions, and mistakes made weeks before exams without structured spaced review.
- **Description:** Flashcard system supporting Concept, Formula, Definition, Vocabulary, Diagram, Question, Cloze, Image, Chemistry, and Map cards, driven by configurable/testable scheduling (SM-2 / FSRS-inspired configurable algorithm) with `Again / Hard / Good / Easy` ratings, Daily Revision Queue, Weak Concept Queue, Missed-Question Auto-Cards, Exam Revision Plans, and Overdue Analytics.
- **User Flow:** Student opens Today's Revision Queue → Reviews due flashcards & auto-generated cards from past mistakes → Rates recall (`Again/Hard/Good/Easy`) → Scheduler computes next interval, ease/stability, and updates retention telemetry.
- **Functional Reqs:** Missed assessment/practice questions can auto-enqueue into revision deck; deterministic configurable scheduler parameters per subject/exam.
- **Non-Functional Reqs:** Card flip & queue prefetch < 100ms; offline-tolerant review sync.
- **API / DB / AI Deps:** `/api/v1/revision/*`, `/api/v1/flashcards/*`; `flashcards`, `student_flashcards`, `flashcard_reviews`, `revision_plans`.
- **Security & Accessibility:** Keyboard shortcuts (`Space` flip, `1-4` rate); ARIA card front/back announcements.
- **Acceptance Criteria & Tests:** Pure unit tests verify interval progression across `Again/Hard/Good/Easy` sequences; overdue counts accurately filter by `due_at <= now()`.
- **Status:** `NOT_STARTED`

#### `F-028` — Personalized Study Plans & Revision Planner
- **Role:** Student, Mentor | **Priority:** P1 | **Phase:** Phase 5
- **User Problem:** Students preparing for Boards/JEE/NEET struggle to balance new chapters, homework, weak areas, and spaced revision across target exam dates.
- **Description:** Deterministic + AI-assisted study plan generator scheduling daily learning blocks based on target exam date, daily available hours, curriculum prerequisites, mastery gaps, upcoming teacher assignments, and overdue revisions.
- **User Flow:** Student sets target exam & weekly hours → System generates weekly/daily plan → Updates dynamically as lessons/quizzes/revisions complete → Student tracks daily tasks on dashboard.
- **Functional Reqs:** Deterministic scheduling constraints (never overbook hours, respect prerequisites); mentor can customize/override student plan.
- **Non-Functional Reqs:** Plan recalculation < 500ms.
- **API / DB / AI Deps:** `/api/v1/study-plans/*`; `study_plans`, `study_plan_items`, `student_goals`.
- **Security & Accessibility:** Scoped to student + assigned mentor; accessible calendar/list toggle.
- **Acceptance Criteria & Tests:** Completing an item updates plan progress; overdue weak-concept tasks reprioritize cleanly without creating duplicate items.
- **Status:** `NOT_STARTED`

#### `F-029` — Homework AI (Image/PDF Upload, OCR, Step Analysis & Graduated Hints)
- **Role:** Student, Teacher | **Priority:** P1 | **Phase:** Phase 6
- **User Problem:** Students solving homework on paper need targeted step-by-step error diagnosis (e.g., sign error, wrong unit, unbalanced equation), not instant answer copying.
- **Description:** Multi-page Image/PDF upload pipeline (`UPLOAD → VALIDATE → MALWARE/MIME CHECK → OCR/VISION EXTRACTION → DETECT QUESTION → EXTRACT STUDENT WORK → SUBJECT ANALYZER + VERIFIER → ERROR CLASSIFICATION → GRADUATED HINTS → STUDENT RETRY`). Subject-specific diagnostics for Maths, Physics, Chemistry, English, and Social Science.
- **User Flow:** Student uploads photo/PDF of handwritten or printed work → Private S3 upload → Async worker runs OCR + math/science verification → Identifies step where error occurred (e.g., "Line 3: Sign flip when moving `-2x`") → Displays Level 1 Hint (concept nudge) → Student retries or requests Level 2/3 hint before solution reveal.
- **Functional Reqs:** Multi-page support; graduated 3-level hints by default; teacher visibility into homework submissions if linked to an assignment; strict file size/type limits.
- **Non-Functional Reqs:** Async status notifications via WebSocket/polling; OCR accuracy tracking.
- **API / DB / AI Deps:** `/api/v1/homework/*`; `homework_submissions`, `homework_files`, `homework_ocr_results`, `homework_evaluations`, `homework_feedback`.
- **Security & Accessibility:** Private bucket + short-lived signed URLs; EXIF metadata stripped on upload; malware scan hook; OCR extracted text visible & editable by student for accessibility/correction.
- **Acceptance Criteria & Tests:** Invalid MIME/oversized upload rejected with 415/413; math sign error detected and receives Level 1 hint without dumping final answer on initial evaluation.
- **Status:** `NOT_STARTED`

---

### Domain H: Role Dashboards & Workflows (Phase 1, 7, 8, 9)

#### `F-030` — Personalized Student Dashboard
- **Role:** Student | **Priority:** P0 | **Phase:** Phase 1 (progressively enriched Phases 2–6)
- **User Problem:** Students need one focused, uncluttered home base tailored to their grade, board, exam target, and immediate next action.
- **Description:** Uncluttered workspace surfacing Resume Learning, Today's Study Plan, Enrolled Subjects, Recent Lessons, Upcoming Revision & Due Flashcards, Quick Practice/Quizzes/Tests, Homework Status, Weak Concepts, Mastery Summary, Learning Streaks/Achievements, Exam Prep Hub, and Explainable Recommendations.
- **User Flow:** Student logs in → Dashboard loads real personalized data (zero fake/hardcoded stats; unimplemented future widgets either hidden behind feature flags or explicitly marked "Phase X / Not Yet Enabled") → Clicks Resume or Today's Task.
- **Functional Reqs:** Adapts layout/modules by grade (6–10 CBSE vs 11–12 Boards/JEE/NEET) and enabled entitlements; genuine empty states for new students with onboarding prompt.
- **Non-Functional Reqs:** Initial dashboard render < 400ms via aggregated query/cache; responsive mobile/tablet/desktop.
- **API / DB / AI Deps:** `/api/v1/dashboard/student`; aggregates `learning_paths`, `student_concept_mastery`, `revision`, `assessments`, `study_plans`.
- **Security & Accessibility:** Strictly `student_id` scoped; WCAG AA contrast, semantic landmarks.
- **Acceptance Criteria & Tests:** New user sees real empty/onboarding state (never fake streaks/charts); every metric traces directly to DB records.
- **Status:** `NOT_STARTED`

#### `F-031` — Teacher Dashboard, Assignments & AI-Assisted Grading with Override
- **Role:** Teacher | **Priority:** P1 | **Phase:** Phase 7
- **User Problem:** Teachers spend hours creating tests/assignments, grading subjective work, and spotting which concepts a whole class misunderstood.
- **Description:** Class & section management, student roster, assignment/quiz/test builder (selecting from Question Bank or authoring original items), submission review queue, AI-assisted rubric grading with mandatory **human teacher override**, class & individual analytics, weak concept heatmaps, completion tracking, and CSV/PDF report exports.
- **User Flow:** Teacher selects Class 10-A → Creates Homework/Test Assignment → Students submit → AI proposes rubric breakdown & draft feedback → Teacher reviews, adjusts marks/comments (logged as override), publishes grades → Inspects class weak-concept report.
- **Functional Reqs:** AI grades always flagged `ai_suggested` until teacher approves/overrides; original AI suggestion & teacher final score both preserved in audit history.
- **Non-Functional Reqs:** Bulk grading view keyboard-navigable; export async for large cohorts.
- **API / DB / AI Deps:** `/api/v1/teachers/*`, `/api/v1/assignments/*`; `assignments`, `assignment_submissions`, `teacher_notes`, `teacher_reports`.
- **Security & Accessibility:** Teacher restricted strictly to `staff_assignments` classes; cross-class access blocked.
- **Acceptance Criteria & Tests:** Teacher overriding AI grade updates authoritative score and creates audit entry; unassigned teacher gets 403.
- **Status:** `NOT_STARTED`

#### `F-032` — Mentor / Tutor Dashboard & Coaching Workflows
- **Role:** Mentor | **Priority:** P1 | **Phase:** Phase 7
- **User Problem:** Academic mentors need longitudinal visibility into assigned mentees' goals, study habits, alerts, and intervention outcomes.
- **Description:** Assigned student portfolio, learning goal management, custom study plan editing, mentoring session notes, follow-up action items/tasks, weakness alerts (e.g., streak drop, repeated misconception, mock score dip), and intervention effectiveness tracking.
- **User Flow:** Mentor views alert ("Student X struggling with Rotational Dynamics") → Reviews mastery & test speed telemetry → Logs mentoring session + assigns targeted remediation & follow-up task → Tracks completion.
- **Functional Reqs:** Session logs with private mentor notes vs shared student action items; automated risk/drop alerts.
- **Non-Functional Reqs:** Alert computation runs in background worker.
- **API / DB / AI Deps:** `/api/v1/mentors/*`; `mentor_assignments`, `mentoring_sessions`, `follow_up_tasks`, `student_goals`, `mentor_alerts`.
- **Security & Accessibility:** Mentor restricted to assigned mentees; private mentor notes hidden from student/parent unless shared.
- **Acceptance Criteria & Tests:** Unassigned mentor receives 403; session follow-up tasks appear in student's study plan.
- **Status:** `NOT_STARTED`

#### `F-033` — Parent / Guardian Dashboard
- **Role:** Parent | **Priority:** P1 | **Phase:** Phase 8
- **User Problem:** Parents want reassurance on effort, attendance/activity, weak areas, and upcoming exams without invading private AI tutoring chats or seeing overwhelming jargon.
- **Description:** Linked child switcher, consent & privacy control panel, high-level progress & goal attainment, weekly learning activity, completed lessons, practice & mastery summaries, weak areas, upcoming tests, overdue revision indicator, downloadable summaries, and notification preferences.
- **User Flow:** Consented Parent logs in → Selects child → Views weekly digest & upcoming exams → Adjusts study/safety notifications or revokes/updates consent settings.
- **Functional Reqs:** Strictly aggregated/summarized views; **zero access to raw AI doubt chats or private student notes**.
- **Non-Functional Reqs:** Plain-language summaries translatable into parent's preferred UI language.
- **API / DB / AI Deps:** `/api/v1/parents/dashboard`; reads aggregated `analytics_snapshots`, `assessments`, `consents`, `student_goals`.
- **Security & Accessibility:** Integration tests verify zero raw `ai_messages` leak in any parent API response.
- **Acceptance Criteria & Tests:** Parent views accurate summary synced with child's completed tests; unlinked parent gets 403.
- **Status:** `NOT_STARTED`

---

### Domain I: Platform Ops, Analytics, Notifications, Monetization & Safety (Phase 1–12)

#### `F-034` — Learning-Oriented Product Analytics & Event Pipeline
- **Role:** Platform Admin, School Admin, Teacher, Student | **Priority:** P1 | **Phase:** Phase 2 & 5
- **User Problem:** Engagement-only metrics ("minutes on app") reward passive scrolling instead of genuine learning and retention.
- **Description:** Dual analytics separation: **Learning Analytics** (lessons completed, objectives achieved, practice accuracy, independent solving rate, hint dependency, mastery gain, retention curve, revision completion, test trajectory, weak concept resolution, homework completion) and **Product/Usage Analytics** (teacher engagement, institution adoption, feature funnels).
- **User Flow:** Transactional domain mutations emit outbox events → Worker aggregates hourly/daily snapshots → Role dashboards query pre-aggregated snapshots.
- **Functional Reqs:** Separate schema/tables for operational learning metrics vs product telemetry; anonymized exports for research/eval.
- **Non-Functional Reqs:** Dashboard queries read snapshots (< 150ms) rather than heavy raw event scans.
- **API / DB / AI Deps:** `/api/v1/analytics/*`; `learning_events`, `assessment_events`, `usage_events`, `analytics_snapshots`.
- **Security & Accessibility:** PII stripped from product analytics; accessible tables + data alternatives for charts.
- **Acceptance Criteria & Tests:** Outbox worker updates snapshots idempotently; charts provide accessible tabular data views.
- **Status:** `NOT_STARTED`

#### `F-035` — Notification & Alerting System
- **Role:** All Roles | **Priority:** P1 | **Phase:** Phase 5 & 7
- **User Problem:** Students miss spaced repetition due dates and assignment deadlines; parents/mentors miss critical progress alerts.
- **Description:** Multi-channel notification engine (In-app feed, Email, optional Push/SMS/WhatsApp adapter) with user preferences, quiet hours (especially for minors), delivery tracking, and templates.
- **User Flow:** Event triggers rule (e.g., assignment published, revision due, parent consent requested) → Worker renders localized template → Dispatches respecting user quiet hours & preferences → Updates in-app inbox.
- **Functional Reqs:** Idempotent dispatch keys; child-appropriate quiet hours; unsubscribe/preference controls.
- **Non-Functional Reqs:** High-priority security/consent notifications bypass marketing opt-outs safely.
- **API / DB / AI Deps:** `/api/v1/notifications/*`; `notifications`, `notification_preferences`, `notification_deliveries`.
- **Security & Accessibility:** No sensitive student PII or answers in lock-screen push previews; accessible notification drawer.
- **Acceptance Criteria & Tests:** Opted-out channel not called; duplicate event sends only 1 notification.
- **Status:** `NOT_STARTED`

#### `F-036` — Subscription, Entitlements, Quotas & Billing Infrastructure
- **Role:** Platform Admin, School Admin, Parent, Student | **Priority:** P1 | **Phase:** Phase 9 & 10
- **User Problem:** AI tokens and voice minutes have real variable costs; hardcoded plan checks across UI/API break monetization flexibility.
- **Description:** Configurable Plans (Free, Premium Student, Board, JEE, NEET, Mentor/Tutor, School/Coaching Institutional Licenses), Entitlements engine (feature flags + AI token/credit caps + voice minute quotas), Usage Ledger, Payment Provider Adapter (Razorpay/Stripe abstraction), Invoices, Transactions, Refunds, and Billing History.
- **User Flow:** User/School selects Plan → Entitlements attached to subscription → Every AI/Voice call checks deterministic quota in Redis/DB → Usage recorded → Payment webhook updates subscription state idempotently.
- **Functional Reqs:** Zero hardcoded plan names/limits in code; webhook signature verification + idempotent event handling; institutional seat management.
- **Non-Functional Reqs:** Quota check < 10ms; grace handling mid-lesson if quota hits cap.
- **API / DB / AI Deps:** `/api/v1/billing/*`, `/api/v1/entitlements/*`; `plans`, `plan_entitlements`, `subscriptions`, `usage_ledgers`, `transactions`, `invoices`, `refunds`.
- **Security & Accessibility:** PCI scope offloaded to payment gateway; minors require parent/guardian checkout consent; accessible invoice PDFs/views.
- **Acceptance Criteria & Tests:** Quota enforcement blocks excess AI/voice calls with clean 402/429 upgrade message; duplicate webhook events are idempotent.
- **Status:** `NOT_STARTED`

#### `F-037` — Cost Telemetry & Unit Economics Engine
- **Role:** Platform Admin | **Priority:** P1 | **Phase:** Phase 3 & 4
- **User Problem:** Unmonitored LLM, embedding, and ElevenLabs voice usage can make unit economics unsustainable overnight.
- **Description:** Real-time ledger tracking LLM input/output tokens & model costs, ElevenLabs characters/minutes, STT minutes, embedding tokens, search/storage/compute estimates, rolling up to **Cost per Student / Lesson / AI Session / Voice Minute / Completed Learning Session**, plus model routing, caching, and budget circuit-breaker alerts.
- **User Flow:** AI/Voice adapter emits exact token/character/duration telemetry → Cost engine prices using versioned rate card → Admin dashboard displays unit economics & budget burn alerts.
- **Functional Reqs:** Rate cards stored in DB/config with effective dates; threshold alerts trigger model downgrade or rate throttling.
- **Non-Functional Reqs:** Async telemetry ingestion adds < 2ms overhead.
- **API / DB / AI Deps:** `/api/v1/admin/economics/*`; `provider_rate_cards`, `ai_cost_events`, `voice_usage_logs`, `cost_rollups`.
- **Security & Accessibility:** Strictly `platform_admin` only.
- **Acceptance Criteria & Tests:** Rate card change computes accurate cost per session; budget cap alert fires in test simulation.
- **Status:** `NOT_STARTED`

#### `F-038` — Child Safety, Moderation, Reporting & DPDP Data Governance
- **Role:** Student, Parent, Platform Admin | **Priority:** P0 | **Phase:** Phase 1 & 3 & 8
- **User Problem:** Serving minors under Indian privacy expectations (DPDP Act) requires age gates, safety filtering, human escalation, retention limits, and verifiable deletion.
- **Description:** Child-safe AI system prompts + input/output moderation classifiers, user "Report Content/AI Issue" flow, moderation review queue, PII minimization wrapper before external AI calls, configurable data retention schedules, and right-to-erasure / account deletion workflow.
- **User Flow:** Student flags inappropriate output or safety classifier trips → Interaction quarantined, safe supportive fallback shown, ticket queued for human review → Account deletion request triggers scheduled anonymization/purge respecting legal/academic audit rules.
- **Functional Reqs:** Self-harm/abuse/inappropriate-content safe redirection; no advertising/behavioral profiling of minors; legal review gate before claiming DPDP compliance.
- **Non-Functional Reqs:** Moderation classifier latency < 150ms.
- **API / DB / AI Deps:** `/api/v1/safety/*`, `/api/v1/privacy/export-delete/*`; `safety_incidents`, `moderation_queue`, `data_deletion_requests`, `audit_logs`.
- **Security & Accessibility:** Immutable audit trail; high-visibility accessible "Report / Get Help" button in all AI & content surfaces.
- **Acceptance Criteria & Tests:** Unsafe prompt test suite triggers safe refusal & incident record; deletion workflow purges/anonymizes PII across tables and object storage.
- **Status:** `NOT_STARTED`

#### `F-039` — Platform Administration, Feature Flags, Health & Audit Logs
- **Role:** Platform Admin | **Priority:** P0 | **Phase:** Phase 1 & 9
- **User Problem:** Operators need safe feature rollouts, immutable audit trails, system health diagnostics, and support tools.
- **Description:** Platform console managing global/tenant feature flags, role assignments, system health (DB/Redis/Queue/AI/Voice provider circuit breakers), searchable immutable audit logs, and support impersonation (strictly read-only, MFA-gated, time-boxed, logged, blocked for private minor chats).
- **User Flow:** Platform Admin enables flag for beta tenant → Views provider latency/error rates → Inspects audit log for admin action.
- **Functional Reqs:** Append-only audit log for auth, RBAC, rights, grading overrides, billing, and deletion actions.
- **Non-Functional Reqs:** Audit log writes must not fail silently on sensitive mutations.
- **API / DB / AI Deps:** `/api/v1/admin/*`; `feature_flags`, `audit_logs`, `system_health_checks`.
- **Security & Accessibility:** MFA required; impersonation banned from reading student private AI messages unless safety-incident escalated with dual control.
- **Acceptance Criteria & Tests:** All privileged mutations emit audit records; feature flag toggles gate endpoints reliably.
- **Status:** `NOT_STARTED`

#### `F-040` — Mobile & Offline-Safe Scale Readiness
- **Role:** Student, Parent, Teacher | **Priority:** P2 | **Phase:** Phase 12
- **User Problem:** Indian students often study on mid-tier Android phones over unstable 3G/4G networks and need camera homework capture & offline-resilient study/revision.
- **Description:** Responsive PWA / mobile app client (React Native/Expo or Capacitor/PWA evaluated at Phase 12), camera capture & compression for homework, mobile voice push-to-talk, offline-cached flashcards & practice drafts with conflict-safe sync, push notifications, and load-tested horizontal scaling.
- **User Flow:** Student loses connectivity during flashcard review or practice → Client queues responses locally in IndexedDB/SQLite → Reconnects → Idempotently syncs with server.
- **Functional Reqs:** Idempotent sync APIs; compressed image upload (<2MB target); adaptive low-bandwidth audio mode.
- **Non-Functional Reqs:** Tested under simulated 3G throttling & 10k concurrent classroom/exam load tests.
- **API / DB / AI Deps:** Sync endpoints + existing versioned APIs; push notification device tokens (`devices`).
- **Security & Accessibility:** Encrypted local storage for auth tokens; 44x44px minimum touch targets.
- **Acceptance Criteria & Tests:** Offline flashcard review syncs cleanly without duplicates on reconnect; load test meets P95 SLOs.
- **Status:** `NOT_STARTED`

---

## 4. Cross-Cutting Non-Functional & Compliance Requirements

1. **Zero Fake Functionality Rule:** Unimplemented phase modules MUST NOT display fake static charts or simulated AI answers; any UI shell for a later phase must be gated behind feature flags (`feature_flags`) or explicitly indicate its pending phase status.
2. **Authoritative Server Control:** Exam timers, scoring, negative/partial marking, permissions, tenant isolation, quotas, and billing state execute exclusively on the server.
3. **Observability:** OpenTelemetry traces, structured JSON logs with correlation IDs, Prometheus/cloud metrics (API, DB pool, queue depth, worker failures, WebSocket drops, AI/Voice latency & error rates).
4. **Accessibility:** WCAG 2.1 Level AA across all portals, math ARIA/MathML fallback via KaTeX, captions/transcripts on all voice lessons, keyboard navigation on whiteboard & exam interfaces.
