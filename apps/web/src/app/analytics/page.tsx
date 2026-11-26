"use client";

import type {
  CohortAnalyticsResponse,
  StudentAnalyticsOverviewResponse,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiClientError,
  fetchCohortAnalytics,
  fetchStudentAnalyticsOverview,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

const COHORT_ROLES = new Set([
  "teacher",
  "school_admin",
  "content_admin",
  "academic_reviewer",
  "platform_admin",
]);

export default function AnalyticsPage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();

  const [overview, setOverview] =
    useState<StudentAnalyticsOverviewResponse | null>(null);
  const [cohort, setCohort] = useState<CohortAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  const canViewCohort = user
    ? user.roles.some((r) => COHORT_ROLES.has(r))
    : false;

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
        const res = await fetchStudentAnalyticsOverview(authToken);
        setOverview(res);
        if (canViewCohort) {
          try {
            const c = await fetchCohortAnalytics(authToken);
            setCohort(c);
          } catch {
            // Optional cohort view when user role has cohort permission
          }
        }
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        } else {
          setError({
            code: "ANALYTICS_ERROR",
            message: "Unable to load learning analytics.",
          });
        }
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [initializing, token, router, canViewCohort]);

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Learning Analytics & Event Stream
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Authoritative metrics projected idempotently from committed outbox events in PostgreSQL.
          </p>
        </div>
        <Link
          href="/assessments"
          className="rounded-md bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
        >
          View Assessments
        </Link>
      </header>

      {loading ? <LoadingCard message="Loading live learning analytics..." /> : null}

      {!loading && error ? (
        <ErrorBanner
          title={`Analytics Unavailable (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      {!loading && overview ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <p className="text-xs font-medium uppercase text-slate-500">
                Assessments Completed
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {overview.assessments_completed}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <p className="text-xs font-medium uppercase text-slate-500">
                Assessment Avg Accuracy
              </p>
              <p className="mt-2 text-3xl font-bold text-indigo-700">
                {overview.average_assessment_accuracy_pct}%
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <p className="text-xs font-medium uppercase text-slate-500">
                Practice Accuracy
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {overview.practice_accuracy_pct}%
              </p>
              <p className="mt-1 text-xs text-slate-600">
                {overview.practice_correct} / {overview.practice_attempts} correct
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <p className="text-xs font-medium uppercase text-slate-500">
                Projected Events
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {overview.total_learning_events}
              </p>
            </div>
          </div>

          {cohort ? (
            <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5">
              <h2 className="text-base font-semibold text-slate-900">
                Educator Cohort Summary
              </h2>
              <p className="mt-1 text-sm text-slate-700">
                Submitted attempts across platform:{" "}
                <span className="font-semibold">
                  {cohort.total_submitted_attempts}
                </span>{" "}
                · Mean Cohort Accuracy:{" "}
                <span className="font-semibold">
                  {cohort.average_accuracy_pct}%
                </span>
              </p>
            </section>
          ) : null}

          <section aria-labelledby="events-heading" className="space-y-3">
            <h2
              id="events-heading"
              className="text-lg font-semibold text-slate-900"
            >
              Recent Learning Events
            </h2>
            {overview.recent_events.length === 0 ? (
              <EmptyState
                title="No Learning Events Recorded Yet"
                description="Complete a practice question or submit a quiz/assessment to see real analytics events appear here."
              />
            ) : (
              <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
                {overview.recent_events.map((ev) => (
                  <li
                    key={ev.id}
                    className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <StatusBadge tone="neutral">{ev.event_type}</StatusBadge>
                      <span className="text-slate-700">
                        {JSON.stringify(ev.metrics_jsonb)}
                      </span>
                    </div>
                    <time className="text-xs text-slate-500">
                      {new Date(ev.occurred_at).toLocaleString()}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
