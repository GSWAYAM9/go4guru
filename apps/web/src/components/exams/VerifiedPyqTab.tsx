"use client";

import type { ExamQuestionsExplorerResponse } from "@go4guru/contracts";
import { EmptyState, StatusBadge } from "@go4guru/ui";
import { MathText } from "@/components/math-text";
import {
  formatQuestionTypeLabel,
  hasVerifiedPyqBadge,
} from "@/lib/exam-prep-helpers";

export interface PyqFilterState {
  verifiedPyqOnly: boolean;
  examYear: string;
  examSession: string;
  difficulty: string;
  questionType: string;
}

interface VerifiedPyqTabProps {
  data: ExamQuestionsExplorerResponse | null;
  filters: PyqFilterState;
  loading: boolean;
  launching: boolean;
  onChangeFilters: (next: PyqFilterState) => void;
  onLaunchFilteredDrill: () => void;
}

export function VerifiedPyqTab({
  data,
  filters,
  loading,
  launching,
  onChangeFilters,
  onLaunchFilteredDrill,
}: VerifiedPyqTabProps) {
  const facets = data?.facets;

  return (
    <div className="space-y-4">
      {/* Strict Provenance Policy Banner + Filters */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Verified PYQ &amp; Exam Question Explorer
            </h2>
            <p className="mt-0.5 text-xs text-slate-600">
              Only questions with verified exam source provenance (exam name,
              year, reviewer sign-off, non-AI origin) receive a Verified PYQ
              badge. Correct answers remain redacted until you submit a drill.
            </p>
          </div>
          <button
            type="button"
            disabled={launching || !data || data.questions.length === 0}
            onClick={onLaunchFilteredDrill}
            className="rounded-lg bg-indigo-700 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {launching
              ? "Starting Timed Drill..."
              : filters.verifiedPyqOnly
                ? "Launch Verified PYQ Drill"
                : "Launch Filtered Practice Set"}
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-800">
            <input
              type="checkbox"
              checked={filters.verifiedPyqOnly}
              onChange={(e) =>
                onChangeFilters({
                  ...filters,
                  verifiedPyqOnly: e.target.checked,
                })
              }
              className="h-4 w-4 rounded border-slate-300 text-indigo-700"
            />
            Verified PYQs Only
          </label>

          <select
            aria-label="Filter by exam year"
            value={filters.examYear}
            onChange={(e) =>
              onChangeFilters({ ...filters, examYear: e.target.value })
            }
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800"
          >
            <option value="">All Years</option>
            {(facets?.available_years ?? []).map((yr) => (
              <option key={yr} value={String(yr)}>
                {yr}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by exam session"
            value={filters.examSession}
            onChange={(e) =>
              onChangeFilters({ ...filters, examSession: e.target.value })
            }
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800"
          >
            <option value="">All Sessions</option>
            {(facets?.available_sessions ?? []).map((sess) => (
              <option key={sess} value={sess}>
                {sess}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by difficulty"
            value={filters.difficulty}
            onChange={(e) =>
              onChangeFilters({ ...filters, difficulty: e.target.value })
            }
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800"
          >
            <option value="">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>

          <select
            aria-label="Filter by exam question type"
            value={filters.questionType}
            onChange={(e) =>
              onChangeFilters({ ...filters, questionType: e.target.value })
            }
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800"
          >
            <option value="">All Question Types</option>
            {(
              facets?.available_question_types ?? [
                "mcq_single",
                "mcq_multiple",
                "numerical",
                "integer",
                "assertion_reason",
                "case_study",
                "match_following",
                "short_answer",
                "long_answer",
              ]
            ).map((qt) => (
              <option key={qt} value={qt}>
                {formatQuestionTypeLabel(qt)}
              </option>
            ))}
          </select>
        </div>

        {facets && facets.unverified_pyq_excluded_count > 0 && (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            Provenance Guard Active:{" "}
            <strong>{facets.unverified_pyq_excluded_count}</strong> unverified
            or AI-generated question(s) claiming PYQ status were automatically
            excluded from verified PYQ listings.
          </p>
        )}
      </div>

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading filtered exam questions...
        </div>
      ) : !data || data.questions.length === 0 ? (
        <EmptyState
          title={
            filters.verifiedPyqOnly
              ? "No verified PYQs match your active filters"
              : "No published questions match your filters"
          }
          description={
            filters.verifiedPyqOnly
              ? "Only reviewer-verified official exam questions with valid year and provenance are displayed here. Try clearing a year/session filter or unchecking Verified PYQs Only to browse original syllabus practice items."
              : "Adjust difficulty or question-type filters to view available published questions."
          }
        />
      ) : (
        <div className="space-y-3">
          {data.questions.map((q, idx) => {
            const verifiedPyq = hasVerifiedPyqBadge(q);
            return (
              <article
                key={q.question_version_id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold text-slate-500">
                      #{idx + 1}
                    </span>
                    <StatusBadge tone="neutral">
                      {formatQuestionTypeLabel(q.question_type)}
                    </StatusBadge>
                    <StatusBadge
                      tone={
                        q.difficulty === "hard" || q.difficulty === "medium"
                          ? "degraded"
                          : "healthy"
                      }
                    >
                      {q.difficulty}
                    </StatusBadge>
                    {verifiedPyq && q.pyq_provenance && (
                      <StatusBadge tone="healthy">
                        Verified PYQ · {q.pyq_provenance.badge_label}
                      </StatusBadge>
                    )}
                  </div>
                  <span className="text-xs text-slate-500">
                    {q.subject_name} · {q.chapter_title}
                    {q.topic_title ? ` · ${q.topic_title}` : ""}
                  </span>
                </div>

                <div className="mt-3 text-sm leading-relaxed text-slate-900">
                  <MathText text={q.stem_markdown} />
                </div>

                {q.options.length > 0 && (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {q.options.map((opt) => (
                      <div
                        key={opt.option_key}
                        className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-800"
                      >
                        <span className="mr-2 font-bold text-indigo-700">
                          ({opt.option_key})
                        </span>
                        <MathText text={opt.content_markdown} />
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2 text-xs text-slate-500">
                  <span>
                    +{q.default_marks} / -{q.default_negative_marks} · Est.{" "}
                    {q.estimated_seconds}s
                  </span>
                  {verifiedPyq && q.pyq_provenance?.paper_code && (
                    <span className="font-mono text-slate-600">
                      Paper: {q.pyq_provenance.paper_code}
                      {q.pyq_provenance.question_number
                        ? ` · Q${q.pyq_provenance.question_number}`
                        : ""}
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
