"use client";

import type {
  MentorDashboardOut,
  MentorStudentReviewOut,
} from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard, StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  assignMentorStudent,
  createMentorFollowUp,
  createMentorGoal,
  createMentorSession,
  fetchMentorDashboard,
  fetchMentorStudentReview,
  updateMentorFollowUp,
  updateMentorGoal,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function MentorHubPage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();

  const [dashboard, setDashboard] = useState<MentorDashboardOut | null>(null);
  const [selectedStudentId, setSelectedStudentId] = useState<string>("");
  const [review, setReview] = useState<MentorStudentReviewOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Forms
  const [assignEmail, setAssignEmail] = useState("");
  const [assignNotes, setAssignNotes] = useState("");
  const [goalTitle, setGoalTitle] = useState("");
  const [goalDesc, setGoalDesc] = useState("");
  const [goalDate, setGoalDate] = useState("");
  const [sessNotes, setSessNotes] = useState("");
  const [sessRec, setSessRec] = useState("");
  const [followTitle, setFollowTitle] = useState("");
  const [followDate, setFollowDate] = useState("");

  const loadReview = useCallback(async (authToken: string, studentId: string) => {
    const data = await fetchMentorStudentReview(authToken, studentId);
    setReview(data);
  }, []);

  const selectedStudentIdRef = useRef(selectedStudentId);
  selectedStudentIdRef.current = selectedStudentId;

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const dash = await fetchMentorDashboard(token);
      setDashboard(dash);
      const targetId = selectedStudentIdRef.current || dash.students[0]?.student_id || "";
      if (targetId) {
        selectedStudentIdRef.current = targetId;
        setSelectedStudentId(targetId);
        await loadReview(token, targetId);
      } else {
        setReview(null);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load Mentor Hub."
      );
    } finally {
      setLoading(false);
    }
  }, [token, loadReview]);

  useEffect(() => {
    if (!initializing && !token) {
      router.replace("/login");
    }
  }, [initializing, token, router]);

  useEffect(() => {
    if (token) {
      void loadDashboard();
    }
  }, [token, loadDashboard]);

  async function handleSelectStudent(studentId: string) {
    setSelectedStudentId(studentId);
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await loadReview(token, studentId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load student review."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleAssignStudent(e: FormEvent) {
    e.preventDefault();
    if (!token || !assignEmail.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await assignMentorStudent(token, {
        student_email: assignEmail.trim(),
        notes: assignNotes.trim() || undefined,
      });
      setAssignEmail("");
      setAssignNotes("");
      setSelectedStudentId(created.student_id);
      setNotice(`Assigned ${created.student_name} to your mentorship roster.`);
      await loadDashboard();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not assign student."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleAddGoal(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStudentId || !goalTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createMentorGoal(token, {
        student_id: selectedStudentId,
        title: goalTitle.trim(),
        description: goalDesc.trim(),
        target_date: goalDate || null,
      });
      setGoalTitle("");
      setGoalDesc("");
      setGoalDate("");
      setNotice("Study goal added.");
      await loadReview(token, selectedStudentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create goal.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdateGoal(
    goalId: string,
    progress_pct: number,
    status: "active" | "completed" | "paused"
  ) {
    if (!token || !selectedStudentId) return;
    setBusy(true);
    try {
      await updateMentorGoal(token, goalId, { progress_pct, status });
      await loadReview(token, selectedStudentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Goal update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleLogSession(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStudentId || !sessNotes.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createMentorSession(token, {
        student_id: selectedStudentId,
        scheduled_at: new Date().toISOString(),
        duration_minutes: 30,
        status: "completed",
        summary_notes: sessNotes.trim(),
        recommendations: sessRec
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
      });
      setSessNotes("");
      setSessRec("");
      setNotice("Mentoring session notes saved.");
      await loadReview(token, selectedStudentId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not log mentor session."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleAddFollowUp(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedStudentId || !followTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createMentorFollowUp(token, {
        student_id: selectedStudentId,
        title: followTitle.trim(),
        due_date: followDate || null,
      });
      setFollowTitle("");
      setFollowDate("");
      setNotice("Follow-up task scheduled.");
      await loadReview(token, selectedStudentId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not add follow-up task."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleFollowUp(
    followUpId: string,
    nextStatus: "open" | "in_progress" | "completed"
  ) {
    if (!token || !selectedStudentId) return;
    setBusy(true);
    try {
      await updateMentorFollowUp(token, followUpId, { status: nextStatus });
      await loadReview(token, selectedStudentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Follow-up update failed.");
    } finally {
      setBusy(false);
    }
  }

  if (initializing || loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <LoadingCard message="Loading Mentor Hub..." />
      </main>
    );
  }

  const canAccess = user?.roles.some((r) =>
    ["mentor", "school_admin", "platform_admin"].includes(r)
  );
  if (!canAccess) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <ErrorBanner
          title="Mentor access required"
          message="Your account does not hold the mentor, school_admin, or platform_admin role."
        />
        <div className="mt-4">
          <Link href="/dashboard" className="text-sm font-medium text-indigo-700 underline">
            Return to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="border-b border-slate-200 pb-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
          Student Mentorship & Interventions
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
          Mentor Hub
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Coach assigned students with structured goals, study-plan alignment, session notes, follow-up tasks, and weakness analysis.
        </p>
      </header>

      {error && <ErrorBanner title="Action failed" message={error} />}
      {notice && (
        <div
          role="status"
          className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900"
        >
          {notice}
        </div>
      )}

      {/* KPI Strip */}
      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          {
            label: "Assigned Students",
            value: dashboard?.assigned_students_count ?? 0,
          },
          { label: "Active Goals", value: dashboard?.active_goals_count ?? 0 },
          {
            label: "Upcoming Sessions",
            value: dashboard?.upcoming_sessions_count ?? 0,
          },
          {
            label: "Open Follow-ups",
            value: dashboard?.open_follow_ups_count ?? 0,
          },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-lg border border-slate-200 bg-white p-4"
          >
            <p className="text-xs font-medium text-slate-500">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
              {kpi.value}
            </p>
          </div>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left column: Assigned Students + Assign Form */}
        <aside className="space-y-4 lg:col-span-4">
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">
              Assigned Students
            </h2>
            {!dashboard?.students.length ? (
              <p className="mt-2 text-xs text-slate-500">
                No students assigned yet. Add a student below.
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {dashboard.students.map((st) => {
                  const active = st.student_id === selectedStudentId;
                  return (
                    <li key={st.assignment_id}>
                      <button
                        type="button"
                        onClick={() => void handleSelectStudent(st.student_id)}
                        className={`w-full rounded-md border px-3 py-2.5 text-left transition ${
                          active
                            ? "border-indigo-600 bg-indigo-50"
                            : "border-slate-200 bg-white hover:bg-slate-50"
                        }`}
                      >
                        <p className="text-sm font-semibold text-slate-900">
                          {st.student_name}
                        </p>
                        <p className="text-xs text-slate-500">
                          {st.student_email}
                        </p>
                        <p className="mt-1 text-xs tabular-nums text-slate-600">
                          {st.active_goals_count} goals ·{" "}
                          {st.open_follow_ups_count} follow-ups
                        </p>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">
              Assign Student
            </h2>
            <form onSubmit={handleAssignStudent} className="mt-3 space-y-2.5">
              <input
                type="email"
                required
                placeholder="student@school.edu"
                value={assignEmail}
                onChange={(e) => setAssignEmail(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                placeholder="Mentorship focus note (optional)"
                value={assignNotes}
                onChange={(e) => setAssignNotes(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-md bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Assign to Roster
              </button>
            </form>
          </section>
        </aside>

        {/* Right column: Selected Student Progress, Weaknesses, Goals, Sessions, Follow-ups */}
        <section className="space-y-5 lg:col-span-8">
          {!review ? (
            <EmptyState
              title="Select an assigned student"
              description="Review progress metrics, weakness diagnostics, goals, session logs, and follow-up actions."
            />
          ) : (
            <>
              {/* Progress & Weakness Review */}
              <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">
                      {review.student_name}
                    </h2>
                    <p className="text-xs text-slate-500">
                      Track: {review.primary_exam_target.toUpperCase()} · Daily
                      target {review.daily_study_minutes_target} mins
                    </p>
                  </div>
                  <StatusBadge tone="healthy">Assigned Mentee</StatusBadge>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Practice Accuracy</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {review.practice_accuracy_pct}%
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Avg Mastery</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {review.mastery_average_pct}%
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Due Flashcards</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {review.due_flashcards_count}
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-xs text-slate-500">Study Plan Items</p>
                    <p className="mt-1 text-lg font-bold tabular-nums">
                      {review.completed_plan_items_count} done
                    </p>
                  </div>
                </div>

                <div className="rounded-md border border-indigo-100 bg-indigo-50/60 p-3.5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-indigo-800">
                    Recommended Mentor Interventions
                  </p>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-slate-800">
                    {review.recommended_interventions.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>

                {review.weak_concepts.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Weakness Analysis (Mastery &lt; 60%)
                    </h3>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      {review.weak_concepts.map((wc) => (
                        <div
                          key={wc.concept_id}
                          className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-xs"
                        >
                          <span className="font-mono text-slate-700">
                            Concept {wc.concept_id.slice(0, 8)}
                          </span>
                          <span className="font-semibold tabular-nums text-amber-700">
                            {wc.mastery_score}% ({wc.band})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Goals & Follow-ups */}
              <div className="grid gap-5 md:grid-cols-2">
                <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
                  <h3 className="text-sm font-semibold text-slate-900">
                    Mentee Goals ({review.goals.length})
                  </h3>
                  <form onSubmit={handleAddGoal} className="space-y-2">
                    <input
                      required
                      placeholder="Goal title (e.g., Master Optics ray diagrams)"
                      value={goalTitle}
                      onChange={(e) => setGoalTitle(e.target.value)}
                      className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        placeholder="Details"
                        value={goalDesc}
                        onChange={(e) => setGoalDesc(e.target.value)}
                        className="rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                      />
                      <input
                        type="date"
                        value={goalDate}
                        onChange={(e) => setGoalDate(e.target.value)}
                        className="rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={busy}
                      className="w-full rounded bg-indigo-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-800"
                    >
                      Add Goal
                    </button>
                  </form>
                  <ul className="space-y-2">
                    {review.goals.map((g) => (
                      <li
                        key={g.id}
                        className="rounded border border-slate-200 p-3 text-xs"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold text-slate-900">
                            {g.title}
                          </span>
                          <StatusBadge
                            tone={g.status === "completed" ? "healthy" : "neutral"}
                          >
                            {g.progress_pct}%
                          </StatusBadge>
                        </div>
                        <div className="mt-2 flex gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              void handleUpdateGoal(
                                g.id,
                                Math.min(100, g.progress_pct + 25),
                                g.progress_pct + 25 >= 100 ? "completed" : "active"
                              )
                            }
                            className="rounded border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-50"
                          >
                            +25% Progress
                          </button>
                          {g.status !== "completed" && (
                            <button
                              type="button"
                              onClick={() =>
                                void handleUpdateGoal(g.id, 100, "completed")
                              }
                              className="rounded border border-emerald-600 px-2 py-1 text-emerald-700 hover:bg-emerald-50"
                            >
                              Mark Complete
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
                  <h3 className="text-sm font-semibold text-slate-900">
                    Follow-up Tasks ({review.follow_ups.length})
                  </h3>
                  <form onSubmit={handleAddFollowUp} className="space-y-2">
                    <input
                      required
                      placeholder="Follow-up action item"
                      value={followTitle}
                      onChange={(e) => setFollowTitle(e.target.value)}
                      className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                    />
                    <input
                      type="date"
                      value={followDate}
                      onChange={(e) => setFollowDate(e.target.value)}
                      className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm"
                    />
                    <button
                      type="submit"
                      disabled={busy}
                      className="w-full rounded border border-indigo-700 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                    >
                      Schedule Follow-up
                    </button>
                  </form>
                  <ul className="space-y-2">
                    {review.follow_ups.map((f) => (
                      <li
                        key={f.id}
                        className="flex items-center justify-between gap-2 rounded border border-slate-200 px-3 py-2 text-xs"
                      >
                        <div>
                          <p className="font-medium text-slate-900">{f.title}</p>
                          <p className="text-slate-500">
                            Status: {f.status.replace("_", " ")}
                            {f.due_date ? ` · Due ${f.due_date}` : ""}
                          </p>
                        </div>
                        {f.status !== "completed" && (
                          <button
                            type="button"
                            onClick={() =>
                              void handleToggleFollowUp(f.id, "completed")
                            }
                            className="shrink-0 rounded border border-emerald-600 px-2 py-1 text-emerald-700 hover:bg-emerald-50"
                          >
                            Done
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Mentoring Sessions & Notes */}
              <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
                <h3 className="text-sm font-semibold text-slate-900">
                  Mentoring Sessions & Notes ({review.sessions.length})
                </h3>
                <form onSubmit={handleLogSession} className="space-y-2.5">
                  <textarea
                    required
                    rows={2}
                    placeholder="Session summary notes..."
                    value={sessNotes}
                    onChange={(e) => setSessNotes(e.target.value)}
                    className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                  <textarea
                    rows={2}
                    placeholder="Actionable recommendations (one per line)..."
                    value={sessRec}
                    onChange={(e) => setSessRec(e.target.value)}
                    className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-md bg-indigo-700 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-800"
                  >
                    Log Session & Notes
                  </button>
                </form>

                {review.sessions.length > 0 && (
                  <div className="space-y-2 pt-2">
                    {review.sessions.map((s) => (
                      <div
                        key={s.id}
                        className="rounded border border-slate-200 bg-slate-50 p-3 text-xs"
                      >
                        <div className="flex items-center justify-between text-slate-500">
                          <span>
                            {new Date(s.scheduled_at).toLocaleDateString()} ·{" "}
                            {s.duration_minutes} mins
                          </span>
                          <StatusBadge tone="neutral">{s.status}</StatusBadge>
                        </div>
                        <p className="mt-1.5 text-sm text-slate-800">
                          {s.summary_notes}
                        </p>
                        {s.recommendations.length > 0 && (
                          <ul className="mt-1.5 list-disc pl-4 text-slate-600">
                            {s.recommendations.map((r, idx) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
