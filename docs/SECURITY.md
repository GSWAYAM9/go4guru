# Security Architecture & Checklist (`docs/SECURITY.md`)

**Threat Model Scope:** Multi-tenant EdTech platform serving minors (Classes 6–12), teachers, parents, school admins, reviewers, and platform operators with AI orchestration, file uploads, exams, and billing.

---

## 1. Security Controls Matrix

| Domain | Required Control | Implementation Standard |
| :--- | :--- | :--- |
| **Transport & Edge** | HTTPS / WSS only, HSTS, TLS 1.2+, CSP, CORS strict allowlist | Enforced at reverse proxy/CDN & FastAPI middleware; zero wildcard CORS with credentials |
| **Authentication** | Argon2id password hashing, short-lived JWT access (10–15 min) + HTTP-only `Secure`/`SameSite=Lax` rotating refresh cookies | Refresh token hash stored in `sessions`; reuse detection revokes token family |
| **Privileged MFA** | TOTP MFA mandatory for `platform_admin`, `school_admin`, `content_admin`, `academic_reviewer` | Enforced in auth policy; recovery codes hashed |
| **RBAC & Tenant Isolation** | Deny-by-default endpoint permissions + mandatory `tenant_id` / ownership predicate in repository layer | PostgreSQL RLS + SQLAlchemy mandatory tenant filters; never trust client `user_id`/`tenant_id` |
| **Exam Integrity** | Server-authoritative timer (`started_at`, `expires_at`), server-side scoring, idempotent submission | Correct answers stripped from active attempt DTOs; client clock ignored |
| **Input & File Uploads** | Pydantic v2 strict schemas, HTML/Markdown XSS sanitization, private S3 pre-signed URLs, MIME/magic-byte validation, size caps, malware scan hook, EXIF strip | Uploaded Excel/Homework files never served from app domain or executed |
| **Encryption & Secrets** | Encryption at rest (RDS/volume + KMS for MFA secrets/tokens), TLS in transit; secrets in Vault/cloud secret manager | Zero secrets in git, client bundles, or logs; `.env*` gitignored |
| **Rate Limiting & Abuse** | Redis sliding-window limits by IP, user, tenant on Auth, AI, Voice, Homework, Search | Progressive backoff & lockout on auth brute force |
| **Audit Logging** | Append-only `audit_logs` on auth events, RBAC changes, rights approvals, grade overrides, billing, deletion | Correlation IDs (`X-Request-ID`) propagated end-to-end |
| **Supply Chain** | Dependabot/Renovate, `pip-audit`, `pnpm audit`, container Trivy scans, pinned lockfiles | Blocking CI gate on Critical/High CVEs |

---

## 2. AI-Specific Security Controls

1. **Prompt Injection Defense:** Strict structural separation between system instructions, retrieved curriculum chunks (wrapped as untrusted data blocks), and student input; pre/post moderation classifiers.
2. **Tool Permission Boundaries:** AI modules only invoke explicitly declared Python tools (`rag_retrieve`, `sympy_verify`, `pint_units`, `chem_balance`). AI **never** has shell access, raw SQL generation access, or arbitrary file I/O.
3. **Zero Arbitrary Code Execution:** Never run `eval()`, `exec()`, or LLM-generated JS/SVG `<script>` in backend or whiteboard. SymPy uses strict AST-whitelisted parsing with CPU/memory timeouts.
4. **PII Minimization:** `ContextResolver` strips emails, phone numbers, real names, school names, and addresses before calling any external LLM/TTS/OCR provider.

---

## 3. Pre-Production Security Verification Checklist

- [ ] Cross-tenant isolation integration tests pass across every tenant-scoped endpoint (Tenant A cannot read/write Tenant B).
- [ ] Horizontal & vertical privilege escalation test matrix passes across all 8 roles.
- [ ] Privileged accounts blocked without verified MFA.
- [ ] Active assessment endpoints verified not to leak `correct_answer` or solution payloads.
- [ ] Formula injection (`=CMD|...`), zip-bomb, and polyglot file upload tests rejected cleanly.
- [ ] Whiteboard XSS & `INSERT_IMAGE` SSRF/arbitrary-URL tests rejected by schema validator.
- [ ] Backup encryption & restore drill verified.
- [ ] Incident response runbook & key-rotation procedure tested.
