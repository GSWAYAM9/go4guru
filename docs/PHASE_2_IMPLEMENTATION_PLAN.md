# Phase 2 Implementation Plan & Acceptance Checklist — Quiz & Assessment Engine

> **Status:** Completed & Verified (`Phase 2`)  
> **Scope:** Implements `F-011` (Configurable Quiz Engine), `F-012` (Server-Authoritative Assessment/Exam Engine), `F-013` (CBSE Board Prep initial configurable workflows + CBSE/JEE Main/JEE Advanced/NEET extensible pattern rules), and `F-034` (Learning Analytics & Transactional Outbox Consumer).  
> **Gate Rule:** Phase 3 does NOT start until every item in Section 4 (Acceptance Checklist) is verified and tested.

---

## 1. Non-Negotiable Architecture & Extensibility Principles

1. **Zero Hardcoded Exam Rules:** Marking schemes, negative marking, partial subset marking (`+4/+3/+2/+1/0/-2`), optional section attempt caps (e.g., `"attempt any 5 of 10"`), durations, grace periods, and shuffle policies live in versioned `exam_patterns.rules_jsonb` (or configurable `test_sections.marking_rule_jsonb` / `quizzes.config_jsonb`).
2. **Server Authority:**
   - `started_at`, `expires_at`, and `grace_until` are calculated strictly in UTC on the server.
   - Scores, negative marks, partial marks, and correctness are calculated exclusively on the server against pinned `question_version_id`s. Any client-supplied score or clock fields are ignored.
   - Active attempt APIs (`start`, `state`, `autosave`) strictly redact `correct_answer_jsonb`, `is_correct`, and `solutions`.
   - `/result` is locked (`403`) until the attempt is submitted or auto-submitted.
3. **Concurrency & Idempotency:**
   - `POST /api/v1/assessments/attempts/{attempt_id}/submit` acquires a PostgreSQL row-level `FOR UPDATE` lock on `assessment_attempts` and honors `Idempotency-Key`, ensuring concurrent duplicate submissions return one identical scored result and emit at most one `outbox_events` record.
   - Submissions arriving after `expires_at + grace_seconds` reject late client payload writes with `422 ASSESSMENT_TIME_EXPIRED`.

---

## 2. Work Breakdown & Dependencies

| Stream | Deliverables | Dependencies |
|---|---|---|
| **2A. Alembic Migration (`0003_phase2_assessment_analytics.py`)** | `exam_patterns`, `quizzes`, `quiz_questions`, `tests`, `test_sections`, `test_questions`, `assessment_attempts`, `attempt_answers`, `processed_event_ids`, `learning_events`, `analytics_snapshots`; Phase 2 RBAC permissions & versioned exam pattern seeds (`CBSE_BOARD`, `JEE_MAIN`, `JEE_ADVANCED`, `NEET`) | Phase 1 `0002_phase1_core` |
| **2B. Exam Rule Engine & QBank Contracts** | Pure deterministic rule evaluator (`assessment/rule_engine.py`: standard, negative marking, JEE Adv partial subset credit, optional section `attempt_limit` cap) + `question_bank.public` question selector (chapter/topic/concept/difficulty mix/type mix/seed) | 2A |
| **2C. Quiz Engine & Exam Templates APIs** | `/api/v1/quizzes/*` (12 quiz types, chapter/topic/diagnostic/timed/teacher quizzes, dynamic selection & seeded randomization) & `/api/v1/assessments/*` (`exam-patterns`, `tests`, `sections`, `questions`, publish) | 2A, 2B |
| **2D. Assessment Session Lifecycle APIs** | Start attempt, `/state` recovery + remaining timer, `/answers` autosave + mark-for-review + visited tracking, `/submit` row-locked idempotent submission + expiry enforcement, `/result` detailed review, `/attempts` history | 2C |
| **2E. Analytics & Transactional Outbox Projection** | `analytics` module (`processed_event_ids`, `learning_events`, `analytics_snapshots`, idempotent `process_outbox_learning_events`, `GET /api/v1/analytics/student/overview`, `GET /api/v1/analytics/cohort`) | 2A, 2D |
| **2F. Next.js Web UI** | `/quizzes` (generator/presets/teacher builder), `/assessments` (template lobby & history), `/assessments/[attemptId]` (live CBT/quiz runner: live countdown, question palette, mark for review, autosave + reload recovery), `/assessments/[attemptId]/result` (score breakdown, negative marking, answer review), `/analytics` | 2C, 2D, 2E |
| **2G. Comprehensive Test Gate** | Unit tests (rule engine edge cases, partial credit, optional limits), Real PG 18 integration tests (timing/expiry, recovery, duplicate submit, `asyncio.gather` concurrency race, negative marking, RBAC/owner 403), Vitest, Playwright full-stack browser E2E | All above |

