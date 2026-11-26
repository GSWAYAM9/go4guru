# Architecture Decision Log (`docs/DECISION_LOG.md`)

Records significant architectural, security, legal, cost, and data decisions with trade-offs and approval state.

---

### `ADR-001` — Monorepo Tech Stack Selection (Next.js + FastAPI + PostgreSQL 18 + Redis)
- **Date:** 2026-11-26 | **Status:** Proposed (Phase 0)
- **Context:** `d:\go4guru` is greenfield (0 existing code files). Host already runs PostgreSQL 18, Node 22.16.0, pnpm 12.3.4, and Python 3.12.10.
- **Decision:** Adopt `Next.js + React + TypeScript` (`apps/web`), `FastAPI + Python 3.12 + SQLAlchemy 2.0 + Alembic` (`apps/api`), Python async workers (`apps/worker`), `PostgreSQL 18 + pgvector`, `Redis`, and `S3-compatible` storage.
- **Trade-Offs:** Unified Python backend accelerates SymPy/SciPy/Pint math verification, OCR, Excel ingestion, and AI orchestration without extra network hops, at the cost of maintaining two runtimes (Node + Python) in the monorepo.

### `ADR-002` — Modular Monolith Before Microservices
- **Date:** 2026-11-26 | **Status:** Proposed (Phase 0)
- **Context:** 16 functional domains with complex cross-domain transactions (assessment submit → outbox → mastery/revision).
- **Decision:** Build a strict modular monolith with explicit module boundaries (`import-linter`) and transactional outbox event decoupling; defer service extraction (`ai`, `classroom`, `ingestion`) until measurable scaling triggers occur.
- **Trade-Offs:** Avoids premature distributed systems complexity, network serialization overhead, and multi-repo deployment overhead while preserving clean future extraction seams.

### `ADR-003` — Quarantine of External `D:\class-*` ALLEN® PDFs
- **Date:** 2026-11-26 | **Status:** Enforced Policy (Phase 0)
- **Context:** Audit of 374 PDFs in sibling `D:\class-*` directories revealed proprietary ALLEN® branding, internal file paths, DRM `/Encrypt` flags, mislabeled filenames, and rendering defects.
- **Decision:** Quarantine all 374 files outside `d:\go4guru`; prohibit production hosting or RAG indexing without explicit written license. Seed Phase 1 with lawful curriculum hierarchy + original/OER items + user-supplied licensed `.xlsx` files.
- **Trade-Offs:** Delays ready-made content volume in Phase 1, but eliminates existential copyright/trademark infringement risk.

### `ADR-004` — Parent Access Boundary (Privacy-Preserving Summaries)
- **Date:** 2026-11-26 | **Status:** Proposed (Phase 0)
- **Context:** Platform serves minors requiring parental consent while encouraging students to ask AI tutors honest doubts without surveillance anxiety.
- **Decision:** Linked Parents access summarized progress, goals, weak topics, and assessments, and are strictly blocked in backend RBAC from reading raw `ai_messages` transcripts.
- **Trade-Offs:** Balances child psychological safety with parental oversight; specific safety/self-harm escalations handled separately via Trust & Safety workflow.

### `ADR-005` — Server-Authoritative Assessments & Outbox Learning Events
- **Date:** 2026-11-26 | **Status:** Proposed (Phase 0)
- **Context:** Client-trusted exam timers/scores and inline synchronous mastery updates fail under cheating or high load.
- **Decision:** Lock `started_at`/`expires_at` and calculate all scores exclusively on server with `Idempotency-Key`; write learning events to `outbox_events` in the same DB transaction for idempotent worker consumption.

### `ADR-006` — Pluggable Voice (`VoiceProviderInterface`) & Language Capability Registry
- **Date:** 2026-11-26 | **Status:** Proposed (Phase 0)
- **Context:** ElevenLabs selected as initial TTS/STT provider across diverse Indian languages where quality varies dramatically.
- **Decision:** Abstract all voice calls behind `VoiceProviderInterface` (with S3 caching & circuit breaker) and drive UI language/voice options truthfully from `language_capabilities` table.

### `ADR-007` — Pending User Decisions Before Coding (Phase 1+ Unblockers)
1. **Local Infra Choice:** Install Docker Desktop (`postgres+pgvector`, `redis`, `minio`) OR run Redis + pgvector via `WSL 2 Ubuntu`?
2. **Initial Question Bank / Excel Data:** Will licensed/original `.xlsx` files be provided for Phase 1 ingestion testing, or should Phase 1 start with an authored sample seed + clean Excel test fixtures?
3. **Whiteboard Engine (Needed Phase 4):** Approve commercial `tldraw` license evaluation vs zero-royalty MIT `Excalidraw`?
4. **External AI / Voice / Storage Keys (Needed Phase 3–4):** Preferred primary LLM provider (Gemini / OpenAI / Anthropic) and cloud region (`ap-south-1` / `asia-south1`).

