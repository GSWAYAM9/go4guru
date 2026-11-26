# Phase 0 Implementation Plan — Foundation and Architecture

> **Status:** Active Execution (`Phase 0`)  
> **Rule:** Follows `DISCOVER -> AUDIT -> SPECIFY -> DESIGN -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> DOCUMENT -> RELEASE` (`AGENTS.md` §30).  
> **Scope Guard:** Implements architecture, configuration, DB/migration framework, logging, error envelope, API versioning, health/readiness, CI/CD, code quality, security baseline, testing setup, and tracking ONLY. Zero Phase 1+ product features or fake UI/API mocks.

---

## 1. Scope & Existing State Preserved
- **Preserved Assets:**
  - `AGENTS.md` and `.agents/rules/*.md` (10 modular rule files)
  - All 25 authoritative specs in `docs/`
  - Sibling `D:\class-*` directories remain untouched and strictly quarantined (`CONTENT_RIGHTS.md`)
  - Host PostgreSQL 18 runtime (`127.0.0.1:5432`) preserved; Docker Compose provides reproducible PG18 + pgvector, Redis, and MinIO topology
- **Approved Stack Preserved (`docs/ARCHITECTURE.md`):**
  - Web: Next.js (App Router) + React + TypeScript + Tailwind CSS (`apps/web`)
  - Shared packages: `packages/contracts`, `packages/ui`, `packages/whiteboard-schema`
  - API: FastAPI + Python 3.12 + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic (`apps/api`)
  - Worker: Python async worker runtime over Redis (`apps/worker`)

## 2. Work Breakdown & Deliverables

| Workstream | Target Files / Modules | Acceptance Criteria |
|---|---|---|
| **0.1 Repo & Env Config** | `.gitignore`, `.editorconfig`, `.env.example`, `package.json`, `pnpm-workspace.yaml` | Git initialized; secrets excluded; all required env variable names documented with zero real secrets |
| **0.2 Modular Monolith Boundaries** | `apps/api/src/modules/{16 domains}/{__init__.py,public.py}`, `apps/api/pyproject.toml` (`import-linter`) | All 16 domains present; `lint-imports` enforces no cross-module internal imports and no `core -> modules` upward imports |
| **0.3 App Config & Security Baseline** | `apps/api/src/core/{config.py,security.py,middleware.py}` | Typed `pydantic-settings`; non-dev weak JWT secret blocked in prod; Argon2id hashing; strict JWT HS256/RS256 allowlist; security headers; CORS allowlist; CSV formula neutralization |
| **0.4 DB & Alembic Framework** | `apps/api/src/core/{database.py,outbox.py}`, `apps/api/alembic/*`, `0001_phase0_baseline.py` | Async SQLAlchemy engine/session factory; baseline migration creating foundation `audit_logs` & `outbox_events` tables with `timestamptz`, UUID PKs, and indexes |
| **0.5 Logging & Error Envelope** | `apps/api/src/core/{logging.py,errors.py}` | Structured JSON logs with `request_id` + secret redaction; all FastAPI/Pydantic/HTTP errors normalized to `{ error: { code, message, details, request_id } }` |
| **0.6 API Versioning & Health** | `apps/api/src/main.py`, `apps/api/src/core/{health.py,redis_client.py}` | `/health/live`, `/api/v1/health/live`, `/health/ready`, `/api/v1/health/ready`, `/api/v1/meta`, `/ws/v1` router boundary; readiness truthfully checks PG + Redis (HTTP 503 when unavailable) |
| **0.7 Async Worker & Shared Packages** | `apps/worker/*`, `packages/{contracts,ui,whiteboard-schema}/*` | Worker boots cleanly with config/DB/Redis readiness check; shared TS packages compile cleanly with `tsc` |
| **0.8 Web Foundation & Truthful UI** | `apps/web/*` | Accessible Next.js App Router foundation shell displaying real backend readiness via `/api/v1/health/ready` (real loading, error, degraded, and healthy states — zero fake metrics) |
| **0.9 CI/CD & Testing** | `.github/workflows/ci.yml`, `infra/docker/docker-compose.yml`, `apps/api/tests/*`, `apps/worker/tests/*`, `apps/web/tests/*` | `ruff`, `mypy`, `lint-imports`, `pytest`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass after final edit |
| **0.10 Governance & Tracking** | `docs/{IMPLEMENTATION_STATUS,MASTER_FEATURE_CHECKLIST,DECISION_LOG}.md` | Updated honestly with exact test counts, local infra gaps (Redis / PG `pgvector`), and Phase 1 entry criteria |

## 3. Risks & Mitigations
- **Local Redis & `pgvector` absent on Windows host:** Docker is not installed on the local Windows workstation and `redis-server` is closed on `6379`. Mitigation: Readiness endpoint MUST report `503` truthfully when Redis/PG are down; CI runs against real `pgvector/pgvector:pg18` + `redis:7.4-alpine` containers; Phase 0 baseline migration uses standard PostgreSQL 18 DDL (`gen_random_uuid()`, `JSONB`, `timestamptz`) without requiring `pgvector` until Phase 3 (`ai` module), while documenting `pgvector` setup for WSL 2 / Docker before Phase 3.
- **Scope creep into Phase 1:** Explicitly defer user auth endpoints, curriculum CRUD, and question bank routes to Phase 1 (`F-001`–`F-010`).
