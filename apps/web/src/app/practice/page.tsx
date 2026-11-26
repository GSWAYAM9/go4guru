"use client";

import type {
  AttemptResultOut,
  PracticeSessionOut,
  QuestionOut,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { MathText } from "@/components/math-text";
import {
  ApiClientError,
  createStudentNote,
  revealPracticeHint,
  saveBookmark,
  searchQuestionsApi,
  startPracticeSession,
  submitPracticeAttempt,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

function PracticeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, initializing } = useAuth();

  const initialChapterId = searchParams.get("chapterId") ?? "";
  const initialSubjectId = searchParams.get("subjectId") ?? "";
  const initialConceptId = searchParams.get("conceptId") ?? "";

  const [queryText, setQueryText] = useState("");
  const [searchResults, setSearchResults] = useState<QuestionOut[]>([]);
  const [session, setSession] = useState<PracticeSessionOut | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  const [selectedKey, setSelectedKey] = useState("");
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [numericAnswer, setNumericAnswer] = useState("");
  const [textAnswer, setTextAnswer] = useState("");

  const [hints, setHints] = useState<Record<string, string[]>>({});
  const [attemptsByQuestion, setAttemptsByQuestion] = useState<
    Record<string, AttemptResultOut>
  >({});

  const [noteTitle, setNoteTitle] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(
    async (authToken: string, text: string) => {
      try {
        const res = await searchQuestionsApi(authToken, {
          q: text || undefined,
          chapterId: initialChapterId || undefined,
          subjectId: initialSubjectId || undefined,
          limit: 20,
        });
        setSearchResults(res.items);
      } catch {
        // Surfaced if user opens practice
      }
    },
    [initialChapterId, initialSubjectId]
  );

  const launchSession = useCallback(
    async (authToken: string) => {
      setLoading(true);
      setError(null);
      try {
        const ps = await startPracticeSession(authToken, {
          chapter_id: initialChapterId || null,
          subject_id: initialSubjectId || null,
          concept_id: initialConceptId || null,
          limit: 10,
        });
        setSession(ps);
        setCurrentIndex(0);
      } catch (err) {
        setError(
          err instanceof ApiClientError
            ? err.message
            : "Unable to start practice session."
        );
      } finally {
        setLoading(false);
      }
    },
    [initialChapterId, initialSubjectId, initialConceptId]
  );

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    void launchSession(token);
    void runSearch(token, "");
  }, [initializing, token, router, launchSession, runSearch]);

  const activeQuestion = session?.questions[currentIndex] ?? null;
  const activeAttempt = activeQuestion
    ? attemptsByQuestion[activeQuestion.question_id]
    : undefined;
  const activeHints = activeQuestion ? (hints[activeQuestion.question_id] ?? []) : [];

  async function handleRevealHint() {
    if (!token || !session || !activeQuestion) return;
    const nextLevel = Math.min(3, activeHints.length + 1);
    setError(null);
    try {
      const res = await revealPracticeHint(
        token,
        session.id,
        activeQuestion.question_id,
        nextLevel
      );
      if (res.hint_markdown) {
        const hintMarkdown = res.hint_markdown;
        setHints((prev) => ({
          ...prev,
          [activeQuestion.question_id]: [
            ...(prev[activeQuestion.question_id] ?? []),
            hintMarkdown,
          ],
        }));
      } else {
        setActionMsg(`No Hint Level ${nextLevel} authored for this question.`);
      }
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Failed to fetch hint."
      );
    }
  }

  async function handleSubmitAttempt() {
    if (!token || !session || !activeQuestion) return;
    setError(null);
    let response_jsonb: Record<string, unknown> = {};
    if (
      activeQuestion.question_type === "mcq_single" ||
      activeQuestion.question_type === "assertion_reason"
    ) {
      response_jsonb = { selected_key: selectedKey };
    } else if (activeQuestion.question_type === "mcq_multiple") {
      response_jsonb = { selected_keys: selectedKeys };
    } else if (
      activeQuestion.question_type === "numerical" ||
      activeQuestion.question_type === "integer"
    ) {
      response_jsonb = { numeric_value: Number(numericAnswer) };
    } else {
      response_jsonb = { text_answer: textAnswer };
    }

    try {
      const res = await submitPracticeAttempt(token, session.id, {
        question_id: activeQuestion.question_id,
        response_jsonb,
        time_spent_seconds: 15,
      });
      setAttemptsByQuestion((prev) => ({
        ...prev,
        [activeQuestion.question_id]: res,
      }));
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Failed to grade attempt."
      );
    }
  }

  async function handleBookmark() {
    if (!token || !activeQuestion) return;
    try {
      await saveBookmark(token, activeQuestion.question_id, "Practice Saved");
      setActionMsg("Question saved to your bookmarks.");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Bookmark failed.");
    }
  }

  async function handleSaveNote() {
    if (!token || !activeQuestion || !noteTitle.trim() || !noteBody.trim()) return;
    try {
      await createStudentNote(token, {
        title: noteTitle.trim(),
        body_markdown: noteBody.trim(),
        question_id: activeQuestion.question_id,
      });
      setNoteTitle("");
      setNoteBody("");
      setActionMsg("Personal note saved.");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Note save failed.");
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Guided Practice Engine
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Solve published questions with graduated hints, immediate server feedback, and verified solutions.
          </p>
        </div>
        {token ? (
          <button
            type="button"
            onClick={() => void launchSession(token)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            New Practice Session
          </button>
        ) : null}
      </header>

      {error ? <ErrorBanner title="Practice Error" message={error} /> : null}
      {actionMsg ? (
        <div
          role="status"
          className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-900"
        >
          {actionMsg}
        </div>
      ) : null}

      {loading ? <LoadingCard message="Starting practice session..." /> : null}

      {!loading && session && session.questions.length === 0 ? (
        <EmptyState
          title="No Published Questions Available Yet"
          description="Only reviewer-approved PUBLISHED questions appear in student practice sessions. Publish questions or commit & approve an Excel import in Admin Studio."
        />
      ) : null}

      {!loading && activeQuestion ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <span className="font-semibold text-slate-900">
                Question {currentIndex + 1} of {session?.questions.length}
              </span>
              <StatusBadge tone="neutral">{activeQuestion.question_type}</StatusBadge>
              <StatusBadge tone="neutral">{activeQuestion.difficulty}</StatusBadge>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void handleBookmark()}
                className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50"
              >
                Save Bookmark
              </button>
              <button
                type="button"
                disabled={activeHints.length >= 3}
                onClick={() => void handleRevealHint()}
                className="rounded border border-indigo-300 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-900 hover:bg-indigo-100 disabled:opacity-50"
              >
                Reveal Hint ({activeHints.length}/3)
              </button>
            </div>
          </div>

          <div className="mt-4 text-base text-slate-900">
            <MathText text={activeQuestion.stem_markdown} />
          </div>

          {activeHints.length > 0 ? (
            <div className="mt-4 space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
              {activeHints.map((h, i) => (
                <p key={i}>
                  <strong>Hint {i + 1}:</strong> <MathText text={h} />
                </p>
              ))}
            </div>
          ) : null}

          <div className="mt-5 space-y-2">
            {activeQuestion.options.length > 0 ? (
              activeQuestion.options.map((opt) => {
                const isMulti = activeQuestion.question_type === "mcq_multiple";
                const checked = isMulti
                  ? selectedKeys.includes(opt.option_key)
                  : selectedKey === opt.option_key;
                return (
                  <label
                    key={opt.option_key}
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${
                      checked
                        ? "border-indigo-600 bg-indigo-50"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type={isMulti ? "checkbox" : "radio"}
                      name={`q-${activeQuestion.question_id}`}
                      checked={checked}
                      onChange={() => {
                        if (isMulti) {
                          setSelectedKeys((prev) =>
                            prev.includes(opt.option_key)
                              ? prev.filter((k) => k !== opt.option_key)
                              : [...prev, opt.option_key]
                          );
                        } else {
                          setSelectedKey(opt.option_key);
                        }
                      }}
                    />
                    <span className="font-semibold">{opt.option_key}.</span>
                    <MathText text={opt.content_markdown} />
                  </label>
                );
              })
            ) : activeQuestion.question_type === "numerical" ||
              activeQuestion.question_type === "integer" ? (
              <div>
                <label
                  htmlFor="num-input"
                  className="block text-sm font-medium text-slate-700"
                >
                  Enter Numeric Answer
                </label>
                <input
                  id="num-input"
                  type="number"
                  step="any"
                  value={numericAnswer}
                  onChange={(e) => setNumericAnswer(e.target.value)}
                  className="mt-1 w-48 rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            ) : (
              <div>
                <label
                  htmlFor="text-input"
                  className="block text-sm font-medium text-slate-700"
                >
                  Enter Answer
                </label>
                <textarea
                  id="text-input"
                  rows={3}
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            )}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => void handleSubmitAttempt()}
              className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
            >
              Check Answer
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={currentIndex === 0}
                onClick={() => {
                  setCurrentIndex((i) => Math.max(0, i - 1));
                  setSelectedKey("");
                  setSelectedKeys([]);
                  setNumericAnswer("");
                }}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!session || currentIndex >= session.questions.length - 1}
                onClick={() => {
                  setCurrentIndex((i) => i + 1);
                  setSelectedKey("");
                  setSelectedKeys([]);
                  setNumericAnswer("");
                }}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>

          {activeAttempt ? (
            <div
              role="status"
              className={`mt-5 rounded-lg border p-4 text-sm ${
                activeAttempt.is_correct
                  ? "border-emerald-300 bg-emerald-50 text-emerald-950"
                  : "border-red-300 bg-red-50 text-red-950"
              }`}
            >
              <p className="font-semibold">
                {activeAttempt.is_correct
                  ? `Correct! (+${activeAttempt.score_awarded} marks)`
                  : "Not quite right — review the verified explanation below."}
              </p>
              {activeAttempt.explanation_markdown ? (
                <p className="mt-2">
                  <strong>Solution:</strong>{" "}
                  <MathText text={activeAttempt.explanation_markdown} />
                </p>
              ) : null}
              {activeAttempt.common_mistakes_markdown ? (
                <p className="mt-1 text-xs">
                  <strong>Common Pitfall:</strong>{" "}
                  <MathText text={activeAttempt.common_mistakes_markdown} />
                </p>
              ) : null}
            </div>
          ) : null}

          <div className="mt-6 border-t border-slate-200 pt-4">
            <h3 className="text-sm font-semibold text-slate-900">
              Add Study Note for This Question
            </h3>
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              <input
                type="text"
                placeholder="Note title..."
                value={noteTitle}
                onChange={(e) => setNoteTitle(e.target.value)}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm"
              />
              <input
                type="text"
                placeholder="Markdown or $LaTeX$ summary..."
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm sm:col-span-2"
              />
            </div>
            <button
              type="button"
              onClick={() => void handleSaveNote()}
              className="mt-2 rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
            >
              Save Personal Note
            </button>
          </div>
        </section>
      ) : null}

      {token ? (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-slate-900">
              Question Bank Search ({searchResults.length})
            </h2>
            <div className="flex gap-2">
              <input
                type="search"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder="Search questions..."
                className="rounded border border-slate-300 px-3 py-1 text-sm"
              />
              <button
                type="button"
                onClick={() => void runSearch(token, queryText)}
                className="rounded bg-slate-800 px-3 py-1 text-sm text-white"
              >
                Filter
              </button>
            </div>
          </div>
          <ul className="mt-3 space-y-2 text-sm">
            {searchResults.map((q) => (
              <li key={q.id} className="rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>
                    {q.question_type} • {q.difficulty}
                  </span>
                  <span>{q.provenance?.is_pyq ? "Verified PYQ" : "Original/Bank"}</span>
                </div>
                <div className="mt-1 text-slate-900">
                  <MathText text={q.stem_markdown} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}

export default function PracticePage() {
  return (
    <Suspense fallback={<div className="p-8"><LoadingCard message="Loading practice workspace..." /></div>}>
      <PracticeContent />
    </Suspense>
  );
}
