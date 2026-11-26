"use client";

import type {
  AdaptiveOverviewOut,
  LearningPathOut,
  MasteryBand,
  NotificationOut,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ApiClientError,
  fetchAdaptiveOverview,
  generateLearningPath,
  listLearningPaths,
  listNotifications,
  markNotificationRead,
  recomputeAdaptiveMastery,
  resolveMisconception,
  updateLearningPathItemStatus,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

function bandTone(band: MasteryBand): "healthy" | "degraded" | "neutral" {
  if (band === "mastered" || band === "proficient") return "healthy";
  if (band === "novice" || band === "developing") return "degraded";
  return "neutral";
}

export default function AdaptiveMasteryPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [overview, setOverview] = useState<AdaptiveOverviewOut | null>(null);
  const [paths, setPaths] = useState<LearningPathOut[]>([]);
  const [notifications, setNotifications] = useState<NotificationOut[]>([]);
  const [pathTitle, setPathTitle] = useState("Personalized Mastery Path");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async (authToken: string) => {
    const ov = await fetchAdaptiveOverview(authToken);
    const [lpList, notifs] = await Promise.all([
      listLearningPaths(authToken),
      listNotifications(authToken),
    ]);
    setOverview(ov);
    setPaths(lpList);
    setNotifications(notifs);
  }, []);

  useEffect(() => {
    if (!initializing && !token) {
      router.replace("/login");
    }
  }, [initializing, token, router]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    setLoading(true);
    setError(null);
    loadAll(token)
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load Adaptive Mastery."
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token, loadAll]);

  async function handleRecompute() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const ov = await recomputeAdaptiveMastery(token);
      setOverview(ov);
      setNotifications(await listNotifications(token));
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Failed to recompute."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleResolveMisconception(id: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await resolveMisconception(token, id);
      await loadAll(token);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Resolve failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleGeneratePath(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !pathTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await generateLearningPath(token, {
        title: pathTitle.trim(),
      });
      setPaths((prev) => [created, ...prev]);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Path generation failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handlePathItemStatus(
    itemId: string,
    status: "pending" | "in_progress" | "completed" | "skipped"
  ) {
    if (!token) return;
    setBusy(true);
    try {
      await updateLearningPathItemStatus(token, itemId, status);
      setPaths(await listLearningPaths(token));
    } finally {
      setBusy(false);
    }
  }

  async function handleReadNotification(id: string) {
    if (!token) return;
    await markNotificationRead(token, id);
    setNotifications(await listNotifications(token));
  }

  if (initializing || loading) {
    return <LoadingCard message="Computing Multi-Signal Concept Mastery..." />;
  }

  const unread = notifications.filter((n) => !n.is_read);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Adaptive Concept Mastery &amp; Remediation
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Transparent multi-signal mastery scoring combining difficulty, hint independence, spaced retention, cross-format transfer, improvement trend, and misconception penalties.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={handleRecompute}
            className="rounded-md bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Updating..." : "Recompute Mastery"}
          </button>
          <Link
            href="/revision"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50"
          >
            Open Revision &amp; Study Plan
          </Link>
        </div>
      </div>

      {error && <ErrorBanner title="Adaptive Engine Notice" message={error} />}

      {/* In-app Notifications Strip */}
      {unread.length > 0 && (
        <section
          aria-label="Revision and Mastery Alerts"
          className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-4"
        >
          <h2 className="text-sm font-bold text-amber-950">
            Active Learning Alerts ({unread.length})
          </h2>
          <div className="space-y-2">
            {unread.slice(0, 4).map((note) => (
              <div
                key={note.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs"
              >
                <div>
                  <span className="font-semibold text-slate-900">{note.title}</span>{" "}
                  — <span className="text-slate-700">{note.body}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleReadNotification(note.id)}
                  className="rounded border border-slate-300 px-2 py-0.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                >
                  Acknowledge
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Algorithm Transparency & KPI Summary */}
      {overview && (
        <section className="grid gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">Tracked Concepts</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {overview.concepts.length}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">Needs Remediation</div>
            <div className="mt-1 text-2xl font-bold text-amber-700">
              {overview.weak_concepts.length}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">Mastered Independently</div>
            <div className="mt-1 text-2xl font-bold text-emerald-700">
              {overview.mastered_concepts.length}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">Active Misconceptions</div>
            <div className="mt-1 text-2xl font-bold text-rose-700">
              {overview.unresolved_misconceptions.length}
            </div>
          </div>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Concept Mastery Cards + Breakdown */}
        <div className="space-y-4 lg:col-span-7">
          <h2 className="text-lg font-bold text-slate-900">
            Concept Mastery Breakdown
          </h2>
          {!overview || overview.concepts.length === 0 ? (
            <EmptyState
              title="No concept attempts tracked yet"
              description="Complete practice questions or assessments mapped to curriculum concepts to build your adaptive mastery profile."
            />
          ) : (
            <div className="space-y-3">
              {overview.concepts.map((c) => (
                <article
                  key={c.concept_id}
                  data-testid={`mastery-card-${c.concept_code}`}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {c.concept_title}{" "}
                        <span className="font-mono text-xs font-normal text-slate-500">
                          ({c.concept_code})
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        {c.subject_name ?? "General STEM"}
                        {c.chapter_title ? ` · ${c.chapter_title}` : ""} ·{" "}
                        {c.attempts_count} attempt(s)
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-slate-900">
                        {c.mastery_score.toFixed(1)}/100
                      </span>
                      <StatusBadge tone={bandTone(c.band)}>{c.band}</StatusBadge>
                    </div>
                  </div>

                  {/* Multi-signal bars */}
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
                    <div className="rounded bg-slate-50 p-2">
                      <div className="text-slate-500">Diff-Weighted Acc</div>
                      <div className="font-semibold">
                        {Math.round(c.difficulty_weighted_accuracy * 100)}%
                      </div>
                    </div>
                    <div className="rounded bg-slate-50 p-2">
                      <div className="text-slate-500">Independent Solving</div>
                      <div className="font-semibold">
                        {Math.round(c.independent_solve_ratio * 100)}%
                      </div>
                    </div>
                    <div className="rounded bg-slate-50 p-2">
                      <div className="text-slate-500">Retention Signal</div>
                      <div className="font-semibold">
                        {Math.round(c.retention_score * 100)}%
                      </div>
                    </div>
                    <div className="rounded bg-slate-50 p-2">
                      <div className="text-slate-500">Transfer Score</div>
                      <div className="font-semibold">
                        {Math.round(c.transfer_score * 100)}%
                      </div>
                    </div>
                    <div className="rounded bg-slate-50 p-2">
                      <div className="text-slate-500">Improvement Trend</div>
                      <div className="font-semibold">
                        {c.improvement_slope.toFixed(2)}
                      </div>
                    </div>
                    <div className="rounded bg-slate-50 p-2">
                      <div className="text-slate-500">Confidence</div>
                      <div className="font-semibold">
                        {Math.round(c.confidence * 100)}%
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}

          {overview && (
            <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <strong>Algorithm ({overview.algorithm_version}):</strong>{" "}
              {overview.limitations_note}
            </p>
          )}
        </div>

        {/* Recommendations, Misconceptions & Learning Paths */}
        <aside className="space-y-6 lg:col-span-5">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-bold text-slate-900">
              Prerequisite-Aware Recommendations
            </h2>
            {!overview || overview.recommendations.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">
                Solve practice or quiz problems to unlock personalized recommendations.
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {overview.recommendations.map((rec, idx) => (
                  <li
                    key={`${rec.concept_id}-${rec.item_type}-${idx}`}
                    className="rounded-lg border border-slate-200 p-3 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <StatusBadge
                        tone={
                          rec.item_type === "advance" ? "healthy" : "degraded"
                        }
                      >
                        {rec.item_type}
                      </StatusBadge>
                      <span className="font-mono text-slate-500">
                        Priority {rec.priority_score}
                      </span>
                    </div>
                    <p className="mt-1.5 text-slate-800">{rec.reason}</p>
                    <Link
                      href={rec.action_route}
                      className="mt-2 inline-block font-semibold text-indigo-700 hover:underline"
                    >
                      Start Action →
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-bold text-slate-900">
              Unresolved Misconceptions
            </h2>
            {!overview || overview.unresolved_misconceptions.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">
                No active misconceptions detected.
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {overview.unresolved_misconceptions.map((m) => (
                  <li
                    key={m.id}
                    className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-rose-950">{m.title}</span>
                      <StatusBadge tone="degraded">{m.severity}</StatusBadge>
                    </div>
                    <p className="mt-1 text-rose-900">{m.description}</p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-rose-700">
                        Observed {m.occurrence_count}x
                      </span>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleResolveMisconception(m.id)}
                        className="rounded border border-rose-300 bg-white px-2.5 py-1 font-medium text-rose-900 hover:bg-rose-100"
                      >
                        Mark Resolved
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Learning Path Generator */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-bold text-slate-900">
              Saved Learning Paths
            </h2>
            <form onSubmit={handleGeneratePath} className="mt-2 flex gap-2">
              <input
                type="text"
                aria-label="Learning path title"
                value={pathTitle}
                onChange={(e) => setPathTitle(e.target.value)}
                className="flex-1 rounded-md border border-slate-300 px-2.5 py-1.5 text-xs"
              />
              <button
                type="submit"
                disabled={busy}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Build Path
              </button>
            </form>
            {paths.length > 0 && (
              <div className="mt-3 space-y-3">
                {paths[0].items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-2 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-slate-900">
                        {item.sequence_no}. {item.concept_title} ({item.item_type})
                      </div>
                      <div className="text-slate-600">{item.reason}</div>
                    </div>
                    <button
                      type="button"
                      disabled={busy || item.status === "completed"}
                      onClick={() => handlePathItemStatus(item.id, "completed")}
                      className="shrink-0 rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                    >
                      {item.status === "completed" ? "Done" : "Complete"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
