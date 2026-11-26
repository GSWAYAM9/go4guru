# Excel Question Bank Ingestion Specification (`docs/EXCEL_IMPORT_SPECIFICATION.md`)

**Current Data Reality:** Per [DATA_ASSET_AUDIT.md](file:///d:/go4guru/docs/DATA_ASSET_AUDIT.md), **0 `.xlsx`, `.xls`, or `.csv` files** currently exist in `d:\go4guru` or adjacent `D:\class-*` folders. Therefore, this specification makes **zero hardcoded assumptions** about workbook sheet names or column headers and instead defines a schema-adaptive, staging-first pipeline.

---

## 1. End-to-End 14-Stage Pipeline

```text
1. UPLOAD           → Private S3/MinIO upload via signed URL; compute file SHA-256
2. FILE VALIDATION  → Verify MIME/magic bytes (.xlsx/.xls/.csv), size cap, zip-bomb & macro checks
3. SHEET DETECTION  → Inspect workbook sheets, row counts, sample rows, detected headers
4. STAGING          → Parse workbook safely in async worker; write immutable import_staging_rows
5. COLUMN MAPPING   → Content Admin maps detected headers -> canonical fields (saved as reusable profiles)
6. NORMALIZATION    → Trim whitespace, strip Excel formula-injection prefixes (=,+,-,@), normalize Unicode/LaTeX
7. VALIDATION       → Row-level Pydantic checks: required fields, option keys, valid answer vs options, difficulty enum
8. DUPLICATE CHECK  → Intra-batch & DB check via canonical_hash + fuzzy/SimHash near-duplicate flagging
9. ACADEMIC MAPPING → Resolve Board/Grade/Subject/Chapter/Topic/Concept IDs; flag unmapped rows
10. SOURCE VALID.   → Require source/license; block is_pyq=true if exam/year/provenance metadata missing
11. PREVIEW         → Generate interactive preview (valid, warning, error, duplicate counts + row diffs)
12. REVIEW          → Content Admin / Academic Reviewer resolves or excludes errored/duplicate rows
13. IMPORT          → Idempotent transactional commit into questions (status = DRAFT or REVIEW)
14. PUBLISH         → Separate Academic Reviewer approval flow promotes verified questions to PUBLISHED
```

---

## 2. Canonical Field Mapping Targets

When Content Admin opens the Column Mapper for an uploaded sheet, detected Excel headers can map to:
- **Required Core:** `stem_markdown`, `question_type` (or auto-inferred), `correct_answer`
- **Options (for MCQ/Matrix/Match):** `option_a`..`option_f`, or single structured column `options_json`
- **Academic Context:** `board`, `academic_session`, `grade`, `subject`, `book`, `chapter`, `topic`, `concept_code`
- **Assessment Metadata:** `difficulty`, `marks`, `negative_marks`, `estimated_seconds`, `language_code`, `competency_tag`, `skill_tags`, `exam_tags`
- **Solutions & Pedagogy:** `explanation`, `steps`, `hint_1`, `hint_2`, `hint_3`, `common_mistakes`, `rubric`
- **Provenance & Rights:** `source_name`, `license_name`, `is_pyq`, `exam_name`, `exam_year`, `exam_session`, `exam_shift`, `paper_code`, `question_number`, `source_url`

---

## 3. Safety, Integrity & Idempotency Guarantees

1. **Immutability of Originals:** Uploaded `.xlsx` files are stored read-only in object storage (`imports/raw/{batch_id}/{sha256}.xlsx`) and never overwritten.
2. **Formula Injection Defense:** Any string cell starting with `=`, `+`, `-`, `@`, `\t`, `\r` (unless parsed as valid negative number/math formula) is escaped on CSV/Excel re-export and sanitized before storage.
3. **Question-Type Inference Rules (Suggested in Preview, Confirmed by Admin):**
   - Options present + single answer key (`A`/`1`) → `mcq_single`
   - Options present + comma/multi keys (`A,C`) → `mcq_multiple`
   - Numeric scalar answer + no options → `numerical` or `integer`
   - Contains `Assertion (A)` & `Reason (R)` markers → `assertion_reason`
   - No options + text/rubric answer → `short_answer` / `long_answer`
4. **Idempotency & Rollback:**
   - Re-uploading the identical file SHA-256 warns the admin and links to the prior batch.
   - Each committed question stores `import_batch_id`; if a batch was imported erroneously before publishing, `POST /api/v1/imports/{batch_id}/rollback` soft-deletes/removes uncommitted draft questions created by that batch atomically.
   - Once questions are `PUBLISHED` and referenced by student `question_attempts`, rollback is blocked (only archival allowed) to preserve historical exam integrity.
5. **Import Audit Report:** Every batch generates a downloadable JSON/CSV report listing total rows, imported count, skipped duplicates, row-level validation errors, warnings, actor ID, and timestamps.
