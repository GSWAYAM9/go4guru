"use client";

import type {
  AttemptDetailedSolutionsResponse,
  ExamPatternOut,
  ExamPerformanceHistoryItemOut,
} from "@go4guru/contracts";
import { EmptyState, StatusBadge } from "@go4guru/ui";
import { MathText } from "@/components/math-text";
import {
  computePatternMaxMarks,
  computePatternTotalQuestions,
  formatAnswerPayload,
  formatExamDuration,
  formatQuestionTypeLabel,
  formatScoringRuleLabel,
} from "@/lib/exam-prep-helpers";

interface TimedMocksTabProps {
  examName: string;
  selectedPattern: ExamPatternOut | null;
  history: ExamPerformanceHistoryItemOut[];
  generatingMock: boolean;
  solutionsLoadingId: string | null;
  activeSolutions: AttemptDetailedSolutionsResponse | null;
  onGenerateMock: (verifiedPyqOnly: boolean) => void;
  onOpenSolutions: (attemptId: string) => void;
  onCloseSolutions: () => void;
}

export function TimedMocksTab({
  examName,
  selectedPattern,
  history,
  generatingMock,
  solutionsLoadingId,
  activeSolutions,
  onGenerateMock,
  onOpenSolutions,
  onCloseSolutions,
}: TimedMocksTabProps) {
  return (
    <div className="space-y-6">
      {/* Versioned Pattern Blueprint & Mock Launcher */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">
                Server-Timed Mock Examinations
              </h2>
              {selectedPattern && (
                <StatusBadge tone="healthy">
                  {selectedPattern.version_label}
                </StatusBadge>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-600">
              Timers, section attempt caps, negative/partial marking, and
              idempotent grading are enforced server-side. Solutions stay locked
              until submission.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={generatingMock || !selectedPattern}
              onClick={() => onGenerateMock(false)}
              className="rounded-lg bg-indigo-700 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generatingMock
                ? "Assembling Timed Mock..."
                : `Start ${examName} Full Mock`}
            </button>
            <button
              type="button"
              disabled={generatingMock || !selectedPattern}
              onClick={() => onGenerateMock(true)}
              className="rounded-lg border border-indigo-300 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-900 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Start Verified-PYQ Timed Mock
            </button>
          </div>
        </div>

        {selectedPattern ? (
          <div className="mt-4 space-y-3">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Duration</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900">
                  {formatExamDuration(selectedPattern.rules.duration_seconds)}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Blueprint Questions</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900">
                  {computePatternTotalQuestions(selectedPattern)}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Maximum Marks</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900">
                  {computePatternMaxMarks(selectedPattern)}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Shuffle Policy</p>
                <p className="mt-0.5 text-sm font-bold text-slate-900">
                  {selectedPattern.rules.shuffle_questions
                    ? "Randomized Qs"
                    : "Fixed Blueprint Order"}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Section</th>
                    <th className="px-3 py-2 font-semibold">Question Types</th>
                    <th className="px-3 py-2 font-semibold">Questions</th>
                    <th className="px-3 py-2 font-semibold">Attempt Cap</th>
                    <th className="px-3 py-2 font-semibold">Marking Scheme</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {selectedPattern.rules.sections.map((sec) => (
                    <tr key={sec.code}>
                      <td className="px-3 py-2.5 font-medium text-slate-900">
                        <span className="mr-1.5 font-mono text-indigo-700">
                          {sec.code}
                        </span>
                        {sec.name}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600">
                        {sec.allowed_question_types
                          .map(formatQuestionTypeLabel)
                          .join(", ") || "Any Published"}
                      </td>
                      <td className="px-3 py-2.5 font-semibold text-slate-800">
                        {sec.question_count}
                      </td>
                      <td className="px-3 py-2.5 text-slate-700">
                        {sec.attempt_limit
                          ? `Max ${sec.attempt_limit} of ${sec.question_count}`
                          : "All Mandatory"}
                      </td>
                      <td className="px-3 py-2.5 font-medium text-slate-900">
                        {formatScoringRuleLabel(sec.scoring)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="mt-4">
            <EmptyState
              title="No versioned ExamPattern configured"
              description="Configure an active exam pattern for this track before generating timed mock examinations."
            />
          </div>
        )}
      </div>

      {/* Performance History + Detailed Solutions Trigger */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
        <h3 className="text-base font-bold text-slate-900">
          Performance History &amp; Detailed Solutions
        </h3>
        <p className="mt-0.5 text-xs text-slate-600">
          Inspect step-by-step worked solutions and common-mistake warnings for
          any submitted mock or chapter practice attempt.
        </p>

        {history.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="No submitted attempts yet for this exam track"
              description="Complete a chapter practice set, verified PYQ drill, or full timed mock to see your score trajectory and unlock detailed solutions."
            />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 font-semibold">Assessment</th>
                  <th className="px-3 py-2 font-semibold">Submitted</th>
                  <th className="px-3 py-2 font-semibold">Score</th>
                  <th className="px-3 py-2 font-semibold">Accuracy</th>
                  <th className="px-3 py-2 font-semibold">Avg Speed</th>
                  <th className="px-3 py-2 font-semibold text-right">
                    Solutions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {history.map((item) => {
                  const busy = solutionsLoadingId === item.attempt_id;
                  return (
                    <tr key={item.attempt_id}>
                      <td className="px-3 py-2.5 font-medium text-slate-900">
                        {item.title}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600">
                        {new Date(item.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="px-3 py-2.5 font-semibold text-slate-900">
                        {item.raw_score} / {item.max_score}
                      </td>
                      <td className="px-3 py-2.5">
                        <StatusBadge
                          tone={
                            item.accuracy_pct >= 75
                              ? "healthy"
                              : "degraded"
                          }
                        >
                          {item.accuracy_pct.toFixed(1)}%
                        </StatusBadge>
                      </td>
                      <td className="px-3 py-2.5 text-slate-700">
                        {item.avg_seconds_per_question.toFixed(0)}s/Q
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => onOpenSolutions(item.attempt_id)}
                          className="rounded-md border border-indigo-300 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-900 hover:bg-indigo-100 disabled:opacity-50"
                        >
                          {busy ? "Loading..." : "Detailed Solutions"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detailed Post-Attempt Solutions Panel */}
      {activeSolutions && (
        <section
          aria-label="Detailed Attempt Solutions"
          className="rounded-xl border-2 border-indigo-200 bg-white p-5 shadow-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Detailed Solutions · {activeSolutions.title}
              </h3>
              <p className="text-xs text-slate-600">
                Score:{" "}
                <strong>
                  {activeSolutions.raw_score} / {activeSolutions.max_score}
                </strong>{" "}
                · Accuracy:{" "}
                <strong>{activeSolutions.accuracy_pct.toFixed(1)}%</strong>
              </p>
            </div>
            <button
              type="button"
              onClick={onCloseSolutions}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Close Solutions
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {activeSolutions.items.map((item) => (
              <article
                key={item.question_version_id}
                className="rounded-lg border border-slate-200 bg-slate-50/70 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-600">
                      Q{item.sequence_no}
                    </span>
                    <StatusBadge
                      tone={
                        item.is_correct === true
                          ? "healthy"
                          : item.is_correct === false
                            ? "degraded"
                            : "neutral"
                      }
                    >
                      {item.is_correct === true
                        ? `Correct (+${item.marks_awarded})`
                        : item.marks_awarded > 0
                          ? `Partial (+${item.marks_awarded})`
                          : `Marks: ${item.marks_awarded}`}
                    </StatusBadge>
                    <span className="text-xs text-slate-500">
                      {item.subject_name} · {item.chapter_title}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">
                    Time spent: {item.time_spent_seconds}s
                  </span>
                </div>

                <div className="mt-2 text-sm text-slate-900">
                  <MathText text={item.stem_markdown} />
                </div>

                <div className="mt-3 grid gap-2 sm:grid-cols-2 text-xs">
                  <div className="rounded border border-slate-200 bg-white p-2.5">
                    <span className="font-semibold text-slate-600">
                      Your Response:{" "}
                    </span>
                    <span className="font-medium text-slate-900">
                      {formatAnswerPayload(item.student_response_jsonb)}
                    </span>
                  </div>
                  <div className="rounded border border-emerald-200 bg-emerald-50/60 p-2.5">
                    <span className="font-semibold text-emerald-900">
                      Official Key:{" "}
                    </span>
                    <span className="font-medium text-emerald-900">
                      {formatAnswerPayload(item.correct_answer_jsonb)}
                    </span>
                  </div>
                </div>

                {item.explanation_markdown && (
                  <div className="mt-3 rounded-lg border border-indigo-100 bg-white p-3 text-xs text-slate-800">
                    <p className="font-semibold text-indigo-900">
                      Step-by-Step Explanation
                    </p>
                    <div className="mt-1 leading-relaxed">
                      <MathText text={item.explanation_markdown} />
                    </div>
                    {item.steps.length > 0 && (
                      <ol className="mt-2 list-decimal space-y-1 pl-4">
                        {item.steps.map((step, i) => (
                          <li key={i}>
                            <MathText text={step} />
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                )}

                {item.common_mistakes_markdown && (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">
                    <strong>Common Mistake to Avoid: </strong>
                    <MathText text={item.common_mistakes_markdown} />
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