---

## 3. Configurable `ExamPatternRules` JSON Structure

```json
{
  "duration_seconds": 1800,
  "grace_seconds": 30,
  "shuffle_questions": true,
  "shuffle_options": false,
  "retake_policy": { "max_attempts": 3, "cooldown_minutes": 0 },
  "sections": [
    {
      "code": "SEC-A",
      "name": "Single Choice / Concept Check",
      "question_count": 5,
      "attempt_limit": null,
      "allowed_question_types": ["mcq_single", "assertion_reason"],
      "difficulty_distribution": { "easy": 2, "medium": 2, "hard": 1 },
      "question_type_distribution": {},
      "scoring": {
        "mode": "standard",
        "correct_marks": 4.0,
        "wrong_marks": -1.0,
        "unanswered_marks": 0.0,
        "partial_credit_per_correct_option": 0.0
      }
    }
  ]
}
```

---

## 4. Phase 2 Acceptance Checklist (Must Pass Before Phase 3)

- [x] **AC-2.01 Configurable Rules:** Versioned `exam_patterns` created via DB/API for CBSE, JEE Main, JEE Advanced, and NEET patterns; zero hardcoded exam scoring constants in routes or UI.
- [x] **AC-2.02 Quiz Selection & Randomization:** Dynamic quiz builder generates exact requested question count, respects difficulty/question-type distributions, supports chapter/topic/diagnostic/timed/teacher quizzes, and uses deterministic seed ordering.
- [x] **AC-2.03 Teacher/Admin vs Student RBAC:** Only authorized roles (`teacher`, `content_admin`, `platform_admin`) can create official exam templates/patterns; students blocked (`403`) from admin/pattern management and blocked (`404`/`403`) from viewing/modifying another student's attempt/state/result.
- [x] **AC-2.04 Answer Confidentiality:** Active `start`, `state`, and `autosave` responses omit `correct_answer_jsonb`, `is_correct`, and `solutions`; `/result` returns `403` while attempt is `in_progress`.
- [x] **AC-2.05 Server Timer & Expiry Enforcement:** Submitting after `expires_at + grace_seconds` fails with `422 ASSESSMENT_TIME_EXPIRED`; client-tampered timestamps or scores are ignored.
- [x] **AC-2.06 Autosave & Recovery:** Saving responses, visited flags, `is_marked_for_review`, and `time_spent_seconds` persists to PostgreSQL and restores completely upon reload (`/state`).
- [x] **AC-2.07 Concurrent & Idempotent Submission:** Concurrent parallel submit calls (`Idempotency-Key` identical or distinct) produce exactly one scored attempt, zero double-counting, and one `outbox_events` row.
- [x] **AC-2.08 Negative & Partial Scoring:** Positive, negative, unanswered, JEE Advanced partial subset marking, and optional `attempt_limit` rules pass unit & integration verification.
- [x] **AC-2.09 Analytics & Idempotent Outbox:** Outbox replay across duplicate triggers never double-increments `analytics_snapshots`; real student accuracy/topic/attempt analytics display cleanly in UI with loading/empty/error states.
- [x] **AC-2.10 Verification & Docs:** Backend (`ruff`, `mypy`, `lint-imports`, `pytest` unit + PG18 concurrency/integration), Frontend (`build`, `lint`, `typecheck`, `vitest`), and Playwright browser E2E (`quiz -> autosave -> reload recovery -> mark for review -> submit -> result review -> analytics`) all pass after final edit; `MASTER_FEATURE_CHECKLIST.md` and `IMPLEMENTATION_STATUS.md` updated honestly.
