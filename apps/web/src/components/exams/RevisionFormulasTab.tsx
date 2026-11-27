"use client";

import type { ExamFormulaOut, ExamRevisionPlanOut } from "@go4guru/contracts";
import { EmptyState, StatusBadge } from "@go4guru/ui";
import { useMemo, useState } from "react";
import { MathText } from "@/components/math-text";

interface RevisionFormulasTabProps {
  examName: string;
  formulas: ExamFormulaOut[];
  revisionPlans: ExamRevisionPlanOut[];
  creatingPlan: boolean;
  onCreateRevisionPlan: (payload: {
    title?: string;
    target_exam_date: string;
    daily_minutes: number;
  }) => Promise<void>;
}

function defaultTargetDateIso(): string {
  const dt = new Date();
  dt.setDate(dt.getDate() + 14);
  return dt.toISOString().slice(0, 10);
}

export function RevisionFormulasTab({
  examName,
  formulas,
  revisionPlans,
  creatingPlan,
  onCreateRevisionPlan,
}: RevisionFormulasTabProps) {
  const [highYieldOnly, setHighYieldOnly] = useState(false);
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [planTitle, setPlanTitle] = useState("");
  const [targetDate, setTargetDate] = useState(defaultTargetDateIso);
  const [dailyMinutes, setDailyMinutes] = useState(120);

  const formulaSubjects = useMemo(() => {
    const map = new Map<string, string>();
    for (const f of formulas) {
      map.set(f.subject_id, f.subject_name);
    }
    return Array.from(map.entries());
  }, [formulas]);

  const filteredFormulas = useMemo(() => {
    return formulas.filter((f) => {
      if (highYieldOnly && !f.is_high_yield) return false;
      if (subjectFilter !== "all" && f.subject_id !== subjectFilter) return false;
      return true;
    });
  }, [formulas, highYieldOnly, subjectFilter]);

  async function handleSubmitPlan(e: React.FormEvent) {
    e.preventDefault();
    await onCreateRevisionPlan({
      title: planTitle.trim() || undefined,
      target_exam_date: targetDate,
      daily_minutes: dailyMinutes,
    });
    setPlanTitle("");
  }

  return (
    <div className="space-y-6">
      {/* Formula Revision Sheets */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              High-Yield Formula Revision Sheets
            </h2>
            <p className="text-xs text-slate-600">
              Quick-scan KaTeX equations, variable units, application criteria,
              and negative-marking pitfalls for {examName}.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-800">
              <input
                type="checkbox"
                checked={highYieldOnly}
                onChange={(e) => setHighYieldOnly(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-700"
              />
              High-Yield Only
            </label>
            <select
              aria-label="Filter formulas by subject"
              value={subjectFilter}
              onChange={(e) => setSubjectFilter(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800"
            >
              <option value="all">All Subjects</option>
              {formulaSubjects.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {filteredFormulas.length === 0 ? (
          <EmptyState
            title="No formula cards published for this filter"
            description="Formula revision cards authored for this exam track will appear here with KaTeX math notation and common pitfalls."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {filteredFormulas.map((formula) => (
              <article
                key={formula.id}
                className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-2xs"
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                      {formula.subject_name} · {formula.chapter_title}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {formula.is_high_yield && (
                        <StatusBadge tone="degraded">High Yield</StatusBadge>
                      )}
                      <StatusBadge tone="neutral">
                        {formula.difficulty}
                      </StatusBadge>
                    </div>
                  </div>
                  <h3 className="mt-1.5 text-sm font-bold text-slate-900">
                    {formula.title}
                  </h3>

                  <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/40 px-3 py-2 text-center text-slate-900">
                    <MathText text={`$$${formula.formula_latex}$$`} />
                  </div>

                  {formula.variables.length > 0 && (
                    <dl className="mt-3 grid grid-cols-1 gap-1 text-xs text-slate-700">
                      {formula.variables.map((v, i) => (
                        <div key={i} className="flex flex-wrap gap-1.5">
                          <dt className="font-mono font-bold text-slate-900">
                            <MathText text={`$${v.symbol}$`} />:
                          </dt>
                          <dd>
                            {v.meaning}
                            {v.unit ? ` (${v.unit})` : ""}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>

                <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 text-xs">
                  <p className="text-slate-700">
                    <strong className="text-slate-900">When to use: </strong>
                    {formula.when_to_use}
                  </p>
                  {formula.common_pitfall && (
                    <p className="rounded bg-amber-50 px-2.5 py-1.5 text-amber-900">
                      <strong>Common pitfall: </strong>
                      {formula.common_pitfall}
                    </p>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Exam Revision Plan Generator & Saved Plans */}
      <section className="grid gap-6 lg:grid-cols-3">
        <form
          onSubmit={(e) => void handleSubmitPlan(e)}
          className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4 lg:col-span-1"
        >
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Generate Exam Revision Plan
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Automatically prioritizes your weakest high-weightage chapters,
              formula reviews, verified PYQ drills, and periodic timed mocks.
            </p>
          </div>

          <div>
            <label
              htmlFor="rev-plan-title"
              className="block text-xs font-semibold text-slate-700"
            >
              Plan Name (Optional)
            </label>
            <input
              id="rev-plan-title"
              type="text"
              value={planTitle}
              onChange={(e) => setPlanTitle(e.target.value)}
              placeholder={`${examName} 14-Day Sprint`}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="rev-target-date"
              className="block text-xs font-semibold text-slate-700"
            >
              Target Exam Date
            </label>
            <input
              id="rev-target-date"
              type="date"
              required
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="rev-daily-mins"
              className="block text-xs font-semibold text-slate-700"
            >
              Daily Study Budget (Minutes)
            </label>
            <input
              id="rev-daily-mins"
              type="number"
              min={15}
              max={600}
              step={15}
              required
              value={dailyMinutes}
              onChange={(e) => setDailyMinutes(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <button
            type="submit"
            disabled={creatingPlan}
            className="w-full rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-50"
          >
            {creatingPlan ? "Generating Plan..." : "Build Revision Schedule"}
          </button>
        </form>

        <div className="space-y-4 lg:col-span-2">
          <h3 className="text-base font-bold text-slate-900">
            Active Revision Schedules ({revisionPlans.length})
          </h3>
          {revisionPlans.length === 0 ? (
            <EmptyState
              title="No revision plan generated yet"
              description="Set your target exam date and daily study budget to generate a weak-chapter-first revision schedule."
            />
          ) : (
            revisionPlans.map((plan) => (
              <div
                key={plan.id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {plan.title}
                    </h4>
                    <p className="text-xs text-slate-600">
                      Target: <strong>{plan.target_exam_date}</strong> ·{" "}
                      {plan.daily_minutes} min/day · {plan.schedule.length} days
                      scheduled
                    </p>
                  </div>
                  <StatusBadge tone="healthy">{plan.status}</StatusBadge>
                </div>

                <div className="space-y-3">
                  {plan.schedule.slice(0, 7).map((day) => (
                    <div
                      key={day.day_number}
                      className="rounded-lg border border-slate-200 bg-slate-50/70 p-3"
                    >
                      <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                        <span>
                          Day {day.day_number} · {day.date}
                        </span>
                        <span className="text-indigo-700">
                          {day.total_minutes} min
                        </span>
                      </div>
                      <ul className="mt-2 space-y-1.5">
                        {day.blocks.map((b, idx) => (
                          <li
                            key={idx}
                            className="flex flex-wrap items-start justify-between gap-2 rounded bg-white px-2.5 py-2 text-xs"
                          >
                            <div>
                              <p className="font-semibold text-slate-900">
                                {b.title}
                              </p>
                              <p className="text-[11px] text-slate-500">
                                {b.focus_note}
                              </p>
                            </div>
                            <span className="shrink-0 rounded bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
                              {b.minutes}m
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
