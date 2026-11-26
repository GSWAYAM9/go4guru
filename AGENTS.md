# AGENTS.md — Non-Negotiable Project Rules

> **Scope:** Applies unconditionally to `d:\go4guru` and all subdirectories. Every AI agent and engineering session MUST obey these rules alongside detailed specs in `docs/`.

---

## 1. Product Vision & Scope
Build a production-grade, multilingual, curriculum-grounded AI learning ecosystem serving **Classes 6–12** (**CBSE**, **Board Exams**, **JEE Main**, **JEE Advanced**, **NEET**) across **8 roles**: `student`, `parent`, `teacher`, `mentor`, `school_admin`, `content_admin`, `academic_reviewer`, and `platform_admin`.  
Scope unifies curriculum learning, pedagogical AI tutoring, live AI classroom (synchronized voice + whiteboard), canonical question bank, Excel ingestion, practice/quiz/exam engines, adaptive concept mastery, spaced repetition, OCR homework coaching, role dashboards, multi-tenant school management, billing/unit economics, and child safety.

## 2. Complete Feature Inventory
All 40 canonical capabilities (`F-001`–`F-040`) are specified in [docs/PRODUCT_REQUIREMENTS_DOCUMENT.md](docs/PRODUCT_REQUIREMENTS_DOCUMENT.md) and tracked in [docs/MASTER_FEATURE_CHECKLIST.md](docs/MASTER_FEATURE_CHECKLIST.md):
- **Phase 1 (Core):** `F-001` Auth/MFA, `F-002` Backend RBAC, `F-005` Versioned Curriculum, `F-006` CMS, `F-007` Rights Governance, `F-008` Canonical Question Bank, `F-009` Excel Importer, `F-010` Practice/Notes/Bookmarks, `F-030` Student Dashboard Core, `F-038` Child Safety Baseline, `F-039` Admin/Flags/Audit.
- **Phase 2 (Assessments):** `F-011` Quiz Engine, `F-012` Server-Authoritative Assessment Engine, `F-013` CBSE Prep, `F-034` Learning Analytics & Outbox.
- **Phase 3 (AI Tutor):** `F-017` 16-Module Orchestrator, `F-018` Multi-Mode Pedagogical Tutor, `F-019` Hybrid RAG, `F-020` Deterministic Math/Science Verifier, `F-021` AI Eval & Review Queue, `F-037` Cost Telemetry.
- **Phase 4 (Live Classroom):** `F-022` Interactive Live Classroom, `F-023` Schema-Driven Whiteboard, `F-024` Voice Provider Abstraction (ElevenLabs).
- **Phase 5 (Adaptive):** `F-026` Concept Mastery Engine, `F-027` Spaced Repetition Flashcards, `F-028` Study Planner, `F-035` Notifications.
- **Phase 6 (Homework):** `F-029` Image/PDF Upload, OCR & Graduated Hint Homework AI.
- **Phase 7 (Educators):** `F-031` Teacher Dashboard & AI-Assisted Grading + Override, `F-032` Mentor Dashboard & Interventions.
- **Phase 8 (Parents):** `F-004` Guardian Consent & Linking, `F-033` Privacy-Preserving Parent Dashboard.
- **Phase 9 (Institutions & Billing):** `F-003` Multi-Tenant Institutions, `F-036` Plans, Quotas, Billing & Invoices.
- **Phase 10 (Exams):** `F-014` JEE Main, `F-015` JEE Advanced, `F-016` NEET (+ full CBSE Boards).
- **Phase 11 (Multilingual):** `F-025` Multilingual Expansion & Capability Registry.
- **Phase 12 (Mobile & Scale):** `F-040` Mobile/PWA, Camera, Offline Sync & Load Scale.

## 3. Current Architecture & Approved Technology Stack
- **Phase 0 State:** Workspace `d:\go4guru` currently holds `docs/` specs only (no app code yet; host runs Windows, Node `v22.16.0`, `pnpm 12.3.4`, Python `3.12.10`, `postgresql-x64-18`, `WSL 2 Ubuntu`).
- **Approved Stack ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)):**
  - **Web:** Next.js (App Router) + React + TypeScript + Tailwind CSS + accessible UI primitives + KaTeX (`apps/web`).
  - **Backend API:** FastAPI + Python 3.12 + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic (`apps/api`).
  - **Workers:** Python async workers (`apps/worker`) over Redis.
  - **Primary DB & Search:** PostgreSQL 18 + `pgvector` + PostgreSQL `tsvector` FTS.
  - **Cache / Queue / PubSub:** Redis.
  - **Object Storage:** S3-compatible private buckets (MinIO local → S3/GCS/R2 cloud) with signed URLs.

