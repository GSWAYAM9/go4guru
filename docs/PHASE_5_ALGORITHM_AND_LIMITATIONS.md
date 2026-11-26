# Phase 5 Adaptive Mastery & Spaced Repetition Algorithm Specification & Limitations

> **Module Owners:** `apps/api/src/modules/learning/adaptive_engine.py`, `apps/api/src/modules/revision/scheduler.py`  
> **Principles:** Transparent, deterministic, configurable via `AdaptiveMasteryConfig` & `SpacedRepetitionConfig`, testable across boundary conditions, and honest about cold-start/empirical calibration limits.

---

## 1. Multi-Signal Concept Mastery Formula (`0.0 – 100.0`)

Let a student have chronological attempt evidence items $e_1, \dots, e_n$ mapped to concept $C$ (across guided practice sessions and server-graded quizzes/assessments). Time-spent duration alone NEVER grants positive mastery.

### 1.1 Difficulty Multiplier $d_i$
- `easy`: $0.80$
- `medium`: $1.00$
- `hard`: $1.25$
- `olympiad` / `advanced`: $1.40$

### 1.2 Independent Attempt Credit & Hint Penalty
Each attempt $e_i$ receives an independence weight $u_i \in [0.25, 1.00]$ when correct (`is_correct = true`) and $0.0$ when incorrect:
- If `hints_used_count == 0`: $u_i = 1.00$ (full independent mastery credit).
- If `hints_used_count > 0`: $u_i = \max(0.25,\; 1.00 - 0.25 \cdot \text{hints\_used\_count})$.
- We also track `independent_solve_ratio`: fraction of correct attempts solved with zero hints ($\in [0, 1]$).

### 1.3 Difficulty-Weighted Independent Accuracy ($S_{\text{acc}} \in [0, 1]$)
$$S_{\text{acc}} = \frac{\sum_{i=1}^n d_i \cdot u_i}{\sum_{i=1}^n d_i}$$
Notice that answering only `easy` questions with multiple hints yields a strictly lower $S_{\text{acc}}$ than solving `medium`/`hard` questions independently.

### 1.4 Retention & Multi-Day Spacing Signal ($S_{\text{ret}} \in [0, 1]$)
Let $\Delta t_{\text{days}}$ be elapsed days since the student's most recent successful independent attempt on concept $C$ (half-life $H = 21.0$ days, $\lambda = \ln(2) / H$):
$$\text{recency\_decay} = \exp\big(-\lambda \cdot \max(0,\; \Delta t_{\text{days}})\big)$$
Plus a discrete **spacing bonus** when correct attempts span multiple distinct UTC calendar days (`min(0.15, (distinct_correct_days - 1) * 0.05)`):
$$S_{\text{ret}} = \min(1.0,\; 0.85 \cdot \text{recency\_decay} + \text{spacing\_bonus})$$

### 1.5 Transfer Across Formats & Assessment Contexts ($S_{\text{xfer}} \in [0, 1]$)
Measures whether the learner demonstrates understanding beyond a single question format or untimed practice mode:
- Distinct question types solved correctly (e.g., `mcq_single`, `numerical`, `integer`, `subjective`), capped at 2 for full variety (`type_factor = min(1.0, correct_qtypes / 2)`).
- Assessment context validation (`context_factor = 1.0` if validated in both `practice` and timed `assessment`/`quiz`, `0.65` if verified in one context only, `0.0` if zero correct).
$$S_{\text{xfer}} = 0.5 \cdot \text{type\_factor} + 0.5 \cdot \text{context\_factor}$$

### 1.6 Improvement Trajectory ($S_{\text{imp}} \in [0, 1]$)
For $n \ge 2$, split chronological attempts into earlier half ($A_{\text{prior}}$ weighted correctness rate) and recent half ($A_{\text{recent}}$):
$$\Delta = A_{\text{recent}} - A_{\text{prior}}, \quad S_{\text{imp}} = \operatorname{clamp}(0.5 + 0.5 \cdot \Delta,\; 0.0,\; 1.0)$$
For $n < 2$, $S_{\text{imp}} = 0.5$ (neutral baseline).

