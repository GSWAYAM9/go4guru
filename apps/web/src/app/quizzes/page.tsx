"use client";

import type { QuizOut, SubjectOut } from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ApiClientError,
  fetchSubjects,
  generateQuiz,
  listQuizzes,
  startQuizAttempt,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function QuizzesPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [quizzes, setQuizzes] = useState<QuizOut[]>([]);
  const [subjects, setSubjects] = useState<SubjectOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  // Quiz Generator Form State
  const [title, setTitle] = useState("Timed Practice Sprint");
  const [quizType, setQuizType] = useState("chapter");
  const [subjectId, setSubjectId] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [durationMinutes, setDurationMinutes] = useState(10);
  const [shuffleQuestions, setShuffleQuestions] = useState(true);
  const [easyCount, setEasyCount] = useState(2);
  const [mediumCount, setMediumCount] = useState(2);
  const [hardCount, setHardCount] = useState(1);
  const [correctMarks, setCorrectMarks] = useState(4);
  const [wrongMarks, setWrongMarks] = useState(-1);

  const loadData = useCallback(async (authToken: string) => {
    setLoading(true);
    setError(null);
    try {
      const [quizRows, subRows] = await Promise.all([
        listQuizzes(authToken),
        fetchSubjects(),
      ]);
      setQuizzes(quizRows);
      setSubjects(subRows);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "LOAD_FAILED",
          message: "Unable to load quizzes right now.",
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
    void loadData(token);
  }, [initializing, token, router, loadData]);

  async function handleGenerateQuiz(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const difficulty_distribution: Record<string, number> = {};
      if (easyCount > 0) difficulty_distribution.easy = easyCount;
      if (mediumCount > 0) difficulty_distribution.medium = mediumCount;
      if (hardCount > 0) difficulty_distribution.hard = hardCount;

      const created = await generateQuiz(token, {
        quiz_type: quizType,
        title: title.trim() || "Timed Quiz",
        subject_id: subjectId || null,
        question_count: questionCount,
        duration_seconds: durationMinutes > 0 ? durationMinutes * 60 : null,
        shuffle_questions: shuffleQuestions,
        difficulty_distribution,
        scoring_rule: {
          mode: "standard",
          correct_marks: correctMarks,
          wrong_marks: wrongMarks <= 0 ? wrongMarks : -Math.abs(wrongMarks),
          unanswered_marks: 0,
          partial_credit_per_correct_option: 0,
        },
      });
      setQuizzes((prev) => [created, ...prev]);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "QUIZ_GEN_ERROR",
          message: "Failed to generate quiz.",
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStartQuiz(quizId: string) {
    if (!token) return;
    setLaunchingId(quizId);
    setError(null);
    try {
      const attempt = await startQuizAttempt(token, quizId);
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
          code: "START_FAILED",
          message: "Unable to start quiz attempt.",
        });
      }
      setLaunchingId(null);
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">
          Configurable Quiz Engine
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Generate chapter, topic, diagnostic, revision, or timed quizzes directly from published questions with server-enforced timing and negative marking.
        </p>
      </header>

      {error ? (
        <ErrorBanner
          title={`Quiz Engine Notice (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      <section
        aria-labelledby="quiz-generator-heading"
        className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs"
      >
        <h2
          id="quiz-generator-heading"
          className="text-lg font-semibold text-slate-900"
        >
          Generate a Custom Timed Quiz
        </h2>
        <form
          onSubmit={(e) => void handleGenerateQuiz(e)}
          className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <div>
            <label
              htmlFor="quiz-title"
              className="block text-sm font-medium text-slate-800"
            >
              Quiz Title
            </label>
            <input
              id="quiz-title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="quiz-type"
              className="block text-sm font-medium text-slate-800"
            >
              Quiz Mode
            </label>
            <select
              id="quiz-type"
              value={quizType}
              onChange={(e) => setQuizType(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            >
              <option value="chapter">Chapter Quiz</option>
              <option value="topic">Topic Quiz</option>
              <option value="diagnostic">Diagnostic Quiz</option>
              <option value="quick">Quick Quiz</option>
              <option value="revision">Revision Quiz</option>
              <option value="teacher">Teacher Assigned Style</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="quiz-subject"
              className="block text-sm font-medium text-slate-800"
            >
              Subject Filter (Optional)
            </label>
            <select
              id="quiz-subject"
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            >
              <option value="">All Published Subjects</option>
              {subjects.map((sub) => (
                <option key={sub.id} value={sub.id}>
                  {sub.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="quiz-count"
              className="block text-sm font-medium text-slate-800"
            >
              Question Count
            </label>
            <input
              id="quiz-count"
              type="number"
              min={1}
              max={100}
              value={questionCount}
              onChange={(e) => setQuestionCount(Number(e.target.value) || 1)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="quiz-duration"
              className="block text-sm font-medium text-slate-800"
            >
              Duration (Minutes)
            </label>
            <input
              id="quiz-duration"
              type="number"
              min={1}
              max={240}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value) || 1)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label
                htmlFor="quiz-correct-marks"
                className="block text-sm font-medium text-slate-800"
              >
                Correct (+)
              </label>
              <input
                id="quiz-correct-marks"
                type="number"
                step="0.5"
                min={0.5}
                value={correctMarks}
                onChange={(e) => setCorrectMarks(Number(e.target.value) || 1)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
              />
            </div>
            <div>
              <label
                htmlFor="quiz-wrong-marks"
                className="block text-sm font-medium text-slate-800"
              >
                Negative (-)
              </label>
              <input
                id="quiz-wrong-marks"
                type="number"
                step="0.25"
                max={0}
                value={wrongMarks}
                onChange={(e) => setWrongMarks(Number(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
              />
            </div>
          </div>

          <fieldset className="grid grid-cols-3 gap-2 sm:col-span-2">
            <legend className="text-xs font-semibold uppercase tracking-wide text-slate-600">
              Difficulty Mix Targets (Optional)
            </legend>
            <div>
              <label htmlFor="mix-easy" className="block text-xs text-slate-700">
                Easy
              </label>
              <input
                id="mix-easy"
                type="number"
                min={0}
                value={easyCount}
                onChange={(e) => setEasyCount(Number(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="mix-medium" className="block text-xs text-slate-700">
                Medium
              </label>
              <input
                id="mix-medium"
                type="number"
                min={0}
                value={mediumCount}
                onChange={(e) => setMediumCount(Number(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="mix-hard" className="block text-xs text-slate-700">
                Hard
              </label>
              <input
                id="mix-hard"
                type="number"
                min={0}
                value={hardCount}
                onChange={(e) => setHardCount(Number(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
            </div>
          </fieldset>

          <div className="flex items-end justify-between gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={shuffleQuestions}
                onChange={(e) => setShuffleQuestions(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-700"
              />
              Randomize Order
            </label>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-50"
            >
              {submitting ? "Generating..." : "Create Quiz"}
            </button>
          </div>
        </form>
      </section>

      <section aria-labelledby="quiz-list-heading" className="space-y-4">
        <h2
          id="quiz-list-heading"
          className="text-lg font-semibold text-slate-900"
        >
          Your & Assigned Quizzes
        </h2>

        {loading ? <LoadingCard message="Loading quizzes..." /> : null}

        {!loading && quizzes.length === 0 ? (
          <EmptyState
            title="No Quizzes Created Yet"
            description="Configure a timed quiz above using published curriculum questions to begin."
          />
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          {quizzes.map((q) => (
            <article
              key={q.id}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <StatusBadge tone="neutral">{q.quiz_type}</StatusBadge>
                  <span className="text-xs text-slate-500">
                    {q.duration_seconds
                      ? `${Math.round(q.duration_seconds / 60)} min`
                      : "Untimed"}
                  </span>
                </div>
                <h3 className="mt-2 text-base font-semibold text-slate-900">
                  {q.title}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  {q.question_count} questions ·{" "}
                  {q.shuffle_questions ? "Randomized" : "Fixed sequence"}
                </p>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  disabled={launchingId === q.id}
                  onClick={() => void handleStartQuiz(q.id)}
                  className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {launchingId === q.id ? "Starting..." : "Start Timed Attempt"}
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
