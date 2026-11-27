# Phase 7 & Phase 8: Tenant Model, Authorization Strategy & Child-Safety Boundaries

> **Scope:** Authoritative architectural documentation for Phase 7 (`F-031` Teacher, `F-032` Mentor, `F-004` Guardian Consent, `F-033` Parent Portal) and Phase 8 (`F-003` Institutional Multi-Tenancy, `F-036` Subscriptions & Entitlements).

---

## 1. Multi-Tenant Data Model (`tenant_id` Scoping)

Every institution-owned record carries an explicit non-null `tenant_id` foreign key pointing to `organizations.id` (with composite indexes leading on `tenant_id` per `AGENTS.md` §5 & §18):

| Table | Tenant Scoping Key | Parent / Hierarchy Links |
|---|---|---|
| `organizations` | `id` (canonical `tenant_id`) | Root tenant entity + `config_jsonb` |
| `schools` | `tenant_id` (`NOT NULL`) | `organizations.id`, unique `(tenant_id, code)` |
| `branches` | `tenant_id` (`NOT NULL`) | `schools.id`, unique `(school_id, code)` |
| `academic_years` | `tenant_id` (`NOT NULL`) | `schools.id`, unique `(school_id, label)` |
| `institution_batches` | `tenant_id` (`NOT NULL`) | `schools.id`, `branches.id`, `academic_years.id` |
| `institution_memberships` | `tenant_id` (`NOT NULL`) | `users.id`, `member_role ∈ {school_admin, teacher, mentor, student}` |
| `batch_enrollments` | `tenant_id` (`NOT NULL`) | `institution_batches.id`, `users.id` |
| `institution_assessments` | `tenant_id` (`NOT NULL`) | `schools.id`, optional `institution_batches.id` |
| `tenant_subscriptions` | `tenant_id` (`UNIQUE, NOT NULL`) | `subscription_plans.id` |
| `teacher_classes`, `teacher_sections`, `class_enrollments`, `teacher_assignments`, `assignment_submissions` | `tenant_id` (nullable for solo educators, populated for institutional teachers) | Scoped to owning teacher and tenant |
| `mentor_assignments`, `mentor_goals`, `mentor_sessions`, `mentor_follow_ups` | `tenant_id` | Scoped to assigned mentor and tenant |

Database migrations:
- `apps/api/alembic/versions/0008_phase7_educator_parent.py`
- `apps/api/alembic/versions/0009_phase8_multitenant_institutions.py`

---

## 2. Backend Authorization & Cross-Tenant Isolation Strategy

Frontend filtering is **never** relied upon for security. Every backend endpoint enforces three layers:

1. **Deny-by-Default RBAC + Privileged MFA (`src/core/auth_context.py`)**:
   - `school_admin` and `platform_admin` MUST complete TOTP MFA verification (`mfa_verified = true`) before any tenant or billing endpoint executes.
   - Fine-grained permissions (`teacher:manage_classes`, `teacher:grade_submissions`, `teacher:view_analytics`, `mentor:manage_students`, `mentor:view_analytics`, `parent:manage_links`, `parent:view_summaries`, `org:manage_tenant`, `org:manage_staff`, `org:manage_enrollments`, `org:view_reports`, `billing:manage_subscription`) are checked server-side on every route.

2. **Tenant Boundary Enforcement (`src/modules/organization/logic.py` + `service.py`)**:
   - `is_tenant_access_allowed(...)` verifies that every non-`platform_admin` caller matches `org_id` via their verified JWT `tenant_id` claim OR an active row in `institution_memberships`. Any mismatch raises `403 CROSS_TENANT_FORBIDDEN`.
   - Every SQL query filters explicitly with `.where(Entity.tenant_id == org_id)`.
   - Every child foreign key (`school_id`, `branch_id`, `academic_year_id`, `batch_id`) passed in request bodies is validated via `is_resource_in_tenant(...)` before writes or reads, blocking cross-tenant foreign-key injection with `403 CROSS_TENANT_RESOURCE_FORBIDDEN`.

3. **Educator & Mentor Student-Scope Isolation**:
   - **Teachers** (`src/modules/teacher/service.py`): `_require_class_access` verifies class ownership (or same-tenant `school_admin`). `_assert_teacher_authorized_for_student` verifies active `class_enrollments` membership before returning student analytics; unauthorized lookups return `403 TEACHER_STUDENT_FORBIDDEN`.
   - **Mentors** (`src/modules/mentor/service.py`): `_assert_mentor_assigned_to_student` verifies an active `mentor_assignments` record before returning progress reviews or writing goals/sessions/follow-ups; unauthorized lookups return `403 MENTOR_STUDENT_FORBIDDEN`.

---

## 3. Child Safety & Parent Privacy Boundary (`F-004`, `F-033`)

- **Verifiable Consent Gate**: Creating a guardian link (`POST /api/v1/parent/links`) generates a salted SHA-256 hashed 8-character verification code and stores `consent_status = 'pending'`. Calling `GET /api/v1/parent/students/{id}/summary` before verification returns `403 GUARDIAN_CONSENT_REQUIRED`.
- **Hard Raw-Transcript Prohibition**:
  - `sanitize_parent_privacy_settings()` unconditionally locks `allow_raw_ai_transcripts = False` even if a client submits `true`.
  - `/api/v1/parent/students/{id}/summary` aggregates ONLY privacy-preserving metrics (practice accuracy, mastery average, weak concept IDs/bands, revision card counts, homework submission counts, upcoming assignments, and parent goals) through public module contracts.
  - Parent accounts do NOT hold AI tutor or homework permissions and receive `403` on `/api/v1/ai/*` and `/api/v1/homework/*`.

---

## 4. Subscription & Entitlement Integration (`F-036`)

- Canonical plans (`school_starter`, `school_growth`, `school_enterprise`) define `max_students`, `max_teachers`, `max_branches`, and `entitlements_jsonb`.
- `billing.public.assert_tenant_quota_available(...)` is called deterministically before adding branches, teachers, or students (`402 ENTITLEMENT_QUOTA_EXCEEDED` when subscription status is not `active`/`trial` or when quota is reached).
- Billing routes (`/api/v1/billing/tenants/{tenant_id}/subscription`) enforce the same cross-tenant `403` boundary.

---

## 5. Verification Coverage

- **Pure-Stdlib Python Unit Tests (`apps/api/tests/unit/test_phase7_phase8_logic.py`)**: Tests cross-tenant isolation rules, resource boundary checks, consent code hashing/verification, parent privacy lock, Teacher Override bounds, CSV formula-injection neutralization, and subscription quota enforcement.
- **PostgreSQL 18 Integration Tests**:
  - `apps/api/tests/integration/test_phase7_educator_parent_pg.py`
  - `apps/api/tests/integration/test_phase8_multitenant_pg.py` (exhaustive Tenant B → Tenant A `403` isolation matrix + cross-tenant FK injection block).
- **Frontend Unit & Component Tests**:
  - `apps/web/src/lib/ecosystem-helpers.test.ts` (`node:test`)
  - `apps/web/tests/phase7.test.tsx` & `apps/web/tests/phase8.test.tsx` (Vitest + Testing Library).
