# Phase 5 Implementation Plan & Acceptance Checklist — Personalized Adaptive Learning & Revision Engine

> **Status:** COMPLETED & VERIFIED (`Phase 5`)  
> **Scope:** Implements `F-026` (Concept Mastery & Adaptive Engine), `F-027` (Spaced Repetition Flashcards & Missed-Question Revision), `F-028` (Personalized Study Plans & Revision Analytics), and in-app revision alerting (`F-035` foundation).  
> **Algorithm Reference:** [docs/PHASE_5_ALGORITHM_AND_LIMITATIONS.md](PHASE_5_ALGORITHM_AND_LIMITATIONS.md)

---

## 1. Work Breakdown & Dependencies

| Stream | Deliverables | Dependencies |
|---|---|---|
| **5A. Migration (`0006_phase5_adaptive_revision`)** | `student_concept_mastery`, `student_misconceptions`, `learning_paths`, `learning_path_items`, `flashcards`, `student_flashcards`, `flashcard_reviews`, `study_plans`, `study_plan_items`, `student_notifications`, and Phase 5 RBAC permissions | `0005_phase4_classroom` |
| **5B. Cross-Module Read Contracts** | Expose attempt evidence & question metadata snapshots on `assessment.public`, `question_bank.public`, and concept prerequisite graph helpers on `curriculum.public` (strict `import-linter` compliance) | Phase 1–2 tables |
| **5C. Multi-Signal Concept Mastery & Adaptive Engine (`learning/`)** | Configurable `AdaptiveMasteryConfig`, transparent 6-signal mastery calculator (difficulty-weighted accuracy, hint-independent solving ratio, time-decay + multi-day retention, question-type/context transfer, chronological improvement slope, unresolved misconception penalty), prerequisite-aware remediation, advancement unlocking, and explainable recommendations (`/api/v1/learning/*`) | 5A, 5B |
| **5D. Spaced Repetition, Flashcards, Missed-Q Auto-Cards, Study Plans & Notifications (`revision/`, `notifications/`)** | Multi-modal flashcards (`concept`, `formula`, `vocabulary`, `missed_question`), SM-2+ configurable scheduler, concept-mastery priority queue, missed-question revision sync, personalized study planner, revision analytics (`/api/v1/revision/*`), and in-app revision alerts (`/api/v1/notifications/*`) | 5A, 5B, 5C |
| **5E. Frontend UI (`/adaptive` & `/revision`)** | Student Concept Mastery heatmap & transparent signal breakdown drawer, Misconceptions & Remediation Path view, Flashcard Review Deck (`concept`/`formula`/`vocabulary`/`missed_question` + 0–5 SM-2+ rating), Missed-Question sync, Study Planner builder/tracker, and Revision Analytics | 5C, 5D |
| **5F. Phase 5 Verification Gate** | Unit tests (mastery signals, hint penalty, independent solve, decay, transfer, improvement slope, remediation vs advancement, SM-2+ scheduling), PG18 integration tests (repeated attempts, missed-question flashcard generation, misconception resolution, prioritization, cross-student isolation), Vitest (`phase5.test.tsx`), and Playwright Chromium E2E (`phase5.spec.ts`) | All above |

---

## 2. Phase 5 Acceptance Checklist

- [x] **AC-5.01 Transparent Multi-Signal Mastery Algorithm:** Mastery is computed cleanly from weighted accuracy, difficulty multiplier, independent vs hint-penalized solving, recency/multi-day retention, transfer across types/contexts, improvement trend, and misconception penalties—never from raw accuracy or time spent in app.
- [x] **AC-5.02 Evidence, Misconceptions & Prerequisite Remediation:** Records attempt evidence summaries, tracks/resolves student misconceptions, traverses prerequisite concepts to recommend prerequisite remediation before target remediation, and unlocks advancement recommendations once proficient.
- [x] **AC-5.03 Multi-Modal Flashcards & Missed-Question Sync:** Supports `concept`, `formula` (KaTeX), `vocabulary`, and auto-generated `missed_question` cards from wrong practice/assessment attempts.
- [x] **AC-5.04 SM-2+ Spaced Repetition & Prioritization:** Schedules intervals, updates ease factors and lapse counters on quality ratings `0–5`, and orders due decks by urgency, overdue decay, low mastery, and missed-question weight.
- [x] **AC-5.05 Personalized Study Plans & Revision Analytics:** Generates time-budgeted actionable study plans linking due revisions and weak concepts, tracks completion/skip states, computes real DB revision analytics, and issues in-app due-revision alerts.
- [x] **AC-5.06 Full Test & E2E Gate:** Unit (`test_phase5_adaptive_and_sm2.py`), PG18 integration (`test_phase5_adaptive_revision_pg.py`), Vitest (`phase5.test.tsx`), `next build` (19 routes), and Playwright Chromium E2E (5/5 incl. `phase5.spec.ts`) pass after final edit.
