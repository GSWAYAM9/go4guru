# Phase 9 — Examination Preparation Ecosystem (`docs/PHASE_9_EXAM_PREP_ARCHITECTURE.md`)

**Last Updated:** 2026-11-26  
**Scope:** Configurable, versioned examination preparation workflows for **CBSE Board**, **JEE Main**, **JEE Advanced**, and **NEET-UG** (`F-013`, `F-014`, `F-015`, `F-016`).

---

## 1. Versioned Examination Configuration & Scoring Rules

All exam configurations are stored in `exam_patterns` (`version_label`, `effective_year`, `is_active`, `rules_jsonb`) and evaluated deterministically via `apps/api/src/modules/assessment/exam_prep_logic.py` and `rule_engine.py`:

| Exam Track | Canonical Code | Versioned Seeded Blueprints | Scoring & Structural Rules | Target Pace |
| :--- | :--- | :--- | :--- | :---: |
| **CBSE Board** | `CBSE_BOARD` | `cbse-2026-v1`, `cbse-board-2026-blueprint-v2` | Sections A–E (`mcq_single`, `assertion_reason`, `short_answer`, `long_answer`, `case_study`), **no negative marking** (`+1/+2/+3/+4/+5`, `0` wrong) | `108s/Q` |
| **JEE Main** | `JEE_MAIN` | `jee-main-2026-v1`, `jee-main-2026-nta-v2` | Physics/Chemistry/Maths MCQ (`+4/-1`) + Numerical/Integer (`+4/-1`), configurable optional section `attempt_limit` (e.g. 5 of 10 or mandatory 5) | `144s/Q` |
| **JEE Advanced** | `JEE_ADVANCED` | `jee-adv-2026-v1`, `jee-adv-2026-p1-v2` | Multi-correct **`jee_adv_partial`** (`+4` all correct, `+3` for 3/4, `+2` for 2/3+, `+1` for 1/2+, `-2` if any wrong option selected, `0` unanswered), Single-correct (`+3/-1`), Integer/Numerical (`+4/0`), Match List (`+3/-1`) | `180s/Q` |
| **NEET-UG** | `NEET` | `neet-2026-v1`, `neet-ug-2026-nta-v2` | Physics, Chemistry, Biology (Botany + Zoology), `+4/-1`, configurable mandatory 180 Q or legacy Section A (35) + Section B (`attempt_limit=10` of 15) | `60s/Q` |

- **Server-Authoritative Enforcement:** All timed mocks and practice drills launch real `AssessmentAttempt` rows via `ExamAssessmentService`, locking `started_at`, `expires_at`, `grace_until`, and `Idempotency-Key` grading on the backend.

---

## 2. Strict PYQ Provenance Policy (Zero Fabrication)

Enforced in both `question_bank/public.py` (`_is_strictly_verified_pyq`) and `assessment/exam_prep_logic.py` (`validate_pyq_provenance`), plus defense-in-depth UI checks (`hasVerifiedPyqBadge`):

1. A question is labeled as a **Verified PYQ** ONLY when ALL of the following hold:
   - `question_provenance.is_pyq = true`
   - `question_versions.ai_generated = false`
   - `question_provenance.source_type` is NOT synthetic/AI-generated
   - `question_provenance.verification_status = 'verified'`
   - `question_provenance.verified_by` is present (non-null reviewer UUID)
   - `exam_name` is non-empty and matches the selected exam track (disambiguating `JEE Main` vs `JEE Advanced`)
   - `exam_year` is present and valid (`1980 <= exam_year <= 2035`)
2. Any question failing this gate is **never** returned when `verified_pyq_only=true`, never receives a PYQ badge, and is counted transparently in `unverified_pyq_excluded_count`.
3. **Answer Redaction:** `/api/v1/exam-prep/{exam_code}/questions` strictly omits `correct_answer_jsonb` and `QuestionOption.is_correct`. Detailed solutions at `/api/v1/exam-prep/attempts/{attempt_id}/solutions` return `403 SOLUTIONS_LOCKED_DURING_ATTEMPT` until the attempt is submitted/graded.

---

## 3. Honest Dataset & Syllabus Coverage Auditing

`compute_exam_coverage_audit` prevents exaggerated claims of complete exam coverage:

- `empty`: zero mapped syllabus chapters and zero published questions.
- `partial_unverified`: mapped chapters exist, but `0` chapters have `audit_verified = true`.
- `audited_partial`: some chapters are audited, or audited chapters still lack published questions.
- `audited_complete`: emitted **ONLY** when `included_chapters > 0`, `100%` of included chapters are marked `audit_verified = true`, AND `100%` have published questions in the Question Bank.

Every API response and the `/exams` header banner surface real audited counts and an explicit `coverage_disclaimer`.

---

## 4. Database Migration (`0010_phase9_exam_prep_ecosystem.py`)

Expands the existing PostgreSQL 18 schema cleanly (revising `0009_phase8_multitenant_institutions`):

- `exam_syllabus_chapters`: versioned chapter mappings per exam track (`weightage_pct`, `expected_questions`, `priority_tier`, `syllabus_status`, `audit_verified`, `audited_by`, `audited_at`).
- `exam_formula_sheets`: KaTeX formula revision cards (`formula_latex`, `variables_jsonb`, `when_to_use`, `common_pitfall`, `is_high_yield`, rights `source_id`/`license_id`).
- `exam_revision_plans`: persisted student revision plans (`target_exam_date`, `daily_minutes`, `focus_chapters_jsonb`, `schedule_jsonb`).
- Idempotently seeds canonical `exam_tracks`, v2 versioned `exam_patterns`, and RBAC permissions (`exam_prep:read`, `exam_prep:manage`).

---

## 5. API Surface (`/api/v1/exam-prep`) & Frontend (`/exams`)

- `GET /tracks` — All 4 exam tracks, versioned patterns, and honest coverage audits.
- `GET / POST /{exam_code}/syllabus` — Syllabus & chapter weightage matrix (write requires `exam_prep:manage` / `content_admin` / `academic_reviewer` / `school_admin` / `platform_admin`).
- `GET /{exam_code}/questions` — Answer-redacted explorer with `verified_pyq_only`, `exam_year`, `exam_session`, `difficulty`, `question_type`, `subject_id`, `chapter_id`, `topic_id`, `concept_id`.
- `POST /{exam_code}/practice` — Launches chapter-wise, topic-wise, or verified-PYQ drills.
- `POST /{exam_code}/mocks/generate` — Assembles & starts a server-timed full/section mock from a pinned `ExamPattern`.
- `GET /{exam_code}/analytics` — Accuracy, average speed vs target pace, pacing diagnosis, weak subjects/chapters/concepts, performance history, and deterministic improvement recommendations.
- `GET / POST /{exam_code}/formulas` — High-yield KaTeX formula revision cards.
- `GET / POST /{exam_code}/revision-plans` — Personalized weak-chapter-first day-by-day revision schedules.
- `GET /attempts/{attempt_id}/solutions` — Post-attempt detailed step-by-step solutions (strictly `403` while `in_progress`).
