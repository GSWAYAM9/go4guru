"""Pure-stdlib unit tests for Phase 9 Examination Preparation Ecosystem logic.

Runs directly with `PYTHONPATH=apps/api python3 -m unittest tests/unit/test_phase9_exam_prep_logic.py`.
"""

from __future__ import annotations

import unittest
from datetime import date

from src.modules.assessment.exam_prep_logic import (
    ChapterCoverageInput,
    ExamAnswerObservation,
    ExamAttemptHistoryInput,
    PureScoringRule,
    PyqProvenanceInput,
    RevisionChapterCandidate,
    apply_section_attempt_limit,
    compute_exam_analytics,
    compute_exam_coverage_audit,
    evaluate_exam_response,
    generate_exam_revision_schedule,
    validate_pyq_provenance,
)


class TestStrictPyqProvenance(unittest.TestCase):
    def test_accepts_verified_pyq_with_full_provenance(self) -> None:
        decision = validate_pyq_provenance(
            PyqProvenanceInput(
                is_pyq=True,
                ai_generated=False,
                source_type="OFFICIAL_EXAM_PAPER",
                verification_status="verified",
                verified_by="11111111-1111-1111-1111-111111111111",
                exam_name="JEE Main",
                exam_year=2024,
                exam_session="January",
                exam_shift="Shift 1",
                paper_code="JM24-J1",
            )
        )
        self.assertTrue(decision.is_verified_pyq)
        self.assertEqual(decision.badge_label, "JEE Main · 2024 · January · Shift 1")
        self.assertEqual(decision.rejection_reasons, ())

    def test_rejects_ai_generated_question_even_if_marked_verified(self) -> None:
        decision = validate_pyq_provenance(
            PyqProvenanceInput(
                is_pyq=True,
                ai_generated=True,
                source_type="ORIGINAL_PLATFORM",
                verification_status="verified",
                verified_by="11111111-1111-1111-1111-111111111111",
                exam_name="NEET",
                exam_year=2023,
            )
        )
        self.assertFalse(decision.is_verified_pyq)
        self.assertIsNone(decision.badge_label)
        self.assertIn("ai_generated_questions_cannot_be_pyq", decision.rejection_reasons)

    def test_rejects_unverified_or_missing_verifier_or_missing_year(self) -> None:
        decision = validate_pyq_provenance(
            PyqProvenanceInput(
                is_pyq=True,
                ai_generated=False,
                source_type="OFFICIAL_EXAM_PAPER",
                verification_status="unverified",
                verified_by=None,
                exam_name="",
                exam_year=None,
            )
        )
        self.assertFalse(decision.is_verified_pyq)
        self.assertIn("verification_status_not_verified", decision.rejection_reasons)
        self.assertIn("missing_verifier_identity", decision.rejection_reasons)
        self.assertIn("missing_exam_name", decision.rejection_reasons)
        self.assertIn("invalid_or_missing_exam_year", decision.rejection_reasons)


