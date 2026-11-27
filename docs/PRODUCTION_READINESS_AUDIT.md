# Go4Guru — Complete Production Readiness Audit (33 Defect Categories)

> **Audit Date:** 2026-11-27  
> **Overall Release Verdict:** **NO-GO — NOT READY FOR PRODUCTION**  
> **Methodology:** Direct static & runtime forensic inspection of `apps/api/src`, `apps/web/src`, `apps/worker/src`, `apps/api/alembic/versions`, `packages/*`, `.github/workflows/ci.yml`, `docker-compose.yml`, and test suites. Zero assumptions taken from existing status docs without code verification.

---

## 1. Executive Release Verdict

| Risk Dimension | Verdict | Primary Blocker(s) |
| :--- | :---: | :--- |
| **Security & Child Safety** | **FAIL (CRITICAL)** | `verification_code_preview` returned in API & auto-filled in UI (`parent_service.py:230`, `parent/page.tsx:118`); zero PostgreSQL RLS policies; plaintext `users.mfa_secret`; no Redis JWT revocation blocklist; unconsented minors not actively gated; no DSAR/safety-report endpoints; no legal DPDP review. |
| **Architecture & Scalability** | **FAIL (CRITICAL)** | `apps/worker` is a Redis ping stub (`outbox_events` drained inline in HTTP GET); `WS_MANAGER` is process-local memory (breaks multi-node scaling); `LocalPrivateStorage` stores uploads/voice/Excel on local disk (not S3); zero `pgvector` HNSW index. |
| **Database & Verification** | **FAIL (CRITICAL)** | Alembic migrations `0007`–`0011` and PG18 integration/cross-tenant test suites (`test_phase6..10_*_pg.py`) have NOT been executed against a live PostgreSQL 18 host. |
| **AI, Voice & Data Quality** | **FAIL (HIGH)** | Zero live LLM/OCR/ElevenLabs evaluations run against real vendor keys; AI Review Queue & AI Cost Telemetry are Backend-Only (zero UI); Curriculum/Exam PYQ archives contain seed/sample records only, not audited Classes 6–12 coverage. |
| **Operations, CI/CD & DR** | **FAIL (CRITICAL)** | No production Dockerfiles or IaC; no automated PG18 backups/PITR/restore drills; no Sentry/OpenTelemetry/Prometheus alerting; no `k6`/Locust load tests; CI missing `pip-audit`/dependency scanning. |
| **Core Assessment Integrity & Hygiene** | **PASS (WITH CAVEATS)** | Zero client-side scoring or client-trusted timers; zero broken `<Link>` routes; zero `eval`/`exec`/raw f-string SQL; zero `window.alert`/`window.open`; 374 third-party ALLEN® PDFs remain strictly quarantined. |

---

## 2. Complete 33-Category Forensic Defect Audit

### 1. Fake Buttons
- **Status:** **PASS (Clean)**
- **Evidence:** Full grep across `apps/web/src/` for `onClick={() => {}}`, empty handlers, and dead buttons returned **0 matches**. Every rendered button invokes a real handler or navigation action.
- **Caveat (Functional Bug, not Fake):** Three real buttons in `apps/web/src/app/admin/page.tsx` (`Approve & Publish` at line 404, `Commit Valid Rows` at line 527, `Rollback Batch` at line 541) invoke real APIs but lack `try/catch` error handling and fail to update local `batch.status` on commit.
- **Severity:** Low (fixed in Batch 1).

### 2. Placeholder Functionality
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  1. `apps/worker/src/go4guru_worker/main.py` — Worker only pings Redis and sleeps; executes zero background jobs (`outbox_events`, expired assessment auto-submit, notifications, Excel imports, license expiry, retention purges).
  2. `apps/web/src/app/admin/page.tsx:121-150` — `handleBootstrapCurriculum` hardcodes a single demo syllabus path (`"2026-27"`, `"MATH"`, `"Class 10 Mathematics Foundation"`, `"CH-1"`, `"Linear Equations"`) instead of real 11-level curriculum CRUD.
  3. `apps/api/src/modules/identity/parent_service.py:230` & `apps/web/src/app/parent/page.tsx:118-125` — Dev-style `verification_code_preview` returned in API response and auto-filled in frontend instead of out-of-band email/SMS delivery.
