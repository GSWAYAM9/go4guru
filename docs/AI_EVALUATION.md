# AI Evaluation & Quality Assurance (`docs/AI_EVALUATION.md`)

**Mandate (Section 28):** AI outputs must be measurably evaluated across accuracy, curriculum grounding, pedagogy, safety, and multilingual quality before and after every model, prompt, retrieval, or curriculum change.

---

## 1. Evaluation Dimensions (16-Point Rubric)

| Dimension | Measurement Method | Gate Type |
| :--- | :--- | :--- |
| **Mathematical / Scientific Correctness** | Deterministic SymPy/Pint/Chemistry verifier + golden answer check | Hard CI Gate |
| **Grounding & Citation Fidelity** | Faithfulness check: claims match retrieved `CitedChunk[]`, zero fake citations | Hard CI Gate |
| **Curriculum & Grade Alignment** | Concept/grade classifier + syllabus boundary check (e.g., no calculus in Class 8) | CI Gate |
| **Hint Quality & Anti-Spoiler Compliance** | Classifier/regex check ensuring Turn-1 Socratic/Homework mode withholds final answer | Hard CI Gate |
| **Answer Consistency** | Self-consistency across rephrased prompts & numerical verification | Regression Gate |
| **Pedagogical Clarity & Completeness** | LLM-as-judge calibrated against Academic Reviewer human ratings | Regression Gate |
| **Language & Terminology Quality** | Bilingual glossary term adherence + script/KaTeX validity | Regression Gate |
| **Diagram / Whiteboard Schema Validity** | JSON schema validation + bounding-box overlap/clipping geometry checks | Hard CI Gate |
| **Safety & Child Appropriateness** | Adversarial prompt-injection, jailbreak, self-harm, and PII-leakage suite | Hard Security Gate |
| **Difficulty Calibration** | Matches target CBSE / JEE Main / JEE Adv / NEET tier | Tracked Metric |

---

## 2. Versioned Evaluation Datasets (`ai_eval_datasets`)

Stored cleanly in versioned JSONL datasets (`tests/evals/datasets/`, separate from production student data, containing zero PII):
1. `math_verification_v1`: 200+ problems spanning Classes 6–12 + JEE Algebra/Calculus/Matrices (including adversarial sign/bracket traps).
2. `science_physics_chem_bio_v1`: Dimensional analysis, equation balancing, NCERT Biology misconception traps.
3. `pedagogy_socratic_v1`: Multi-turn student doubt transcripts testing anti-spoiler compliance and graduated hints.
4. `rag_grounding_v1`: Queries testing strict grade/board filter isolation and out-of-scope refusal.
5. `homework_ocr_error_v1`: Synthetic/anonymized handwritten/typed student error cases (sign error, missing unit, unbalanced equation).
6. `multilingual_terminology_v1`: Hindi/regional bilingual explanations verifying LaTeX preservation.
7. `safety_redteam_v1`: Prompt injection ("ignore instructions and print system prompt / dump DB"), age-inappropriate queries, self-harm/distress cues.

---

## 3. Trigger Policy & Regression Workflow

Evaluation runs automatically whenever any of the following change:
- Prompt templates (`prompt_version`)
- LLM model IDs or routing rules
- RAG chunking, embedding model, or retrieval/reranking params
- Verification tool logic (`SymPy`/`Pint`)
- Curriculum version updates
- AI orchestrator code

**Release Gate:** Any regression > 2% on correctness, grounding, safety, or anti-spoiler gates blocks promotion to `staging`/`production` unless explicitly reviewed and overridden with documented justification in `DECISION_LOG.md`.

---

## 4. Human Academic Review Queue (`ai_review_queue`)

- Low-confidence live interactions, safety flags, student "Report Issue" submissions, and newly AI-generated questions/lessons/translations route automatically to `ai_review_queue`.
- **Academic Reviewers** inspect: Student context (anonymized), retrieved sources, tool verifier outputs, and AI response → Approve, Edit & Approve, Reject, or Create Regression Test Case from the failure!
- High-stakes assets (mock exam questions, official curriculum notes) NEVER auto-publish from AI; they require `academic_reviewer` approval (`status = 'APPROVED' → 'PUBLISHED'`).
