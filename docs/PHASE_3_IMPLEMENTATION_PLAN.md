# Phase 3 Implementation Plan & Acceptance Checklist — AI Tutor & Grounded AI Architecture

> **Status:** Completed & Verified (`Phase 3`)  
> **Scope:** Implements `F-017` (16-Module AI Teaching Orchestrator), `F-018` (Multi-Mode Pedagogical Tutor & Doubt Solver), `F-019` (Curriculum-Grounded Hybrid RAG), `F-020` (Deterministic Math/Science Verification), `F-021` (AI Evaluation Suite & Human Review Queue), and `F-037` (AI Cost Telemetry, Quotas & Rate Limits; voice metering completes in Phase 4).  
> **Gate Rule:** Phase 4 does NOT start until every item in Section 3 (Acceptance Checklist) is verified and tested.

---

## 1. Non-Negotiable Phase 3 Principles

1. **Zero Monolithic Prompts:** Every orchestration stage runs as a dedicated module with explicit Pydantic I/O contracts and logged `prompt_version`: `SafetyLayer -> IntentRouter -> StudentContextResolver -> CurriculumContextResolver -> HybridRetrievalService -> TeachingPlanner -> ModeGenerator <-> MathScienceVerifier (<= 2 retries) -> CitationValidator -> OutputSafety -> CostLedger & ReviewQueue`.
2. **Confidentiality & Privacy Minimization:** External provider payloads NEVER receive student `display_name`, `email`, `phone`, or `school`. Provider API keys remain strictly backend env vars (`SecretStr`, never `NEXT_PUBLIC_*`). Parents are denied (`403`) access to student `ai_sessions` / `ai_messages`.
3. **Truthful Verification & Provider Disclosure:** Responses are marked `verified` ONLY when an actual deterministic check (`SymPy` AST-whitelisted solver/equivalence, `Pint` dimensional unit check, or stoichiometry atom balance) succeeds; if verification fails or cannot be applied, surface `unverified` or `verification_failed` honestly. Unconfigured external LLM keys execute `GroundedDeterministicFallbackProvider` with explicit `is_fallback=true` disclosure.
4. **Strict Content Rights RAG Gate:** Only `status = 'PUBLISHED'` AND `embedding_allowed = true` AND unexpired licenses may enter `knowledge_documents` / `knowledge_chunks` or be returned by hybrid search (`quarantined_third_party` sources are permanently excluded).

---

## 2. Work Breakdown & Dependencies

| Stream | Deliverables | Dependencies |
|---|---|---|
| **3A. Migration (`0004_phase3_ai_tutor_rag.py`)** | `knowledge_documents`, `knowledge_chunks` (FTS `tsvector` GIN + dense vector), `ai_sessions`, `ai_messages`, `ai_tool_calls`, `provider_rate_cards`, `ai_cost_events`, `ai_review_queue`, `ai_eval_datasets`, `ai_eval_runs`, `ai_eval_results`, Phase 3 RBAC seeds | `0003_phase2_assessment_analytics` |
| **3B. Upstream Module Contracts** | `identity/public.py` PII-stripped `AnonymizedStudentContextContract`; `curriculum/public.py` `ResolvedTutorCurriculumContract` | 3A |
| **3C. Provider Gateway, Routing, Safety & Cost Control** | `ai/provider.py` (`GeminiProvider`, `OpenAIProvider`, `AnthropicProvider`, `GroundedDeterministicFallbackProvider`, `CircuitBreaker`, `AIRouterGateway`), `ai/safety.py` (prompt-injection, self-harm crisis redirect, PII guard), per-user RPM & daily quota enforcement, USD cost recording | 3A |
| **3D. Deterministic Math/Science Verifier & Hybrid RAG** | `ai/verifier.py` (`SymPy` AST-whitelisted solver, `Pint` SI unit checker, chemistry atom conservation balancer), `ai/retrieval.py` (licensed chunk ingestion, PostgreSQL FTS + dense cosine RRF fusion, pre-filtered by grade/subject/board/language/rights, post-generation citation validation) | 3A |
| **3E. Modular AI Orchestrator & API** | `ai/resolvers.py`, `ai/pedagogy.py` (Concept Explain, Step-by-Step, Hints, Socratic anti-spoiler, Practice Gen, Exam Prep, Follow-ups, 6-lang & grade framing), `ai/orchestrator.py`, `ai/router.py`, `ai/evals.py` | 3B, 3C, 3D |
| **3F. Student & Reviewer Next.js UI** | `/tutor` (multi-mode interactive AI Tutor chat: session history, teaching mode switcher, curriculum & language framing, verified/fallback badges, clickable citations, follow-up chips, optional practice generator, safety report flag) & `/admin` / eval panel | 3E |
| **3G. Evaluation Dataset & Comprehensive Tests** | `tests/evals/datasets/` JSONL datasets (`math_verification`, `science_verification`, `rag_grounding`, `pedagogy_anti_spoiler`, `safety_redteam`, `multilingual`), unit tests (SymPy/Pint/Chemistry/CircuitBreaker/Safety), PG18 integration tests (RAG rights isolation, parent 403, Socratic spoiler guard, quota/cost logging, eval run), Vitest, Playwright Chromium E2E | All above |

