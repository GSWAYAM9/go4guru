"""Unit tests for dynamic Excel/CSV inspection, normalization, validation, and grading."""

from __future__ import annotations

import io

import openpyxl
from src.modules.question_bank.importer import (
    compute_canonical_hash,
    inspect_and_parse_workbook,
    map_and_validate_row,
)
from src.modules.question_bank.public import evaluate_practice_response


def _build_sample_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Physics_Custom_Sheet"
    ws.append(["Prompt", "Choice1", "Choice2", "Choice3", "Choice4", "Key", "Diff"])
    ws.append(["What is SI unit of force?", "Joule", "Newton", "Watt", "Pascal", "B", "easy"])
    ws.append(["=cmd|' /C calc'!A0", "10", "20", "", "", "B", "medium"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_dynamic_xlsx_sheet_and_header_detection() -> None:
    data = _build_sample_xlsx()
    sheets, rows_by_sheet = inspect_and_parse_workbook(data, "xlsx")
    assert len(sheets) == 1
    assert sheets[0]["sheet_name"] == "Physics_Custom_Sheet"
    assert sheets[0]["headers"] == [
        "Prompt",
        "Choice1",
        "Choice2",
        "Choice3",
        "Choice4",
        "Key",
        "Diff",
    ]
    assert sheets[0]["row_count"] == 2
    assert len(rows_by_sheet["Physics_Custom_Sheet"]) == 2


def test_row_validation_formula_neutralization_and_pyq_guard() -> None:
    col_map = {
        "stem_markdown": "Prompt",
        "option_a": "Choice1",
        "option_b": "Choice2",
        "correct_answer": "Key",
        "is_pyq": "PYQ_Claim",
    }
    norm, errors, warnings = map_and_validate_row(
        raw_row={
            "Prompt": '=HYPERLINK("http://evil")',
            "Choice1": "-5",
            "Choice2": "10",
            "Key": "A",
            "PYQ_Claim": "true",
        },
        column_map=col_map,
    )
    assert norm["stem_markdown"].startswith("'=")
    assert any("Neutralized formula-like" in w for w in warnings)
    assert any("PYQ safety violation" in e for e in errors)


def test_canonical_hash_normalization_catches_punctuation_variants() -> None:
    h1 = compute_canonical_hash("What is Newton's Second Law?", "mcq_single")
    h2 = compute_canonical_hash("  what   is newtons second law  ", "mcq_single")
    h3 = compute_canonical_hash("What is Newtons Second Law", "mcq_single")
    assert h2 == h3
    assert h1 != compute_canonical_hash("Different stem", "mcq_single")


def test_practice_deterministic_grading_variants() -> None:
    ok_mcq, score_mcq = evaluate_practice_response(
        question_type="mcq_single",
        correct_answer_jsonb={"correct_key": "B"},
        response_jsonb={"selected_key": "b"},
        default_marks=4.0,
    )
    assert ok_mcq is True and score_mcq == 4.0

    ok_multi, _ = evaluate_practice_response(
        question_type="mcq_multiple",
        correct_answer_jsonb={"correct_keys": ["A", "C"]},
        response_jsonb={"selected_keys": ["C", "A"]},
        default_marks=4.0,
    )
    assert ok_multi is True

    ok_num, _ = evaluate_practice_response(
        question_type="numerical",
        correct_answer_jsonb={"expected_value": 9.81, "tolerance_abs": 0.02},
        response_jsonb={"numeric_value": 9.8},
        default_marks=4.0,
    )
    assert ok_num is True
