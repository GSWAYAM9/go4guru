# Phase 6 — Homework AI Implementation (`F-029`)

## 1. Architecture Integration

Phase 6 integrates directly into the existing **GO4GURU** modular monolith (`apps/api`, `apps/web`, `@go4guru/contracts`) without introducing standalone services, separate databases, or parallel authentication systems:

- **Backend Module (`apps/api/src/modules/homework/`):** Follows strict `import-linter` boundaries, importing only from `src.core.*`, `src.modules.ai.public`, and `src.modules.notifications.public`. Mounted in `apps/api/src/main.py` at `/api/v1/homework`.
- **Database Persistence (`apps/api/alembic/versions/0007_phase6_homework_ai.py`):** Extends the existing PostgreSQL 18 schema (`down_revision = "0006_phase5_adaptive_revision"`) with four normalized tables:
  - `homework_submissions` (student/tenant ownership, subject selection/detection, status, page/retry counts, OCR review flag)
  - `homework_files` (private storage key, magic-byte format, SHA-256, EXIF-stripped flag, PDF page count, scan status)
  - `homework_ocr_results` (per-page OCR provider, extracted text/LaTeX, handwriting flags, confidence, student correction override, warnings)
  - `homework_evaluations` (attempt-versioned step evaluations, subject-aware error classifications, 3-level graduated hints, anti-spoiler reveal state, deterministic verifier results, validation report, revision recommendations)
- **RBAC & Privacy Enforcement:** Migration seeds `homework:manage_own` (assigned to `student`, `teacher`, `mentor`, `platform_admin`) and `homework:review` (assigned to `teacher`, `mentor`, `academic_reviewer`, `school_admin`, `platform_admin`). The `parent` role is intentionally excluded from raw Homework AI coaching sessions and receives a `403` on backend routes.
- **Storage & Upload Security (`file_security.py`):** Enforces per-file size (`10 MB`), combined submission size (`25 MB`), and page count (`10` pages) limits; inspects binary magic headers (`JPEG`, `PNG`, `WebP`, `PDF`); rejects spoofed SVG/HTML and active PDF triggers (`/JavaScript`, `/JS`, `/OpenAction`, `/Launch`, `/EmbeddedFile`, `/RichMedia`); strips JPEG/PNG/WebP EXIF & text metadata; and persists immutable sanitized bytes outside webroot via `LocalPrivateStorage` using server-generated keys.

## 2. OCR, Subject-Aware Evaluation & Anti-Spoiler Flow

- **OCR & Handwriting (`ocr.py`):**
  1. Digital PDFs extract embedded text streams deterministically (`pdf_text_stream`).
  2. Images & scanned PDFs route through existing `AIRouterGateway` multimodal Vision (`GeminiProvider` `inline_data` / `OpenAIProvider` `image_url`) with handwriting recognition when `GEMINI_API_KEY` or `OPENAI_API_KEY` is configured.
  3. Optional local `tesseract` CLI runs safely without shell interpolation if present on host `PATH`.
  4. If no OCR key/binary is available, student-supplied companion transcripts work, or the pipeline returns an honest `unavailable_manual_review_required` low-confidence state prompting OCR editing — never fabricating text.
- **5-Subject Diagnostic Taxonomy (`schemas.py`, `evaluator.py`):**
  - **Mathematics:** `algebra`, `formula`, `arithmetic`, `sign`, `logic`, `missing_steps` (SymPy verification)
  - **Physics:** `concept`, `formula`, `units`, `calculation`, `diagram`, `reasoning` (Pint & SymPy verification)
  - **Chemistry:** `equation`, `reaction`, `formula`, `concept`, `calculation`, `units` (Stoichiometric atom-conservation verification)
  - **English:** `grammar`, `spelling`, `vocabulary`, `sentence_structure`, `comprehension`, `writing`
  - **Social Science:** `factual_accuracy`, `concept`, `structure`, `missing_points`, `explanation`, `map_timeline`
- **Validation & Anti-Spoiler Guard (`validate_evaluation_output`, `service.py`):**
  - Validates error categories strictly against the detected subject taxonomy.
  - Audits Hint Levels 1 & 2 to block premature answer leaks and strips PII before external LLM calls.
  - Persists `current_hint_level_unlocked = 1` and `solution_revealed = False` by default; `complete_solution_markdown` is omitted (`null`) from API responses until the student explicitly calls `POST /api/v1/homework/submissions/{id}/solution/reveal` with `{"confirm_reveal": true}`.

## 3. API Endpoints (`/api/v1/homework`)

- `POST /api/v1/homework/submissions` — Multipart multi-page upload, validation, private storage, OCR, and initial evaluation
- `GET /api/v1/homework/submissions` — Student's submission history
- `GET /api/v1/homework/submissions/{submission_id}` — Full submission detail, OCR pages, latest evaluation, and attempt history
- `GET /api/v1/homework/submissions/{submission_id}/files/{file_id}` — Authenticated private file download (`X-Content-Type-Options: nosniff`)
- `PATCH /api/v1/homework/submissions/{submission_id}/ocr` — Save student OCR corrections, optional subject override, and re-evaluate
- `POST /api/v1/homework/submissions/{submission_id}/retry` — Evaluate revised student attempt and compute errors resolved across attempts
- `POST /api/v1/homework/submissions/{submission_id}/hints/unlock` — Stepwise hint unlocking (`Level 1 -> 2 -> 3`)
- `POST /api/v1/homework/submissions/{submission_id}/solution/reveal` — Explicit confirmation required to reveal full solution

## 4. Environment Variables (`.env.example`)

- `GEMINI_API_KEY` — Activates live Gemini Vision handwriting OCR and multimodal LLM evaluation via `AIRouterGateway`
- `HOMEWORK_MAX_FILE_BYTES` (default `10485760`) — Per-file byte cap
- `HOMEWORK_MAX_TOTAL_BYTES` (default `26214400`) — Combined submission byte cap
- `HOMEWORK_MAX_PAGES` (default `10`) — Maximum files/PDF pages per submission
- `HOMEWORK_OCR_PROVIDER` (default `auto`) — `auto | gemini_vision | openai_vision | tesseract | builtin`
- `HOMEWORK_OCR_MIN_CONFIDENCE` (default `0.65`) — Confidence threshold below which `needs_ocr_review` is triggered

## 5. Known Limitations Requiring External Credentials / Runtime Services

- Automatic handwritten image OCR requires either `GEMINI_API_KEY`, `OPENAI_API_KEY`, or a host `tesseract` binary; without them, digital PDFs extract embedded text and image uploads gracefully enter the interactive OCR transcription review flow.
- Live LLM rubric refinement activates when `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` is configured; otherwise the deterministic subject-aware verifier engines (SymPy/Pint/stoichiometry/rubric checks) execute locally.
- Running `alembic upgrade head` and `pytest apps/api/tests/unit/test_phase6_homework_ai.py apps/api/tests/integration/test_phase6_homework_pg.py` requires the project's Python 3.12 virtualenv and live PostgreSQL 18 instance.