- **Severity:** **Critical** (Worker stub & consent code preview), **High** (Admin curriculum bootstrap).
- **Remediation:** Batch 3 (Worker), Batch 4 (Guardian consent delivery), Batch 5 (Curriculum CRUD UI).

### 3. Mock Data in Production Paths
- **Status:** **DEFECTS FOUND (Fallback / Seed Boundaries)**
- **Evidence:**
  - `apps/api/src/modules/ai/provider.py` — `GroundedDeterministicFallbackProvider` activates whenever live vendor API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are unset (`ADR-009`). While explicitly labeled and useful for deterministic tests, production deployment MUST fail-closed or alert loudly if unintended fallback occurs.
  - `apps/api/src/modules/assessment/exam_service.py` & `apps/api/src/modules/curriculum/multilingual_service.py` — Seed/sample exam blueprints, formula sheets, and glossary records exist for demo/testing, not full audited national datasets.
  - Positive check: Zero hardcoded fake live analytics numbers in UI dashboards (all dashboard/analytics/teacher/mentor/parent/institution metrics query live API endpoints).
- **Severity:** High (requires production startup check for live AI/OCR/voice keys + honest dataset coverage banner).
- **Remediation:** Batch 7 (Live provider verification & production provider health guard).

### 4. Hardcoded Values
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  1. `apps/web/src/app/admin/page.tsx:121-150` — Hardcoded curriculum bootstrap strings (`"2026-27"`, `"MATH"`, `"Linear Equations"`).
  2. `apps/web/src/app/admin/page.tsx:167-187` — Hardcoded `question_type: "numerical"` in admin question creation form.
  3. `apps/api/src/modules/ai/provider.py` / `classroom/voice/provider.py` — Rate-card fallback unit costs embedded in code when DB `provider_rate_cards` row is absent (needs admin CRUD to keep rates synchronized with vendor pricing).
- **Severity:** Medium.
- **Remediation:** Batch 5 (Full Curriculum & Multi-Type Question Authoring UI), Batch 6 (Rate-card CRUD).

### 5. Missing APIs
- **Status:** **DEFECTS FOUND**
- **Evidence:** Compared against `docs/API_SPECIFICATION.md` and `docs/PRODUCT_REQUIREMENTS_DOCUMENT.md`:
  - `F-001`: Email/OTP verification, forgot/reset password, MFA recovery codes, SSO OAuth callbacks.
  - `F-006`: Entire `/api/v1/content/*` CMS route group (`items`, `versions`, `reviews`, `publish`, `translations`).
  - `F-034`: `/api/v1/analytics/institution/overview`, `/api/v1/analytics/platform/learning-metrics`.
  - `F-035`: `/api/v1/notifications/preferences` (including minor quiet hours).
  - `F-036`: `/api/v1/billing/checkout`, `/webhooks/{provider}`, `/invoices`, `/refunds`, `/usage-ledgers`.
  - `F-038`: `/api/v1/safety/report`, `/api/v1/admin/moderation-queue`, `/api/v1/users/me/data-export`, `/api/v1/users/me/deletion-request`.
  - `F-039`: `/api/v1/admin/feature-flags/*`, MFA-gated read-only support impersonation.
- **Severity:** High (Critical for `F-038` DPDP/Safety & `F-036` Billing).
- **Remediation:** Batches 4, 5, and 6.

### 6. Missing Database Persistence
- **Status:** **DEFECTS FOUND**
- **Evidence:** 96 tables exist across Alembic `0001`–`0011`, but the following PRD tables are **absent**:
  - `F-001`: `auth_providers`, `devices`, `password_reset_tokens`.
  - `F-006`: `content_items`, `content_versions`, `content_translations`, `content_reviews`, `content_publications`.
  - `F-008`: `question_tags`.
  - `F-034`: `usage_events`.
  - `F-035`: `notification_preferences`, `notification_deliveries`.
  - `F-036`: `usage_ledgers`, `transactions`, `invoices`, `refunds`.
  - `F-038`: `safety_incidents`, `moderation_queue`, `data_deletion_requests`.
  - `F-039`: `feature_flags`.
  - Ephemeral memory/disk state that must be externalized: `WS_MANAGER` connections (in-memory), `LocalPrivateStorage` files (local disk).
