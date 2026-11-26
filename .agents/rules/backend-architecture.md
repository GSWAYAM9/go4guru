---
trigger: model_decision
description: Rules for FastAPI backend modules, REST/WebSocket APIs, modular monolith boundaries, assessment authority, and outbox workers in apps/api and apps/worker.
---

# Backend Architecture Rules (`apps/api`, `apps/worker`)

Reference: [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), [docs/API_SPECIFICATION.md](../../docs/API_SPECIFICATION.md).

1. **Modular Monolith Structure:** Organize domain logic under `apps/api/src/modules/<domain>/` (`router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py`, `public.py`). Cross-module calls MUST import only from `<other_module>/public.py`, never internal `repository.py` or ORM models for cross-domain writes.
2. **Router Thinness:** FastAPI route handlers validate Pydantic v2 DTOs, resolve auth/RBAC dependencies (`CurrentUser`, `RequirePermission`, `TenantContext`), call service methods, and map domain exceptions to standard `{ "error": { "code", "message", "details", "request_id" } }` responses. Zero business SQL in routers.
3. **Async & Blocking Safety:** Use `async def` with `asyncpg`/SQLAlchemy 2.0 async sessions for I/O routes; offload CPU-heavy work (Excel parsing, OCR, SymPy batching, audio processing) to `apps/worker` or bounded thread/process pools so the ASGI event loop never blocks.
4. **Transactional Outbox:** Domain mutations that trigger mastery, spaced repetition, notifications, or analytics MUST insert `outbox_events` inside the same DB transaction. Workers MUST consume events idempotently via `processed_event_ids`.
5. **Assessment Authority:** Lock `started_at` and `expires_at` (UTC) on the server, compute all objective/partial/negative scores strictly on the server, enforce `Idempotency-Key` on submissions, and redact answer keys/solutions in active attempt payloads.
6. **Observability:** Propagate `X-Request-ID` correlation IDs, emit structured JSON logs (never logging tokens, passwords, or student PII), and expose `/health/live` and `/health/ready`.
