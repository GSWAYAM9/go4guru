# Project Audit (`docs/PROJECT_AUDIT.md`)

**Audit Date:** 2026-11-26  
**Workspace Audited:** `d:\go4guru`  
**Phase:** Phase 0 — Discovery and Foundation  
**Auditor:** Engineering Architecture & Platform Discovery Pass  

---

## 1. Executive Summary

The target workspace `d:\go4guru` is a **greenfield directory** created on `2026-11-26 19:18:41 IST` containing **0 files and 0 directories** prior to this Phase 0 audit. There is no existing source code, framework, database schema, authentication system, deployment configuration, environment file, test suite, or question-bank dataset inside `d:\go4guru`.

However, empirical filesystem inspection of the parent drive (`D:\`) identified **9 sibling educational PDF directories** (`D:\class-6` through `D:\class-12`, including `D:\class-8-socialscience` and `D:\class-10-english`) created between October and November 2026 containing **374 PDF files (450.79 MB)**. Inspection of representative PDFs across all 9 sibling directories reveals that they are **third-party proprietary ALLEN® Career Institute ("NCERT Questions with Solutions" / "NCERT Basics") documents**, not official open NCERT textbooks or licensed datasets, and contain mislabeled files, binary duplicates, DRM/permission flags, and raw LaTeX/citation artifacts (detailed in [DATA_ASSET_AUDIT.md](file:///d:/go4guru/docs/DATA_ASSET_AUDIT.md)).

No `.xlsx`, `.xls`, `.csv`, `.json`, or `.docx` datasets exist in `d:\go4guru` or `D:\class-*`.

---

## 2. Current Repository Structure

Prior to writing `docs/` in Phase 0:

```text
d:\go4guru\
└── (empty — 0 files, 0 bytes, no .git directory)
```

- **Version Control:** Not initialized (`git status` fails with `fatal: not a git repository`).
- **Package Managers / Lockfiles:** None (`package.json`, `pnpm-lock.yaml`, `package-lock.json`, `pyproject.toml`, `requirements.txt`, `uv.lock` do not exist).
- **Environment Files:** None (0 `.env*` files exist in `d:\go4guru`).

---

## 3. Host Machine Toolchain & Runtime Audit

Inspected read-only on Windows host:

| Component | Status | Observed Details | Implications for Platform |
| :--- | :--- | :--- | :--- |
| **OS** | Present | Windows | Local development & cross-platform scripts required |
| **Node.js** | Installed | `v22.16.0` (`C:\Program Files\nodejs\node.exe`) | Ready for Next.js / React / TypeScript frontend |
| **npm / pnpm** | Installed | `npm 10.9.2`, `pnpm 12.3.4` (`npx`, `corepack` present) | Recommended JS/TS monorepo manager: `pnpm` |
| **Git & GitHub CLI** | Installed | `git 2.52.0.windows.1`, `gh` CLI present | Ready for repo initialization and CI/CD integration |
| **Python** | Installed | `Python 3.12.10` (primary), `3.13` (64-bit), `3.10` (64-bit) via `py` | Python 3.12 already has `fastapi`, `uvicorn`, `pydantic`, `pandas`, `sympy`, `scipy`, `openai`, `groq`, `pytest`, `python-docx` globally; project MUST still isolate in a `.venv` |
| **PostgreSQL** | Running | `postgresql-x64-18` service (`Running`), `psql.exe` at `C:\Program Files\PostgreSQL\18\bin\psql.exe` (not on `PATH`) | Primary DB engine ready locally; **note:** `pgvector` extension files are NOT present in `share\extension` |
| **MySQL** | Running | `MySQL80` service (`Running`) | Unrelated to this project unless an existing data dump requires it; do not choose MySQL over PostgreSQL |
| **WSL 2** | Configured | Default distribution: `Ubuntu` (WSL 2; WSL 1 disabled) | Can host Redis and pgvector-enabled PostgreSQL if Docker Desktop is not installed |
| **Docker** | Missing | `docker` NOT_FOUND (`C:\Program Files\Docker` = `False`) | Containerized local stack (Postgres+pgvector, Redis, MinIO) requires Docker Desktop or WSL2 Docker Engine |
| **Redis** | Missing | `redis-server` NOT_FOUND natively on Windows | Needs WSL2/Docker container or managed Redis for queues, rate limiting, and classroom pub/sub |
| **uv** | Missing | `uv` NOT_FOUND | Can use `pip` + `venv` or install `uv` for deterministic Python lockfiles |
| **SQLite / Yarn** | Missing | `sqlite3` NOT_FOUND, `yarn` NOT_FOUND | Not needed (`PostgreSQL 18` + `pnpm` preferred) |

---

## 4. Existing Applications, Code, Data & Config Audit

| Domain | Current State in `d:\go4guru` | Gap / Risk |
| :--- | :--- | :--- |
| **Frontend Applications** | None | All role portals (Student, Teacher, Mentor, Parent, School Admin, Content Admin, Reviewer, Platform Admin) missing |
| **Backend API** | None | All REST and WebSocket endpoints missing |
| **Database & Migrations** | None (host Postgres 18 service runs, no app DB or schema created) | Full multi-domain PostgreSQL schema & Alembic migrations missing |
| **Authentication & RBAC** | None | Secure auth, JWT/sessions, MFA for privileged users, RBAC, tenant isolation, and parental consent flows missing |
| **Routes & UI Design System** | None | Shared design tokens, responsive layout shell, KaTeX math, whiteboard UI, accessibility baseline missing |
| **Integrations** | None | LLM provider abstraction, ElevenLabs voice adapter, OCR, S3/object storage, payment provider abstraction missing |
| **Curriculum & Content** | None in repo; 374 external proprietary PDFs in sibling `D:\class-*` | Must NOT ingest unlicensed third-party PDFs; need versioned curriculum seed + lawful/original content |
| **Question Bank & Excel Files** | None in `d:\go4guru` or `D:\class-*` | Canonical Question Bank schema, Excel staging/ingestion pipeline, and verified PYQ dataset missing |
| **Deployment & Observability** | None | Dockerfiles, `docker-compose`, CI/CD, secrets management, logging, tracing, metrics, and cost telemetry missing |
| **Tests** | None | Unit, integration, API, E2E, AI eval, security, tenant isolation, load, and accessibility suites missing |

---

## 5. Broken, Incomplete, or Risky Findings

Because `d:\go4guru` has no code yet, there is no broken codebase debt inside the workspace. However, **critical pre-implementation risks** exist in the surrounding environment:

1. **Third-Party Copyrighted Material in Sibling Folders (`D:\class-*`):** All sampled PDFs contain ALLEN® logos, watermarks, internal network paths, and promotional footers. Using these in production or RAG embeddings without written licensing creates severe legal/copyright liability.
2. **Mislabeled & Corrupted External PDFs:** E.g., `D:\class-9\The+French+Revolution+-+Exercise.pdf` actually contains Class 6 Maths Chapter 7 Fractions; 9 duplicate files waste space; 75 PDFs carry `/Encrypt` flags; Class 12 Maths Google Docs exports contain `[cite_start]` and broken LaTeX tokens.
3. **Missing Excel Question Bank Sources:** The prompt anticipates Excel question bank ingestion, but no `.xlsx`/`.xls`/`.csv` files are present in the workspace.
4. **Missing Infrastructure Dependencies Locally:** Redis, `pgvector`, object storage (MinIO/S3), and Docker are not yet installed/configured on the Windows host.
5. **No Source Control Yet:** `d:\go4guru` is not yet a git repository; initializing git with a strict `.gitignore` (blocking `.env*`, credentials, raw copyrighted PDFs, large binaries) is mandatory before writing application code.

---

## 6. Preservation vs. Refactoring / Foundation Strategy

### What Must Be Preserved
1. **External sibling directories (`D:\class-6` .. `D:\class-12`):** Never modify, rename, move, or delete the user's original files on `D:\`.
2. **Existing PostgreSQL 18 host service:** Preserve and leverage `postgresql-x64-18` (or run an isolated project database/cluster) without interfering with unrelated local databases or `MySQL80`.
3. **Existing Python 3.12 / Node 22 / pnpm 12 host runtimes:** Do not downgrade or break global installations; isolate project dependencies in `.venv` and `node_modules`.

### Recommended Foundation Actions (Phase 0 → Phase 1)
1. Initialize Git in `d:\go4guru` with a strict `.gitignore` and commit Phase 0 documentation first.
2. Adopt the Section 38 target stack (`Next.js + React + TypeScript` web app, `FastAPI + Python 3.12` modular monolith backend, `PostgreSQL 18 + pgvector`, `Redis`, `S3-compatible` object storage, `ARQ/Celery` worker).
3. Quarantine all external ALLEN® PDFs strictly outside production content/RAG pipelines unless explicit commercial licensing is provided; author lawful NCERT-aligned curriculum metadata + original/OER content and await user-supplied `.xlsx` datasets (or build & test the Excel importer using real user files once supplied, plus isolated test fixtures).
4. Resolve local Redis + `pgvector` availability (via Docker Desktop or WSL2 Ubuntu) before Phase 1 database setup.