- **Severity:** High.
- **Remediation:** Batches 4, 5, and 6.

### 7. Incomplete Workflows
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  1. **AI Evaluation & Review Queue (`F-021`) & AI Cost Telemetry (`F-037`):** Fully built in backend + `api-client`, but completely unwired in frontend (0 UI screens).
  2. **Content Rights (`F-007`) & Hybrid RAG Knowledge Docs (`F-019`):** Backend CRUD/approval endpoints exist, but `/admin` has no UI to create/approve licenses or ingest/manage knowledge documents.
  3. **Excel Import UI (`F-009`):** `admin/page.tsx:519-542` commits rows without updating `batch.status`, breaking the visual transition to the `Rollback Batch` button.
  4. **Student Dashboard (`F-030`):** Only displays Phase 1 core metrics; disconnected from Study Plans, Due Flashcards, Homework, Weak Concepts, Exam Readiness, and Notifications.
  5. **Outbox-Driven Adaptive/Analytics Loop (`F-026`/`F-034`):** Depends on synchronous drain inside `GET /analytics/student/overview` (`analytics/router.py:52`) instead of async worker.
- **Severity:** High.
- **Remediation:** Batch 1 (Admin Studio wiring & UI bug fixes), Batch 3 (Async worker), Batch 5 (Dashboard enrichment).

### 8. Broken Navigation
- **Status:** **PASS (Clean)**
- **Evidence:** Audited all 26 `apps/web/src/app/**/page.tsx` routes against every `<Link href="...">` in `apps/web/src/components/app-shell.tsx` and all page components. Zero broken links or 404 internal targets exist.
- **Minor UX Gap:** Notifications inbox is buried inside `/adaptive` rather than accessible from `AppShell` header (addressed in Batch 1).
- **Severity:** Low.

### 9. Missing Authorization
- **Status:** **DEFECTS FOUND (Minor Consent & Token Revocation)**
- **Evidence:**
  - Positive: All backend routes enforce deny-by-default `require_authenticated` / `require_roles` dependencies; zero unprotected admin/teacher/mentor/parent/institution endpoints found.
  - **Gap 1 (`F-038`/`F-004`):** Minors with `status='pending_parent_consent'` or unverified guardian consent are NOT actively blocked from creating AI tutor sessions, uploading homework, or initiating billing actions.
  - **Gap 2 (`F-001`):** Logout revokes the refresh token in DB, but issued short-lived access JWTs (up to 15 min) remain valid until expiry because there is no Redis `jti`/session revocation blocklist checked in `core/deps.py`.
- **Severity:** **High**.
- **Remediation:** Batch 4 (Active minor consent enforcement + Redis JWT session blocklist).

### 10. Missing Tenant Isolation
- **Status:** **CRITICAL DEFECT**
- **Evidence:**
  - Application-layer `tenant_id` filtering exists in `apps/api/src/modules/organization/service.py` and `billing/service.py`, **HOWEVER**:
  - Grep across `apps/api/alembic/versions/*.py` for `ENABLE ROW LEVEL SECURITY` / `CREATE POLICY` returned **0 matches**. Zero PostgreSQL Row-Level Security (RLS) policies exist to prevent cross-tenant leakage on future developer query mistakes.
  - `apps/api/tests/integration/test_phase8_multitenant_pg.py` has **never been executed** against a live PostgreSQL 18 database.
- **Severity:** **Critical**.
- **Remediation:** Batch 2 (Add PostgreSQL RLS migration + session tenant GUC + run live PG18 cross-tenant isolation tests).

### 11. Incorrect Permissions
- **Status:** **DEFECT FOUND (Guardian Consent Bypass)**
- **Evidence:**
  - `apps/api/src/modules/identity/parent_service.py:230` returns `verification_code_preview=code` in the `POST /api/v1/parent/links/request` response, and `apps/web/src/app/parent/page.tsx:118-125` displays and auto-fills that code directly into the parent's verification input. Any authenticated parent account who knows a student's email can immediately self-verify a guardian link without out-of-band confirmation!
  - Positive check: Parent access to student `ai_sessions`/`ai_messages` is hard-blocked (`403`), and `academic_reviewer`/`content_admin`/`school_admin`/`platform_admin` MFA guards work properly.
