"use client";

import type {
  GlossaryTermOut,
  LanguageCapabilityOut,
} from "@go4guru/contracts";
import { StatusBadge } from "@go4guru/ui";
import { useMemo, useState } from "react";
import { MathText } from "@/components/math-text";
import { upsertMultilingualGlossaryTerm } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

interface GlossaryTerminologyTabProps {
  capabilities: LanguageCapabilityOut[];
  terms: GlossaryTermOut[];
  loading: boolean;
  onRefresh: () => Promise<void>;
}

const EDITOR_ROLES = new Set([
  "teacher",
  "content_admin",
  "academic_reviewer",
  "platform_admin",
]);

export function GlossaryTerminologyTab({
  capabilities,
  terms,
  loading,
  onRefresh,
}: GlossaryTerminologyTabProps) {
  const { token, user } = useAuth();
  const [langFilter, setLangFilter] = useState("all");
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [search, setSearch] = useState("");

  const [conceptKey, setConceptKey] = useState("");
  const [subjectArea, setSubjectArea] = useState("physics");
  const [englishTerm, setEnglishTerm] = useState("");
  const [languageCode, setLanguageCode] = useState("hi");
  const [localizedTerm, setLocalizedTerm] = useState("");
  const [transliteration, setTransliteration] = useState("");
  const [latexSymbol, setLatexSymbol] = useState("");
  const [preserveEnglish, setPreserveEnglish] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canEdit = (user?.roles ?? []).some((r) => EDITOR_ROLES.has(r));

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return terms.filter((term) => {
      if (langFilter !== "all" && term.language_code !== langFilter)
        return false;
      if (subjectFilter !== "all" && term.subject_area !== subjectFilter)
        return false;
      if (!q) return true;
      return (
        term.english_term.toLowerCase().includes(q) ||
        term.localized_term.toLowerCase().includes(q) ||
        (term.transliteration ?? "").toLowerCase().includes(q) ||
        term.concept_key.toLowerCase().includes(q)
      );
    });
  }, [terms, langFilter, subjectFilter, search]);

  async function handleSubmitTerm(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      await upsertMultilingualGlossaryTerm(token, {
        concept_key: conceptKey.trim().toLowerCase().replace(/\s+/g, "_"),
        subject_area: subjectArea,
        english_term: englishTerm.trim(),
        language_code: languageCode,
        localized_term: localizedTerm.trim(),
        transliteration: transliteration.trim() || null,
        latex_symbol: latexSymbol.trim() || null,
        preserve_english_in_bilingual: preserveEnglish,
      });
      setConceptKey("");
      setEnglishTerm("");
      setLocalizedTerm("");
      setTransliteration("");
      setLatexSymbol("");
      await onRefresh();
      setMessage("Saved STEM glossary term to the multilingual dictionary.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save glossary term."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-6" aria-label="STEM Terminology Dictionary">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Bilingual STEM Terminology Dictionary
          </h2>
          <p className="text-sm text-slate-600">
            Preserves NCERT / JEE / NEET English technical terms and LaTeX
            symbols alongside verified regional script equivalents.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter term or concept..."
            aria-label="Filter glossary terms"
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm"
          />
          <select
            value={langFilter}
            onChange={(e) => setLangFilter(e.target.value)}
            aria-label="Filter glossary by language"
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
          >
            <option value="all">All Languages</option>
            {capabilities.map((c) => (
              <option key={c.language_code} value={c.language_code}>
                {c.display_name} ({c.language_code})
              </option>
            ))}
          </select>
          <select
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            aria-label="Filter glossary by subject"
            className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
          >
            <option value="all">All Subjects</option>
            <option value="physics">Physics</option>
            <option value="chemistry">Chemistry</option>
            <option value="mathematics">Mathematics</option>
            <option value="biology">Biology</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading STEM glossary dictionary...
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          No glossary terms match the selected filter.
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((term) => (
            <article
              key={term.id}
              className="rounded-xl border border-slate-200 bg-white p-4 space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    {term.localized_term}
                  </h3>
                  <p className="text-xs text-slate-600">
                    English: <strong className="text-slate-900">{term.english_term}</strong>
                    {term.transliteration ? ` · ${term.transliteration}` : ""}
                  </p>
                </div>
                <StatusBadge
                  tone={term.review_status === "approved" ? "healthy" : "neutral"}
                >
                  {term.language_code.toUpperCase()}
                </StatusBadge>
              </div>

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
                <span className="capitalize">{term.subject_area}</span>
                {term.latex_symbol && (
                  <>
                    <span aria-hidden="true">·</span>
                    <MathText text={term.latex_symbol} />
                  </>
                )}
                <span aria-hidden="true">·</span>
                <span>
                  {term.preserve_english_in_bilingual
                    ? "Keeps English in bilingual mode"
                    : "Localized only"}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Add / Update Term Form (Teachers, Content Admins, Reviewers) */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-5 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Add or Update Verified STEM Term
          </h3>
          <p className="text-xs text-slate-600">
            {canEdit
              ? "Authorized educators and reviewers can register terminology mappings directly."
              : "Sign in with a teacher, content admin, or academic reviewer role to add terms."}
          </p>
        </div>

        <form
          onSubmit={(e) => void handleSubmitTerm(e)}
          className="grid gap-3 md:grid-cols-3"
        >
          <input
            required
            disabled={!canEdit}
            value={conceptKey}
            onChange={(e) => setConceptKey(e.target.value)}
            placeholder="Concept key (e.g. momentum)"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
          />
          <input
            required
            disabled={!canEdit}
            value={englishTerm}
            onChange={(e) => setEnglishTerm(e.target.value)}
            placeholder="English STEM term (e.g. Momentum)"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
          />
          <input
            required
            disabled={!canEdit}
            value={localizedTerm}
            onChange={(e) => setLocalizedTerm(e.target.value)}
            placeholder="Localized script term (e.g. संवेग)"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
          />
          <select
            disabled={!canEdit}
            value={languageCode}
            onChange={(e) => setLanguageCode(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
          >
            {capabilities.map((c) => (
              <option key={c.language_code} value={c.language_code}>
                {c.display_name} ({c.language_code})
              </option>
            ))}
          </select>
          <select
            disabled={!canEdit}
            value={subjectArea}
            onChange={(e) => setSubjectArea(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
          >
            <option value="physics">Physics</option>
            <option value="chemistry">Chemistry</option>
            <option value="mathematics">Mathematics</option>
            <option value="biology">Biology</option>
          </select>
          <input
            disabled={!canEdit}
            value={latexSymbol}
            onChange={(e) => setLatexSymbol(e.target.value)}
            placeholder="LaTeX symbol (e.g. $p = mv$)"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-mono disabled:bg-slate-100"
          />
          <input
            disabled={!canEdit}
            value={transliteration}
            onChange={(e) => setTransliteration(e.target.value)}
            placeholder="Transliteration (optional)"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
          />
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              disabled={!canEdit}
              checked={preserveEnglish}
              onChange={(e) => setPreserveEnglish(e.target.checked)}
            />
            Preserve English term in bilingual mode
          </label>
          <button
            type="submit"
            disabled={!canEdit || submitting}
            className="whitespace-nowrap shrink-0 rounded-md bg-slate-900 px-3.5 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Save Glossary Term"}
          </button>
        </form>

        {message && <p className="text-xs text-emerald-800">{message}</p>}
        {error && <p className="text-xs text-rose-700">{error}</p>}
      </div>
    </section>
  );
}
