# Go4Guru — Missing Features Inventory & Prioritized Batched Remediation Plan

> **Audit Date:** 2026-11-27  
> **Companion Reports:** [docs/REQUIREMENT_TRACEABILITY_AUDIT.md](REQUIREMENT_TRACEABILITY_AUDIT.md) · [docs/PRODUCTION_READINESS_AUDIT.md](PRODUCTION_READINESS_AUDIT.md)  
> **Execution Discipline:** **Do NOT start remediation until the user approves the batch(es).** After every approved batch, run full relevant tests and update `docs/MASTER_FEATURE_CHECKLIST.md` and `docs/IMPLEMENTATION_STATUS.md` truthfully.

---

## 1. Complete Inventory of Missing & Incomplete Capabilities

### A. Completely Unbuilt Features (`2. DESIGNED` / `NOT STARTED`)
1. **`F-006` — Rights-Aware Content Management System (CMS):**
   - Missing DB tables: `content_items`, `content_versions`, `content_translations`, `content_reviews`, `content_publications`.
   - Missing APIs: `/api/v1/content/*` CRUD, draft/review/publish state machine, translation linking, rights enforcement.
   - Missing UI: Editorial CMS Studio for `content_admin` and `academic_reviewer`.
2. **`F-040` — Mobile/PWA & Offline-Safe Scale Readiness:**
   - Missing Web App Manifest, Service Worker, offline asset caching.
   - Missing mobile camera capture with client-side image compression for Homework AI.
   - Missing IndexedDB offline flashcard/note/assessment-answer sync queue.
   - Missing `k6`/Locust 10k-concurrency load & stress test suite.

### B. Backend-Only Features Missing Frontend UI (`5. BACKEND ONLY`)
1. **`F-021` — AI Quality Evaluation & Review Queue:** Backend APIs (`/api/v1/ai/evals/run`, `/evals/runs`, `/review-queue`, `/review-queue/{id}/decision`) and `fetchAiReviewQueue` exist, but **zero UI pages** render them.
2. **`F-037` — AI/Voice Cost Telemetry & Unit Economics:** Backend `GET /api/v1/admin/ai-costs` and `fetchAdminAiCosts` exist, but **zero UI pages** render them.
3. **Partial Backend-Only Admin Surfaces:**
   - `F-007` Content Rights creation & legal approval UI (backend `/api/v1/content-rights/*` exists; `/admin` only reads counts).
   - `F-008` Verified PYQ tagging UI (`POST /api/v1/questions/{id}/verify-pyq` exists; no UI).
   - `F-019` Hybrid RAG Knowledge Documents ingestion/browsing UI (`/api/v1/ai/knowledge/documents` exists; no UI).
   - `F-039` Audit Log viewer & User Role Assignment UI (`GET /api/v1/admin/audit-logs`, `POST /api/v1/admin/users/roles` exist; no UI).

### C. Critical Security, Privacy & Child Safety Gaps
1. **Guardian Consent Bypass (`F-004`):** `parent_service.py:230` leaks `verification_code_preview` in API response and `parent/page.tsx:118-125` auto-fills it. Must deliver out-of-band and disable preview in non-dev environments.
2. **Zero PostgreSQL Row-Level Security (`F-003`):** `0` RLS policies across all 11 migrations (`0001`–`0011`).
3. **Plaintext MFA Secret (`F-001`):** `users.mfa_secret` stored unencrypted in DB; no MFA recovery codes; no Redis revoked-JWT blocklist on logout; no email verification, password reset, SSO (`auth_providers`), `devices` table, or breach screening.
4. **Child Safety & DPDP Governance (`F-038`):** Unconsented minors (`pending_parent_consent`) are not blocked from AI/homework/billing; missing `safety_incidents`, `moderation_queue`, `data_deletion_requests`, global Report/Get Help button + API, DSAR data export/deletion, retention purge jobs, minor notification quiet hours, and formal DPDP legal review.
5. **Upload Malware Scanning (`P0-06`/`F-029`):** No ClamAV/AV hook before storing homework/Excel uploads.
6. **SymPy DoS Guard (`F-020`):** No CPU/wall-clock subprocess timeout on SymPy expression parsing.