- **Severity:** **Critical**.
- **Remediation:** Batch 4 (Remove `verification_code_preview` from API in non-dev environments and implement out-of-band student/guardian verification delivery).

### 12. Missing Validation
- **Status:** **MINOR DEFECTS FOUND**
- **Evidence:**
  - Positive: FastAPI Pydantic v2 models validate nearly all request/response payloads; magic-byte/EXIF/size validation exists for homework and Excel uploads; whiteboard opcodes validated strictly by schema.
  - Gaps:
    1. `ai/verifier.py` — SymPy expression parsing lacks a strict CPU/wall-clock subprocess timeout against pathological algebraic expansion payloads.
    2. `identity/service.py` — Password policy checks length/complexity but lacks compromised-password breach screening (`F-001`).
    3. `admin/page.tsx` — Client-side form validation on question creation is minimal (relies on backend errors).
- **Severity:** Medium.
- **Remediation:** Batch 4 (SymPy timeout sandbox & password breach check).

### 13. Missing Error Handling
- **Status:** **MINOR DEFECTS FOUND**
- **Evidence:**
  - Positive: 23 of 24 interactive pages wrap fetches/mutations in `try/catch` and render `ErrorBanner`.
  - Defect: `apps/web/src/app/admin/page.tsx` has unhandled async mutations on:
    - Line 404: `Approve & Publish` button (`onClick` calls `reviewQuestion` without `try/catch` or `setError`).
    - Line 527: `Commit Valid Rows` button (`onClick` calls `commitExcelImport` without `try/catch` or `batch` state update).
    - Line 541: `Rollback Batch` button (`onClick` calls `rollbackExcelImport` without `try/catch` or `batch` state update).
- **Severity:** Medium.
- **Remediation:** Batch 1 (Wrap all 3 handlers in `try/catch`, show `ErrorBanner` on failure, refresh `batch` state on commit/rollback).

### 14. Missing Loading States
- **Status:** **PASS (Minor Enhancements)**
- **Evidence:** All 24 authenticated/interactive pages import and render `LoadingCard` or button disabled/busy indicators during initial loads and submissions.
- **Minor Gap:** In `admin/page.tsx`, `Approve & Publish`, `Commit Valid Rows`, and `Rollback Batch` do not toggle a per-action loading indicator while the request is in flight (double-click risk).
- **Severity:** Low.
- **Remediation:** Batch 1 (Add `busyAction` state on those 3 admin buttons).

### 15. Missing Empty States
- **Status:** **PASS (Clean)**
- **Evidence:** Audited all 24 interactive pages—every collection view uses `EmptyState` or an explicit domain empty-state message when zero records exist.
- **Severity:** None.

### 16. Inaccessible Components
- **Status:** **MINOR DEFECTS FOUND**
- **Evidence:**
  - Positive: Skip-to-content link, landmark regions, focus rings, keyboard navigation, KaTeX math markup, and whiteboard `aria_summary` are present; Phase 11 live headless Chromium check confirmed clean structure on primary routes.
  - Defects:
    1. `apps/web/src/app/exams/page.tsx` & `apps/web/src/app/institution/page.tsx` — Unauthenticated sign-in gate cards omit an `<h1>` heading (WCAG 2.1 AA heading hierarchy violation on first load before login).
    2. Automated `axe-core` WCAG 2.1 AA accessibility regression suite is not yet wired into CI across all 26 routes.
- **Severity:** Medium.
- **Remediation:** Batch 1 (Add `<h1>` on `/exams` & `/institution` auth gates), Batch 7 (Add automated `axe-core` Playwright audit in CI).

### 17. Unresponsive Layouts
- **Status:** **PASS (Minor Mobile Polish Needed)**
- **Evidence:** Tailwind responsive grid/flex utilities (`sm:`, `md:`, `lg:`) are used across `AppShell` and all 26 routes; Phase 11 Chromium check verified desktop (`1440×900`) and mobile (`390×844`) layouts without horizontal overflow on inspected routes.
- **Gap:** Wide multi-column admin/analytics/teacher tables should be audited at `360px` width under full live data to verify horizontal scroll wrappers (`overflow-x-auto`) on every table.
- **Severity:** Low.
- **Remediation:** Batch 1 / Batch 8 mobile QA sweep.

