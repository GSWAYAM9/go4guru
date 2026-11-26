# API Specification (`docs/API_SPECIFICATION.md`)

**Base URL:** `/api/v1` (REST) | `/ws/v1` (WebSockets)  
**Documentation:** Auto-generated OpenAPI 3.1 (`/api/v1/openapi.json`, disabled or auth-gated in production if desired)  
**Format:** JSON (`application/json`, `multipart/form-data` only for controlled pre-signed/upload handshakes, SSE/WS for streaming).

---

## 1. Global API Conventions

- **Versioning:** URI path prefix `/api/v1/...`. Breaking schema changes increment to `/api/v2/...`.
- **Standard Error Envelope:**
  ```json
  {
    "error": {
      "code": "ASSESSMENT_TIME_EXPIRED",
      "message": "The submission window for this assessment has closed.",
      "details": {},
      "request_id": "req_01J..."
    }
  }
  ```
- **Pagination:** Cursor-based (`cursor`, `limit <= 100`) for large feeds/question banks; explicit offset allowed on admin tables.
- **Idempotency:** Critical mutations (`POST /assessments/{attempt_id}/submit`, `POST /imports`, `POST /billing/webhooks/*`) require `Idempotency-Key` header or unique client key.
- **Rate Limiting:** Redis sliding-window limits per IP, per User, and per Tenant (stricter limits on `/auth/*`, `/ai/*`, `/voice/*`, `/homework/*`).
- **Authorization:** Every endpoint declares required permission + tenant/ownership resolver. Zero trust in client-supplied `user_id`, `role`, `score`, or `timer`.

---

## 2. API Domain Map

