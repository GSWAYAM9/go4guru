---
trigger: model_decision
description: Rules for AI orchestration, 16-module pipeline, hybrid RAG, SymPy/Pint/Chemistry verification, anti-spoiler pedagogy, evaluations, and cost tracking.
---

# AI Engineering Rules (`apps/api/src/modules/ai`, `apps/worker`)

Reference: [docs/AI_ARCHITECTURE.md](../../docs/AI_ARCHITECTURE.md), [docs/AI_EVALUATION.md](../../docs/AI_EVALUATION.md), [docs/COST_MODEL.md](../../docs/COST_MODEL.md).

1. **Modular Orchestration Only:** Implement the 16-module architecture (`IntentRouter`, `ContextResolver`, `CurriculumResolver`, `RetrievalService`, `TeachingPlanner`, `ProblemSolver`, `MathScienceVerifier`, domain generators, `Translation`, `Whiteboard/Voice Planners`, `SafetyLayer`, `QualityEvaluator`) with typed Pydantic I/O contracts and versioned prompts (`prompt_version`). Never write one monolithic prompt or allow unbounded agent loops (cap tool/retry loops at max 2).
2. **Model-Agnostic Gateway:** Call LLMs exclusively through `LLMProvider` abstraction; route tasks by complexity (light models for classification/routing, reasoning models for complex JEE/proofs) and enforce circuit-breaker fallbacks.
3. **Strict RAG Grounding & Rights Filter:** Every retrieval query MUST apply SQL pre-filters on curriculum metadata (`board`, `grade`, `subject`, `language`) AND rights (`status = 'PUBLISHED'` AND `embedding_allowed = true` AND unexpired license). Wrap retrieved chunks as untrusted data blocks; validate cited `chunk_id`s post-generation.
4. **Deterministic Math & Science Verification:** Verify symbolic algebra/calculus via AST-whitelisted SymPy (timeout <= 2s, zero `eval`/`exec`), physics units via Pint, and chemistry stoichiometry deterministically. If verification fails after bounded retry, surface explicit uncertainty—never fabricate confident wrong math.
5. **Pedagogical Anti-Spoiler Guard:** Default `spoiler_guard = true` for `Hint`, `Socratic`, and `Homework Coaching` modes; guide with graduated hints instead of dumping Turn-1 final answers.
6. **PII Minimization & Cost Ledger:** Strip all student PII (`name`, `email`, `phone`, `school`) in `ContextResolver` before external provider calls. Record tokens, latency, and USD estimate to `ai_cost_events` and enforce deterministic Redis/DB quotas before execution.
7. **Evaluation Gate:** Any prompt, model, retrieval, or verifier change MUST pass `tests/evals/` golden regression gates (correctness, grounding, anti-spoiler, safety red-team).
