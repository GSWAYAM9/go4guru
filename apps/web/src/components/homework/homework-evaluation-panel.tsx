"use client";

import type {
  HomeworkEvaluationOut,
  HomeworkSubmissionDetailOut,
  HomeworkSubjectSelection,
} from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { MathText } from "@/components/math-text";
import {
  computeRetryProgress,
  describeConfidenceBand,
  formatBytes,
  formatErrorCategoryLabel,
  formatOverallStatus,
  SUBJECT_LABELS,
  SUBJECT_OPTIONS,
} from "@/lib/homework-helpers";

interface HomeworkEvaluationPanelProps {
  submission: HomeworkSubmissionDetailOut;
  busyAction: string | null;
  onSaveOcr: (payload: {
    pages: { page_no: number; corrected_text: string }[];
    subject_override: HomeworkSubjectSelection;
    re_evaluate: boolean;
  }) => Promise<void>;
  onSubmitRetry: (payload: {
    revised_work_text: string;
    student_reflection: string;
  }) => Promise<boolean>;
  onUnlockHint: (nextLevel: 1 | 2 | 3) => Promise<void>;
  onRevealSolution: () => Promise<void>;
}

const STEP_STATUS_STYLES: Record<
  string,
  { label: string; className: string }
> = {
  correct: {
    label: "Correct",
    className: "border-emerald-200 bg-emerald-50/60 text-emerald-900",
  },
  partially_correct: {
    label: "Partial",
    className: "border-amber-200 bg-amber-50/60 text-amber-900",
  },
  incorrect: {
    label: "Needs fix",
    className: "border-rose-200 bg-rose-50/70 text-rose-900",
  },
  missing: {
    label: "Missing step",
    className: "border-rose-200 bg-rose-50/70 text-rose-900",
  },
  uncertain: {
    label: "Review",
    className: "border-slate-200 bg-slate-50 text-slate-800",
  },
};