### 1.7 Evidence Volume Damping & Misconception Penalty ($P_{\text{misc}}$)
To avoid jumping to `100%` after 1 lucky guess:
$$\text{confidence} = \min\Big(1.0,\; \frac{n}{5.0}\Big)$$
Unresolved misconceptions (`student_misconceptions.resolved_at IS NULL`) deduct:
$$\text{low} = 4.0, \quad \text{medium} = 8.0, \quad \text{high} = 14.0 \quad (\text{capped at } 28.0)$$
Final concept mastery score (`0.0 – 100.0`):
$$\text{raw\_composite} = 100 \cdot \big(0.45 S_{\text{acc}} + 0.20 S_{\text{ret}} + 0.15 S_{\text{xfer}} + 0.10 S_{\text{imp}} + 0.10 \cdot \text{indep\_ratio}\big)$$
$$\text{mastery\_score} = \operatorname{clamp}\big(\text{raw\_composite} \cdot (0.55 + 0.45 \cdot \text{confidence}) - P_{\text{misc}},\; 0.0,\; 100.0\big)$$

### 1.8 Mastery Bands
- `< 40.0`: `novice`
- `40.0 – 59.99`: `developing` (Weak / Needs Remediation)
- `60.0 – 79.99`: `proficient`
- `>= 80.0` (with `confidence >= 0.6` and `indep_ratio >= 0.65`): `mastered` (Advancement Unlocked)

---

## 2. Remediation vs. Advancement Logic
1. **Prerequisite Check First:** For every weak concept ($< 60.0$ or unresolved high misconception or decaying retention $< 0.65$), inspect prerequisite edges (`concept_prerequisites`). If a prerequisite concept also scores `< 60.0`, prioritize **`remediate_prerequisite`** before returning to the target concept.
2. **Misconception & Missed-Question Repair:** Concepts with wrong attempts link directly to `missed_question` flashcards and targeted remedial practice (`remediate_concept`).
3. **Advancement:** Mastered concepts (`>= 80.0` + high independence) unlock dependent downstream concepts (`advance_downstream`) or `hard`/exam-pattern challenge sets (`advance_challenge`).

---

## 3. SM-2+ Spaced Repetition Scheduling
For quality rating $q \in \{0, 1, 2, 3, 4, 5\}$ (`0–2` = lapse/forgot, `3` = hard recall, `4` = good recall, `5` = effortless):
- Update Ease Factor ($EF$, default `2.50`, floor `1.30`):
  $$EF' = \max\big(1.30,\; EF + (0.1 - (5 - q)(0.08 + (5 - q) \cdot 0.02))\big)$$
- If $q < 3$: reset `repetitions = 0`, `interval_days = 1`, increment `lapse_count`.
- If $q \ge 3$:
  - `reps == 0` -> `interval = 1` day
  - `reps == 1` -> `interval = 6` days
  - `reps >= 2` -> `interval = round(prev_interval * EF' * mastery_modifier)` where weaker concept mastery (`< 60`) applies `mastery_modifier = 0.85` (more frequent review) and strong mastery (`>= 80`) applies `1.10`, clamped to `[1, 180]` days.
- **Due Queue Priority Score:** Combines `overdue_days * 12` + `(100 - concept_mastery) * 0.6` + `lapse_count * 10` + `18` for `missed_question` cards.

---

## 4. Documented Limitations
1. **No Item Response Theory (3PL IRT) Calibration Yet:** Difficulty multipliers (`0.80–1.40`) use authored difficulty labels (`easy|medium|hard|olympiad`) until sufficient empirical cohort response volume (`N >= 500` per item) justifies Rasch/IRT parameter fitting in later scale phases.
2. **Conceptual Transfer Proxy:** Transfer currently measures diversity across question types and practice-vs-assessment contexts rather than cross-domain transfer tasks requiring multi-concept synthesis.
3. **In-App Notifications Only (`F-035` Foundation):** Revision reminders are persisted in `student_notifications` and surfaced inside the web app; external SMS/email/push dispatch remains disabled until institutional tenant gateway keys are configured in Phases 7–9.
4. **Heuristic Misconception Tagging:** Automatically detects conceptual gaps via mapped concept errors & authored `common_mistakes` strings when available; deep handwritten OCR error diagnosis arrives in Phase 6 (`F-029`).
