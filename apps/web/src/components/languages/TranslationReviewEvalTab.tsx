"use client";

import type {
  LanguageCapabilityOut,
  LanguageQualityEvaluationOut,
  TranslationEntryOut,
} from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import { useState } from "react";
import { MathText } from "@/components/math-text";
import {
  reviewTranslationEntry,
  runLanguageQualityEvaluation,
  submitTranslationEntry,
} from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { verifyClientNotationPreservation } from "@/lib/multilingual-helpers";

interface TranslationReviewEvalTabProps {
  capabilities: LanguageCapabilityOut[];
  translations: TranslationEntryOut[];
  evaluations: LanguageQualityEvaluationOut[];
  onRefreshAll: () => Promise<void>;
}

const REVIEWER_ROLES = new Set([
  "academic_reviewer",
  "content_admin",
  "platform_admin",
]);
const TRANSLATOR_ROLES = new Set([
  "teacher",
  "academic_reviewer",
  "content_admin",
  "platform_admin",
]);

export function TranslationReviewEvalTab({
  capabilities,
  translations,
  evaluations,
  onRefreshAll,
}: TranslationReviewEvalTabProps) {
  const { token, user } = useAuth();
  const roles = user?.roles ?? [];
  const canReview = roles.some((r) => REVIEWER_ROLES.has(r));
  const canSubmit = roles.some((r) => TRANSLATOR_ROLES.has(r));

  // Translation submission form
  const [resourceType, setResourceType] = useState<
    "ui_string" | "question" | "lesson_segment" | "formula_note" | "concept_summary"
  >("concept_summary");
  const [resourceKey, setResourceKey] = useState("physics.newtons_second_law");
  const [targetLang, setTargetLang] = useState("hi");
  const [sourceText, setSourceText] = useState(
    "Force equals mass times acceleration: $F = ma$ with $g = 9.8 m/s^2$."
  );
  const [translatedText, setTranslatedText] = useState(
    "बल (Force) द्रव्यमान और त्वरण के गुणनफल के बराबर होता है: $F = ma$, जहाँ $g = 9.8 m/s^2$ है।"
  );
  const [submitting, setSubmitting] = useState(false);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [translationMsg, setTranslationMsg] = useState<string | null>(null);
  const [translationErr, setTranslationErr] = useState<string | null>(null);

  // Quality evaluation runner
  const [evalLang, setEvalLang] = useState("hi");
  const [evalModality, setEvalModality] = useState<
    "bilingual" | "explanation" | "ui" | "subtitle" | "question" | "answer"
  >("bilingual");
  const [runningEval, setRunningEval] = useState(false);
  const [evalMsg, setEvalMsg] = useState<string | null>(null);
  const [evalErr, setEvalErr] = useState<string | null>(null);

  const liveNotation = verifyClientNotationPreservation(
    sourceText,
    translatedText
  );

  async function handleSubmitTranslation(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setTranslationMsg(null);
    setTranslationErr(null);
    try {
      await submitTranslationEntry(token, {
        resource_type: resourceType,
        resource_key: resourceKey.trim(),
        source_language_code: "en",
        target_language_code: targetLang,
        source_text: sourceText.trim(),
        translated_text: translatedText.trim(),
      });
      await onRefreshAll();
      setTranslationMsg(
        "Submitted translation to academic review queue with automated notation verification."
      );
    } catch (err) {
      setTranslationErr(
        err instanceof Error ? err.message : "Failed to submit translation."
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReview(
    entryId: string,
    decision: "approved" | "needs_revision" | "rejected"
  ) {
    if (!token) return;
    setReviewingId(entryId);
    setTranslationMsg(null);
    setTranslationErr(null);
    try {
      await reviewTranslationEntry(token, entryId, {
        decision,
        reviewer_notes: `Reviewed via Phase 10 Language Studio (${decision}).`,
      });
      await onRefreshAll();
      setTranslationMsg(`Marked translation as ${decision}.`);
    } catch (err) {
      setTranslationErr(
        err instanceof Error ? err.message : "Unable to review translation."
      );
    } finally {
      setReviewingId(null);
    }
  }

  async function handleRunEval() {
    if (!token) return;
    setRunningEval(true);
    setEvalMsg(null);
    setEvalErr(null);
    try {
      const res = await runLanguageQualityEvaluation(token, {
        language_code: evalLang,
        modality: evalModality,
      });
      await onRefreshAll();
      setEvalMsg(
        `Completed ${res.language_code.toUpperCase()} (${res.modality}) evaluation: ${res.overall_score.toFixed(1)}% overall (${res.passed ? "PASSED" : "NEEDS IMPROVEMENT"}).`
      );
    } catch (err) {
      setEvalErr(
        err instanceof Error
          ? err.message
          : "Failed to run language quality evaluation."
      );
    } finally {
      setRunningEval(false);
    }
  }

  return (
    <section
      className="space-y-8"
      aria-label="Translation review workflow and language quality evaluations"
    >
      {/* Part 1: Translation Submission & Review Queue */}
      <div className="grid gap-6 lg:grid-cols-12">
        <form
          onSubmit={(e) => void handleSubmitTranslation(e)}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 lg:col-span-5"
        >
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Submit Translation for Review
            </h2>
            <p className="text-xs text-slate-600">
              Automated notation checks verify LaTeX formulas, SI units, and
              chemical equations before reviewer approval.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-xs font-medium text-slate-700">
              Resource Type
              <select
                value={resourceType}
                onChange={(e) =>
                  setResourceType(
                    e.target.value as
                      | "ui_string"
                      | "question"
                      | "lesson_segment"
                      | "formula_note"
                      | "concept_summary"
                  )
                }
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
              >
                <option value="concept_summary">Concept Summary</option>
                <option value="question">Question Stem</option>
                <option value="lesson_segment">Lesson Segment</option>
                <option value="formula_note">Formula Note</option>
                <option value="ui_string">UI String</option>
              </select>
            </label>

            <label className="block text-xs font-medium text-slate-700">
              Target Language
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
              >
                {capabilities
                  .filter((c) => c.language_code !== "en")
                  .map((c) => (
                    <option key={c.language_code} value={c.language_code}>
                      {c.display_name} ({c.language_code})
                    </option>
                  ))}
              </select>
            </label>
          </div>

          <label className="block text-xs font-medium text-slate-700">
            Resource Key
            <input
              required
              value={resourceKey}
              onChange={(e) => setResourceKey(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 font-mono text-xs"
            />
          </label>

          <label className="block text-xs font-medium text-slate-700">
            English Source Text
            <textarea
              rows={2}
              required
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-xs"
            />
          </label>

          <label className="block text-xs font-medium text-slate-700">
            Translated Text
            <textarea
              rows={3}
              required
              value={translatedText}
              onChange={(e) => setTranslatedText(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-xs"
            />
          </label>

          <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
            <span className="text-slate-700">Pre-submit Notation Audit</span>
            <StatusBadge
              tone={liveNotation.all_preserved ? "healthy" : "degraded"}
            >
              {liveNotation.all_preserved
                ? "Math & Science Intact"
                : `Missing ${liveNotation.missing_math.length + liveNotation.missing_science.length} token(s)`}
            </StatusBadge>
          </div>

          <button
            type="submit"
            disabled={!canSubmit || !token || submitting}
            className="whitespace-nowrap shrink-0 rounded-md bg-indigo-700 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-800 disabled:opacity-50"
          >
            {submitting
              ? "Submitting..."
              : canSubmit
                ? "Submit to Translation Review Queue"
                : "Sign in as Teacher / Reviewer to Submit"}
          </button>

          {translationMsg && (
            <p className="text-xs text-emerald-800">{translationMsg}</p>
          )}
          {translationErr && (
            <p className="text-xs text-rose-700">{translationErr}</p>
          )}
        </form>

        {/* Review Queue List */}
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 lg:col-span-7">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">
              Academic Translation Review Queue ({translations.length})
            </h2>
            <span className="text-xs text-slate-500">
              {canReview
                ? "Reviewer approval enabled"
                : "Approval requires Academic Reviewer role"}
            </span>
          </div>

          {translations.length === 0 ? (
            <p className="rounded-lg border border-slate-100 bg-slate-50 p-4 text-xs text-slate-600">
              {token
                ? "No translation entries in the review queue yet."
                : "Sign in to load and review pending academic translations."}
            </p>
          ) : (
            <div className="space-y-3">
              {translations.map((entry) => (
                <article
                  key={entry.id}
                  className="rounded-lg border border-slate-200 p-3.5 space-y-2 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-mono font-medium text-slate-900">
                      {entry.resource_key} ·{" "}
                      {entry.source_language_code.toUpperCase()} →{" "}
                      {entry.target_language_code.toUpperCase()}
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge
                        tone={entry.notation_preserved ? "healthy" : "degraded"}
                      >
                        {entry.notation_preserved
                          ? "Notation OK"
                          : "Notation Drift"}
                      </StatusBadge>
                      <StatusBadge
                        tone={
                          entry.status === "approved"
                            ? "healthy"
                            : entry.status === "pending_review"
                              ? "degraded"
                              : "neutral"
                        }
                      >
                        {entry.status}
                      </StatusBadge>
                    </div>
                  </div>
                  <div className="text-slate-600">
                    <MathText text={entry.translated_text} />
                  </div>
                  {canReview && entry.status !== "approved" && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      <button
                        type="button"
                        disabled={reviewingId === entry.id}
                        onClick={() => void handleReview(entry.id, "approved")}
                        className="rounded-md bg-emerald-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-800"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        disabled={reviewingId === entry.id}
                        onClick={() =>
                          void handleReview(entry.id, "needs_revision")
                        }
                        className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50"
                      >
                        Needs Revision
                      </button>
                      <button
                        type="button"
                        disabled={reviewingId === entry.id}
                        onClick={() => void handleReview(entry.id, "rejected")}
                        className="rounded-md border border-rose-300 bg-white px-2.5 py-1 text-xs font-medium text-rose-800 hover:bg-rose-50"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Part 2: Language Quality Evaluation Suite */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Empirical Language Quality Evaluation Suite
            </h2>
            <p className="text-xs text-slate-600">
              Measures script Unicode fidelity, LaTeX math preservation,
              scientific/SI notation accuracy, terminology alignment, and
              fluency per language.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={evalLang}
              onChange={(e) => setEvalLang(e.target.value)}
              aria-label="Language to evaluate"
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
            >
              {capabilities.map((c) => (
                <option key={c.language_code} value={c.language_code}>
                  {c.display_name} ({c.language_code})
                </option>
              ))}
            </select>
            <select
              value={evalModality}
              onChange={(e) =>
                setEvalModality(
                  e.target.value as
                    | "bilingual"
                    | "explanation"
                    | "ui"
                    | "subtitle"
                    | "question"
                    | "answer"
                )
              }
              aria-label="Modality to evaluate"
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
            >
              <option value="bilingual">Bilingual STEM</option>
              <option value="explanation">AI Explanation</option>
              <option value="ui">UI Localization</option>
              <option value="subtitle">Subtitles</option>
              <option value="question">Question Bank</option>
              <option value="answer">Answer Handling</option>
            </select>
            <button
              type="button"
              disabled={!canReview || !token || runningEval}
              onClick={() => void handleRunEval()}
              className="whitespace-nowrap shrink-0 rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {runningEval
                ? "Evaluating..."
                : canReview
                  ? "Run Quality Suite"
                  : "Reviewer Role Required"}
            </button>
          </div>
        </div>

        {evalMsg && <p className="text-xs text-emerald-800">{evalMsg}</p>}
        {evalErr && <p className="text-xs text-rose-700">{evalErr}</p>}

        {evaluations.length === 0 ? (
          <p className="rounded-lg border border-slate-100 bg-slate-50 p-4 text-xs text-slate-600">
            No persisted evaluation runs recorded yet. Reviewers can execute a
            language quality audit above, and automated unit tests continuously
            verify script & notation metrics across all 14 languages.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs tabular-nums">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 font-semibold">Language</th>
                  <th className="px-3 py-2 font-semibold">Modality</th>
                  <th className="px-3 py-2 font-semibold text-right">Script</th>
                  <th className="px-3 py-2 font-semibold text-right">Math</th>
                  <th className="px-3 py-2 font-semibold text-right">Science</th>
                  <th className="px-3 py-2 font-semibold text-right">Terms</th>
                  <th className="px-3 py-2 font-semibold text-right">Overall</th>
                  <th className="px-3 py-2 font-semibold">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {evaluations.map((ev) => (
                  <tr key={ev.id}>
                    <td className="px-3 py-2 font-semibold uppercase text-slate-900">
                      {ev.language_code}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{ev.modality}</td>
                    <td className="px-3 py-2 text-right">
                      {ev.script_fidelity_score.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right">
                      {ev.math_preservation_score.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right">
                      {ev.science_notation_score.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right">
                      {ev.terminology_accuracy_score.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right font-semibold text-slate-900">
                      {ev.overall_score.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge tone={ev.passed ? "healthy" : "degraded"}>
                        {ev.passed ? "Passed" : "Needs Work"}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