| Domain | Prefix | Key Endpoints | Primary Roles |
| :--- | :--- | :--- | :--- |
| **Health** | `/health` | `GET /health/live`, `GET /health/ready` | Public / Infra |
| **Auth** | `/api/v1/auth` | `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `POST /mfa/setup`, `POST /mfa/verify`, `GET /sessions`, `DELETE /sessions/{id}` | All |
| **Users** | `/api/v1/users` | `GET /me`, `PATCH /me/profile`, `PATCH /me/languages`, `POST /me/deletion-request`, `GET /me/data-export` | All |
| **Parents & Consent** | `/api/v1/parents` | `POST /links/invite`, `POST /consents/{token}/verify`, `GET /children`, `GET /children/{id}/summary`, `PATCH /children/{id}/privacy`, `POST /consents/{id}/withdraw` | Parent, Student |
| **Curriculum** | `/api/v1/curriculum` | `GET /boards`, `GET /versions`, `GET /tree`, `GET /chapters/{id}`, `GET /concepts/{id}`, `POST/PATCH /admin/*` | All (read), Content Admin (write) |
| **Content CMS** | `/api/v1/content` | `GET /items`, `GET /items/{id}`, `POST /items`, `POST /items/{id}/versions`, `POST /versions/{id}/submit-review`, `POST /versions/{id}/review`, `POST /items/{id}/publish` | Student (published), Content Admin, Reviewer |
| **Question Bank** | `/api/v1/questions` | `GET /` (search/filter), `GET /{id}` (redacted keys for students), `POST /`, `PATCH /{id}`, `POST /{id}/verify-pyq`, `POST /{id}/review` | Content Admin, Reviewer, Teacher |
| **Excel Imports** | `/api/v1/imports` | `POST /upload`, `GET /{batch_id}`, `POST /{batch_id}/mapping`, `POST /{batch_id}/validate`, `GET /{batch_id}/preview`, `POST /{batch_id}/commit`, `POST /{batch_id}/rollback`, `GET /{batch_id}/report` | Content Admin, Reviewer |
| **Practice & Notes** | `/api/v1/practice` | `POST /sessions`, `POST /attempts`, `POST /attempts/{id}/hint`, `GET /notes`, `POST/PATCH/DELETE /notes/{id}`, `POST/DELETE /bookmarks/{question_id}` | Student |
| **Quizzes** | `/api/v1/quizzes` | `POST /generate`, `GET /{id}`, `POST /{id}/start`, `GET /daily` | Student, Teacher |
| **Assessments** | `/api/v1/assessments` | `GET /tests`, `POST /tests/{id}/attempts`, `GET /attempts/{id}/state`, `PUT /attempts/{id}/answers` (autosave), `POST /attempts/{id}/submit`, `GET /attempts/{id}/result`, `POST /teacher/tests` | Student, Teacher, School Admin |
| **Exam Tracks** | `/api/v1/exams` | `GET /{track}/patterns` (`cbse\|jee-main\|jee-advanced\|neet`), `GET /{track}/pyqs`, `GET /{track}/mock-tests` | Student |
| **AI Tutor** | `/api/v1/ai` | `POST /sessions`, `GET /sessions`, `GET /sessions/{id}/messages`, `POST /sessions/{id}/turns` (streaming SSE/JSON), `POST /sessions/{id}/mode` | Student (own only; Parent blocked) |
| **AI Quality Evals** | `/api/v1/ai-evals` | `POST /runs`, `GET /runs/{id}`, `GET /review-queue`, `POST /review-queue/{id}/decision` | Academic Reviewer, Platform Admin |
| **AI Classroom** | `/api/v1/classroom` & `WS /ws/v1/classroom/{id}` | `POST /lessons/generate`, `POST /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/control` (`pause\|resume\|seek\|language\|speed`), `POST /sessions/{id}/doubt`, `POST /sessions/{id}/checkpoint` | Student |
| **Whiteboard** | `/api/v1/whiteboard` | `GET /sessions/{id}/events`, `POST /sessions/{id}/events`, `GET /sessions/{id}/snapshots/latest`, `POST /sessions/{id}/export` | Student, Teacher |
| **Voice & Languages** | `/api/v1/voice`, `/api/v1/languages` | `GET /languages/capabilities`, `GET /voice/voices`, `POST /voice/tts`, `POST /voice/stt` | All |
| **Adaptive & Revision** | `/api/v1/learning`, `/api/v1/revision` | `GET /mastery`, `GET /weak-concepts`, `GET /recommendations`, `GET /flashcards/due`, `POST /flashcards/{id}/review`, `GET/POST /study-plans` | Student, Mentor, Teacher |
| **Homework AI** | `/api/v1/homework` | `POST /submissions/presign`, `POST /submissions/{id}/finalize`, `GET /submissions/{id}`, `POST /submissions/{id}/unlock-hint`, `POST /submissions/{id}/retry` | Student, Teacher |
| **Teacher** | `/api/v1/teachers` | `GET /classes`, `POST /assignments`, `GET /assignments/{id}/submissions`, `POST /submissions/{id}/grade` (supports AI draft + override), `GET /classes/{id}/analytics`, `POST /reports/export` | Teacher |
| **Mentor** | `/api/v1/mentors` | `GET /mentees`, `POST /mentees/{id}/sessions`, `POST /mentees/{id}/goals`, `POST /mentees/{id}/tasks`, `GET /alerts` | Mentor |
| **Institutions** | `/api/v1/institutions` | `POST/GET /schools`, `POST/GET /branches`, `POST/GET /academic-years`, `POST/GET /classes`, `POST/GET /sections`, `POST /enrollments/bulk`, `GET /analytics` | School Admin, Platform Admin |
| **Analytics** | `/api/v1/analytics` | `GET /student/overview`, `GET /teacher/cohort`, `GET /institution/overview`, `GET /platform/learning-metrics` | Role-scoped |
| **Notifications** | `/api/v1/notifications` | `GET /`, `PATCH /{id}/read`, `PUT /preferences` | All |
| **Billing & Economics** | `/api/v1/billing`, `/api/v1/admin/economics` | `GET /plans`, `GET /subscription`, `POST /checkout`, `POST /webhooks/{provider}`, `GET /invoices`, `GET /admin/economics/unit-costs` | Student/Parent/School Admin, Platform Admin |
| **Safety & Admin** | `/api/v1/safety`, `/api/v1/admin` | `POST /safety/report`, `GET /admin/moderation`, `GET /admin/audit-logs`, `GET/PUT /admin/feature-flags`, `GET /admin/health` | Student/All (report), Platform Admin |
