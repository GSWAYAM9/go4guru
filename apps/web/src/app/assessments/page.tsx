"use client";

import type {
  AttemptHistoryItem,
  ExamPatternOut,
  TestOut,
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
  createTestTemplate,
  listAttemptHistory,
  listExamPatterns,
  listTests,
  publishTestTemplate,
  startTestAttempt,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

const CREATOR_ROLES = new Set([
  "teacher",
  "content_admin",
  "school_admin",
  "platform_admin",
]);

export default function AssessmentsPage() {
  const router = useRouter();
  const { token, user, initializing } = useAuth();

  const [patterns, setPatterns] = useState<ExamPatternOut[]>([]);
  const [tests, setTests] = useState<TestOut[]>([]);
  const [history, setHistory] = useState<AttemptHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  // Teacher/Admin Test Template Builder State
  const [newTitle, setNewTitle] = useState("Unit Mock Assessment");
  const [newCategory, setNewCategory] = useState("cbse_mock");
  const [selectedPatternId, setSelectedPatternId] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [secName, setSecName] = useState("Section A: Core");
  const [secQCount, setSecQCount] = useState(3);
  const [secCorrectMarks, setSecCorrectMarks] = useState(4);
  const [secWrongMarks, setSecWrongMarks] = useState(-1);
  const [creatingTest, setCreatingTest] = useState(false);

  const canCreateTests = user
    ? user.roles.some((r) => CREATOR_ROLES.has(r))
    : false;

  const loadAll = useCallback(async (authToken: string) => {
    setLoading(true);
    setError(null);
    try {
      const [patRows, testRows, histRows] = await Promise.all([
        listExamPatterns(authToken),
        listTests(authToken),
        listAttemptHistory(authToken),
      ]);
      setPatterns(patRows);
      setTests(testRows);
      setHistory(histRows);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "LOAD_ERROR",
          message: "Unable to load assessments catalog.",
        });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    void loadAll(token);
  }, [initializing, token, router, loadAll]);

  async function handleStartTest(testId: string) {
    if (!token) return;
    setBusyId(testId);
    setError(null);
    try {
      const attempt = await startTestAttempt(token, testId);
      router.push(`/assessments/${attempt.attempt_id}`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "START_ERROR",
          message: "Unable to start assessment.",
        });
      }
      setBusyId(null);
    }
  }

  async function handlePublishTest(testId: string) {
    if (!token) return;
    setBusyId(testId);
    setError(null);
    try {
      const updated = await publishTestTemplate(token, testId);
      setTests((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      }
    } finally {
      setBusyId(null);
    }
  }

  async function handleCreateTemplate(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setCreatingTest(true);
    setError(null);
    try {
      const created = await createTestTemplate(token, {
        title: newTitle.trim(),
        test_category: newCategory,
        exam_pattern_id: selectedPatternId || null,
        duration_seconds: durationMinutes * 60,
        grace_seconds: 30,
        sections: [
          {
            name: secName.trim() || "Section A",
            question_count: secQCount,
            scoring_rule: {
              mode: "standard",
              correct_marks: secCorrectMarks,
              wrong_marks:
                secWrongMarks <= 0 ? secWrongMarks : -Math.abs(secWrongMarks),
              unanswered_marks: 0,
              partial_credit_per_correct_option: 0,
            },
          },
        ],
      });
      setTests((prev) => [created, ...prev]);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "CREATE_TEST_FAILED",
          message: "Failed to create assessment template.",
        });
      }
    } finally {
      setCreatingTest(false);
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">
          Assessments & Configurable Exam Patterns
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Versioned database exam blueprints (CBSE, JEE Main, JEE Advanced, NEET), published test templates, and authoritative attempt history.
        </p>
      </header>

      {error ? (
        <ErrorBanner
          title={`Assessment Error (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      {loading ? <LoadingCard message="Loading exam patterns and tests..." /> : null}

      {!loading ? (
        <>
          <section aria-labelledby="patterns-heading" className="space-y-3">
            <h2
              id="patterns-heading"
              className="text-lg font-semibold text-slate-900"
            >
              Active Configurable Exam Patterns ({patterns.length})
            </h2>
            {patterns.length === 0 ? (
              <EmptyState
                title="No Exam Patterns Configured"
                description="Versioned exam patterns appear here once configured by administrators."
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {patterns.map((p) => (
                  <article
                    key={p.id}
                    className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-slate-900">
                        {p.exam_track_name} ({p.version_label})
                      </h3>
                      <StatusBadge tone="neutral">
                        {p.effective_year}
                      </StatusBadge>
                    </div>
                    <p className="mt-1 text-xs text-slate-600">
                      Duration:{" "}
                      {p.rules.duration_seconds
                        ? `${Math.round(p.rules.duration_seconds / 60)} min`
                        : "Untimed"}{" "}
                      · Grace: {p.rules.grace_seconds}s
                    </p>
                    <ul className="mt-2 space-y-1 text-xs text-slate-700">
                      {p.rules.sections.map((s) => (
                        <li key={s.code}>
                          <span className="font-medium">{s.name}:</span>{" "}
                          {s.question_count} Qs
                          {s.attempt_limit ? ` (max ${s.attempt_limit})` : ""} ·
                          +{s.scoring.correct_marks} / {s.scoring.wrong_marks} (
                          {s.scoring.mode})
                        </li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            )}
          </section>

          {canCreateTests ? (
            <section
              aria-labelledby="builder-heading"
              className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-6"
            >
              <h2
                id="builder-heading"
                className="text-lg font-semibold text-slate-900"
              >
                Educator / Admin Test Template Builder
              </h2>
              <form
                onSubmit={(e) => void handleCreateTemplate(e)}
                className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
              >
                <div>
                  <label
                    htmlFor="test-title"
                    className="block text-sm font-medium text-slate-800"
                  >
                    Test Title
                  </label>
                  <input
                    id="test-title"
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label
                    htmlFor="test-cat"
                    className="block text-sm font-medium text-slate-800"
                  >
                    Category
                  </label>
                  <select
                    id="test-cat"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="cbse_mock">CBSE Mock</option>
                    <option value="jee_main">JEE Main</option>
                    <option value="jee_adv">JEE Advanced</option>
                    <option value="neet">NEET</option>
                    <option value="chapter_test">Chapter Test</option>
                    <option value="teacher_test">Teacher Test</option>
                  </select>
                </div>
                <div>
                  <label
                    htmlFor="test-pattern"
                    className="block text-sm font-medium text-slate-800"
                  >
                    Linked Pattern (Optional)
                  </label>
                  <select
                    id="test-pattern"
                    value={selectedPatternId}
                    onChange={(e) => setSelectedPatternId(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Standalone Custom Rule</option>
                    {patterns.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.version_label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label
                    htmlFor="sec-name"
                    className="block text-sm font-medium text-slate-800"
                  >
                    Section Name
                  </label>
                  <input
                    id="sec-name"
                    type="text"
                    required
                    value={secName}
                    onChange={(e) => setSecName(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label
                      htmlFor="sec-qcount"
                      className="block text-xs font-medium text-slate-800"
                    >
                      Qs
                    </label>
                    <input
                      id="sec-qcount"
                      type="number"
                      min={1}
                      value={secQCount}
                      onChange={(e) =>
                        setSecQCount(Number(e.target.value) || 1)
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="sec-plus"
                      className="block text-xs font-medium text-slate-800"
                    >
                      +Marks
                    </label>
                    <input
                      id="sec-plus"
                      type="number"
                      min={1}
                      value={secCorrectMarks}
                      onChange={(e) =>
                        setSecCorrectMarks(Number(e.target.value) || 1)
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="sec-neg"
                      className="block text-xs font-medium text-slate-800"
                    >
                      -Neg
                    </label>
                    <input
                      id="sec-neg"
                      type="number"
                      max={0}
                      value={secWrongMarks}
                      onChange={(e) =>
                        setSecWrongMarks(Number(e.target.value) || 0)
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm"
                    />
                  </div>
                </div>
                <div className="flex items-end justify-between gap-2">
                  <div className="w-28">
                    <label
                      htmlFor="test-dur"
                      className="block text-xs font-medium text-slate-800"
                    >
                      Minutes
                    </label>
                    <input
                      id="test-dur"
                      type="number"
                      min={1}
                      value={durationMinutes}
                      onChange={(e) =>
                        setDurationMinutes(Number(e.target.value) || 10)
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={creatingTest}
                    className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-50"
                  >
                    {creatingTest ? "Creating..." : "Create Draft Test"}
                  </button>
                </div>
              </form>
            </section>
          ) : null}

          <section aria-labelledby="tests-heading" className="space-y-3">
            <h2
              id="tests-heading"
              className="text-lg font-semibold text-slate-900"
            >
              Assessment Templates ({tests.length})
            </h2>
            {tests.length === 0 ? (
              <EmptyState
                title="No Published Tests Available"
                description="Published mock exams and teacher-created tests will appear here once published."
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {tests.map((t) => (
                  <article
                    key={t.id}
                    className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <StatusBadge tone="neutral">
                          {t.test_category}
                        </StatusBadge>
                        <StatusBadge
                          tone={
                            t.status === "PUBLISHED" ? "healthy" : "degraded"
                          }
                        >
                          {t.status}
                        </StatusBadge>
                      </div>
                      <h3 className="mt-2 text-base font-semibold text-slate-900">
                        {t.title}
                      </h3>
                      <p className="mt-1 text-sm text-slate-600">
                        Max Marks: {t.total_marks} ·{" "}
                        {t.duration_seconds
                          ? `${Math.round(t.duration_seconds / 60)} min`
                          : "Untimed"}{" "}
                        · {t.sections.length} section(s)
                      </p>
                    </div>
                    <div className="mt-4 flex justify-end gap-2">
                      {t.status === "DRAFT" && canCreateTests ? (
                        <button
                          type="button"
                          disabled={busyId === t.id}
                          onClick={() => void handlePublishTest(t.id)}
                          className="rounded-md border border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
                        >
                          Publish Test
                        </button>
                      ) : null}
                      {t.status === "PUBLISHED" ? (
                        <button
                          type="button"
                          disabled={busyId === t.id}
                          onClick={() => void handleStartTest(t.id)}
                          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        >
                          {busyId === t.id ? "Starting..." : "Launch Test"}
                        </button>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section aria-labelledby="history-heading" className="space-y-3">
            <h2
              id="history-heading"
              className="text-lg font-semibold text-slate-900"
            >
              Attempt History ({history.length})
            </h2>
            {history.length === 0 ? (
              <EmptyState
                title="No Attempts Yet"
                description="Start a quiz or assessment to see your timed attempt history here."
              />
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-600">
                    <tr>
                      <th className="px-4 py-3">Assessment</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Score</th>
                      <th className="px-4 py-3">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {history.map((h) => (
                      <tr key={h.attempt_id}>
                        <td className="px-4 py-3 font-medium text-slate-900">
                          {h.title}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {h.source_kind}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge
                            tone={
                              h.status === "in_progress"
                                ? "degraded"
                                : "healthy"
                            }
                          >
                            {h.status}
                          </StatusBadge>
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {h.raw_score !== null && h.max_score !== null
                            ? `${h.raw_score} / ${h.max_score} (${h.accuracy_pct ?? 0}%)`
                            : "In Progress"}
                        </td>
                        <td className="px-4 py-3">
                          {h.status === "in_progress" ? (
                            <Link
                              href={`/assessments/${h.attempt_id}`}
                              className="font-medium text-indigo-700 hover:underline"
                            >
                              Resume
                            </Link>
                          ) : (
                            <Link
                              href={`/assessments/${h.attempt_id}/result`}
                              className="font-medium text-indigo-700 hover:underline"
                            >
                              View Result
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