### D. Architecture, Scalability & Infrastructure Gaps
1. **Stub Background Worker (`P0-07`/`F-026`/`F-034`/`F-012`/`F-009`):** `apps/worker/src/go4guru_worker/main.py` only pings Redis. Must handle:
   - `outbox_events` consumption (remove inline drain from `GET /api/v1/analytics/student/overview`)
   - Expired assessment auto-submission reaper
   - Async Excel import parsing for large workbooks
   - Multi-channel notification delivery + minor quiet hours
   - 30-day content license expiry alerts & data-retention purges
2. **Process-Local WebSocket Manager (`F-022`):** `WS_MANAGER` in `classroom/service.py:86` cannot scale past 1 API instance; needs Redis Pub/Sub fanout.
3. **Local Filesystem Storage (`P0-06`/`F-009`/`F-024`/`F-029`):** `LocalPrivateStorage` must be replaced by S3/GCS/R2 private buckets with short-lived signed URLs.
4. **Vector Search Scaling (`F-019`):** `DOUBLE PRECISION[]` linear cosine scan must migrate to `pgvector` HNSW index before large corpus ingestion.
5. **Production Ops & DR (`P11-01`):** Missing production Dockerfiles, IaC, automated PG18 backups + WAL PITR + restore drill, Sentry/OpenTelemetry/Prometheus alerting, CI `pip-audit` + dependency upgrades, and operational runbooks.

### E. Incomplete Product Workflows & Data Coverage
1. **Student Dashboard (`F-030`):** `/dashboard/page.tsx` only shows Phase 1 stats; missing Study Plan, Due Flashcards, Homework Status, Weak Concepts, Mastery Summary, Exam Prep Hub, and Notifications.
2. **Global Notifications (`F-035`):** Notifications exist only inside `/adaptive`, missing `AppShell` header bell, `notification_preferences`, `notification_deliveries`, and email/push/SMS channels.
3. **Billing & Monetization (`F-036`):** Missing `usage_ledgers`, `transactions`, `invoices`, `refunds`, Razorpay/Stripe adapter + signed webhooks, B2C plans, and plan-tied AI/voice spend caps & kill-switches.
4. **Admin & Curriculum Authoring (`F-005`/`F-008`/`F-039`):** Hardcoded curriculum bootstrap form; numerical-only question form; missing `question_tags`, `feature_flags`, and `usage_events` + institutional/platform analytics endpoints; unhandled errors & stale state in `/admin/page.tsx`.
5. **AI Streaming & Live Provider QA (`F-017`/`F-018`/`F-024`/`F-025`/`F-029`):** No SSE streaming on AI tutor turns; no LLM Quiz Generator; zero live runs against real Gemini/OpenAI/Anthropic/Vision OCR/ElevenLabs keys; no native Indic language academic QA.
6. **Audited Curriculum & PYQ Dataset (`F-005`/`F-013`–`F-016`):** Only seed/sample syllabus chapters and PYQs exist; full audited Classes 6–12 NCERT/CBSE/JEE/NEET coverage has not been curated or verified.
7. **Live PG18 Integration Verification (Phases 6–10):** Alembic migrations `0007`–`0011` and `test_phase6..10_*_pg.py` have not been executed on a live PostgreSQL 18 host.

---

## 2. Prioritized Controlled Remediation Plan (8 Approval-Gated Batches)

> **Execution Protocol:** Each batch is a self-contained, testable slice. After each approved batch:
> 1. Run all affected unit, integration, Vitest, lint, and build checks.
> 2. Verify UI changes in a real headless browser.
> 3. Update `docs/MASTER_FEATURE_CHECKLIST.md`, `docs/IMPLEMENTATION_STATUS.md`, and `docs/DECISION_LOG.md` (if architectural).

