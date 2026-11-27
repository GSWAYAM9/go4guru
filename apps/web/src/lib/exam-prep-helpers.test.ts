import assert from "node:assert/strict";
import test from "node:test";
import type { ExamCoverageAuditOut, ExamPatternOut, ExamQuestionItemOut } from "@go4guru/contracts";
import {
  computePatternMaxMarks,
  computePatternTotalQuestions,
  formatAnswerPayload,
  formatExamDuration,
  formatQuestionTypeLabel,
  formatScoringRuleLabel,
  getCoverageBadgeMeta,
  getPacingBadgeMeta,
  hasVerifiedPyqBadge,
} from "./exam-prep-helpers";

test("formatScoringRuleLabel describes CBSE no-negative, JEE Main +4/-1, and JEE Advanced partial rules", () => {
  assert.equal(
    formatScoringRuleLabel({
      mode: "standard",
      correct_marks: 1,
      wrong_marks: 0,
      unanswered_marks: 0,
      partial_credit_per_correct_option: 0,
    }),
    "+1 / 0 (No Negative)"
  );
  assert.equal(
    formatScoringRuleLabel({
      mode: "standard",
      correct_marks: 4,
      wrong_marks: -1,
      unanswered_marks: 0,
      partial_credit_per_correct_option: 0,
    }),
    "+4 / -1"
  );
  assert.equal(
    formatScoringRuleLabel({
      mode: "jee_adv_partial",
      correct_marks: 4,
      wrong_marks: -2,
      unanswered_marks: 0,
      partial_credit_per_correct_option: 1,
    }),
    "+4/+3/+2/+1 / -2 (Partial Subset)"
  );
});

test("computePatternMaxMarks respects optional section attempt_limit (e.g. NEET Sec-B 10 of 15)", () => {
  const pattern: ExamPatternOut = {
    id: "p1",
    exam_track_id: "t1",
    exam_track_code: "NEET",
    exam_track_name: "NEET-UG",
    version_label: "neet-2026-v1",
    effective_year: 2026,
    is_active: true,
    rules: {
      duration_seconds: 12000,
      grace_seconds: 30,
      shuffle_questions: true,
      shuffle_options: true,
      retake_policy: { max_attempts: null, cooldown_minutes: 0 },
      sections: [
        {
          code: "SEC-A",
          name: "Mandatory",
          question_count: 35,
          attempt_limit: null,
          allowed_question_types: ["mcq_single"],
          difficulty_distribution: {},
          question_type_distribution: {},
          scoring: {
            mode: "standard",
            correct_marks: 4,
            wrong_marks: -1,
            unanswered_marks: 0,
            partial_credit_per_correct_option: 0,
          },
        },
        {
          code: "SEC-B",
          name: "Optional 10 of 15",
          question_count: 15,
          attempt_limit: 10,
          allowed_question_types: ["mcq_single"],
          difficulty_distribution: {},
          question_type_distribution: {},
          scoring: {
            mode: "standard",
            correct_marks: 4,
            wrong_marks: -1,
            unanswered_marks: 0,
            partial_credit_per_correct_option: 0,
          },
        },
      ],
    },
  };

  assert.equal(computePatternTotalQuestions(pattern), 50);
  assert.equal(computePatternMaxMarks(pattern), 180); // (35 + 10) * 4
  assert.equal(formatExamDuration(12000), "3h 20m");
});

test("getCoverageBadgeMeta honestly labels partial/unverified vs audited complete", () => {
  const partialAudit: ExamCoverageAuditOut = {
    exam_code: "JEE_MAIN",
    mapped_chapters_count: 10,
    included_chapters_count: 10,
    audited_chapters_count: 3,
    chapters_with_questions_count: 4,
    published_question_count: 20,
    verified_pyq_count: 5,
    unverified_pyq_excluded_count: 2,
    audited_coverage_pct: 30,
    question_coverage_pct: 40,
    coverage_status: "audited_partial",
    coverage_disclaimer: "Partial coverage.",
  };
  assert.equal(getCoverageBadgeMeta(partialAudit).tone, "degraded");
  assert.equal(
    getCoverageBadgeMeta({ ...partialAudit, coverage_status: "audited_complete" }).tone,
    "healthy"
  );
  assert.equal(getPacingBadgeMeta("rushing_errors").tone, "degraded");
  assert.equal(formatQuestionTypeLabel("mcq_multiple"), "Multi-Correct MCQ");
});

test("hasVerifiedPyqBadge rejects null or malformed provenance", () => {
  const baseQ: ExamQuestionItemOut = {
    question_id: "q1",
    question_version_id: "qv1",
    question_type: "mcq_single",
    subject_id: "s1",
    subject_name: "Physics",
    chapter_id: "c1",
    chapter_title: "Electrostatics",
    topic_id: null,
    topic_title: null,
    concept_id: null,
    concept_title: null,
    stem_markdown: "Sample",
    difficulty: "medium",
    default_marks: 4,
    default_negative_marks: 1,
    estimated_seconds: 90,
    options: [],
    pyq_provenance: null,
  };
  assert.equal(hasVerifiedPyqBadge(baseQ), false);
  assert.equal(
    hasVerifiedPyqBadge({
      ...baseQ,
      pyq_provenance: {
        is_verified_pyq: true,
        badge_label: "JEE Main · 2024 · January",
        exam_name: "JEE Main",
        exam_year: 2024,
        exam_session: "January",
        exam_shift: "Shift 1",
        paper_code: "JM24",
        question_number: "12",
        source_url: null,
        verification_status: "verified",
      },
    }),
    true
  );
});

test("formatAnswerPayload renders human-readable options, multi-select, numeric, and match answers", () => {
  assert.equal(formatAnswerPayload({}), "Unattempted");
  assert.equal(formatAnswerPayload({ selected_key: "b" }), "Option B");
  assert.equal(formatAnswerPayload({ correct_keys: ["a", "c"] }), "Options A, C");
  assert.equal(
    formatAnswerPayload({ expected_value: 9.81, tolerance_abs: 0.02 }),
    "9.81 (±0.02)"
  );
  assert.equal(
    formatAnswerPayload({ expected_matches: { P: "2", Q: "1" } }),
    "P→2, Q→1"
  );
});
