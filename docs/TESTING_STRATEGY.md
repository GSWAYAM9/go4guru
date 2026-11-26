# Testing Strategy (`docs/TESTING_STRATEGY.md`)

**Core Rule:** No feature passes Phase acceptance or moves to `COMPLETED` in [MASTER_FEATURE_CHECKLIST.md](file:///d:/go4guru/docs/MASTER_FEATURE_CHECKLIST.md) without automated tests covering both happy paths and failure/security boundaries.

---

## 1. Nine-Tier Verification Pyramid

| Tier | Scope & Focus | Tooling | Execution Cadence |
| :--- | :--- | :--- | :--- |
| **1. Unit Tests** | Pure business logic: mastery formulas, SM-2/spaced repetition intervals, JEE Adv partial marking, negative marking, SymPy/Pint verification, Excel row normalization, schema validation | `pytest`, `vitest` / `jest` | Every commit / PR |
| **2. Integration Tests** | Real PostgreSQL 18 + Redis interactions: Alembic migrations, transactional outbox idempotency, curriculum DAG cycle checks, Excel staging → commit → rollback, pgvector+FTS rights-filtered queries | `pytest` + ephemeral PG/Redis | Every PR |
| **3. API Contract & AuthZ Tests** | Every endpoint's Pydantic input/output schema, 401/403 RBAC matrix across all 8 roles, cross-tenant isolation (`Tenant A` vs `Tenant B`), rate limits, idempotent exam submit | `pytest` (`httpx.AsyncClient`) | Every PR |
| **4. End-to-End (E2E) Tests** | Real browser flows: login/MFA, curriculum browsing, practice + notes, timed assessment with reload recovery, Excel upload preview/import, live classroom sync, whiteboard actions, homework upload, teacher grading override | `Playwright` | Staging / Release PR |
| **5. AI Evaluation Tests** | Golden datasets testing math/science correctness, RAG grounding & grade isolation, anti-spoiler Socratic hints, bilingual terminology, safety/jailbreak refusal | Custom Eval Runner (`pytest` / CLI) | Prompt/Model/RAG/Curriculum PRs |
| **6. Security Tests** | Prompt injection, XSS in Markdown/whiteboard, formula injection in Excel, MIME spoofing, JWT tampering, expired exam submission bypass, Parent-to-AI-chat unauthorized access | `pytest` security suite + OWASP ZAP / `gitleaks` / `pip-audit` | Weekly + Pre-Release |
| **7. Data Quality Tests** | Imported Question Bank invariants: valid answers matching options, non-empty solutions, zero `is_pyq=true` without verified provenance, zero duplicate canonical hashes, KaTeX parseability | Automated Data QA Job | Every import + nightly |
| **8. Accessibility Tests** | WCAG 2.1 AA automated audit (`axe-core`), keyboard-only navigation on exam timer/palette & whiteboard, ARIA announcements, caption presence on classroom audio | `axe-playwright` + manual screen-reader checklist | PR / Release |
| **9. Load & Resilience Tests** | Concurrent 10k exam timer heartbeats + autosaves, WebSocket classroom room fan-out, worker queue burst under 10k-row Excel import, Redis/Voice circuit-breaker degradation | `k6` or `Locust` | Pre-Phase Release |

---

## 2. Mandatory Critical Test Scenarios (Section 47 Coverage)

- **Authentication & Authorization:** Expired JWT, revoked refresh reuse detection, MFA enforcement on admin roles, 8×N endpoint permission matrix.
- **Tenant Isolation:** Every tenant-owned resource (`schools`, `classes`, `assignments`, `tests`, `analytics`, `reports`) tested across 2 distinct tenant fixtures.
- **Excel Import:** Multi-sheet detection, missing columns, invalid difficulty/options, duplicate fingerprint detection, CSV/Excel formula injection neutralization, batch rollback.
- **Quiz & Assessment:** Server UTC timer expiry blocks late submits; client-tampered timer/score payloads ignored; concurrent duplicate submit calls with same `Idempotency-Key` score exactly once; JEE Adv partial marking and NEET negative marking verified across edge cases.
- **AI, RAG & Verification:** RAG SQL filter rejects `embedding_allowed=false` and `status != 'PUBLISHED'`; SymPy catches wrong algebraic step; Socratic mode does not leak answer on Turn 1.
- **Classroom, Voice & Whiteboard:** Invalid whiteboard opcode rejected; replay from `snapshot + events` matches live canvas state; ElevenLabs outage falls back gracefully to captions.
- **Homework, Mastery & Revision:** Multi-page PDF/image validation, graduated hints stay locked until requested, outbox replay does not double-increment mastery, SM-2 interval math verified.
- **Parent, Teacher & Institution:** Consented parent sees summary metrics but receives 403 on student raw AI chat; teacher override updates authoritative grade while logging AI baseline.