### `ADR-008` — Phase 0 Worker Package Namespace, Baseline DDL & CI Service Scope
- **Date:** 2026-11-26 | **Status:** Accepted (Phase 0 Implementation)
- **Context:** Installing both `apps/api` (`src/`) and `apps/worker` (`src/`) as editable distributions in a single shared `.venv` caused Python module shadowing on `src.main`. Additionally, local Windows lacks `redis-server`, Docker Desktop, and `pgvector`.
- **Decision:** Place the worker Python package under `apps/worker/src/go4guru_worker/` so `apps/api` (`src.*`) and `apps/worker` (`go4guru_worker.*`) coexist cleanly in one `.venv`; keep Alembic `0001_phase0_baseline.py` scoped strictly to `audit_logs` and `outbox_events` using standard PG 18 types (`UUID`, `TIMESTAMPTZ`, `JSONB`) without premature domain tables or `pgvector` extension dependency; test PostgreSQL DDL emission offline locally while enabling full `pgvector:pg18` + `redis` live socket tests in `.github/workflows/ci.yml` (`GO4GURU_RUN_LIVE_DB_TESTS=1`).
- **Trade-Offs:** Keeps Phase 0 clean and prevents editable-install shadowing across backend packages; requires starting WSL2/Docker Redis + Postgres DB credentials locally before Phase 1 online migration runs.

### `ADR-009` — Phase 3 Native PostgreSQL 18 Hybrid Search & Truthful Unconfigured LLM Fallback
- **Date:** 2026-11-26 | **Status:** Accepted (Phase 3 Implementation)
- **Context:** Host PostgreSQL 18.3 on Windows does not bundle native `pgvector` binary files, and local/CI environments may boot without live vendor LLM API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Meanwhile, Phase 3 requires genuine hybrid search (sparse FTS + dense semantic vector RRF), server-only provider abstraction, and zero fabricated AI claims.
- **Decision:**
  1. Store `knowledge_chunks.fts_tsv` (`TSVECTOR` with GIN index) alongside `embedding_vec` (`DOUBLE PRECISION[]` normalized float vector) in PostgreSQL 18, fusing SQL `ts_rank_cd` full-text rank and SQL-prefiltered dense cosine similarity via Reciprocal Rank Fusion (`RRF`). An upgrade migration can swap `embedding_vec` to `pgvector` `vector(...) HNSW` seamlessly when targeting Linux/pgvector.
  2. Implement real HTTP adapters for `GeminiProvider`, `OpenAIProvider`, and `AnthropicProvider` (with retries, circuit-breaker failover, and rate-card cost logging). When no external vendor key is configured or external providers fail/trip circuit breakers, route explicitly to `GroundedDeterministicFallbackProvider` returning curated syllabus chunks with citations + deterministic SymPy/Pint/Chemistry verifier results, clearly flagging `is_fallback=true` and `provider="grounded_fallback"` — never pretending a live LLM generated prose without a key.
- **Trade-Offs:** Exact cosine over pre-filtered `DOUBLE PRECISION[]` rows scales cleanly to thousands of curriculum-scoped chunks per grade/subject without failing native Windows PG 18 installs; HNSW ANN via `pgvector` remains recommended at multi-million chunk scale.

### `ADR-010` — Phase 4 Whiteboard Technology Evaluation & Deterministic Canvas Architecture
- **Date:** 2026-11-26 | **Status:** Accepted (Phase 4 Implementation)
- **Context:** Evaluating `tldraw` vs `@excalidraw/excalidraw` vs a custom schema-driven renderer under React 19 + Next.js 15, strict zero-arbitrary-code security, KaTeX formula rendering, parameterized STEM diagrams (`free_body`, `circuit`, `ray_optics`, `chem_bond`, `number_line`), Cartesian graph plotting, undo/redo snapshots, and commercial licensing constraints (`ADR-007`).
- **Evaluation Summary:**
  - `tldraw` SDK v2/v3 offers strong UX but mandates a paid commercial SaaS license to remove the `made with tldraw` watermark in production and introduces custom license risk.
  - `@excalidraw/excalidraw` is MIT-licensed, but assumes browser-only bundle semantics requiring dynamic `ssr: false` shims, treats KaTeX math and structured domain diagrams as bolted-on overlays, and does not natively enforce our 12-opcode STEM graph/diagram schema.
- **Decision:** Implement an **engine-agnostic canonical 12-opcode `WhiteboardAction` schema** (`@go4guru/whiteboard-schema`) backed by a **zero-royalty React 19 SVG + HTML/KaTeX Deterministic Whiteboard Engine** (`apps/web/src/components/whiteboard-canvas.tsx`) supporting native `WRITE_TEXT`, `INSERT_FORMULA` (KaTeX `trust: false`), `DRAW_LINE`, `DRAW_ARROW`, `DRAW_SHAPE`, `DRAW_GRAPH` (deterministic coordinate plotting), `DRAW_DIAGRAM` (parameterized vector templates), rights-vetted `INSERT_IMAGE`, `HIGHLIGHT`, `ERASE`, `MOVE`, `TRANSFORM`, interactive student annotations, monotonic undo/redo stacks backed by PostgreSQL `whiteboard_events` + `whiteboard_snapshots`, `aria_summary` live accessibility feed, and clean SVG export.
- **Trade-Offs:** Zero licensing cost, full React 19/SSR compatibility, and 100% schema fidelity without executing any external/AI HTML or JS; complex freehand artistic brushes can be layered cleanly via an Excalidraw adapter later without altering DB events or APIs.
