"use client";

import type { StudentDashboardResponse } from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiClientError, fetchStudentDashboard } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();
  const [data, setData] = useState<StudentDashboardResponse | null>(null);
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
        const res = await fetchStudentDashboard(authToken);
        setData(res);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        } else {
          setError({
            code: "NETWORK_ERROR",
            message: "Unable to load student dashboard.",
          });
        }
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [initializing, token, router]);

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Student Learning Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Live progress computed directly from your PostgreSQL attempts, notes, and saved questions.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/onboarding"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Academic Settings
          </Link>
          <Link
            href="/practice"
            className="rounded-md bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
          >
            Start Practice
          </Link>
        </div>
      </header>

      {loading ? <LoadingCard message="Loading live student progress..." /> : null}

      {!loading && error ? (
        <ErrorBanner
          title={`Dashboard Unavailable (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      {!loading && data ? (
        <div className="space-y-6">
          {!data.onboarding_completed ? (
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <div>
                <p className="font-semibold">Complete Your Academic Onboarding</p>
                <p>
                  Select your Class (6–12), Board, and Exam Target so your dashboard reflects your syllabus.
                </p>
              </div>
              <Link
                href="/onboarding"
                className="rounded-md bg-amber-800 px-3 py-1.5 font-medium text-white hover:bg-amber-900"
              >
                Finish Onboarding
              </Link>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Question Attempts
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900">
                {data.total_attempts}
              </p>
              <p className="mt-1 text-xs text-slate-600">
                {data.correct_attempts} correct
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Verified Accuracy
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900">
                {data.accuracy_pct}%
              </p>
              <p className="mt-1 text-xs text-slate-600">
                Target: {data.primary_exam_target} ({data.daily_study_minutes_target}m/day)
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Practice Sessions &amp; Hints
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900">
                {data.total_practice_sessions}
              </p>
              <p className="mt-1 text-xs text-slate-600">
                Hints used total: {data.hints_used_total}
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Notes &amp; Saved Qs
              </p>
              <p className="mt-2 text-2xl font-bold text-slate-900">
                {data.notes_count} / {data.saved_questions_count}
              </p>
              <p className="mt-1 text-xs text-slate-600">
                <Link href="/notes" className="text-indigo-700 underline">
                  Manage Notes &amp; Bookmarks
                </Link>
              </p>
            </div>
          </div>

          {data.total_attempts === 0 ? (
            <EmptyState
              title={`Welcome${user ? `, ${user.display_name}` : ""}! No practice attempts recorded yet.`}
              description="Explore the published curriculum and start a guided practice session to track real question accuracy and progress."
              action={
                <Link
                  href="/curriculum"
                  className="inline-block rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
                >
                  Explore Curriculum
                </Link>
              }
            />
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="rounded-lg border border-slate-200 bg-white p-5">
                <h2 className="text-base font-semibold text-slate-900">
                  Recent Practice Attempts
                </h2>
                <ul className="mt-3 divide-y divide-slate-100 text-sm">
                  {data.recent_attempts.map((a) => (
                    <li
                      key={a.attempt_id}
                      className="flex items-center justify-between py-2.5"
                    >
                      <div>
                        <span className="font-mono text-xs text-slate-500">
                          {a.question_id.slice(0, 8)}...
                        </span>
                        <span className="ml-2 text-slate-700">
                          Score: {a.score_awarded} (Hints: {a.hints_used_count})
                        </span>
                      </div>
                      <StatusBadge tone={a.is_correct ? "healthy" : "degraded"}>
                        {a.is_correct ? "Correct" : "Incorrect"}
                      </StatusBadge>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-5">
                <h2 className="text-base font-semibold text-slate-900">
                  Subject Activity
                </h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {data.subject_activity.map((sa, idx) => (
                    <li
                      key={sa.subject_id ?? `gen-${idx}`}
                      className="flex items-center justify-between rounded bg-slate-50 px-3 py-2"
                    >
                      <span className="font-medium text-slate-800">
                        {sa.subject_name}
                      </span>
                      <span className="text-slate-600">
                        {sa.practice_sessions_count} session(s)
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          )}

          <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            Roadmap Status: {data.unimplemented_features_note}
          </p>
        </div>
      ) : null}
    </main>
  );
}
