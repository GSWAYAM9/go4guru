"use client";

import type {
  AttemptQuestionStateItem,
  AttemptStateResponse,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MathText } from "@/components/math-text";
import {
  ApiClientError,
  type AutosaveAnswerPayload,
  autosaveAttemptAnswers,
  getAttemptState,
  submitAttempt,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

function formatTimer(totalSec: number | null): string {
  if (totalSec === null) return "Untimed";
  const clamped = Math.max(0, Math.floor(totalSec));
  const hrs = Math.floor(clamped / 3600);
  const mins = Math.floor((clamped % 3600) / 60);
  const secs = clamped % 60;
  if (hrs > 0) {
    return `${hrs}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function hasAnswerValue(q: AttemptQuestionStateItem): boolean {
  const r = q.response_jsonb;
  if (!r) return false;
  if (typeof r.selected_key === "string" && r.selected_key.trim() !== "") {
    return true;
  }
  if (Array.isArray(r.selected_keys) && r.selected_keys.length > 0) {
    return true;
  }
  if (
    r.numeric_value !== undefined &&
    r.numeric_value !== null &&
    String(r.numeric_value).trim() !== ""
  ) {
    return true;
  }
  if (typeof r.text_answer === "string" && r.text_answer.trim() !== "") {
    return true;
  }
  return false;
}

export default function AttemptRunnerPage() {
  const params = useParams<{ attemptId: string }>();
  const attemptId = params.attemptId;
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [state, setState] = useState<AttemptStateResponse | null>(null);
  const [questions, setQuestions] = useState<AttemptQuestionStateItem[]>([]);
  const [activeIdx, setActiveIdx] = useState(0);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  const idempotencyKeyRef = useRef<string>(
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? `sub-${crypto.randomUUID()}`
      : `sub-${attemptId}`
  );
  const activeIdxRef = useRef(0);
  useEffect(() => {
    activeIdxRef.current = activeIdx;
  }, [activeIdx]);

  const loadState = useCallback(
    async (authToken: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await getAttemptState(authToken, attemptId);
        if (res.status !== "in_progress") {
          router.replace(`/assessments/${attemptId}/result`);
          return;
        }
        setState(res);
        setQuestions(
          res.questions.map((q, i) =>
            i === 0 ? { ...q, is_visited: true } : q
          )
        );
        setRemainingSeconds(res.remaining_seconds);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        } else {
          setError({
            code: "LOAD_ATTEMPT_ERROR",
            message: "Unable to load active assessment attempt.",
          });
        }
      } finally {
        setLoading(false);
      }
    },
    [attemptId, router]
  );

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    void loadState(token);
  }, [initializing, token, router, loadState]);

  const timerActive =
    state?.status === "in_progress" && remainingSeconds !== null;

  // Client visual countdown synced from authoritative server remaining_seconds
  useEffect(() => {
    if (!timerActive) {
      return;
    }
    const timer = window.setInterval(() => {
      const curIdx = activeIdxRef.current;
      setRemainingSeconds((prev) =>
        prev === null ? null : Math.max(0, prev - 1)
      );
      setQuestions((prev) =>
        prev.map((q, idx) =>
          idx === curIdx
            ? { ...q, time_spent_seconds: q.time_spent_seconds + 1 }
            : q
        )
      );
    }, 1000);
    return () => window.clearInterval(timer);
  }, [timerActive]);

  const currentQuestion = questions[activeIdx] ?? null;

  function toPayloads(items: AttemptQuestionStateItem[]): AutosaveAnswerPayload[] {
    return items.map((q) => ({
      question_version_id: q.question_version_id,
      response_jsonb: q.response_jsonb,
      is_visited: q.is_visited,
      is_marked_for_review: q.is_marked_for_review,
      time_spent_seconds: q.time_spent_seconds,
    }));
  }

  async function persistAnswers(
    nextQuestions: AttemptQuestionStateItem[],
    silent = false
  ) {
    if (!token || !state) return;
    setSaving(true);
    if (!silent) setError(null);
    try {
      const res = await autosaveAttemptAnswers(
        token,
        attemptId,
        toPayloads(nextQuestions)
      );
      setRemainingSeconds(res.remaining_seconds);
      setStatusNotice(
        `Saved ${res.saved_count} responses (${new Date(res.server_now_utc).toLocaleTimeString()})`
      );
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      }
    } finally {
      setSaving(false);
    }
  }

  function updateCurrentQuestion(
    patch: Partial<AttemptQuestionStateItem>,
    autosaveAfter = false
  ) {
    const updated = questions.map((q, idx) =>
      idx === activeIdx ? { ...q, ...patch, is_visited: true } : q
    );
    setQuestions(updated);
    if (autosaveAfter) {
      void persistAnswers(updated, true);
    }
  }

  function selectQuestion(nextIndex: number) {
    const updated = questions.map((q, idx) =>
      idx === nextIndex ? { ...q, is_visited: true } : q
    );
    setQuestions(updated);
    setActiveIdx(nextIndex);
  }

  async function handleSaveAndNext() {
    await persistAnswers(questions);
    if (activeIdx + 1 < questions.length) {
      selectQuestion(activeIdx + 1);
    }
  }

  async function handleSubmit() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitAttempt(
        token,
        attemptId,
        idempotencyKeyRef.current,
        toPayloads(questions)
      );
      router.push(`/assessments/${attemptId}/result`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "SUBMIT_ERROR",
          message: "Failed to submit attempt.",
        });
      }
      setSubmitting(false);
    }
  }

  const summary = useMemo(() => {
    const answered = questions.filter(hasAnswerValue).length;
    const marked = questions.filter((q) => q.is_marked_for_review).length;
    return { answered, marked, total: questions.length };
  }, [questions]);

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">
      {loading ? <LoadingCard message="Loading assessment session..." /> : null}

      {error ? (
        <ErrorBanner
          title={`Session Alert (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      {error?.code === "ASSESSMENT_TIME_EXPIRED" ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Your pre-expiry autosaved answers have been auto-submitted by the server.{" "}
          <Link
            href={`/assessments/${attemptId}/result`}
            className="font-semibold underline"
          >
            View Final Result
          </Link>
        </div>
      ) : null}

      {!loading && state && !currentQuestion ? (
        <EmptyState
          title="No Questions In Attempt"
          description="This attempt has no assigned question versions."
        />
      ) : null}

      {!loading && state && currentQuestion ? (
        <>
          <header className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            <div>
              <div className="flex items-center gap-2">
                <StatusBadge tone="neutral">{state.source_kind}</StatusBadge>
                <span className="text-xs text-slate-600">
                  {summary.answered}/{summary.total} Answered · {summary.marked}{" "}
                  Marked for Review
                </span>
              </div>
              <h1 className="mt-1 text-xl font-bold text-slate-900">
                {state.title}
              </h1>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div
                aria-live="polite"
                className="rounded-lg border border-slate-300 bg-slate-50 px-4 py-2 text-center"
              >
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Server Timer
                </span>
                <span
                  data-testid="assessment-timer"
                  className="font-mono text-lg font-bold text-slate-900"
                >
                  {formatTimer(remainingSeconds)}
                </span>
              </div>
              <button
                type="button"
                disabled={saving}
                onClick={() => void persistAnswers(questions)}
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Now"}
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => void handleSubmit()}
                className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
              >
                {submitting ? "Submitting..." : "Submit Assessment"}
              </button>
            </div>
          </header>

          {statusNotice ? (
            <p className="text-xs text-slate-600" role="status">
              {statusNotice}
            </p>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-4">
            <section
              aria-label="Question Workspace"
              className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-xs lg:col-span-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">
                    Question {currentQuestion.sequence_no} of {questions.length}
                  </span>
                  {currentQuestion.section_name ? (
                    <StatusBadge tone="neutral">
                      {currentQuestion.section_name}
                    </StatusBadge>
                  ) : null}
                  <StatusBadge tone="neutral">
                    {currentQuestion.difficulty}
                  </StatusBadge>
                </div>
                <span className="text-xs font-medium text-slate-600">
                  +{currentQuestion.marks} / {currentQuestion.negative_marks}
                </span>
              </div>

              <div className="text-base leading-relaxed text-slate-900">
                <MathText text={currentQuestion.stem_markdown} />
              </div>

              {(currentQuestion.question_type === "mcq_single" ||
                currentQuestion.question_type === "assertion_reason") && (
                <fieldset className="space-y-2">
                  <legend className="sr-only">Select one option</legend>
                  {currentQuestion.options.map((opt) => {
                    const checked =
                      String(
                        currentQuestion.response_jsonb.selected_key ?? ""
                      ).toUpperCase() === opt.option_key.toUpperCase();
                    return (
                      <label
                        key={opt.option_key}
                        className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition ${
                          checked
                            ? "border-indigo-600 bg-indigo-50"
                            : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="radio"
                          name={`q-${currentQuestion.question_version_id}`}
                          value={opt.option_key}
                          checked={checked}
                          onChange={() =>
                            updateCurrentQuestion({
                              response_jsonb: { selected_key: opt.option_key },
                            })
                          }
                          className="mt-1 h-4 w-4 text-indigo-700"
                        />
                        <div>
                          <span className="mr-2 font-semibold text-slate-900">
                            ({opt.option_key})
                          </span>
                          <MathText text={opt.content_markdown} />
                        </div>
                      </label>
                    );
                  })}
                </fieldset>
              )}

              {currentQuestion.question_type === "mcq_multiple" && (
                <fieldset className="space-y-2">
                  <legend className="sr-only">Select one or more options</legend>
                  {currentQuestion.options.map((opt) => {
                    const currentKeys = Array.isArray(
                      currentQuestion.response_jsonb.selected_keys
                    )
                      ? (currentQuestion.response_jsonb.selected_keys as string[])
                      : [];
                    const checked = currentKeys.includes(opt.option_key);
                    return (
                      <label
                        key={opt.option_key}
                        className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition ${
                          checked
                            ? "border-indigo-600 bg-indigo-50"
                            : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            const nextKeys = checked
                              ? currentKeys.filter((k) => k !== opt.option_key)
                              : [...currentKeys, opt.option_key];
                            updateCurrentQuestion({
                              response_jsonb: { selected_keys: nextKeys },
                            });
                          }}
                          className="mt-1 h-4 w-4 rounded text-indigo-700"
                        />
                        <div>
                          <span className="mr-2 font-semibold text-slate-900">
                            ({opt.option_key})
                          </span>
                          <MathText text={opt.content_markdown} />
                        </div>
                      </label>
                    );
                  })}
                </fieldset>
              )}

              {(currentQuestion.question_type === "numerical" ||
                currentQuestion.question_type === "integer") && (
                <div>
                  <label
                    htmlFor="numeric-response"
                    className="block text-sm font-medium text-slate-800"
                  >
                    Numeric Value
                  </label>
                  <input
                    id="numeric-response"
                    type="number"
                    step="any"
                    value={String(
                      currentQuestion.response_jsonb.numeric_value ?? ""
                    )}
                    onChange={(e) =>
                      updateCurrentQuestion({
                        response_jsonb:
                          e.target.value === ""
                            ? {}
                            : { numeric_value: Number(e.target.value) },
                      })
                    }
                    className="mt-1 w-60 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </div>
              )}

              {![
                "mcq_single",
                "assertion_reason",
                "mcq_multiple",
                "numerical",
                "integer",
              ].includes(currentQuestion.question_type) && (
                <div>
                  <label
                    htmlFor="text-response"
                    className="block text-sm font-medium text-slate-800"
                  >
                    Your Answer
                  </label>
                  <textarea
                    id="text-response"
                    rows={3}
                    value={String(
                      currentQuestion.response_jsonb.text_answer ?? ""
                    )}
                    onChange={(e) =>
                      updateCurrentQuestion({
                        response_jsonb: { text_answer: e.target.value },
                      })
                    }
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={activeIdx === 0}
                    onClick={() => selectQuestion(Math.max(0, activeIdx - 1))}
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      updateCurrentQuestion(
                        {
                          is_marked_for_review:
                            !currentQuestion.is_marked_for_review,
                        },
                        true
                      )
                    }
                    className={`rounded-md border px-3 py-2 text-sm font-medium ${
                      currentQuestion.is_marked_for_review
                        ? "border-amber-600 bg-amber-100 text-amber-900"
                        : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
                    }`}
                  >
                    {currentQuestion.is_marked_for_review
                      ? "Unmark Review"
                      : "Mark for Review"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      updateCurrentQuestion({ response_jsonb: {} }, true)
                    }
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Clear Response
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => void handleSaveAndNext()}
                  className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
                >
                  Save & Next
                </button>
              </div>
            </section>

            <aside
              aria-label="Question Palette"
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
            >
              <h2 className="text-sm font-semibold text-slate-900">
                Question Palette
              </h2>
              <div className="mt-3 grid grid-cols-5 gap-2">
                {questions.map((q, idx) => {
                  const answered = hasAnswerValue(q);
                  let style = "border-slate-300 bg-white text-slate-700";
                  if (q.is_marked_for_review) {
                    style = "border-amber-500 bg-amber-100 text-amber-900";
                  } else if (answered) {
                    style =
                      "border-emerald-600 bg-emerald-100 text-emerald-900";
                  } else if (q.is_visited) {
                    style = "border-rose-300 bg-rose-50 text-rose-800";
                  }
                  return (
                    <button
                      key={q.question_version_id}
                      type="button"
                      aria-label={`Question ${q.sequence_no}${q.is_marked_for_review ? " marked for review" : answered ? " answered" : ""}`}
                      onClick={() => selectQuestion(idx)}
                      className={`h-10 rounded-md border text-sm font-semibold ${style} ${
                        idx === activeIdx ? "ring-2 ring-indigo-600" : ""
                      }`}
                    >
                      {q.sequence_no}
                    </button>
                  );
                })}
              </div>

              <dl className="mt-4 space-y-1 text-xs text-slate-600">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded border border-emerald-600 bg-emerald-100" />
                  <dt>Answered</dt>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded border border-amber-500 bg-amber-100" />
                  <dt>Marked for Review</dt>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded border border-rose-300 bg-rose-50" />
                  <dt>Visited (Unanswered)</dt>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded border border-slate-300 bg-white" />
                  <dt>Not Visited</dt>
                </div>
              </dl>
            </aside>
          </div>
        </>
      ) : null}
    </main>
  );
}
