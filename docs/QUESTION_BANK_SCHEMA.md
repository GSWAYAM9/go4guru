# Canonical Question Bank Schema (`docs/QUESTION_BANK_SCHEMA.md`)

**Goal:** One unified, versioned, provenance-verified Question Bank capable of serving CBSE Boards, JEE Main, JEE Advanced, NEET, daily practice, adaptive remediation, teacher tests, and multilingual delivery.

---

## 1. Structural Design Principles

1. **Separated Identity vs Versioned Content:** `questions.id` is permanent; `question_versions.id` is pinned by every `test_questions` and `question_attempts` row so fixing a typo never invalidates historical grading.
2. **Strict PYQ Provenance:** `is_pyq = true` MUST NOT be set on AI-generated or unverified questions. Genuine PYQs require `exam_name`, `exam_year`, verification status (`verified`), reviewer attribution, and source metadata (`session`, `shift`, `paper_code`, `question_number`, `source_url`).
3. **Answer Confidentiality:** Student-facing question fetch endpoints strip `correct_answer_jsonb`, `question_options.is_correct`, and `question_solutions` until an attempt is submitted (or practice mode explicitly verifies a single answer).

---

## 2. Supported Question Types (`question_type` Enum + Typed `answer_schema_jsonb`)

| Type Code | Description | Auto-Gradable? | Typical Exam Use |
| :--- | :--- | :---: | :--- |
| `mcq_single` | Single correct out of N options | Yes | CBSE, JEE Main, NEET |
| `mcq_multiple` | 1 or more correct options; supports partial marking | Yes | JEE Advanced |
| `numerical` | Floating-point value with configurable tolerance (`abs_tol` / `rel_tol` / rounding) | Yes | JEE Main, JEE Adv |
| `integer` | Exact integer (`0–9` or arbitrary integer) | Yes | JEE Adv, JEE Main |
| `assertion_reason` | Statement I & II / Assertion & Reason standardized choices | Yes | CBSE, NEET |
| `case_based` | Shared stimulus passage + 3–5 sub-questions (linked via `parent_question_id` or `subquestions`) | Mixed | CBSE Boards |
| `match_following` | Left column matched to right column pairs | Yes | CBSE, JEE Adv, NEET |
| `matrix_match` | Multiple right-column matches per row (`P→1,3; Q→2`) | Yes | JEE Advanced |
| `short_answer` | Brief subjective text/math response evaluated via rubric + teacher/AI assist | Assisted | CBSE Boards |
| `long_answer` | Multi-step derivation/explanation with step-wise marking rubric | Assisted | CBSE Boards |
| `essay` | Structured writing composition evaluated by rubric | Assisted | English / SST |
| `diagram_based` | Visual diagram stimulus + labeling/MCQ/short sub-items | Mixed | Science, Biology, Geo |
| `passage_based` | Reading comprehension / unseen passage group | Mixed | English, JEE Adv |
| `comprehension` | Multi-question paragraph cluster | Yes/Mixed | JEE Adv, English |
| `map_based` | Geographical/historical map pinpointing or identification | Mixed | CBSE Social Science |
| `image_based` | Image stimulus with identification/analysis | Mixed | NEET, Science |
| `audio_based` | Listening comprehension with accessible transcript option | Mixed | English / Languages |
| `extensible_json` | Future interactive widget schema validated by JSON Schema | Configurable | Future labs |

---

## 3. Canonical JSON Shapes

### 3.1 `answer_schema_jsonb` & `correct_answer_jsonb` Examples
- **`mcq_multiple`:**
  ```json
  {
    "correct_keys": ["A", "C"],
    "partial_marking_supported": true
  }
  ```
- **`numerical`:**
  ```json
  {
    "expected_value": 9.81,
    "tolerance_abs": 0.05,
    "tolerance_pct": null,
    "unit": "m/s^2",
    "decimal_places": 2
  }
  ```
- **`short_answer` / `long_answer` (`rubric_jsonb`):**
  ```json
  {
    "max_marks": 5,
    "criteria": [
      {"step": "Diagram / Free Body Diagram", "marks": 1.0},
      {"step": "Correct governing equation", "marks": 1.5},
      {"step": "Algebraic derivation", "marks": 1.5},
      {"step": "Final value with SI unit", "marks": 1.0}
    ]
  }
  ```

---

## 4. Lifecycle, Deduplication & Provenance Rules

- **Lifecycle:** `DRAFT → VALIDATION → REVIEW → APPROVED → PUBLISHED → ARCHIVED`.
- **Canonical Deduplication:** Compute normalized text fingerprint (lowercased, whitespace/punctuation collapsed, normalized LaTeX whitespace) `canonical_hash = SHA256(...)`, plus optional semantic similarity check during Excel staging to catch near-duplicates.
- **AI-Generated Questions:** Must carry `ai_generated = true`, `ai_metadata_jsonb` (`model`, `prompt_version`, `generation_timestamp`, `verifier_passed`, `eval_score`), and `source_type = 'ai_generated'`. Cannot enter official high-stakes mock exams unless `status = 'PUBLISHED'` after human `academic_reviewer` approval.