## 4. Architecture Boundaries & Modularity
- **Modular Monolith:** Backend modules live under `apps/api/src/modules/{identity,organization,curriculum,content,question_bank,assessment,learning,revision,ai,classroom,homework,teacher,mentor,billing,analytics,notifications}`.
- **Import Discipline:** Modules MUST communicate only via explicit public module contracts (`public.py`/`contracts.py`) or transactional outbox events (`outbox_events`). Circular imports and cross-module raw table writes are forbidden.
- **Deterministic vs. AI Boundary:** Permissions, exam timers, scoring, negative/partial marking, quotas, billing, scheduling constraints, and content rights checks MUST run in deterministic code—never delegated to an LLM.
- **No Premature Microservices:** Do not split services until scaling/isolation thresholds in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) are met.

## 5. Database Conventions
- Schema specification: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).
- Use PostgreSQL 18 with UUIDv7/`gen_random_uuid()` PKs, `timestamptz` `created_at`/`updated_at`, explicit FKs, `CHECK` constraints, and composite indexes leading with `tenant_id` on tenant tables.
- Normalize structured relational data; reserve `JSONB` strictly for genuinely polymorphic schemas (e.g., exam pattern rules, whiteboard actions, evidence).
- All schema changes MUST use backward-compatible Alembic expand/contract migrations.

## 6. API Conventions
- Specification: [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md).
- REST endpoints versioned under `/api/v1/...`; realtime classroom under `/ws/v1/...`; OpenAPI 3.1 kept current.
- Enforce Pydantic v2 input/output schemas, standard `{ "error": { "code", "message", "details", "request_id" } }` envelope, cursor pagination for large collections, `Idempotency-Key` on critical mutations, and Redis rate limiting.

## 7. Security & Privacy Requirements
- Specs: [docs/SECURITY.md](docs/SECURITY.md), [docs/PRIVACY_AND_CHILD_SAFETY.md](docs/PRIVACY_AND_CHILD_SAFETY.md).
- Hash passwords with Argon2id; issue short-lived JWTs + HTTP-only rotating refresh cookies; enforce TOTP MFA for `platform_admin`, `school_admin`, `content_admin`, and `academic_reviewer`.
- Enforce deny-by-default RBAC in backend dependencies—never UI-only hiding.
- Validate uploads (MIME/magic bytes, size caps, formula-injection stripping, EXIF removal, malware scan hook) into private buckets served only via short-lived signed URLs.
- Never commit secrets, API keys, or `.env*` files; never expose private keys in `NEXT_PUBLIC_*`.
- Never execute arbitrary code (`eval`/`exec`/raw SVG `<script>`); wrap retrieved RAG text as untrusted data to defend against prompt injection.

## 8. Child Safety Requirements
- Enforce minor age gates and verifiable parent/guardian consent (`consents`, `parent_links`).
- **Parent Boundary:** Linked parents receive privacy-preserving learning summaries and MUST be denied access (403) to raw student AI chat transcripts (`ai_messages`).
- **PII Minimization:** Strip student names, emails, phones, and school identifiers before sending context to external AI, OCR, or voice providers.
- Include child-safe AI moderation, self-harm/distress helpline redirection, and one-click issue reporting.
- Never claim legal DPDP Act compliance until qualified legal counsel reviews the implemented system.

## 9. AI Grounding & Evaluation Rules
- Specs: [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md), [docs/AI_EVALUATION.md](docs/AI_EVALUATION.md).
- Use the 16-module orchestrator (`IntentRouter` through `QualityEvaluator`); forbid monolithic all-in-one prompts and cap tool/retry loops (max 2 verifier retries).
- Default `spoiler_guard = true` in Hint, Socratic, and Homework Coaching modes (never dump final answers on Turn 1).
- Ground curriculum answers in hybrid `pgvector` + FTS RAG filtered strictly by `status = 'PUBLISHED'` and `embedding_allowed = true`.
- Verify math, physics units, and chemical equations deterministically via sandboxed SymPy/SciPy/Pint/stoichiometry tools; surface honest uncertainty if verification fails.
- Run AI evaluation regression suites whenever prompts, models, retrieval, tools, or curriculum change; route flagged/AI-authored high-stakes content to `ai_review_queue`.

