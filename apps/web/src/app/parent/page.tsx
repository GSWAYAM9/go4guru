"use client";

import type {
  GuardianLinkOut,
  ParentDashboardOut,
  ParentLearningSummaryOut,
} from "@go4guru/contracts";
import { EmptyState, ErrorBanner, LoadingCard, StatusBadge } from "@go4guru/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  createParentGoal,
  fetchParentDashboard,
  fetchParentStudentSummary,
  requestGuardianLink,
  revokeGuardianLink,
  updateGuardianPrivacy,
  updateParentGoal,
  verifyGuardianLink,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatConsentStatusLabel } from "@/lib/ecosystem-helpers";

export default function ParentPortalPage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();

  const [dashboard, setDashboard] = useState<ParentDashboardOut | null>(null);
  const [selectedLink, setSelectedLink] = useState<GuardianLinkOut | null>(null);
  const [summary, setSummary] = useState<ParentLearningSummaryOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Forms
  const [studentEmail, setStudentEmail] = useState("");
  const [relationshipType, setRelationshipType] = useState<"parent" | "guardian">(
    "parent"
  );
  const [verifyCodes, setVerifyCodes] = useState<Record<string, string>>({});
  const [goalTitle, setGoalTitle] = useState("");
  const [goalMinutes, setGoalMinutes] = useState("45");
  const [goalDate, setGoalDate] = useState("");

  const loadSummaryIfVerified = useCallback(
    async (authToken: string, link: GuardianLinkOut) => {
      if (link.consent_status !== "verified") {
        setSummary(null);
        return;
      }
      const data = await fetchParentStudentSummary(
        authToken,
        link.student_user_id
      );
      setSummary(data);
    },
    []
  );

  const selectedLinkIdRef = useRef<string | undefined>(selectedLink?.id);
  selectedLinkIdRef.current = selectedLink?.id;

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const dash = await fetchParentDashboard(token);
      setDashboard(dash);
      const nextLink =
        dash.linked_students.find((l) => l.id === selectedLinkIdRef.current) ??
        dash.linked_students.find((l) => l.consent_status === "verified") ??
        dash.linked_students[0] ??
        null;
      selectedLinkIdRef.current = nextLink?.id;
      setSelectedLink(nextLink);
      if (nextLink) {
        await loadSummaryIfVerified(token, nextLink);
      } else {
        setSummary(null);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load Parent Portal."
      );
    } finally {
      setLoading(false);
    }
  }, [token, loadSummaryIfVerified]);

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

  async function handleRequestLink(e: FormEvent) {
    e.preventDefault();
    if (!token || !studentEmail.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await requestGuardianLink(token, {
        student_email: studentEmail.trim(),
        relationship_type: relationshipType,
      });
      setStudentEmail("");
      setNotice(
        created.verification_code_preview
          ? `Consent verification code generated: ${created.verification_code_preview}. Enter it to verify consent.`
          : "Guardian link request submitted."
      );
      if (created.verification_code_preview) {
        setVerifyCodes((prev) => ({
          ...prev,
          [created.id]: created.verification_code_preview ?? "",
        }));
      }
      await loadDashboard();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not link student account."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleVerifyLink(linkId: string) {
    if (!token) return;
    const code = (verifyCodes[linkId] ?? "").trim();
    if (!code) return;
    setBusy(true);
    setError(null);
    try {
      const verified = await verifyGuardianLink(token, linkId, code);
      setNotice(`Consent verified for ${verified.student_name}.`);
      setSelectedLink(verified);
      await loadDashboard();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Verification code rejected."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleRevokeLink(linkId: string) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await revokeGuardianLink(token, linkId);
      setNotice("Guardian link revoked.");
      setSummary(null);
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revocation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleTogglePrivacy(
    link: GuardianLinkOut,
    key: "share_learning_summary" | "share_weak_topics" | "share_upcoming_tests"
  ) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateGuardianPrivacy(token, link.id, {
        [key]: !link.privacy_settings[key],
      });
      setSelectedLink(updated);
      await loadSummaryIfVerified(token, updated);
      setNotice("Privacy control updated.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update privacy setting."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateGoal(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedLink || !goalTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createParentGoal(token, {
        student_user_id: selectedLink.student_user_id,
        title: goalTitle.trim(),
        target_minutes_per_day: Number(goalMinutes) || 45,
        target_date: goalDate || null,
      });
      setGoalTitle("");
      setGoalDate("");
      setNotice("Study goal saved.");
      await loadSummaryIfVerified(token, selectedLink);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create goal.");
    } finally {
      setBusy(false);
    }
  }

  async function handleGoalStatus(
    goalId: string,
    status: "active" | "achieved" | "archived"
  ) {
    if (!token || !selectedLink) return;
    setBusy(true);
    try {
      await updateParentGoal(token, goalId, { status });
      await loadSummaryIfVerified(token, selectedLink);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update goal.");
    } finally {
      setBusy(false);
    }
  }

  if (initializing || loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <LoadingCard message="Loading Parent Portal..." />
      </main>
    );
  }

  const canAccess = user?.roles.some((r) =>
    ["parent", "platform_admin"].includes(r)
  );
  if (!canAccess) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <ErrorBanner
          title="Parent / Guardian access required"
          message="Sign in with a parent account to manage guardian consent and view privacy-preserving learning summaries."
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
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Child-Safe Guardian Portal
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Parent & Guardian Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Verifiable guardian consent, privacy-preserving academic summaries, goals, weak topics, revision health, and upcoming tests.
          </p>
        </div>
        {summary && (
          <button
            type="button"
            onClick={() => window.print()}
            className="shrink-0 whitespace-nowrap rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Print Progress Report
          </button>
        )}
      </header>

      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700">
        <span className="font-semibold text-slate-900">Child-Safety Privacy Boundary:</span>{" "}
        Linked parents receive verified academic progress summaries, revision counts, and upcoming test schedules. Raw student AI tutor and homework chat transcripts are strictly excluded.
      </div>

      {error && <ErrorBanner title="Action failed" message={error} />}
      {notice && (
        <div
          role="status"
          className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900"
        >
          {notice}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Guardian Links & Consent */}
        <aside className="space-y-5 lg:col-span-4">
          <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">
              Linked Student Accounts ({dashboard?.linked_students.length ?? 0})
            </h2>
            {!dashboard?.linked_students.length ? (
              <p className="text-xs text-slate-500">
                No linked students yet. Request a guardian link below.
              </p>
            ) : (
              <div className="space-y-3">
                {dashboard.linked_students.map((link) => {
                  const badge = formatConsentStatusLabel(link.consent_status);
                  const active = selectedLink?.id === link.id;
                  return (
                    <div
                      key={link.id}
                      className={`rounded-md border p-3 ${
                        active
                          ? "border-indigo-600 bg-indigo-50/40"
                          : "border-slate-200 bg-white"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedLink(link);
                            if (token) void loadSummaryIfVerified(token, link);
                          }}
                          className="text-left"
                        >
                          <p className="text-sm font-semibold text-slate-900">
                            {link.student_name}
                          </p>
                          <p className="text-xs text-slate-500">
                            {link.student_email}
                          </p>
                        </button>
                        <StatusBadge tone={badge.tone}>{badge.label}</StatusBadge>
                      </div>

                      {link.consent_status === "pending" && (
                        <div className="mt-3 flex gap-2">
                          <input
                            placeholder="8-char code"
                            value={verifyCodes[link.id] ?? ""}
                            onChange={(e) =>
                              setVerifyCodes((prev) => ({
                                ...prev,
                                [link.id]: e.target.value,
                              }))
                            }
                            className="w-full rounded border border-slate-300 bg-white px-2.5 py-1 text-xs uppercase"
                          />
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void handleVerifyLink(link.id)}
                            className="shrink-0 rounded bg-indigo-700 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-800"
                          >
                            Verify
                          </button>
                        </div>
                      )}

                      {link.consent_status === "verified" && (
                        <div className="mt-2.5 flex justify-end">
                          <button
                            type="button"
                            onClick={() => void handleRevokeLink(link.id)}
                            className="text-xs font-medium text-rose-700 hover:underline"
                          >
                            Revoke Link
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">
              Link a Student Account
            </h2>
            <form onSubmit={handleRequestLink} className="mt-3 space-y-2.5">
              <input
                type="email"
                required
                placeholder="student@example.com"
                value={studentEmail}
                onChange={(e) => setStudentEmail(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
              <select
                value={relationshipType}
                onChange={(e) =>
                  setRelationshipType(e.target.value as "parent" | "guardian")
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="parent">Parent</option>
                <option value="guardian">Legal Guardian</option>
              </select>
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-md bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Send Guardian Link Request
              </button>
            </form>
          </section>

          {selectedLink && (
            <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">
                Privacy Controls ({selectedLink.student_name})
              </h2>
              {(
                [
                  ["share_learning_summary", "Share learning & practice summary"],
                  ["share_weak_topics", "Share weak concepts list"],
                  ["share_upcoming_tests", "Share upcoming tests & assignments"],
                ] as const
              ).map(([key, label]) => (
                <label
                  key={key}
                  className="flex items-center justify-between gap-2 text-xs text-slate-700"
                >
                  <span>{label}</span>
                  <input
                    type="checkbox"
                    checked={selectedLink.privacy_settings[key]}
                    onChange={() => void handleTogglePrivacy(selectedLink, key)}
                  />
                </label>
              ))}
              <div className="flex items-center justify-between border-t border-slate-100 pt-2 text-xs text-slate-500">
                <span>Raw AI tutor chat transcripts</span>
                <span className="font-semibold text-slate-700">
                  Locked Off
                </span>
              </div>
            </section>
          )}
        </aside>

        {/* Right: Learning Summary, Weak Topics, Revision, Upcoming Tests, Goals */}
        <section className="space-y-5 lg:col-span-8">
          {!selectedLink ? (
            <EmptyState
              title="Link a student account to begin"
              description="Once guardian consent is verified, privacy-preserving academic summaries appear here."
            />
          ) : selectedLink.consent_status !== "verified" ? (
            <EmptyState
              title="Consent verification required"
              description="Enter the verification code on the left to unlock this student's learning summary."
            />
          ) : !summary ? (
            <LoadingCard message="Loading learning summary..." />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">Practice Accuracy</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
                    {summary.practice_accuracy_pct}%
                  </p>
                  <p className="text-xs tabular-nums text-slate-500">
                    {summary.practice_correct_attempts}/
                    {summary.practice_total_attempts} correct
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">Concept Mastery</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
                    {summary.mastery_average_pct}%
                  </p>
                  <p className="text-xs tabular-nums text-slate-500">
                    {summary.mastered_concepts_count} mastered
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">Revision Cards</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
                    {summary.revision_due_flashcards} due
                  </p>
                  <p className="text-xs tabular-nums text-slate-500">
                    {summary.revision_completed_plan_items} plan items done
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="text-xs text-slate-500">Homework & Practice</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">
                    {summary.homework_evaluated_submissions}
                  </p>
                  <p className="text-xs tabular-nums text-slate-500">
                    {summary.practice_sessions_completed} practice sessions
                  </p>
                </div>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-slate-900">
                    Weak Topics Needing Attention
                  </h2>
                  {summary.weak_topics.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      No weak topics flagged or topic sharing is disabled.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {summary.weak_topics.map((wt) => (
                        <li
                          key={wt.concept_id}
                          className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-xs"
                        >
                          <span className="font-mono text-slate-700">
                            Concept {wt.concept_id.slice(0, 8)}
                          </span>
                          <span className="font-semibold tabular-nums text-amber-700">
                            {wt.mastery_score}% ({wt.band})
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-slate-900">
                    Upcoming Tests & Assignments
                  </h2>
                  {summary.upcoming_assessments.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      No upcoming class tests or assignments scheduled.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {summary.upcoming_assessments.map((a) => (
                        <li
                          key={a.id}
                          className="rounded border border-slate-200 px-3 py-2 text-xs"
                        >
                          <p className="font-semibold text-slate-900">
                            {a.title}
                          </p>
                          <p className="text-slate-500">
                            {a.assignment_type.toUpperCase()} · {a.max_marks}{" "}
                            marks
                            {a.due_at
                              ? ` · Due ${new Date(a.due_at).toLocaleDateString()}`
                              : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
                <h2 className="text-sm font-semibold text-slate-900">
                  Family Study Goals ({summary.goals.length})
                </h2>
                <form
                  onSubmit={handleCreateGoal}
                  className="grid gap-2 sm:grid-cols-12"
                >
                  <input
                    required
                    placeholder="e.g., Complete 45 mins Physics revision daily"
                    value={goalTitle}
                    onChange={(e) => setGoalTitle(e.target.value)}
                    className="rounded border border-slate-300 px-3 py-2 text-sm sm:col-span-5"
                  />
                  <input
                    type="number"
                    min={10}
                    max={360}
                    value={goalMinutes}
                    onChange={(e) => setGoalMinutes(e.target.value)}
                    className="rounded border border-slate-300 px-2.5 py-2 text-sm sm:col-span-2"
                    aria-label="Daily target minutes"
                  />
                  <input
                    type="date"
                    value={goalDate}
                    onChange={(e) => setGoalDate(e.target.value)}
                    className="rounded border border-slate-300 px-2.5 py-2 text-sm sm:col-span-3"
                  />
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded bg-indigo-700 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-800 sm:col-span-2"
                  >
                    Add Goal
                  </button>
                </form>

                {summary.goals.length > 0 && (
                  <ul className="space-y-2">
                    {summary.goals.map((g) => (
                      <li
                        key={g.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 px-3 py-2 text-xs"
                      >
                        <div>
                          <p className="font-semibold text-slate-900">
                            {g.title}
                          </p>
                          <p className="text-slate-500 tabular-nums">
                            {g.target_minutes_per_day} mins/day
                            {g.target_date ? ` · Target ${g.target_date}` : ""}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusBadge
                            tone={g.status === "achieved" ? "healthy" : "neutral"}
                          >
                            {g.status}
                          </StatusBadge>
                          {g.status === "active" && (
                            <button
                              type="button"
                              onClick={() =>
                                void handleGoalStatus(g.id, "achieved")
                              }
                              className="rounded border border-emerald-600 px-2 py-1 text-emerald-700 hover:bg-emerald-50"
                            >
                              Mark Achieved
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
