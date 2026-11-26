"""Configurable, versioned examination scoring & section-rule evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ScoringRule(BaseModel):
    """Configurable per-section or per-quiz marking specification."""

    mode: Literal["standard", "partial_subset"] = "standard"
    correct_marks: float = Field(default=4.0, gt=0)
    wrong_marks: float = Field(default=0.0, le=0)
    unanswered_marks: float = Field(default=0.0)
    partial_credit_per_correct_option: float = Field(default=0.0, ge=0)


class ExamSectionRule(BaseModel):
    """Configurable rule definition for a single exam section."""

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    question_count: int = Field(ge=1, le=200)
    attempt_limit: int | None = Field(default=None, ge=1, le=200)
    allowed_question_types: list[str] = Field(default_factory=list)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    question_type_distribution: dict[str, int] = Field(default_factory=dict)
    scoring: ScoringRule = Field(default_factory=ScoringRule)

    @model_validator(mode="after")
    def validate_attempt_limit(self) -> ExamSectionRule:
        if self.attempt_limit is not None and self.attempt_limit > self.question_count:
            raise ValueError("attempt_limit cannot exceed section question_count.")
        return self


class RetakePolicy(BaseModel):
    max_attempts: int | None = Field(default=None, ge=1)
    cooldown_minutes: int = Field(default=0, ge=0)


class ExamPatternRules(BaseModel):
    """Top-level schema validated on exam_patterns.rules_jsonb."""

    duration_seconds: int | None = Field(default=1800, ge=30, le=21600)
    grace_seconds: int = Field(default=30, ge=0, le=300)
    shuffle_questions: bool = False
    shuffle_options: bool = False
    retake_policy: RetakePolicy = Field(default_factory=RetakePolicy)
    sections: list[ExamSectionRule] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EvaluatedItemResult:
    """Deterministic grading output for one question in an attempt."""

    attempted: bool
    is_correct: bool
    marks_awarded: float
    counted_toward_limit: bool


def is_response_empty(question_type: str, response_jsonb: dict[str, Any]) -> bool:
    """Determine whether a saved response represents an unanswered question."""
    if not response_jsonb:
        return True
    if question_type in {"mcq_single", "assertion_reason"}:
        return not str(response_jsonb.get("selected_key") or "").strip()
    if question_type == "mcq_multiple":
        keys = response_jsonb.get("selected_keys")
        return not isinstance(keys, list) or len(keys) == 0
    if question_type in {"numerical", "integer"}:
        val = response_jsonb.get("numeric_value")
        return val is None or str(val).strip() == ""
    return not str(response_jsonb.get("text_answer") or "").strip()


def evaluate_question_with_rule(
    *,
    question_type: str,
    correct_answer_jsonb: dict[str, Any],
    response_jsonb: dict[str, Any],
    rule: ScoringRule,
) -> EvaluatedItemResult:
    """Evaluate one question response strictly using the configured ScoringRule."""
    if is_response_empty(question_type, response_jsonb):
        return EvaluatedItemResult(
            attempted=False,
            is_correct=False,
            marks_awarded=float(rule.unanswered_marks),
            counted_toward_limit=False,
        )

    if question_type in {"mcq_single", "assertion_reason"}:
        expected = str(correct_answer_jsonb.get("correct_key", "")).strip().upper()
        given = str(response_jsonb.get("selected_key", "")).strip().upper()
        is_correct = bool(expected and given == expected)
        return EvaluatedItemResult(
            attempted=True,
            is_correct=is_correct,
            marks_awarded=float(rule.correct_marks if is_correct else rule.wrong_marks),
            counted_toward_limit=True,
        )

    if question_type == "mcq_multiple":
        expected_set = {
            str(k).strip().upper() for k in correct_answer_jsonb.get("correct_keys", [])
        }
        given_raw = response_jsonb.get("selected_keys", [])
        given_set = (
            {str(k).strip().upper() for k in given_raw} if isinstance(given_raw, list) else set()
        )
        if not expected_set:
            return EvaluatedItemResult(True, False, float(rule.wrong_marks), True)

        if given_set == expected_set:
            return EvaluatedItemResult(True, True, float(rule.correct_marks), True)

        # Any wrong option selected triggers negative wrong_marks immediately
        if not given_set.issubset(expected_set):
            return EvaluatedItemResult(True, False, float(rule.wrong_marks), True)

        # Subset of ONLY correct options: either partial_subset credit or standard 0/wrong
        if rule.mode == "partial_subset" and rule.partial_credit_per_correct_option > 0:
            partial_score = min(
                float(rule.correct_marks),
                float(len(given_set) * rule.partial_credit_per_correct_option),
            )
            return EvaluatedItemResult(True, False, partial_score, True)
        return EvaluatedItemResult(True, False, float(rule.wrong_marks), True)

    if question_type in {"numerical", "integer"}:
        try:
            expected_val = float(correct_answer_jsonb["expected_value"])
            tol = float(correct_answer_jsonb.get("tolerance_abs", 0.01))
            given_val = float(response_jsonb["numeric_value"])
        except (KeyError, TypeError, ValueError):
            return EvaluatedItemResult(True, False, float(rule.wrong_marks), True)
        is_correct = abs(given_val - expected_val) <= tol
        return EvaluatedItemResult(
            attempted=True,
            is_correct=is_correct,
            marks_awarded=float(rule.correct_marks if is_correct else rule.wrong_marks),
            counted_toward_limit=True,
        )

    expected_text = str(correct_answer_jsonb.get("expected_text", "")).strip().lower()
    given_text = str(response_jsonb.get("text_answer", "")).strip().lower()
    is_correct = bool(expected_text and given_text == expected_text)
    return EvaluatedItemResult(
        attempted=True,
        is_correct=is_correct,
        marks_awarded=float(rule.correct_marks if is_correct else rule.wrong_marks),
        counted_toward_limit=True,
    )