---

## 3. Phase 3 Acceptance Checklist (Must Pass Before Phase 4)

- [x] **AC-3.01 Modular Provider & Model Routing:** Backend abstracts `gemini`, `openai`, `anthropic`, and `grounded_fallback` behind `LLMProvider`; lightweight tasks route separately from complex reasoning; circuit breaker + timeouts fail over cleanly; zero API keys leak to `NEXT_PUBLIC_*` or API responses.
- [x] **AC-3.02 Student & Curriculum Context Resolvers (Zero PII):** `ContextResolver` strips PII cleanly and resolves grade/board/exam target/language prefs + practice tier; `CurriculumResolver` attaches syllabus hierarchy, learning objectives, and prerequisite context.
- [x] **AC-3.03 Hybrid RAG & Source Rights Isolation:** Only approved, `embedding_allowed=true`, `PUBLISHED` chunks enter retrieval; FTS + vector RRF returns ranked citations with `hierarchy_path` & `source_attribution`; post-gen citation check strips hallucinated chunk IDs; quarantined sources never appear.
- [x] **AC-3.04 Multi-Mode Pedagogy & Anti-Spoiler:** Supports Concept Explanation, Step-by-Step Solution, Hints, Socratic (`spoiler_guard=true` Turn-1 withheld answer), Exam-Specific framing, Grade-aware depth, Practice Draft Generation, and Follow-up Questions, respecting `preferred_explanation_language`.
- [x] **AC-3.05 Real Deterministic Verification:** Math expressions verified via AST-whitelisted `SymPy`, physics units checked via `Pint`, chemistry equations balanced via stoichiometry linear algebra; unverified outputs are NEVER labeled `verified`.
- [x] **AC-3.06 AI Safety & Parent Privacy Boundary:** Self-harm/crisis input triggers supportive helpline redirect + `ai_review_queue` escalation; prompt injection blocked; `parent` role gets `403` attempting to read student AI sessions/messages.
- [x] **AC-3.07 Cost Tracking & Rate Limits:** Every turn logs tokens, latency, fallback flag, and USD cost from `provider_rate_cards` into `ai_cost_events`; exceeds RPM/daily quota enforces `429 RATE_LIMIT_EXCEEDED`.
- [x] **AC-3.08 Versioned Eval Dataset & Review Queue:** Automated regression suite executes curated golden eval dataset against orchestrator/verifier/safety/RAG and persists `ai_eval_runs`/`ai_eval_results` + reviewer queue triage.
- [x] **AC-3.09 Student Tutor UI:** Student can create/resume tutor sessions, ask doubts, switch modes/languages/curriculum context, inspect verification status & cited curriculum excerpts, click follow-up prompts, generate practice drafts, and flag messages.
- [x] **AC-3.10 Verification & Docs:** `ruff`, `mypy`, `lint-imports`, `pytest` (unit + PG18 integration + eval regression gates), `@go4guru/contracts` build, `eslint`, `tsc`, `vitest`, `next build`, and Playwright Chromium E2E all pass after final edit; `IMPLEMENTATION_STATUS.md`, `MASTER_FEATURE_CHECKLIST.md`, `PHASE_3_IMPLEMENTATION_PLAN.md`, and `DECISION_LOG.md` updated truthfully.
