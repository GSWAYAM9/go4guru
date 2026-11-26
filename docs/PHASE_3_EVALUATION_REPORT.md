# Phase 3 AI Architecture, Supported Models, Evaluation Report & Risks (`docs/PHASE_3_EVALUATION_REPORT.md`)

**Last Updated:** 2026-11-26  
**Scope:** Covers Phase 3 (`F-017`, `F-018`, `F-019`, `F-020`, `F-021`, AI cost tier of `F-037`, safety controls of `F-038`).

---

## 1. Supported Providers & Configured Models

Backend credentials live exclusively inside `apps/api/src/core/config.py` (`SecretStr`, never exposed in frontend `NEXT_PUBLIC_*` variables or API payloads). `GET /api/v1/ai/models` returns non-secret provider readiness flags truthfully.

| Provider Key | Adapter Class | Fast Routing Model | Complex Reasoning Model | Rate Card (`provider_rate_cards`) | Status in Default Local Env |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `gemini` | `GeminiProvider` | `gemini-2.5-flash` | `gemini-2.5-pro` | `$0.15 / $0.60` (flash), `$1.25 / $10.00` (pro) per 1M | Unconfigured (`GEMINI_API_KEY` empty) unless set in `.env` |
| `openai` | `OpenAIProvider` | `gpt-4o-mini` | `gpt-4o` | `$0.15 / $0.60` (mini), `$2.50 / $10.00` (4o) per 1M | Unconfigured (`OPENAI_API_KEY` empty) unless set in `.env` |
| `anthropic` | `AnthropicProvider` | `claude-3-5-haiku-latest` | `claude-3-7-sonnet-latest` | `$0.80 / $4.00` (haiku), `$3.00 / $15.00` (sonnet) per 1M | Unconfigured (`ANTHROPIC_API_KEY` empty) unless set in `.env` |
| `grounded_fallback` | `synthesize_grounded_fallback` | `deterministic-v1` | `deterministic-v1` | `$0.00 / $0.00` | Always active fallback returning retrieved curriculum citations + SymPy/Pint/Chemistry verifier checks (`is_fallback = true`) |

**Routing & Resilience:** `AIRouterGateway` routes light classification vs complex derivations (`TaskComplexity`), guards each provider with a `CircuitBreaker` (opening after repeated timeouts/HTTP >= 400 failures), fails over across configured providers cleanly, and executes at most `ai_max_verifier_retries` (default 2) correction loops when deterministic math/science checks reject an LLM draft.

---

## 2. Verification Boundaries & Anti-Fabrication Rules

1. **SymPy Math (`verifier.py`):** Uses `ast.parse` whitelist (disallowing imports, attributes, lambdas, comprehensions, dunders) + `sympy.parsing.sympy_parser.parse_expr` (`__builtins__: {}`). Verifies arithmetic/symbolic simplification, solves single equations, and checks algebraic equivalence (`simplify(a - b) == 0`).
2. **Pint Physics Units (`verifier.py`):** Verifies dimensional compatibility (`kilogram * meter / second ** 2 == newton`) and flags mismatches cleanly (`verification_failed`).
3. **Chemistry Stoichiometry (`verifier.py`):** Parses species & parenthesized formulas and verifies atom-count conservation across reactants `->` products.
4. **Honesty Policy:** Responses only carry `verification_status = "verified"` when an actual deterministic tool check passes. Conceptual/qualitative prose turns are explicitly labeled `not_applicable` or `unverified` — never stamped `verified`.

---

## 3. Golden Evaluation Dataset Results (`phase3_golden_eval_v1.jsonl`)

Versioned dataset stored at `apps/api/tests/evals/datasets/phase3_golden_eval_v1.jsonl` (11 test cases across 4 release-gate categories) executed by `tests/evals/test_ai_golden_eval_suite.py` and `POST /api/v1/ai/evals/run`:

| Category | Cases | Pass Rate | Verified Controls |
| :--- | :---: | :---: | :--- |
| `math_verification` | 2 | 100% | Linear & quadratic equation solving via sandboxed SymPy |
| `science_verification` | 4 | 100% | Pint SI force dimensionality pass/fail + chemical atom conservation pass/fail |
| `pedagogy_anti_spoiler` | 2 | 100% | `spoiler_guard = true` on `hint`/`socratic` turns + withheld Turn-1 answers |
| `safety_redteam` | 3 | 100% | Prompt-injection block, self-harm crisis helpline redirect (`14416`), email/phone PII scrubbing |
| **Total Gate Suite** | **11** | **100%** | Blocked on > 2% regression; persisted in `ai_eval_datasets`, `ai_eval_runs`, `ai_eval_results` |

---

## 4. Documented Limitations & Remaining Risks

1. **Unconfigured Remote Vendor Keys in Local Dev:** Because `.env` does not hold paid Gemini/OpenAI/Anthropic secrets in local CI/sandbox runs, live vendor HTTP failover was verified against `httpx.MockTransport` in unit tests (`test_circuit_breaker_failover_with_httpx_mock_transport`), while live end-to-end tests exercise `grounded_fallback`. Real external vendor latency, rate-limit headers, and structured-JSON compliance should be re-validated in staging once real provider keys are provisioned.
2. **Native Windows PostgreSQL Vector Storage (`ADR-009`):** Host PostgreSQL 18.3 lacks `pgvector`, so dense semantic retrieval currently fuses SQL `tsvector` GIN full-text ranks with SQL-prefiltered `DOUBLE PRECISION[]` cosine vectors via Reciprocal Rank Fusion (`RRF`). While accurate and rights-enforced, multi-million-chunk corpora should enable `pgvector` HNSW indexes on Linux PostgreSQL in staging/production.
3. **Process-Local Rate Limits / Circuit Breaker:** When host Redis (`127.0.0.1:6379`) is stopped, per-user RPM & daily quotas enforce deterministically against `ai_cost_events` in PostgreSQL; distributed multi-worker rate limiting requires active Redis.
4. **Corpus Size:** Due to the `ADR-003` copyright quarantine of `D:\class-*` PDFs, RAG corpus coverage depends on licensed/original documents ingested via `POST /api/v1/ai/knowledge/documents`.
