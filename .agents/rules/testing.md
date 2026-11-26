---
trigger: model_decision
description: Rules for unit, integration, API/RBAC, multi-tenant, E2E, AI evaluation, security, accessibility, data quality, and load testing.
---

# Testing & Verification Rules

Reference: [docs/TESTING_STRATEGY.md](../../docs/TESTING_STRATEGY.md), [docs/MASTER_FEATURE_CHECKLIST.md](../../docs/MASTER_FEATURE_CHECKLIST.md).

1. **Mandatory Verification Before Completion:** Never report a task or feature complete until relevant automated tests run and pass *after the final edit*. Report exact commands run, scope, and observed counts—never fabricate or extrapolate test passes.
2. **No Silent Test Dilution:** Never skip, delete, or weaken failing assertions to make CI green. Fix the underlying bug or document genuine blockers.
3. **Required Coverage by Layer:**
   - **Unit:** Mastery formulas, SM-2 intervals, negative/partial marking (JEE Adv subsets), SymPy/Pint verification, Excel row normalization.
   - **Integration (Real PostgreSQL 18 + Redis):** Migrations, outbox idempotency, curriculum DAG cycle checks, Excel staging/rollback, rights-filtered RAG queries.
   - **API & AuthZ Matrix:** Every new endpoint MUST have tests verifying 401 unauthenticated, 403 cross-role, and 403/404 cross-tenant isolation (`Tenant A` vs `Tenant B`).
   - **Assessment Reliability:** Test expired UTC server timer rejection, tampered client score rejection, and duplicate `Idempotency-Key` submission safety.
   - **Security & Data Quality:** Test formula-injection neutralization, XSS sanitization, answer-key redaction in active exams, and zero unverified PYQs.
   - **E2E, A11y & AI Evals:** Playwright critical flows + `axe` WCAG AA checks + golden AI eval regression suites on prompt/model/RAG edits.
