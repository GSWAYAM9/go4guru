# Deployment & Infrastructure Strategy (`docs/DEPLOYMENT.md`)

**Environments:** `development` (local) | `staging` (pre-prod mirror) | `production` (live HA)

---

## 1. Environment Topology

| Component | Development (Local) | Staging | Production |
| :--- | :--- | :--- | :--- |
| **Web (`apps/web`)** | `pnpm dev` (`localhost:3000`) | Managed container / ECS / Cloud Run | Multi-AZ autoscaling containers + CDN |
| **API (`apps/api`)** | `uvicorn` reload (`localhost:8000`) | 2 container replicas behind HTTPS LB | Multi-AZ autoscaling containers (REST + WS sticky/Redis pubsub) |
| **Workers (`apps/worker`)** | Local Python worker process | Dedicated worker container(s) | Autoscaled worker pools (separate queues: `imports`, `events`, `ai`, `evals`) |
| **PostgreSQL 18 + pgvector** | Host PostgreSQL 18 (`postgresql-x64-18`) + WSL2/Docker pgvector | Managed PostgreSQL + pgvector | Multi-AZ Managed PostgreSQL + Read Replica + automated encrypted snapshots |
| **Redis** | WSL2/Docker Redis (`localhost:6379`) | Managed Redis | HA Managed Redis (cluster/sentinel) |
| **Object Storage** | MinIO container (`localhost:9000`) | Cloud S3 / GCS / R2 (private buckets) | Private encrypted buckets + lifecycle rules + cross-region backup |

---

## 2. Local Host Gap Noted in Phase 0

Per [PROJECT_AUDIT.md](file:///d:/go4guru/docs/PROJECT_AUDIT.md), **Docker**, **Redis**, and the **pgvector** extension in Windows PostgreSQL 18 are not yet installed on this workstation (though `WSL 2 Ubuntu` and `PostgreSQL 18` are present). Before Phase 1/3 runtime execution:
- Option A (Recommended): Install Docker Desktop (WSL2 backend) and run `infra/docker/docker-compose.yml` (`postgres:18-pgvector`, `redis:7`, `minio`).
- Option B: Run Redis + pgvector-enabled PostgreSQL inside the existing `WSL 2 Ubuntu` distro, or install `pgvector` binary for Windows PG 18 + Redis/Memurai.

---

## 3. CI/CD Pipeline & Promotion Gates

1. **Pull Request Gate:**
   - Frontend: `pnpm lint`, `tsc --noEmit`, unit/component tests, build check.
   - Backend: `ruff check`, `mypy` / `pyright`, `import-linter` boundary check, `pytest` unit + integration tests (ephemeral Postgres+Redis).
   - Security: `pip-audit`, `pnpm audit`, secret-scan (`gitleaks`), Dockerfile/IaC lint.
2. **Staging Deployment:**
   - Build immutable multi-stage Docker images tagged by Git SHA.
   - Run `alembic upgrade head` in pre-deploy job (backward-compatible expand/contract migrations only).
   - Run automated Playwright E2E smoke suite + AI Evaluation regression suite.
3. **Production Deployment & Rollback:**
   - Blue/green or rolling deploy with `/health/ready` probe checks.
   - Database migrations never drop columns/tables destructively in the same release as code changes (two-phase expand/contract) so instant image rollback remains safe.

---

## 4. Secrets, Backups & Observability

- **Secrets Management:** `.env.example` documents variable *names* only (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `LLM_API_KEY`, `ELEVENLABS_API_KEY`, `S3_BUCKET`, etc.). Staging/Prod inject secrets via cloud Secret Manager / KMS; never stored in repo or client `NEXT_PUBLIC_*` variables.
- **Backups & Restore Drills:** Automated daily PostgreSQL WAL/snapshots + encrypted off-site S3 retention; monthly automated restore drill into an isolated staging DB to verify RPO (< 15 min) and RTO (< 1 hr).
- **Observability:** Structured JSON logs (`correlation_id`, `tenant_id`, `user_id_hash`), OpenTelemetry distributed traces (Next.js → FastAPI → PostgreSQL/Redis/AI), Prometheus/Grafana or cloud dashboards monitoring API P95/5xx, DB pool saturation, worker dead-letter queue depth, WebSocket disconnects, and AI/Voice latency & error spikes with PagerDuty/Slack alerts.