### 18. AI Features Not Genuinely Integrated
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  - Real HTTP adapters exist for Gemini, OpenAI, and Anthropic (`apps/api/src/modules/ai/provider.py`), and the 16-module orchestrator (`orchestrator.py`) is genuinely wired to Hybrid RAG, SymPy Verifier, PII Scrubber, and Safety Filter.
  - **Gaps:**
    1. Without vendor API keys configured in the environment, requests silently execute `GroundedDeterministicFallbackProvider` (`ADR-009`) — live vendor LLM calls have **never been executed or verified end-to-end**.
    2. `POST /api/v1/ai/sessions/{id}/turns` returns a single JSON blob instead of SSE token streaming.
    3. `QuizGenerator` (LLM mode), `WhiteboardPlanner` (LLM generation), and `RevisionPlanner` (LLM narrative) operate as deterministic templates rather than live LLM-integrated modules.
    4. Homework Vision OCR (`homework/ocr.py`) has a live provider adapter interface, but has never been verified against real handwritten image/PDF inputs via Gemini Vision/Google Cloud Vision.
- **Severity:** High.
- **Remediation:** Batch 5 (SSE streaming + LLM Quiz Generator), Batch 7 (Live vendor LLM & Vision OCR integration verification).

### 19. AI Features Without Evaluation
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  - Golden evaluation suite (`apps/api/tests/evals/test_ai_golden_eval_suite.py`) and `ai_eval_runs`/`ai_review_queue` tables exist, **HOWEVER**:
    1. Evals have only ever been run against `GroundedDeterministicFallbackProvider`, never against live Gemini/OpenAI/Anthropic models.
    2. `F-021` (AI Review Queue & Eval Runner) has **zero frontend UI**, so `academic_reviewer` cannot inspect flagged outputs or trigger evaluation runs.
    3. No automated prompt-injection red-team benchmark against live LLMs has been executed.
- **Severity:** **High**.
- **Remediation:** Batch 1 (Wire AI Review Queue & Eval Runner UI in `/admin`), Batch 7 (Execute live LLM golden eval + prompt-injection red-team suite).

### 20. Voice Features Without Real Integration
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  - `VoiceProviderInterface` and `ElevenLabsVoiceProvider` (`apps/api/src/modules/classroom/voice/provider.py`) contain real HTTP client code and graceful subtitle fallback, **HOWEVER**:
    1. Live ElevenLabs TTS & STT calls have **never been executed** with a real `ELEVENLABS_API_KEY`.
    2. Synthesized audio assets are cached via `LocalPrivateStorage` (`provider.py:140`) on local disk rather than private S3/GCS/R2 signed URLs.
    3. Voice character/minute budget caps per plan are not enforced before synthesizing audio.
- **Severity:** High.
- **Remediation:** Batch 6 (S3 audio cache + quota caps), Batch 7 (Live ElevenLabs TTS/STT verification & Indic pronunciation QA).

### 21. Whiteboard Features Without Persistence
- **Status:** **PASS (Core Persistence Works; Minor Export Gaps)**
- **Evidence:** `apps/api/src/modules/classroom/service.py` persists every validated 12-opcode `WhiteboardAction` to append-only `whiteboard_events` and periodic `whiteboard_snapshots` tables (`0005`), enabling replay and resume.
- **Minor Gap:** `0005` persistence works on single node; multi-node live broadcast needs Redis Pub/Sub (`WS_MANAGER`), and board PNG/JSON export is not yet built.
- **Severity:** Medium (scaling via Redis Pub/Sub in Batch 6).

### 22. Assessments With Client-Only Scoring/Timers
- **Status:** **PASS (Verified Server-Authoritative)**
- **Evidence:** Inspected `apps/web/src/app/assessments/[attemptId]/page.tsx` and `apps/api/src/modules/assessment/service.py`. Server controls UTC `started_at`/`expires_at`, strips `correct_answer_jsonb`/`is_correct`/solutions prior to submission, requires `Idempotency-Key` on submit, and computes all scores/negative/partial marking strictly server-side. Client countdown is display-only synchronized from server `remaining_seconds`.
- **Operational Gap:** Expired unsubmitted attempts are not automatically finalized in the background because `apps/worker` is a stub (remediated in Batch 3).
- **Severity:** Medium (background auto-submit reaper needed in Batch 3).