export function HomeworkEvaluationPanel({
  submission,
  busyAction,
  onSaveOcr,
  onSubmitRetry,
  onUnlockHint,
  onRevealSolution,
}: HomeworkEvaluationPanelProps) {
  const [selectedAttemptNo, setSelectedAttemptNo] = useState<number>(
    submission.latest_evaluation?.attempt_no ?? 1
  );
  const [ocrOpen, setOcrOpen] = useState<boolean>(submission.needs_ocr_review);
  const [ocrDrafts, setOcrDrafts] = useState<Record<number, string>>({});
  const [subjectOverride, setSubjectOverride] =
    useState<HomeworkSubjectSelection>(
      submission.detected_subject ?? submission.selected_subject
    );
  const [retryText, setRetryText] = useState("");
  const [retryReflection, setRetryReflection] = useState("");
  const [confirmRevealStep, setConfirmRevealStep] = useState(false);

  useEffect(() => {
    setSelectedAttemptNo(submission.latest_evaluation?.attempt_no ?? 1);
    setOcrOpen(submission.needs_ocr_review);
    setSubjectOverride(
      submission.detected_subject ?? submission.selected_subject
    );
    const drafts: Record<number, string> = {};
    for (const page of submission.ocr_pages) {
      drafts[page.page_no] = page.effective_text;
    }
    setOcrDrafts(drafts);
    setConfirmRevealStep(false);
  }, [submission]);

  const activeEvaluation: HomeworkEvaluationOut | null =
    submission.latest_evaluation !== null &&
    selectedAttemptNo === submission.latest_evaluation.attempt_no
      ? submission.latest_evaluation
      : (submission.evaluation_history.find(
          (ev) => ev.attempt_no === selectedAttemptNo
        ) ?? submission.latest_evaluation);

  const isLatestAttempt =
    activeEvaluation !== null &&
    submission.latest_evaluation !== null &&
    activeEvaluation.attempt_no === submission.latest_evaluation.attempt_no;

  const retryProgress = computeRetryProgress(submission.evaluation_history);

  async function handleOcrSubmit(e: React.FormEvent) {
    e.preventDefault();
    const pages = submission.ocr_pages
      .map((p) => ({
        page_no: p.page_no,
        corrected_text: (ocrDrafts[p.page_no] ?? p.effective_text).trim(),
      }))
      .filter((p) => p.corrected_text.length > 0);
    if (pages.length === 0) return;
    await onSaveOcr({
      pages,
      subject_override: subjectOverride,
      re_evaluate: true,
    });
  }

  async function handleRetrySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (retryText.trim().length < 3) return;
    const ok = await onSubmitRetry({
      revised_work_text: retryText.trim(),
      student_reflection: retryReflection.trim(),
    });
    if (ok) {
      setRetryText("");
      setRetryReflection("");
    }
  }

  const statusMeta = activeEvaluation
    ? formatOverallStatus(activeEvaluation.overall_status)
    : { label: submission.status.replace("_", " "), tone: "neutral" as const };

  const subjectLabel = activeEvaluation
    ? SUBJECT_LABELS[activeEvaluation.subject_area]
    : submission.detected_subject
      ? SUBJECT_LABELS[submission.detected_subject]
      : "Detecting";

  return (
    <div className="space-y-5">
      {/* 1. Submission & Question Header */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
              <span className="font-semibold text-indigo-700">{subjectLabel}</span>
              <span aria-hidden="true">·</span>
              <span className="tabular-nums">
                {submission.page_count} page{submission.page_count === 1 ? "" : "s"}
              </span>
              {activeEvaluation && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="tabular-nums">
                    Confidence {Math.round(activeEvaluation.confidence * 100)}%
                  </span>
                </>
              )}
              {submission.retry_count > 0 && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="tabular-nums">
                    {submission.retry_count} retr{submission.retry_count === 1 ? "y" : "ies"}
                  </span>
                </>
              )}
            </div>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-900">
              {submission.title}
            </h2>
          </div>

          <StatusBadge tone={statusMeta.tone}>{statusMeta.label}</StatusBadge>
        </div>

        {activeEvaluation && (
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50/80 p-3.5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Detected Question
            </p>
            <div className="mt-1 text-sm font-medium text-slate-900">
              <MathText text={activeEvaluation.detected_question} />
            </div>
            <p className="mt-2 text-sm text-slate-700">
              <MathText text={activeEvaluation.feedback_summary} />
            </p>
            <p className="mt-2 text-xs text-slate-500">
              {describeConfidenceBand(activeEvaluation.confidence_band)}
              {activeEvaluation.validation_report.verifier_agreement === "verified" &&
                " · Deterministic math/science verifier confirmed"}
            </p>
          </div>
        )}

        {/* Attempt switcher & retry progress bar */}
        {submission.evaluation_history.length > 1 && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-slate-600">Attempt:</span>
              {[...submission.evaluation_history]
                .sort((a, b) => a.attempt_no - b.attempt_no)
                .map((ev) => (
                  <button
                    key={ev.id}
                    type="button"
                    onClick={() => setSelectedAttemptNo(ev.attempt_no)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium transition tabular-nums ${
                      ev.attempt_no === activeEvaluation?.attempt_no
                        ? "bg-indigo-700 text-white"
                        : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    #{ev.attempt_no}
                  </button>
                ))}
            </div>
            {retryProgress && (
              <p className="text-xs font-medium text-slate-700 tabular-nums">
                {retryProgress.improved
                  ? `Progress: ${retryProgress.errorsResolved} error(s) resolved across ${retryProgress.attemptCount} attempts`
                  : `${retryProgress.latestErrors} issue(s) remaining on Attempt #${retryProgress.attemptCount}`}
              </p>
            )}
          </div>
        )}
      </section>

      {/* 2. OCR Extraction & Correction Drawer */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Uploaded Pages & OCR Transcription
            </h3>
            <p className="text-xs text-slate-600">
              {submission.needs_ocr_review
                ? "OCR confidence is low or unavailable — confirm or edit the extracted text and click Re-Evaluate."
                : "Inspect extracted text or correct any misread handwriting symbol at any time."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setOcrOpen((v) => !v)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-50"
          >
            {ocrOpen ? "Hide OCR Editor" : "Review / Edit OCR"}
          </button>
        </div>

        {ocrOpen && (
          <form onSubmit={(e) => void handleOcrSubmit(e)} className="mt-4 space-y-4">
            {submission.files.length > 0 && (
              <div className="flex flex-wrap gap-3 text-xs text-slate-600">
                {submission.files.map((f) => (
                  <span
                    key={f.id}
                    className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 tabular-nums"
                  >
                    Page {f.page_no}: {f.original_filename} ({f.detected_format.toUpperCase()} ·{" "}
                    {formatBytes(f.size_bytes)}
                    {f.exif_stripped ? " · EXIF stripped" : ""})
                  </span>
                ))}
              </div>
            )}

            {submission.ocr_pages.map((page) => (
              <div
                key={page.id}
                className="rounded-lg border border-slate-200 bg-slate-50/50 p-3.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-slate-800 tabular-nums">
                    Page {page.page_no} · {page.ocr_provider.replace(/_/g, " ")}
                  </span>
                  <span className="text-slate-600 tabular-nums">
                    Confidence {Math.round(page.confidence * 100)}%
                    {page.handwriting_detected ? " · Handwriting detected" : ""}
                  </span>
                </div>
                {page.warnings.length > 0 && (
                  <p className="mt-1.5 text-xs text-amber-800">
                    {page.warnings.join(" ")}
                  </p>
                )}
                <label
                  htmlFor={`ocr-page-${page.page_no}`}
                  className="mt-2 block text-xs font-medium text-slate-700"
                >
                  Extracted transcription (editable)
                </label>
                <textarea
                  id={`ocr-page-${page.page_no}`}
                  rows={4}
                  value={ocrDrafts[page.page_no] ?? ""}
                  onChange={(e) =>
                    setOcrDrafts((prev) => ({
                      ...prev,
                      [page.page_no]: e.target.value,
                    }))
                  }
                  placeholder="Type or correct the question on line 1 and your steps below..."
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            ))}

            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="min-w-48">
                <label
                  htmlFor="ocr-subject-override"
                  className="block text-xs font-medium text-slate-700"
                >
                  Subject for re-evaluation
                </label>
                <select
                  id="ocr-subject-override"
                  value={subjectOverride}
                  onChange={(e) =>
                    setSubjectOverride(e.target.value as HomeworkSubjectSelection)
                  }
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900"
                >
                  {SUBJECT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={busyAction !== null}
                className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {busyAction === "ocr"
                  ? "Re-Evaluating..."
                  : "Save Transcription & Re-Evaluate"}
              </button>
            </div>
          </form>
        )}
      </section>

      {activeEvaluation && (
        <>
          {/* 3. Step-by-Step Evaluation & Error Classifications */}
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
            <section
              aria-labelledby="steps-eval-heading"
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs xl:col-span-7"
            >
              <h3
                id="steps-eval-heading"
                className="text-sm font-semibold text-slate-900"
              >
                Step-by-Step Evaluation
              </h3>

              {activeEvaluation.step_evaluations.length === 0 ? (
                <p className="mt-3 text-xs text-slate-600">
                  No individual working steps were extracted yet. Use the OCR
                  editor above or submit a retry with numbered steps.
                </p>
              ) : (
                <ol className="mt-3 space-y-2.5">
                  {activeEvaluation.step_evaluations.map((step) => {
                    const style =
                      STEP_STATUS_STYLES[step.status] ??
                      STEP_STATUS_STYLES.uncertain;
                    return (
                      <li
                        key={step.step_no}
                        className={`rounded-lg border p-3 ${style.className}`}
                      >
                        <div className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-semibold tabular-nums">
                            Step {step.step_no}
                          </span>
                          <span className="font-medium">{style.label}</span>
                        </div>
                        <div className="mt-1 text-sm font-medium text-slate-900">
                          <MathText text={step.student_work} />
                        </div>
                        <p className="mt-1 text-xs text-slate-700">
                          <MathText text={step.explanation} />
                        </p>
                        {step.error_categories.length > 0 && (
                          <p className="mt-1.5 text-xs font-medium text-rose-800">
                            Error type:{" "}
                            {step.error_categories
                              .map(formatErrorCategoryLabel)
                              .join(" · ")}
                          </p>
                        )}
                      </li>
                    );
                  })}
                </ol>
              )}

              {activeEvaluation.strengths.length > 0 && (
                <div className="mt-4 border-t border-slate-200 pt-3">
                  <p className="text-xs font-semibold text-emerald-900">
                    What you did well
                  </p>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-xs text-slate-700">
                    {activeEvaluation.strengths.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

            {/* Subject-Aware Error Classifications */}
            <section
              aria-labelledby="errors-heading"
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs xl:col-span-5"
            >
              <h3
                id="errors-heading"
                className="text-sm font-semibold text-slate-900"
              >
                {subjectLabel} Diagnostic Findings
              </h3>
              {activeEvaluation.error_classifications.length === 0 ? (
                <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3 text-xs text-emerald-900">
                  No subject-level errors detected in this attempt.
                </div>
              ) : (
                <ul className="mt-3 space-y-2.5">
                  {activeEvaluation.error_classifications.map((err, idx) => (
                    <li
                      key={`${err.category}-${err.step_no ?? "all"}-${idx}`}
                      className="rounded-lg border border-slate-200 bg-slate-50/70 p-3"
                    >
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span className="font-semibold text-slate-900">
                          {formatErrorCategoryLabel(err.category)}
                          {err.step_no ? ` · Step ${err.step_no}` : ""}
                        </span>
                        <span
                          className={`font-medium uppercase ${
                            err.severity === "high"
                              ? "text-rose-700"
                              : err.severity === "medium"
                                ? "text-amber-700"
                                : "text-slate-600"
                          }`}
                        >
                          {err.severity}
                        </span>
                      </div>
                      <p className="mt-1 text-xs font-medium text-slate-800">
                        {err.summary}
                      </p>
                      <p className="mt-1 text-xs text-slate-600">
                        {err.guidance}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {/* 4. Graduated Hints Coach (Anti-Spoiler Guard) */}
          <section
            aria-labelledby="hints-coach-heading"
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <h3
                  id="hints-coach-heading"
                  className="text-sm font-semibold text-slate-900"
                >
                  Graduated Hints Coach
                </h3>
                <p className="text-xs text-slate-600">
                  Complete solution stays hidden by default so you can fix the
                  error yourself step-by-step.
                </p>
              </div>
              <span className="text-xs font-medium text-slate-600 tabular-nums">
                Unlocked {activeEvaluation.current_hint_level_unlocked} of{" "}
                {activeEvaluation.max_hint_level} hints
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {activeEvaluation.unlocked_hints.map((hint) => (
                <div
                  key={hint.level}
                  className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3.5"
                >
                  <p className="text-xs font-semibold text-indigo-900">
                    {hint.title}
                  </p>
                  <div className="mt-1 text-sm text-slate-800">
                    <MathText text={hint.content_markdown} />
                  </div>
                </div>
              ))}
            </div>

            {isLatestAttempt && (
              <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-3">
                {activeEvaluation.has_more_hints && (
                  <button
                    type="button"
                    disabled={busyAction !== null}
                    onClick={() =>
                      void onUnlockHint(
                        Math.min(
                          3,
                          activeEvaluation.current_hint_level_unlocked + 1
                        ) as 1 | 2 | 3
                      )
                    }
                    className="rounded-lg border border-indigo-300 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-900 hover:bg-indigo-100 disabled:opacity-50"
                  >
                    {busyAction === "hint"
                      ? "Unlocking Hint..."
                      : `Unlock Hint Level ${Math.min(
                          3,
                          activeEvaluation.current_hint_level_unlocked + 1
                        )}`}
                  </button>
                )}

                {!activeEvaluation.solution_revealed && !confirmRevealStep && (
                  <button
                    type="button"
                    onClick={() => setConfirmRevealStep(true)}
                    className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Reveal Complete Solution
                  </button>
                )}

                {!activeEvaluation.solution_revealed && confirmRevealStep && (
                  <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                    <span>
                      Try submitting a retry first — reveal full solution now?
                    </span>
                    <button
                      type="button"
                      disabled={busyAction !== null}
                      onClick={() => void onRevealSolution()}
                      className="rounded bg-amber-800 px-2.5 py-1 font-semibold text-white hover:bg-amber-900 disabled:opacity-50"
                    >
                      {busyAction === "reveal"
                        ? "Revealing..."
                        : "Confirm Reveal"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmRevealStep(false)}
                      className="rounded border border-amber-300 bg-white px-2.5 py-1 font-medium text-amber-900 hover:bg-amber-100"
                    >
                      Keep Practicing
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeEvaluation.solution_revealed &&
              activeEvaluation.complete_solution_markdown && (
                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Revealed Complete Solution
                  </p>
                  <div className="mt-2 whitespace-pre-wrap text-sm text-slate-900">
                    <MathText text={activeEvaluation.complete_solution_markdown} />
                  </div>
                </div>
              )}
          </section>

          {/* 5. Student Retry Workflow */}
          {isLatestAttempt && (
            <section
              aria-labelledby="retry-heading"
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
            >
              <h3
                id="retry-heading"
                className="text-sm font-semibold text-slate-900"
              >
                Try Again — Submit Revised Steps
              </h3>
              <p className="mt-1 text-xs text-slate-600">
                Apply the hint above and rewrite your steps. Homework AI will
                re-verify your work and track errors resolved from Attempt #
                {activeEvaluation.attempt_no}.
              </p>

              <form
                onSubmit={(e) => void handleRetrySubmit(e)}
                className="mt-3 space-y-3"
              >
                <div>
                  <label
                    htmlFor="homework-retry-work"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Your revised solution steps
                  </label>
                  <textarea
                    id="homework-retry-work"
                    rows={4}
                    required
                    minLength={3}
                    value={retryText}
                    onChange={(e) => setRetryText(e.target.value)}
                    placeholder={"Step 1: 2x = 10 - 4\nStep 2: 2x = 6\nStep 3: x = 3"}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label
                    htmlFor="homework-retry-reflection"
                    className="block text-xs font-medium text-slate-700"
                  >
                    What did you change? (optional reflection)
                  </label>
                  <input
                    id="homework-retry-reflection"
                    type="text"
                    value={retryReflection}
                    onChange={(e) => setRetryReflection(e.target.value)}
                    placeholder="e.g. Subtracted 4 instead of adding 4 when moving across ="
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={busyAction !== null || retryText.trim().length < 3}
                  className="rounded-lg bg-indigo-700 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-800 disabled:opacity-50"
                >
                  {busyAction === "retry"
                    ? "Evaluating Revised Attempt..."
                    : "Submit Revised Attempt"}
                </button>
              </form>
            </section>
          )}

          {/* 6. Revision Recommendations */}
          {activeEvaluation.revision_recommendations.length > 0 && (
            <section
              aria-labelledby="revision-recs-heading"
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
            >
              <h3
                id="revision-recs-heading"
                className="text-sm font-semibold text-slate-900"
              >
                Recommended Next Revision
              </h3>
              <ul className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                {activeEvaluation.revision_recommendations.map((rec, idx) => (
                  <li
                    key={`${rec.recommended_action}-${idx}`}
                    className="flex flex-col justify-between rounded-lg border border-slate-200 bg-slate-50/70 p-3.5"
                  >
                    <div>
                      <p className="text-xs font-semibold text-slate-900">
                        {rec.topic_title}
                      </p>
                      <p className="mt-1 text-xs text-slate-600">{rec.reason}</p>
                    </div>
                    <div className="mt-3">
                      <Link
                        href={rec.action_route}
                        className="inline-flex items-center text-xs font-semibold text-indigo-700 hover:text-indigo-900"
                      >
                        Open {rec.action_route.replace("/", "")} →
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