## 10. Curriculum & Question-Bank Rules
- Specs: [docs/CURRICULUM_ARCHITECTURE.md](docs/CURRICULUM_ARCHITECTURE.md), [docs/QUESTION_BANK_SCHEMA.md](docs/QUESTION_BANK_SCHEMA.md).
- Follow the 11-level versioned hierarchy (`Board → Session → Grade → Subject → Book → Chapter → Section → Topic → Concept → Learning Objective → Prerequisite`). Never hardcode syllabus trees in UI components.
- Support 18+ canonical question types with immutable `question_versions` pinned by assessments.
- Student attempt endpoints MUST redact `correct_answer_jsonb`, option `is_correct`, and solutions until submission.

## 11. PYQ Provenance Rules
- **Never** label AI-generated or unverified questions as Previous Year Questions (`is_pyq = true`).
- Genuine PYQs MUST record verified `exam_name`, `exam_year`, `verification_status = 'verified'`, `verified_by`, and available `session`/`shift`/`paper_code`/`source_url` provenance.

## 12. Excel Import Rules
- Spec: [docs/EXCEL_IMPORT_SPECIFICATION.md](docs/EXCEL_IMPORT_SPECIFICATION.md).
- Never modify original uploaded Excel files; store immutable copies in private object storage.
- Never hardcode assumed Excel column names; implement the 14-stage pipeline (`Upload → File Validation → Sheet Detection → Staging → Column Mapping → Normalization → Validation → Duplicate Detection → Academic Mapping → Source Validation → Preview → Review → Import → Publish`) with formula-injection neutralization, SHA-256/canonical deduplication, row-level error reporting, idempotency, and batch rollback.

## 13. Content Licensing & Rights Rules
- Spec: [docs/CONTENT_RIGHTS.md](docs/CONTENT_RIGHTS.md).
- **Quarantine Mandate:** The 374 third-party ALLEN® PDFs observed in sibling `D:\class-*` directories MUST NOT be copied, hosted, parsed, or RAG-indexed without explicit written licensing.
- Every CMS item, question, and RAG document requires `source_id`, `license_id`, and `legal_review_status = 'approved'`. Prefer official NCERT links (`OFFICIAL_LINK`) and original authored content (`ORIGINAL_PLATFORM`). Never imply NCERT/CBSE/NTA endorsement.

## 14. Multilingual Architecture
- Spec: [docs/VOICE_MULTILINGUAL_ARCHITECTURE.md](docs/VOICE_MULTILINGUAL_ARCHITECTURE.md).
- Maintain 6 independent language preferences (`ui`, `explanation`, `voice`, `subtitle`, `question`, `answer`).
- Drive UI language/voice options strictly from the **Language Capability Registry** (`language_capabilities`); never advertise unsupported TTS/STT or unreviewed academic translations. Preserve KaTeX math and bilingual STEM glossary terms.

## 15. Voice Provider Abstraction
- Wrap all TTS/STT behind `VoiceProviderInterface` (`apps/api/src/modules/classroom/voice/`) with **ElevenLabs** as initial adapter.
- Cache static lesson audio by content hash in private S3, track exact characters/duration/cost in `voice_usage_logs`, and degrade gracefully to synchronized captions/text on provider failure or quota exhaustion.

## 16. Whiteboard Architecture
- Spec: [docs/WHITEBOARD_SPECIFICATION.md](docs/WHITEBOARD_SPECIFICATION.md).
- Use validated structured `WhiteboardAction` opcodes (`WRITE_TEXT`, `INSERT_FORMULA`, `DRAW_LINE`, `DRAW_ARROW`, `DRAW_SHAPE`, `DRAW_GRAPH`, `DRAW_DIAGRAM`, `INSERT_IMAGE`, `HIGHLIGHT`, `ERASE`, `MOVE`, `TRANSFORM`). Never execute AI-generated code inside the canvas.
- Persist append-only `whiteboard_events` + periodic `whiteboard_snapshots` for replay/resume, and include `aria_summary` for screen-reader accessibility. Resolve `Excalidraw` (MIT) vs `tldraw` (commercial license) in `DECISION_LOG.md` before Phase 4.