| Batch | Name | Priority | Features Addressed | Scope & Key Deliverables | Exit / Acceptance Criteria |
| :---: | :--- | :---: | :--- | :--- | :--- |
| **Batch 1** | **Checklist Honesty, Admin Studio Wiring & UI/A11y Bug Fixes** | **P0 (Immediate)** | `F-007`, `F-008`, `F-009`, `F-019`, `F-021`, `F-035`, `F-037`, `F-039`, `F-013`, `F-003` | 1. Correct `docs/MASTER_FEATURE_CHECKLIST.md` & `IMPLEMENTATION_STATUS.md` to eliminate all over-claims.<br>2. Fix `/admin/page.tsx` unhandled `try/catch` + busy states + Excel commit `batch.status` refresh.<br>3. Add missing `<h1>` on `/exams` & `/institution` unauthenticated gates.<br>4. Wire **already-built** backend APIs into `/admin` Studio tabs: **AI Review Queue & Eval Runner (`F-021`)**, **AI/Voice Cost Telemetry (`F-037`)**, **Audit Logs & Role Assignment (`F-039`)**, **Content Rights Create/Approve (`F-007`)**, **PYQ Verification (`F-008`)**, and **Knowledge Docs Ingestion (`F-019`)**.<br>5. Add global **Notifications Bell** popover to `AppShell` (`F-035`). | Zero Backend-Only features left for `F-021`/`F-037`; Vitest + `compile_applet` + `lint_applet` + Playwright/Chromium check pass across all new tabs; checklist updated truthfully. |
| **Batch 2** | **PostgreSQL RLS & Live PG18 Verification (Phases 6–10)** | **P0 (Blocker)** | `P0-03`, `F-003`, `F-004`, `F-013`–`F-016`, `F-025`, `F-029`, `F-031`–`F-033`, `F-036` | 1. Create Alembic migration `0012_postgresql_rls_policies.py` enabling PostgreSQL RLS (`ENABLE ROW LEVEL SECURITY` + tenant policies via `current_setting('app.current_tenant_id', true)`) on all tenant-scoped tables.<br>2. Set session tenant GUC automatically in `core/deps.py` / DB session helper.<br>3. Wire PG18 + Redis service container in CI & run `alembic upgrade head` (`0001`–`0012`) plus full `pytest` suite (`test_phase1..10_*_pg.py`), including cross-tenant isolation tests. | All 12 migrations apply cleanly on PG18; `test_phase8_multitenant_pg.py` + RLS tests verify zero cross-tenant leakage at both app & DB layer; all Phase 6–10 PG18 suites pass. |
| **Batch 3** | **Durable Async Background Worker & Outbox Decoupling** | **P0 (Blocker)** | `P0-07`, `F-007`, `F-009`, `F-012`, `F-026`, `F-034`, `F-035`, `F-038` | 1. Upgrade `apps/worker` from Redis ping stub to a resilient async job runner with idempotency, retries, and dead-letter handling.<br>2. Move `process_outbox_learning_events` out of HTTP `GET /api/v1/analytics/student/overview` into continuous worker loop.<br>3. Add scheduled worker jobs: expired assessment auto-submit reaper, async Excel import parser, notification dispatcher (with minor quiet hours), 30-day license expiry alerts, and data-retention purges.<br>4. Add comprehensive worker unit & integration tests. | Zero synchronous outbox drains in HTTP GET handlers; expired attempts auto-submit deterministically; worker unit + integration tests pass. |
| **Batch 4** | **Auth Hardening, Child Safety & DPDP Technical Controls** | **P0 (Blocker)** | `F-001`, `F-004`, `F-020`, `F-038` | 1. **Fix `F-004` Consent Leak:** Remove `verification_code_preview` from non-dev API responses & UI auto-fill; route codes through out-of-band notification adapter.<br>2. **Enforce Minor Consent Gate:** Block `pending_parent_consent` minors from AI tutor, homework uploads, and billing until guardian consent is verified.<br>3. **Auth Hardening:** Encrypt `users.mfa_secret` (Fernet/KMS envelope), add Redis revoked-session blocklist checked in `core/deps.py`, add email verification, single-use hashed password reset tokens, MFA recovery codes, `devices` table, and password breach check.<br>4. **Safety & DPDP:** Add migration `0013` (`safety_incidents`, `moderation_queue`, `data_deletion_requests`), global `POST /api/v1/safety/report` + Report/Get Help button across student UI, `GET /users/me/data-export`, `POST /users/me/deletion-request`, and SymPy CPU timeout sandbox. | Consent bypass eliminated; minor gating verified by authz tests; encrypted MFA + Redis token revocation tested; DSAR & safety reporting functional end-to-end. |
| **Batch 5** | **Student Dashboard, Editorial CMS (`F-006`), Full Authoring & AI Streaming** | **P1 (High)** | `F-005`, `F-006`, `F-008`, `F-011`, `F-017`, `F-018`, `F-030`, `F-034`, `F-039` | 1. Enrich `/dashboard` with Today's Study Plan, Due Flashcards, Homework Status, Weak Concepts, Mastery Summary, and Exam Readiness.<br>2. Build `F-006` Rights-Aware CMS (`content_items`, `content_versions`, `content_translations`, `content_reviews`, `content_publications`, `/api/v1/content/*`, CMS UI).<br>3. Replace hardcoded curriculum bootstrap with full 11-level Curriculum CRUD UI; expand Admin Question Authoring to all canonical question types + `question_tags`.<br>4. Add `feature_flags` table/API/UI (`F-039`), `usage_events` + institutional/platform analytics (`F-034`), SSE streaming on AI Tutor turns (`F-017`/`F-018`), and verified LLM Quiz Generator (`F-011`). | `/dashboard` unifies student journey; `F-006` CMS passes all 12 completion points; SSE streaming & `feature_flags` verified with automated tests. |
| **Batch 6** | **Full Billing/Quotas, S3 Storage, Redis Pub/Sub WS & Security Patching** | **P1 (High)** | `P0-06`, `F-009`, `F-019`, `F-022`, `F-024`, `F-029`, `F-036`, `F-037` | 1. Complete `F-036`: `usage_ledgers`, `transactions`, `invoices`, `refunds`, Razorpay/Stripe payment adapter + signed webhook verification, B2C plans, and plan-tied AI/voice quota + spend kill-switches.<br>2. Replace `LocalPrivateStorage` with S3/GCS/R2 signed-URL adapter + ClamAV scan hook across Excel, Homework, and Voice.<br>3. Upgrade `WS_MANAGER` to Redis Pub/Sub for multi-instance live classrooms.<br>4. Migrate `ai/rag.py` to `pgvector` HNSW index.<br>5. Patch `bun audit` advisories (`next`, dev deps) and add `pip-audit` + `bun audit` gates to CI. | Multi-node WebSocket fanout verified; zero local disk uploads; signed webhook & AI spend kill-switch tests pass; clean dependency audit. |
| **Batch 7** | **Production Ops, Monitoring, DR, Live AI/Voice QA & Audited Dataset** | **P1 (Release Gate)** | `P11-01`, `F-005`, `F-013`–`F-016`, `F-017`, `F-021`, `F-024`, `F-025`, `F-029`, `F-038` | 1. Production multi-stage Dockerfiles (`api`, `web`, `worker`) + IaC manifests.<br>2. Automated PG18 backups + WAL PITR + documented restore drill.<br>3. OpenTelemetry + Prometheus + Sentry + alerting rules + operational runbooks.<br>4. Execute live vendor AI/OCR/ElevenLabs evaluations, prompt-injection red-team, and native Indic QA.<br>5. Curate & audit full Classes 6–12 syllabus & verified PYQ dataset; add `axe-core` Playwright E2E CI.<br>6. Obtain qualified legal counsel DPDP review sign-off. | All live vendor evals meet quality/safety thresholds; restore drill & observability verified; Playwright E2E + `axe-core` green; legal DPDP sign-off obtained. |
| **Batch 8** | **Phase 12 Mobile/PWA, Offline Sync & 10k Load Scale (`F-040`)** | **P2 (Scale)** | `F-040`, `F-012`, `F-027`, `F-029` | 1. PWA Web App Manifest + Service Worker.<br>2. Mobile camera capture with client-side image compression for Homework AI.<br>3. IndexedDB offline sync queue for flashcards, notes, and assessment answer retries.<br>4. `k6`/Locust 10k-concurrency load testing & DB/Redis SLO tuning. | Offline flashcards/answers sync cleanly on reconnect; `k6`/Locust passes target p95 latency & error-rate SLOs at 10k simulated users. |

---

## 3. Recommended Starting Point

**Recommended First Approval:** **Batch 1 (Checklist Honesty, Admin Studio Wiring & UI/A11y Bug Fixes)** — zero external infrastructure dependencies, immediately resolves the biggest documentation-vs-code honesty gaps (`F-021`, `F-037`, `F-007`, `F-008`, `F-019`, `F-039`, `F-035`), fixes real runtime bugs in `/admin`, and can be verified immediately in the workspace with Vitest, `compile_applet`, `lint_applet`, and headless Chromium before moving to **Batch 2 (PostgreSQL RLS & Live PG18 Verification)** and **Batch 3/4 (Async Worker & Child Safety/Auth Hardening)**.