### 23. Question-Bank Data Quality Problems
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  1. Only seed/sample questions exist in fixtures—there is no audited, production-sized Classes 6–12 CBSE/JEE/NEET question bank yet.
  2. `question_tags` table from `docs/QUESTION_BANK_SCHEMA.md` is missing from Alembic migrations.
  3. `/admin/page.tsx:167-187` restricts manual question authoring to `"numerical"` only—authors cannot create MCQ, multi-correct, assertion-reason, matrix-match, or subjective questions with hints/solutions in the UI.
- **Severity:** High.
- **Remediation:** Batch 5 (Multi-format Question Authoring UI + `question_tags`), Batch 7 (Audited question bank curation).

### 24. PYQ Provenance Problems
- **Status:** **PASS ON CODE GUARDRAILS / GAP ON UI & DATASET**
- **Evidence:**
  - Positive: Backend strictly enforces `is_pyq=true` ONLY when `verification_status='verified'`, `exam_name`, `exam_year`, and `verified_by` are present (`question_bank/service.py`, `assessment/exam_service.py`). Zero fabricated PYQ labels exist in code.
  - Gaps:
    1. `/admin/page.tsx` has **no UI** to invoke `POST /api/v1/questions/{id}/verify-pyq` with provenance metadata (`exam_name`, `exam_year`, `session`, `shift`, `paper_code`, `source_url`).
    2. Audited multi-year verified PYQ archive has not been curated yet.
- **Severity:** Medium (UI in Batch 1; dataset curation in Batch 7).

### 25. Missing Curriculum Mappings
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  - Database supports the full 11-level versioned curriculum (`0002`) and exam syllabus mappings (`0010`), **HOWEVER**:
    1. Actual populated syllabus coverage is seed/demo-scale (not complete audited Classes 6–12 NCERT + JEE Main + JEE Advanced + NEET chapter/topic/concept/LO/prerequisite mappings).
    2. `/admin/page.tsx` has only a hardcoded single-chapter bootstrap button (`handleBootstrapCurriculum`), lacking full 11-level curriculum CRUD/mapping tools.
- **Severity:** High.
- **Remediation:** Batch 5 (Full 11-level Curriculum Admin UI), Batch 7 (Audited syllabus curation).

### 26. Content Licensing Concerns
- **Status:** **PASS ON QUARANTINE / OPERATIONAL GAPS REMAIN**
- **Evidence:**
  - Positive: The 374 third-party ALLEN® PDFs remain **100% quarantined** (zero third-party PDFs in repo, storage, or RAG). Backend rejects quarantined sources (`QUARANTINED_SOURCE_FORBIDDEN`) and filters RAG strictly by `status='PUBLISHED'` & `embedding_allowed=true`.
  - Gaps:
    1. Zero UI in `/admin` to manage `content_sources` / `content_licenses` or perform legal approval reviews (`F-007`).
    2. No automated 30-day license expiry alerting job in `apps/worker`.
    3. `F-006` CMS does not exist yet to govern authored textbook/lesson content rights end-to-end.
- **Severity:** High.
- **Remediation:** Batch 1 (Content Rights UI), Batch 3 (Expiry alert job), Batch 5 (`F-006` CMS).

### 27. Privacy Issues
- **Status:** **CRITICAL DEFECTS FOUND**
- **Evidence:**
  1. `users.mfa_secret` stored unencrypted in PostgreSQL (`apps/api/src/modules/identity/models.py:26`).
  2. Missing DSAR endpoints & tables (`GET /api/v1/users/me/data-export`, `POST /api/v1/users/me/deletion-request`, `data_deletion_requests`).
  3. No automated data-retention purge worker jobs for expired homework uploads, inactive sessions, or deleted accounts.
  4. No formal legal DPDP Act counsel review completed (must NOT claim DPDP legal compliance).
  - Positive: PII scrubber strips student identifiers before external AI/OCR/voice calls; structured logger redacts auth tokens/passwords/emails; parent access to raw AI chat returns `403`.
- **Severity:** **Critical**.
- **Remediation:** Batch 4 (Encrypt `mfa_secret`, add DSAR export/deletion), Batch 3 (Retention purge jobs), Batch 7 (Legal counsel DPDP review).

