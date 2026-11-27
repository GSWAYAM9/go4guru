"use client";

import type { ExamAnalyticsResponse, WeaknessBucketOut } from "@go4guru/contracts";
import { EmptyState, StatusBadge } from "@go4guru/ui";
import { getPacingBadgeMeta } from "@/lib/exam-prep-helpers";

interface ExamAnalyticsTabProps {
  analytics: ExamAnalyticsResponse | null;
}

function WeaknessList({
  title,
  emptyLabel,
  items,
}: {
  title: string;
  emptyLabel: string;
  items: WeaknessBucketOut[];
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
      <h3 className="text-sm font-bold text-slate-900">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500">{emptyLabel}</p>
      ) : (
        <ul className="mt-3 space-y-2.5">
          {items.map((item) => (
            <li
              key={`${item.entity_id ?? item.name}`}
              className="rounded-lg border border-slate-100 bg-slate-50 p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-900">
                  {item.name}
                </span>
                <StatusBadge
                  tone={
                    item.severity === "critical" || item.severity === "needs_focus"
                      ? "degraded"
                      : "neutral"
                  }
                >
                  {item.accuracy_pct.toFixed(1)}%
                </StatusBadge>
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-slate-600">
                <span>
                  {item.correct}/{item.attempts} correct
                </span>
                <span>Avg {item.avg_seconds.toFixed(0)}s/Q</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ExamAnalyticsTab({ analytics }: ExamAnalyticsTabProps) {
  if (!analytics) {
    return (
      <EmptyState
        title="Exam analytics unavailable"
        description="Select an examination track to view accuracy, pacing, and weak-area diagnostics."
      />
    );
  }

  const pacing = getPacingBadgeMeta(analytics.pacing_status);

  return (
    <div className="space-y-6">
      {/* Top KPI Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
          <p className="text-xs font-medium text-slate-500">Overall Accuracy</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {analytics.overall_accuracy_pct.toFixed(1)}%
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Across {analytics.total_questions_answered} answered Qs
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
          <p className="text-xs font-medium text-slate-500">Average Speed</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {analytics.average_seconds_per_question > 0
              ? `${analytics.average_seconds_per_question.toFixed(0)}s/Q`
              : "—"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Exam target: {analytics.target_seconds_per_question}s/Q
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
          <p className="text-xs font-medium text-slate-500">Pacing Diagnosis</p>
          <div className="mt-2">
            <StatusBadge tone={pacing.tone}>{pacing.label}</StatusBadge>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Calibrated for {analytics.exam_name}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
          <p className="text-xs font-medium text-slate-500">
            Completed Attempts
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {analytics.total_attempts}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Timed mocks &amp; chapter drills
          </p>
        </div>
      </div>

      {/* Weak Subjects / Chapters / Concepts */}
      <div className="grid gap-4 lg:grid-cols-3">
        <WeaknessList
          title="Weak Subjects (<70%)"
          emptyLabel="No weak subjects flagged yet."
          items={analytics.weak_subjects}
        />
        <WeaknessList
          title="Weak Chapters (<70%)"
          emptyLabel="No weak chapters flagged yet."
          items={analytics.weak_chapters}
        />
        <WeaknessList
          title="Weak Concepts (<70%)"
          emptyLabel="No weak concepts flagged yet."
          items={analytics.weak_concepts}
        />
      </div>

      {/* Improvement Recommendations */}
      <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-5">
        <h3 className="text-sm font-bold text-indigo-950">
          Targeted Improvement Recommendations
        </h3>
        <ul className="mt-3 space-y-2 text-xs leading-relaxed text-slate-800">
          {analytics.improvement_recommendations.map((rec, idx) => (
            <li
              key={idx}
              className="flex items-start gap-2 rounded-lg bg-white px-3 py-2.5 shadow-2xs"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[11px] font-bold text-indigo-800">
                {idx + 1}
              </span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
