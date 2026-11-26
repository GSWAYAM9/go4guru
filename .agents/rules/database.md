---
trigger: model_decision
description: Rules for PostgreSQL 18 schema design, Alembic migrations, pgvector indexes, tenant scoping, transactional outbox, and data retention.
---

# Database Rules (PostgreSQL 18 + Alembic + pgvector)

Reference: [docs/DATABASE_SCHEMA.md](../../docs/DATABASE_SCHEMA.md).

1. **PostgreSQL 18 & Normalized Modeling:** Use PostgreSQL 18 as the sole primary transactional store. Normalize relational entities with explicit `FOREIGN KEY`, `NOT NULL`, `UNIQUE`, and `CHECK` constraints. Use `JSONB` strictly for genuinely polymorphic attributes (exam pattern rules, whiteboard action payloads, structured lesson artifacts, mastery evidence)—never dump entire tables into generic JSON blobs.
2. **Identifiers, Timestamps & Soft Delete:** Use UUIDv7 / `gen_random_uuid()` primary keys, `timestamptz` (`created_at`, `updated_at`), and `deleted_at` soft deletes only where historical integrity or auditability requires it (preserving financial/audit/attempt records).
3. **Tenant & Query Indexing:** Every tenant-owned table MUST include `tenant_id` (or `organization_id`) with composite indexes leading on `tenant_id`. All repository queries for tenant data MUST require an explicit `tenant_id` parameter (and align with PostgreSQL RLS policies).
4. **Safe Migrations (Expand/Contract):** Author all DDL via Alembic migrations in `apps/api/alembic/`. Never drop columns/tables or rename live fields in a single deploy step; keep migrations backward-compatible for rolling zero-downtime rollbacks.
5. **Hybrid Search & Vector Indexes:** Keep `knowledge_chunks` embeddings (`vector(1536)`) and `tsvector` GIN indexes inside PostgreSQL alongside rights/curriculum metadata columns so filtering happens atomically before similarity ranking.
6. **Outbox & Audit Immutability:** Write `outbox_events` in the same ACID transaction as domain changes. Treat `audit_logs` as append-only (no `UPDATE`/`DELETE` endpoints or repository methods).