### 28. Child Safety Issues
- **Status:** **CRITICAL DEFECTS FOUND**
- **Evidence:**
  1. **Guardian Consent Bypass (`F-004`):** `parent_service.py:230` returns `verification_code_preview=code` in the HTTP response and `parent/page.tsx:118-125` auto-fills it in the UI!
  2. **Unconsented Minors Not Blocked:** Minor accounts without verified guardian consent are not blocked from accessing AI tutor, homework upload, or billing endpoints.
  3. **Missing Safety Reporting & Moderation Queue:** `safety_incidents` and `moderation_queue` tables and global `POST /api/v1/safety/report` + persistent Report/Get Help button across all student screens are absent (only AI message flag exists in `/tutor`).
  4. **Missing Minor Quiet Hours:** `F-035` lacks quiet-hour suppression for late-night notifications to minors.
  - Positive: Self-harm/crisis helpline redirect in `ai/safety.py` works and is unit-tested; anti-spoiler guard defaults `true`; parent raw AI chat `403` works.
- **Severity:** **Critical**.
- **Remediation:** Batch 4 (Fix consent preview leak, enforce minor consent gate, build safety reporting + moderation queue), Batch 3 (Minor quiet hours).

### 29. Performance Issues
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  1. **Inline Outbox Drain on HTTP GET:** `apps/api/src/modules/analytics/router.py:52` runs `await process_outbox_learning_events(db, limit=100)` synchronously inside `GET /api/v1/analytics/student/overview`, adding write contention and latency spikes to read traffic.
  2. **Synchronous Excel Import Parsing:** `question_bank/service.py` parses/validates workbooks synchronously inside FastAPI HTTP requests (timeouts & worker starvation on multi-thousand-row files).
  3. **Linear-Scan Vector Search:** `ai/rag.py` stores embeddings as `DOUBLE PRECISION[]` (`ADR-009`) rather than `pgvector` HNSW ANN indexes—latency will degrade linearly above ~50k chunks.
  4. **Zero Load Testing:** No latency benchmarks (`p50`/`p95`/`p99`) or DB `EXPLAIN ANALYZE` query plans have been run under realistic concurrency.
- **Severity:** **High**.
- **Remediation:** Batch 3 (Move outbox & Excel import to `apps/worker`), Batch 6 (`pgvector` HNSW migration), Batch 8 (`k6`/Locust load benchmarks).

### 30. Scalability Issues
- **Status:** **CRITICAL DEFECTS FOUND**
- **Evidence:**
  1. **Process-Local WebSockets:** `WS_MANAGER = ClassroomConnectionManager()` (`classroom/service.py:86`) stores sockets in Python process memory—horizontally scaling FastAPI beyond 1 replica breaks live classroom broadcast/reconnection.
  2. **Local Disk Storage:** `LocalPrivateStorage` (`core/storage.py:11`) is used by Excel imports (`question_bank/service.py:634`), Homework uploads (`homework/service.py:380,640`), and Voice audio cache (`classroom/voice/provider.py:140`)—cannot survive ephemeral container restarts or multi-node clusters.
  3. **Stub Worker:** `apps/worker` cannot offload any background compute.
- **Severity:** **Critical**.
- **Remediation:** Batch 3 (Async worker), Batch 6 (Redis Pub/Sub `WS_MANAGER` + private S3/GCS/R2 object storage).

### 31. Cost Risks
- **Status:** **HIGH RISK**
- **Evidence:**
  1. **No Automated Spend Caps / Kill-Switches:** `ai_cost_events` and `voice_usage_logs` record usage, but there is no hard daily/monthly tenant or global AI/voice spend cap that automatically throttles or degrades to deterministic/caption fallback when exceeded.
  2. **No Cost Visibility UI:** `F-037` (`GET /api/v1/admin/ai-costs`) is Backend-Only—admins cannot monitor live token/voice burn in `/admin`.
  3. **No Plan-Tied AI/Voice Quotas:** `F-036` billing checks seat/teacher/branch counts only, not per-student AI turn or ElevenLabs character allowances.
- **Severity:** **High**.
- **Remediation:** Batch 1 (AI Cost Telemetry UI in `/admin`), Batch 6 (Automated AI/voice quotas & spend kill-switches).