## 17. Assessment & Classroom Reliability Rules
- Server MUST control assessment `started_at`, `expires_at`, autosave state, negative/partial marking, and final scoring. Never trust client timers or client-computed scores. Require `Idempotency-Key` on submissions.
- Live AI classrooms ([docs/CLASSROOM_ARCHITECTURE.md](docs/CLASSROOM_ARCHITECTURE.md)) MUST run from validated structured `LessonArtifact` JSON controlled by a server-side state machine over WebSockets.

## 18. Multi-Tenant Isolation
- Scope all institutional records (`organizations`, `schools`, `branches`, `academic_years`, `classes`, `sections`, `enrollments`, institutional tests/analytics) by `tenant_id`.
- Enforce tenant checks in backend repositories/PostgreSQL RLS and verify with automated cross-tenant isolation tests.

## 19. Testing Requirements
- Follow the 9-tier strategy in [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md): Unit, Integration (real PG/Redis), API & AuthZ Matrix, Playwright E2E, AI Eval Regression, Security, Data Quality, Accessibility (WCAG 2.1 AA), and Load tests.
- Every task requires tests covering happy paths, error paths, authorization boundaries, and edge cases.

## 20. Documentation Requirements
- Keep the 25 architectural/product documents in `docs/` authoritative and synchronized with code, schema, APIs, and security controls.

## 21. Feature Completion Definition (12-Point Rule)
A feature is **NOT** complete until all 12 items pass: (1) UI, (2) API, (3) DB/migrations, (4) validation, (5) backend authorization, (6) error handling, (7) loading state, (8) empty state, (9) passing automated tests after final edit, (10) updated docs, (11) passing acceptance criteria, (12) zero fake/placeholder logic.

## 22. Prohibition Against Fake Functionality
Never ship fake buttons, hardcoded analytics pretending to be live metrics, simulated AI/DB responses in production paths, or silent mock fallbacks. Unimplemented phase items must be feature-flagged off or explicitly labeled `NOT_IMPLEMENTED` with their phase dependencies.

## 23. Prohibition Against Silently Removing Existing Functionality
Never delete, bypass, or rewrite working features, schemas, auth, or APIs without first inspecting them and documenting the reason, impact, migration strategy, and risks.

## 24. Prohibition Against Undocumented Architectural Changes
Any change to stack, database structure, module boundaries, security/privacy model, licensing, or cost model MUST be recorded in [docs/DECISION_LOG.md](docs/DECISION_LOG.md) before implementation.

## 25. Mandatory `IMPLEMENTATION_STATUS.md` Updates
Update [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) after every meaningful implementation task with current phase, completed/incomplete items, blockers, observed test counts, debt, and next tasks.

## 26. Mandatory `MASTER_FEATURE_CHECKLIST.md` Updates
Update [docs/MASTER_FEATURE_CHECKLIST.md](docs/MASTER_FEATURE_CHECKLIST.md) after every meaningful implementation task, marking granular columns (`UI`, `API`, `DB`, `Valid`, `Authz`, `Err/Load/Empty`, `Tests`, `Docs`) honestly.

## 27. Mandatory Test Verification Before Completion
Never declare any task or feature complete without running the relevant test suite(s) *after the final edit* and reporting only directly observed command results, counts, and scope.

## 28. Document Assumptions & Decisions
Record non-trivial assumptions and trade-offs explicitly in [docs/DECISION_LOG.md](docs/DECISION_LOG.md) and affected `docs/` specs. Ask the user before proceeding whenever a decision is genuinely blocking (legal, cost, data rights, or infra choices).

## 29. Inspect Existing Code Before Modifying
Before modifying any file or subsystem, inspect existing directory structure, dependencies, schema/migrations, auth, routes, tests, and data files. Never guess symbol names, columns, or behavior from memory.

## 30. Controlled Phased Implementation
Follow `DISCOVER → AUDIT → SPECIFY → DESIGN → PLAN → IMPLEMENT → TEST → REVIEW → DOCUMENT → RELEASE` across Phases 0–12 ([docs/ROADMAP.md](docs/ROADMAP.md)). Implement the smallest coherent slice per task; never attempt uncontrolled multi-phase coding dumps.
