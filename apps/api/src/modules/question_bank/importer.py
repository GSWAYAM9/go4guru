"""Schema-adaptive Excel (.xlsx) and CSV inspection, normalization, and validation helpers."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from typing import Any, Literal

import openpyxl

from src.core.security import sanitize_spreadsheet_cell

_NUM_LITERAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]+")

CANONICAL_TARGET_FIELDS: tuple[str, ...] = (
    "stem_markdown",
    "question_type",
    "correct_answer",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "difficulty",
    "marks",
    "negative_marks",
    "estimated_seconds",
    "language_code",
    "explanation",
    "hint_1",
    "hint_2",
    "hint_3",
    "common_mistakes",
    "grade",
    "subject",
    "chapter",
    "topic",
    "concept_code",
    "is_pyq",
    "exam_name",
    "exam_year",
    "source_url",
)


def compute_canonical_hash(stem_markdown: str, question_type: str) -> str:
    """Compute normalized canonical SHA-256 fingerprint for deduplication."""
    normalized = stem_markdown.lower().strip()
    normalized = _PUNCT_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    composite = f"{question_type.lower()}::{normalized}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def normalize_cell_value(value: Any, *, allow_signed_number: bool = False) -> str:
    """Trim whitespace and neutralize formula injection (`=`, `+`, `-`, `@`, `\\t`, `\\r`)."""
    if value is None:
        return ""
    text_val = str(value).strip()
    if not text_val:
        return ""
    if allow_signed_number and _NUM_LITERAL_RE.match(text_val):
        return text_val
    return sanitize_spreadsheet_cell(text_val)


def _inspect_xlsx(
    file_bytes: bytes,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if not file_bytes.startswith(b"PK\x03\x04"):
        raise ValueError("Invalid .xlsx file signature (expected ZIP container).")
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheets_meta: list[dict[str, Any]] = []
    rows_by_sheet: dict[str, list[dict[str, Any]]] = {}
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            iterator = ws.iter_rows(values_only=True)
            header_row: list[str] | None = None
            for xlsx_row in iterator:
                if xlsx_row and any(
                    cell is not None and str(cell).strip() != "" for cell in xlsx_row
                ):
                    header_row = [
                        (
                            str(cell).strip()
                            if cell is not None and str(cell).strip() != ""
                            else f"col_{idx + 1}"
                        )
                        for idx, cell in enumerate(xlsx_row)
                    ]
                    break
            if header_row is None:
                sheets_meta.append(
                    {"sheet_name": sheet_name, "row_count": 0, "headers": [], "sample_rows": []}
                )
                rows_by_sheet[sheet_name] = []
                continue

            parsed_rows: list[dict[str, Any]] = []
            for row_offset, raw_row in enumerate(iterator, start=2):
                if not raw_row or not any(
                    cell is not None and str(cell).strip() != "" for cell in raw_row
                ):
                    continue
                row_dict = {
                    header_row[idx]: (
                        ""
                        if idx >= len(raw_row) or raw_row[idx] is None
                        else str(raw_row[idx]).strip()
                    )
                    for idx in range(len(header_row))
                }
                parsed_rows.append({"row_number": row_offset, "raw": row_dict})

            sheets_meta.append(
                {
                    "sheet_name": sheet_name,
                    "row_count": len(parsed_rows),
                    "headers": header_row,
                    "sample_rows": [item["raw"] for item in parsed_rows[:3]],
                }
            )
            rows_by_sheet[sheet_name] = parsed_rows
    finally:
        wb.close()
    return sheets_meta, rows_by_sheet


def _inspect_csv(
    file_bytes: bytes,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    try:
        decoded = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc

    reader = csv.reader(io.StringIO(decoded))
    csv_header: list[str] | None = None
    csv_rows: list[dict[str, Any]] = []
    for row_idx, csv_row in enumerate(reader, start=1):
        if csv_header is None:
            if not any(cell.strip() for cell in csv_row):
                continue
            csv_header = [
                cell.strip() if cell.strip() else f"col_{i + 1}" for i, cell in enumerate(csv_row)
            ]
            continue
        if not any(cell.strip() for cell in csv_row):
            continue
        row_dict = {
            csv_header[i]: ("" if i >= len(csv_row) else csv_row[i].strip())
            for i in range(len(csv_header))
        }
        csv_rows.append({"row_number": row_idx, "raw": row_dict})

    if csv_header is None:
        return (
            [{"sheet_name": "csv", "row_count": 0, "headers": [], "sample_rows": []}],
            {"csv": []},
        )

    return (
        [
            {
                "sheet_name": "csv",
                "row_count": len(csv_rows),
                "headers": csv_header,
                "sample_rows": [r["raw"] for r in csv_rows[:3]],
            }
        ],
        {"csv": csv_rows},
    )


def inspect_and_parse_workbook(
    file_bytes: bytes, file_format: Literal["xlsx", "csv"]
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Inspect arbitrary .xlsx/.csv structure dynamically with zero hardcoded headers."""
    if file_format == "xlsx":
        return _inspect_xlsx(file_bytes)
    return _inspect_csv(file_bytes)


