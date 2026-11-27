import assert from "node:assert/strict";
import test from "node:test";
import type { HomeworkEvaluationOut } from "@go4guru/contracts";
import {
  computeRetryProgress,
  describeConfidenceBand,
  formatBytes,
  formatErrorCategoryLabel,
  formatOverallStatus,
  HOMEWORK_MAX_FILE_BYTES,
  HOMEWORK_MAX_PAGES,
  HOMEWORK_MAX_TOTAL_BYTES,
  reorderPageQueue,
  SUBJECT_ERROR_TAXONOMY,
  validateHomeworkFileQueue,
} from "./homework-helpers.ts";

test("validateHomeworkFileQueue accepts valid multi-page images and PDFs", () => {
  const result = validateHomeworkFileQueue([
    { name: "page1.jpg", size: 250_000, type: "image/jpeg" },
    { name: "page2.png", size: 420_000, type: "image/png" },
    { name: "worksheet.pdf", size: 1_200_000, type: "application/pdf" },
  ]);
  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, []);
  assert.equal(result.totalBytes, 1_870_000);
});

test("validateHomeworkFileQueue rejects empty queues, unsupported files, oversized files, and too many pages", () => {
  const emptyRes = validateHomeworkFileQueue([]);
  assert.equal(emptyRes.valid, false);
  assert.match(emptyRes.errors[0] ?? "", /at least one/i);

  const badFormat = validateHomeworkFileQueue([
    { name: "exploit.svg", size: 1024, type: "image/svg+xml" },
    { name: "macro.exe", size: 2048, type: "application/octet-stream" },
  ]);
  assert.equal(badFormat.valid, false);
  assert.equal(badFormat.errors.length, 2);

  const tooLargeSingle = validateHomeworkFileQueue([
    { name: "huge.png", size: HOMEWORK_MAX_FILE_BYTES + 1, type: "image/png" },
  ]);
  assert.equal(tooLargeSingle.valid, false);
  assert.match(tooLargeSingle.errors[0] ?? "", /10 MB/i);

  const tooLargeTotal = validateHomeworkFileQueue([
    { name: "p1.png", size: 9 * 1024 * 1024, type: "image/png" },
    { name: "p2.png", size: 9 * 1024 * 1024, type: "image/png" },
    { name: "p3.png", size: 9 * 1024 * 1024, type: "image/png" },
  ]);
  assert.equal(tooLargeTotal.valid, false);
  assert.ok(tooLargeTotal.totalBytes > HOMEWORK_MAX_TOTAL_BYTES);
  assert.match(tooLargeTotal.errors.join(" "), /25 MB/i);

  const tooManyPages = validateHomeworkFileQueue(
    Array.from({ length: HOMEWORK_MAX_PAGES + 1 }, (_, i) => ({
      name: `page_${i + 1}.jpg`,
      size: 50_000,
      type: "image/jpeg",
    }))
  );
  assert.equal(tooManyPages.valid, false);
  assert.match(tooManyPages.errors[0] ?? "", /Maximum 10 files/i);
});

test("reorderPageQueue moves items immutably and ignores out-of-bounds moves", () => {
  const original = ["p1", "p2", "p3"];
  assert.deepEqual(reorderPageQueue(original, 2, 0), ["p3", "p1", "p2"]);
  assert.deepEqual(reorderPageQueue(original, 0, 1), ["p2", "p1", "p3"]);
  assert.deepEqual(reorderPageQueue(original, -1, 2), ["p1", "p2", "p3"]);
  assert.deepEqual(original, ["p1", "p2", "p3"]);
});

test("subject taxonomy covers all 5 subjects with 6 canonical categories each", () => {
  const subjects = Object.keys(SUBJECT_ERROR_TAXONOMY) as Array<
    keyof typeof SUBJECT_ERROR_TAXONOMY
  >;
  assert.deepEqual(subjects.sort(), [
    "chemistry",
    "english",
    "mathematics",
    "physics",
    "social_science",
  ]);
  for (const subj of subjects) {
    assert.equal(SUBJECT_ERROR_TAXONOMY[subj].length, 6);
  }
  assert.equal(formatErrorCategoryLabel("missing_steps"), "Missing Steps");
  assert.equal(formatErrorCategoryLabel("map_timeline"), "Map Timeline");
  assert.equal(formatBytes(512), "512 B");
  assert.equal(formatBytes(2048), "2.0 KB");
  assert.equal(formatOverallStatus("correct").tone, "healthy");
  assert.match(describeConfidenceBand("uncertain"), /edit transcription/i);
});

test("computeRetryProgress accurately measures errors resolved across attempts", () => {
  const baseEval: Omit<HomeworkEvaluationOut, "id" | "attempt_no" | "overall_status" | "error_classifications"> = {
    subject_area: "mathematics",
    detected_question: "Solve 2x + 4 = 10",
    student_work_summary: "2 steps",
    extracted_steps: [],
    step_evaluations: [],
    feedback_summary: "Check sign",
    strengths: [],
    unlocked_hints: [],
    current_hint_level_unlocked: 1,
    max_hint_level: 3,
    has_more_hints: true,
    solution_revealed: false,
    complete_solution_markdown: null,
    verifier_results: {},
    validation_report: {
      passed: true,
      spoiler_guard_passed: true,
      taxonomy_valid: true,
      verifier_agreement: "verified",
      safety_passed: true,
      confidence_adjusted: false,
      issues: [],
    },
    revision_recommendations: [],
    confidence: 0.88,
    confidence_band: "high",
    provider_used: "deterministic_subject_engine",
    model_id: "sympy-math-evaluator-v1",
    is_fallback: true,
    safety_verdict: "allow",
    created_at: "2026-11-26T12:00:00Z",
  };

  assert.equal(
    computeRetryProgress([
      {
        ...baseEval,
        id: "e1",
        attempt_no: 1,
        overall_status: "needs_correction",
        error_classifications: [
          {
            subject_area: "mathematics",
            category: "sign",
            severity: "high",
            step_no: 1,
            summary: "Sign error",
            guidance: "Subtract 4 from both sides",
          },
        ],
      },
    ]),
    null
  );

  const progress = computeRetryProgress([
    {
      ...baseEval,
      id: "e2",
      attempt_no: 2,
      overall_status: "correct",
      error_classifications: [],
    },
    {
      ...baseEval,
      id: "e1",
      attempt_no: 1,
      overall_status: "needs_correction",
      error_classifications: [
        {
          subject_area: "mathematics",
          category: "sign",
          severity: "high",
          step_no: 1,
          summary: "Sign error",
          guidance: "Subtract 4 from both sides",
        },
        {
          subject_area: "mathematics",
          category: "missing_steps",
          severity: "low",
          step_no: 1,
          summary: "Show intermediate step",
          guidance: "Write both sides clearly",
        },
      ],
    },
  ]);

  assert.deepEqual(progress, {
    attemptCount: 2,
    initialErrors: 2,
    latestErrors: 0,
    errorsResolved: 2,
    improved: true,
  });
});