class TestExamSpecificScoringRules(unittest.TestCase):
    def test_cbse_board_no_negative_marking(self) -> None:
        rule = PureScoringRule(mode="standard", correct_marks=1.0, wrong_marks=0.0)
        ok = evaluate_exam_response(
            question_type="assertion_reason",
            correct_answer={"correct_key": "A"},
            response={"selected_key": "A"},
            rule=rule,
        )
        wrong = evaluate_exam_response(
            question_type="assertion_reason",
            correct_answer={"correct_key": "A"},
            response={"selected_key": "D"},
            rule=rule,
        )
        self.assertEqual(ok.marks_awarded, 1.0)
        self.assertTrue(ok.is_correct)
        self.assertEqual(wrong.marks_awarded, 0.0)
        self.assertFalse(wrong.is_correct)

    def test_jee_main_mcq_and_numerical_with_section_attempt_limit(self) -> None:
        rule = PureScoringRule(mode="standard", correct_marks=4.0, wrong_marks=-1.0)
        num_ok = evaluate_exam_response(
            question_type="numerical",
            correct_answer={"expected_value": 9.81, "tolerance_abs": 0.02},
            response={"numeric_value": 9.8},
            rule=rule,
        )
        num_wrong = evaluate_exam_response(
            question_type="numerical",
            correct_answer={"expected_value": 9.81, "tolerance_abs": 0.02},
            response={"numeric_value": 10.5},
            rule=rule,
        )
        blank = evaluate_exam_response(
            question_type="numerical",
            correct_answer={"expected_value": 9.81},
            response={},
            rule=rule,
        )
        self.assertEqual(num_ok.marks_awarded, 4.0)
        self.assertEqual(num_wrong.marks_awarded, -1.0)
        self.assertEqual(blank.marks_awarded, 0.0)

        # JEE Main Section B (5 of 10) — 6th attempted question must be discarded
        raw_results = [num_ok, num_ok, num_ok, num_ok, num_ok, num_ok]
        adjusted, discarded = apply_section_attempt_limit(raw_results, attempt_limit=5)
        self.assertEqual(discarded, 1)
        self.assertEqual(sum(r.marks_awarded for r in adjusted), 20.0)
        self.assertFalse(adjusted[5].attempted)

    def test_jee_advanced_exact_partial_marking_and_matrix_match(self) -> None:
        adv_rule = PureScoringRule(mode="jee_adv_partial", correct_marks=4.0, wrong_marks=-2.0)
        correct_4 = {"correct_keys": ["A", "B", "C", "D"]}

        full = evaluate_exam_response(
            question_type="mcq_multiple",
            correct_answer=correct_4,
            response={"selected_keys": ["A", "B", "C", "D"]},
            rule=adv_rule,
        )
        three_of_four = evaluate_exam_response(
            question_type="mcq_multiple",
            correct_answer=correct_4,
            response={"selected_keys": ["A", "C", "D"]},
            rule=adv_rule,
        )
        two_of_four = evaluate_exam_response(
            question_type="mcq_multiple",
            correct_answer=correct_4,
            response={"selected_keys": ["A", "B"]},
            rule=adv_rule,
        )
        one_of_four = evaluate_exam_response(
            question_type="mcq_multiple",
            correct_answer=correct_4,
            response={"selected_keys": ["B"]},
            rule=adv_rule,
        )
        wrong_included = evaluate_exam_response(
            question_type="mcq_multiple",
            correct_answer={"correct_keys": ["A", "B"]},
            response={"selected_keys": ["A", "C"]},
            rule=adv_rule,
        )
        self.assertEqual(full.marks_awarded, 4.0)
        self.assertTrue(full.is_correct)
        self.assertEqual(three_of_four.marks_awarded, 3.0)
        self.assertTrue(three_of_four.is_partial)
        self.assertEqual(two_of_four.marks_awarded, 2.0)
        self.assertEqual(one_of_four.marks_awarded, 1.0)
        self.assertEqual(wrong_included.marks_awarded, -2.0)

        match_rule = PureScoringRule(mode="standard", correct_marks=3.0, wrong_marks=-1.0)
        match_ok = evaluate_exam_response(
            question_type="match_following",
            correct_answer={"expected_matches": {"P": "2", "Q": "1"}},
            response={"matches": {"p": "2", "q": "1"}},
            rule=match_rule,
        )
        self.assertTrue(match_ok.is_correct)
        self.assertEqual(match_ok.marks_awarded, 3.0)

    def test_neet_optional_section_b_limit_10_of_15(self) -> None:
        rule = PureScoringRule(mode="standard", correct_marks=4.0, wrong_marks=-1.0)
        ok = evaluate_exam_response(
            question_type="mcq_single",
            correct_answer={"correct_key": "B"},
            response={"selected_key": "B"},
            rule=rule,
        )
        results = [ok] * 12
        adjusted, discarded = apply_section_attempt_limit(results, attempt_limit=10)
        self.assertEqual(discarded, 2)
        self.assertEqual(sum(r.marks_awarded for r in adjusted), 40.0)


