# Phase 1 Implementation Plan — Core Learning Platform

> **Scope:** Implements Phase 1 Core Learning Platform features (`F-001`, `F-002`, `F-005`, `F-006`/`F-007` foundation, `F-008`, `F-009`, `F-010`, `F-030` core, `F-038`/`F-039` baseline audit/safety) on top of the verified Phase 0 foundation.  
> **Gate:** Phase 2 does NOT start until all Phase 1 tasks, unit tests, real PostgreSQL 18 integration tests, API/RBAC matrix tests, and Playwright E2E tests pass and docs/checklists are updated.

---

## 1. Environment & Data Audit Inputs (Verified Before Coding)

1. **Workspace & Sibling Excel/CSV Audit:**
   - Re-verified `d:\go4guru` and sibling `D:\class-*`: **0 `.xlsx`, `.xls`, or `.csv` files exist**.
   - Therefore, Phase 1 **does not hardcode workbook sheet names or column headers**. The Excel/CSV pipeline inspects uploaded `.xlsx` (`openpyxl`) and `.csv` sheets dynamically, stages raw rows into `import_staging_rows`, and requires explicit Content Admin column mapping before validation/commit.
   - All 374 external ALLEN® PDFs in `D:\class-*` remain strictly quarantined (`THIRD_PARTY_QUARANTINED`).
2. **Non-Fabrication Rule:**
   - Alembic migrations seed ONLY structural reference metadata (`roles`, `permissions`, `role_permissions`, `grades 6..12`, `exam_tracks`, and default `ORIGINAL_PLATFORM` license option).
   - No fabricated NCERT full syllabi or unverified PYQs are auto-injected as official content; curriculum nodes and questions come from authenticated admin creation, schema-adaptive Excel/CSV imports, or explicit clearly labeled development/demo seed CLI utilities (`source_category = 'original_platform'`, `is_pyq = false`).
