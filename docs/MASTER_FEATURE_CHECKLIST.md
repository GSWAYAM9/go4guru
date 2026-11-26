# Master Feature Checklist (`docs/MASTER_FEATURE_CHECKLIST.md`)

**Rule (Section 50 — Feature Completion Rule):**  
A feature is marked **`COMPLETED`** ONLY when ALL 12 criteria are verified:
1. UI exists  
2. API exists (where needed)  
3. Database schema & migrations exist (where needed)  
4. Input/Output validation exists  
5. Authorization & tenant/role checks exist in backend  
6. Error handling exists  
7. Loading state exists  
8. Empty state exists  
9. Automated tests exist and pass after final edit  
10. Documentation updated  
11. Acceptance criteria pass  
12. Zero fake/hardcoded production functionality remains  

> **Legend:** `—` = Not Started | `WIP` = In Progress | `DONE` = Verified Complete | `N/A` = Not Applicable

| Feature ID | Phase | Feature Name | UI | API | DB | Valid | Authz | Err/Load/Empty | Tests | Docs | Overall Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `F-001` | 1 | Authentication, Sessions & Privileged MFA | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-002` | 1 | Backend RBAC & Permission Policies | N/A | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-005` | 1 | Versioned Data-Driven Curriculum (6–12) | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-006` | 1 | Rights-Aware Content Management System | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-007` | 1 | Content Rights, Licensing & Provenance | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-008` | 1 | Canonical Multi-Format Question Bank | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-009` | 1 | Excel Question Bank Ingestion Pipeline | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-010` | 1 | Guided Practice Engine, Notes & Saved Qs | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-030` | 1 | Personalized Student Dashboard (Core) | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-038` | 1 | Child Safety, Moderation & DPDP Baseline | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `IN_PROGRESS` (Minor gate, PII scrubber, AI safety/crisis redirect, parent `ai_sessions` 403 done; formal guardian consent linking in Ph 8) |
| `F-039` | 1 | Platform Admin, Feature Flags & Audit Logs | WIP | WIP | DONE | DONE | DONE | DONE | DONE | DONE | `IN_PROGRESS` (Audit logs & role assignment & AI cost summary done; feature flags next) |
| `F-011` | 2 | Configurable Quiz Engine | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-012` | 2 | Server-Authoritative Assessment/Test Engine | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-013` | 2 | CBSE Board Prep Workflows & Rubrics | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `IN_PROGRESS` (Configurable CBSE pattern `cbse-2026-v1`, timed mock & objective/numerical breakdowns DONE; subjective rubric grading in Ph 3/7) |
| `F-034` | 2 | Learning-Oriented Analytics & Events | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-017` | 3 | Modular AI Teaching Orchestrator | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-018` | 3 | Multi-Mode Pedagogical AI Tutor & Doubts | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-019` | 3 | Curriculum-Grounded Hybrid RAG System | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-020` | 3 | Deterministic Math & Science Verification | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-021` | 3 | AI Quality Evaluation & Review Queue | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-037` | 3 | AI/Voice Cost Telemetry & Unit Economics | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-022` | 4 | Interactive Live AI Classroom & State Machine | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-023` | 4 | Schema-Driven Interactive Whiteboard | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-024` | 4 | Voice Provider Abstraction & ElevenLabs | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-026` | 5 | Event-Driven Concept Mastery & Adaptive Loop | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-027` | 5 | Spaced Repetition & Multi-Modal Flashcards | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-028` | 5 | Personalized Study Plans & Revision Planner | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `F-035` | 5 | Notification & Alerting System | DONE | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `IN_PROGRESS` (In-app `student_notifications` inbox & triggers for due revision, weak mastery & study plans DONE; email/push dispatch in Ph 7–9) |
| `F-029` | 6 | Homework AI (Upload, OCR, Analysis, Hints) | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-031` | 7 | Teacher Dashboard, Assignments & Grading | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-032` | 7 | Mentor Dashboard, Goals & Interventions | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-004` | 8 | Parent Consent & Privacy-Preserving Linking | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-033` | 8 | Parent/Guardian Dashboard & Summaries | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-003` | 9 | Multi-Tenant School & Institution Management | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-036` | 9 | Subscriptions, Entitlements, Quotas & Billing | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-014` | 10 | JEE Main Preparation Ecosystem | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-015` | 10 | JEE Advanced Preparation Ecosystem | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-016` | 10 | NEET Preparation Ecosystem | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |
| `F-025` | 11 | Multilingual System & Capability Registry | WIP | DONE | DONE | DONE | DONE | DONE | DONE | DONE | `IN_PROGRESS` (`language_capabilities` table, honest TTS/subtitle matrix & classroom language controls DONE; full localization QA in Ph 11) |
| `F-040` | 12 | Mobile & Offline-Safe Scale Readiness | — | — | — | — | — | — | — | Spec | `NOT_STARTED` |

---

## Phase 0 — Foundation Infrastructure Checklist

| Component ID | Phase | Foundation Component | UI | API | DB/Mig | Valid | Security | Err/Load/Empty | Tests | Docs | Overall Status |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `P0-01` | 0 | Monorepo & 16-Module Boundary Enforcement (`import-linter`) | N/A | DONE | N/A | DONE | DONE | N/A | DONE | DONE | `COMPLETED` |
| `P0-02` | 0 | Env & Typed Config (`pydantic-settings`, `.env.example`, `.gitignore`) | DONE | DONE | N/A | DONE | DONE | N/A | DONE | DONE | `COMPLETED` |
| `P0-03` | 0 | Async PG18 Connection & Alembic Baseline (`audit_logs`, `outbox_events`) | N/A | DONE | DONE | DONE | DONE | N/A | DONE | DONE | `COMPLETED` |
| `P0-04` | 0 | Structured Logging (`request_id` + Redaction) & Error Envelope | N/A | DONE | N/A | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `P0-05` | 0 | API Versioning (`/api/v1`, `/ws/v1` stub) & Live/Ready Probes (`503` on down) | DONE | DONE | N/A | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `P0-06` | 0 | Security Baseline (Argon2id, Pinned JWT, Headers, CORS, CSV Sanitizer) | N/A | DONE | N/A | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |
| `P0-07` | 0 | Shared TS Packages, Worker Bootstrap, CI Workflow & Docker Topology | DONE | DONE | N/A | DONE | DONE | DONE | DONE | DONE | `COMPLETED` |

---

## Summary Counts
- **Phase 0 Foundation Deliverables:** 7 / 7 `COMPLETED`
- **Total Master Product Features (`F-001`–`F-040`):** 40
- **Completed:** 23 (`F-001`, `F-002`, `F-005`, `F-007`, `F-008`, `F-009`, `F-010`, `F-011`, `F-012`, `F-017`, `F-018`, `F-019`, `F-020`, `F-021`, `F-022`, `F-023`, `F-024`, `F-026`, `F-027`, `F-028`, `F-030`, `F-034`, `F-037`)
- **In Progress:** 5 (`F-013`, `F-025`, `F-035`, `F-038`, `F-039`)
- **Not Started:** 12 (`F-006` CMS item authoring + Phases 6–12 remaining features)