class TestHonestCoverageAudit(unittest.TestCase):
    def test_never_claims_complete_when_unaudited_or_missing_questions(self) -> None:
        unverified = compute_exam_coverage_audit(
            exam_code="JEE_MAIN",
            chapters=[
                ChapterCoverageInput("c1", False, "included", 12, 3),
                ChapterCoverageInput("c2", False, "included", 0, 0),
            ],
            total_published_questions=12,
            total_verified_pyqs=3,
            unverified_pyq_excluded_count=2,
        )
        self.assertEqual(unverified.coverage_status, "partial_unverified")
        self.assertEqual(unverified.unverified_pyq_excluded_count, 2)
        self.assertIn("not claimed", unverified.coverage_disclaimer.lower())

        audited_but_missing_q = compute_exam_coverage_audit(
            exam_code="NEET",
            chapters=[
                ChapterCoverageInput("c1", True, "included", 10, 4),
                ChapterCoverageInput("c2", True, "included", 0, 0),
            ],
            total_published_questions=10,
            total_verified_pyqs=4,
        )
        self.assertEqual(audited_but_missing_q.coverage_status, "audited_partial")

        complete = compute_exam_coverage_audit(
            exam_code="CBSE_BOARD",
            chapters=[
                ChapterCoverageInput("c1", True, "included", 15, 2),
                ChapterCoverageInput("c2", True, "included", 10, 1),
            ],
            total_published_questions=25,
            total_verified_pyqs=3,
        )
        self.assertEqual(complete.coverage_status, "audited_complete")
        self.assertEqual(complete.audited_coverage_pct, 100.0)


class TestAnalyticsAndRevisionSchedule(unittest.TestCase):
    def test_analytics_detects_rushing_errors_and_weak_chapters(self) -> None:
        observations = [
            ExamAnswerObservation("a1", "s1", "Physics", "c1", "Electrostatics", "co1", "Gauss Law", False, True, -1.0, 4.0, 22),
            ExamAnswerObservation("a1", "s1", "Physics", "c1", "Electrostatics", "co1", "Gauss Law", False, True, -1.0, 4.0, 28),
            ExamAnswerObservation("a1", "s2", "Biology", "c2", "Genetics", "co2", "Mendelian Cross", True, True, 4.0, 4.0, 35),
        ]
        history = [
            ExamAttemptHistoryInput("a1", "NEET Mock 1", "neet", "2026-11-20T10:00:00+00:00", 2.0, 12.0, 33.3, 28.3)
        ]
        summary = compute_exam_analytics(
            exam_code="NEET",
            observations=observations,
            history=history,
        )
        self.assertEqual(summary.pacing_status, "rushing_errors")
        self.assertEqual(summary.target_seconds_per_question, 60)
        self.assertEqual(summary.weak_chapters[0].name, "Electrostatics")
        self.assertEqual(summary.weak_chapters[0].severity, "critical")
        self.assertTrue(any("Electrostatics" in r for r in summary.improvement_recommendations))

    def test_revision_schedule_prioritizes_weak_high_yield_and_includes_mocks(self) -> None:
        chapters = [
            RevisionChapterCandidate("c1", "Organic Chemistry", "Chemistry", 12.0, "high_yield", 40.0, 6),
            RevisionChapterCandidate("c2", "Kinematics", "Physics", 5.0, "core", 85.0, 2),
        ]
        schedule = generate_exam_revision_schedule(
            exam_code="JEE_MAIN",
            start_date=date(2026, 11, 26),
            target_exam_date=date(2026, 12, 2),
            daily_minutes=90,
            chapters=chapters,
        )
        self.assertEqual(len(schedule), 7)
        # Day 1 prioritizes Organic Chemistry (weak + high yield)
        self.assertIn("Organic Chemistry", schedule[0]["blocks"][0]["title"])
        # Day 5 is a timed mock day
        self.assertEqual(schedule[4]["blocks"][0]["activity"], "timed_mock")
        self.assertEqual(schedule[0]["total_minutes"], 90)


if __name__ == "__main__":
    unittest.main()
