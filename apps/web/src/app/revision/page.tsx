"use client";

import type {
  FlashcardOut,
  FlashcardType,
  RevisionAnalyticsOut,
  StudyPlanOut,
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
  createFlashcard,
  fetchRevisionAnalytics,
  generateStudyPlan,
  listDueFlashcards,
  listFlashcards,
  listStudyPlans,
  reviewFlashcard,
  syncMissedFlashcards,
  updateStudyPlanItemStatus,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function RevisionPage() {
  const router = useRouter();
  const { token, initializing } = useAuth();

  const [dueCards, setDueCards] = useState<FlashcardOut[]>([]);
  const [allCards, setAllCards] = useState<FlashcardOut[]>([]);
  const [plans, setPlans] = useState<StudyPlanOut[]>([]);
  const [analytics, setAnalytics] = useState<RevisionAnalyticsOut | null>(null);

  const [revealedCardId, setRevealedCardId] = useState<string | null>(null);
  const [cardType, setCardType] = useState<FlashcardType>("formula");
  const [frontMd, setFrontMd] = useState("");
  const [backMd, setBackMd] = useState("");
  const [hintMd, setHintMd] = useState("");

  const [planTitle, setPlanTitle] = useState("Weekly Adaptive Revision Sprint");
  const [dailyBudget, setDailyBudget] = useState(45);

  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async (authToken: string) => {
    const [due, all, sp, ana] = await Promise.all([
      listDueFlashcards(authToken),
      listFlashcards(authToken),
      listStudyPlans(authToken),
      fetchRevisionAnalytics(authToken),
    ]);
    setDueCards(due);
    setAllCards(all);
    setPlans(sp);
    setAnalytics(ana);
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
              : "Failed to load Revision Workspace."
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

  async function handleSyncMissed() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const res = await syncMissedFlashcards(token);
      setStatusNotice(
        `Synced missed questions: ${res.created_count} new revision card(s) added (${res.existing_count} already queued).`
      );
      await loadAll(token);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Sync failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateCard(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !frontMd.trim() || !backMd.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createFlashcard(token, {
        card_type: cardType,
        front_markdown: frontMd.trim(),
        back_markdown: backMd.trim(),
        hint_markdown: hintMd.trim() || null,
      });
      setFrontMd("");
      setBackMd("");
      setHintMd("");
      setStatusNotice("Flashcard added cleanly to due SM-2+ deck.");
      await loadAll(token);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Create failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleReview(cardId: string, quality: number) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const res = await reviewFlashcard(token, cardId, {
        quality,
        response_ms: 2500,
      });
      setRevealedCardId(null);
      setStatusNotice(
        `Scheduled next review in ${res.new_interval_days} day(s) (ease factor ${res.new_ease}).`
      );
      await loadAll(token);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Review failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleGeneratePlan(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !planTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await generateStudyPlan(token, {
        title: planTitle.trim(),
        daily_minutes_budget: dailyBudget,
      });
      setStatusNotice("Generated personalized daily revision schedule.");
      await loadAll(token);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? `${err.code}: ${err.message}` : "Plan failed."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handlePlanItemStatus(
    itemId: string,
    status: "pending" | "completed" | "skipped"
  ) {
    if (!token) return;
    setBusy(true);
    try {
      await updateStudyPlanItemStatus(token, itemId, status);
      await loadAll(token);
    } finally {
      setBusy(false);
    }
  }

  if (initializing || loading) {
    return <LoadingCard message="Loading Spaced Repetition Deck & Study Planner..." />;
  }

  const activeCard = dueCards[0] ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Spaced Repetition Flashcards &amp; Personalized Study Planner
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            SM-2+ prioritized review across concept, KaTeX formula, vocabulary, and missed-question cards synchronized with adaptive study plans.
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={handleSyncMissed}
          className="rounded-md bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Sync Missed Questions to Cards
        </button>
      </div>

      {error && <ErrorBanner title="Revision Notice" message={error} />}
      {statusNotice && (
        <div
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-900"
        >
          {statusNotice}
        </div>
      )}

      {/* Revision Analytics KPIs */}
      {analytics && (
        <section className="grid gap-4 sm:grid-cols-5">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Total Flashcards</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {analytics.total_flashcards}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Due Now</div>
            <div className="mt-1 text-2xl font-bold text-indigo-700">
              {analytics.due_now_count}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Missed-Q Cards</div>
            <div className="mt-1 text-2xl font-bold text-amber-700">
              {analytics.missed_question_cards_count}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Retention Rate</div>
            <div className="mt-1 text-2xl font-bold text-emerald-700">
              {analytics.retention_success_rate_pct}%
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs text-slate-500">Study Plan Done</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {analytics.active_plan_completion_pct}%
            </div>
          </div>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Active SM-2+ Flashcard Review Deck & Card Creator */}
        <div className="space-y-6 lg:col-span-7">
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">
                Due Revision Queue ({dueCards.length})
              </h2>
              {activeCard && (
                <StatusBadge
                  tone={
                    activeCard.card_type === "missed_question"
                      ? "degraded"
                      : "neutral"
                  }
                >
                  {activeCard.card_type} · priority {activeCard.priority_score}
                </StatusBadge>
              )}
            </div>

            {!activeCard ? (
              <div className="mt-4">
                <EmptyState
                  title="All due flashcards reviewed"
                  description="Create a formula, concept, or vocabulary card below, or sync missed practice questions to queue new reviews."
                />
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-5">
                  <div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                    Front Prompt {activeCard.concept_title ? `· ${activeCard.concept_title}` : ""}
                  </div>
                  <div className="mt-2 text-base font-medium text-slate-900">
                    <MathText text={activeCard.front_markdown} />
                  </div>
                  {activeCard.hint_markdown && (
                    <p className="mt-2 text-xs text-indigo-900">
                      Hint: {activeCard.hint_markdown}
                    </p>
                  )}
                </div>

                {revealedCardId !== activeCard.id ? (
                  <button
                    type="button"
                    onClick={() => setRevealedCardId(activeCard.id)}
                    className="w-full rounded-md bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
                  >
                    Reveal Answer &amp; Rate Recall
                  </button>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-slate-900">
                      <div className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                        Verified Solution / Card Back
                      </div>
                      <div className="mt-2 whitespace-pre-wrap">
                        <MathText text={activeCard.back_markdown} />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                      {[
                        { q: 1, label: "1 · Forgot (Lapse)" },
                        { q: 2, label: "2 · Hard Lapse" },
                        { q: 3, label: "3 · Recall" },
                        { q: 4, label: "4 · Good" },
                        { q: 5, label: "5 · Effortless" },
                      ].map((opt) => (
                        <button
                          key={opt.q}
                          type="button"
                          disabled={busy}
                          onClick={() => handleReview(activeCard.id, opt.q)}
                          className={`rounded-md px-2 py-2 text-xs font-semibold ${
                            opt.q < 3
                              ? "border border-rose-300 bg-rose-50 text-rose-900 hover:bg-rose-100"
                              : "border border-emerald-300 bg-emerald-50 text-emerald-900 hover:bg-emerald-100"
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Create Multi-Modal Flashcard */}
          <form
            onSubmit={handleCreateCard}
            className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-base font-bold text-slate-900">
              Create Flashcard (Concept / Formula / Vocabulary)
            </h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label
                  htmlFor="card-type-select"
                  className="block text-xs font-medium text-slate-600"
                >
                  Card Type
                </label>
                <select
                  id="card-type-select"
                  value={cardType}
                  onChange={(e) => setCardType(e.target.value as FlashcardType)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-sm"
                >
                  <option value="formula">Formula Card (KaTeX)</option>
                  <option value="concept">Concept Card</option>
                  <option value="vocabulary">Vocabulary Card</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label
                  htmlFor="card-hint-input"
                  className="block text-xs font-medium text-slate-600"
                >
                  Memory Cue / Hint (Optional)
                </label>
                <input
                  id="card-hint-input"
                  type="text"
                  value={hintMd}
                  onChange={(e) => setHintMd(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                  placeholder="Optional recall cue..."
                />
              </div>
            </div>
            <div>
              <label
                htmlFor="card-front-input"
                className="block text-xs font-medium text-slate-600"
              >
                Front Prompt (Supports $KaTeX$)
              </label>
              <input
                id="card-front-input"
                type="text"
                required
                value={frontMd}
                onChange={(e) => setFrontMd(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="e.g., State Ohm's Law formula for resistance $R$"
              />
            </div>
            <div>
              <label
                htmlFor="card-back-input"
                className="block text-xs font-medium text-slate-600"
              >
                Back Answer
              </label>
              <textarea
                id="card-back-input"
                required
                rows={2}
                value={backMd}
                onChange={(e) => setBackMd(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="e.g., $V = I R$, so $R = V / I$ in Ohms"
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              className="rounded-md bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Add Flashcard to Deck
            </button>
          </form>
        </div>

        {/* Right: Personalized Study Planner & Deck Summary */}
        <aside className="space-y-6 lg:col-span-5">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-bold text-slate-900">
              Personalized Revision Study Plan
            </h2>
            <form onSubmit={handleGeneratePlan} className="mt-3 space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  aria-label="Study plan title"
                  value={planTitle}
                  onChange={(e) => setPlanTitle(e.target.value)}
                  className="flex-1 rounded-md border border-slate-300 px-2.5 py-1.5 text-xs"
                />
                <select
                  aria-label="Daily minutes budget"
                  value={dailyBudget}
                  onChange={(e) => setDailyBudget(Number(e.target.value))}
                  className="rounded-md border border-slate-300 px-2 py-1.5 text-xs"
                >
                  <option value={30}>30 min/day</option>
                  <option value={45}>45 min/day</option>
                  <option value={60}>60 min/day</option>
                  <option value={90}>90 min/day</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                Generate Adaptive Study Plan
              </button>
            </form>

            {plans.length === 0 ? (
              <p className="mt-3 text-xs text-slate-500">
                No active study plan yet. Generate one above based on your weak concepts and due flashcards.
              </p>
            ) : (
              <div className="mt-4 space-y-2">
                <div className="text-xs font-semibold text-slate-700">
                  {plans[0].title} ({plans[0].daily_minutes_budget} min/day)
                </div>
                {plans[0].items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 p-2.5 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-slate-900">
                        {item.title}
                      </div>
                      <div className="text-slate-600">{item.description}</div>
                      <div className="mt-1 text-[11px] text-slate-500">
                        {item.scheduled_for} · {item.estimated_minutes} min ·{" "}
                        {item.item_type}
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={busy || item.status === "completed"}
                      onClick={() => handlePlanItemStatus(item.id, "completed")}
                      className="shrink-0 rounded border border-slate-300 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      {item.status === "completed" ? "Completed" : "Mark Done"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900">
              Deck Inventory ({allCards.length})
            </h2>
            {allCards.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">No flashcards created yet.</p>
            ) : (
              <ul className="mt-2 space-y-1.5 text-xs">
                {allCards.slice(0, 6).map((c) => (
                  <li
                    key={c.id}
                    className="flex items-center justify-between rounded border border-slate-100 bg-slate-50 px-2.5 py-1.5"
                  >
                    <span className="truncate pr-2 text-slate-800">
                      {c.front_markdown}
                    </span>
                    <StatusBadge tone={c.is_due ? "degraded" : "healthy"}>
                      {c.is_due ? "Due" : `${c.interval_days}d`}
                    </StatusBadge>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