def map_and_validate_row(
    *,
    raw_row: dict[str, Any],
    column_map: dict[str, str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Normalize and validate one staged spreadsheet row per mapped column headers."""
    errors: list[str] = []
    warnings: list[str] = []

    def get_mapped(canonical_field: str, *, numeric: bool = False) -> str:
        header = column_map.get(canonical_field, "")
        if not header or header not in raw_row:
            return ""
        raw_val = raw_row.get(header)
        raw_str = "" if raw_val is None else str(raw_val).strip()
        normalized = normalize_cell_value(raw_str, allow_signed_number=numeric)
        if raw_str and normalized.startswith("'") and not raw_str.startswith("'"):
            warnings.append(f"Neutralized formula-like prefix in '{canonical_field}' ({header}).")
        return normalized

    stem = get_mapped("stem_markdown")
    if len(stem) < 3:
        errors.append("Missing or too-short 'stem_markdown'.")

    raw_answer = get_mapped("correct_answer", numeric=True)
    if not raw_answer:
        errors.append("Missing 'correct_answer'.")

    options: list[dict[str, Any]] = []
    for key, field in (
        ("A", "option_a"),
        ("B", "option_b"),
        ("C", "option_c"),
        ("D", "option_d"),
        ("E", "option_e"),
    ):
        val = get_mapped(field, numeric=True)
        if val:
            options.append({"option_key": key, "content_markdown": val, "is_correct": False})

    explicit_type = get_mapped("question_type").lower()
    if not explicit_type:
        if options:
            if "," in raw_answer:
                inferred_type = "mcq_multiple"
            else:
                inferred_type = "mcq_single"
        elif _NUM_LITERAL_RE.match(raw_answer):
            inferred_type = "integer" if "." not in raw_answer else "numerical"
        else:
            inferred_type = "short_answer"
        question_type = inferred_type
        warnings.append(f"Inferred question_type='{inferred_type}'.")
    else:
        question_type = explicit_type

    valid_types = {
        "mcq_single",
        "mcq_multiple",
        "numerical",
        "integer",
        "assertion_reason",
        "case_based",
        "match_following",
        "matrix_match",
        "short_answer",
        "long_answer",
        "essay",
        "diagram_based",
        "passage_based",
        "comprehension",
        "map_based",
        "image_based",
        "audio_based",
        "extensible_json",
    }
    if question_type not in valid_types:
        errors.append(f"Unsupported question_type '{question_type}'.")

    correct_answer_jsonb: dict[str, Any] = {}
    if question_type in {"mcq_single", "assertion_reason"}:
        if len(options) < 2:
            errors.append(f"{question_type} requires at least 2 options.")
        opt_keys = {o["option_key"] for o in options}
        ans_key = raw_answer.upper()
        if ans_key not in opt_keys:
            errors.append(
                f"correct_answer '{raw_answer}' does not match "
                f"provided option keys {sorted(opt_keys)}."
            )
        else:
            for o in options:
                o["is_correct"] = o["option_key"] == ans_key
            correct_answer_jsonb = {"correct_key": ans_key}
    elif question_type == "mcq_multiple":
        if len(options) < 2:
            errors.append("mcq_multiple requires at least 2 options.")
        opt_keys = {o["option_key"] for o in options}
        ans_keys = sorted({part.strip().upper() for part in raw_answer.split(",") if part.strip()})
        if not ans_keys or not set(ans_keys).issubset(opt_keys):
            errors.append(f"correct_answer '{raw_answer}' has keys outside {sorted(opt_keys)}.")
        else:
            for o in options:
                o["is_correct"] = o["option_key"] in ans_keys
            correct_answer_jsonb = {"correct_keys": ans_keys}
    elif question_type in {"numerical", "integer"}:
        if not _NUM_LITERAL_RE.match(raw_answer):
            errors.append(f"Numeric question requires numeric correct_answer, got '{raw_answer}'.")
        else:
            correct_answer_jsonb = {
                "expected_value": int(raw_answer)
                if question_type == "integer"
                else float(raw_answer),
                "tolerance_abs": 0.01 if question_type == "numerical" else 0.0,
            }
    else:
        correct_answer_jsonb = {"expected_text": raw_answer}

    difficulty = (get_mapped("difficulty") or "medium").lower()
    if difficulty not in {"easy", "medium", "hard", "olympiad"}:
        errors.append(f"Invalid difficulty '{difficulty}'.")

    marks_str = get_mapped("marks", numeric=True) or "4"
    neg_str = get_mapped("negative_marks", numeric=True) or "0"
    sec_str = get_mapped("estimated_seconds", numeric=True) or "60"
    try:
        marks = float(marks_str)
        neg_marks = float(neg_str)
        est_seconds = int(float(sec_str))
        if marks <= 0 or neg_marks < 0 or est_seconds < 5:
            errors.append("Marks/time constraints invalid.")
    except ValueError:
        errors.append("Marks, negative_marks, and estimated_seconds must be numeric.")
        marks, neg_marks, est_seconds = 4.0, 0.0, 60

    is_pyq_raw = get_mapped("is_pyq").lower()
    is_pyq = is_pyq_raw in {"true", "1", "yes", "y"}
    exam_name = get_mapped("exam_name") or None
    exam_year_str = get_mapped("exam_year", numeric=True)
    exam_year: int | None = None
    if exam_year_str:
        try:
            exam_year = int(float(exam_year_str))
        except ValueError:
            errors.append(f"Invalid exam_year '{exam_year_str}'.")
    if is_pyq and (not exam_name or exam_year is None):
        errors.append(
            "PYQ safety violation: rows claiming is_pyq=true require non-empty "
            "exam_name and exam_year (and post-import reviewer verification)."
        )

    hints: list[dict[str, Any]] = []
    for level, field in ((1, "hint_1"), (2, "hint_2"), (3, "hint_3")):
        h_text = get_mapped(field)
        if h_text:
            hints.append({"hint_level": level, "hint_markdown": h_text})

    normalized_payload = {
        "stem_markdown": stem,
        "question_type": question_type,
        "correct_answer_jsonb": correct_answer_jsonb,
        "options": options,
        "difficulty": difficulty,
        "default_marks": marks,
        "default_negative_marks": neg_marks,
        "estimated_seconds": est_seconds,
        "language_code": get_mapped("language_code") or "en",
        "explanation": get_mapped("explanation"),
        "common_mistakes": get_mapped("common_mistakes") or None,
        "hints": hints,
        "grade": get_mapped("grade") or None,
        "subject": get_mapped("subject") or None,
        "chapter": get_mapped("chapter") or None,
        "topic": get_mapped("topic") or None,
        "concept_code": get_mapped("concept_code") or None,
        "claimed_is_pyq": is_pyq,
        "exam_name": exam_name,
        "exam_year": exam_year,
        "source_url": get_mapped("source_url") or None,
        "canonical_hash": compute_canonical_hash(stem, question_type),
    }
    return normalized_payload, errors, warnings


def serialize_import_report_csv(rows: list[dict[str, Any]]) -> str:
    """Generate formula-safe CSV audit report for an import batch."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["row_number", "sheet_name", "status", "errors", "warnings", "created_question_id"]
    )
    for r in rows:
        writer.writerow(
            [
                r["row_number"],
                sanitize_spreadsheet_cell(str(r["sheet_name"])),
                r["validation_status"],
                sanitize_spreadsheet_cell(json.dumps(r["errors"])),
                sanitize_spreadsheet_cell(json.dumps(r["warnings"])),
                str(r.get("created_question_id") or ""),
            ]
        )
    return buf.getvalue()
