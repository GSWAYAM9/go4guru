---
trigger: model_decision
description: Rules for authentication, RBAC, MFA, multi-tenant isolation, child safety, DPDP privacy boundaries, secure uploads, and AI security.
---

# Security, Privacy & Child Safety Rules

Reference: [docs/SECURITY.md](../../docs/SECURITY.md), [docs/PRIVACY_AND_CHILD_SAFETY.md](../../docs/PRIVACY_AND_CHILD_SAFETY.md).

1. **Authentication & Privileged MFA:** Hash passwords with Argon2id; issue short-lived JWT access tokens + HTTP-only `Secure` `SameSite=Lax` rotating refresh cookies with token-reuse revocation. Enforce TOTP MFA on `platform_admin`, `school_admin`, `content_admin`, and `academic_reviewer`.
2. **Backend-Enforced RBAC & Tenant Isolation:** Every API endpoint MUST declare explicit permission dependencies and validate ownership/`tenant_id` in backend code. Never trust client-supplied `user_id`, `role`, `tenant_id`, `score`, or `timer`.
3. **Minor Consent & Parent Privacy Boundary:** Enforce minor age gate and verifiable `consents` / `parent_links` workflows. Linked parents access aggregated learning summaries only and MUST receive `403 Forbidden` on raw student AI chat endpoints (`ai_messages`).
4. **Upload & Input Hardening:** Validate uploads via magic bytes/MIME, strict size limits, EXIF stripping, formula-injection escaping (`=`, `+`, `-`, `@`), and malware scanning hook into private S3 buckets. Sanitize all Markdown/HTML before rendering; reject arbitrary external image URLs in AI/whiteboard schemas.
5. **AI Security & Zero Arbitrary Execution:** Never pass `eval()`, `exec()`, or raw SQL from LLM outputs. Enforce Redis rate limits and budget caps on AI/Voice/Homework endpoints; log safety incidents and provide distress helpline redirects when safety classifiers trigger.
6. **Secrets & Legal Claims:** Keep secrets out of git, logs, and frontend bundles. Do not claim DPDP legal compliance in UI/docs without formal legal counsel sign-off.
