"use client";

import type {
  AiMessageOut,
  AiModelsCatalogResponse,
  AiSessionOut,
  AiUsageQuotaResponse,
  SubjectOut,
  TeachingMode,
} from "@go4guru/contracts";
import {
  EmptyState,
  ErrorBanner,
  LoadingCard,
  StatusBadge,
} from "@go4guru/ui";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { MathText } from "@/components/math-text";
import {
  ApiClientError,
  createAiSession,
  fetchAiModels,
  fetchAiUsage,
  fetchSubjects,
  flagAiMessage,
  listAiMessages,
  listAiSessions,
  sendAiTurn,
  updateAiSessionMode,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

const MODES: { value: TeachingMode; label: string }[] = [
  { value: "explain", label: "Concept Explain" },
  { value: "step_by_step", label: "Step-by-Step Solver" },
  { value: "hint", label: "Hints (Anti-Spoiler)" },
  { value: "socratic", label: "Socratic Guide (Anti-Spoiler)" },
  { value: "practice", label: "Practice Generator" },
  { value: "exam_prep", label: "Exam Prep" },
  { value: "revision", label: "Revision Summary" },
];

export default function TutorPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [sessions, setSessions] = useState<AiSessionOut[]>([]);
  const [activeSession, setActiveSession] = useState<AiSessionOut | null>(null);
  const [messages, setMessages] = useState<AiMessageOut[]>([]);
  const [modelsCatalog, setModelsCatalog] =
    useState<AiModelsCatalogResponse | null>(null);
  const [usage, setUsage] = useState<AiUsageQuotaResponse | null>(null);
  const [subjects, setSubjects] = useState<SubjectOut[]>([]);

  const [newTitle, setNewTitle] = useState("New Curriculum Doubt Session");
  const [newSubjectId, setNewSubjectId] = useState("");
  const [newMode, setNewMode] = useState<TeachingMode>("explain");
  const [newLanguage, setNewLanguage] = useState("en");

  const [promptInput, setPromptInput] = useState("");
  const [turnMode, setTurnMode] = useState<TeachingMode>("explain");
  const [turnLanguage, setTurnLanguage] = useState("en");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [flagStatus, setFlagStatus] = useState<string | null>(null);
  const [error, setError] = useState<{
    code: string;
    message: string;
    requestId?: string;
  } | null>(null);

  const loadSessionMessages = useCallback(
    async (authToken: string, sess: AiSessionOut) => {
      setActiveSession(sess);
      setTurnMode(sess.teaching_mode);
      setTurnLanguage(sess.language_code);
      try {
        const rows = await listAiMessages(authToken, sess.id);
        setMessages(rows);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError({
            code: err.code,
            message: err.message,
            requestId: err.requestId,
          });
        }
      }
    },
    []
  );

  const loadInitial = useCallback(
    async (authToken: string) => {
      setLoading(true);
      setError(null);
      try {
        const [sessRows, modRes, usageRes, subRows] = await Promise.all([
          listAiSessions(authToken),
          fetchAiModels(authToken),
          fetchAiUsage(authToken),
          fetchSubjects(),
        ]);
        setSessions(sessRows);
        setModelsCatalog(modRes);
        setUsage(usageRes);
        setSubjects(subRows);
        if (sessRows.length > 0) {
          await loadSessionMessages(authToken, sessRows[0]);
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
            code: "TUTOR_LOAD_FAILED",
            message: "Unable to initialize AI Tutor workspace.",
          });
        }
      } finally {
        setLoading(false);
      }
    },
    [loadSessionMessages]
  );

  useEffect(() => {
    if (initializing) return;
    if (!token) {
      router.push("/login");
      return;
    }
    void loadInitial(token);
  }, [initializing, token, router, loadInitial]);

  async function handleCreateSession(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    try {
      const created = await createAiSession(token, {
        session_type: "tutor",
        title: newTitle.trim() || "Tutor Session",
        teaching_mode: newMode,
        language_code: newLanguage,
        subject_id: newSubjectId || null,
      });
      setSessions((prev) => [created, ...prev]);
      setActiveSession(created);
      setTurnMode(created.teaching_mode);
      setTurnLanguage(created.language_code);
      setMessages([]);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      }
    }
  }

  async function handleModeSync(nextMode: TeachingMode, nextLang: string) {
    setTurnMode(nextMode);
    setTurnLanguage(nextLang);
    if (!token || !activeSession) return;
    try {
      const updated = await updateAiSessionMode(token, activeSession.id, {
        teaching_mode: nextMode,
        language_code: nextLang,
      });
      setActiveSession(updated);
      setSessions((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s))
      );
    } catch {
      // Turn request also carries explicit mode/language
    }
  }

  async function submitPrompt(overrideText?: string) {
    const text = (overrideText ?? promptInput).trim();
    if (!token || !activeSession || !text) return;
    setSending(true);
    setError(null);
    setFlagStatus(null);
    try {
      const res = await sendAiTurn(token, activeSession.id, {
        message: text,
        teaching_mode: turnMode,
        language_code: turnLanguage,
      });
      setMessages((prev) => [
        ...prev,
        res.student_message,
        res.assistant_message,
      ]);
      if (!overrideText) setPromptInput("");
      const updatedUsage = await fetchAiUsage(token);
      setUsage(updatedUsage);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      } else {
        setError({
          code: "AI_TURN_ERROR",
          message: "Failed to complete AI Tutor turn.",
        });
      }
    } finally {
      setSending(false);
    }
  }

  async function handleFlagMessage(messageId: string) {
    if (!token) return;
    try {
      await flagAiMessage(
        token,
        messageId,
        "Student requested academic review"
      );
      setFlagStatus("Message flagged for Academic Reviewer queue.");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({
          code: err.code,
          message: err.message,
          requestId: err.requestId,
        });
      }
    }
  }

  return (
    <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Grounded AI Tutor
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Modular 16-stage curriculum tutor with RAG citations, anti-spoiler Socratic coaching, child-safety guardrails, and deterministic SymPy/Pint/Chemistry verification.
          </p>
        </div>
        {usage ? (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs text-slate-700">
            <div>
              Quota:{" "}
              <span className="font-semibold">
                {usage.turns_used_today} / {usage.daily_turn_limit}
              </span>{" "}
              today ({usage.rpm_limit}/min)
            </div>
            <div>Est. Cost Today: ${usage.estimated_cost_usd_today}</div>
          </div>
        ) : null}
      </header>

      {error ? (
        <ErrorBanner
          title={`AI Tutor Notice (${error.code})`}
          message={error.message}
          requestId={error.requestId}
        />
      ) : null}

      {flagStatus ? (
        <p
          role="status"
          className="rounded-md border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm text-indigo-900"
        >
          {flagStatus}
        </p>
      ) : null}

      {modelsCatalog ? (
        <section
          aria-label="Provider Capabilities & Limitations"
          className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-900">
              Model Routing Status:
            </span>
            {modelsCatalog.providers.map((p) => (
              <StatusBadge
                key={p.provider}
                tone={p.configured ? "healthy" : "neutral"}
              >
                {p.provider}: {p.configured ? p.fast_model : "key not set"}
              </StatusBadge>
            ))}
          </div>
          <p className="mt-2 text-slate-600">
            {modelsCatalog.known_limitations[0]}{" "}
            {modelsCatalog.known_limitations[1]}
          </p>
        </section>
      ) : null}

      {loading ? <LoadingCard message="Loading AI Tutor sessions..." /> : null}

      {!loading ? (
        <div className="grid gap-6 lg:grid-cols-4">
          <aside className="space-y-4 lg:col-span-1">
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
              <h2 className="text-sm font-semibold text-slate-900">
                Start New Session
              </h2>
              <form
                onSubmit={(e) => void handleCreateSession(e)}
                className="mt-3 space-y-3"
              >
                <div>
                  <label
                    htmlFor="ai-sess-title"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Session Topic
                  </label>
                  <input
                    id="ai-sess-title"
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label
                    htmlFor="ai-sess-subject"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Subject Scope
                  </label>
                  <select
                    id="ai-sess-subject"
                    value={newSubjectId}
                    onChange={(e) => setNewSubjectId(e.target.value)}
                    className="mt-1 w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
                  >
                    <option value="">All Published Subjects</option>
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label
                      htmlFor="ai-new-mode"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Mode
                    </label>
                    <select
                      id="ai-new-mode"
                      value={newMode}
                      onChange={(e) =>
                        setNewMode(e.target.value as TeachingMode)
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-xs"
                    >
                      {MODES.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="ai-new-lang"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Language
                    </label>
                    <select
                      id="ai-new-lang"
                      value={newLanguage}
                      onChange={(e) => setNewLanguage(e.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-xs"
                    >
                      {(modelsCatalog?.supported_languages ?? ["en", "hi"]).map(
                        (lang) => (
                          <option key={lang} value={lang}>
                            {lang}
                          </option>
                        )
                      )}
                    </select>
                  </div>
                </div>
                <button
                  type="submit"
                  className="w-full rounded-md bg-indigo-700 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
                >
                  Create Tutor Session
                </button>
              </form>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
              <h2 className="text-sm font-semibold text-slate-900">
                Your Sessions ({sessions.length})
              </h2>
              {sessions.length === 0 ? (
                <p className="mt-2 text-xs text-slate-500">
                  No tutor sessions yet.
                </p>
              ) : (
                <ul className="mt-2 space-y-1.5">
                  {sessions.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() =>
                          token && void loadSessionMessages(token, s)
                        }
                        className={`w-full rounded-md border px-2.5 py-2 text-left text-xs ${
                          activeSession?.id === s.id
                            ? "border-indigo-600 bg-indigo-50 font-semibold text-indigo-950"
                            : "border-slate-200 text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        <div className="truncate">{s.title}</div>
                        <div className="mt-0.5 text-[11px] text-slate-500">
                          {s.teaching_mode} · {s.language_code}
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </aside>

          <section
            aria-label="Tutor Conversation"
            className="flex flex-col space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-xs lg:col-span-3"
          >
            {!activeSession ? (
              <EmptyState
                title="Create or Select a Tutor Session"
                description="Start a new curriculum-grounded session on the left to ask conceptual doubts, solve equations step by step, or request Socratic hints."
              />
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">
                      {activeSession.title}
                    </h2>
                    <p className="text-xs text-slate-600">
                      Scope: {activeSession.curriculum_context.board_code ?? "CBSE"} ·{" "}
                      {activeSession.curriculum_context.subject_name ?? "General STEM"}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <label htmlFor="turn-mode" className="sr-only">
                      Teaching Mode
                    </label>
                    <select
                      id="turn-mode"
                      value={turnMode}
                      onChange={(e) =>
                        void handleModeSync(
                          e.target.value as TeachingMode,
                          turnLanguage
                        )
                      }
                      className="rounded-md border border-slate-300 px-2.5 py-1.5 text-xs"
                    >
                      {MODES.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                    <label htmlFor="turn-lang" className="sr-only">
                      Explanation Language
                    </label>
                    <select
                      id="turn-lang"
                      value={turnLanguage}
                      onChange={(e) =>
                        void handleModeSync(turnMode, e.target.value)
                      }
                      className="rounded-md border border-slate-300 px-2.5 py-1.5 text-xs"
                    >
                      {(modelsCatalog?.supported_languages ?? ["en", "hi"]).map(
                        (lang) => (
                          <option key={lang} value={lang}>
                            Lang: {lang}
                          </option>
                        )
                      )}
                    </select>
                  </div>
                </div>

                <div className="max-h-[32rem] space-y-4 overflow-y-auto pr-1">
                  {messages.length === 0 ? (
                    <p className="text-sm text-slate-500">
                      Ask a question below (for example: &ldquo;Solve 2*x + 4 = 10&rdquo; or &ldquo;Give me a hint on Ohm&apos;s Law&rdquo;).
                    </p>
                  ) : null}

                  {messages.map((m) => (
                    <article
                      key={m.id}
                      className={`rounded-xl border p-4 text-sm ${
                        m.role === "student"
                          ? "ml-8 border-indigo-200 bg-indigo-50/50"
                          : "mr-4 border-slate-200 bg-slate-50"
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2">
                        <span className="text-xs font-semibold uppercase text-slate-700">
                          {m.role === "student" ? "You" : "AI Tutor"}
                        </span>
                        {m.role === "assistant" ? (
                          <div className="flex flex-wrap items-center gap-1.5">
                            <StatusBadge
                              tone={
                                m.verification_status === "verified"
                                  ? "healthy"
                                  : m.verification_status ===
                                      "verification_failed"
                                    ? "degraded"
                                    : "neutral"
                              }
                            >
                              {m.verification_status}
                            </StatusBadge>
                            {m.spoiler_guard ? (
                              <StatusBadge tone="neutral">
                                Anti-Spoiler
                              </StatusBadge>
                            ) : null}
                            {m.is_fallback ? (
                              <StatusBadge tone="degraded">
                                Grounded Fallback
                              </StatusBadge>
                            ) : null}
                            <button
                              type="button"
                              onClick={() => void handleFlagMessage(m.id)}
                              className="rounded border border-slate-300 px-2 py-0.5 text-[11px] text-slate-600 hover:bg-white"
                            >
                              Report Issue
                            </button>
                          </div>
                        ) : null}
                      </div>

                      <div className="whitespace-pre-wrap leading-relaxed text-slate-900">
                        <MathText text={m.content_markdown} />
                      </div>

                      {m.citations.length > 0 ? (
                        <div className="mt-3 border-t border-slate-200 pt-2">
                          <p className="text-xs font-semibold text-slate-700">
                            Cited Curriculum Sources:
                          </p>
                          <ul className="mt-1 space-y-1 text-xs text-slate-600">
                            {m.citations.map((c) => (
                              <li key={c.chunk_id}>
                                <span className="font-medium text-slate-800">
                                  [{c.hierarchy_path}]
                                </span>{" "}
                                {c.excerpt.slice(0, 180)}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {m.generated_practice.length > 0 ? (
                        <div className="mt-3 rounded-lg border border-indigo-100 bg-white p-3">
                          <p className="text-xs font-semibold text-indigo-900">
                            AI-Generated Practice Draft (Not an official PYQ):
                          </p>
                          {m.generated_practice.map((d, dIdx) => (
                            <div key={dIdx} className="mt-1.5 text-xs">
                              <MathText text={d.stem_markdown} />
                              <ul className="mt-1 grid gap-1 sm:grid-cols-2">
                                {d.options.map((opt) => (
                                  <li key={opt.option_key}>
                                    ({opt.option_key}){" "}
                                    <MathText text={opt.content_markdown} />
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {m.follow_up_questions.length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {m.follow_up_questions.map((fq, fqIdx) => (
                            <button
                              key={fqIdx}
                              type="button"
                              onClick={() => void submitPrompt(fq)}
                              className="rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs text-indigo-800 hover:bg-indigo-50"
                            >
                              {fq}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void submitPrompt();
                  }}
                  className="flex flex-col gap-2 border-t border-slate-100 pt-3 sm:flex-row"
                >
                  <label htmlFor="ai-turn-input" className="sr-only">
                    Ask your academic question
                  </label>
                  <input
                    id="ai-turn-input"
                    type="text"
                    required
                    value={promptInput}
                    onChange={(e) => setPromptInput(e.target.value)}
                    placeholder="Ask a doubt, equation (e.g., Solve 3*x + 5 = 20), or concept question..."
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                  <button
                    type="submit"
                    disabled={sending}
                    className="rounded-md bg-indigo-700 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-50"
                  >
                    {sending ? "Thinking..." : "Ask Tutor"}
                  </button>
                </form>
              </>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
