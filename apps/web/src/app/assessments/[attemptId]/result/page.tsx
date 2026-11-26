"use client";

import type { AttemptResultResponse } from "@go4guru/contracts";
import {
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MathText } from "@/components/math-text";
import { ApiClientError, getAttemptResult } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function AttemptResultPage() {
  const params = useParams<{ attemptId: string }>();
  const attemptId = params.attemptId;
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [result, setResult] = useState<AttemptResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    const authToken = token;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getAttemptResult(authToken, attemptId);
        setResult(res);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        } else {
          setError({
            code: "RESULT_LOAD_FAILED",
            message: "Unable to load attempt scorecard.",
          });
        }
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [initializing, token, router, attemptId]);

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Assessment Scorecard & Solution Review
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Server-computed score, negative/partial marking breakdown, and verified explanations.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/assessments"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            All Assessments
          </Link>
          <Link
            href="/analytics"
            className="rounded-md bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
          >
            View Analytics
          </Link>
        </div>
      </header>

      {loading ? <LoadingCard message="Loading authoritative scorecard..." /> : null}

      {!loading && error ? (
        <ErrorBanner
          title={`Result Unavailable (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      {!loading && result ? (
        <div className="space-y-6">
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-xl font-semibold text-slate-900">
                {result.title}
              </h2>
              <StatusBadge tone="healthy">{result.status}</StatusBadge>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium uppercase text-slate-500">
                  Final Score
                </p>
                <p
                  data-testid="final-score"
                  className="mt-1 text-2xl font-bold text-slate-900"
                >
                  {result.raw_score} / {result.max_score}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium uppercase text-slate-500">
                  Accuracy
                </p>
                <p className="mt-1 text-2xl font-bold text-indigo-700">
                  {result.accuracy_pct}%
                </p>
              </div>
              <div className="rounded-lg bg-emerald-50 p-4">
                <p className="text-xs font-medium uppercase text-emerald-700">
                  Correct
                </p>
                <p className="mt-1 text-2xl font-bold text-emerald-900">
                  {result.correct_count}
                </p>
              </div>
              <div className="rounded-lg bg-rose-50 p-4">
                <p className="text-xs font-medium uppercase text-rose-700">
                  Wrong / Partial
                </p>
                <p className="mt-1 text-2xl font-bold text-rose-900">
                  {result.wrong_count}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium uppercase text-slate-500">
                  Unanswered
                </p>
                <p className="mt-1 text-2xl font-bold text-slate-800">
                  {result.unanswered_count}
                </p>
              </div>
            </div>
          </section>

          {result.section_breakdown.length > 0 ? (
            <section
              aria-labelledby="sections-heading"
              className="overflow-x-auto rounded-xl border border-slate-200 bg-white"
            >
              <h3
                id="sections-heading"
                className="border-b border-slate-200 px-4 py-3 text-base font-semibold text-slate-900"
              >
                Section Breakdown
              </h3>
              <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-600">
                  <tr>
                    <th className="px-4 py-2">Section</th>
                    <th className="px-4 py-2">Attempted</th>
                    <th className="px-4 py-2">Correct</th>
                    <th className="px-4 py-2">Wrong</th>
                    <th className="px-4 py-2">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.section_breakdown.map((sec, idx) => (
                    <tr key={`${sec.section_id ?? idx}`}>
                      <td className="px-4 py-2 font-medium text-slate-900">
                        {sec.section_name}
                      </td>
                      <td className="px-4 py-2">
                        {sec.attempted} / {sec.total_questions}
                      </td>
                      <td className="px-4 py-2 text-emerald-700">
                        {sec.correct}
                      </td>
                      <td className="px-4 py-2 text-rose-700">{sec.wrong}</td>
                      <td className="px-4 py-2 font-semibold">
                        {sec.raw_score} / {sec.max_score}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}

          <section aria-labelledby="review-heading" className="space-y-4">
            <h3
              id="review-heading"
              className="text-lg font-semibold text-slate-900"
            >
              Detailed Answer Review ({result.items.length})
            </h3>
            {result.items.map((item) => (
              <article
                key={item.question_version_id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                  <span className="text-sm font-semibold text-slate-900">
                    Question {item.sequence_no}
                    {item.section_name ? ` · ${item.section_name}` : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    <StatusBadge
                      tone={item.is_correct ? "healthy" : "degraded"}
                    >
                      {item.marks_awarded >= 0
                        ? `+${item.marks_awarded}`
                        : item.marks_awarded}{" "}
                      marks
                    </StatusBadge>
                    <span className="text-xs text-slate-500">
                      {item.time_spent_seconds}s spent
                    </span>
                  </div>
                </div>

                <div className="mt-3 text-sm text-slate-900">
                  <MathText text={item.stem_markdown} />
                </div>

                <div className="mt-3 grid gap-3 rounded-lg bg-slate-50 p-3 text-xs sm:grid-cols-2">
                  <div>
                    <span className="font-semibold text-slate-700">
                      Your Response:
                    </span>{" "}
                    <code className="text-slate-900">
                      {JSON.stringify(item.student_response_jsonb)}
                    </code>
                  </div>
                  <div>
                    <span className="font-semibold text-emerald-800">
                      Correct Answer:
                    </span>{" "}
                    <code className="text-emerald-900">
                      {JSON.stringify(item.correct_answer_jsonb)}
                    </code>
                  </div>
                </div>

                {item.explanation_markdown ? (
                  <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/40 p-3 text-sm text-slate-800">
                    <p className="font-semibold text-indigo-950">
                      Verified Explanation:
                    </p>
                    <div className="mt-1">
                      <MathText text={item.explanation_markdown} />
                    </div>
                    {item.steps.length > 0 ? (
                      <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs">
                        {item.steps.map((s, sIdx) => (
                          <li key={sIdx}>
                            <MathText text={s} />
                          </li>
                        ))}
                      </ol>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))}
          </section>
        </div>
      ) : null}
    </main>
  );
}
