"""Unit tests for the configurable Phase 2 exam rule and scoring engine."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.modules.assessment.rule_engine import (
    ExamPatternRules,
    ScoringRule,
    evaluate_question_with_rule,
    is_response_empty,
)


def test_standard_scoring_correct_wrong_and_unanswered() -> None:
    rule = ScoringRule(
        mode="standard",
        correct_marks=4.0,
        wrong_marks=-1.0,
        unanswered_marks=0.0,
    )
    res_ok = evaluate_question_with_rule(
        question_type="mcq_single",
        correct_answer_jsonb={"correct_key": "B"},
        response_jsonb={"selected_key": "b"},
        rule=rule,
    )
    assert res_ok.attempted is True
    assert res_ok.is_correct is True
    assert res_ok.marks_awarded == 4.0

    res_wrong = evaluate_question_with_rule(
        question_type="mcq_single",
        correct_answer_jsonb={"correct_key": "B"},
        response_jsonb={"selected_key": "A"},
        rule=rule,
    )
    assert res_wrong.attempted is True
    assert res_wrong.is_correct is False
    assert res_wrong.marks_awarded == -1.0

    res_blank = evaluate_question_with_rule(
        question_type="mcq_single",
        correct_answer_jsonb={"correct_key": "B"},
        response_jsonb={},
        rule=rule,
    )
    assert res_blank.attempted is False
    assert res_blank.is_correct is False
    assert res_blank.marks_awarded == 0.0


def test_jee_advanced_partial_subset_scoring() -> None:
    rule = ScoringRule(
        mode="partial_subset",
        correct_marks=4.0,
        wrong_marks=-2.0,
        unanswered_marks=0.0,
        partial_credit_per_correct_option=1.0,
    )
    correct = {"correct_keys": ["A", "C", "D"]}

    full = evaluate_question_with_rule(
        question_type="mcq_multiple",
        correct_answer_jsonb=correct,
        response_jsonb={"selected_keys": ["d", "a", "c"]},
        rule=rule,
    )
    assert full.is_correct is True
    assert full.marks_awarded == 4.0

    partial_two = evaluate_question_with_rule(
        question_type="mcq_multiple",
        correct_answer_jsonb=correct,
        response_jsonb={"selected_keys": ["A", "C"]},
        rule=rule,
    )
    assert partial_two.attempted is True
    assert partial_two.is_correct is False
    assert partial_two.marks_awarded == 2.0

    any_wrong_option = evaluate_question_with_rule(
        question_type="mcq_multiple",
        correct_answer_jsonb=correct,
        response_jsonb={"selected_keys": ["A", "B"]},
        rule=rule,
    )
    assert any_wrong_option.is_correct is False
    assert any_wrong_option.marks_awarded == -2.0

    blank = evaluate_question_with_rule(
        question_type="mcq_multiple",
        correct_answer_jsonb=correct,
        response_jsonb={"selected_keys": []},
        rule=rule,
    )
    assert blank.attempted is False
    assert blank.marks_awarded == 0.0


def test_numerical_and_integer_tolerance_scoring() -> None:
    rule = ScoringRule(mode="standard", correct_marks=4.0, wrong_marks=0.0, unanswered_marks=0.0)
    ok = evaluate_question_with_rule(
        question_type="numerical",
        correct_answer_jsonb={"expected_value": 9.81, "tolerance_abs": 0.02},
        response_jsonb={"numeric_value": "9.80"},
        rule=rule,
    )
    assert ok.is_correct is True
    assert ok.marks_awarded == 4.0

    bad = evaluate_question_with_rule(
        question_type="numerical",
        correct_answer_jsonb={"expected_value": 9.81, "tolerance_abs": 0.01},
        response_jsonb={"numeric_value": 9.95},
        rule=rule,
    )
    assert bad.is_correct is False
    assert bad.marks_awarded == 0.0


def test_exam_pattern_rules_validation_rejects_invalid_attempt_limit_or_negative() -> None:
    with pytest.raises(ValidationError):
        ExamPatternRules.model_validate(
            {
                "duration_seconds": 3600,
                "grace_seconds": 15,
                "sections": [
                    {
                        "code": "SEC-A",
                        "name": "Bad Section",
                        "question_count": 5,
                        "attempt_limit": 10,
                    }
                ],
            }
        )

    with pytest.raises(ValidationError):
        ScoringRule.model_validate({"wrong_marks": 1.0})


def test_is_response_empty_variants() -> None:
    assert is_response_empty("mcq_single", {}) is True
    assert is_response_empty("mcq_single", {"selected_key": "  "}) is True
    assert is_response_empty("mcq_single", {"selected_key": "A"}) is False
    assert is_response_empty("mcq_multiple", {"selected_keys": []}) is True
    assert is_response_empty("mcq_multiple", {"selected_keys": ["B"]}) is False
    assert is_response_empty("numerical", {"numeric_value": "  "}) is True
    assert is_response_empty("numerical", {"numeric_value": 0}) is False
