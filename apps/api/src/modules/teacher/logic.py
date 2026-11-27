"""Pure-stdlib deterministic helpers for Teacher AI-assisted grading, override, and CSV export."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: object) -> str:
    """Neutralize spreadsheet formula injection characters in exported CSV cells."""
    text = "" if value is None else str(value)
    if text and text[0] in _FORMULA_PREFIXES:
        return "'" + text
    return text


@dataclass(frozen=True, slots=True)
class AiGradingDraft:
    suggested_score: float
    rubric_band: str
    feedback_summary: str


def compute_ai_grading_draft(
    *,
    response_text: str,
    instructions: str,
    max_marks: float,
) -> AiGradingDraft:
    """Compute a deterministic AI-assisted grading draft when no external LLM key is active.

    Always leaves final authority to the teacher via explicit Teacher Override.
    """
    cleaned = response_text.strip()
    if max_marks <= 0:
        max_marks = 10.0

    if not cleaned:
        return AiGradingDraft(
            suggested_score=0.0,
            rubric_band="missing",
            feedback_summary=(
                "No written response detected. Teacher review recommended before finalizing score."
            ),
        )

    words = re.findall(r"[A-Za-z0-9]+", cleaned.lower())
    word_count = len(words)
    instruction_tokens = {
        tok
        for tok in re.findall(r"[A-Za-z]{4,}", instructions.lower())
        if tok not in {"that", "with", "from", "this", "have", "your", "show", "step", "steps"}
    }
    response_tokens = set(words)
    overlap_ratio = (
        len(instruction_tokens & response_tokens) / max(len(instruction_tokens), 1)
        if instruction_tokens
        else 0.5
    )

    has_math_or_steps = bool(
        re.search(r"(=|->|therefore|hence|step\s*\d|\d+\s*[+\-*/^])", cleaned.lower())
    )
    depth_score = min(1.0, word_count / 35.0)
    structure_bonus = 0.15 if has_math_or_steps else 0.0
    raw_ratio = min(0.95, max(0.2, 0.45 * depth_score + 0.40 * overlap_ratio + structure_bonus))
    suggested = round(raw_ratio * max_marks * 2.0) / 2.0
    suggested = max(0.0, min(max_marks, suggested))

    pct = (suggested / max_marks) * 100.0
    if pct >= 80.0:
        band = "strong"
        summary = (
            f"AI Draft ({suggested:.1f}/{max_marks:.1f}): Clear, well-structured reasoning "
            f"with strong coverage ({word_count} words). Verify final arithmetic and award marks."
        )
    elif pct >= 55.0:
        band = "developing"
        summary = (
            f"AI Draft ({suggested:.1f}/{max_marks:.1f}): Partial concept coverage detected "
            f"({word_count} words). Check intermediate steps and add targeted feedback."
        )
    else:
        band = "needs_review"
        summary = (
            f"AI Draft ({suggested:.1f}/{max_marks:.1f}): Brief response ({word_count} words) "
            "missing key reasoning steps. Teacher review and remediation recommended."
        )
    return AiGradingDraft(
        suggested_score=suggested,
        rubric_band=band,
        feedback_summary=summary,
    )


def validate_teacher_override_score(*, score: float, max_marks: float) -> float:
    """Validate and normalize teacher override score within [0, max_marks]."""
    if score < 0 or score > max_marks:
        raise ValueError(f"Teacher score must be between 0 and {max_marks}.")
    return round(float(score), 2)


def render_safe_csv_report(headers: list[str], rows: list[list[object]]) -> str:
    """Render RFC-4180 CSV with spreadsheet formula neutralization on every cell."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([sanitize_csv_cell(h) for h in headers])
    for row in rows:
        writer.writerow([sanitize_csv_cell(cell) for cell in row])
    return buf.getvalue()