### 32. Missing Tests
- **Status:** **CRITICAL DEFECTS FOUND**
- **Evidence:**
  1. **Unexecuted PG18 Integration Tests (Phases 6–10):** `test_phase6_homework_pg.py`, `test_phase7_educator_parent_pg.py`, `test_phase8_multitenant_pg.py`, `test_phase9_exam_prep_pg.py`, and `test_phase10_multilingual_pg.py` exist in code but have **NOT** been executed against a live PostgreSQL 18 + Redis instance (nor have migrations `0007`–`0011`).
  2. **Zero Worker Tests:** `apps/worker` has no automated tests.
  3. **Zero Live AI/OCR/Voice Eval Tests:** Golden evals have only run against `GroundedDeterministicFallbackProvider`.
  4. **Zero Playwright Full-Stack E2E & Accessibility (`axe-core`) CI Tests:** Only manual headless browser smoke checks were run against the dev web server.
  5. **Zero Load/Stress (`k6`/Locust) & Security Penetration Tests.**
  6. **Missing Web Dependency Audit & Python `pip-audit` in CI:** Phase 11 `bun audit` surfaced known transitive advisories (e.g., `next`, `vitest`/`esbuild` dev deps) that need scheduled patching and CI gating.
- **Severity:** **Critical**.
- **Remediation:** Batch 2 (Live PG18 + RLS pytest in CI), Batch 3 (Worker tests), Batch 6 (Dependency patching + `pip-audit`), Batch 7 (Playwright E2E + `axe-core` + live AI evals), Batch 8 (`k6` load tests).

### 33. Missing Documentation (and Documentation Drift)
- **Status:** **DEFECTS FOUND**
- **Evidence:**
  1. **`docs/MASTER_FEATURE_CHECKLIST.md` Over-Claims:** Marks 23 features `COMPLETED`, whereas 21 of them fail the 12-Point Rule (including `F-021` & `F-037` which have zero frontend UI!).
  2. **Missing Operational Runbooks:** No tested Backup & WAL PITR Restore Runbook, Incident Response / Data Breach Runbook, Secret Rotation Runbook, or Production Deployment Architecture Guide (IaC/Kubernetes/Cloud Run topology).
  3. **ADR Updates Needed:** Document `parent_service` verification delivery architecture, Redis Pub/Sub WS fanout, S3 storage adapter, and `pgvector` HNSW rollout in `docs/DECISION_LOG.md` when implemented.
- **Severity:** High.
- **Remediation:** Batch 1 (Immediately correct `MASTER_FEATURE_CHECKLIST.md` & `IMPLEMENTATION_STATUS.md` to match forensic truth), Batch 7 (Write & test operational/DR runbooks).

---

## 3. Summary Count of Production Audit Findings

| Severity | Count | Key Themes |
| :--- | :---: | :--- |
| **Critical (Release Blockers)** | **9** | Guardian consent code leak (`verification_code_preview`), zero PostgreSQL RLS, unexecuted PG18 migrations/tests (`0007`–`0011`), stub `apps/worker` + inline HTTP outbox drain, in-memory `WS_MANAGER`, `LocalPrivateStorage` on disk, unconsented minor gating/DSAR/DPDP legal review, no prod Dockerfiles/backups/monitoring/DR. |
| **High** | **13** | Plaintext `mfa_secret`, no Redis JWT revocation blocklist, Backend-Only `F-021`/`F-037` & unwired `F-007`/`F-019`/`F-039` admin UIs, unbuilt `F-006` CMS, incomplete `F-036` billing/payments/AI spend kill-switches, unenriched `/dashboard`, no SSE AI streaming, live LLM/OCR/ElevenLabs evals unexecuted, audited syllabus/PYQ dataset curation, `MASTER_FEATURE_CHECKLIST.md` over-claims. |
| **Medium** | **7** | Admin `try/catch` & Excel commit state bug, `/exams` & `/institution` signed-out `<h1>`, SymPy CPU timeout sandbox, password breach check, global `AppShell` notification bell + minor quiet hours, `pgvector` HNSW index, `F-040` PWA/offline/load suite. |
| **Low** | **4** | Per-action loading states on 3 admin buttons, `/practice` & `/notes` Vitest coverage, whiteboard PNG/JSON export, `360px` wide-table polish. |