3. **Database & Runtime:**
   - Real PostgreSQL 18.3 persistence (`asyncpg` + SQLAlchemy 2.0 async + Alembic migrations).
   - Integration and Playwright E2E suites run against a real isolated PostgreSQL 18.3 cluster (`initdb`/`pg_ctl` on an isolated test port when `DATABASE_URL` isn't pre-provisioned locally, or `pgvector/pgvector:pg18` in CI).

---

## 2. Incremental Dependency Graph & Work Breakdown

```text
Workstream 1A: Shared Auth Context, Audit Helper & Phase 1 Alembic Schema (0002_phase1_core.py)
   ├── Workstream 1B: Identity, Auth, MFA, RBAC & Profiles (`identity`)
   │       │
   │       ├── Workstream 1C: Content Rights & 11-Level Versioned Curriculum (`content` rights + `curriculum`)
   │       │       │
   │       │       └── Workstream 1D: Canonical Question Bank, Search, Filters & Excel/CSV Importer (`question_bank`)
   │       │               │
   │       │               └── Workstream 1E: Practice Engine, Attempts, Solutions, Hints, Notes, Bookmarks & Core Dashboard (`assessment` practice subset + `learning`)
   │       │
   └── Workstream 1F: Next.js Web UI Workspaces (Auth/Onboarding, Curriculum Explorer, Practice+Notes/Bookmarks, Admin Curriculum/Question/Excel Import Studio, Student Core Dashboard)
           │
           └── Workstream 1G: Verification Gate (Unit + Real PG18 Integration + API/RBAC Matrix + Security/XSS/PYQ/Formula + Playwright E2E + Status/Checklist Docs)
```

---

## 3. Detailed Task Breakdown & Acceptance Criteria

### 1A. Core Database Schema & Module Boundary Configuration
- **Tasks:**
  1. Refine `apps/api/pyproject.toml` `import-linter` contract so cross-module communication is allowed ONLY via `src.modules.<domain>.public` and sibling internal imports (`models`, `repository`, `service`, `router`, `schemas`) are forbidden.
  2. Add Alembic migration `0002_phase1_core.py` creating Phase 1 tables with explicit FKs, `CHECK` constraints, `timestamptz`, and indexes:
     - Identity & RBAC: `users`, `user_profiles`, `roles`, `permissions`, `role_permissions`, `user_roles`, `sessions`, `student_profiles`.
     - Curriculum: `boards`, `academic_sessions`, `curriculum_versions`, `grades`, `subjects`, `books`, `chapters`, `sections`, `topics`, `concepts`, `learning_objectives`, `concept_prerequisites`, `exam_tracks`, `exam_concept_mappings`.
     - Content Rights: `content_sources`, `content_licenses`.
     - Question Bank & Import Staging: `questions`, `question_versions`, `question_options`, `question_solutions`, `question_hints`, `question_provenance`, `question_reviews`, `import_batches`, `import_staging_rows`.
     - Practice & Notes: `practice_sessions`, `question_attempts`, `student_notes`, `saved_questions`.
  3. Seed idempotent structural RBAC defaults (`8` roles, canonical Phase 1 permissions, `Class 6..12` grades, `exam_tracks`) in migration/bootstrap helper.
- **Dependencies:** Phase 0 `0001_phase0_baseline.py`.
- **Gate:** `alembic upgrade head` & `downgrade`/`upgrade` execute cleanly against real PostgreSQL 18.3.

### 1B. Identity, Authentication, MFA, RBAC & Profiles (`F-001`, `F-002`)
- **Tasks:**
  1. `identity` ORM models, Pydantic schemas, repository, service, `public.py` contract, and routers under `/api/v1/auth` and `/api/v1/users`.
  2. Email/password registration (Argon2id, minor DOB check), login, rotating refresh tokens (`HTTP-only` cookie + SHA-256 stored `sessions` with reuse revocation), logout, session listing/revocation.
  3. TOTP MFA setup & verification (`pyotp`) enforced for `platform_admin`, `school_admin`, `content_admin`, `academic_reviewer` before privileged endpoints succeed (`403 MFA_REQUIRED`).
  4. Backend RBAC dependencies (`get_current_user`, `require_permissions`, `require_roles`) with immutable `audit_logs` writes on auth/MFA/role actions.
  5. User profile (`GET/PATCH /api/v1/users/me/profile`) & Student profile (`GET/PUT /api/v1/users/me/student-profile`).
- **Dependencies:** 1A.
- **Gate:** Unit + PG18 integration tests for registration/login, refresh rotation + reuse revocation, privileged MFA enforcement, and 8-role RBAC `401`/`403` matrix.

### 1C. Content Rights Governance & Versioned Curriculum (`F-005`, `F-007`)
- **Tasks:**
  1. `content` rights models (`content_sources`, `content_licenses`) + `/api/v1/content-rights/*` APIs enforcing `THIRD_PARTY_QUARANTINED` block and legal approval checks.
  2. `curriculum` 11-level hierarchy models, CRUD/versioning/publishing endpoints under `/api/v1/curriculum/*` (`boards`, `sessions`, `versions`, `grades`, `subjects`, `books`, `chapters`, `sections`, `topics`, `concepts`, `learning-objectives`, `prerequisites`).
  3. Recursive DAG cycle detection rejecting cyclic `concept_prerequisites`.
  4. Published-only filtering on student/public tree endpoints (`GET /api/v1/curriculum/tree`), while admins can manage `draft` versions before publishing.
- **Dependencies:** 1A, 1B.
- **Gate:** DAG cycle rejection test, draft-vs-published visibility test, quarantined license rejection test, admin vs student `403` tests.

### 1D. Canonical Question Bank, Search/Filters & 14-Stage Excel/CSV Importer (`F-008`, `F-009`)
- **Tasks:**
  1. `question_bank` models (`questions`, `question_versions`, `question_options`, `question_solutions`, `question_hints`, `question_provenance`, `question_reviews`) supporting multi-format questions (`mcq_single`, `mcq_multiple`, `numerical`, `integer`, `assertion_reason`, `match_following`, `short_answer`, `long_answer`, `case_based`, etc.).
  2. Question CRUD, immutable new-version creation on content edits, review workflow (`DRAFT -> REVIEW -> APPROVED -> PUBLISHED -> ARCHIVED`), strict PYQ provenance gate (`is_pyq=true` blocked without `exam_name`, `exam_year`, `verification_status='verified'`, reviewer sign-off), and strict `ai_generated` labeling checks.
  3. Search & filter API (`GET /api/v1/questions`) with PostgreSQL full-text search + multi-facet filters (`board_id`, `grade_id`, `subject_id`, `chapter_id`, `topic_id`, `concept_id`, `question_type`, `difficulty`, `is_pyq`, `language_code`).
  4. Role-based answer-key redaction (strips `correct_answer_jsonb`, `is_correct`, solutions from student read payloads).
  5. Schema-adaptive Excel/CSV staging pipeline (`/api/v1/imports/*`): `.xlsx` (via `openpyxl`) and `.csv` upload with SHA-256 archival, dynamic sheet/header inspection, raw staging, admin column mapping, formula-injection stripping, row validation, duplicate detection (`canonical_hash`), preview diff summary, idempotent commit into `DRAFT`/`REVIEW`, and atomic batch rollback.
- **Dependencies:** 1B, 1C.
- **Gate:** Version immutability test, PYQ provenance constraint test, student answer redaction test, Excel formula-injection + duplicate + validation error + commit + rollback integration tests.

### 1E. Guided Practice Engine, Notes, Bookmarks & Student Core Dashboard (`F-010`, `F-030`)
- **Tasks:**
  1. Practice sessions (`POST /api/v1/practice/sessions`, `GET /api/v1/practice/sessions/{id}`), immediate attempt evaluation (`POST /api/v1/practice/sessions/{id}/attempts`) persisting `question_attempts` + `outbox_events` and revealing verified solution + common mistakes upon attempt.
  2. Progressive hint reveal (`POST /api/v1/practice/sessions/{id}/hints`) recording `hints_used_count`.
  3. Personal student Markdown/KaTeX notes (`/api/v1/notes`) and idempotent saved questions/bookmarks (`/api/v1/bookmarks`) strictly scoped to `student_id`.
  4. Student core dashboard (`GET /api/v1/dashboard/student`) computing real DB totals, accuracy %, chapter/topic practice coverage, recent sessions, saved question count, notes count, and empty/onboarding state.
- **Dependencies:** 1B, 1C, 1D.
- **Gate:** Hint tracking accuracy, immediate server-evaluated correctness & solution reveal, owner-only `403` isolation on notes/bookmarks/sessions, empty-vs-active real dashboard telemetry.

### 1F. Next.js Web Workspaces & Accessibility (`apps/web`, `packages/*`)
- **Tasks:**
  1. Update `@go4guru/contracts` & `@go4guru/ui` with shared Phase 1 types and accessible UI primitives (KaTeX safe math renderer, nav shell, form controls, loading skeletons, empty states, error banners).
  2. Build connected Next.js App Router views with real backend persistence:
     - `/login`, `/register`, `/onboarding` (profile + grade/board/exam target + MFA verify when privileged)
     - `/dashboard` (Student Core Dashboard with real DB progress, resume practice, or onboarding guidance; admin quick links for admins)
     - `/curriculum` (Dynamic Board → Session → Grade → Subject → Book → Chapter → Topic → Concept → Objective tree & Question filter entry)
     - `/practice` (Interactive Practice Session UI: MCQ/Numerical input, hint reveals, immediate solution feedback, Save Question, Create Note)
     - `/notes` & `/bookmarks` (Personal study notes & saved question folders)
     - `/admin/curriculum`, `/admin/questions`, `/admin/imports` (Curriculum authoring/publish, Question versioning/search/review, Dynamic Excel/CSV upload → column mapper → validation preview → commit/rollback)
- **Dependencies:** 1B–1E.
- **Gate:** `pnpm build`, `pnpm lint`, `pnpm typecheck`, `pnpm test` (`vitest`), plus **Playwright real-browser E2E tests** exercising full flows end-to-end against live FastAPI + PostgreSQL 18!

### 1G. Final Phase 1 Gate & Documentation Sync
- **Tasks:**
  1. Run full backend (`ruff`, `mypy`, `lint-imports`, `pytest` unit + real PG18 integration + API/RBAC matrix) and frontend (`eslint`, `tsc`, `vitest`, `next build`, Playwright E2E) **after final edit**.
  2. Update [MASTER_FEATURE_CHECKLIST.md](file:///d:/go4guru/docs/MASTER_FEATURE_CHECKLIST.md), [IMPLEMENTATION_STATUS.md](file:///d:/go4guru/docs/IMPLEMENTATION_STATUS.md), [API_SPECIFICATION.md](file:///d:/go4guru/docs/API_SPECIFICATION.md), and [DATABASE_SCHEMA.md](file:///d:/go4guru/docs/DATABASE_SCHEMA.md) to reflect exact implemented endpoints, tables, tests, and Phase 2 entry readiness.
