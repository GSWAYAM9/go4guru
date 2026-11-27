"""Configurable, versioned examination scoring & section-rule evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ScoringRule(BaseModel):
    """Configurable per-section or per-quiz marking specification."""

    mode: Literal["standard", "partial_subset", "jee_adv_partial"] = "standard"
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
    from src.modules.assessment.exam_prep_logic import is_answer_blank

    return is_answer_blank(question_type, response_jsonb)


def evaluate_question_with_rule(
    *,
    question_type: str,
    correct_answer_jsonb: dict[str, Any],
    response_jsonb: dict[str, Any],
    rule: ScoringRule,
) -> EvaluatedItemResult:
    """Evaluate one question response strictly using the configured ScoringRule."""
    from src.modules.assessment.exam_prep_logic import PureScoringRule, evaluate_exam_response

    outcome = evaluate_exam_response(
        question_type=question_type,
        correct_answer=correct_answer_jsonb,
        response=response_jsonb,
        rule=PureScoringRule(
            mode=rule.mode,
            correct_marks=rule.correct_marks,
            wrong_marks=rule.wrong_marks,
            unanswered_marks=rule.unanswered_marks,
            partial_credit_per_correct_option=rule.partial_credit_per_correct_option,
        ),
    )
    return EvaluatedItemResult(
        attempted=outcome.attempted,
        is_correct=outcome.is_correct,
        marks_awarded=outcome.marks_awarded,
        counted_toward_limit=outcome.attempted,
    )
